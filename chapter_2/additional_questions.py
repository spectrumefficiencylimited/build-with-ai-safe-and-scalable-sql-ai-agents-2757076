"""
Additional Complex Questions - Ready to Use

Copy and paste these questions into your notebook for testing.
"""

# ===========================================================================
# QUESTION 1: Seasonal Low-Fare Analysis (Medium - 3/5)
# ===========================================================================
# Tests: Activity Type, Price Category, Date Handling, Column Quoting

question_1 = """
Compare low-fare carrier passenger volumes between summer months
(June, July, August) and winter months (December, January, February)
of 2024. Show the top 10 low-fare airlines and their total passengers
for each season.

Only include passengers who actually departed from or arrived at SFO,
not those just connecting through the airport.
"""

# ===========================================================================
# QUESTION 2: International Carrier Growth (Medium-High - 4/5)
# ===========================================================================
# Tests: Activity Type, Geographic, Codeshare, Year Comparison, Quoting

question_2 = """
Which international airlines showed the biggest growth from 2023 to 2024?
Show the top 10 airlines ranked by percentage increase in passenger volume.
For each airline, show their 2023 total, 2024 total, and growth percentage.

Make sure to exclude transit passengers and avoid double-counting from
codeshare agreements.
"""

# ===========================================================================
# QUESTION 3: Terminal and Airline Analysis (Medium - 3/5)
# ===========================================================================
# Tests: Activity Type, Codeshare, Grouping, Column Quoting

question_3 = """
For each SFO terminal in 2024, show which airline handles the most
passengers. Include the terminal name, airline name, and total passengers.
Only count passengers who are actually boarding or arriving at SFO,
not connecting passengers.
"""

# ===========================================================================
# QUESTION 4: Domestic vs International by Price (Medium-High - 4/5)
# ===========================================================================
# Tests: Activity, Geographic, Price, Codeshare, Percentages

question_4 = """
Break down 2024 passenger traffic by geography (Domestic vs International)
and price category (Low Fare vs Other). For each combination, show:
- Total passengers
- Top 3 airlines
- Percentage of overall traffic

Exclude connecting passengers and make sure not to double-count
codeshare flights.
"""

# ===========================================================================
# QUESTION 5: Regional Market Share Analysis (High - 5/5)
# ===========================================================================
# Tests: Activity, Geographic Regions, Price, Codeshare, Percentages, Complex Agg

question_5 = """
Analyze which international regions are dominated by low-fare carriers in 2024.
For each international region (Europe, Asia, etc.), calculate:
- Total passengers on low-fare carriers
- Total passengers on all carriers
- Low-fare market share percentage
- Top low-fare carrier in that region

Only include actual passengers (not connecting), and avoid counting the
same passengers multiple times from codeshare agreements.
"""

# ===========================================================================
# QUESTION 6: Monthly Trend Analysis (Medium - 3/5)
# ===========================================================================
# Tests: Activity Type, Geographic, Date Handling, Column Quoting

question_6 = """
Show the month-by-month trend of total passenger traffic for 2024.
For each month, show the total passengers and break it down by
domestic vs international.

Only include passengers who departed or arrived at SFO, not those
connecting through the airport.
"""

# ===========================================================================
# QUESTION 7: Codeshare Flight Analysis (High - 5/5)
# ===========================================================================
# Tests: Activity Type, Deep Codeshare Understanding, Distinct Counting, Conditionals

question_7 = """
For 2024, identify which airlines have the most codeshare partnerships.
For each operating airline, show:
- How many different published airlines market their flights
- Total passengers on codeshare flights (where operating ≠ published)
- Total passengers on non-codeshare flights
- Percentage that are codeshares

Only include actual passengers, not connecting passengers.
"""

# ===========================================================================
# USAGE EXAMPLE
# ===========================================================================

"""
# Pick a question to test
test_question = question_2  # Change this to test different questions

print("=" * 100)
print("TESTING COMPLEX QUESTION")
print("=" * 100)
print(test_question)
print("=" * 100)

# Test WITHOUT skill
print("\n🔴 WITHOUT SKILL:")
result_no_skill = agent_no_skill.ask_question(
    question=test_question,
    verbose=True
)

# Test WITH skill
print("\n\n🟢 WITH SKILL:")
result_with_skill = agent_with_skill.ask_question(
    question=test_question,
    verbose=True
)

# Compare
print("\n" + "=" * 100)
print("COMPARISON:")
print(f"Without skill - Success: {result_no_skill.success}")
print(f"With skill    - Success: {result_with_skill.success}")
if result_no_skill.success and result_with_skill.success:
    print(f"\nQuery length - Without: {len(result_no_skill.query)}, With: {len(result_with_skill.query)}")
print("=" * 100)
"""

# ===========================================================================
# QUICK REFERENCE
# ===========================================================================

questions_summary = {
    "question_1": {
        "name": "Seasonal Low-Fare Analysis",
        "difficulty": "Medium (3/5)",
        "concepts": ["Activity Type", "Price Category", "Date Handling", "Quoting"],
        "good_for": "Testing date extraction and price category filtering"
    },
    "question_2": {
        "name": "International Carrier Growth",
        "difficulty": "Medium-High (4/5)",
        "concepts": ["Activity Type", "Geographic", "Codeshare", "Year Comparison"],
        "good_for": "Testing growth calculations and year-over-year logic"
    },
    "question_3": {
        "name": "Terminal and Airline Analysis",
        "difficulty": "Medium (3/5)",
        "concepts": ["Activity Type", "Codeshare", "Grouping", "Quoting"],
        "good_for": "Testing grouping and top-N per group queries"
    },
    "question_4": {
        "name": "Geo + Price Breakdown",
        "difficulty": "Medium-High (4/5)",
        "concepts": ["Activity", "Geographic", "Price", "Codeshare", "Percentages"],
        "good_for": "Testing multi-dimensional analysis"
    },
    "question_5": {
        "name": "Regional Market Share",
        "difficulty": "High (5/5)",
        "concepts": ["All 6 core concepts"],
        "good_for": "Comprehensive skill testing with complex aggregations"
    },
    "question_6": {
        "name": "Monthly Trend Analysis",
        "difficulty": "Medium (3/5)",
        "concepts": ["Activity Type", "Geographic", "Date Handling"],
        "good_for": "Testing time series and trend analysis"
    },
    "question_7": {
        "name": "Codeshare Analysis",
        "difficulty": "High (5/5)",
        "concepts": ["Activity Type", "Deep Codeshare Logic", "Conditionals"],
        "good_for": "Testing advanced codeshare understanding"
    }
}

# Print available questions
if __name__ == "__main__":
    print("=" * 100)
    print("AVAILABLE COMPLEX QUESTIONS")
    print("=" * 100)

    for key, info in questions_summary.items():
        print(f"\n{key}: {info['name']}")
        print(f"  Difficulty: {info['difficulty']}")
        print(f"  Concepts: {', '.join(info['concepts'])}")
        print(f"  Good for: {info['good_for']}")

    print("\n" + "=" * 100)
    print("RECOMMENDED TESTING ORDER:")
    print("=" * 100)
    print("""
    Start Simple:
      1. question_6 (Monthly Trends)
      2. question_3 (Terminal Analysis)

    Add Complexity:
      3. question_1 (Seasonal Low-Fare)
      4. question_2 (International Growth)

    High Complexity:
      5. question_4 (Geo + Price Breakdown)
      6. question_5 (Regional Market Share)
      7. question_7 (Codeshare Analysis)
    """)
    print("=" * 100)
