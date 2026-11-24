# ELEC 411 airline demand warehouse
 
## Reproduce
Use Python 3.12 and NumPy (tested with 2.3.5).
 
    python -m pip install numpy==2.3.5
    python build_project.py
 
Run the commands from the extracted project directory. The build uses the included CSV and works offline once NumPy is installed. It rebuilds airline_warehouse.sqlite and writes results.json. The supplied Dashboard.html embeds the results for this fixed dataset. Keep dashboard.css alongside it to load the styles offline.
 
## Dataset documentation
Source: Box and Jenkins AirPassengers. See https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/AirPassengers.html
CSV: https://raw.githubusercontent.com/mwaskom/seaborn-data/master/flights.csv
 
The included CSV reproduces the 144 observations in the source CSV. Columns: year (integer, 1949–1960), month (English calendar month name), passengers (positive integer, in thousands). One row per month. No missing observations or duplicate months. The ETL derives YYYYMM, an ISO month start date, month number and quarter, then converts thousands to passengers.
 
The fact contains one observation per month and series. The passenger measure is additive across disjoint months of the same series. Month and series are the two foreign keys. Run queries.sql in a SQLite client for rollups.
 
## Demonstration
1. Run build_project.py. Point out the 144 loaded observations and describe how the validation prevents gaps and duplicates.
2. Open airline_warehouse.sqlite and inspect both dimensions, the demand fact and the monthly_demand view. Run the annual and quarterly SQL queries.
3. Open the HTML dashboard and switch between 1949 and 1960. Show the annual volume change and the seasonal peaks.
4. Compare the regression curve with actual test values and the seasonal baseline. Explain that no observations after 1958 were used for forecasting.
5. Show the four cluster bands. Explain why July and August group together and why the result is for historical aggregate demand only.
