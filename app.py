"""
ChurchWiki - A simple FastAPI + Jinja2 app to browse Canadian churches.

Data source: OpenStreetMap via Overpass API (ODbL license)
Run: python app.py
"""

import os
import pandas as pd
import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "churches_canada.csv")

app = FastAPI(title="ChurchWiki Canada")

# Templates and static files
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Load church data into memory at startup
churches_df: pd.DataFrame = pd.DataFrame()


@app.on_event("startup")
def load_data():
    global churches_df
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: Church data not found at {DATA_PATH}")
        print("Run 'python fetch_osm_churches.py' first to download the data.")
        return

    churches_df = pd.read_csv(DATA_PATH, dtype=str, low_memory=False)
    churches_df = churches_df.fillna("")
    print(f"Loaded {len(churches_df):,} churches from {DATA_PATH}")


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    page: int = Query(1, ge=1),
    denomination: str = Query("", alias="denomination"),
    search: str = Query("", alias="search"),
):
    """Main page: paginated list of churches with search and denomination filter."""
    per_page = 50
    df = churches_df.copy()

    # Filter by denomination
    if denomination:
        df = df[df["denomination"].str.lower() == denomination.lower()]

    # Search by name or city
    if search:
        mask = (
            df["name"].str.lower().str.contains(search.lower(), na=False)
            | df["addr_city"].str.lower().str.contains(search.lower(), na=False)
        )
        df = df[mask]

    total = len(df)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    start = (page - 1) * per_page
    end = start + per_page
    page_data = df.iloc[start:end]

    churches = page_data.to_dict(orient="records")

    # Get unique denominations for filter dropdown
    denoms = sorted(churches_df["denomination"].unique())
    denoms = [d for d in denoms if d]  # remove empty

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "churches": churches,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "denomination": denomination,
            "search": search,
            "denominations": denoms,
        },
    )


@app.get("/church/{osm_id:path}", response_class=HTMLResponse)
async def church_detail(request: Request, osm_id: str):
    """Detail page for a single church by OSM ID."""
    row = churches_df[churches_df["osm_id"] == osm_id]
    if row.empty:
        return HTMLResponse("<h1>Church not found</h1>", status_code=404)

    church = row.iloc[0].to_dict()
    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "church": church},
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
