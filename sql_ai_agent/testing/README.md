# SQL AI Agent Testing Framework

A comprehensive testing suite for evaluating SQL AI Agent performance across different LLM models.

## Features

- **20 Test Cases**: Covering various difficulty levels and SQL patterns
  - Simple queries (basic SELECT, filtering, aggregation)
  - Moderate queries (JOINs, grouping, time series)
  - Complex queries (growth analysis, percentages, CTEs)
  - Edge cases (domain-specific knowledge)

- **Debug Testing**: Evaluates model's ability to fix syntax errors
  - Tests retry/debug mechanism
  - Measures trials needed to fix errors
  - Covers common SQL mistakes

- **Multi-Model Support**: Test across different providers and models
  - OpenAI (GPT-4o, GPT-4o-mini, etc.)
  - Anthropic (Claude Sonnet, Haiku)
  - Google (Gemini models)
  - Custom models via llm_config.yaml

- **Comprehensive Metrics**:
  - Success rate (% correct queries)
  - Query execution time
  - Number of trials to fix errors
  - Row counts and validation results

- **CSV Reports**: Detailed results and summary statistics

## Installation

The testing framework is part of the `sql_ai_agent` package:

```bash
cd /path/to/sql-ai-agent
pip install -e .
```

## Quick Start

### 1. View Test Cases

```python
from sql_ai_agent.testing import get_test_cases, get_test_summary

# Get all test cases
all_tests = get_test_cases()

# Get test summary
summary = get_test_summary()
print(f"Total tests: {summary['total_tests']}")
print(f"By difficulty: {summary['by_difficulty']}")
```

### 2. Run Tests from Command Line

```bash
# Test with default OpenAI model
python -m sql_ai_agent.testing.framework

# Test specific providers
python -m sql_ai_agent.testing.framework --providers openai anthropic

# Test specific models
python -m sql_ai_agent.testing.framework --models openai:gpt-4o openai:gpt-4o-mini

# Run specific test cases
python -m sql_ai_agent.testing.framework --tests 1 2 3 5 10

# Customize output files
python -m sql_ai_agent.testing.framework --output my_results.csv --summary my_summary.csv

# Adjust debug trials
python -m sql_ai_agent.testing.framework --max-debug-trials 5
```

### 3. Run Tests Programmatically

```python
from sql_ai_agent.testing import TestRunner

# Initialize test runner
runner = TestRunner(
    db_host="postgres",
    db_port=5432,
    db_name="my_db",
    db_user="postgres",
    db_password="password"
)

# Run tests for multiple models
results_df = runner.run_all_tests(
    providers=['openai'],
    models={'openai': ['gpt-4o', 'gpt-4o-mini']},
    max_debug_trials=3
)

# Save results
results_df.to_csv('results.csv', index=False)

# Generate summary
summary_df = runner.generate_summary_report(results_df)
summary_df.to_csv('summary.csv', index=False)
print(summary_df)
```

### 4. Test Specific Components

#### Query Generation Only

```python
from sql_ai_agent.testing import TestRunner

runner = TestRunner()
agent = runner.create_agent('openai', 'gpt-4o')

# Run only query generation tests
query_results = runner.run_query_tests(
    agent=agent,
    provider='openai',
    model='gpt-4o',
    test_case_ids=[1, 2, 3]  # Test specific cases
)
```

#### Debug Mechanism Only

```python
from sql_ai_agent.testing import DebugTester, get_debug_test_cases

# Create agent
runner = TestRunner()
agent = runner.create_agent('openai', 'gpt-4o')

# Test debug capability
debug_tester = DebugTester(agent)
debug_results = debug_tester.run_debug_tests(max_trials=5)

# Get summary
summary = debug_tester.get_debug_summary(debug_results)
print(f"Success Rate: {summary['success_rate']:.2f}%")
print(f"Avg Trials to Fix: {summary['avg_trials_to_fix']:.2f}")
```

## Test Cases Overview

### Difficulty Distribution
- **Easy (5 tests)**: Basic SELECT, filtering, simple aggregation
- **Medium (7 tests)**: GROUP BY, date operations, comparisons
- **Hard (8 tests)**: YoY growth, percentages, complex joins

### Category Breakdown
- Basic queries (2)
- Aggregation (2)
- Filtering (2)
- Comparison (1)
- Ranking (2)
- Time series (2)
- Percentage/Growth (3)
- Market share (1)
- Complex filtering (1)
- Edge cases (3)

### Sample Test Cases

**Test 1 (Easy)**: "How many total rows are in the air_traffic table?"
- Tests: Basic COUNT query
- Expected: Single row with count

**Test 6 (Medium)**: "Compare domestic vs international passenger traffic for 2024"
- Tests: GROUP BY with filtering
- Expected: 2 rows (Domestic, International)

**Test 13 (Hard)**: "Calculate year-over-year growth percentage comparing 2023 to 2024"
- Tests: Multi-period aggregation, percentage calculation
- Expected: Growth percentage with proper formula

## Debug Test Cases

The framework includes 5 debug test cases with intentional errors:

1. **Missing quotes** around column names with spaces
2. **Wrong table name** (missing underscore)
3. **Missing GROUP BY** for aggregation
4. **Misspelled column** name
5. **Invalid date format** in comparison

Each debug test measures:
- Success rate (can the model fix the error?)
- Trials needed (how many attempts?)
- Execution time

## Output Format

### Detailed Results CSV

Columns:
- `test_type`: 'query_generation' or 'debug_mechanism'
- `provider`: LLM provider (e.g., 'openai')
- `model`: Model name (e.g., 'gpt-4o')
- `test_id`: Test case ID
- `question` or `description`: Test description
- `success`: Boolean indicating if test passed
- `execution_time`: Time in seconds
- `generated_query` or `final_query`: SQL query produced
- `error_message` or `final_error`: Error if failed
- `validation_message`: Validation result
- `timestamp`: When test was run

### Summary CSV

Columns:
- `provider`: LLM provider
- `model`: Model name
- `test_type`: Type of test
- `total_tests`: Number of tests run
- `successful`: Number passed
- `failed`: Number failed
- `success_rate`: Percentage passed
- `avg_execution_time`: Average time per test
- `avg_trials_to_fix`: (Debug only) Average attempts to fix

## Configuration

The testing framework uses `llm_config.yaml` for model configuration:

```yaml
providers:
  openai:
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    models:
      - name: gpt-4o
        default: true
      - name: gpt-4o-mini
      - name: gpt-3.5-turbo
```

## Advanced Usage

### Custom Validation Functions

```python
from sql_ai_agent.testing.test_cases import TestCase

def custom_validator(df):
    """Custom validation logic."""
    return df is not None and len(df) > 0 and 'total' in df.columns

custom_test = TestCase(
    id=100,
    question="Your custom question",
    category="custom",
    difficulty="medium",
    description="Custom test case",
    validation_fn=custom_validator
)
```

### Filtering Test Cases

```python
from sql_ai_agent.testing import get_test_cases

# Get only easy tests
easy_tests = get_test_cases(difficulty='easy')

# Get only aggregation tests
agg_tests = get_test_cases(category='aggregation')

# Get specific tests
specific_tests = get_test_cases(ids=[1, 5, 10, 15])
```

### Custom Debug Tests

```python
from sql_ai_agent.testing.debug_tester import DebugTestCase, DebugTester

# Create custom debug test
custom_debug = DebugTestCase(
    id=100,
    description="Your custom error scenario",
    bad_query="SELECT * FORM air_traffic",  # Typo: FORM instead of FROM
    error_type="typo",
    expected_fix="Fix FORM to FROM"
)

# Run custom test
debug_tester = DebugTester(agent)
success, trials, time, query, error = debug_tester.run_single_debug_test(
    bad_query=custom_debug.bad_query,
    question="Show all data",
    max_trials=3
)
```

## Troubleshooting

### Connection Issues

If you get database connection errors:

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection manually
psql -h postgres -U postgres -d my_db -c "SELECT 1"
```

### Import Errors

If you get import errors:

```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH=/path/to/project:$PYTHONPATH

# Or install in editable mode
pip install -e .
```

### API Key Issues

Ensure your API keys are set in environment variables:

```bash
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

## Best Practices

1. **Start Small**: Run a few test cases first to validate setup
   ```bash
   python -m sql_ai_agent.testing.framework --tests 1 2 3
   ```

2. **Compare Models**: Run same tests across multiple models
   ```bash
   python -m sql_ai_agent.testing.framework --models openai:gpt-4o openai:gpt-4o-mini
   ```

3. **Analyze Results**: Look at detailed CSV for failure patterns
   ```python
   import pandas as pd
   df = pd.read_csv('test_results.csv')

   # See which tests failed most
   failures = df[df['success'] == False]
   print(failures.groupby('test_id').size().sort_values(ascending=False))
   ```

4. **Track Over Time**: Save results with timestamps for comparison
   ```bash
   python -m sql_ai_agent.testing.framework --output results_$(date +%Y%m%d).csv
   ```

## Examples

See `examples/` directory for:
- `run_basic_tests.py`: Simple test execution
- `compare_models.py`: Multi-model comparison
- `analyze_results.ipynb`: Jupyter notebook for result analysis

## Contributing

To add new test cases:

1. Edit `sql_ai_agent/testing/test_cases.py`
2. Add your test to the `TEST_CASES` list
3. Include validation function if needed
4. Update test count in documentation

## License

Same as parent project.
