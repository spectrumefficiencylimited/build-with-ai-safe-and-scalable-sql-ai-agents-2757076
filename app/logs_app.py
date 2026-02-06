"""
SQL AI Agent Logs Observability Dashboard

A dedicated Streamlit app for monitoring and analyzing SQL AI Agent performance.
Provides insights into query success rates, execution times, token usage, and model performance.
"""

import streamlit as st
import sys
import os
import pandas as pd
import json
import ibis
import duckdb
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.log_database import verify_log_table
from sql_ai_agent.SqlAgent import SqlAgent
from sql_ai_agent.llm_config_loader import load_config

# Page configuration
st.set_page_config(
    page_title="SQL AI Agent - Logs Observability",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-metric {
        border-left-color: #4caf50;
    }
    .error-metric {
        border-left-color: #f44336;
    }
    .warning-metric {
        border-left-color: #ff9800;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_postgres_connection():
    """Initialize PostgreSQL connection for logs."""
    try:
        con = ibis.postgres.connect(
            user="postgres",
            password="password",
            host="postgres",
            port=5432,
            database="my_db",
        )
        return con
    except Exception as e:
        st.error(f"Failed to connect to PostgreSQL: {e}")
        return None


def read_json_logs(file_path, days_back=7):
    """Read logs from JSON file and filter by date."""
    if not os.path.exists(file_path):
        st.error(f"Log file not found: {file_path}")
        return pd.DataFrame()

    try:
        logs = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    log_entry = json.loads(line)

                    # Parse timestamp
                    timestamp_str = log_entry.get('timestamp', '')
                    if timestamp_str:
                        # Handle different timestamp formats
                        try:
                            timestamp = pd.to_datetime(timestamp_str)
                        except:
                            timestamp = datetime.now()
                    else:
                        timestamp = datetime.now()

                    # Filter by date
                    if timestamp >= cutoff_date:
                        # Flatten extra fields if present
                        extra = log_entry.get('extra', {})

                        log_data = {
                            'timestamp': timestamp,
                            'level': log_entry.get('level', 'INFO'),
                            'logger': log_entry.get('logger', 'unknown'),
                            'message': log_entry.get('message', ''),
                            'session_id': log_entry.get('session_id', ''),
                            'operation_type': log_entry.get('operation_type', ''),
                            'prompt_tokens': extra.get('prompt_tokens', 0),
                            'completion_tokens': extra.get('completion_tokens', 0),
                            'total_tokens': extra.get('total_tokens', 0),
                            'duration_ms': extra.get('duration_ms', 0),
                            'model_name': extra.get('model_name', ''),
                            'success': extra.get('success', None),
                            'error': log_entry.get('exception', ''),
                        }
                        logs.append(log_data)

                except json.JSONDecodeError:
                    continue

        return pd.DataFrame(logs)

    except Exception as e:
        st.error(f"Error reading JSON log file: {e}")
        return pd.DataFrame()


def read_postgres_logs(con, days_back=7):
    """Read logs from PostgreSQL database."""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d %H:%M:%S')

        query = f"""
        SELECT
            timestamp,
            level,
            logger,
            message,
            session_id,
            operation_type,
            extra_fields::text as extra_fields,
            exception
        FROM sql_agent_logs
        WHERE timestamp >= '{cutoff_date}'::timestamptz
        ORDER BY timestamp DESC;
        """

        logs_df = con.sql(query).to_pandas()

        if not logs_df.empty:
            # Helper function to safely parse extra_fields
            def parse_extra_field(extra_fields, field_name, default=0):
                if pd.isna(extra_fields):
                    return default

                # If it's a string, try to parse as JSON
                if isinstance(extra_fields, str):
                    try:
                        data = json.loads(extra_fields)
                        return data.get(field_name, default)
                    except (json.JSONDecodeError, AttributeError):
                        return default
                # If it's already a dict
                elif isinstance(extra_fields, dict):
                    return extra_fields.get(field_name, default)
                else:
                    return default

            # Parse extra_fields JSON column
            logs_df['prompt_tokens'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'prompt_tokens', 0)
            )
            logs_df['completion_tokens'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'completion_tokens', 0)
            )
            logs_df['total_tokens'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'total_tokens', 0)
            )
            logs_df['duration_ms'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'duration_ms', 0)
            )
            logs_df['model_name'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'model_name', '')
            )
            logs_df['success'] = logs_df['extra_fields'].apply(
                lambda x: parse_extra_field(x, 'success', None)
            )
            logs_df['error'] = logs_df['exception'].fillna('')

            # Ensure timestamp is datetime
            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])

        return logs_df

    except Exception as e:
        st.error(f"Error reading PostgreSQL logs: {e}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()


def calculate_metrics(logs_df):
    """Calculate key performance metrics from logs."""
    if logs_df.empty:
        return {}

    # Query results only
    query_logs = logs_df[logs_df['operation_type'] == 'query_result'].copy()

    # LLM invocations only
    llm_logs = logs_df[logs_df['operation_type'] == 'llm_invocation'].copy()

    metrics = {
        'total_queries': len(query_logs),
        'successful_queries': len(query_logs[query_logs['success'] == True]) if 'success' in query_logs.columns else 0,
        'failed_queries': len(query_logs[query_logs['success'] == False]) if 'success' in query_logs.columns else 0,
        'total_errors': len(logs_df[logs_df['level'] == 'ERROR']),
        'total_warnings': len(logs_df[logs_df['level'] == 'WARNING']),
        'total_llm_calls': len(llm_logs),
        'total_tokens': int(llm_logs['total_tokens'].sum()) if not llm_logs.empty else 0,
        'avg_tokens_per_call': float(llm_logs['total_tokens'].mean()) if not llm_logs.empty else 0,
        'avg_query_time': float(query_logs['duration_ms'].mean()) if not query_logs.empty else 0,
        'unique_sessions': logs_df['session_id'].nunique(),
        'unique_models': logs_df['model_name'].nunique() if 'model_name' in logs_df.columns else 0,
    }

    # Calculate success rate
    if metrics['total_queries'] > 0:
        metrics['success_rate'] = (metrics['successful_queries'] / metrics['total_queries']) * 100
    else:
        metrics['success_rate'] = 0.0

    return metrics


def display_metrics_cards(metrics):
    """Display key metrics in card format."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Total Queries",
            value=f"{metrics.get('total_queries', 0):,}",
            delta=None
        )
        st.metric(
            label="✅ Success Rate",
            value=f"{metrics.get('success_rate', 0):.1f}%",
            delta=None
        )

    with col2:
        st.metric(
            label="🤖 LLM Calls",
            value=f"{metrics.get('total_llm_calls', 0):,}",
            delta=None
        )
        st.metric(
            label="🔢 Total Tokens",
            value=f"{metrics.get('total_tokens', 0):,}",
            delta=None
        )

    with col3:
        st.metric(
            label="⚡ Avg Query Time",
            value=f"{metrics.get('avg_query_time', 0):.0f} ms",
            delta=None
        )
        st.metric(
            label="📝 Avg Tokens/Call",
            value=f"{metrics.get('avg_tokens_per_call', 0):.0f}",
            delta=None
        )

    with col4:
        st.metric(
            label="❌ Failed Queries",
            value=f"{metrics.get('failed_queries', 0):,}",
            delta=None
        )
        st.metric(
            label="🔧 Unique Sessions",
            value=f"{metrics.get('unique_sessions', 0):,}",
            delta=None
        )


def plot_success_failure_chart(logs_df):
    """Create bar chart for success/failure rates."""
    query_logs = logs_df[logs_df['operation_type'] == 'query_result'].copy()

    if query_logs.empty or 'success' not in query_logs.columns:
        st.info("No query result data available for success/failure analysis.")
        return

    # Count successes and failures
    success_counts = query_logs['success'].value_counts()

    fig = go.Figure(data=[
        go.Bar(
            x=['Successful', 'Failed'],
            y=[
                success_counts.get(True, 0),
                success_counts.get(False, 0)
            ],
            marker_color=['#4caf50', '#f44336'],
            text=[
                success_counts.get(True, 0),
                success_counts.get(False, 0)
            ],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Query Success vs Failure',
        xaxis_title='Status',
        yaxis_title='Count',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_token_usage_over_time(logs_df):
    """Create time series chart for token usage."""
    llm_logs = logs_df[logs_df['operation_type'] == 'llm_invocation'].copy()

    if llm_logs.empty:
        st.info("No LLM invocation data available for token usage analysis.")
        return

    # Group by day
    llm_logs['date'] = pd.to_datetime(llm_logs['timestamp']).dt.date
    daily_tokens = llm_logs.groupby('date')['total_tokens'].sum().reset_index()

    fig = go.Figure(data=[
        go.Bar(
            x=daily_tokens['date'],
            y=daily_tokens['total_tokens'],
            marker_color='steelblue',
            text=daily_tokens['total_tokens'],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Token Usage Over Time',
        xaxis_title='Date',
        yaxis_title='Total Tokens',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_model_performance(logs_df):
    """Create bar chart comparing model performance."""
    llm_logs = logs_df[logs_df['operation_type'] == 'llm_invocation'].copy()

    if llm_logs.empty or 'model_name' not in llm_logs.columns:
        st.info("No model data available for performance analysis.")
        return

    # Filter out empty model names
    llm_logs = llm_logs[llm_logs['model_name'] != '']

    if llm_logs.empty:
        st.info("No model information found in logs.")
        return

    # Group by model
    model_stats = llm_logs.groupby('model_name').agg({
        'total_tokens': 'sum',
        'duration_ms': 'mean'
    }).reset_index()

    model_stats.columns = ['model', 'total_tokens', 'avg_duration_ms']

    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Token Usage by Model', 'Avg Response Time by Model')
    )

    # Token usage
    fig.add_trace(
        go.Bar(
            x=model_stats['model'],
            y=model_stats['total_tokens'],
            name='Tokens',
            marker_color='steelblue',
            text=model_stats['total_tokens'],
            textposition='auto',
        ),
        row=1, col=1
    )

    # Response time
    fig.add_trace(
        go.Bar(
            x=model_stats['model'],
            y=model_stats['avg_duration_ms'],
            name='Avg Time (ms)',
            marker_color='coral',
            text=model_stats['avg_duration_ms'].round(0),
            textposition='auto',
        ),
        row=1, col=2
    )

    fig.update_xaxes(title_text="Model", row=1, col=1)
    fig.update_xaxes(title_text="Model", row=1, col=2)
    fig.update_yaxes(title_text="Total Tokens", row=1, col=1)
    fig.update_yaxes(title_text="Avg Duration (ms)", row=1, col=2)

    fig.update_layout(
        height=400,
        showlegend=False,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_execution_time_distribution(logs_df):
    """Create histogram of query execution times."""
    query_logs = logs_df[logs_df['operation_type'] == 'query_result'].copy()

    if query_logs.empty or 'duration_ms' not in query_logs.columns:
        st.info("No query execution time data available.")
        return

    # Filter out zeros
    query_logs = query_logs[query_logs['duration_ms'] > 0]

    if query_logs.empty:
        st.info("No valid execution time data.")
        return

    fig = go.Figure(data=[
        go.Histogram(
            x=query_logs['duration_ms'],
            nbinsx=30,
            marker_color='seagreen',
        )
    ])

    fig.update_layout(
        title='Query Execution Time Distribution',
        xaxis_title='Duration (ms)',
        yaxis_title='Count',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_activity_over_time(logs_df):
    """Create time series chart showing activity over time."""
    if logs_df.empty:
        st.info("No activity data available.")
        return

    # Group by hour
    logs_df['hour'] = pd.to_datetime(logs_df['timestamp']).dt.floor('H')
    hourly_activity = logs_df.groupby('hour').size().reset_index(name='count')

    fig = go.Figure(data=[
        go.Scatter(
            x=hourly_activity['hour'],
            y=hourly_activity['count'],
            mode='lines+markers',
            marker_color='purple',
            line=dict(width=2),
        )
    ])

    fig.update_layout(
        title='Activity Over Time (Hourly)',
        xaxis_title='Time',
        yaxis_title='Number of Events',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


@st.cache_resource
def init_logs_agent(logs_df, _provider, _model):
    """Initialize SQL AI Agent for querying logs data."""
    try:
        # Create in-memory DuckDB connection
        import duckdb
        duckdb_con = duckdb.connect(':memory:')

        # Create table from DataFrame
        duckdb_con.execute("CREATE TABLE logs_data AS SELECT * FROM logs_df")

        # Wrap in Ibis connection
        ibis_con = ibis.duckdb.connect(':memory:')
        ibis_con.con = duckdb_con

        # Load config
        config = load_config()
        api_key = config.get_api_key(_provider)
        base_url = config.get_base_url(_provider)
        fallback_model = config.get_fallback_model(_provider)

        # Create agent
        agent = SqlAgent(
            api_key=api_key,
            base_url=base_url,
            model=_model,
            con=ibis_con,
            tbl_name="logs_data",
            fallback=False,
            fallback_model=fallback_model,
            memory=True,
            memory_size=10,
            read_only=True,
            enforce_limit=True,
            max_result_limit=1000,
            enable_logging=False,
        )

        return agent, ibis_con

    except Exception as e:
        st.error(f"Failed to initialize logs agent: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None, None


def display_query_result(result):
    """Display query result from the agent."""
    if result.success:
        if result.data is not None and not result.data.empty:
            st.dataframe(result.data, use_container_width=True)
        else:
            st.info("Query executed successfully but returned no data.")
    else:
        st.error(f"❌ {result.error}")


# Main App
def main():
    st.title("📊 SQL AI Agent - Logs Observability Dashboard")
    st.markdown("Monitor and analyze SQL AI Agent performance metrics")

    # Sidebar configuration
    st.sidebar.header("⚙️ Data Source Configuration")

    data_source = st.sidebar.radio(
        "Select Data Source",
        ["PostgreSQL", "JSON File"],
        help="Choose where to load logs from"
    )

    days_back = st.sidebar.slider(
        "Days to Load",
        min_value=1,
        max_value=30,
        value=7,
        help="Number of days of historical data to load"
    )

    # Auto-refresh settings
    st.sidebar.divider()
    st.sidebar.header("🔄 Refresh Settings")

    auto_refresh = st.sidebar.checkbox(
        "Enable Auto-Refresh",
        value=False,
        help="Automatically refresh data every N seconds"
    )

    if auto_refresh:
        refresh_interval = st.sidebar.slider(
            "Refresh Interval (seconds)",
            min_value=10,
            max_value=300,
            value=60,
            step=10
        )
        # Use experimental_rerun with timer
        import time
        time.sleep(refresh_interval)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

    # Load logs based on selected source
    st.sidebar.divider()
    logs_df = pd.DataFrame()

    if data_source == "PostgreSQL":
        st.sidebar.info("📊 Loading logs from PostgreSQL database...")

        # Initialize connection
        con = init_postgres_connection()

        if con is not None:
            # Verify table exists
            try:
                table_info = verify_log_table(con, "sql_agent_logs", "postgres")

                if table_info.get("exists", False):
                    st.sidebar.success("✅ Connected to PostgreSQL")

                    # Show table statistics
                    row_count = table_info.get("row_count", 0)
                    st.sidebar.info(f"📊 Total logs in database: {row_count:,}")

                    if row_count > 0:
                        earliest = table_info.get("earliest_log")
                        latest = table_info.get("latest_log")
                        if earliest and latest:
                            st.sidebar.info(f"📅 Date range: {earliest} to {latest}")

                    # Load filtered logs
                    logs_df = read_postgres_logs(con, days_back=days_back)

                    if logs_df.empty:
                        st.sidebar.warning(f"⚠️ No logs found in last {days_back} days")
                        cutoff = datetime.now() - timedelta(days=days_back)
                        st.sidebar.info(f"Searching since: {cutoff.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        st.sidebar.success(f"✅ Loaded {len(logs_df):,} log entries")
                else:
                    error_msg = table_info.get("error", "Table not found")
                    st.sidebar.error(f"❌ Log table not found: {error_msg}")
                    st.error("""
                    **PostgreSQL log table not found!**

                    The `sql_agent_logs` table does not exist in the database.
                    Please initialize it using one of these methods:

                    1. **Using the main agent app**: Open the agent app and click "Initialize Log Schema"
                    2. **Using Jupyter notebook**: Run the log initialization notebook

                    See `app/logs_app_README.md` for details.
                    """)
            except Exception as e:
                st.sidebar.error(f"❌ Error verifying table: {e}")
                st.error(f"Database error: {e}")
                import traceback
                with st.expander("🔍 Show Full Error Details"):
                    st.code(traceback.format_exc())

    else:  # JSON File
        json_file_path = st.sidebar.text_input(
            "JSON Log File Path",
            value="logs/sql_agent_streamlit.log",
            help="Path to the JSON log file"
        )

        if json_file_path:
            # Convert to absolute path if relative
            if not os.path.isabs(json_file_path):
                json_file_path = os.path.join(project_root, json_file_path)

            st.sidebar.info(f"📄 Loading logs from: {json_file_path}")
            logs_df = read_json_logs(json_file_path, days_back=days_back)

            if not logs_df.empty:
                st.sidebar.success(f"✅ Loaded {len(logs_df)} log entries")
            else:
                st.sidebar.warning("⚠️ No logs found or file is empty")

    # Display dashboard if logs are loaded
    if logs_df.empty:
        st.warning("⚠️ No log data available. Please check your data source configuration.")
        st.info("💡 Tip: Make sure the database/file exists and contains log entries within the selected time range.")
        return

    # Display data info
    st.sidebar.divider()
    st.sidebar.markdown(f"**📊 Data Summary**")
    st.sidebar.markdown(f"- Total Log Entries: **{len(logs_df):,}**")
    st.sidebar.markdown(f"- Date Range: **{days_back} days**")
    st.sidebar.markdown(f"- From: **{logs_df['timestamp'].min()}**")
    st.sidebar.markdown(f"- To: **{logs_df['timestamp'].max()}**")

    # Chat Agent Configuration
    st.sidebar.divider()
    st.sidebar.header("🤖 AI Chat Assistant")

    enable_chat = st.sidebar.checkbox(
        "Enable Chat Interface",
        value=False,
        help="Ask natural language questions about the logs data"
    )

    if enable_chat:
        # LLM Configuration
        config = load_config()

        # Get enabled providers
        enabled_providers = config.list_providers(enabled_only=True)

        # Provider display map
        provider_map = {
            "OpenAI": "openai",
            "Anthropic": "anthropic",
            "Google": "google",
            "Docker Model Runner": "docker_model_runner",
        }

        # Filter to only show enabled providers
        available_display = [name for name, key in provider_map.items() if key in enabled_providers]

        provider_display = st.sidebar.selectbox(
            "LLM Provider",
            options=available_display,
            help="Select the LLM provider for the chat agent"
        )
        provider = provider_map[provider_display]

        # Get available models for the provider
        available_models = config.get_model_names(provider)
        default_model = config.get_default_model(provider)

        # Find default model index
        default_index = 0
        if default_model in available_models:
            default_index = available_models.index(default_model)

        model = st.sidebar.selectbox(
            "Model",
            options=available_models,
            index=default_index,
            help="Select the LLM model"
        )

        # Initialize session state for chat
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        if "logs_agent" not in st.session_state or st.session_state.get("agent_provider") != provider or st.session_state.get("agent_model") != model:
            # Clear cache and reinitialize agent
            init_logs_agent.clear()
            agent, agent_con = init_logs_agent(logs_df, provider, model)
            if agent:
                st.session_state.logs_agent = agent
                st.session_state.agent_provider = provider
                st.session_state.agent_model = model
                st.sidebar.success("✅ Chat agent initialized")
            else:
                st.sidebar.error("❌ Failed to initialize chat agent")
                enable_chat = False

    # Main content tabs
    tab1, tab2 = st.tabs(["📊 Dashboard", "💬 Chat Assistant"]) if enable_chat else (st.container(), None)

    # Tab 1: Dashboard (or main container if chat disabled)
    with tab1:
        # Calculate and display metrics
        st.header("📈 Key Performance Metrics")
        metrics = calculate_metrics(logs_df)
        display_metrics_cards(metrics)

        # Visualizations
        st.divider()
        st.header("📊 Performance Analysis")

        # Row 1: Success/Failure and Token Usage
        col1, col2 = st.columns(2)

        with col1:
            plot_success_failure_chart(logs_df)

        with col2:
            plot_token_usage_over_time(logs_df)

        # Row 2: Model Performance
        st.divider()
        plot_model_performance(logs_df)

        # Row 3: Execution Time and Activity
        col3, col4 = st.columns(2)

        with col3:
            plot_execution_time_distribution(logs_df)

        with col4:
            plot_activity_over_time(logs_df)

        # Detailed Logs Table
        st.divider()
        st.header("📋 Detailed Logs")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            level_filter = st.multiselect(
                "Filter by Level",
                options=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                default=['INFO', 'WARNING', 'ERROR'],
                key="dashboard_level_filter"
            )

        with col2:
            operation_filter = st.multiselect(
                "Filter by Operation",
                options=logs_df['operation_type'].unique().tolist(),
                default=logs_df['operation_type'].unique().tolist(),
                key="dashboard_operation_filter"
            )

        with col3:
            max_rows = st.slider(
                "Max Rows to Display",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                key="dashboard_max_rows"
            )

        # Apply filters
        filtered_df = logs_df[
            (logs_df['level'].isin(level_filter)) &
            (logs_df['operation_type'].isin(operation_filter))
        ].head(max_rows)

        # Reset index for selection
        filtered_df_display = filtered_df.reset_index(drop=True)

        # Display table
        display_columns = [
            'timestamp', 'level', 'operation_type', 'message',
            'duration_ms', 'total_tokens', 'model_name', 'success'
        ]

        # Only show columns that exist
        display_columns = [col for col in display_columns if col in filtered_df_display.columns]

        # Interactive table with row selection
        st.markdown("**Click on a row to view detailed extra_fields information**")

        event = st.dataframe(
            filtered_df_display[display_columns],
            use_container_width=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row",
            key="logs_table"
        )

        # Display extra_fields for selected row
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_row = filtered_df_display.iloc[selected_idx]

            st.divider()
            st.subheader("📝 Detailed Log Information")

            # Display basic info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Timestamp", str(selected_row['timestamp'])[:19])
            with col2:
                st.metric("Level", selected_row['level'])
            with col3:
                st.metric("Operation", selected_row.get('operation_type', 'N/A'))
            with col4:
                st.metric("Success", str(selected_row.get('success', 'N/A')))

            # Display message
            st.markdown("**Message:**")
            st.info(selected_row.get('message', 'No message'))

            # Display extra_fields in formatted JSON
            st.markdown("**Extra Fields:**")

            # Get extra_fields from the original filtered_df (not filtered_df_display)
            # because we need access to all columns
            original_row = filtered_df.iloc[selected_idx]

            extra_fields_data = None

            # Check if extra_fields column exists
            if 'extra_fields' in original_row.index and pd.notna(original_row['extra_fields']):
                extra_fields_value = original_row['extra_fields']

                # Parse if it's a JSON string
                if isinstance(extra_fields_value, str):
                    try:
                        extra_fields_data = json.loads(extra_fields_value)
                    except json.JSONDecodeError:
                        st.warning("Could not parse extra_fields as JSON")
                        st.code(extra_fields_value)
                # If it's already a dict
                elif isinstance(extra_fields_value, dict):
                    extra_fields_data = extra_fields_value

            # Display as formatted JSON
            if extra_fields_data:
                st.json(extra_fields_data, expanded=True)
            else:
                st.info("No extra_fields available for this log entry")



        # Download button
        st.divider()
        csv_data = logs_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full Logs (CSV)",
            data=csv_data,
            file_name=f"sql_agent_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    # Tab 2: Chat Interface
    if enable_chat and tab2:
        with tab2:
            st.header("💬 Ask Questions About Your Logs")
            st.markdown("""
            Use natural language to query and analyze your logs data. Examples:
            - "Show me all ERROR level logs from the last hour"
            - "What are the top 5 models by token usage?"
            - "How many successful queries were there today?"
            - "Show queries that took longer than 5 seconds"
            """)

            # Display chat messages
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

                    # Display query result if available
                    if "result" in message and message["result"] is not None:
                        display_query_result(message["result"])

            # Chat input
            if prompt := st.chat_input("Ask a question about your logs..."):
                # Add user message to chat history
                st.session_state.chat_messages.append({"role": "user", "content": prompt})

                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing logs..."):
                        try:
                            result = st.session_state.logs_agent.ask_question(
                                question=prompt,
                                verbose=False,
                                distinct_char_values=True,
                            )

                            if result.success:
                                response = "Here are the results:"
                                st.markdown(response)
                                display_query_result(result)

                                # Add to chat history
                                st.session_state.chat_messages.append({
                                    "role": "assistant",
                                    "content": response,
                                    "result": result
                                })
                            else:
                                error_msg = f"❌ {result.error}"
                                st.error(error_msg)
                                st.session_state.chat_messages.append({
                                    "role": "assistant",
                                    "content": error_msg,
                                    "result": None
                                })

                        except Exception as e:
                            error_msg = f"❌ Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": error_msg,
                                "result": None
                            })

            # Clear chat button
            if st.session_state.chat_messages:
                if st.button("🗑️ Clear Chat History"):
                    st.session_state.chat_messages = []
                    st.rerun()


if __name__ == "__main__":
    main()

