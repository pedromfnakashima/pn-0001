"""Gera os arquivos reduzidos da aba "Campo Grande" do dashboard (Deputado Estadual, MS 2026).

Fontes brutas (não versionadas; ver .gitignore):
  - TSE: votação por seção eleitoral 2026 (MS) e eleitorado por local de votação 2026 (MS),
    que traz latitude/longitude de cada local de votação;
  - IBGE: malhas intramunicipais do Censo 2022 (setores, bairros e subdistritos) de MS.

Cada local de votação (ponto) é atribuído ao setor censitário, bairro e subdistrito
(= Região Urbana) do IBGE que o contém (junção espacial ponto-em-polígono). Os votos são
somados por local de votação; as agregações por bairro/região são feitas no dashboard.

Rodar depois de preparar_dados_dashboard.py (usa o ranking estadual gerado por ele):
    conda activate llm_001
    python notebooks-e-python/preparar_dados_campo_grande.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_TSE = RAIZ / "dados/votacao_secao_2026_MS/votacao_secao_2026_MS.csv"
CSV_LOCAIS = RAIZ / "dados/eleitorado_local_votacao_2026/eleitorado_local_votacao_2026_MS.csv"
CSV_CORRESP = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"
CSV_VOTOS_MUN = RAIZ / "dados/app/votos_dep_estadual_ms_2026.csv"
DIR_IBGE = RAIZ / "dados/ibge-mapas-e-dados/censo_2022_intramunicipal"
SAIDA = RAIZ / "dados/app"

CD_IBGE_CG = "5002704"
CD_CARGO_DEP_ESTADUAL = 7
VOTOS_NAO_VALIDOS = {95, 96}  # branco, nulo
TOP_N = 50
TOLERANCIA_SIMPLIFICACAO_M = 15

corresp = pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str})
CD_TSE_CG = int(corresp.loc[corresp["CD_MUNICIPIO_IBGE"] == CD_IBGE_CG, "CD_MUNICIPIO_TSE"].iloc[0])

# --- Locais de votação (TSE) -------------------------------------------------
loc = pd.read_csv(CSV_LOCAIS, sep=";", encoding="latin1", decimal=",")
loc = loc[(loc["CD_MUNICIPIO"] == CD_TSE_CG) & (loc["NR_TURNO"] == 1)].copy()
# Seção agregada vota na urna da seção principal, que pode estar em outro prédio:
# seus eleitores passam a contar no local da principal.
local_secao = loc.set_index(["NR_ZONA", "NR_SECAO"])["NR_LOCAL_VOTACAO"]
agregada = loc["NR_SECAO_PRINCIPAL"] > 0
loc.loc[agregada, "NR_LOCAL_VOTACAO"] = local_secao.loc[
    list(zip(loc.loc[agregada, "NR_ZONA"], loc.loc[agregada, "NR_SECAO_PRINCIPAL"]))].values
loc = loc.sort_values("NR_SECAO_PRINCIPAL")  # principais (-1) primeiro: nome e coordenada vêm do prédio da urna
locais = (
    loc.groupby(["NR_ZONA", "NR_LOCAL_VOTACAO"], as_index=False)
    .agg(NM_LOCAL_VOTACAO=("NM_LOCAL_VOTACAO", "first"), DS_ENDERECO=("DS_ENDERECO", "first"),
         NM_BAIRRO_TSE=("NM_BAIRRO", "first"), LAT=("NR_LATITUDE", "first"), LON=("NR_LONGITUDE", "first"),
         QT_SECOES=("NR_SECAO", "nunique"), QT_ELEITORES=("QT_ELEITOR_SECAO", "sum"))
)
# O TSE usa -1 quando o local não tem coordenada.
sem_coord = (locais["LAT"] == -1) | locais["LAT"].isna()
locais.loc[sem_coord, ["LAT", "LON"]] = pd.NA

# --- Junção espacial com as malhas do IBGE ------------------------------------
def malha(nome: str) -> gpd.GeoDataFrame:
    g = gpd.read_file(f"zip://{DIR_IBGE / f'MS_{nome}_CD2022.zip'}")
    return g[g["CD_MUN"] == CD_IBGE_CG].to_crs(4326)


setores, bairros, subdist = malha("setores"), malha("bairros"), malha("subdistritos")
# Subdistritos sem nome: área rural do distrito-sede e distritos sem subdivisão (Anhanduí, Rochedinho).
subdist["NM_REGIAO"] = subdist["NM_SUBDIST"].fillna(
    subdist["NM_DIST"].map(lambda d: "Zona rural (distrito-sede)" if d == "Campo Grande" else f"Distrito de {d}")
)

pts = gpd.GeoDataFrame(locais, geometry=gpd.points_from_xy(locais["LON"], locais["LAT"]), crs=4326)
for camadas in (setores[["CD_SETOR", "geometry"]],
                bairros[["CD_BAIRRO", "NM_BAIRRO", "geometry"]],
                subdist[["CD_SUBDIST", "NM_REGIAO", "geometry"]]):
    pts = gpd.sjoin(pts, camadas, how="left", predicate="within").drop(columns="index_right")
# Coordenada fora de todos os subdistritos (imprecisão do ponto ou da malha): região mais próxima.
fora = pts["CD_SUBDIST"].isna() & pts["LAT"].notna()
if fora.any():
    prox = gpd.sjoin_nearest(pts.loc[fora, ["geometry"]].to_crs(5880),
                             subdist[["CD_SUBDIST", "NM_REGIAO", "geometry"]].to_crs(5880),
                             max_distance=5_000, distance_col="DIST_M")
    pts.loc[prox.index, ["CD_SUBDIST", "NM_REGIAO"]] = prox[["CD_SUBDIST", "NM_REGIAO"]].values
    print(f"{len(prox)} local(is) atribuído(s) à região mais próxima (até {prox['DIST_M'].max():.0f} m)")
for col in ("CD_SETOR", "CD_BAIRRO", "CD_SUBDIST"):
    pts[col] = pts[col].astype("string")
locais = pd.DataFrame(pts.drop(columns="geometry")).rename(
    columns={"NM_BAIRRO": "NM_BAIRRO_IBGE", "CD_BAIRRO": "CD_BAIRRO_IBGE",
             "CD_SUBDIST": "CD_REGIAO_IBGE", "NM_REGIAO": "NM_REGIAO_IBGE"}
)

# --- Votos por local de votação (TSE) -----------------------------------------
# A chave é zona + seção: quando um local é substituído, o arquivo de votação mantém o
# NR_LOCAL_VOTACAO original, enquanto o de eleitorado traz o local efetivo (com coordenadas).
cols = ["CD_CARGO", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_VOTAVEL", "QT_VOTOS"]
partes = []
for chunk in pd.read_csv(CSV_TSE, sep=";", encoding="latin1", usecols=cols, chunksize=500_000):
    chunk = chunk[(chunk["CD_CARGO"] == CD_CARGO_DEP_ESTADUAL) & (chunk["CD_MUNICIPIO"] == CD_TSE_CG)]
    partes.append(chunk.drop(columns=["CD_CARGO", "CD_MUNICIPIO"]))
votos = pd.concat(partes).merge(loc[["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]],
                                on=["NR_ZONA", "NR_SECAO"], how="left")
if votos["NR_LOCAL_VOTACAO"].isna().any():
    raise SystemExit("Há seções nos resultados sem cadastro no arquivo de eleitorado.")
chaves = ["NR_ZONA", "NR_LOCAL_VOTACAO", "NR_VOTAVEL"]
votos = votos.groupby(chaves, as_index=False)["QT_VOTOS"].sum()

validos = (votos[~votos["NR_VOTAVEL"].isin(VOTOS_NAO_VALIDOS)]
           .groupby(["NR_ZONA", "NR_LOCAL_VOTACAO"])["QT_VOTOS"].sum().rename("QT_VALIDOS"))
locais = locais.join(validos, on=["NR_ZONA", "NR_LOCAL_VOTACAO"]).fillna({"QT_VALIDOS": 0})
locais["QT_VALIDOS"] = locais["QT_VALIDOS"].astype(int)

# Mesmo critério de ranking da aba estadual: 50 candidatos mais votados em MS.
votos_mun = pd.read_csv(CSV_VOTOS_MUN)
top = (votos_mun[votos_mun["NR_VOTAVEL"] >= 1000].groupby("NR_VOTAVEL")["QT_VOTOS"].sum()
       .nlargest(TOP_N).index)
votos_top = votos[votos["NR_VOTAVEL"].isin(top)].sort_values(chaves)

# --- Malhas simplificadas para o mapa -----------------------------------------
def simplificar(g: gpd.GeoDataFrame, cols: list[str]) -> gpd.GeoDataFrame:
    g = g[cols + ["geometry"]].copy()
    g["geometry"] = g.to_crs(5880).simplify(TOLERANCIA_SIMPLIFICACAO_M).to_crs(4326)
    return g


SAIDA.mkdir(parents=True, exist_ok=True)
arquivos = {
    "cg_locais_votacao_2026.csv": locais,
    "cg_votos_top50_por_local_2026.csv": votos_top,
}
for nome, df in arquivos.items():
    df.to_csv(SAIDA / nome, index=False, encoding="utf-8")
simplificar(bairros.rename(columns={"CD_BAIRRO": "CD_BAIRRO_IBGE", "NM_BAIRRO": "NM_BAIRRO_IBGE"}),
            ["CD_BAIRRO_IBGE", "NM_BAIRRO_IBGE"]).to_file(
    SAIDA / "cg_bairros_ibge_2022.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)
simplificar(subdist.rename(columns={"CD_SUBDIST": "CD_REGIAO_IBGE", "NM_REGIAO": "NM_REGIAO_IBGE"}),
            ["CD_REGIAO_IBGE", "NM_REGIAO_IBGE"]).to_file(
    SAIDA / "cg_regioes_ibge_2022.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

print(f"Locais: {len(locais)} · sem coordenada: {int(sem_coord.sum())} · "
      f"fora de bairro IBGE: {int(locais['CD_BAIRRO_IBGE'].isna().sum())} · "
      f"fora de região: {int(locais['CD_REGIAO_IBGE'].isna().sum())}")
for nome in [*arquivos, "cg_bairros_ibge_2022.geojson", "cg_regioes_ibge_2022.geojson"]:
    print(f"  {(SAIDA / nome).stat().st_size / 1e3:8.0f} kB  {nome}")
