"""
Debug Tester Module

Tests the SQL AI Agent's ability to debug and fix syntactically incorrect queries
using the debug_prompt_template and retry mechanism.
"""

import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class DebugTestCase:
    """Represents a debug test case with a broken query."""

    id: int
    description: str
    bad_query: str
    error_type: str
    expected_fix: str  # Description of what needs to be fixed


@dataclass
class DebugTestResult:
    """Results from a single debug test."""

    test_id: int
    description: str
    bad_query: str
    error_type: str
    success: bool
    trials_needed: int
    max_trials: int
    execution_time: float
    final_query: Optional[str]
    final_error: Optional[str]


# Predefined debug test cases with syntax errors
DEBUG_TEST_CASES = [
    DebugTestCase(
        id=1,
        description="Missing quotes around column names with spaces",
        bad_query="""
        SELECT Operating Airline, SUM(Passenger Count) as total
        FROM air_traffic
        WHERE Year = 2024
        GROUP BY Operating Airline
        ORDER BY total DESC
        LIMIT 10
        """,
        error_type="syntax_error_quotes",
        expected_fix="Add double quotes around 'Operating Airline' and 'Passenger Count'",
    ),

    DebugTestCase(
        id=2,
        description="Wrong table name (missing underscore)",
        bad_query="""
        SELECT "Operating Airline", SUM("Passenger Count") as total
        FROM airtraffic
        WHERE "Year" = 2024
        GROUP BY "Operating Airline"
        LIMIT 10
        """,
        error_type="wrong_table_name",
        expected_fix="Change 'airtraffic' to 'air_traffic'",
    ),

    DebugTestCase(
        id=3,
        description="Missing GROUP BY for aggregation",
        bad_query="""
        SELECT "Terminal", SUM("Passenger Count") as total
        FROM air_traffic
        WHERE "Year" = 2024
        ORDER BY total DESC
        """,
        error_type="missing_group_by",
        expected_fix="Add GROUP BY Terminal clause",
    ),

    DebugTestCase(
        id=4,
        description="Wrong column name (misspelled)",
        bad_query="""
        SELECT "Operating Airline", SUM("Passanger Count") as total
        FROM air_traffic
        WHERE "Year" = 2024
        GROUP BY "Operating Airline"
        """,
        error_type="wrong_column_name",
        expected_fix="Fix typo: 'Passanger' → 'Passenger'",
    ),

    DebugTestCase(
        id=5,
        description="Invalid date comparison syntax",
        bad_query="""
        SELECT SUM("Passenger Count") as total
        FROM air_traffic
        WHERE "Date" = '2024-01'
        """,
        error_type="date_format_error",
        expected_fix="Use proper date comparison or LIKE operator",
    ),
]


class DebugTester:
    """
    Tests the debug/retry mechanism of SQL AI Agent.

    Simulates the agent receiving broken queries and attempts to fix them
    using the debug_chain similar to how ask_question handles failures.
    """

    def __init__(self, agent):
        """
        Initialize DebugTester with an SQL AI Agent instance.

        Args:
            agent: SqlAgent instance to test
        """
        self.agent = agent

    def run_single_debug_test(
        self,
        bad_query: str,
        question: str,
        max_trials: int = 3
    ) -> Tuple[bool, int, float, Optional[str], Optional[str]]:
        """
        Test if the agent can debug and fix a broken query.

        Simulates the debug retry mechanism from SqlAgent.ask_question().

        Args:
            bad_query: SQL query with syntax error
            question: Original user question (for context)
            max_trials: Maximum number of debug attempts

        Returns:
            Tuple of (success, trials_needed, execution_time, final_query, final_error)
        """
        from sql_ai_agent.SqlAgent import debug_agent, query_processing, DebugAttempt

        start_time = time.time()
        debug_memory: List[DebugAttempt] = []
        current_query = bad_query
        current_error = None

        # Try to execute the bad query to get the error
        try:
            from sql_ai_agent.db_handler import query_execute
            result = query_execute(con=self.agent.con, query=current_query)
            # If it succeeds, the query wasn't actually broken
            execution_time = time.time() - start_time
            return True, 0, execution_time, current_query, None
        except Exception as e:
            current_error = str(e)

        # Now attempt to debug
        for trial in range(1, max_trials + 1):
            debug_memory.append(DebugAttempt(query=current_query, error=current_error))

            # Use the debug chain to get a fixed query
            llm_debug_output = debug_agent(
                chain=self.agent.debug_chain,
                question=question,
                tbl_name=self.agent.tbl_name,
                db_type=self.agent.db_type,
                schema=self.agent.schema,
                query=current_query,
                error_msg=current_error,
                debug_memory=debug_memory,
            )

            # Process the debug output
            query_result = query_processing(
                llm_output=llm_debug_output,
                con=self.agent.con,
                validator=self.agent.validator,
                verbose=False,
                logger=None,
                prompt=None,
            )

            if query_result.success:
                execution_time = time.time() - start_time
                return True, trial, execution_time, query_result.query, None
            else:
                current_query = query_result.query
                current_error = query_result.error

        # Failed after all trials
        execution_time = time.time() - start_time
        return False, max_trials, execution_time, current_query, current_error

    def run_debug_tests(
        self,
        test_cases: Optional[List[DebugTestCase]] = None,
        max_trials: int = 3
    ) -> List[DebugTestResult]:
        """
        Run multiple debug test cases.

        Args:
            test_cases: List of DebugTestCase objects (uses defaults if None)
            max_trials: Maximum retry attempts per test

        Returns:
            List of DebugTestResult objects
        """
        if test_cases is None:
            test_cases = DEBUG_TEST_CASES

        results = []

        for test_case in test_cases:
            # Create a generic question for context
            question = "Show data from the air_traffic table"

            success, trials, exec_time, final_query, final_error = self.run_single_debug_test(
                bad_query=test_case.bad_query,
                question=question,
                max_trials=max_trials
            )

            result = DebugTestResult(
                test_id=test_case.id,
                description=test_case.description,
                bad_query=test_case.bad_query.strip(),
                error_type=test_case.error_type,
                success=success,
                trials_needed=trials,
                max_trials=max_trials,
                execution_time=exec_time,
                final_query=final_query,
                final_error=final_error,
            )

            results.append(result)

        return results

    def get_debug_summary(self, results: List[DebugTestResult]) -> dict:
        """
        Generate summary statistics from debug test results.

        Args:
            results: List of DebugTestResult objects

        Returns:
            Dictionary with summary metrics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        success_rate = (successful / total * 100) if total > 0 else 0

        trials_list = [r.trials_needed for r in results if r.success]
        avg_trials = sum(trials_list) / len(trials_list) if trials_list else 0

        avg_time = sum(r.execution_time for r in results) / total if total > 0 else 0

        return {
            'total_tests': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'avg_trials_to_fix': avg_trials,
            'avg_execution_time': avg_time,
        }


def get_debug_test_cases() -> List[DebugTestCase]:
    """Get all predefined debug test cases."""
    return DEBUG_TEST_CASES
