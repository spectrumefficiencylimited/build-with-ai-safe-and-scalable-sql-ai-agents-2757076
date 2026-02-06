# SQL AI Agent - Logs Observability Dashboard

A dedicated Streamlit application for monitoring and analyzing SQL AI Agent performance through comprehensive logging analytics.

## Features

### 📊 Key Metrics
- **Total Queries**: Count of all queries executed
- **Success Rate**: Percentage of successful vs failed queries
- **LLM Calls**: Total number of LLM invocations
- **Token Usage**: Total and average tokens consumed
- **Query Performance**: Average execution times
- **Session Analytics**: Unique sessions tracked

### 📈 Visualizations
- **Success/Failure Bar Chart**: Visual breakdown of query outcomes
- **Token Usage Over Time**: Daily token consumption trends
- **Model Performance Comparison**: Token usage and response times by model
- **Execution Time Distribution**: Histogram of query execution times
- **Activity Timeline**: Hourly activity patterns

### 🔍 Features
- **Dual Data Sources**:
  - PostgreSQL database (production logs)
  - JSON file (local/development logs)
- **Time Range Filtering**: View last 1-30 days of data
- **Auto-Refresh**: Optional automatic data refresh (10-300 seconds)
- **Manual Refresh**: On-demand data reload
- **Interactive Filters**: Filter logs by level, operation type
- **CSV Export**: Download complete logs for offline analysis

## Usage

### Running the Dashboard

```bash
# From project root
streamlit run app/logs_app.py

# Or from app directory
cd app
streamlit run logs_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Data Source Configuration

#### Option 1: PostgreSQL (Recommended for Production)

1. Select "PostgreSQL" in the sidebar
2. Ensure the PostgreSQL database is running:
   ```bash
   docker ps | grep postgres
   ```
3. The app will connect to:
   - Host: `postgres`
   - Port: `5432`
   - Database: `my_db`
   - Table: `sql_agent_logs`

**Requirements:**
- PostgreSQL container must be running
- Log table must be initialized (see main agent app)
- Network access to the database

#### Option 2: JSON File (Development/Local)

1. Select "JSON File" in the sidebar
2. Enter the path to your JSON log file:
   - Default: `logs/sql_agent_streamlit.log`
   - Can use absolute or relative paths
3. The app will parse JSON-formatted log entries

**JSON Log Format:**
```json
{
  "timestamp": "2024-02-05T10:30:00",
  "level": "INFO",
  "logger": "sql_ai_agent",
  "message": "Query executed successfully",
  "session_id": "abc-123",
  "operation_type": "query_result",
  "extra": {
    "prompt_tokens": 150,
    "completion_tokens": 50,
    "total_tokens": 200,
    "duration_ms": 1250,
    "model_name": "gpt-4o",
    "success": true
  }
}
```

### Configuration Options

#### Time Range
- **Days to Load**: Select 1-30 days of historical data
- Default: 7 days
- Filters logs by timestamp

#### Auto-Refresh
- **Enable/Disable**: Toggle automatic refresh
- **Interval**: 10-300 seconds
- Useful for monitoring live systems

#### Log Filters
- **Level**: DEBUG, INFO, WARNING, ERROR
- **Operation Type**: query_result, llm_invocation, etc.
- **Max Rows**: Limit displayed logs (10-500)

## Metrics Explained

### Success Rate
Calculated as: `(Successful Queries / Total Queries) × 100`
- Based on logs with `operation_type = 'query_result'`
- Requires `success` field in extra_fields

### Token Usage
- **Total Tokens**: Sum of all LLM invocation tokens
- **Avg Tokens/Call**: Mean tokens per LLM call
- Sourced from `prompt_tokens`, `completion_tokens`, `total_tokens`

### Query Performance
- **Avg Query Time**: Mean execution time in milliseconds
- Based on `duration_ms` field in logs
- Excludes failed queries

### Model Performance
- Aggregates metrics by `model_name`
- Compares token usage and response times
- Useful for model selection and optimization

## Troubleshooting

### No Data Displayed

**PostgreSQL:**
```bash
# Check if table exists
docker exec -it postgres psql -U postgres -d my_db -c "SELECT COUNT(*) FROM sql_agent_logs;"

# Verify logs within date range
docker exec -it postgres psql -U postgres -d my_db -c "SELECT MAX(timestamp), MIN(timestamp) FROM sql_agent_logs;"
```

**JSON File:**
```bash
# Check if file exists
ls -lh logs/sql_agent_streamlit.log

# View recent entries
tail -n 20 logs/sql_agent_streamlit.log

# Verify JSON format
cat logs/sql_agent_streamlit.log | jq . | head -n 5
```

### Connection Errors

**PostgreSQL:**
- Ensure Docker container is running
- Check network connectivity
- Verify credentials (postgres/password)

**JSON File:**
- Check file path is correct
- Verify file permissions
- Ensure JSON is properly formatted

### Missing Metrics

Some metrics require specific log fields:
- **Token Usage**: Requires `operation_type = 'llm_invocation'` with token fields
- **Success Rate**: Requires `success` field in extra_fields
- **Model Performance**: Requires `model_name` field

If metrics show 0 or N/A, check that logs contain the required fields.

## Integration with Main Agent App

This dashboard is designed to work alongside the main agent app (`agent_app.py`):

1. **Main Agent App**: Generates logs during query execution
2. **Logs Dashboard**: Analyzes and visualizes those logs

### Workflow

```
┌─────────────────┐
│  User Queries   │
│  (agent_app.py) │
└────────┬────────┘
         │
         ▼
   ┌─────────────┐
   │   Logs DB   │
   │ (Postgres/  │
   │   JSON)     │
   └─────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Observability │
  │   Dashboard  │
  │ (logs_app.py)│
  └──────────────┘
```

### Best Practices

1. **Use PostgreSQL for Production**: More robust, queryable, indexed
2. **Use JSON for Development**: Easier to inspect, version control
3. **Monitor Success Rates**: Track query accuracy over time
4. **Watch Token Usage**: Optimize costs by monitoring consumption
5. **Review Failed Queries**: Identify common error patterns
6. **Compare Models**: Use performance metrics for model selection

## Data Export

### CSV Download
- Click "📥 Download Full Logs (CSV)" button
- Exports all logs (not just filtered view)
- Filename includes timestamp: `sql_agent_logs_YYYYMMDD_HHMMSS.csv`

### Use Cases
- Offline analysis in Excel/Pandas
- Long-term archival
- Sharing with team members
- Import into other analytics tools

## Performance Considerations

### Large Datasets
- Use shorter time ranges (1-7 days) for faster loading
- Enable filtering to reduce displayed rows
- Consider database indexing for PostgreSQL

### Auto-Refresh
- Disable when not actively monitoring
- Use longer intervals (60+ seconds) to reduce load
- Manual refresh is more efficient for ad-hoc analysis

## Future Enhancements

Potential additions:
- Cost estimation per model
- Alert thresholds for error rates
- Session-level drill-down
- Query pattern analysis
- Real-time streaming updates
- Custom date range picker
- User/session comparison
- Export to JSON/Parquet

## Support

For issues or questions:
- Check the main project README
- Review log file formats
- Verify database schema
- Check Streamlit documentation

## License

Same as parent project (MIT)
