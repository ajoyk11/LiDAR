
import os
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# 1. USER SETTINGS

DPID = "DP1.30003.001"
SITE = "BART"

START_MONTH = "2022-07"
END_MONTH = "2022-08"

TARGET_DATA = "classified_point_cloud_colorized"

# Current working directory
OUT_DIR = Path.cwd()

# NEON API
API_URL = "https://data.neonscience.org/api/v0/data/query"

TOKEN = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"

HEADERS = {
    "X-API-Token": TOKEN
}



# 2. QUERY NEON API

params = {
    "productCode": DPID,
    "siteCode": SITE,
    "startDateMonth": START_MONTH,
    "endDateMonth": END_MONTH,
    "includeProvisional": "false"
}

print("\nConnecting to NEON API...")

response = requests.get(
    API_URL,
    params=params,
    headers=HEADERS,
    timeout=120
)

response.raise_for_status()

result = response.json()

# 3. EXTRACT ALL AVAILABLE FILES

data = result.get("data", {})

all_files = []

for release_info in data.get("releases", []):

    release_name = release_info.get("release")

    for package in release_info.get("packages", []):

        month = package.get("month")
        site_code = package.get("siteCode")
        package_type = package.get("packageType")

        for file_info in package.get("files", []):

            all_files.append({
                "Site": site_code,
                "Month": month,
                "Release": release_name,
                "Package": package_type,
                "Filename": file_info.get("name"),
                "Size_MB": round(
                    file_info.get("size", 0) / (1024 ** 2), 3
                ),
                "URL": file_info.get("url"),
                "MD5": file_info.get("md5")
            })

# 4. LIST ALL AVAILABLE DATA

if not all_files:
    print("No released files found for this query.")
    raise SystemExit

inventory = pd.DataFrame(all_files)

inventory = inventory.sort_values(
    ["Month", "Filename"]
).reset_index(drop=True)

print("\n============================================")
print("COMPLETE NEON FILE INVENTORY")
print("============================================")

print(f"\nTotal available files: {len(inventory)}")

print(
    inventory[
        ["Month", "Release", "Filename", "Size_MB"]
    ].to_string(index=False)
)

# Save complete inventory
inventory_path = OUT_DIR / "BART_NEON_DP1_30003_2022_inventory.csv"

inventory.to_csv(inventory_path, index=False)

print("\nInventory saved:")
print(inventory_path)

# 5. SELECT ONLY COLORIZED CLASSIFIED POINT CLOUD

selected = inventory[
    inventory["Filename"].str.contains(
        TARGET_DATA,
        case=False,
        na=False
    )
].copy()

selected = selected.drop_duplicates(
    subset=["Filename"]
).reset_index(drop=True)

print("\n============================================")
print("SELECTED DATA")
print("============================================")

print(f"\nSelected files: {len(selected)}")

if selected.empty:
    print("No matching classified_point_cloud_colorized files.")
    raise SystemExit

print(
    selected[
        ["Month", "Filename", "Size_MB"]
    ].to_string(index=False)
)

# Save selected file inventory
selected_path = OUT_DIR / "BART_classified_point_cloud_colorized_inventory.csv"

selected.to_csv(selected_path, index=False)

# 6. DOWNLOAD SELECTED FILES

DOWNLOAD_DIR = OUT_DIR / "BART_classified_point_cloud_colorized"

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

print("\n============================================")
print("DOWNLOADING SELECTED FILES")
print("============================================")

session = requests.Session()
session.headers.update(HEADERS)

for _, row in tqdm(
    selected.iterrows(),
    total=len(selected),
    desc="Downloading"
):

    filename = row["Filename"]
    file_url = row["URL"]

    if not file_url:
        print(f"\nMissing URL: {filename}")
        continue

    output_file = DOWNLOAD_DIR / filename

    # Skip already downloaded files
    if output_file.exists():
        print(f"\nAlready exists: {filename}")
        continue

    try:

        with session.get(
            file_url,
            stream=True,
            timeout=(30, 300)
        ) as r:

            r.raise_for_status()

            with open(output_file, "wb") as f:

                for chunk in r.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if chunk:
                        f.write(chunk)

        print(f"\nDownloaded: {filename}")

    except Exception as e:

        print(f"\nDownload failed: {filename}")
        print("Error:", e)

# 
# 7. FINAL SUMMARY

print("\n============================================")
print("DOWNLOAD COMPLETED")
print("============================================")

print("Product:", DPID)
print("Site:", SITE)
print("Period:", START_MONTH, "to", END_MONTH)

print("Provisional data: EXCLUDED")

print("Total available files:", len(inventory))
print("Selected files:", len(selected))

print("Download directory:")
print(DOWNLOAD_DIR)

print("\nDownloaded files:")

for f in DOWNLOAD_DIR.iterdir():

    if f.is_file():
        print(f.name, "-", round(f.stat().st_size / 1024**2, 2), "MB")
