"""Generate dual-bar horizontal charts matching the preprint figures.

Translates the matplotlib logic from osm-preprint-2026/scripts/table_funders.py
(lines 688-807) into Plotly graph_objects.
"""

import math

import numpy as np
import plotly.graph_objects as go


def _ylOrRd_color(t: float) -> str:
    """Approximate matplotlib YlOrRd colormap as an RGB string.

    t should be in [0, 1]. Returns 'rgb(r, g, b)'.
    """
    # Simplified YlOrRd: yellow (1,1,0.8) -> orange (1,0.55,0) -> dark red (0.5,0,0)
    if t < 0.5:
        s = t * 2  # 0..1 within first half
        r = 1.0
        g = 1.0 - 0.45 * s
        b = 0.8 - 0.8 * s
    else:
        s = (t - 0.5) * 2  # 0..1 within second half
        r = 1.0 - 0.5 * s
        g = 0.55 - 0.55 * s
        b = 0.0
    return f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"


def _log_normalize(values: np.ndarray) -> np.ndarray:
    """Log-normalize values to [0, 1] range."""
    vmin = max(values.min(), 1)
    vmax = values.max()
    if vmax <= vmin:
        return np.zeros_like(values, dtype=float)
    log_vals = np.log10(np.maximum(values, vmin))
    log_min = math.log10(vmin)
    log_max = math.log10(vmax)
    denom = log_max - log_min
    if denom == 0:
        return np.zeros_like(values, dtype=float)
    return (log_vals - log_min) / denom


def make_bar_chart(
    df,
    name_col: str,
    total_col: str = "total_articles",
    observed_col: str = "open_data_pct",
    corrected_col: str = "corrected_pct",
    ci_lo_col: str = "ci_lo_pct",
    ci_hi_col: str = "ci_hi_pct",
    url_col: str | None = None,
    baseline_pct: float | None = None,
    baseline_label: str = "",
    show_correction: bool = True,
    title: str = "",
    colorbar_label: str = "Total Articles",
    sort_by: str = "observed",
) -> go.Figure:
    """Build a horizontal dual-bar chart with optional correction overlay.

    Args:
        df: DataFrame with the summary data.
        name_col: Column for bar labels (y-axis).
        sort_by: One of 'observed', 'corrected', 'total', 'alphabetical'.
    """
    df = df.copy()

    # Sort
    if sort_by == "corrected" and corrected_col in df.columns:
        df = df.sort_values(corrected_col, ascending=True)
    elif sort_by == "total":
        df = df.sort_values(total_col, ascending=True)
    elif sort_by == "alphabetical":
        df = df.sort_values(name_col, ascending=False)
    else:  # default: observed
        df = df.sort_values(observed_col, ascending=True)

    labels = df[name_col].values
    observed = df[observed_col].values
    totals = df[total_col].values
    urls = df[url_col].values if url_col and url_col in df.columns else None

    # Colors from log-normalized totals
    norm_vals = _log_normalize(totals)
    colors = [_ylOrRd_color(t) for t in norm_vals]
    colors_light = [c.replace("rgb(", "rgba(").replace(")", ",0.35)") for c in colors]

    has_correction = (
        show_correction
        and corrected_col in df.columns
        and df[corrected_col].notna().any()
    )

    fig = go.Figure()

    if has_correction:
        corrected = df[corrected_col].values
        ci_lo = df[ci_lo_col].values
        ci_hi = df[ci_hi_col].values

        # Background bar: corrected estimate (lighter)
        fig.add_trace(go.Bar(
            y=labels,
            x=corrected,
            orientation="h",
            marker_color=colors_light,
            marker_line=dict(color="grey", width=0.3),
            error_x=dict(
                type="data",
                symmetric=False,
                array=ci_hi - corrected,
                arrayminus=corrected - ci_lo,
                color="black",
                thickness=0.8,
                width=2,
            ),
            name="Estimated (corrected)",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Corrected: %{x:.1f}%<br>"
                "CI: [%{customdata[0]:.1f}%, %{customdata[1]:.1f}%]"
                "<extra></extra>"
            ),
            customdata=np.column_stack([ci_lo, ci_hi]),
        ))

        # Foreground bar: observed (full opacity)
        fig.add_trace(go.Bar(
            y=labels,
            x=observed,
            orientation="h",
            marker_color=colors,
            marker_line=dict(color="grey", width=0.3),
            name="Observed",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Observed: %{x:.1f}%<br>"
                "Articles: %{customdata[0]:,}<br>"
                "Open data: %{customdata[1]:,}<br>"
                "Open code: %{customdata[2]:,}"
                "<extra></extra>"
            ),
            customdata=np.column_stack([
                totals,
                df["open_data_articles"].values,
                df["open_code_articles"].values,
            ]),
        ))

        max_val = max(ci_hi.max(), observed.max())
    else:
        # Single bar: observed only
        fig.add_trace(go.Bar(
            y=labels,
            x=observed,
            orientation="h",
            marker_color=colors,
            marker_line=dict(color="grey", width=0.3),
            name="Observed",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Observed: %{x:.1f}%<br>"
                "Articles: %{customdata[0]:,}"
                "<extra></extra>"
            ),
            customdata=np.column_stack([totals]),
        ))
        max_val = observed.max()

    # Add link icons just inside the left edge for items with a URL
    if urls is not None:
        link_urls_filtered = []
        link_y = []
        for label, url in zip(labels, urls):
            if url and isinstance(url, str) and url.startswith("http"):
                link_y.append(label)
                link_urls_filtered.append(url)
        if link_y:
            # Position at a small fixed x so they're visible inside the plot
            link_x = max_val * 0.005
            fig.add_trace(go.Scatter(
                x=[link_x] * len(link_y),
                y=link_y,
                mode="text",
                text=["🔗"] * len(link_y),
                textfont=dict(size=10),
                customdata=link_urls_filtered,
                hovertemplate="View on OpenAlex ↗<extra></extra>",
                showlegend=False,
            ))

    # Baseline reference line
    if baseline_pct is not None:
        fig.add_vline(
            x=baseline_pct,
            line_dash="dash",
            line_color="grey",
            opacity=0.7,
            annotation_text=f"{baseline_label}: {baseline_pct:.1f}%",
            annotation_position="top",
            annotation_font_size=11,
            annotation_font_color="grey",
        )

    n_items = len(df)
    fig.update_layout(
        barmode="overlay",
        title=dict(text=title, font_size=16),
        xaxis_title="% Articles with Open Data Statement",
        yaxis=dict(tickfont_size=10),
        height=max(500, 32 * n_items + 120),
        margin=dict(l=10, r=30, t=60, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(range=[0, max_val * 1.15 if max_val > 0 else 100]),
        template="plotly_white",
    )

    # Add a dummy scatter trace for the colorbar
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker=dict(
            size=0,
            colorscale="YlOrRd",
            cmin=math.log10(max(totals.min(), 1)),
            cmax=math.log10(totals.max()),
            colorbar=dict(
                title=colorbar_label,
                tickvals=[
                    math.log10(v) for v in [100, 1000, 10000, 100000]
                    if v <= totals.max()
                ],
                ticktext=[
                    str(v) for v in [100, 1000, 10000, 100000]
                    if v <= totals.max()
                ],
                len=0.5,
                y=0.5,
            ),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    return fig
