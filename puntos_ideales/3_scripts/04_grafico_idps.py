"""
Grid interactivo 5x2 (anio x metodo) de los puntos ideales de idps_py/idps.csv,
con Plotly: hover (nombre + idp, +- sd en Bayes) y zoom/pan nativos.

El signo de idp_pca es arbitrario por anio (lo decide sklearn, no los datos);
se reorienta por anio contra idp_bayes (que ya viene fijado contra legisladores
de referencia de izquierda/derecha en 03_puntos_ideales.py) usando el signo de
su correlacion, igual que hacia orientar_pca() en index.html.

Uso: python 04_grafico_idps.py
Salida: ../index.html (esqueleto minimo) + ../idps_data.js (los datos de los
10 paneles); plotly.js se carga desde CDN, asi que hace falta internet para
abrirlo. index.html referencia a idps_data.js por nombre de archivo: los dos
tienen que viajar juntos.
"""

import math
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

AQUI = Path(__file__).parent
CSV = AQUI / "idps_py" / "idps.csv"
OUT_HTML = AQUI.parent / "index.html"
OUT_DATA = AQUI.parent / "idps_data.js"

IZQUIERDA, DERECHA = "#2a78d6", "#e34948"
WHISKER, BASELINE, GRID = "#898781", "#c3c2b7", "#e1e0d9"
SURFACE, PAGE = "#fcfcfb", "#f9f9f7"
TEXT, TEXT2, MUTED = "#0b0b0b", "#52514e", "#898781"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def orientar_pca(df):
    """Mismo criterio que corregir_signo_idps() en R / orientPca() en el JS viejo:
    si idp_pca correlaciona negativo con idp_bayes ese anio, se invierte el signo."""
    df = df.copy()
    for anio, g in df.groupby("anio"):
        r = g["idp_pca"].corr(g["idp_bayes"])
        if r is not None and r < 0:
            df.loc[g.index, "idp_pca"] = -df.loc[g.index, "idp_pca"]
    return df


def panel(fig, row, col, nombres, valores, sd=None):
    orden = valores.argsort()
    v, nom = valores.to_numpy()[orden], nombres.to_numpy()[orden]
    colores = [DERECHA if x >= 0 else IZQUIERDA for x in v]
    kw = dict(
        x=v,
        y=list(range(len(v))),
        orientation="h",
        marker=dict(color=colores, line=dict(width=0)),
        showlegend=False,
        hoverlabel=dict(bgcolor=TEXT, font_color=SURFACE, font_size=12),
    )
    if sd is not None:
        s = sd.to_numpy()[orden]
        kw["error_x"] = dict(type="data", array=s, color=WHISKER, thickness=1, width=0)
        kw["customdata"] = list(zip(nom, s))
        kw["hovertemplate"] = "<b>%{customdata[0]}</b><br>idp = %{x:.2f} (±%{customdata[1]:.2f})<extra></extra>"
    else:
        kw["customdata"] = nom
        kw["hovertemplate"] = "<b>%{customdata}</b><br>idp = %{x:.2f}<extra></extra>"
    fig.add_trace(go.Bar(**kw), row=row, col=col)


def main():
    df = pd.read_csv(CSV)
    df = orientar_pca(df)
    anios = sorted(df["anio"].unique())

    bayes_domain = math.ceil((df["idp_bayes"].abs() + df["sd_bayes"]).max() * 10) / 10
    pca_domain = 1.08

    fig = make_subplots(
        rows=len(anios), cols=2,
        column_titles=["Bayes · media posterior", "PCA · reescalado a [-1, 1], orientado contra Bayes"],
        row_titles=[str(a) for a in anios],
        horizontal_spacing=0.05, vertical_spacing=0.025,
    )

    for i, anio in enumerate(anios, start=1):
        g = df[df["anio"] == anio]
        panel(fig, i, 1, g["nombre"], g["idp_bayes"], sd=g["sd_bayes"])
        gp = g.dropna(subset=["idp_pca"])
        panel(fig, i, 2, gp["nombre"], gp["idp_pca"])

    # leyenda compartida: trazas invisibles, una sola vez
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                              marker=dict(size=10, color=IZQUIERDA),
                              name="Izquierda (idp < 0)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                              marker=dict(size=10, color=DERECHA),
                              name="Derecha (idp > 0)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                              line=dict(color=WHISKER, width=2),
                              name="± 1 desvio (incertidumbre, solo Bayes)"), row=1, col=1)

    for i in range(1, len(anios) + 1):
        fig.update_xaxes(range=[-bayes_domain, bayes_domain], zeroline=True,
                          zerolinecolor=BASELINE, zerolinewidth=1, gridcolor=GRID,
                          tickfont=dict(size=10, color=MUTED), row=i, col=1)
        fig.update_xaxes(range=[-pca_domain, pca_domain], zeroline=True,
                          zerolinecolor=BASELINE, zerolinewidth=1, gridcolor=GRID,
                          tickfont=dict(size=10, color=MUTED), row=i, col=2)
        for c in (1, 2):
            fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False,
                              autorange="reversed", row=i, col=c)

    fig.update_annotations(font=dict(size=13, color=TEXT2))
    for ann in fig.layout.annotations:
        if ann.text in [str(a) for a in anios]:
            ann.font = dict(size=15, color=TEXT)

    fig.update_layout(
        title=dict(text="Puntos ideales · Camara de Diputados, 2022–2026", x=0.01,
                   font=dict(size=20, color=TEXT, family=FONT)),
        font=dict(family=FONT, color=TEXT),
        paper_bgcolor=PAGE, plot_bgcolor=SURFACE,
        height=1500, width=1150,
        margin=dict(l=70, r=20, t=110, b=30),
        legend=dict(x=1.0, y=1.0, xanchor="left", yanchor="top", font=dict(size=11)),
        bargap=0.1,
    )

    # el <script src="https://cdn.plot.ly/..."> con el hash de integridad que
    # corresponde a esta version de plotly: se lo pedimos a la propia libreria
    # en vez de hardcodear la URL, para no desincronizarla si se actualiza plotly.
    cdn_html = pio.to_html(fig, include_plotlyjs="cdn", full_html=True)
    cdn_tag = re.search(r'<script charset="utf-8" src="https://cdn\.plot\.ly/[^>]*></script>', cdn_html).group(0)

    fig_json = pio.to_json(fig, remove_uids=True, pretty=True)
    OUT_DATA.write_text(f"const IDPS_FIGURE = {fig_json};\n", encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Puntos ideales · Diputados 2022-2026</title>
{cdn_tag}
</head>
<body style="margin:0">
<div id="graph" style="width:100%; height:100vh"></div>
<script src="idps_data.js"></script>
<script>
  Plotly.newPlot("graph", IDPS_FIGURE.data, IDPS_FIGURE.layout,
    {{displaylogo: false, scrollZoom: false}});
</script>
</body>
</html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")
    print("guardado:", OUT_HTML, f"({OUT_HTML.stat().st_size / 1e3:.1f} KB)")
    print("guardado:", OUT_DATA, f"({OUT_DATA.stat().st_size / 1e3:.0f} KB) · plotly.js desde CDN, requiere internet")


if __name__ == "__main__":
    main()
