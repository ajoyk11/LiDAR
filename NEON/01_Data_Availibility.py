
import requests
import pandas as pd
from pathlib import Path

DPID = "DP1.30003.001"  # product code
BASE = "https://data.neonscience.org/api/v0"

# Get all NEON sites
sites = requests.get(f"{BASE}/sites").json()["data"]
site_codes = sorted(s["siteCode"] for s in sites)

# Get product availability
product = requests.get(f"{BASE}/products/{DPID}").json()["data"]

# Site-wise available months
availability = {
    s["siteCode"]: set(s["availableMonths"])
    for s in product["siteCodes"]
}

# Create month columns (latest first)
months = sorted(
    {m for values in availability.values() for m in values},
    reverse=True
)

# Create binary availability matrix
df = pd.DataFrame(
    [
        [site] + [
            int(month in availability.get(site, set()))
            for month in months
        ]
        for site in site_codes
    ],
    columns=["Site"] + [m.replace("-", "_") for m in months]
)

# Save CSV in current working directory
df.to_csv(Path.cwd() / f"{DPID}_site_month_availability.csv",
          index=False)

print(df)
print("\nCSV saved successfully!")
