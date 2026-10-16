"""Dashboard Streamlit: votação para Deputado Estadual em MS (Eleições 2026, 1º turno).

Abas: mapa por município (MS), mapa intramunicipal de Campo Grande e metodologia.

Executar (ambiente conda llm_001):
    conda activate llm_001
    streamlit run notebooks-e-python/dashboard_dep_estadual_ms_2026.py
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "dados/app"
CSV_VOTOS = APP / "votos_dep_estadual_ms_2026.csv"
CSV_CG_LOCAIS = APP / "cg_locais_votacao_2026.csv"
CSV_CG_VOTOS = APP / "cg_votos_top50_por_local_2026.csv"
GEOJSON_CG = {"bairro": APP / "cg_bairros_ibge_2022.geojson", "regiao": APP / "cg_regioes_ibge_2022.geojson"}
SHP_IBGE = RAIZ / "dados/ibge-mapas-e-dados/MS_Municipios_2025/MS_Municipios_2025.shp"
CSV_CORRESP = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"

VOTOS_NAO_VALIDOS = {95, 96}  # branco, nulo
TOP_N = 50
CD_IBGE_CG = "5002704"
CENTRO_CG = {"lat": -20.47, "lon": -54.62}

st.set_page_config(page_title="Dep. Estadual MS 2026", page_icon="🗳️", layout="wide")


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


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


@st.cache_data(show_spinner="Carregando dados de Campo Grande…")
def carregar_cg() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Locais de votação, votos do top 50 por local e malhas IBGE (gerados por preparar_dados_campo_grande.py)."""
    codigos = {c: str for c in ("CD_SETOR", "CD_BAIRRO_IBGE", "CD_REGIAO_IBGE")}
    locais = pd.read_csv(CSV_CG_LOCAIS, dtype=codigos)
    locais["NM_LOCAL"] = locais["NM_LOCAL_VOTACAO"] + " (Z" + locais["NR_ZONA"].astype(str) + ")"
    votos = pd.read_csv(CSV_CG_VOTOS)
    malhas = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in GEOJSON_CG.items()}
    return locais, votos, malhas["bairro"], malhas["regiao"]


votos = carregar_votos()
geojson, centro = carregar_malha()
cg_locais, cg_votos, geo_bairros, geo_regioes = carregar_cg()

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
    lambda r: f"{r.POSICAO}º · {r.NM_URNA} ({r.PARTIDO} {r.NR_VOTAVEL}) · {fmt(r.QT_VOTOS)} votos", axis=1
)

# --- Barra lateral -----------------------------------------------------------
st.sidebar.header("Filtros")
rotulo = st.sidebar.selectbox(f"Candidato (top {TOP_N} mais votados)", ranking["ROTULO"])
cand = ranking.loc[ranking["ROTULO"] == rotulo].iloc[0]
METRICAS = {
    "% dos votos válidos na área": "PCT_AREA",
    "Votos absolutos": "QT_VOTOS",
    "% da votação do candidato na abrangência": "PCT_CAND",
}
metrica_lbl = st.sidebar.radio("Métrica do mapa", list(METRICAS),
                               help="Área = município (aba MS) ou local/bairro/região (aba Campo Grande). "
                                    "Abrangência = estado (aba MS) ou Campo Grande (aba Campo Grande).")
metrica = METRICAS[metrica_lbl]
st.sidebar.caption(
    "Fonte: TSE – Votação por seção eleitoral 2026 (1º turno), Candidatos 2026 e Eleitorado por local de "
    "votação 2026; IBGE – Malha Municipal 2025 e malhas intramunicipais do Censo 2022. "
    "Votos válidos = nominais + legenda (exclui brancos e nulos)."
)

st.title("Deputado Estadual · Mato Grosso do Sul · Eleições 2026")
st.subheader(f"{cand['NM_URNA']} ({cand['NR_VOTAVEL']}) — {cand['PARTIDO']}")
st.caption(f"Nome civil: {cand['NM_VOTAVEL']} · {cand['POSICAO']}º mais votado no estado")

aba_ms, aba_cg, aba_met = st.tabs(["🗺️ MS por município", "🏙️ Campo Grande", "📘 Metodologia"])

# =============================================================================
# Aba 1 — MS por município
# =============================================================================
mun = pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str})[["CD_MUNICIPIO_IBGE", "NM_MUNICIPIO_IBGE"]]
dc = candidatos[candidatos["NR_VOTAVEL"] == cand["NR_VOTAVEL"]][["CD_MUNICIPIO_IBGE", "QT_VOTOS"]]
dc = mun.merge(dc, on="CD_MUNICIPIO_IBGE", how="left").fillna({"QT_VOTOS": 0})
dc = dc.join(validos_mun, on="CD_MUNICIPIO_IBGE")
dc["PCT_AREA"] = 100 * dc["QT_VOTOS"] / dc["VALIDOS_MUN"]
dc["PCT_CAND"] = 100 * dc["QT_VOTOS"] / cand["QT_VOTOS"]

with aba_ms:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Posição no estado", f"{cand['POSICAO']}º")
    k2.metric("Votos no estado", fmt(cand["QT_VOTOS"]))
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
            hover_data={"CD_MUNICIPIO_IBGE": False, "QT_VOTOS": ":,.0f", "PCT_AREA": ":.2f", "PCT_CAND": ":.2f"},
            labels={"QT_VOTOS": "Votos", "PCT_AREA": "% válidos no município", "PCT_CAND": "% do total do candidato"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=640, coloraxis_colorbar_title_text="")
        st.plotly_chart(fig, key="mapa_ms")
        st.caption(f"Cor: {metrica_lbl}")

    with col_tab:
        st.markdown("**Municípios ordenados por votos**")
        tab = (
            dc.sort_values("QT_VOTOS", ascending=False)
            [["NM_MUNICIPIO_IBGE", "QT_VOTOS", "PCT_AREA", "PCT_CAND"]]
            .rename(columns={"NM_MUNICIPIO_IBGE": "Município", "QT_VOTOS": "Votos",
                             "PCT_AREA": "% válidos mun.", "PCT_CAND": "% do total"})
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

# =============================================================================
# Aba 2 — Campo Grande (locais de votação, bairros e regiões do IBGE)
# =============================================================================
NIVEIS_CG = {
    "Locais de votação": ("NM_LOCAL", None, None),
    "Bairros (IBGE)": ("NM_BAIRRO_IBGE", "CD_BAIRRO_IBGE", geo_bairros),
    "Regiões Urbanas / distritos (IBGE)": ("NM_REGIAO_IBGE", "CD_REGIAO_IBGE", geo_regioes),
}

cl = cg_locais.merge(
    cg_votos[cg_votos["NR_VOTAVEL"] == cand["NR_VOTAVEL"]][["NR_ZONA", "NR_LOCAL_VOTACAO", "QT_VOTOS"]],
    on=["NR_ZONA", "NR_LOCAL_VOTACAO"], how="left",
).fillna({"QT_VOTOS": 0})
votos_cg = cl["QT_VOTOS"].sum()

with aba_cg:
    nivel = st.radio("Nível de agregação", list(NIVEIS_CG), horizontal=True)
    col_nome, col_cod, geo = NIVEIS_CG[nivel]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Votos em Campo Grande", fmt(votos_cg))
    k2.metric("Peso de Campo Grande", f"{100 * votos_cg / cand['QT_VOTOS']:.1f}%", "dos votos do candidato no estado",
              delta_color="off")
    k3.metric("% dos válidos em Campo Grande", f"{100 * votos_cg / cl['QT_VALIDOS'].sum():.2f}%")

    chaves = [col_cod, col_nome] if col_cod else ["NR_ZONA", "NR_LOCAL_VOTACAO", col_nome]
    extra = {"LAT": ("LAT", "first"), "LON": ("LON", "first"), "NM_BAIRRO_IBGE": ("NM_BAIRRO_IBGE", "first"),
             "NM_REGIAO_IBGE": ("NM_REGIAO_IBGE", "first")} if not col_cod else {}
    ag = (
        cl.dropna(subset=[chaves[0]])
        .groupby(chaves, as_index=False)
        .agg(QT_VOTOS=("QT_VOTOS", "sum"), QT_VALIDOS=("QT_VALIDOS", "sum"), QT_ELEITORES=("QT_ELEITORES", "sum"),
             QT_LOCAIS=("NR_LOCAL_VOTACAO", "size"), **extra)
    )
    ag["PCT_AREA"] = 100 * ag["QT_VOTOS"] / ag["QT_VALIDOS"]
    ag["PCT_CAND"] = 100 * ag["QT_VOTOS"] / votos_cg if votos_cg else 0.0
    melhor = ag.sort_values("QT_VOTOS", ascending=False).iloc[0]
    k4.metric(f"Maior votação ({nivel.split(' ')[0].lower()})", melhor[col_nome],
              f"{fmt(melhor['QT_VOTOS'])} votos", delta_color="off")

    hover = {"QT_VOTOS": ":,.0f", "PCT_AREA": ":.2f", "PCT_CAND": ":.2f", "QT_ELEITORES": ":,.0f"}
    rotulos = {"QT_VOTOS": "Votos", "PCT_AREA": "% válidos na área", "PCT_CAND": "% do total em CG",
               "QT_ELEITORES": "Eleitores aptos", "NM_BAIRRO_IBGE": "Bairro (IBGE)", "NM_REGIAO_IBGE": "Região (IBGE)"}
    contorno = [{"source": geo_regioes if col_cod is None else geo, "type": "line",
                 "color": "#6b7280", "line": {"width": 0.8}}]

    col_mapa, col_tab = st.columns([3, 2])
    with col_mapa:
        if col_cod is None:
            fig = px.scatter_map(
                ag, lat="LAT", lon="LON", size="QT_VOTOS", color=metrica, size_max=28,
                color_continuous_scale="Blues", map_style="carto-positron", center=CENTRO_CG, zoom=11,
                hover_name=col_nome, hover_data={**hover, "LAT": False, "LON": False,
                                                 "NM_BAIRRO_IBGE": True, "NM_REGIAO_IBGE": True},
                labels=rotulos,
            )
            fig.update_traces(marker=dict(sizemin=3))
        else:
            fig = px.choropleth_map(
                ag, geojson=geo, locations=col_cod, featureidkey=f"properties.{col_cod}", color=metrica,
                color_continuous_scale="Blues", map_style="carto-positron", center=CENTRO_CG, zoom=10.6,
                opacity=0.8, hover_name=col_nome, hover_data={**hover, col_cod: False}, labels=rotulos,
            )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=640, coloraxis_colorbar_title_text="",
                          map_layers=contorno)
        st.plotly_chart(fig, key="mapa_cg")
        st.caption(
            f"Cor: {metrica_lbl}"
            + (" · Tamanho do círculo: votos absolutos · Linhas: Regiões Urbanas (IBGE)" if col_cod is None else
               " · Áreas sem cor não têm local de votação (os votos são atribuídos ao local onde o eleitor vota)")
        )

    with col_tab:
        st.markdown(f"**{nivel} ordenados por votos**")
        tab = (
            ag.sort_values("QT_VOTOS", ascending=False)[[col_nome, "QT_VOTOS", "PCT_AREA", "PCT_CAND", "QT_LOCAIS"]]
            .rename(columns={col_nome: nivel.split(" (")[0], "QT_VOTOS": "Votos", "PCT_AREA": "% válidos",
                             "PCT_CAND": "% do total CG", "QT_LOCAIS": "Locais"})
        )
        if col_cod is None:
            tab = tab.drop(columns="Locais")
        st.dataframe(
            tab, hide_index=True, height=640, width="stretch",
            column_config={
                "Votos": st.column_config.NumberColumn(format="localized"),
                "% válidos": st.column_config.NumberColumn(format="%.2f%%"),
                "% do total CG": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0, max_value=max(float(tab["% do total CG"].max()), 0.01)),
            },
        )

    with st.expander("Votos do candidato por zona eleitoral (Campo Grande)"):
        zonas = cl.groupby("NR_ZONA", as_index=False).agg(
            Votos=("QT_VOTOS", "sum"), Validos=("QT_VALIDOS", "sum"), Locais=("NR_LOCAL_VOTACAO", "size"))
        zonas["% válidos"] = 100 * zonas["Votos"] / zonas["Validos"]
        st.dataframe(
            zonas.rename(columns={"NR_ZONA": "Zona", "Validos": "Votos válidos"}), hide_index=True, width="stretch",
            column_config={"Votos": st.column_config.NumberColumn(format="localized"),
                           "Votos válidos": st.column_config.NumberColumn(format="localized"),
                           "% válidos": st.column_config.NumberColumn(format="%.2f%%")},
        )

# =============================================================================
# Aba 3 — Metodologia
# =============================================================================
with aba_met:
    n_loc, n_sec, n_ele = len(cg_locais), int(cg_locais["QT_SECOES"].sum()), int(cg_locais["QT_ELEITORES"].sum())
    n_sem_bairro = int(cg_locais["CD_BAIRRO_IBGE"].isna().sum())

    st.markdown(f"""
### 1. Fontes de dados

| Base | Órgão | Uso no dashboard |
|---|---|---|
| Votação por seção eleitoral 2026 – MS (`votacao_secao_2026_MS`) | TSE | Votos por votável em cada seção (1º turno, cargo Deputado Estadual) |
| Candidatos 2026 – MS (`consulta_cand_2026_MS`) | TSE | Nome de urna e partido |
| Eleitorado por local de votação 2026 (`eleitorado_local_votacao_2026_MS`) | TSE | Local de votação de cada seção, endereço, **latitude/longitude** e eleitores aptos |
| Códigos oficiais de UF e municípios segundo o TSE e o IBGE (`municipio_tse_ibge`) | TSE | Correspondência entre códigos municipais |
| Malha Municipal 2025 – MS | IBGE | Mapa por município |
| Malhas intramunicipais do Censo 2022 – MS (setores, bairros, subdistritos) | IBGE | Mapa de Campo Grande |

### 2. Correspondência de códigos TSE × IBGE

O TSE identifica municípios com um código próprio de 5 dígitos (Campo Grande = `90514`), diferente do código
IBGE de 7 dígitos (Campo Grande = `5002704`). A tabela de correspondência
(`correspondencia_municipios_tse_ibge_MS.csv`) é gerada a partir da **tabela oficial do TSE** e
**verificada** por um segundo método independente: pareamento pelo nome do município normalizado (maiúsculas,
sem acentos e pontuação) entre o arquivo de votação do TSE e a malha do IBGE. O script interrompe a geração se
os dois métodos divergirem — para os 79 municípios de MS eles coincidem integralmente.

**Abaixo do município não existe código comum.** Zona, local de votação e seção são códigos do TSE; setor
censitário, bairro e subdistrito são códigos do IBGE. A ligação entre as duas hierarquias é **geográfica**:

```
TSE:  município (90514) ─ zona ─ local de votação (lat/lon) ─ seção ─ votos
                                        │
                              junção espacial (ponto-em-polígono)
                                        │
IBGE: município (5002704) ─ distrito ─ subdistrito (Região Urbana) ─ bairro ─ setor censitário
```

### 3. Ligação seção → local de votação

Os votos vêm por **seção**; as coordenadas, por **local de votação**. A chave usada é **zona + seção**, e o local
é o do cadastro de eleitorado. Motivo: quando um local é substituído (reforma, interdição etc.), o arquivo de
votação mantém o número do local *original*, enquanto o cadastro de eleitorado traz o local *efetivo* — o
prédio onde a urna de fato ficou. Seções agregadas (que votam na urna da seção principal) são contadas uma
única vez, pela seção principal.

### 4. Agregação geográfica em Campo Grande

1. Cada local de votação (ponto lat/lon do TSE) é cruzado com os polígonos do IBGE (Censo 2022): **setor
   censitário**, **bairro** (74 bairros oficiais) e **subdistrito**. Em Campo Grande os subdistritos do IBGE
   correspondem às **7 Regiões Urbanas** do município; fora delas há a zona rural do distrito-sede e os
   distritos de Anhanduí e Rochedinho.
2. Locais fora de todos os polígonos (imprecisão da coordenada ou da malha) são atribuídos à região mais
   próxima, até 5 km.
3. Os votos são somados por local → bairro → região. Os percentuais usam como denominador os **votos válidos
   (nominais + legenda) para Deputado Estadual** na mesma área.

Situação atual: **{n_loc} locais de votação**, **{fmt(n_sec)} seções**, **{fmt(n_ele)} eleitores aptos**;
{n_loc - n_sem_bairro} locais dentro de um bairro do IBGE e {n_sem_bairro} na zona rural ou em distritos (sem bairro).

### 5. Limitações

- **Local de votação ≠ residência.** O mapa mostra onde o eleitor vota, não onde mora. Em geral se vota perto
  de casa, mas há exceções (mudanças de endereço sem transferência do título, por exemplo).
- **Zonas eleitorais não coincidem com bairros ou regiões** (ver tabela abaixo). Por isso a agregação parte do
  local de votação, e não da zona.
- **Áreas sem local de votação** ficam sem cor no mapa de bairros; seus moradores votam em locais vizinhos.
- Os bairros do IBGE seguem a lei municipal, com limites aproximados aos setores censitários; podem diferir
  levemente do desenho da Prefeitura.
- Coordenadas são informadas pelos cartórios eleitorais e podem conter imprecisões pontuais.

### 6. Reprodução

```bash
conda activate llm_001
python notebooks-e-python/gerar_correspondencia_tse_ibge_ms.py   # tabela TSE × IBGE (verificada)
python notebooks-e-python/preparar_dados_dashboard.py            # votos por município
python notebooks-e-python/preparar_dados_campo_grande.py         # locais, votos por local e malhas de CG
```
Os arquivos brutos (centenas de MB) não são versionados; o dashboard usa apenas os arquivos reduzidos em
`dados/app/` (< 1,5 MB no total).
""")

    st.markdown("#### Eleitores aptos por Região (IBGE) × zona eleitoral — Campo Grande")
    cruz = pd.crosstab(cg_locais["NM_REGIAO_IBGE"], cg_locais["NR_ZONA"], values=cg_locais["QT_ELEITORES"],
                       aggfunc="sum", margins=True, margins_name="Total").fillna(0).astype(int)
    cruz.columns = [f"Zona {c}" if c != "Total" else c for c in cruz.columns]
    st.dataframe(cruz, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="localized") for c in cruz.columns})

    with st.expander(f"Locais de votação de Campo Grande ({n_loc}) e atribuição geográfica"):
        st.dataframe(
            cg_locais[["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "NM_BAIRRO_TSE", "NM_BAIRRO_IBGE",
                       "NM_REGIAO_IBGE", "CD_SETOR", "QT_SECOES", "QT_ELEITORES"]]
            .rename(columns={"NR_ZONA": "Zona", "NR_LOCAL_VOTACAO": "Nº local", "NM_LOCAL_VOTACAO": "Local",
                             "NM_BAIRRO_TSE": "Bairro (TSE)", "NM_BAIRRO_IBGE": "Bairro (IBGE)",
                             "NM_REGIAO_IBGE": "Região (IBGE)", "CD_SETOR": "Setor censitário",
                             "QT_SECOES": "Seções", "QT_ELEITORES": "Eleitores"}),
            hide_index=True, width="stretch",
        )
        st.caption("O bairro informado pelo TSE é texto livre do cartório e não segue a divisão oficial; "
                   "por isso o bairro do IBGE é obtido pela coordenada.")

    with st.expander("Tabela de correspondência TSE × IBGE (municípios de MS)"):
        st.dataframe(pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str}), hide_index=True, width="stretch")
