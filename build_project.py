"""Build the airline demand warehouse and analysis. Requires Python 3.12 and NumPy."""
import calendar
import csv
import json
import sqlite3
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DB = ROOT / "airline_warehouse.sqlite"
SOURCE = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/flights.csv"
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS dim_month (
    month_key INTEGER PRIMARY KEY,
    month_start TEXT UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    month_number INTEGER NOT NULL CHECK(month_number BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    quarter INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4)
);
CREATE TABLE IF NOT EXISTS dim_series (
    series_key INTEGER PRIMARY KEY,
    series_name TEXT UNIQUE NOT NULL,
    source_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_passenger_demand (
    month_key INTEGER NOT NULL REFERENCES dim_month(month_key),
    series_key INTEGER NOT NULL REFERENCES dim_series(series_key),
    passengers INTEGER NOT NULL CHECK(passengers > 0),
    PRIMARY KEY (month_key, series_key)
);
CREATE VIEW IF NOT EXISTS monthly_demand AS
SELECT d.month_start, d.year, d.month_number, d.month_name, d.quarter,
       s.series_name, f.passengers
FROM fact_passenger_demand f
JOIN dim_month d USING(month_key)
JOIN dim_series s USING(series_key);
"""

def etl():
    path = ROOT / "flights.csv"
    months, facts = [], []
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            year = int(row["year"])
            month = list(calendar.month_name).index(row["month"])
            key = year * 100 + month
            count = int(row["passengers"])
            if count <= 0 or month == 0:
                raise ValueError(f"Invalid source observation for {key}")
            months.append((key, f"{year:04d}-{month:02d}-01", year, month,
                           row["month"], (month - 1) // 3 + 1))
            facts.append((key, 1, count * 1000))
    expected = [year * 100 + month for year in range(1949, 1961) for month in range(1, 13)]
    if sorted(row[0] for row in months) != expected:
        raise ValueError("Missing, duplicate or out-of-range month")
    with sqlite3.connect(DB) as con:
        con.executescript(SCHEMA)
        con.execute("DELETE FROM fact_passenger_demand")
        con.execute("DELETE FROM dim_month")
        con.execute("DELETE FROM dim_series")
        con.execute("INSERT INTO dim_series VALUES (1, ?, ?)",
                    ("International airline passenger totals", SOURCE))
        con.executemany("INSERT INTO dim_month VALUES (?, ?, ?, ?, ?, ?)", months)
        con.executemany("INSERT INTO fact_passenger_demand VALUES (?, ?, ?)", facts)
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        return con.execute("SELECT * FROM monthly_demand ORDER BY month_start").fetchall()

def forecasting(values):
    time = np.arange(len(values))
    design = np.column_stack([np.ones(len(time)), time / 12] +
                             [(time % 12 == m).astype(float) for m in range(1, 12)])
    fit = np.linalg.lstsq(design[:120], np.log(values[:120]), rcond=None)[0]
    fitted_log = design[:120] @ fit
    correction = np.exp(np.log(values[:120]) - fitted_log).mean()
    predictions = np.exp(design[120:] @ fit) * correction
    naive = np.tile(values[108:120], 2)
    observed = values[120:]
    def metrics(estimate):
        error = estimate - observed
        return {"MAE": float(np.abs(error).mean()), "RMSE": float(np.sqrt((error ** 2).mean())),
                "MAPE": float(np.mean(np.abs(error) / observed) * 100)}
    return predictions, naive, {"Log seasonal regression": metrics(predictions),
                                "Seasonal naive": metrics(naive)}

def clustering(years):
    shares = 100 * years / years.sum(axis=1, keepdims=True)
    profiles = shares.mean(axis=0)
    outcomes = {}
    for k in (2, 3, 4):
        best = None
        from itertools import combinations
        ordered = np.argsort(profiles, kind="stable")
        for splits in combinations(range(1, 12), k - 1):
            groups = np.split(ordered, splits)
            cost = sum(((profiles[g] - profiles[g].mean()) ** 2).sum() for g in groups)
            if best is None or cost < best[0]:
                best = cost, groups
        _, groups = best
        silhouettes = []
        for group in groups:
            for m in group:
                remainder = group[group != m]
                if len(remainder) == 0:
                    silhouettes.append(0)
                    continue
                a = np.abs(profiles[m] - profiles[remainder]).mean()
                b = min(np.abs(profiles[m] - profiles[other]).mean()
                        for other in groups if other is not group)
                silhouettes.append((b - a) / max(a, b))
        outcomes[k] = {"silhouette": float(np.mean(silhouettes)),
                       "groups": [[calendar.month_abbr[m + 1] for m in sorted(g)] for g in groups],
                       "centers": [float(profiles[g].mean()) for g in groups]}
    return profiles.tolist(), outcomes

def main():
    rows = etl()
    values = np.array([row[-1] for row in rows], dtype=float)
    prediction, naive, scores = forecasting(values)
    profiles, groups = clustering(values.reshape(12, 12))
    result = {"monthly": [{"period": r[0][:7], "passengers": r[-1]} for r in rows],
              "forecast": [{"period": r[0][:7], "actual": r[-1],
                            "regression": round(p), "baseline": round(n)}
                           for r, p, n in zip(rows[120:], prediction, naive)],
              "metrics": scores, "monthly_share": profiles, "clusters": groups}
    (ROOT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "metrics": scores, "clusters": groups}, indent=2))

if __name__ == "__main__":
    main()

