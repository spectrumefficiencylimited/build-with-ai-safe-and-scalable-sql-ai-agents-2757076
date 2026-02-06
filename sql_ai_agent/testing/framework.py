"""
SQL AI Agent Testing Framework

Main testing orchestration module that:
1. Loads model configurations from llm_config.yaml
2. Runs query generation tests
3. Runs debug/retry tests
4. Generates CSV reports with metrics

Usage:
    python -m sql_ai_agent.testing.framework --models openai --output results.csv
"""

import argparse
import time
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import ibis

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.SqlAgent import SqlAgent
from sql_ai_agent.llm_config_loader import load_config
from sql_ai_agent.testing.test_cases import get_test_cases, get_test_summary
from sql_ai_agent.testing.debug_tester import DebugTester, get_debug_test_cases


class TestRunner:
    """
    Main test runner for SQL AI Agent evaluation.

    Tests multiple models across:
    - Query generation and execution
    - Debug/retry capabilities
    """

    def __init__(
        self,
        db_host: str = "postgres",
        db_port: int = 5432,
        db_name: str = "my_db",
        db_user: str = "postgres",
        db_password: str = "password",
        table_name: str = "air_traffic",
    ):
        """
        Initialize TestRunner with database connection parameters.

        Args:
            db_host: PostgreSQL host
            db_port: PostgreSQL port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            table_name: Name of the air_traffic table
        """
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.table_name = table_name

        # Initialize database connection
        self.con = ibis.postgres.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )

        # Load LLM configuration
        self.config = load_config()

    def create_agent(self, provider: str, model: str) -> SqlAgent:
        """
        Create an SQL AI Agent with specified provider and model.

        Args:
            provider: LLM provider (e.g., 'openai', 'anthropic')
            model: Model name

        Returns:
            Configured SqlAgent instance
        """
        api_key = self.config.get_api_key(provider)
        base_url = self.config.get_base_url(provider)
        fallback_model = self.config.get_fallback_model(provider)

        agent = SqlAgent(
            api_key=api_key,
            base_url=base_url,
            model=model,
            con=self.con,
            tbl_name=self.table_name,
            fallback=False,  # Disable fallback for testing
            fallback_model=fallback_model,
            memory=False,  # Disable memory for consistent testing
            memory_size=10,
            read_only=True,  # Keep read-only for safety
            enforce_limit=True,
            max_result_limit=10000,
            enable_logging=False,  # Disable logging for performance
        )

        return agent

    def run_query_tests(
        self,
        agent: SqlAgent,
        provider: str,
        model: str,
        test_case_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run query generation and execution tests.

        Args:
            agent: SqlAgent instance to test
            provider: LLM provider name
            model: Model name
            test_case_ids: Optional list of specific test IDs to run

        Returns:
            List of test result dictionaries
        """
        test_cases = get_test_cases(ids=test_case_ids)
        results = []

        print(f"\n{'=' * 80}")
        print(f"Testing {provider}/{model} - Query Generation ({len(test_cases)} tests)")
        print(f"{'=' * 80}\n")

        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] Test {test_case.id}: {test_case.question[:60]}...")

            start_time = time.time()

            try:
                # Execute the test
                result = agent.ask_question(
                    question=test_case.question,
                    verbose=False,
                    distinct_char_values=False,
                )

                execution_time = time.time() - start_time

                # Validate the result
                validation_passed = True
                validation_message = "Query executed successfully"

                if result.success:
                    # Run custom validation if provided
                    if test_case.validation_fn and result.data is not None:
                        try:
                            validation_passed = test_case.validation_fn(result.data)
                            if not validation_passed:
                                validation_message = "Custom validation failed"
                        except Exception as e:
                            validation_passed = False
                            validation_message = f"Validation error: {str(e)}"

                    # Check row count constraints
                    if result.data is not None:
                        row_count = len(result.data)

                        if test_case.min_rows is not None and row_count < test_case.min_rows:
                            validation_passed = False
                            validation_message = f"Too few rows: {row_count} < {test_case.min_rows}"

                        if test_case.max_rows is not None and row_count > test_case.max_rows:
                            validation_passed = False
                            validation_message = f"Too many rows: {row_count} > {test_case.max_rows}"
                    else:
                        validation_passed = False
                        validation_message = "No data returned"

                else:
                    validation_passed = False
                    validation_message = result.error or "Query execution failed"

                success = result.success and validation_passed

                result_dict = {
                    'test_type': 'query_generation',
                    'provider': provider,
                    'model': model,
                    'test_id': test_case.id,
                    'question': test_case.question,
                    'category': test_case.category,
                    'difficulty': test_case.difficulty,
                    'success': success,
                    'query_executed': result.success,
                    'validation_passed': validation_passed,
                    'validation_message': validation_message,
                    'execution_time': execution_time,
                    'generated_query': result.query if result.query else None,
                    'error_message': result.error if not result.success else None,
                    'rows_returned': len(result.data) if result.data is not None else 0,
                    'timestamp': datetime.now().isoformat(),
                }

                results.append(result_dict)

                status = "✓ PASS" if success else "✗ FAIL"
                print(f"   {status} ({execution_time:.2f}s) - {validation_message}")

            except Exception as e:
                execution_time = time.time() - start_time
                print(f"   ✗ ERROR ({execution_time:.2f}s) - {str(e)}")

                results.append({
                    'test_type': 'query_generation',
                    'provider': provider,
                    'model': model,
                    'test_id': test_case.id,
                    'question': test_case.question,
                    'category': test_case.category,
                    'difficulty': test_case.difficulty,
                    'success': False,
                    'query_executed': False,
                    'validation_passed': False,
                    'validation_message': f"Exception: {str(e)}",
                    'execution_time': execution_time,
                    'generated_query': None,
                    'error_message': str(e),
                    'rows_returned': 0,
                    'timestamp': datetime.now().isoformat(),
                })

        return results

    def run_debug_tests(
        self,
        agent: SqlAgent,
        provider: str,
        model: str,
        max_trials: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Run debug/retry mechanism tests.

        Args:
            agent: SqlAgent instance to test
            provider: LLM provider name
            model: Model name
            max_trials: Maximum number of retry attempts

        Returns:
            List of debug test result dictionaries
        """
        debug_tester = DebugTester(agent)
        debug_test_cases = get_debug_test_cases()

        print(f"\n{'=' * 80}")
        print(f"Testing {provider}/{model} - Debug Mechanism ({len(debug_test_cases)} tests)")
        print(f"{'=' * 80}\n")

        debug_results = debug_tester.run_debug_tests(
            test_cases=debug_test_cases,
            max_trials=max_trials
        )

        results = []

        for i, result in enumerate(debug_results, 1):
            print(f"[{i}/{len(debug_results)}] Debug Test {result.test_id}: {result.description}")

            status = "✓ FIXED" if result.success else "✗ FAILED"
            trials_info = f"in {result.trials_needed} trial(s)" if result.success else f"after {result.max_trials} trials"
            print(f"   {status} {trials_info} ({result.execution_time:.2f}s)")

            result_dict = {
                'test_type': 'debug_mechanism',
                'provider': provider,
                'model': model,
                'test_id': result.test_id,
                'description': result.description,
                'error_type': result.error_type,
                'success': result.success,
                'trials_needed': result.trials_needed,
                'max_trials': result.max_trials,
                'execution_time': result.execution_time,
                'bad_query': result.bad_query,
                'final_query': result.final_query,
                'final_error': result.final_error,
                'timestamp': datetime.now().isoformat(),
            }

            results.append(result_dict)

        return results

    def run_all_tests(
        self,
        providers: List[str],
        models: Optional[Dict[str, List[str]]] = None,
        test_case_ids: Optional[List[int]] = None,
        max_debug_trials: int = 3
    ) -> pd.DataFrame:
        """
        Run all tests for specified providers and models.

        Args:
            providers: List of provider names (e.g., ['openai', 'anthropic'])
            models: Dict mapping provider to list of models (uses defaults if None)
            test_case_ids: Optional list of specific test IDs to run
            max_debug_trials: Maximum debug retry attempts

        Returns:
            DataFrame with all test results
        """
        all_results = []

        for provider in providers:
            # Get models for this provider
            if models and provider in models:
                provider_models = models[provider]
            else:
                # Use default models from config
                provider_models = [self.config.get_default_model(provider)]

            for model in provider_models:
                print(f"\n{'#' * 80}")
                print(f"# Testing Provider: {provider.upper()} | Model: {model}")
                print(f"{'#' * 80}")

                try:
                    # Create agent for this model
                    agent = self.create_agent(provider, model)

                    # Run query generation tests
                    query_results = self.run_query_tests(
                        agent, provider, model, test_case_ids
                    )
                    all_results.extend(query_results)

                    # Run debug tests
                    debug_results = self.run_debug_tests(
                        agent, provider, model, max_debug_trials
                    )
                    all_results.extend(debug_results)

                except Exception as e:
                    print(f"\n✗ ERROR: Failed to test {provider}/{model}: {str(e)}")
                    import traceback
                    traceback.print_exc()

        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        return df

    def generate_summary_report(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate summary statistics from test results.

        Args:
            results_df: DataFrame with all test results

        Returns:
            DataFrame with summary metrics by provider/model
        """
        summary_data = []

        # Group by provider, model, and test_type
        for (provider, model, test_type), group in results_df.groupby(['provider', 'model', 'test_type']):
            total_tests = len(group)
            successful = group['success'].sum()
            failed = total_tests - successful
            success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
            avg_execution_time = group['execution_time'].mean()

            summary = {
                'provider': provider,
                'model': model,
                'test_type': test_type,
                'total_tests': total_tests,
                'successful': successful,
                'failed': failed,
                'success_rate': f"{success_rate:.2f}%",
                'avg_execution_time': f"{avg_execution_time:.3f}s",
            }

            # Add test-type specific metrics
            if test_type == 'debug_mechanism':
                fixed_queries = group[group['success'] == True]
                if len(fixed_queries) > 0:
                    avg_trials = fixed_queries['trials_needed'].mean()
                    summary['avg_trials_to_fix'] = f"{avg_trials:.2f}"

            summary_data.append(summary)

        summary_df = pd.DataFrame(summary_data)
        return summary_df


def main():
    """Main entry point for command-line testing."""
    parser = argparse.ArgumentParser(
        description='SQL AI Agent Testing Framework'
    )

    parser.add_argument(
        '--providers',
        nargs='+',
        default=['openai'],
        help='LLM providers to test (e.g., openai anthropic google)'
    )

    parser.add_argument(
        '--models',
        nargs='+',
        help='Specific models to test (format: provider:model, e.g., openai:gpt-4o)'
    )

    parser.add_argument(
        '--tests',
        nargs='+',
        type=int,
        help='Specific test case IDs to run (default: all)'
    )

    parser.add_argument(
        '--output',
        default='test_results.csv',
        help='Output CSV file path (default: test_results.csv)'
    )

    parser.add_argument(
        '--summary',
        default='test_summary.csv',
        help='Summary CSV file path (default: test_summary.csv)'
    )

    parser.add_argument(
        '--max-debug-trials',
        type=int,
        default=3,
        help='Maximum debug retry attempts (default: 3)'
    )

    parser.add_argument(
        '--db-host',
        default='postgres',
        help='PostgreSQL host (default: postgres)'
    )

    parser.add_argument(
        '--db-port',
        type=int,
        default=5432,
        help='PostgreSQL port (default: 5432)'
    )

    args = parser.parse_args()

    # Parse models if provided
    models_dict = {}
    if args.models:
        for model_spec in args.models:
            if ':' in model_spec:
                provider, model = model_spec.split(':', 1)
                if provider not in models_dict:
                    models_dict[provider] = []
                models_dict[provider].append(model)

    # Initialize test runner
    print("\nInitializing SQL AI Agent Test Framework...")
    print(f"Database: {args.db_host}:{args.db_port}")
    print(f"Providers: {', '.join(args.providers)}")

    runner = TestRunner(
        db_host=args.db_host,
        db_port=args.db_port,
    )

    # Run tests
    print("\nStarting tests...\n")

    results_df = runner.run_all_tests(
        providers=args.providers,
        models=models_dict if models_dict else None,
        test_case_ids=args.tests,
        max_debug_trials=args.max_debug_trials
    )

    # Save detailed results
    results_df.to_csv(args.output, index=False)
    print(f"\n{'=' * 80}")
    print(f"✓ Detailed results saved to: {args.output}")

    # Generate and save summary
    summary_df = runner.generate_summary_report(results_df)
    summary_df.to_csv(args.summary, index=False)
    print(f"✓ Summary report saved to: {args.summary}")

    # Print summary to console
    print(f"\n{'=' * 80}")
    print("Test Summary:")
    print(f"{'=' * 80}\n")
    print(summary_df.to_string(index=False))
    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    main()
