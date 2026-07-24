"""OpenSciMetrics Dashboard — interactive companion to the OSM preprint."""

import math
import os

from dash import Dash, Input, Output, callback, ctx, dash_table, dcc, html, no_update
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
# Threshold sliders
#
# Entity sizes span three to four orders of magnitude (100 to 95k articles, 1k
# to 3.6M works) and the thresholds worth setting all live near the bottom of
# that range. On a linear track the useful marks collapse into the first few
# percent and overprint each other, so the handle moves on a log10 scale and
# the marks are labelled with real counts. The paired number box carries the
# exact value, which the log position cannot express precisely.
# ---------------------------------------------------------------------------

# Candidate marks; only those strictly inside a slider's range are drawn. Scales
# reaching into the millions carry wider labels ("300K", "3.6M") and get whole
# decades, which still leaves them room to breathe once the row wraps narrow.
_HALF_DECADE_STEPS = [300, 1_000, 3_000, 10_000, 30_000, 100_000, 300_000]
_DECADE_STEPS = [1_000, 10_000, 100_000, 1_000_000]


def _mark_steps(max_val: int) -> list[int]:
    return _DECADE_STEPS if max_val >= 1_000_000 else _HALF_DECADE_STEPS


# Left end of each scale. 100 articles is the pipeline's minimum analysis
# threshold, so no entity falls below it and "All" there really is unfiltered.
_ARTICLE_FLOOR = 100
_WORKS_FLOOR = 1_000


def _fmt_count(v: int) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        return f"{round(v / 1_000)}K"
    return str(v)


def _log_marks(floor: int, max_val: int) -> dict[float, str]:
    """Marks evenly spread in log space, labelled with real counts."""
    marks = {math.log10(floor): "All"}
    for v in _mark_steps(max_val):
        if floor < v < max_val:
            marks[math.log10(v)] = _fmt_count(v)
    marks[math.log10(max_val)] = _fmt_count(max_val)
    return marks


def _to_log(value: int | None, floor: int, max_val: int) -> float:
    """Real count -> slider position. Anything at or below the floor parks the
    handle at the left end, which means 'no minimum'."""
    if not value or value <= floor:
        return math.log10(floor)
    return math.log10(min(value, max_val))


def _from_log(pos: float | None, floor: int, max_val: int) -> int:
    """Slider position -> real count, with the left end meaning 'no minimum'."""
    if pos is None:
        return 0
    value = round(10**pos)
    if value <= floor:
        return 0
    return min(value, max_val)


def _threshold_control(
    label: str,
    slider_id: str,
    value_id: str,
    floor: int,
    max_val: int,
    default: int,
) -> html.Div:
    """A log-scaled slider paired with a number box holding the exact value."""
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "13px"}),
            html.Div(
                [
                    html.Div(
                        dcc.Slider(
                            id=slider_id,
                            min=math.log10(floor),
                            max=math.log10(max_val),
                            value=_to_log(default, floor, max_val),
                            marks=_log_marks(floor, max_val),
                            step=0.01,
                            allow_direct_input=False,
                            updatemode="drag",
                            tooltip=None,
                        ),
                        style={"flex": "1", "minWidth": "200px"},
                    ),
                    dcc.Input(
                        id=value_id,
                        type="number",
                        value=default,
                        min=0,
                        max=max_val,
                        step=1,
                        debounce=True,
                        style={"width": "84px", "padding": "6px"},
                    ),
                ],
                style={"display": "flex", "gap": "12px", "alignItems": "center"},
            ),
        ],
        style={"minWidth": "320px", "flex": "1"},
    )


def _register_threshold_sync(slider_id: str, value_id: str, floor: int, max_val: int):
    """Keep slider and number box in step. Dash allows the cycle because both
    directions live in one callback; `no_update` on the untouched side stops it
    bouncing back."""

    @callback(
        Output(slider_id, "value"),
        Output(value_id, "value"),
        Input(slider_id, "value"),
        Input(value_id, "value"),
        prevent_initial_call=True,
    )
    def _sync(pos, boxed):
        if ctx.triggered_id == slider_id:
            return no_update, _from_log(pos, floor, max_val)
        clamped = min(max(boxed or 0, 0), max_val)
        return _to_log(clamped, floor, max_val), (
            clamped if clamped != boxed else no_update
        )


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _build_controls(
    prefix: str,
    min_default: int,
    max_val: int,
    *,
    works_threshold: bool = False,
    works_default: int = 0,
    works_max: int = 0,
) -> html.Div:
    """Build the controls row for a tab."""
    sliders = [
        _threshold_control(
            "Min articles",
            f"{prefix}-min-articles",
            f"{prefix}-min-articles-value",
            floor=_ARTICLE_FLOOR,
            max_val=max_val,
            default=min_default,
        ),
    ]
    if works_threshold:
        sliders.append(
            _threshold_control(
                "Min OpenAlex works",
                f"{prefix}-min-works",
                f"{prefix}-min-works-value",
                floor=_WORKS_FLOOR,
                max_val=works_max,
                default=works_default,
            )
        )

    return html.Div(
        style={
            "display": "flex",
            "gap": "24px",
            "alignItems": "flex-end",
            "flexWrap": "wrap",
            "marginBottom": "16px",
        },
        children=[
            *sliders,
            html.Div(
                [
                    html.Label(
                        "Search", style={"fontWeight": "bold", "fontSize": "13px"}
                    ),
                    dcc.Input(
                        id=f"{prefix}-search",
                        type="text",
                        placeholder="Filter by name...",
                        debounce=True,
                        style={"width": "200px", "padding": "6px"},
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(
                        "Sort by", style={"fontWeight": "bold", "fontSize": "13px"}
                    ),
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
                ]
            ),
            html.Div(
                [
                    dcc.Checklist(
                        id=f"{prefix}-show-correction",
                        options=[
                            {"label": " Show corrected estimates", "value": "show"}
                        ],
                        value=["show"],
                        style={"fontSize": "13px"},
                    ),
                ]
            ),
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
_funder_works_max = int(FUNDERS["aggregated_works_count"].max())
_journal_max = int(JOURNALS["total_articles"].max())

# Tabs render lazily, so these are registered up front against ids that only
# exist once their tab is open (suppress_callback_exceptions covers the gap).
_register_threshold_sync(
    "funder-min-articles", "funder-min-articles-value", _ARTICLE_FLOOR, _funder_max
)
_register_threshold_sync(
    "funder-min-works", "funder-min-works-value", _WORKS_FLOOR, _funder_works_max
)
_register_threshold_sync(
    "journal-min-articles", "journal-min-articles-value", _ARTICLE_FLOOR, _journal_max
)


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
    style={
        "maxWidth": "1400px",
        "margin": "0 auto",
        "padding": "20px",
        "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    children=[
        # Header
        html.H1("OpenSciMetrics", style={"marginBottom": "4px"}),
        html.P(
            [
                "Open data and code sharing rates across biomedical funders, journals, "
                "and institutions. Interactive companion to the ",
                html.A(
                    "Open Science Metrics",
                    href="https://github.com/nimh-dsst/open-science-metrics",
                    target="_blank",
                ),
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
        return html.Div(
            [
                _build_controls(
                    "funder",
                    min_default=2694,
                    max_val=_funder_max,
                    works_threshold=True,
                    works_default=100000,
                    works_max=_funder_works_max,
                ),
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
                    style_cell={
                        "textAlign": "left",
                        "padding": "8px",
                        "fontSize": "13px",
                    },
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
            ]
        )
    else:
        return html.Div(
            [
                _build_controls("journal", min_default=4262, max_val=_journal_max),
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
                    style_cell={
                        "textAlign": "left",
                        "padding": "8px",
                        "fontSize": "13px",
                    },
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
            ]
        )


@callback(
    Output("funder-chart", "figure"),
    Output("funder-table", "data"),
    Input("funder-min-articles-value", "value"),
    Input("funder-min-works-value", "value"),
    Input("funder-search", "value"),
    Input("funder-sort", "value"),
    Input("funder-show-correction", "value"),
)
def update_funder(min_articles, min_works, search, sort_by, show_correction):
    df = FUNDERS
    if search:
        # An explicit search bypasses the size thresholds: many funders named in
        # the paper (e.g. HHMI) fall below them, and silently returning nothing
        # reads as missing data rather than a filter.
        df = filter_by_search(df, search, "label")
    else:
        if min_articles:
            df = filter_by_min_articles(df, min_articles)
        if min_works:
            df = df[df["aggregated_works_count"] >= min_works]

    show_corr = "show" in (show_correction or [])
    fig = make_bar_chart(
        df,
        name_col="label",
        url_col="openalex_url",
        baseline_pct=METADATA["baseline_rates"]["funder_linked"],
        baseline_label="Funder-linked rate",
        show_correction=show_corr,
        title="Open Data Rates Among Major Funders",
        colorbar_label="Funder-Linked Articles",
        sort_by=sort_by,
    )
    return fig, df.to_dict("records")


@callback(
    Output("journal-chart", "figure"),
    Output("journal-table", "data"),
    Input("journal-min-articles-value", "value"),
    Input("journal-search", "value"),
    Input("journal-sort", "value"),
    Input("journal-show-correction", "value"),
)
def update_journal(min_articles, search, sort_by, show_correction):
    df = JOURNALS
    if search:
        # See update_funder: search bypasses the threshold so journals named in
        # the paper (e.g. Nature Genetics, 227 articles) remain findable.
        df = filter_by_search(df, search, "journal")
    elif min_articles:
        df = filter_by_min_articles(df, min_articles)

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
            // URL is the first element of the bar's customdata array
            if (Array.isArray(cd) && cd.length > 0) {
                var url = cd[0];
                if (typeof url === 'string' && url.startsWith('http')) {
                    window.open(url, '_blank');
                }
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
