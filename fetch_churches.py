"""
Fetch Canadian church data from the CRA Open Data portal.

Downloads the 2023 List of Charities (Identification CSV) from
Open Canada and filters for religious organizations / places of worship.

Source: https://open.canada.ca/data/en/dataset/05b3abd0-e70f-4b3b-a9c5-acc436bd15b6
License: Open Government Licence - Canada
"""

import os
import sys
import requests
import pandas as pd

# CRA 2023 List of Charities - Identification CSV
IDENTIFICATION_CSV_URL = (
    "https://open.canada.ca/data/dataset/"
    "05b3abd0-e70f-4b3b-a9c5-acc436bd15b6/resource/"
    "31a52caf-fa79-4ab3-bded-1ccc7b61c17f/download/ident_2023_updated.csv"
)

# Output paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_CSV = os.path.join(DATA_DIR, "cra_charities_identification_2023.csv")
CHURCHES_CSV = os.path.join(DATA_DIR, "churches_canada.csv")

# Religion-related category codes from CRA codes list (4-digit codes)
# 0030 = Religion (places of worship, congregations, parishes - the main one)
# 0070 = Support of religion (missionary, religious education, fellowships)
RELIGION_CATEGORY_CODES = ["0030", "0070"]

# Keywords to catch religion orgs that may be in other categories
RELIGION_KEYWORDS = [
    "church", "churches", "mosque", "masjid", "temple",
    "synagogue", "parish", "congregation", "chapel",
    "gurdwara", "mandir", "tabernacle", "ministry",
    "cathedral", "basilica", "abbey",
]


def download_csv(url: str, output_path: str) -> None:
    """Download CSV file from URL with progress indication."""
    print(f"Downloading from: {url}")
    print("This is ~13 MB, may take a moment...")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = (downloaded / total_size) * 100
                print(f"\r  Progress: {pct:.1f}% ({downloaded // 1024} KB)", end="")

    print(f"\n  Saved to: {output_path}")


def filter_churches(
    input_path: str,
    output_path: str,
    category_only: bool = False,
) -> pd.DataFrame:
    """
    Filter the CRA charities CSV for religious organizations / churches.

    Uses two strategies:
      1. Category-based: Categories 0030 (Religion) and 0070 (Support of Religion)
      2. Keyword-based: Catches churches in other categories by name matching

    Args:
        input_path: Path to the full CRA identification CSV.
        output_path: Path to save the filtered churches CSV.
        category_only: If True, only use category codes (no keyword matching).

    Returns:
        DataFrame of filtered church records.
    """
    print(f"\nLoading CSV: {input_path}")
    df = pd.read_csv(input_path, dtype=str, low_memory=False)

    print(f"  Total charities loaded: {len(df):,}")

    # Normalize column names (strip whitespace)
    df.columns = df.columns.str.strip()

    # Filter by Religion categories (0030 and 0070)
    category_mask = df["Category"].isin(RELIGION_CATEGORY_CODES)
    print(f"  Religion categories (0030 + 0070): {category_mask.sum():,}")

    if category_only:
        churches_df = df[category_mask].copy()
    else:
        # Also match by name keywords (catches churches filed under other categories)
        name_lower = df["Legal Name"].fillna("").str.lower()
        keyword_pattern = "|".join(RELIGION_KEYWORDS)
        keyword_mask = name_lower.str.contains(keyword_pattern, na=False)
        print(f"  Keyword matches (across all categories): {keyword_mask.sum():,}")

        # Combine: category OR keyword
        combined_mask = category_mask | keyword_mask
        churches_df = df[combined_mask].copy()

        # Remove duplicates (some will match both)
        churches_df = churches_df.drop_duplicates(subset=["BN"])

    print(f"  Total unique religious orgs after filter: {len(churches_df):,}")

    # Save filtered results
    churches_df.to_csv(output_path, index=False)
    print(f"\n  Filtered churches saved to: {output_path}")

    return churches_df


def print_summary(df: pd.DataFrame) -> None:
    """Print a summary of the church data."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total churches found: {len(df):,}")

    # Province breakdown
    province_col = None
    for col in df.columns:
        if "province" in col.lower():
            province_col = col
            break

    if province_col:
        print(f"\nBy Province/Territory:")
        province_counts = df[province_col].value_counts()
        for province, count in province_counts.items():
            print(f"  {province}: {count:,}")

    # Sample records
    print(f"\nSample records (first 5):")
    name_col = None
    for col in df.columns:
        if "legal" in col.lower() and "name" in col.lower():
            name_col = col
            break
    if name_col is None:
        for col in df.columns:
            if "name" in col.lower():
                name_col = col
                break

    city_col = None
    for col in df.columns:
        if "city" in col.lower():
            city_col = col
            break

    display_cols = [c for c in [name_col, city_col, province_col] if c is not None]
    if display_cols:
        print(df[display_cols].head(5).to_string(index=False))


def main():
    """Main entry point."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Step 1: Download the CSV if not already cached
    if os.path.exists(RAW_CSV):
        print(f"Using cached file: {RAW_CSV}")
    else:
        download_csv(IDENTIFICATION_CSV_URL, RAW_CSV)

    # Step 2: Filter for churches
    # Set category_only=True to only use CRA religion categories (0030, 0070)
    # Set category_only=False to also match by name keywords (broader results)
    churches_df = filter_churches(
        input_path=RAW_CSV,
        output_path=CHURCHES_CSV,
        category_only=False,
    )

    # Step 3: Summary
    print_summary(churches_df)

    print(f"\n\nDone! Church data is at: {CHURCHES_CSV}")
    print("You can set 'category_only=True' to restrict to CRA religion categories only.")


if __name__ == "__main__":
    main()
