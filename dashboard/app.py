"""OpenSciMetrics Dashboard — interactive companion to the OSM preprint."""

import os

from dash import Dash, Input, Output, callback, dash_table, dcc, html
from dash.dash_table.Format import Format, Scheme

from dashboard.charts import make_bar_chart
from dashboard.data import (
    FUNDERS,
    JOURNALS,
    METADATA,
    filter_by_min_articles,
    filter_by_search,
)

app = Dash(
    __name__,
    title="OpenSciMetrics Dashboard",
    update_title="Loading...",
    suppress_callback_exceptions=True,
)
server = app.server  # For gunicorn


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _build_controls(prefix: str, min_default: int, max_val: int) -> html.Div:
    """Build the controls row for a tab (min articles, search, sort, correction)."""
    return html.Div(
        style={"display": "flex", "gap": "24px", "alignItems": "flex-end",
               "flexWrap": "wrap", "marginBottom": "16px"},
        children=[
            html.Div([
                html.Label("Min articles", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Slider(
                    id=f"{prefix}-min-articles",
                    min=0,
                    max=max_val,
                    value=min_default,
                    marks={
                        0: "0",
                        100: "100",
                        500: "500",
                        1000: "1K",
                        2000: "2K",
                        5000: "5K",
                        10000: "10K",
                        max_val: f"{max_val // 1000}K" if max_val >= 1000 else str(max_val),
                    },
                    step=100,
                    tooltip={"placement": "bottom", "always_visible": False},
                ),
            ], style={"minWidth": "300px", "flex": "1"}),
            html.Div([
                html.Label("Search", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Input(
                    id=f"{prefix}-search",
                    type="text",
                    placeholder="Filter by name...",
                    debounce=True,
                    style={"width": "200px", "padding": "6px"},
                ),
            ]),
            html.Div([
                html.Label("Sort by", style={"fontWeight": "bold", "fontSize": "13px"}),
                dcc.Dropdown(
                    id=f"{prefix}-sort",
                    options=[
                        {"label": "Observed %", "value": "observed"},
                        {"label": "Corrected %", "value": "corrected"},
                        {"label": "Total articles", "value": "total"},
                        {"label": "Alphabetical", "value": "alphabetical"},
                    ],
                    value="observed",
                    clearable=False,
                    style={"width": "160px"},
                ),
            ]),
            html.Div([
                dcc.Checklist(
                    id=f"{prefix}-show-correction",
                    options=[{"label": " Show corrected estimates", "value": "show"}],
                    value=["show"],
                    style={"fontSize": "13px"},
                ),
            ]),
        ],
    )


def _build_table_columns(cols: list[dict]) -> list[dict]:
    """Format columns for dash_table with numeric formatting."""
    formatted = []
    for c in cols:
        col = {"name": c["name"], "id": c["id"]}
        if c.get("presentation"):
            col["presentation"] = c["presentation"]
        if c.get("type") == "numeric":
            col["type"] = "numeric"
            col["format"] = Format(precision=1, scheme=Scheme.fixed)
        formatted.append(col)
    return formatted


# ---------------------------------------------------------------------------
# Funder columns for the data table
# ---------------------------------------------------------------------------
FUNDER_TABLE_COLS = [
    {"name": "Funder", "id": "funder_link", "presentation": "markdown"},
    {"name": "Country", "id": "country"},
    {"name": "Articles", "id": "total_articles", "type": "numeric"},
    {"name": "Open Data", "id": "open_data_articles", "type": "numeric"},
    {"name": "Open Code", "id": "open_code_articles", "type": "numeric"},
    {"name": "OD %", "id": "open_data_pct", "type": "numeric"},
    {"name": "OC %", "id": "open_code_pct", "type": "numeric"},
    {"name": "Corrected %", "id": "corrected_pct", "type": "numeric"},
    {"name": "CI Low %", "id": "ci_lo_pct", "type": "numeric"},
    {"name": "CI High %", "id": "ci_hi_pct", "type": "numeric"},
]

JOURNAL_TABLE_COLS = [
    {"name": "Journal", "id": "journal"},
    {"name": "Articles", "id": "total_articles", "type": "numeric"},
    {"name": "Open Data", "id": "open_data_articles", "type": "numeric"},
    {"name": "Open Code", "id": "open_code_articles", "type": "numeric"},
    {"name": "OD %", "id": "open_data_pct", "type": "numeric"},
    {"name": "OC %", "id": "open_code_pct", "type": "numeric"},
    {"name": "Corrected %", "id": "corrected_pct", "type": "numeric"},
    {"name": "CI Low %", "id": "ci_lo_pct", "type": "numeric"},
    {"name": "CI High %", "id": "ci_hi_pct", "type": "numeric"},
]


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

_funder_max = int(FUNDERS["total_articles"].max())
_journal_max = int(JOURNALS["total_articles"].max())


def _build_footer() -> list:
    parts = []
    repo = os.environ.get("GIT_REPO", "")
    commit = os.environ.get("GIT_COMMIT", "")
    branch = os.environ.get("GIT_BRANCH", "")
    build_ts = os.environ.get("BUILD_TIMESTAMP", "")
    info = [p for p in [repo, branch, commit, build_ts] if p]
    if info:
        parts.append(f"Deploy: {' | '.join(info)}")
    parts.append(f"Data generated: {METADATA.get('data_generated', 'unknown')}")
    return [html.Span(p) for p in parts]


app.layout = html.Div(
    style={"maxWidth": "1400px", "margin": "0 auto", "padding": "20px",
           "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"},
    children=[
        # Header
        html.H1("OpenSciMetrics", style={"marginBottom": "4px"}),
        html.P(
            [
                "Open data and code sharing rates across biomedical funders, journals, "
                "and institutions. Interactive companion to the ",
                html.A("OSM preprint", href="https://github.com/nimh-dsst/osm-preprint-2026",
                       target="_blank"),
                f". Data: {METADATA['date_range']['from']} to {METADATA['date_range']['to']}.",
            ],
            style={"color": "#666", "marginBottom": "20px"},
        ),

        # Tabs
        dcc.Tabs(
            id="main-tabs",
            value="funders",
            children=[
                dcc.Tab(label="Funders", value="funders"),
                dcc.Tab(label="Journals", value="journals"),
            ],
        ),

        # Tab content
        html.Div(id="tab-content"),

        # Footer
        html.Hr(style={"marginTop": "40px"}),
        html.Div(
            style={"color": "#999", "fontSize": "12px", "textAlign": "center"},
            children=_build_footer(),
        ),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab: str):
    if tab == "funders":
        return html.Div([
            _build_controls("funder", min_default=2500, max_val=_funder_max),
            dcc.Graph(id="funder-chart"),
            html.H3("Funder Data", style={"marginTop": "24px"}),
            dash_table.DataTable(
                id="funder-table",
                columns=_build_table_columns(FUNDER_TABLE_COLS),
                sort_action="native",
                filter_action="native",
                export_format="csv",
                page_size=25,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            ),
        ])
    else:
        return html.Div([
            _build_controls("journal", min_default=1800, max_val=_journal_max),
            dcc.Graph(id="journal-chart"),
            html.H3("Journal Data", style={"marginTop": "24px"}),
            dash_table.DataTable(
                id="journal-table",
                columns=_build_table_columns(JOURNAL_TABLE_COLS),
                sort_action="native",
                filter_action="native",
                export_format="csv",
                page_size=25,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            ),
        ])


@callback(
    Output("funder-chart", "figure"),
    Output("funder-table", "data"),
    Input("funder-min-articles", "value"),
    Input("funder-search", "value"),
    Input("funder-sort", "value"),
    Input("funder-show-correction", "value"),
)
def update_funder(min_articles, search, sort_by, show_correction):
    df = FUNDERS
    if min_articles:
        df = filter_by_min_articles(df, min_articles)
    if search:
        df = filter_by_search(df, search, "label")

    show_corr = "show" in (show_correction or [])
    fig = make_bar_chart(
        df,
        name_col="label",
        url_col="openalex_url",
        baseline_pct=METADATA["baseline_rates"]["funded"],
        baseline_label="Funded baseline",
        show_correction=show_corr,
        title="Open Data Rates Among Major Funders",
        colorbar_label="Total Funded Articles",
        sort_by=sort_by,
    )
    return fig, df.to_dict("records")


@callback(
    Output("journal-chart", "figure"),
    Output("journal-table", "data"),
    Input("journal-min-articles", "value"),
    Input("journal-search", "value"),
    Input("journal-sort", "value"),
    Input("journal-show-correction", "value"),
)
def update_journal(min_articles, search, sort_by, show_correction):
    df = JOURNALS
    if min_articles:
        df = filter_by_min_articles(df, min_articles)
    if search:
        df = filter_by_search(df, search, "journal")

    show_corr = "show" in (show_correction or [])
    fig = make_bar_chart(
        df,
        name_col="journal",
        baseline_pct=METADATA["baseline_rates"]["overall"],
        baseline_label="Overall baseline",
        show_correction=show_corr,
        title="Open Data Rates Among Top Journals",
        colorbar_label="Total Articles",
        sort_by=sort_by,
    )
    return fig, df.to_dict("records")


# ---------------------------------------------------------------------------
# Click-to-open: navigate to OpenAlex when a funder bar is clicked
# ---------------------------------------------------------------------------

app.clientside_callback(
    """
    function(clickData) {
        if (clickData && clickData.points && clickData.points.length > 0) {
            var point = clickData.points[0];
            var cd = point.customdata;
            // Link markers store URL as a scalar string in customdata
            if (typeof cd === 'string' && cd.startsWith('http')) {
                window.open(cd, '_blank');
            }
        }
        return '';
    }
    """,
    Output("funder-chart", "className"),
    Input("funder-chart", "clickData"),
    prevent_initial_call=True,
)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8050)
