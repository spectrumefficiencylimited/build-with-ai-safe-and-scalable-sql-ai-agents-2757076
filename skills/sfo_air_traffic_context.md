# SFO Air Traffic Passenger Statistics - Domain Knowledge

## Schema Reference

```
Table: air_traffic (Monthly passenger data, July 1999 - present)

Year                        int64      -- 4-digit year (1999-present)
Date                        timestamp  -- First day of month (YYYY-MM-DD)
Operating Airline           string     -- Airline that operated the flight
Operating Airline IATA Code string     -- 2-letter code (may be NULL)
Published Airline           string     -- Marketing airline (codeshare)
Published Airline IATA Code string     -- 2-letter code (may be NULL)
GEO Summary                 string     -- "Domestic" or "International"
GEO Region                  string     -- "US", "Europe", "Asia", etc.
Activity Type Code          string     -- "Deplaned", "Enplaned", "Thru / Transit"
Price Category Code         string     -- "Low Fare" or "Other"
Terminal                    string     -- "Terminal 1", "Terminal 2", etc.
Boarding Area               string     -- A, B, C, D, E, F, G
Passenger Count             int64      -- Monthly passenger total
```

**CRITICAL**: Column names with spaces MUST be quoted: `"Operating Airline"`, `"Passenger Count"`, etc.

## Key Column Details

### Activity Type Code (string)
- **`Deplaned`**: Passengers arriving at SFO
- **`Enplaned`**: Passengers departing from SFO
- **`Thru / Transit`**: Connecting passengers (not originating/terminating at SFO)
- **Common filter**: Use `IN ('Deplaned', 'Enplaned')` to exclude transit passengers

### Airlines (Codeshares)
- **Operating Airline**: Airline that actually operates the flight (use this to avoid double-counting)
- **Published Airline**: Marketing airline selling the ticket
- When `Operating Airline ≠ Published Airline`, it's a codeshare flight
- **Best practice**: Use Operating Airline for passenger totals to avoid counting same passengers multiple times

### Geographic Fields
- **GEO Summary**: `"Domestic"` or `"International"`
- **GEO Region**: For Domestic = `"US"`, for International = region names (`"Europe"`, `"Asia"`, `"Canada"`, `"Mexico"`, etc.)

### Price Category Code
- **`Low Fare`**: Budget/discount carriers
- **`Other`**: Full-service and premium carriers

### Date vs Year
- **Date** (timestamp): Use for month/quarter extraction, date ranges
- **Year** (int64): Use for simple year filtering (more efficient)
- Each month represented by 1st day: `2024-01-01` = January 2024

## Critical Best Practices

### 1. Excluding Transit Passengers
Most analyses should exclude transit passengers:
```sql
WHERE "Activity Type Code" IN ('Deplaned', 'Enplaned')
-- OR exclude explicitly
WHERE "Activity Type Code" != 'Thru / Transit'
```

### 2. Avoiding Codeshare Double-Counting
Use Operating Airline to count actual flights/passengers:
```sql
GROUP BY "Operating Airline"  -- ✓ Correct
-- NOT: GROUP BY "Published Airline"  -- ✗ May double-count
```

### 3. Geographic Filtering
```sql
-- High-level split
WHERE "GEO Summary" = 'International'

-- Regional detail
WHERE "GEO Region" = 'Europe'
-- Note: Domestic flights all have "GEO Region" = 'US'
```

### 4. Column Quoting
Always use double quotes for columns with spaces:
```sql
SELECT "Operating Airline", "Passenger Count", "Activity Type Code"
```

## Common Query Patterns

### Top Airlines (excluding transit)
```sql
SELECT "Operating Airline", SUM("Passenger Count") as total
FROM air_traffic
WHERE "Year" = 2024 AND "Activity Type Code" IN ('Deplaned', 'Enplaned')
GROUP BY "Operating Airline"
ORDER BY total DESC
LIMIT 10
```

### International vs Domestic
```sql
SELECT "GEO Summary", SUM("Passenger Count") as total
FROM air_traffic
WHERE "Year" = 2024 AND "Activity Type Code" IN ('Deplaned', 'Enplaned')
GROUP BY "GEO Summary"
```

### Low-Fare Carriers
```sql
SELECT "Operating Airline", SUM("Passenger Count") as total
FROM air_traffic
WHERE "Price Category Code" = 'Low Fare'
  AND "Activity Type Code" IN ('Deplaned', 'Enplaned')
GROUP BY "Operating Airline"
```

### Terminal Usage
```sql
SELECT "Terminal", SUM("Passenger Count") as total
FROM air_traffic
WHERE "Activity Type Code" != 'Thru / Transit'
GROUP BY "Terminal"
```

📊 Percentage & Growth Calculations (Dataset Guidance)
1. Always define the base (denominator) explicitly

For any percentage, growth, or rate calculation:

The denominator must be stated and named explicitly

Never infer the denominator from context

Required pattern:

percentage = (numerator / denominator) × 100


Example:

Year-over-year growth percentage must use the earlier period
(e.g., previous year) as the denominator.

2. Use prior-period totals for growth metrics

When calculating growth between two periods (year-over-year, month-over-month):

Use the earlier period as the denominator

Never divide by the later period or by the average

Canonical formula:
```
growth_percentage = ((current_period − prior_period) × 100.0) / prior_period
```

This rule applies regardless of time granularity (year, quarter, month).

3. Compute aggregates before calculating percentages

Percentages must be calculated after aggregation, not at the row level.

Correct order of operations:

Filter rows (e.g., geography, activity type)

Aggregate raw counts per entity and period

Compute percentage metrics from aggregated totals

Anti-pattern (do not do):

Calculating percentages on individual rows and summing them

Mixing aggregation and percentage logic in the same expression repeatedly

4. Handle zero and missing denominators explicitly

For any division:

Use NULLIF(denominator, 0)

Exclude entities where the denominator is zero or missing

Do not silently return infinite or misleading values

Required behavior:

If the denominator is zero or NULL:
- Return NULL for the percentage
- Or exclude the entity from ranking

5. Enforce numeric precision
To avoid integer division or rounding errors:
- Cast or multiply by a floating-point value (100.0)
- Do not rely on implicit type coercion
Required pattern:
```
(value_diff * 100.0) / NULLIF(base_value, 0)
``
6. Name intermediate values clearly

When possible:
Store aggregated values in clearly named columns or CTEs
- Use semantic names such as:
  - total_2023
  - total_2024
  - prior_period_total
  - current_period_total
- This improves:
  - Readability
  - Validation
  - Agent reliability

7. Ranking rules for percentage metrics
When ranking by a percentage:
- Rank after percentage calculation
- Exclude rows with NULL or invalid percentages
- Document whether negative growth is allowed

Example rule:
```
Rank entities by growth_percentage DESC.
Exclude entities with prior-period totals equal to zero.
```
8. Dataset-wide convention (recommended)

Add a short “contract” the agent can rely on:

Dataset Convention:
All growth and percentage metrics must:
- Use prior-period totals as the denominator
- Be computed from aggregated values
- Explicitly guard against division by zer


## Quick Reference

| Question Type | Key Filters |
|--------------|-------------|
| Total passengers | `"Activity Type Code" IN ('Deplaned', 'Enplaned')` |
| Actual airlines | `GROUP BY "Operating Airline"` |
| International only | `"GEO Summary" = 'International'` |
| Low-fare carriers | `"Price Category Code" = 'Low Fare'` |
| Departures only | `"Activity Type Code" = 'Enplaned'` |
| By region | `GROUP BY "GEO Region"` |

## Common Pitfalls to Avoid

❌ **Don't** include transit passengers in total traffic counts
❌ **Don't** use Published Airline for totals (causes double-counting)
❌ **Don't** forget to quote column names with spaces
❌ **Don't** mix Operating and Published airlines in same analysis
❌ **Don't** count Deplaned + Enplaned for "unique passengers" (counts each twice)

✅ **Do** exclude `'Thru / Transit'` for most analyses
✅ **Do** use `"Operating Airline"` to avoid codeshare duplicates
✅ **Do** quote all column names with spaces
✅ **Do** filter by appropriate Activity Type Code
✅ **Do** use GEO Summary for domestic vs international split
