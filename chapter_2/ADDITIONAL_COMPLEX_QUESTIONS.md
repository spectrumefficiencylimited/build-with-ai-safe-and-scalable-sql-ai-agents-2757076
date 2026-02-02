# Additional Complex Questions for Skills Testing

This document provides additional complex questions to test the skills system from different angles.

---

## Question 1: Seasonal Low-Fare Analysis (Medium Complexity)

**Difficulty**: ★★★☆☆ (3/5)
**Concepts Tested**: 4

```python
question_1 = """
Compare low-fare carrier passenger volumes between summer months
(June, July, August) and winter months (December, January, February)
of 2024. Show the top 10 low-fare airlines and their total passengers
for each season.

Only include passengers who actually departed from or arrived at SFO,
not those just connecting through the airport.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Price Category Filtering - Low Fare only
3. ✓ Date Handling - Extract month from timestamp, group by season
4. ✓ Column Quoting - Handle spaces in names

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Filters `"Price Category Code" = 'Low Fare'`
- Extracts month from `Date` column (timestamp)
- Properly groups months into seasons
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers
- ❌ Doesn't know about Price Category Code
- ❌ Uses Year column instead of Date for month extraction
- ❌ Syntax errors from unquoted columns

---

## Question 2: International Carrier Growth (Medium-High Complexity)

**Difficulty**: ★★★★☆ (4/5)
**Concepts Tested**: 5

```python
question_2 = """
Which international airlines showed the biggest growth from 2023 to 2024?
Show the top 10 airlines ranked by percentage increase in passenger volume.
For each airline, show their 2023 total, 2024 total, and growth percentage.

Make sure to exclude transit passengers and avoid double-counting from
codeshare agreements.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Geographic Filtering - International only
3. ✓ Codeshare Awareness - Use Operating Airline
4. ✓ Year Comparison - Calculate growth rates
5. ✓ Column Quoting - Handle spaces

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Filters `"GEO Summary" = 'International'`
- Uses `"Operating Airline"` to avoid codeshare double-counting
- Compares Year 2023 vs 2024
- Calculates percentage growth correctly
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers (inflated numbers)
- ❌ Doesn't filter for international flights
- ❌ Uses Published Airline (double-counts codeshares)
- ❌ Incorrect growth calculation

---

## Question 3: Terminal and Airline Analysis (Medium Complexity)

**Difficulty**: ★★★☆☆ (3/5)
**Concepts Tested**: 4

```python
question_3 = """
For each SFO terminal in 2024, show which airline handles the most
passengers. Include the terminal name, airline name, and total passengers.
Only count passengers who are actually boarding or arriving at SFO,
not connecting passengers.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Codeshare Awareness - Use Operating Airline
3. ✓ Grouping - By terminal, find top airline
4. ✓ Column Quoting - Handle spaces

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Uses `"Operating Airline"` to avoid duplicates
- Groups by `"Terminal"`
- Uses window function or subquery to find top airline per terminal
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers
- ❌ Uses Published Airline (wrong counts)
- ❌ Syntax errors from unquoted columns

---

## Question 4: Domestic vs International by Price Category (Medium-High Complexity)

**Difficulty**: ★★★★☆ (4/5)
**Concepts Tested**: 5

```python
question_4 = """
Break down 2024 passenger traffic by geography (Domestic vs International)
and price category (Low Fare vs Other). For each combination, show:
- Total passengers
- Top 3 airlines
- Percentage of overall traffic

Exclude connecting passengers and make sure not to double-count
codeshare flights.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Geographic Filtering - Domestic and International breakdown
3. ✓ Price Category Filtering - Low Fare and Other breakdown
4. ✓ Codeshare Awareness - Use Operating Airline
5. ✓ Percentage Calculations - Market share

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Groups by `"GEO Summary"` (Domestic/International)
- Groups by `"Price Category Code"` (Low Fare/Other)
- Uses `"Operating Airline"` to avoid codeshare double-counting
- Calculates percentages correctly
- Uses window functions for top 3 per group
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers
- ❌ Doesn't know Price Category Code column
- ❌ Uses Published Airline (double-counts)
- ❌ Incorrect percentage calculations

---

## Question 5: Regional Analysis for Low-Fare Carriers (High Complexity)

**Difficulty**: ★★★★★ (5/5)
**Concepts Tested**: 6

```python
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
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Geographic Filtering - International regions
3. ✓ Price Category Filtering - Low Fare vs all carriers
4. ✓ Codeshare Awareness - Use Operating Airline
5. ✓ Percentage Calculations - Market share by region
6. ✓ Complex Aggregations - Multiple levels of grouping

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Filters `"GEO Summary" = 'International'`
- Groups by `"GEO Region"` (Europe, Asia, etc.)
- Filters `"Price Category Code" = 'Low Fare'` for subset
- Uses `"Operating Airline"` to avoid codeshare double-counting
- Calculates market share percentages correctly
- Uses window functions or CTEs for complex aggregation
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers
- ❌ Doesn't know how to filter regions
- ❌ Doesn't know about Price Category Code
- ❌ Uses Published Airline (inflates numbers)
- ❌ Complex SQL errors without proper understanding

---

## Question 6: Monthly Trend Analysis (Medium Complexity)

**Difficulty**: ★★★☆☆ (3/5)
**Concepts Tested**: 4

```python
question_6 = """
Show the month-by-month trend of total passenger traffic for 2024.
For each month, show the total passengers and break it down by
domestic vs international.

Only include passengers who departed or arrived at SFO, not those
connecting through the airport.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Geographic Filtering - Domestic vs International breakdown
3. ✓ Date Handling - Extract month from timestamp
4. ✓ Column Quoting - Handle spaces

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Groups by `"GEO Summary"` for domestic/international split
- Extracts month from `Date` column (timestamp)
- Orders by month chronologically
- Quotes all column names

**Common mistakes without skill:**
- ❌ Includes transit passengers
- ❌ Uses Year column instead of Date for month extraction
- ❌ Doesn't understand GEO Summary column

---

## Question 7: Codeshare Flight Analysis (High Complexity)

**Difficulty**: ★★★★★ (5/5)
**Concepts Tested**: 5

```python
question_7 = """
For 2024, identify which airlines have the most codeshare partnerships.
For each operating airline, show:
- How many different published airlines market their flights
- Total passengers on codeshare flights (where operating ≠ published)
- Total passengers on non-codeshare flights
- Percentage that are codeshares

Only include actual passengers, not connecting passengers.
"""
```

**What this tests:**
1. ✓ Activity Type Filtering - Exclude transit passengers
2. ✓ Codeshare Understanding - Operating vs Published comparison
3. ✓ Distinct Counting - Count unique partners
4. ✓ Conditional Aggregation - Separate codeshare vs non-codeshare
5. ✓ Percentage Calculations - Codeshare ratio

**Expected skill benefits:**
- Filters `"Activity Type Code" IN ('Deplaned', 'Enplaned')`
- Understands `"Operating Airline" != "Published Airline"` = codeshare
- Counts DISTINCT `"Published Airline"` per operating airline
- Uses CASE WHEN for conditional aggregation
- Calculates percentages correctly
- Quotes all column names

**Common mistakes without skill:**
- ❌ Doesn't understand codeshare concept
- ❌ Includes transit passengers
- ❌ Incorrect logic for identifying codeshares
- ❌ Fails to count distinct partners correctly

---

## Quick Reference Table

| Question | Difficulty | Key Concepts | Best For Testing |
|----------|-----------|--------------|------------------|
| 1. Seasonal Low-Fare | ★★★☆☆ | Activity, Price, Date, Quoting | Date handling, Price categories |
| 2. International Growth | ★★★★☆ | Activity, Geographic, Codeshare, Growth | Year comparison, Growth calculations |
| 3. Terminal Analysis | ★★★☆☆ | Activity, Codeshare, Grouping | Terminal grouping, Top-N queries |
| 4. Geo + Price Breakdown | ★★★★☆ | Activity, Geographic, Price, Codeshare, % | Multi-dimensional analysis |
| 5. Regional Market Share | ★★★★★ | All 6 concepts | Complex aggregations |
| 6. Monthly Trends | ★★★☆☆ | Activity, Geographic, Date | Time series analysis |
| 7. Codeshare Analysis | ★★★★★ | Activity, Codeshare understanding | Codeshare logic mastery |

---

## Usage Template

```python
# Pick a question
question = question_2  # or question_1, question_3, etc.

print("=" * 80)
print("TESTING QUESTION:")
print(question)
print("=" * 80)

# Test WITHOUT skill
print("\nWITHOUT SKILL:")
result_no_skill = agent_no_skill.ask_question(
    question=question,
    verbose=True
)

# Test WITH skill
print("\n\nWITH SKILL:")
result_with_skill = agent_with_skill.ask_question(
    question=question,
    verbose=True
)

# Compare results
print("\n" + "=" * 80)
print("COMPARISON:")
print(f"Without skill success: {result_no_skill.success}")
print(f"With skill success: {result_with_skill.success}")
print("=" * 80)
```

---

## Recommended Testing Sequence

### Phase 1: Start Simple
1. **Question 6** (Monthly Trends) - Easiest to understand
2. **Question 3** (Terminal Analysis) - Simple grouping

### Phase 2: Add Complexity
3. **Question 1** (Seasonal Low-Fare) - Introduces price categories
4. **Question 2** (International Growth) - Adds year comparison

### Phase 3: High Complexity
5. **Question 4** (Geo + Price Breakdown) - Multi-dimensional
6. **Question 5** (Regional Market Share) - Full complexity
7. **Question 7** (Codeshare Analysis) - Advanced codeshare logic

---

## Expected Improvements Summary

All questions should show these improvements with skill:

✅ **Correctness**: Proper filtering (activity types, geography, price)
✅ **Accuracy**: Avoid double-counting (use Operating Airline)
✅ **Syntax**: Proper column quoting (no syntax errors)
✅ **Business Logic**: Correct interpretation of requirements
✅ **Query Quality**: More efficient, cleaner SQL structure

The skill provides the domain knowledge needed to go from generic SQL generation to business-accurate query generation.
