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
                df = pd.read_csv(os.path.join(project_root, "data/air_traffic.csv"))
                con.create_table("air_traffic", df, overwrite=True)
            except Exception as e:
                st.error(f"Failed to load sample data: {e}")
                return None, None
            return con, "air_traffic"
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None, None


def init_agent(con, tbl_name, provider, model, memory_enabled, memory_size,
               enable_logging=False, log_level="INFO", log_file=None):
    """Initialize SQL AI Agent."""
    try:
        config = load_config()

        # Get provider settings
        api_key = config.get_api_key(provider)
        base_url = config.get_base_url(provider)
        fallback_model = config.get_fallback_model(provider)

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
            read_only=True,  # Security: only allow SELECT queries
            enable_logging=enable_logging,
            log_level=log_level,
            log_file=log_file,
        )

        return agent
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
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

        # Show result data
        if result.data is not None and not result.data.empty:
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

    # Define log file path
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "sql_agent_streamlit.log") if enable_logging else None

    # Query settings
    st.subheader("Query Settings")
    include_distinct_values = st.checkbox(
        "Include Distinct Character Values",
        value=False,
        help="When enabled, includes sample values from character columns in the prompt to help the LLM generate more accurate queries"
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
    - 🔒 Read-only mode (safe)
    - ✅ SQL validation
    - 🔄 Auto-retry with fallback
    - 📊 Performance logging
    - 🔤 Distinct value hints (optional)
    """)

    # Logging info
    if enable_logging:
        st.info(f"📝 Logging to: `{log_file}`")


# Main content area
st.title("🤖 SQL AI Agent Chatbot")
st.markdown("Ask questions about your data in natural language!")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state or "last_config" not in st.session_state or \
   st.session_state.get("last_config") != (db_type, provider, model, memory_enabled, memory_size, enable_logging, log_level):
    # Initialize or reinitialize agent when config changes
    with st.spinner("Initializing connection and agent..."):
        con, tbl_name = init_database_connection(db_type)

        if con is not None and model is not None:
            agent = init_agent(
                con, tbl_name, provider, model, memory_enabled, memory_size,
                enable_logging, log_level, log_file
            )

            if agent is not None:
                st.session_state.agent = agent
                st.session_state.last_config = (db_type, provider, model, memory_enabled, memory_size, enable_logging, log_level)
                st.session_state.log_file = log_file
                st.success("✅ Agent initialized successfully!")
            else:
                st.error("Failed to initialize agent. Please check your configuration.")
                st.stop()
        else:
            st.error("Failed to initialize. Please check your configuration.")
            st.stop()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display query result if available
        if "result" in message and message["result"] is not None:
            display_query_result(message["result"])

# Log viewer (if logging is enabled)
if enable_logging and log_file and os.path.exists(log_file):
    with st.expander("📊 View Agent Logs", expanded=False):
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
