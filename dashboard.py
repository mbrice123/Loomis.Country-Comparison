import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# PAGE SETUP
# =========================
st.set_page_config(page_title="Country Comparison Dashboard", layout="wide")
st.title("Multi-Country Comparison Dashboard")

# =========================
# LOAD DATA
# =========================
df = pd.read_excel(
    "country_dashboard.xlsm",
    sheet_name="country_Data"
)

# =========================
# BASIC COLUMN SETUP
# =========================
required_cols = ["country", "year"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

rating_col = "rating"
if rating_col not in df.columns:
    st.error(f"Missing rating column: {rating_col}")
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"])
df["year"] = df["year"].astype(int)

countries = sorted(df["country"].dropna().unique().tolist())
excluded_cols = ["country", "year", "country_year_key", rating_col]
variables = [col for col in df.columns if col not in excluded_cols]

# =========================
# USER CONTROLS
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    country_1 = st.selectbox("Select Country 1:", countries, index=0)
    country_2 = st.selectbox("Select Country 2:", countries, index=1 if len(countries) > 1 else 0)
    country_3 = st.selectbox("Select Country 3:", countries, index=2 if len(countries) > 2 else 0)

with col2:
    variable = st.selectbox("Select Variable:", variables)
    treat_zero_as_missing = st.checkbox(
        "Treat 0 as missing data",
        value=True,
        help="Use this when blank Excel cells are showing up as zero in the dashboard."
    )

with col3:
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())
    start_year = st.number_input("Start Year:", value=min_year, min_value=min_year, max_value=max_year)
    end_year = st.number_input("End Year:", value=max_year, min_value=min_year, max_value=max_year)

# =========================
# CLEAN SELECTED VARIABLE
# =========================
def clean_numeric_series(series, treat_zero=True):
    cleaned = pd.to_numeric(series, errors="coerce")
    cleaned = cleaned.replace([np.inf, -np.inf], np.nan)

    if treat_zero:
        cleaned = cleaned.replace(0, np.nan)

    return cleaned

df[variable] = clean_numeric_series(df[variable], treat_zero=treat_zero_as_missing)

# =========================
# RATING SETUP
# =========================
all_ratings = sorted(df[rating_col].dropna().astype(str).unique().tolist())

country_rating_lookup = (
    df[["country", rating_col]]
    .dropna()
    .drop_duplicates(subset=["country"], keep="first")
)

anchor_rating_series = country_rating_lookup.loc[
    country_rating_lookup["country"] == country_1,
    rating_col
]

if len(anchor_rating_series) == 0:
    st.warning(f"No rating found for {country_1}.")
    selected_rating = None
else:
    selected_rating = str(anchor_rating_series.iloc[0])

rating_override = st.checkbox("Override anchor country rating bucket", value=False)

if rating_override:
    selected_rating = st.selectbox(
        "Select Rating Bucket:",
        all_ratings,
        index=all_ratings.index(selected_rating) if selected_rating in all_ratings else 0
    )

# =========================
# FILTER SELECTED COUNTRIES
# =========================
selected = df[
    (df["country"].isin([country_1, country_2, country_3])) &
    (df["year"] >= start_year) &
    (df["year"] <= end_year)
].copy()

# =========================
# TIME SERIES CHART
# =========================
title = f"{country_1}, {country_2}, {country_3} - {variable} ({start_year}-{end_year})"
st.subheader(title)

fig = go.Figure()
colors = px.colors.qualitative.Plotly

latest_notes = []

for i, country in enumerate([country_1, country_2, country_3]):
    cdata = selected[selected["country"] == country].sort_values("year").copy()

    if cdata.empty:
        latest_notes.append({
            "Country": country,
            "Latest Available Year": "No data",
            "Status": "No rows available in selected range"
        })
        continue

    cdata[variable] = clean_numeric_series(cdata[variable], treat_zero=treat_zero_as_missing)

    valid_cdata = cdata.dropna(subset=[variable]).copy()

    if valid_cdata.empty:
        latest_notes.append({
            "Country": country,
            "Latest Available Year": "No data",
            "Status": f"No usable {variable} data in selected range"
        })
        continue

    latest_year = int(valid_cdata["year"].max())

    if latest_year < end_year:
        latest_notes.append({
            "Country": country,
            "Latest Available Year": latest_year,
            "Status": f"Line stops at latest available value, not {end_year}"
        })
    else:
        latest_notes.append({
            "Country": country,
            "Latest Available Year": latest_year,
            "Status": "Current through selected end year"
        })

    color = colors[i % len(colors)]

    hist = valid_cdata[valid_cdata["year"] <= 2026]
    proj = valid_cdata[valid_cdata["year"] >= 2026]

    if not hist.empty:
        fig.add_trace(
            go.Scatter(
                x=hist["year"],
                y=hist[variable],
                mode="lines+markers",
                name=country,
                line=dict(color=color, dash="solid"),
                connectgaps=False,
                legendgroup=country,
                hovertemplate=
                    "<b>%{text}</b><br>" +
                    "Year: %{x}<br>" +
                    variable + ": %{y}<extra></extra>",
                text=[country] * len(hist)
            )
        )

    if not proj.empty and len(proj) > 1:
        fig.add_trace(
            go.Scatter(
                x=proj["year"],
                y=proj[variable],
                mode="lines+markers",
                name=f"{country} projected",
                line=dict(color=color, dash="dash"),
                connectgaps=False,
                legendgroup=country,
                showlegend=False,
                hovertemplate=
                    "<b>%{text}</b><br>" +
                    "Year: %{x}<br>" +
                    variable + ": %{y}<extra></extra>",
                text=[country] * len(proj)
            )
        )

fig.update_layout(
    xaxis_title="Year",
    yaxis_title=variable,
    legend_title="Country",
    template="plotly_white",
    xaxis=dict(showgrid=True, gridcolor="lightgray", dtick=5),
    yaxis=dict(showgrid=True, gridcolor="lightgray")
)

fig.add_annotation(
    text="Dashed lines indicate projected data from 2026 onward where available",
    xref="paper",
    yref="paper",
    x=1.0,
    y=-0.15,
    showarrow=False,
    font=dict(size=10, color="gray")
)

fig.add_annotation(
    text="Source: IMF, Oxford Economics, World Bank",
    xref="paper",
    yref="paper",
    x=0.0,
    y=-0.15,
    showarrow=False,
    font=dict(size=10, color="gray")
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# LATEST DATA AVAILABILITY
# =========================
st.markdown("### Latest Data Availability")
latest_notes_df = pd.DataFrame(latest_notes)
st.dataframe(latest_notes_df, use_container_width=True)

# =========================
# PIVOT TABLE
# =========================
pivot = selected.pivot(index="year", columns="country", values=variable)
st.dataframe(pivot, use_container_width=True)

# =========================
# RATING PEER DOT PLOT
# =========================
st.markdown("---")
st.subheader("Rating Peer Dot Plot")

if selected_rating is None:
    st.info("No rating available for the selected anchor country.")

else:
    st.write(
        f"Anchor country: **{country_1}** | "
        f"Peer bucket: **{selected_rating}**"
    )

    # -----------------------------------
    # Countries in selected rating bucket
    # -----------------------------------
    peer_countries = (
        df.loc[
            df[rating_col].astype(str) == selected_rating,
            "country"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    # Make sure anchor is included even if rating bucket logic misses it
    if country_1 not in peer_countries:
        peer_countries.append(country_1)

    peer_df = df[
        (df["country"].isin(peer_countries)) &
        (df["year"] >= start_year) &
        (df["year"] <= end_year)
    ].copy()

    if peer_df.empty:
        st.warning("No peer data found for the selected rating bucket.")

    else:
        peer_df[variable] = clean_numeric_series(peer_df[variable], treat_zero=treat_zero_as_missing)

        latest_rows = []
        missing_rows = []

        for country in sorted(peer_df["country"].dropna().unique()):
            cdata = peer_df[peer_df["country"] == country].sort_values("year").copy()
            valid = cdata.dropna(subset=[variable]).copy()

            if valid.empty:
                missing_rows.append({
                    "country": country,
                    rating_col: cdata[rating_col].dropna().iloc[0] if not cdata[rating_col].dropna().empty else "N/A",
                    "latest_available_year": "No data",
                    variable: "No usable data"
                })
                continue

            latest_row = valid.loc[valid["year"].idxmax()].copy()
            latest_rows.append(latest_row)

        peer_latest = pd.DataFrame(latest_rows)

        if peer_latest.empty:
            st.warning(
                f"No usable {variable} data available for this rating peer bucket "
                f"between {start_year} and {end_year}."
            )

            if len(missing_rows) > 0:
                st.markdown("### Countries With No Usable Data")
                st.dataframe(pd.DataFrame(missing_rows), use_container_width=True)

        else:
            peer_latest["is_anchor"] = peer_latest["country"] == country_1
            peer_latest["latest_available_year"] = peer_latest["year"].astype(int)

            peer_latest = (
                peer_latest
                .sort_values(variable, ascending=True)
                .reset_index(drop=True)
            )

            fig_dot = go.Figure()

            # ==================================
            # NORMAL PEERS
            # ==================================
            peer_only = peer_latest[~peer_latest["is_anchor"]].copy()

            fig_dot.add_trace(
                go.Scatter(
                    x=peer_only[variable],
                    y=peer_only["country"],
                    mode="markers",
                    marker=dict(
                        color="steelblue",
                        size=10
                    ),
                    name=f"{selected_rating} Peers",
                    customdata=peer_only[["latest_available_year"]],
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        variable + ": %{x}<br>" +
                        "Latest year: %{customdata[0]}" +
                        "<extra></extra>"
                )
            )

            # ==================================
            # ANCHOR COUNTRY
            # ==================================
            anchor_plot = peer_latest[peer_latest["is_anchor"]].copy()

            fig_dot.add_trace(
                go.Scatter(
                    x=anchor_plot[variable],
                    y=anchor_plot["country"],
                    mode="markers+text",
                    marker=dict(
                        color="red",
                        size=16,
                        line=dict(
                            color="black",
                            width=2
                        )
                    ),
                    text=anchor_plot["country"],
                    textposition="middle right",
                    name=f"{country_1} Anchor",
                    customdata=anchor_plot[["latest_available_year"]],
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        variable + ": %{x}<br>" +
                        "Latest year: %{customdata[0]}" +
                        "<extra></extra>"
                )
            )

            # ==================================
            # MEDIAN OF PEER GROUP ONLY
            # ==================================
            median_val = peer_only[variable].median()

            if pd.notna(median_val):
                fig_dot.add_vline(
                    x=median_val,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="Peer Median",
                    annotation_position="top"
                )

            # ==================================
            # FORCE Y AXIS ORDER TO MATCH SORT
            # ==================================
            fig_dot.update_layout(
                title=(
                    f"{selected_rating} Countries - "
                    f"{variable} using latest available country-level data"
                ),
                xaxis_title=variable,
                yaxis_title="Country",
                template="plotly_white",
                height=max(500, 25 * len(peer_latest)),
                yaxis=dict(
                    categoryorder="array",
                    categoryarray=peer_latest["country"].tolist()
                )
            )

            st.plotly_chart(fig_dot, use_container_width=True)

            # ==================================
            # RANKING TABLE
            # ==================================
            st.markdown("### Peer Ranking Table")

            peer_table = (
                peer_latest[
                    [
                        "country",
                        rating_col,
                        "latest_available_year",
                        variable
                    ]
                ]
                .sort_values(variable, ascending=False)
                .reset_index(drop=True)
            )

            peer_table.index += 1

            st.dataframe(peer_table, use_container_width=True)

            # ==================================
            # MISSING DATA TABLE
            # ==================================
            if len(missing_rows) > 0:
                st.markdown("### Countries With No Usable Data")
                missing_df = pd.DataFrame(missing_rows)
                st.dataframe(missing_df, use_container_width=True)

            st.caption(
                "Note: The dot plot uses each country's latest available non-missing value "
                "within the selected year range. This prevents missing future values from appearing as zero."
            )

# =========================
# SAVE HTML COPY OF MAIN TIMESERIES FIGURE
# =========================
fig.write_html("chart.html")
