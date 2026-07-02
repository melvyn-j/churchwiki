"""
Fetch Christian churches in Canada from OpenStreetMap via Overpass API.

This pulls actual church locations (not charitable trusts) with:
- Name, denomination, address, city, province
- Website, phone
- GPS coordinates

Source: OpenStreetMap (ODbL license)
API: https://overpass-api.de/api/interpreter
"""

import os
import json
import time
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_JSON = os.path.join(DATA_DIR, "osm_churches_raw.json")
CHURCHES_CSV = os.path.join(DATA_DIR, "churches_canada.csv")

OVERPASS_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

# Query all Christian places of worship in Canada
# nwr = nodes, ways, relations
# "out center tags" gives us the center coordinates for ways/relations
OVERPASS_QUERY = """
[out:json][timeout:300];
area["ISO3166-1"="CA"]->.canada;
(
  nwr["amenity"="place_of_worship"]["religion"="christian"](area.canada);
);
out center tags;
"""


def fetch_from_overpass() -> dict:
    """Query the Overpass API for all Christian churches in Canada."""
    print("Querying Overpass API for Christian churches in Canada...")
    print("This may take 1-3 minutes (large query)...")

    response = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=360,
    )
    response.raise_for_status()

    data = response.json()
    print(f"  Received {len(data.get('elements', []))} elements from OSM")
    return data


def parse_elements(data: dict) -> list[dict]:
    """Parse OSM elements into flat church records."""
    records = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})

        # Get coordinates (center for ways/relations, direct for nodes)
        if element["type"] == "node":
            lat = element.get("lat")
            lon = element.get("lon")
        else:
            center = element.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")

        record = {
            "osm_id": f"{element['type']}/{element['id']}",
            "name": tags.get("name", ""),
            "denomination": tags.get("denomination", ""),
            "addr_street": tags.get("addr:street", ""),
            "addr_housenumber": tags.get("addr:housenumber", ""),
            "addr_city": tags.get("addr:city", ""),
            "addr_province": tags.get("addr:province", ""),
            "addr_postcode": tags.get("addr:postcode", ""),
            "phone": tags.get("phone", tags.get("contact:phone", "")),
            "website": tags.get("website", tags.get("contact:website", "")),
            "email": tags.get("email", tags.get("contact:email", "")),
            "opening_hours": tags.get("opening_hours", ""),
            "wheelchair": tags.get("wheelchair", ""),
            "lat": lat,
            "lon": lon,
        }

        records.append(record)

    return records


def build_address(row: dict) -> str:
    """Build a full address string from components."""
    parts = []
    if row["addr_housenumber"]:
        parts.append(row["addr_housenumber"])
    if row["addr_street"]:
        parts.append(row["addr_street"])
    return " ".join(parts)


def main():
    """Main entry point."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Step 1: Fetch from Overpass (or use cached)
    if os.path.exists(RAW_JSON):
        print(f"Using cached file: {RAW_JSON}")
        with open(RAW_JSON, "r") as f:
            data = json.load(f)
        print(f"  Loaded {len(data.get('elements', []))} elements")
    else:
        data = fetch_from_overpass()
        # Cache the raw response
        with open(RAW_JSON, "w") as f:
            json.dump(data, f)
        print(f"  Cached raw data to: {RAW_JSON}")

    # Step 2: Parse into records
    print("\nParsing church records...")
    records = parse_elements(data)
    print(f"  Parsed {len(records)} churches")

    # Step 3: Convert to DataFrame and clean up
    df = pd.DataFrame(records)

    # Build full address column
    df["address"] = df.apply(build_address, axis=1)

    # Drop unnamed churches (some OSM nodes are just markers without names)
    named = df[df["name"].str.strip() != ""]
    unnamed = len(df) - len(named)
    print(f"  Named churches: {len(named)}")
    print(f"  Unnamed (dropped): {unnamed}")
    df = named.copy()

    # Sort by province then name
    df = df.sort_values(["addr_province", "name"]).reset_index(drop=True)

    # Save
    df.to_csv(CHURCHES_CSV, index=False)
    print(f"\n  Saved to: {CHURCHES_CSV}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Christian churches: {len(df):,}")

    print(f"\nBy denomination (top 15):")
    denom_counts = df["denomination"].replace("", "(not specified)").value_counts()
    for denom, count in denom_counts.head(15).items():
        print(f"  {denom}: {count:,}")

    print(f"\nBy province (from addr:province tag):")
    prov_counts = df["addr_province"].replace("", "(not tagged)").value_counts()
    for prov, count in prov_counts.head(15).items():
        print(f"  {prov}: {count:,}")

    print(f"\nSample records:")
    display_cols = ["name", "denomination", "addr_city", "addr_province"]
    print(df[display_cols].head(10).to_string(index=False))

    print(f"\n\nDone! Church data at: {CHURCHES_CSV}")


if __name__ == "__main__":
    main()
