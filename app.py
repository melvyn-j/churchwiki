"""
ChurchWiki - A simple FastAPI + Jinja2 app to browse Canadian churches.

Data source: CRA 2023 List of Charities (Open Government Licence - Canada)
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
        print("Run 'python fetch_churches.py' first to download the data.")
        return

    churches_df = pd.read_csv(DATA_PATH, dtype=str, low_memory=False)
    churches_df = churches_df.fillna("")
    print(f"Loaded {len(churches_df):,} churches from {DATA_PATH}")


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    page: int = Query(1, ge=1),
    province: str = Query("", alias="province"),
    search: str = Query("", alias="search"),
):
    """Main page: paginated list of churches with search and province filter."""
    per_page = 50
    df = churches_df.copy()

    # Filter by province
    if province:
        df = df[df["Province"].str.upper() == province.upper()]

    # Search by name or city
    if search:
        mask = (
            df["Legal Name"].str.lower().str.contains(search.lower(), na=False)
            | df["City"].str.lower().str.contains(search.lower(), na=False)
        )
        df = df[mask]

    total = len(df)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    start = (page - 1) * per_page
    end = start + per_page
    page_data = df.iloc[start:end]

    churches = page_data.to_dict(orient="records")

    # Get unique provinces for filter dropdown
    provinces = sorted(churches_df["Province"].unique())

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "churches": churches,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "province": province,
            "search": search,
            "provinces": provinces,
        },
    )


@app.get("/church/{bn}", response_class=HTMLResponse)
async def church_detail(request: Request, bn: str):
    """Detail page for a single church by BN (Business Number)."""
    row = churches_df[churches_df["BN"] == bn]
    if row.empty:
        return HTMLResponse("<h1>Church not found</h1>", status_code=404)

    church = row.iloc[0].to_dict()
    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "church": church},
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
