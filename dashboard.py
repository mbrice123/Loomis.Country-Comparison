import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# LOAD DATA
# =========================
df = pd.read_excel(
    r"L:\Dept\FIM\Shared\Global Macro\Sovereign Analysts, PMs\Mike B\country_dashboard\country_dashboard.xlsm",
    sheet_name="country_Data"
)

st.set_page_config(page_title="Country Comparison Dashboard", layout="wide")
st.title("Multi-Country Comparison Dashboard")

# =========================
# BASIC COLUMN SETUP
# =========================
required_cols = ["country", "year"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

# Assumes your new ratings column is called "rating"
# If it is named something slightly different (e.g. "Rating"), change it here
rating_col = "rating"
if rating_col not in df.columns:
    st.error(f"Missing rating column: {rating_col}")
    st.stop()

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

with col3:
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())
    start_year = st.number_input("Start Year:", value=min_year, min_value=min_year, max_value=max_year)
    end_year = st.number_input("End Year:", value=max_year, min_value=min_year, max_value=max_year)

# Optional rating override
all_ratings = sorted(df[rating_col].dropna().astype(str).unique().tolist())

# get anchor country's rating
country_rating_lookup = (
    df[["country", rating_col]]
    .dropna()
    .drop_duplicates(subset=["country"], keep="first")
)

anchor_rating_series = country_rating_lookup.loc[
    country_rating_lookup["country"] == country_1, rating_col
]

if len(anchor_rating_series) == 0:
    st.warning(f"No rating found for {country_1}.")
    selected_rating = None
else:
    selected_rating = str(anchor_rating_series.iloc[0])

rating_override = st.checkbox("Override anchor country rating bucket", value=False)

if rating_override:
    selected_rating = st.selectbox("Select Rating Bucket:", all_ratings, index=all_ratings.index(selected_rating) if selected_rating in all_ratings else 0)

# =========================
# FILTER SELECTED COUNTRIES
# =========================
selected = df[
    (df["country"].isin([country_1, country_2, country_3])) &
    (df["year"] >= start_year) &
    (df["year"] <= end_year)
].copy()

# =========================
# SMART CLEAN FUNCTION
# =========================
def smart_clean(vals_list):
    vals = list(vals_list)
    first_real = None
    last_real = None

    for i in range(len(vals)):
        if vals[i] is not None and not (isinstance(vals[i], float) and np.isnan(vals[i])) and vals[i] != 0 and vals[i] != 0.0:
            first_real = i
            break

    for i in range(len(vals) - 1, -1, -1):
        if vals[i] is not None and not (isinstance(vals[i], float) and np.isnan(vals[i])) and vals[i] != 0 and vals[i] != 0.0:
            last_real = i
            break

    if first_real is None or last_real is None:
        return [np.nan] * len(vals)

    for i in range(0, first_real):
        vals[i] = np.nan
    for i in range(last_real + 1, len(vals)):
        vals[i] = np.nan

    return vals

# =========================
# TIME SERIES CHART
# =========================
title = f"{country_1}, {country_2}, {country_3} - {variable} ({start_year}-{end_year})"
st.subheader(title)

fig = go.Figure()
colors = px.colors.qualitative.Plotly

for i, country in enumerate([country_1, country_2, country_3]):
    cdata = selected[selected["country"] == country].sort_values("year").copy()

    if cdata.empty:
        continue

    cleaned = smart_clean(cdata[variable].tolist())
    cdata[variable] = cleaned
    color = colors[i % len(colors)]

    hist = cdata[cdata["year"] <= 2026]
    proj = cdata[cdata["year"] >= 2026]

    if not hist.empty:
        fig.add_trace(
            go.Scatter(
                x=hist["year"],
                y=hist[variable],
                mode="lines+markers",
                name=country,
                line=dict(color=color, dash="solid"),
                connectgaps=False,
                legendgroup=country
            )
        )

    if not proj.empty and len(proj) > 1:
        fig.add_trace(
            go.Scatter(
                x=proj["year"],
                y=proj[variable],
                mode="lines+markers",
                name=f"{country} (projected)",
                line=dict(color=color, dash="dash"),
                connectgaps=False,
                legendgroup=country,
                showlegend=False
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
    text="--- Dashed lines indicate projected data (post-2026)",
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
# PIVOT TABLE
# =========================
pivot = selected.pivot(index="year", columns="country", values=variable)
st.dataframe(pivot, use_container_width=True)

# =========================
# RATING PEER DOT PLOT
# =========================
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

    peer_df = df[
        (df["country"].isin(peer_countries)) &
        (df["year"] >= start_year) &
        (df["year"] <= end_year)
    ].copy()

    if peer_df.empty:
        st.warning(
            "No peer data found for the selected rating bucket."
        )

    else:

        latest_peer_year = peer_df["year"].max()

        peer_latest = peer_df[
            peer_df["year"] == latest_peer_year
        ].copy()

        peer_latest = peer_latest.dropna(
            subset=[variable]
        )

        # ==================================
        # ADD ANCHOR COUNTRY IF MISSING
        # ==================================
# ==================================
# ADD ANCHOR COUNTRY IF MISSING
# ==================================

anchor_row = df[
    (df["country"] == country_1) &
    (df["year"] == latest_peer_year)
].copy()

anchor_row = anchor_row.dropna(
    subset=[variable]
)

if (
    not anchor_row.empty
    and country_1 not in peer_latest["country"].values
):
    peer_latest = pd.concat(
        [peer_latest, anchor_row],
        ignore_index=True
    )

if peer_latest.empty:

    st.warning(
        f"No {variable} data available "
        f"for {latest_peer_year}."
    )

else:

    # ==================================
    # SORT ENTIRE DATASET INCLUDING ANCHOR
    # ==================================

    peer_latest = (
        peer_latest
        .sort_values(variable, ascending=True)
        .reset_index(drop=True)
    )

    peer_latest["is_anchor"] = (
        peer_latest["country"] == country_1
    )

    fig_dot = go.Figure()

    # ==================================
    # NORMAL PEERS
    # ==================================

    peer_only = peer_latest[
        ~peer_latest["is_anchor"]
    ]

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
            hovertemplate=
                "<b>%{y}</b><br>"
                + variable +
                ": %{x}<extra></extra>"
        )
    )

    # ==================================
    # ANCHOR COUNTRY
    # ==================================

    anchor_plot = peer_latest[
        peer_latest["is_anchor"]
    ]

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
            name=f"{country_1} (Anchor)",
            hovertemplate=
                "<b>%{y}</b><br>"
                + variable +
                ": %{x}<extra></extra>"
        )
    )

    # ==================================
    # MEDIAN OF PEER GROUP ONLY
    # ==================================

    median_val = peer_only[variable].median()

    fig_dot.add_vline(
        x=median_val,
        line_dash="dash",
        line_color="gray",
        annotation_text="Median",
        annotation_position="top"
    )

    # ==================================
    # FORCE Y AXIS ORDER TO MATCH SORT
    # ==================================

    fig_dot.update_layout(
        title=(
            f"{selected_rating} Countries - "
            f"{variable} ({latest_peer_year})"
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

    st.plotly_chart(
        fig_dot,
        use_container_width=True
    )

    # ==================================
    # RANKING TABLE
    # ==================================

    st.markdown("### Peer Ranking Table")

    peer_table = (
        peer_latest[
            [
                "country",
                rating_col,
                "year",
                variable
            ]
        ]
        .sort_values(
            variable,
            ascending=False
        )
        .reset_index(drop=True)
    )

    peer_table.index += 1

    st.dataframe(
        peer_table,
        use_container_width=True
    )
        # =========================
# SAVE HTML COPY OF MAIN TIMESERIES FIGURE
# =========================
fig.write_html(
    r"L:\Dept\FIM\Shared\Global Macro\Sovereign Analysts, PMs\Mike B\country_dashboard\chart.html"
)
