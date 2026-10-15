"""Dashboard Streamlit: votação para Deputado Estadual em MS (Eleições 2026, 1º turno) por município.

Executar (ambiente conda llm_001):
    conda activate llm_001
    streamlit run notebooks-e-python/dashboard_dep_estadual_ms_2026.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
CSV_VOTOS = RAIZ / "dados/app/votos_dep_estadual_ms_2026.csv"
SHP_IBGE = RAIZ / "dados/ibge-mapas-e-dados/MS_Municipios_2025/MS_Municipios_2025.shp"
CSV_CORRESP = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"

VOTOS_NAO_VALIDOS = {95, 96}  # branco, nulo
TOP_N = 50

st.set_page_config(page_title="Dep. Estadual MS 2026", page_icon="🗳️", layout="wide")


@st.cache_data(show_spinner="Carregando votação…")
def carregar_votos() -> pd.DataFrame:
    """Votos para Deputado Estadual por município e votável (gerado por preparar_dados_dashboard.py)."""
    return pd.read_csv(CSV_VOTOS, dtype={"CD_MUNICIPIO_IBGE": str})


@st.cache_data(show_spinner="Carregando malha municipal do IBGE…")
def carregar_malha() -> tuple[dict, pd.DataFrame]:
    gdf = gpd.read_file(SHP_IBGE)[["CD_MUN", "NM_MUN", "geometry"]]
    # Simplifica a geometria (~100 m) para deixar o mapa leve no navegador.
    gdf["geometry"] = gdf.to_crs(5880).simplify(100).to_crs(4326)
    centro = gdf.to_crs(5880).dissolve().centroid.to_crs(4326).iloc[0]
    return gdf.set_index("CD_MUN").__geo_interface__, pd.DataFrame({"lat": [centro.y], "lon": [centro.x]})


votos = carregar_votos()
geojson, centro = carregar_malha()

validos_mun = (
    votos[~votos["NR_VOTAVEL"].isin(VOTOS_NAO_VALIDOS)]
    .groupby("CD_MUNICIPIO_IBGE")["QT_VOTOS"].sum().rename("VALIDOS_MUN")
)
candidatos = votos[votos["NR_VOTAVEL"] >= 1000]
ranking = (
    candidatos.groupby(["NR_VOTAVEL", "SQ_CANDIDATO"], as_index=False)
    .agg(QT_VOTOS=("QT_VOTOS", "sum"), NM_URNA=("NM_URNA_CANDIDATO", "first"),
         NM_VOTAVEL=("NM_VOTAVEL", "first"), PARTIDO=("SG_PARTIDO", "first"))
    .sort_values("QT_VOTOS", ascending=False).head(TOP_N).reset_index(drop=True)
)
ranking["POSICAO"] = ranking.index + 1
ranking["NM_URNA"] = ranking["NM_URNA"].fillna(ranking["NM_VOTAVEL"])
ranking["PARTIDO"] = ranking["PARTIDO"].fillna("—")
ranking["ROTULO"] = ranking.apply(
    lambda r: f"{r.POSICAO}º · {r.NM_URNA} ({r.PARTIDO} {r.NR_VOTAVEL}) · {r.QT_VOTOS:,.0f} votos".replace(",", "."),
    axis=1,
)

# --- Barra lateral -----------------------------------------------------------
st.sidebar.header("Filtros")
rotulo = st.sidebar.selectbox(f"Candidato (top {TOP_N} mais votados)", ranking["ROTULO"])
cand = ranking.loc[ranking["ROTULO"] == rotulo].iloc[0]
METRICAS = {
    "% dos votos válidos no município": "PCT_MUN",
    "Votos absolutos": "QT_VOTOS",
    "% da votação total do candidato": "PCT_CAND",
}
metrica_lbl = st.sidebar.radio("Métrica do mapa", list(METRICAS))
metrica = METRICAS[metrica_lbl]
st.sidebar.caption(
    "Fonte: TSE – Votação por seção eleitoral 2026 (1º turno) e Candidatos 2026; IBGE – Malha Municipal 2025. "
    "Votos válidos = nominais + legenda (exclui brancos e nulos)."
)

# --- Dados do candidato por município ---------------------------------------
mun = pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str})[["CD_MUNICIPIO_IBGE", "NM_MUNICIPIO_IBGE"]]
dc = candidatos[candidatos["NR_VOTAVEL"] == cand["NR_VOTAVEL"]][["CD_MUNICIPIO_IBGE", "QT_VOTOS"]]
dc = mun.merge(dc, on="CD_MUNICIPIO_IBGE", how="left").fillna({"QT_VOTOS": 0})
dc = dc.join(validos_mun, on="CD_MUNICIPIO_IBGE")
dc["PCT_MUN"] = 100 * dc["QT_VOTOS"] / dc["VALIDOS_MUN"]
dc["PCT_CAND"] = 100 * dc["QT_VOTOS"] / cand["QT_VOTOS"]

# --- Layout -----------------------------------------------------------------
st.title("Deputado Estadual · Mato Grosso do Sul · Eleições 2026")
st.subheader(f"{cand['NM_URNA']} ({cand['NR_VOTAVEL']}) — {cand['PARTIDO']}")
st.caption(f"Nome civil: {cand['NM_VOTAVEL']}")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Posição no estado", f"{cand['POSICAO']}º")
k2.metric("Votos no estado", f"{cand['QT_VOTOS']:,.0f}".replace(",", "."))
k3.metric("Municípios com voto", f"{(dc['QT_VOTOS'] > 0).sum()} de {len(dc)}")
top_mun = dc.sort_values("QT_VOTOS", ascending=False).iloc[0]
k4.metric("Maior votação", top_mun["NM_MUNICIPIO_IBGE"], f"{top_mun['PCT_CAND']:.1f}% do total", delta_color="off")

col_mapa, col_tab = st.columns([3, 2])
with col_mapa:
    fig = px.choropleth_map(
        dc, geojson=geojson, locations="CD_MUNICIPIO_IBGE", color=metrica,
        color_continuous_scale="Blues", map_style="carto-positron",
        center={"lat": centro.lat[0], "lon": centro.lon[0]}, zoom=5.3, opacity=0.85,
        hover_name="NM_MUNICIPIO_IBGE",
        hover_data={"CD_MUNICIPIO_IBGE": False, "QT_VOTOS": ":,.0f", "PCT_MUN": ":.2f", "PCT_CAND": ":.2f"},
        labels={"QT_VOTOS": "Votos", "PCT_MUN": "% válidos no município", "PCT_CAND": "% do total do candidato"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=640, coloraxis_colorbar_title_text="")
    st.plotly_chart(fig)
    st.caption(f"Cor: {metrica_lbl}")

with col_tab:
    st.markdown("**Municípios ordenados por votos**")
    tab = (
        dc.sort_values("QT_VOTOS", ascending=False)
        [["NM_MUNICIPIO_IBGE", "QT_VOTOS", "PCT_MUN", "PCT_CAND"]]
        .rename(columns={"NM_MUNICIPIO_IBGE": "Município", "QT_VOTOS": "Votos",
                         "PCT_MUN": "% válidos mun.", "PCT_CAND": "% do total"})
    )
    st.dataframe(
        tab, hide_index=True, height=640, width="stretch",
        column_config={
            "Votos": st.column_config.NumberColumn(format="localized"),
            "% válidos mun.": st.column_config.NumberColumn(format="%.2f%%"),
            "% do total": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=float(tab["% do total"].max())),
        },
    )

with st.expander(f"Ranking dos {TOP_N} candidatos mais votados"):
    st.dataframe(
        ranking[["POSICAO", "NM_URNA", "NR_VOTAVEL", "PARTIDO", "QT_VOTOS"]]
        .rename(columns={"POSICAO": "#", "NM_URNA": "Candidato", "NR_VOTAVEL": "Número",
                         "PARTIDO": "Partido", "QT_VOTOS": "Votos"}),
        hide_index=True, width="stretch",
        column_config={"Votos": st.column_config.NumberColumn(format="localized"),
                       "Número": st.column_config.NumberColumn(format="%d")},
    )
