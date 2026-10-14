
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================
# Configuration
# =========================================================

st.set_page_config(
    page_title="Singapore Air Quality Dashboard",
    page_icon="🌤️",
    layout="wide"
)

API_URL = "https://api-open.data.gov.sg/v2/real-time/api/pm25"

REGIONS = ["north", "south", "east", "west", "central"]

st.title("🌤️ Singapore PM2.5 Dashboard")
st.caption("Air quality data from data.gov.sg (NEA)")


# =========================================================
# Step 1: Fetch Data from API
# =========================================================

@st.cache_data(ttl=900)
def fetch_pm25(date=None):
    """
    Fetch PM2.5 readings from data.gov.sg.
    Cache the result for 15 minutes.
    """

    all_items = []
    pagination_token = None

    for _ in range(100):
        params = {}

        if date:
            params["date"] = str(date)

        if pagination_token:
            params["paginationToken"] = pagination_token

        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if result.get("code") != 0:
            raise ValueError(
                result.get("errorMsg", "API error")
            )

        data = result.get("data", {})

        all_items.extend(data.get("items", []))

        pagination_token = data.get("paginationToken")

        if not pagination_token:
            break

    else:
        raise ValueError(
            "Too many pages returned. Try another date."
        )

    return all_items


# =========================================================
# Step 2: Transform JSON into DataFrame
# =========================================================

def transform_data(items):

    records = []

    for item in items:

        timestamp = item.get("timestamp")

        readings = item.get(
            "readings", {}
        ).get("pm25_one_hourly", {})

        for region, value in readings.items():

            records.append({
                "Timestamp": timestamp,
                "Region": region.title(),
                "PM2.5": value
            })

    df = pd.DataFrame(
        records,
        columns=["Timestamp", "Region", "PM2.5"]
    )

    if not df.empty:
        df["Timestamp"] = pd.to_datetime(
            df["Timestamp"]
        )

        df = df.sort_values(
            ["Timestamp", "Region"]
        )

    return df


# =========================================================
# Step 3: Sidebar
# =========================================================

st.sidebar.header("⚙️ Dashboard Settings")

mode = st.sidebar.radio(
    "Select Data",
    ["Latest Readings", "Historical Readings"]
)

selected_date = None

if mode == "Historical Readings":

    selected_date = st.sidebar.date_input(
        "Select Date",
        value=datetime.now(
            ZoneInfo("Asia/Singapore")
        ).date(),
        max_value=datetime.now(
            ZoneInfo("Asia/Singapore")
        ).date()
    )

if st.sidebar.button("🔄 Refresh Data"):

    fetch_pm25.clear()
    st.rerun()


# =========================================================
# Step 4: Load Data
# =========================================================

try:

    with st.spinner("Fetching air quality data..."):

        items = fetch_pm25(selected_date)

        df = transform_data(items)

except requests.exceptions.RequestException as e:

    st.error(f"API request failed: {e}")
    st.stop()

except (ValueError, KeyError, TypeError) as e:

    st.error(f"Unable to process API data: {e}")
    st.stop()


if df.empty:

    st.warning("No air quality data available.")
    st.stop()


# =========================================================
# Step 5: Latest Reading
# =========================================================

latest_time = df["Timestamp"].max()

latest_df = df[
    df["Timestamp"] == latest_time
].copy()

st.subheader("📍 Regional Air Quality")

st.caption(
    f"Reading time: {latest_time.strftime('%d %b %Y, %I:%M %p %Z')}"
)

cols = st.columns(5)

for i, region in enumerate(REGIONS):

    regional_data = latest_df[
        latest_df["Region"] == region.title()
    ]

    if not regional_data.empty:

        value = regional_data.iloc[0]["PM2.5"]

        cols[i].metric(
            label=region.title(),
            value=f"{value} µg/m³"
        )


# =========================================================
# Step 6: Regional Bar Chart
# =========================================================

st.divider()

st.subheader("📊 PM2.5 by Region")

chart_data = latest_df.set_index("Region")[
    ["PM2.5"]
]

st.bar_chart(chart_data)


# =========================================================
# Step 7: Historical Trend Chart
# =========================================================

if mode == "Historical Readings":

    st.divider()

    st.subheader("📈 Historical PM2.5 Trend")

    trend_df = df.pivot_table(
        index="Timestamp",
        columns="Region",
        values="PM2.5"
    )

    st.line_chart(trend_df)


# =========================================================
# Step 8: Data Table
# =========================================================

st.divider()

st.subheader("📋 Air Quality Data")

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# Step 9: Download as CSV
# =========================================================

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="📥 Download CSV",
    data=csv,
    file_name="singapore_pm25.csv",
    mime="text/csv"
)


# =========================================================
# Footer
# =========================================================

st.divider()

st.caption(
    "Source: National Environment Agency (NEA), "
    "data.gov.sg | PM2.5 readings in µg/m³"
)
