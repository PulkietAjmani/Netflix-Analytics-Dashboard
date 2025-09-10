# dashboard.py
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Netflix Analytics", page_icon="📊", layout="wide")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # --- Robust date parsing ---
    date_col = (
        df["date_added"]
        .astype(str)
        .str.strip()
        .replace({"": None, "NaT": None, "nan": None})
    )
    # Try strict US-style like "August 4, 2017"; fall back to mixed if needed
    parsed = pd.to_datetime(date_col, format="%B %d, %Y", errors="coerce")
    if parsed.isna().sum() > 0:
        parsed = pd.to_datetime(date_col, format="mixed", errors="coerce")
    df["date_added"] = parsed
    df["year_added"] = df["date_added"].dt.year

    # --- Tidy text fields ---
    for c in ["country", "listed_in", "director", "cast"]:
        if c in df.columns:
            df[c] = df[c].fillna("Unknown")

    # Movies vs Shows counts
    mv_tv = df["type"].value_counts().reset_index()
    mv_tv.columns = ["type", "count"]

    # Content added over time (by year)
    by_year = (
        df.dropna(subset=["year_added"])
        .groupby("year_added", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("year_added")
    )

    # Top countries (explode "USA, India" -> rows)
    countries = (
        df[["country"]]
        .assign(country=df["country"].str.split(","))
        .explode("country")
        .assign(country=lambda x: x["country"].str.strip())
    )
    top_countries = (
        countries[countries["country"].notna() & (countries["country"] != "Unknown")]
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"country": "country"})
        .head(10)
    )

    # Top genres
    genres = (
        df["listed_in"]
        .str.split(",")
        .explode()
        .str.strip()
        .to_frame(name="genre")
    )
    top_genres = (
        genres[genres["genre"].notna() & (genres["genre"] != "Unknown")]
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"genre": "genre"})
        .head(10)
    )

    return df, mv_tv, by_year, top_countries, top_genres


# ===== Sidebar =====
st.sidebar.title("📁 Data Source")
csv_path = st.sidebar.text_input(
    "CSV path", value="netflix_titles.csv", help="Path to netflix_titles.csv"
)

try:
    df, mv_tv, by_year, top_countries, top_genres = load_data(csv_path)
except Exception as e:
    st.error(f"Could not load data from '{csv_path}'. Details: {e}")
    st.stop()

# Optional year filter
years = sorted([y for y in df["year_added"].dropna().unique()])
if years:
    y_min, y_max = int(min(years)), int(max(years))
    sel_range = st.sidebar.slider("Filter by year added", y_min, y_max, (y_min, y_max))
    mask = df["year_added"].between(sel_range[0], sel_range[1])
else:
    sel_range = None
    mask = pd.Series([True] * len(df))

st.title("📊 Netflix Analytics Dashboard")

tab1, tab2, tab3 = st.tabs(["Overview", "Countries", "Genres"])

# ===== Overview =====
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Movies vs TV Shows")
        fig_type = px.bar(mv_tv, x="type", y="count", text="count", title=None)
        fig_type.update_traces(textposition="outside")
        st.plotly_chart(fig_type, use_container_width=True)

    with col2:
        st.subheader("Content Added Over Time")
        by_year_filtered = (
            df.loc[mask, ["year_added"]]
            .dropna()
            .groupby("year_added", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("year_added")
        )
        fig_year = px.line(by_year_filtered, x="year_added", y="count", markers=True)
        st.plotly_chart(fig_year, use_container_width=True)

    # Data quality note
    unparsed = df["date_added"].isna().sum()
    st.caption(f"Unparsed/blank dates: {unparsed}")

# ===== Countries =====
with tab2:
    st.subheader("Top Countries")
    top_countries_filtered = (
        df.loc[mask, ["country"]]
        .assign(country=lambda x: x["country"].str.split(","))
        .explode("country")
        .assign(country=lambda x: x["country"].str.strip())
    )
    top_countries_filtered = (
        top_countries_filtered[
            top_countries_filtered["country"].notna()
            & (top_countries_filtered["country"] != "Unknown")
        ]
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"country": "country"})
        .head(10)
    )
    fig_countries = px.bar(
        top_countries_filtered, x="country", y="count", text="count"
    )
    fig_countries.update_traces(textposition="outside")
    st.plotly_chart(fig_countries, use_container_width=True)

# ===== Genres =====
with tab3:
    st.subheader("Top Genres")
    top_genres_filtered = (
        df.loc[mask, ["listed_in"]]
        .assign(listed_in=lambda x: x["listed_in"].str.split(","))
        .explode("listed_in")
        .assign(genre=lambda x: x["listed_in"].str.strip())
        .drop(columns=["listed_in"])
    )
    top_genres_filtered = (
        top_genres_filtered[
            top_genres_filtered["genre"].notna()
            & (top_genres_filtered["genre"] != "Unknown")
        ]
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"genre": "genre"})
        .head(10)
    )
    fig_genres = px.bar(top_genres_filtered, x="genre", y="count", text="count")
    fig_genres.update_traces(textposition="outside")
    st.plotly_chart(fig_genres, use_container_width=True)

# ===== Footer =====
st.caption("Data: Netflix Titles (Kaggle). This is an educational project.")
