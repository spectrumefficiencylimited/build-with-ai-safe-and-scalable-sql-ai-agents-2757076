"""
Test Cases for SQL AI Agent

20 test questions covering various difficulty levels and query patterns
for the SFO air traffic passenger statistics database.

Test Categories:
- Simple queries (1-5): Basic SELECT, filtering, aggregation
- Moderate queries (6-12): JOINs, grouping, date operations
- Complex queries (13-17): Window functions, CTEs, complex aggregations
- Edge cases (18-20): Tricky scenarios requiring domain knowledge
"""

from dataclasses import dataclass
from typing import List, Optional, Callable
import pandas as pd


@dataclass
class TestCase:
    """Represents a single test case for the SQL AI Agent."""

    id: int
    question: str
    category: str
    difficulty: str
    description: str
    validation_fn: Optional[Callable[[pd.DataFrame], bool]] = None
    expected_columns: Optional[List[str]] = None
    min_rows: Optional[int] = None
    max_rows: Optional[int] = None


def validate_not_empty(df: pd.DataFrame) -> bool:
    """Validate that result is not empty."""
    return df is not None and not df.empty and len(df) > 0


def validate_single_row(df: pd.DataFrame) -> bool:
    """Validate that result has exactly one row."""
    return df is not None and len(df) == 1


def validate_has_total_column(df: pd.DataFrame) -> bool:
    """Validate that result has a total/count column."""
    if df is None or df.empty:
        return False
    # Check for common aggregate column names
    cols_lower = [c.lower() for c in df.columns]
    return any(name in cols_lower for name in ['total', 'count', 'sum', 'passenger_count'])


def validate_year_column(df: pd.DataFrame) -> bool:
    """Validate that result includes year information."""
    if df is None or df.empty:
        return False
    cols_lower = [c.lower() for c in df.columns]
    return 'year' in cols_lower


def validate_percentage_column(df: pd.DataFrame) -> bool:
    """Validate that result includes percentage calculations."""
    if df is None or df.empty:
        return False
    cols_lower = [c.lower() for c in df.columns]
    return any('percent' in c or 'growth' in c or 'rate' in c for c in cols_lower)


# Define all 20 test cases
TEST_CASES = [
    # ==================== Simple Queries (1-5) ====================
    TestCase(
        id=1,
        question="How many total rows are in the air_traffic table?",
        category="basic",
        difficulty="easy",
        description="Simple COUNT(*) query",
        validation_fn=validate_single_row,
        min_rows=1,
        max_rows=1,
    ),

    TestCase(
        id=2,
        question="What are the top 5 airlines by total passenger count in 2024?",
        category="aggregation",
        difficulty="easy",
        description="Simple GROUP BY with ORDER BY and LIMIT, requires excluding transit passengers",
        validation_fn=validate_has_total_column,
        min_rows=1,
        max_rows=5,
    ),

    TestCase(
        id=3,
        question="Show total passengers by terminal, excluding transit passengers",
        category="aggregation",
        difficulty="easy",
        description="GROUP BY with filtering on Activity Type Code",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=4,
        question="How many international passengers arrived at SFO in 2023?",
        category="filtering",
        difficulty="easy",
        description="Filter by GEO Summary, Activity Type Code, and Year",
        validation_fn=validate_single_row,
        min_rows=1,
        max_rows=1,
    ),

    TestCase(
        id=5,
        question="List all distinct operating airlines in the database",
        category="basic",
        difficulty="easy",
        description="Simple DISTINCT query",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    # ==================== Moderate Queries (6-12) ====================
    TestCase(
        id=6,
        question="Compare domestic vs international passenger traffic for 2024",
        category="comparison",
        difficulty="medium",
        description="GROUP BY GEO Summary with proper filtering",
        validation_fn=validate_has_total_column,
        min_rows=2,
        max_rows=2,
    ),

    TestCase(
        id=7,
        question="What are the top 3 low-fare carriers by passenger count in 2024?",
        category="aggregation",
        difficulty="medium",
        description="Filter by Price Category Code, GROUP BY, ORDER BY",
        validation_fn=validate_not_empty,
        min_rows=1,
        max_rows=3,
    ),

    TestCase(
        id=8,
        question="Show monthly passenger trends for United Airlines in 2024",
        category="time_series",
        difficulty="medium",
        description="Filter by airline, extract month from Date, GROUP BY month",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=9,
        question="Which terminal had the highest passenger traffic in January 2024?",
        category="ranking",
        difficulty="medium",
        description="Filter by date, GROUP BY Terminal, ORDER BY, LIMIT 1",
        validation_fn=validate_single_row,
        min_rows=1,
        max_rows=1,
    ),

    TestCase(
        id=10,
        question="What percentage of total passengers were on low-fare carriers in 2024?",
        category="percentage",
        difficulty="medium",
        description="Calculate percentage from aggregated totals",
        validation_fn=validate_percentage_column,
        min_rows=1,
    ),

    TestCase(
        id=11,
        question="Show passenger count by boarding area for Terminal 1 in 2024",
        category="filtering",
        difficulty="medium",
        description="Multiple filters with GROUP BY",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=12,
        question="Which GEO Region had the most international passengers in 2023?",
        category="ranking",
        difficulty="medium",
        description="Filter International, exclude US region, GROUP BY, ORDER BY",
        validation_fn=validate_single_row,
        min_rows=1,
        max_rows=1,
    ),

    # ==================== Complex Queries (13-17) ====================
    TestCase(
        id=13,
        question="Calculate year-over-year growth percentage for total passengers comparing 2023 to 2024",
        category="growth_analysis",
        difficulty="hard",
        description="Multi-period aggregation with percentage calculation",
        validation_fn=validate_percentage_column,
        min_rows=1,
    ),

    TestCase(
        id=14,
        question="Which 5 airlines had the highest year-over-year growth from 2023 to 2024?",
        category="growth_analysis",
        difficulty="hard",
        description="Per-airline YoY growth calculation with ranking",
        validation_fn=validate_not_empty,
        min_rows=1,
        max_rows=5,
    ),

    TestCase(
        id=15,
        question="Show quarterly passenger trends for 2024, broken down by domestic vs international",
        category="time_series",
        difficulty="hard",
        description="Quarter extraction, pivot by GEO Summary",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=16,
        question="What is the market share percentage of each airline in 2024?",
        category="market_share",
        difficulty="hard",
        description="Calculate each airline's percentage of total traffic",
        validation_fn=validate_percentage_column,
        min_rows=1,
    ),

    TestCase(
        id=17,
        question="Find airlines that operate in both terminals and have more than 100000 passengers in 2024",
        category="complex_filtering",
        difficulty="hard",
        description="Multi-condition filtering with HAVING clause",
        validation_fn=validate_not_empty,
        min_rows=0,  # May have zero results
    ),

    # ==================== Edge Cases (18-20) ====================
    TestCase(
        id=18,
        question="Show total enplaned passengers only (departures) for each month in 2024",
        category="edge_case",
        difficulty="medium",
        description="Tests understanding of Activity Type Code (Enplaned vs Deplaned)",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=19,
        question="Compare passenger counts using Operating Airline vs Published Airline to identify codeshare impact",
        category="edge_case",
        difficulty="hard",
        description="Tests understanding of codeshare double-counting",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),

    TestCase(
        id=20,
        question="What is the average passenger count per flight by terminal in 2024, excluding transit passengers?",
        category="edge_case",
        difficulty="hard",
        description="Requires proper understanding of what constitutes a 'flight' in this dataset",
        validation_fn=validate_not_empty,
        min_rows=1,
    ),
]


def get_test_cases(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    ids: Optional[List[int]] = None
) -> List[TestCase]:
    """
    Get test cases with optional filtering.

    Args:
        category: Filter by category (e.g., 'basic', 'aggregation', 'growth_analysis')
        difficulty: Filter by difficulty ('easy', 'medium', 'hard')
        ids: Filter by specific test case IDs

    Returns:
        List of TestCase objects matching the filters

    Examples:
        >>> # Get all test cases
        >>> all_tests = get_test_cases()

        >>> # Get only easy tests
        >>> easy_tests = get_test_cases(difficulty='easy')

        >>> # Get specific tests
        >>> tests = get_test_cases(ids=[1, 5, 10])
    """
    cases = TEST_CASES

    if category:
        cases = [c for c in cases if c.category == category]

    if difficulty:
        cases = [c for c in cases if c.difficulty == difficulty]

    if ids:
        cases = [c for c in cases if c.id in ids]

    return cases


def get_test_summary() -> dict:
    """
    Get summary statistics about the test suite.

    Returns:
        Dictionary with test suite statistics
    """
    total = len(TEST_CASES)
    by_difficulty = {}
    by_category = {}

    for test in TEST_CASES:
        # Count by difficulty
        if test.difficulty not in by_difficulty:
            by_difficulty[test.difficulty] = 0
        by_difficulty[test.difficulty] += 1

        # Count by category
        if test.category not in by_category:
            by_category[test.category] = 0
        by_category[test.category] += 1

    return {
        'total_tests': total,
        'by_difficulty': by_difficulty,
        'by_category': by_category,
        'categories': list(by_category.keys()),
        'difficulties': list(by_difficulty.keys()),
    }


if __name__ == "__main__":
    # Print test suite summary
    summary = get_test_summary()

    print("=" * 80)
    print("SQL AI Agent Test Suite Summary")
    print("=" * 80)
    print(f"\nTotal Test Cases: {summary['total_tests']}")

    print("\nBy Difficulty:")
    for diff, count in sorted(summary['by_difficulty'].items()):
        print(f"  {diff.capitalize()}: {count}")

    print("\nBy Category:")
    for cat, count in sorted(summary['by_category'].items()):
        print(f"  {cat}: {count}")

    print("\n" + "=" * 80)
    print("Test Cases Detail:")
    print("=" * 80)

    for test in TEST_CASES:
        print(f"\n[{test.id}] {test.difficulty.upper()} - {test.category}")
        print(f"Question: {test.question}")
        print(f"Description: {test.description}")
