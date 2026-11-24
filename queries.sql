-- Annual demand and peak month volume
SELECT year, SUM(passengers) AS annual_passengers, MAX(passengers) AS peak_month_passengers
FROM monthly_demand GROUP BY year ORDER BY year;

-- Quarterly demand
SELECT year, quarter, SUM(passengers) AS passengers
FROM monthly_demand GROUP BY year, quarter ORDER BY year, quarter;

-- Fact and dimension counts
SELECT (SELECT COUNT(*) FROM fact_passenger_demand) AS facts,
       (SELECT COUNT(*) FROM dim_month) AS months,
       (SELECT COUNT(*) FROM dim_series) AS series;

PRAGMA foreign_key_check;
