"""
SQL AI Agent Chatbot - Streamlit Application

A conversational interface for querying databases using natural language.
The agent remembers conversation history and can answer follow-up questions.
"""

import streamlit as st
import sys
import os
import ibis
import pandas as pd
import json
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.SqlAgent import SqlAgent
from sql_ai_agent.llm_config_loader import load_config
from sql_ai_agent.log_database import (
    init_postgres_log_schema,
    init_duckdb_log_schema,
    DatabaseLogHandler,
    verify_log_table,
)
from sql_ai_agent.logger import setup_logging

# Page configuration
st.set_page_config(
    page_title="SQL AI Agent Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .sql-query {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #1f77b4;
        font-family: monospace;
        margin: 0.5rem 0;
    }
    .error-message {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #f44336;
        color: #c62828;
    }
    .success-message {
        background-color: #e8f5e9;
        padding: 0.5rem;
        border-radius: 0.3rem;
        border-left: 3px solid #4caf50;
        color: #2e7d32;
    }
    .log-entry {
        font-family: monospace;
        font-size: 0.85rem;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.3rem;
        border-left: 3px solid #9e9e9e;
        color: #212121;
    }
    .log-debug {
        background-color: #f5f5f5;
        border-left-color: #757575;
        color: #424242;
    }
    .log-info {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
        color: #0d47a1;
    }
    .log-warning {
        background-color: #fff3e0;
        border-left-color: #ff9800;
        color: #e65100;
    }
    .log-error {
        background-color: #ffebee;
        border-left-color: #f44336;
        color: #b71c1c;
    }
</style>
""", unsafe_allow_html=True)


def read_log_file(log_file_path, max_lines=50):
    """Read the most recent log entries from a log file."""
    if not os.path.exists(log_file_path):
        return []

    try:
        with open(log_file_path, 'r') as f:
            lines = f.readlines()

        # Get the last max_lines entries
        recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines

        log_entries = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            try:
                # Try to parse as JSON
                log_entry = json.loads(line)
                log_entries.append(log_entry)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                log_entries.append({'message': line, 'level': 'INFO'})

        return log_entries
    except Exception as e:
        return [{'message': f'Error reading log file: {str(e)}', 'level': 'ERROR'}]


def format_log_entry(entry, show_full=False):
    """Format a log entry for display."""
    if isinstance(entry, dict):
        level = entry.get('level', 'INFO')
        message = entry.get('message', '')
        timestamp = entry.get('timestamp', '')

        # CSS class based on level
        level_class = f"log-{level.lower()}"

        if show_full:
            # Show full JSON
            formatted = f'<div class="log-entry {level_class}">'
            formatted += f'<strong>[{level}]</strong> {timestamp}<br/>'
            formatted += f'{message}<br/>'

            # Show extra fields if present
            extra_fields = {k: v for k, v in entry.items()
                          if k not in ['level', 'message', 'timestamp', 'logger']}
            if extra_fields:
                formatted += f'<small>{json.dumps(extra_fields, indent=2)}</small>'

            formatted += '</div>'
            return formatted
        else:
            # Compact view
            return f'<div class="log-entry {level_class}"><strong>[{level}]</strong> {message}</div>'
    else:
        return f'<div class="log-entry log-info">{entry}</div>'


@st.cache_resource
def init_database_connection(db_type, host="postgres", port=5432):
    """Initialize database connection (cached to persist across reruns)."""
    try:
        if db_type == "PostgreSQL":
            con = ibis.postgres.connect(
                user="postgres",
                password="password",
                host=host,
                port=port,
                database="my_db",
            )
            return con, "air_traffic"
        else:  # DuckDB
            con = ibis.duckdb.connect()
            # Load sample data for DuckDB
            try:
                df = pd.read_csv(os.path.join(project_root, "data/air_traffic_gold.csv"))
                con.create_table("air_traffic", df, overwrite=True)
            except Exception as e:
                st.error(f"Failed to load sample data: {e}")
                return None, None
            return con, "air_traffic"
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None, None


def get_table_row_count(con, tbl_name):
    """Get the total number of rows in the table."""
    try:
        # Use Ibis API to get count
        table = con.table(tbl_name)
        count_result = table.count().execute()
        return int(count_result)
    except Exception as e:
        # Fallback: try raw SQL
        try:
            query = f'SELECT COUNT(*) FROM "{tbl_name}"'
            result = con.sql(query).to_pandas()
            return int(result.iloc[0, 0])
        except Exception as e2:
            st.error(f"Failed to get row count: {e2}")
            return None


def init_agent(con, tbl_name, provider, model, memory_enabled, memory_size,
               enable_logging=False, log_level="INFO", log_file=None,
               read_only=True, enforce_limit=True, max_result_limit=10,
               log_to_database=False, log_db_con=None, log_db_type=None):
    """Initialize SQL AI Agent with optional database logging."""
    try:
        config = load_config()

        # Get provider settings
        api_key = config.get_api_key(provider)
        base_url = config.get_base_url(provider)
        fallback_model = config.get_fallback_model(provider)

        # If database logging is enabled, set log_file to None and disable console
        # (logs will go to database instead)
        if log_to_database and log_db_con is not None:
            log_file = None
            log_to_console = False  # Disable console when using database
        else:
            log_to_console = True

        agent = SqlAgent(
            api_key=api_key,
            base_url=base_url,
            model=model,
            con=con,
            tbl_name=tbl_name,
            fallback=True,
            fallback_model=fallback_model,
            memory=memory_enabled,
            memory_size=memory_size,
            read_only=read_only,
            enforce_limit=enforce_limit,
            max_result_limit=max_result_limit,
            enable_logging=enable_logging,
            log_level=log_level,
            log_file=log_file,
            log_to_console=log_to_console,
        )

        # Add database logging handler if enabled
        if log_to_database and log_db_con is not None and enable_logging:
            try:
                if not agent.logger:
                    st.error("Logger was not created. Check SqlAgent initialization.")
                    return None

                # Verify log table exists (but don't auto-initialize for PostgreSQL)
                stats = verify_log_table(log_db_con, "sql_agent_logs", log_db_type)
                if not stats.get('exists', False):
                    if log_db_type == "postgres":
                        error_msg = "❌ PostgreSQL log table 'sql_agent_logs' does not exist."
                        if 'error' in stats:
                            error_msg += f"\n\nVerification error: {stats['error']}"
                        error_msg += "\n\nPlease initialize it by clicking 'Initialize Log Schema' button in the Logging Settings sidebar."
                        st.error(error_msg)
                        return None
                    else:
                        # Auto-initialize for DuckDB only
                        st.info("📋 Log table doesn't exist. Initializing DuckDB schema...")
                        init_duckdb_log_schema(log_db_con, "sql_agent_logs")
                        st.success(f"✅ DuckDB log schema initialized automatically")
                else:
                    st.success(f"✅ Found existing log table with {stats.get('row_count', 0)} logs")

                # Get the underlying Python logger
                python_logger = agent.logger.logger

                # Create database handler with custom error handling
                db_handler = DatabaseLogHandler(
                    con=log_db_con,
                    table_name="sql_agent_logs",
                    db_type=log_db_type,
                    schema="public" if log_db_type == "postgres" else None,
                    level=python_logger.level,
                )

                # Override handleError to show errors in Streamlit
                original_handle_error = db_handler.handleError
                def handle_error_with_display(record):
                    import sys
                    import traceback as tb
                    ei = sys.exc_info()
                    if ei:
                        error_msg = f"Database logging error: {''.join(tb.format_exception(*ei))}"
                        st.error(error_msg)
                    original_handle_error(record)

                db_handler.handleError = handle_error_with_display

                # Add handler to logger
                python_logger.addHandler(db_handler)

                # Verify handler was added
                handler_count = len(python_logger.handlers)
                st.success(f"✅ Database logging handler added ({handler_count} handler(s) total)")

                # Log successful initialization
                agent.logger.info(
                    "Database logging initialized",
                    extra={
                        'operation_type': 'initialization',
                        'log_database_type': log_db_type,
                        'log_table': 'sql_agent_logs',
                    }
                )

            except Exception as e:
                st.error(f"Failed to initialize database logging: {e}")
                import traceback
                st.error(traceback.format_exc())

        return agent
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None


def format_dataframe(df):
    """Format dataframe for display."""
    if df is None or df.empty:
        return "No results returned."
    return df


def format_sql_query(query):
    """Format SQL query with proper indentation and line breaks."""
    if not query:
        return query

    try:
        # Try to use sqlglot for formatting
        import sqlglot
        formatted = sqlglot.transpile(query, read="postgres", pretty=True)[0]
        return formatted
    except Exception:
        # If formatting fails, return original with basic formatting
        # Add line breaks after common SQL keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
                   'INNER JOIN', 'OUTER JOIN', 'GROUP BY', 'ORDER BY', 'HAVING',
                   'LIMIT', 'OFFSET', 'UNION', 'AND', 'OR']

        formatted_query = query
        for keyword in keywords:
            formatted_query = formatted_query.replace(f' {keyword} ', f'\n{keyword} ')

        return formatted_query


def display_query_result(result):
    """Display query result with SQL and data."""
    if result.success:
        # Show prompt in expandable section
        if result.prompt:
            with st.expander("💭 Prompt Sent to LLM", expanded=False):
                st.text(result.prompt)

        # Show SQL query in expandable section
        with st.expander("📝 Generated SQL Query", expanded=False):
            formatted_sql = format_sql_query(result.query)
            st.code(formatted_sql, language="sql", line_numbers=True)

        # Check if this is a write operation result
        is_write_operation = (
            result.data is not None
            and not result.data.empty
            and 'query_type' in result.data.columns
            and result.data['query_type'].iloc[0] == 'write_operation'
        )

        # Show result data
        if is_write_operation:
            # Write operation - show success message
            st.success("✅ " + result.data['message'].iloc[0])
        elif result.data is not None and not result.data.empty:
            # SELECT query - show data table
            st.dataframe(result.data, use_container_width=True)
        else:
            st.info("Query executed successfully but returned no data.")
    else:
        # Show error
        st.markdown(f'<div class="error-message">❌ {result.error}</div>', unsafe_allow_html=True)

        # Show prompt if available
        if result.prompt:
            with st.expander("💭 Prompt Sent to LLM", expanded=False):
                st.text(result.prompt)

        if result.query:
            with st.expander("📝 Failed Query", expanded=False):
                formatted_sql = format_sql_query(result.query)
                st.code(formatted_sql, language="sql", line_numbers=True)


# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")

    # Database selection
    st.subheader("Database")
    db_type = st.selectbox(
        "Select Database",
        ["PostgreSQL", "DuckDB"],
        help="Choose between PostgreSQL (requires running container) or DuckDB (in-memory)"
    )

    # LLM Provider selection
    st.subheader("LLM Provider")
    provider_map = {
        "OpenAI": "openai",
        "Anthropic": "anthropic",
        "Google": "google",
        "Docker Model Runner": "docker_model_runner",
    }

    provider_display = st.selectbox(
        "Select Provider",
        list(provider_map.keys()),
        index=0,
    )
    provider = provider_map[provider_display]

    # Model selection
    try:
        config = load_config()
        available_models = config.get_model_names(provider)
        default_model = config.get_default_model(provider)

        model = st.selectbox(
            "Select Model",
            available_models,
            index=available_models.index(default_model) if default_model in available_models else 0,
        )
    except Exception as e:
        st.error(f"Failed to load models: {e}")
        model = None

    # Memory settings
    st.subheader("Memory Settings")
    memory_enabled = st.checkbox(
        "Enable Conversation Memory",
        value=True,
        help="When enabled, the agent remembers previous questions and can answer follow-ups"
    )

    memory_size = st.slider(
        "Memory Size (Q&A pairs)",
        min_value=1,
        max_value=30,
        value=10,
        help="Number of question-answer pairs to remember",
        disabled=not memory_enabled,
    )

    # Logging settings
    st.subheader("Logging Settings")
    enable_logging = st.checkbox(
        "Enable Logging",
        value=False,
        help="Track agent performance, LLM token usage, and operations"
    )

    log_level = st.selectbox(
        "Log Level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        index=1,  # Default to INFO
        help="Logging detail level",
        disabled=not enable_logging,
    )

    # Logging destination
    log_destination = st.radio(
        "Log Destination",
        ["File", "Database"],
        index=0,
        help="Choose where to store logs: file-based or database",
        disabled=not enable_logging,
    )

    log_to_database = (log_destination == "Database" and enable_logging)
    log_file = None
    log_db_con = None
    log_db_type = None

    if enable_logging:
        if log_destination == "File":
            # Define log file path
            logs_dir = os.path.join(project_root, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            log_file = os.path.join(logs_dir, "sql_agent_streamlit.log")
            st.info(f"📝 Logging to file: `{log_file}`")

        else:  # Database logging
            log_db_type_display = st.selectbox(
                "Log Database",
                ["PostgreSQL", "DuckDB"],
                index=0 if db_type == "PostgreSQL" else 1,
                help="Choose database for storing logs (can be different from data database)"
            )
            log_db_type = "postgres" if log_db_type_display == "PostgreSQL" else "duckdb"

            # Initialize log database schema button
            if st.button("🔧 Initialize Log Schema", help="Create log table in selected database"):
                with st.spinner(f"Initializing {log_db_type_display} log schema..."):
                    try:
                        # Create connection for logging database
                        if log_db_type == "postgres":
                            log_db_con = ibis.postgres.connect(
                                user="postgres",
                                password="password",
                                host="postgres",
                                port=5432,
                                database="my_db",
                            )
                            init_postgres_log_schema(
                                con=log_db_con,
                                table_name="sql_agent_logs",
                                schema="public"
                            )
                            st.success(f"✅ PostgreSQL log schema initialized!")
                            st.info("Table: public.sql_agent_logs with 6 indexes")
                        else:
                            # Create persistent DuckDB for logs
                            logs_dir = os.path.join(project_root, "logs")
                            os.makedirs(logs_dir, exist_ok=True)
                            duckdb_log_path = os.path.join(logs_dir, "sql_agent_logs.duckdb")
                            log_db_con = ibis.duckdb.connect(duckdb_log_path)
                            init_duckdb_log_schema(
                                con=log_db_con,
                                table_name="sql_agent_logs"
                            )
                            st.success(f"✅ DuckDB log schema initialized!")
                            st.info(f"Database: {duckdb_log_path}")

                        # Verify table creation
                        stats = verify_log_table(log_db_con, "sql_agent_logs", log_db_type)
                        st.metric("Current log count", stats['row_count'])

                    except Exception as e:
                        st.error(f"Failed to initialize log schema: {e}")

            # Show current log statistics
            try:
                # Create connection to check stats
                if log_db_type == "postgres":
                    temp_log_con = ibis.postgres.connect(
                        user="postgres",
                        password="password",
                        host="postgres",
                        port=5432,
                        database="my_db",
                    )
                else:
                    logs_dir = os.path.join(project_root, "logs")
                    duckdb_log_path = os.path.join(logs_dir, "sql_agent_logs.duckdb")
                    if os.path.exists(duckdb_log_path):
                        temp_log_con = ibis.duckdb.connect(duckdb_log_path)
                    else:
                        temp_log_con = None

                if temp_log_con:
                    stats = verify_log_table(temp_log_con, "sql_agent_logs", log_db_type)
                    if stats['exists']:
                        st.success(f"📊 Log table exists: {stats['row_count']} logs")
                    else:
                        st.warning("⚠️ Log table not initialized. Click 'Initialize Log Schema' button above.")
            except Exception:
                st.warning("⚠️ Log table not found. Initialize schema first.")

            # Show agent logger diagnostics
            if "agent" in st.session_state and hasattr(st.session_state.agent, 'logger'):
                with st.expander("🔍 Logger Diagnostics", expanded=False):
                    agent = st.session_state.agent
                    if agent.logger:
                        python_logger = agent.logger.logger
                        st.code(f"""
Logger exists: True
Logger name: {python_logger.name}
Log level: {python_logger.level}
Number of handlers: {len(python_logger.handlers)}
Handler types: {[type(h).__name__ for h in python_logger.handlers]}
                        """)
                    else:
                        st.warning("Agent logger is None")

    # Query settings
    st.subheader("Query Settings")
    include_distinct_values = st.checkbox(
        "Include Distinct Character Values",
        value=True,
        help="When enabled, includes sample values from character columns in the prompt to help the LLM generate more accurate queries"
    )

    # SQL Safety & Validation
    st.subheader("SQL Safety & Validation")

    # Rows Count Display
    st.text("Rows Count")
    if "row_count" in st.session_state and st.session_state.row_count is not None:
        st.metric("Total Rows", f"{st.session_state.row_count:,}")
    else:
        st.metric("Total Rows", "N/A")

    # Read-Only checkbox
    read_only = st.checkbox(
        "Read-Only",
        value=True,
        help="When enabled, only SELECT queries are allowed. Prevents INSERT, UPDATE, DELETE operations."
    )

    # Enforce Limit checkbox
    enforce_limit = st.checkbox(
        "Enforce Limit",
        value=True,
        help="Automatically enforce a LIMIT clause on queries to prevent returning too many rows"
    )

    # Limit Size dropdown (conditional on Enforce Limit)
    max_result_limit = st.selectbox(
        "Limit Size",
        options=[10, 100, 1000, 10000],
        index=0,  # Default to 10
        help="Maximum number of rows to return from queries",
        disabled=not enforce_limit
    )

    st.divider()

    # Clear conversation button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        if "messages" in st.session_state:
            st.session_state.messages = []
        if "agent" in st.session_state and hasattr(st.session_state.agent, 'clear_memory'):
            st.session_state.agent.clear_memory()
        st.rerun()

    # Memory info
    if memory_enabled and "agent" in st.session_state:
        st.divider()
        st.subheader("Memory Status")
        try:
            info = st.session_state.agent.get_memory_info()
            st.metric("Current Pairs", f"{info['current_pairs']}/{info['memory_size_limit']}")
            if info['memory_full']:
                st.warning("⚠️ Memory full - oldest messages will be dropped")
        except:
            pass

    # About section
    st.divider()
    st.subheader("About")
    st.markdown("""
    This chatbot uses an AI agent to convert natural language questions
    into SQL queries and execute them against your database.

    **Features:**
    - 🧠 Conversation memory
    - 🔒 Configurable safety controls
    - ✅ SQL validation
    - 🔄 Auto-retry with fallback
    - 📊 Performance logging (file or database)
    - 🔤 Distinct value hints (optional)
    """)


# Main content area
st.title("🤖 SQL AI Agent Chatbot")
st.markdown("Ask questions about your data in natural language!")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "row_count" not in st.session_state:
    st.session_state.row_count = None

if "agent" not in st.session_state or "last_config" not in st.session_state or \
   st.session_state.get("last_config") != (db_type, provider, model, memory_enabled, memory_size,
                                          enable_logging, log_level, read_only, enforce_limit, max_result_limit,
                                          log_destination if enable_logging else None,
                                          log_db_type if log_to_database else None):
    # Initialize or reinitialize agent when config changes
    with st.spinner("Initializing connection and agent..."):
        con, tbl_name = init_database_connection(db_type)

        if con is not None and model is not None:
            # Get total row count from the table
            st.session_state.row_count = get_table_row_count(con, tbl_name)

            # Create log database connection if database logging is enabled
            if log_to_database:
                try:
                    if log_db_type == "postgres":
                        log_db_con = ibis.postgres.connect(
                            user="postgres",
                            password="password",
                            host="postgres",
                            port=5432,
                            database="my_db",
                        )
                    else:  # duckdb
                        logs_dir = os.path.join(project_root, "logs")
                        os.makedirs(logs_dir, exist_ok=True)
                        duckdb_log_path = os.path.join(logs_dir, "sql_agent_logs.duckdb")
                        log_db_con = ibis.duckdb.connect(duckdb_log_path)
                except Exception as e:
                    st.error(f"Failed to connect to log database: {e}")
                    log_db_con = None

            agent = init_agent(
                con, tbl_name, provider, model, memory_enabled, memory_size,
                enable_logging, log_level, log_file,
                read_only, enforce_limit, max_result_limit,
                log_to_database, log_db_con, log_db_type
            )

            if agent is not None:
                st.session_state.agent = agent
                st.session_state.last_config = (db_type, provider, model, memory_enabled, memory_size,
                                               enable_logging, log_level, read_only, enforce_limit, max_result_limit,
                                               log_destination if enable_logging else None,
                                               log_db_type if log_to_database else None)
                st.session_state.log_file = log_file
                st.session_state.log_to_database = log_to_database
                st.session_state.log_db_con = log_db_con if log_to_database else None
                st.session_state.log_db_type = log_db_type if log_to_database else None

                # Check if this is the first initialization
                if "first_init_done" not in st.session_state:
                    st.session_state.first_init_done = True
                    st.success("✅ Agent initialized successfully!")
                    st.rerun()  # Rerun to update the sidebar with row count
                else:
                    st.success("✅ Agent initialized successfully!")
            else:
                st.error("Failed to initialize agent. Please check your configuration.")
                st.stop()
        else:
            st.error("Failed to initialize. Please check your configuration.")
            st.stop()

# Ensure row count is set if agent exists but row_count is None
if "agent" in st.session_state and (st.session_state.row_count is None or "row_count" not in st.session_state):
    if hasattr(st.session_state.agent, 'con') and hasattr(st.session_state.agent, 'tbl_name'):
        st.session_state.row_count = get_table_row_count(
            st.session_state.agent.con,
            st.session_state.agent.tbl_name
        )

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display query result if available
        if "result" in message and message["result"] is not None:
            display_query_result(message["result"])

# Log viewer (if logging is enabled)
if enable_logging:
    with st.expander("📊 View Agent Logs", expanded=False):
        if log_destination == "File" and log_file and os.path.exists(log_file):
            # File-based log viewer
            col1, col2 = st.columns([3, 1])

            with col1:
                max_log_lines = st.slider(
                    "Number of log entries to display",
                    min_value=10,
                    max_value=200,
                    value=50,
                    step=10
                )

            with col2:
                show_full_logs = st.checkbox("Show full details", value=False)
                if st.button("🔄 Refresh Logs"):
                    st.rerun()

            # Read and display logs
            log_entries = read_log_file(log_file, max_lines=max_log_lines)

            if log_entries:
                st.markdown(f"**Showing {len(log_entries)} most recent log entries:**")

                # Display logs
                for entry in log_entries:
                    st.markdown(format_log_entry(entry, show_full=show_full_logs), unsafe_allow_html=True)
            else:
                st.info("No log entries yet. Start asking questions to see logs appear here.")

            # Download logs button
            if log_entries:
                st.divider()
                log_content = "\n".join([json.dumps(entry) if isinstance(entry, dict) else str(entry)
                                        for entry in log_entries])
                st.download_button(
                    label="📥 Download Logs",
                    data=log_content,
                    file_name=f"sql_agent_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

        elif log_destination == "Database" and st.session_state.get('log_db_con'):
            # Database-based log viewer
            col1, col2 = st.columns([3, 1])

            with col1:
                max_log_entries = st.slider(
                    "Number of log entries to display",
                    min_value=10,
                    max_value=200,
                    value=50,
                    step=10
                )

            with col2:
                if st.button("🔄 Refresh Logs"):
                    st.rerun()

            # Query logs from database
            try:
                log_db_con = st.session_state.log_db_con
                log_db_type = st.session_state.log_db_type

                # First, check total count
                count_query = "SELECT COUNT(*) as count FROM sql_agent_logs;"

                if log_db_type == "postgres":
                    count_result = log_db_con.sql(count_query).to_pandas()
                else:
                    count_result = log_db_con.con.execute(count_query).df()

                total_count = count_result.iloc[0, 0]
                st.info(f"🔍 Total logs in database: {total_count}")

                # Query recent logs
                query = f"""
                SELECT
                    timestamp,
                    level,
                    logger,
                    message,
                    session_id,
                    operation_type
                FROM sql_agent_logs
                ORDER BY timestamp DESC
                LIMIT {max_log_entries};
                """

                if log_db_type == "postgres":
                    # Use ibis sql() method which returns a table expression
                    logs_df = log_db_con.sql(query).to_pandas()
                else:  # duckdb
                    logs_df = log_db_con.con.execute(query).df()

                if not logs_df.empty:
                    st.markdown(f"**Showing {len(logs_df)} most recent log entries:**")

                    # Format and display logs
                    for _, row in logs_df.iterrows():
                        level = row['level']
                        message = row['message']
                        timestamp = row['timestamp']
                        operation_type = row.get('operation_type', '')

                        level_class = f"log-{level.lower()}"
                        formatted = f'<div class="log-entry {level_class}">'
                        formatted += f'<strong>[{level}]</strong> {timestamp} | {message}'
                        if operation_type:
                            formatted += f' <small>({operation_type})</small>'
                        formatted += '</div>'
                        st.markdown(formatted, unsafe_allow_html=True)

                    # Download logs button
                    st.divider()
                    csv_data = logs_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Logs (CSV)",
                        data=csv_data,
                        file_name=f"sql_agent_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                    # Show log statistics
                    st.divider()
                    st.subheader("Log Statistics")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Logs", len(logs_df))

                    with col2:
                        # Count by level
                        level_counts = logs_df['level'].value_counts()
                        error_count = level_counts.get('ERROR', 0)
                        st.metric("Errors", error_count)

                    with col3:
                        # Count by operation type
                        if 'operation_type' in logs_df.columns:
                            op_counts = logs_df['operation_type'].value_counts()
                            st.metric("Operations", len(op_counts))

                else:
                    st.info("No log entries yet. Start asking questions to see logs appear here.")

            except Exception as e:
                st.error(f"Failed to read logs from database: {e}")
                st.info("Make sure the log schema is initialized.")

        else:
            st.info("No logs available. Check your logging configuration.")


# Chat input
if prompt := st.chat_input("Ask a question about your data..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = st.session_state.agent.ask_question(
                    question=prompt,
                    verbose=False,
                    distinct_char_values=include_distinct_values,
                )

                if result.success:
                    # Check if this is a write operation
                    is_write_operation = (
                        result.data is not None
                        and not result.data.empty
                        and 'query_type' in result.data.columns
                        and result.data['query_type'].iloc[0] == 'write_operation'
                    )

                    if is_write_operation:
                        response = "I've executed your write operation successfully:"
                    else:
                        response = "I've executed your query. Here are the results:"
                else:
                    response = "I encountered an issue with your query:"

                st.markdown(response)
                display_query_result(result)

                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "result": result,
                })

            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "result": None,
                })

    # Always update row count after query execution (success or failure)
    if "agent" in st.session_state and hasattr(st.session_state.agent, 'con') and hasattr(st.session_state.agent, 'tbl_name'):
        try:
            new_row_count = get_table_row_count(
                st.session_state.agent.con,
                st.session_state.agent.tbl_name
            )
            # Only trigger rerun if row count changed
            if new_row_count != st.session_state.row_count:
                st.session_state.row_count = new_row_count
                st.rerun()  # Rerun to update the sidebar immediately
            else:
                st.session_state.row_count = new_row_count
        except Exception:
            pass  # Keep existing row count if update fails

# Display helpful suggestions if chat is empty
if len(st.session_state.messages) == 0:
    st.info("👋 Welcome! Try asking questions like:")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        - "How many rows are in the dataset?"
        - "Show me passenger counts by year"
        - "Which airline had the most passengers?"
        """)

    with col2:
        st.markdown("""
        - "What are the top 5 airports by traffic?"
        - "Show international flight statistics"
        - "Compare 2023 and 2024 passenger numbers"
        """)

    if memory_enabled:
        st.success("💡 **Memory is enabled** - I'll remember our conversation and can answer follow-up questions!")
    else:
        st.warning("⚠️ **Memory is disabled** - Each question will be independent.")

    if include_distinct_values:
        st.info("🔤 **Distinct values enabled** - Sample values from text columns will be included to improve query accuracy.")
