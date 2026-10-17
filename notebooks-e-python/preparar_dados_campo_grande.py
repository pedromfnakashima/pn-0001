"""Gera os arquivos reduzidos da aba "Campo Grande" do dashboard (Deputado Estadual, MS 2026).

Fontes brutas (não versionadas; ver .gitignore):
  - TSE: votação por seção eleitoral 2026 (MS) e eleitorado por local de votação 2026 (MS),
    que traz latitude/longitude de cada local de votação;
  - IBGE: malhas intramunicipais do Censo 2022 (setores, bairros e subdistritos) de MS.

Cada local de votação (ponto) é atribuído ao setor censitário, bairro e subdistrito
(= Região Urbana) do IBGE que o contém (junção espacial ponto-em-polígono). Os votos são
somados por local de votação; as agregações por bairro/região são feitas no dashboard.

Para a comparação 2026 − 2022, a votação de 2022 (mesmos candidatos, identificados pelo CPF,
em qualquer cargo com votação própria) é redistribuída nos locais de 2026 pela chave
zona + seção; seções extintas vão para o local de 2026 mais próximo do seu local de 2022.

Rodar depois de preparar_dados_dashboard.py e preparar_dados_ms_2022.py:
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
CSV_CAND_PARES = RAIZ / "dados/app/candidatos_2022.csv"
CSV_TSE_2022 = RAIZ / "dados/votacao_secao_2022_MS/votacao_secao_2022_MS.csv"
CSV_LOCAIS_2022 = RAIZ / "dados/eleitorado_local_votacao_2022/eleitorado_local_votacao_2022_MS.csv"
DIR_IBGE = RAIZ / "dados/ibge-mapas-e-dados/censo_2022_intramunicipal"
SAIDA = RAIZ / "dados/app"

CD_IBGE_CG = "5002704"
CD_CARGO_DEP_ESTADUAL = 7
CARGOS_COM_VOTO_2022 = {3, 5, 6, 7}  # governador, senador, dep. federal, dep. estadual
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

# --- Votação de 2022 redistribuída nos locais de 2026 -------------------------
# Candidatos de 2026 × candidaturas de 2022 (pelo CPF), gerado por preparar_dados_ms_2022.py.
pares = pd.read_csv(CSV_CAND_PARES).drop(columns="QT_VOTOS_2022_MS")

cols22 = ["NR_TURNO", "CD_CARGO", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "NR_VOTAVEL", "QT_VOTOS"]
partes = []
for chunk in pd.read_csv(CSV_TSE_2022, sep=";", encoding="latin1", usecols=cols22, chunksize=500_000):
    chunk = chunk[(chunk["NR_TURNO"] == 1) & (chunk["CD_MUNICIPIO"] == CD_TSE_CG)
                  & chunk["CD_CARGO"].isin(CARGOS_COM_VOTO_2022)]
    partes.append(chunk.drop(columns=["NR_TURNO", "CD_MUNICIPIO"]))
v22 = pd.concat(partes)

# Chave principal: zona + seção. O eleitor costuma permanecer na mesma seção entre eleições,
# então os votos de 2022 seguem o eleitorado até o local onde ele vota em 2026.
v22 = v22.merge(loc[["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]].rename(columns={"NR_LOCAL_VOTACAO": "LOCAL_2026"}),
                on=["NR_ZONA", "NR_SECAO"], how="left")
# Seções extintas: local de 2026 mais próximo do local de votação de 2022.
sem_par = v22.loc[v22["LOCAL_2026"].isna(), ["NR_ZONA", "NR_LOCAL_VOTACAO"]].drop_duplicates()
if not sem_par.empty:
    l22 = pd.read_csv(CSV_LOCAIS_2022, sep=";", encoding="latin1", decimal=",",
                      usecols=["NR_TURNO", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO", "NR_LATITUDE", "NR_LONGITUDE"])
    l22 = (l22[(l22["CD_MUNICIPIO"] == CD_TSE_CG) & (l22["NR_TURNO"] == 1)]
           .drop_duplicates(["NR_ZONA", "NR_LOCAL_VOTACAO"]).merge(sem_par))
    p22 = gpd.GeoDataFrame(l22, geometry=gpd.points_from_xy(l22["NR_LONGITUDE"], l22["NR_LATITUDE"]), crs=4326)
    p26 = gpd.GeoDataFrame(locais[["NR_LOCAL_VOTACAO", "NR_ZONA"]].rename(
        columns={"NR_LOCAL_VOTACAO": "LOCAL_PROX", "NR_ZONA": "ZONA_PROX"}),
        geometry=gpd.points_from_xy(locais["LON"], locais["LAT"]), crs=4326)
    prox = gpd.sjoin_nearest(p22.to_crs(5880), p26.to_crs(5880), distance_col="DIST_M")
    prox = prox.drop_duplicates(["NR_ZONA", "NR_LOCAL_VOTACAO"])
    v22 = v22.merge(prox[["NR_ZONA", "NR_LOCAL_VOTACAO", "ZONA_PROX", "LOCAL_PROX"]], how="left")
    usa_prox = v22["LOCAL_2026"].isna()
    v22.loc[usa_prox, "LOCAL_2026"] = v22.loc[usa_prox, "LOCAL_PROX"]
    v22.loc[usa_prox, "NR_ZONA"] = v22.loc[usa_prox, "ZONA_PROX"]
    print(f"2022: {usa_prox.mean():.2%} das linhas de votação (seções extintas) atribuídas ao local de 2026 "
          f"mais próximo (até {prox['DIST_M'].max():.0f} m)")
if v22["LOCAL_2026"].isna().any():
    raise SystemExit("Votos de 2022 sem local de 2026 correspondente.")
v22 = v22.astype({"LOCAL_2026": int, "NR_ZONA": int})
chaves22 = ["NR_ZONA", "LOCAL_2026"]

validos22 = (v22[~v22["NR_VOTAVEL"].isin(VOTOS_NAO_VALIDOS)]
             .groupby([*chaves22, "CD_CARGO"], as_index=False)["QT_VOTOS"].sum()
             .rename(columns={"LOCAL_2026": "NR_LOCAL_VOTACAO", "CD_CARGO": "CD_CARGO_2022",
                              "QT_VOTOS": "QT_VALIDOS_2022"}))
votos22 = (v22.merge(pares[["NR_VOTAVEL", "CD_CARGO_2022", "NR_VOTAVEL_2022"]],
                     left_on=["CD_CARGO", "NR_VOTAVEL"], right_on=["CD_CARGO_2022", "NR_VOTAVEL_2022"],
                     suffixes=("_X", ""))
           .groupby([*chaves22, "NR_VOTAVEL"], as_index=False)["QT_VOTOS"].sum()
           .rename(columns={"LOCAL_2026": "NR_LOCAL_VOTACAO", "QT_VOTOS": "QT_VOTOS_2022"}))
pares = pares.merge(votos22.groupby("NR_VOTAVEL")["QT_VOTOS_2022"].sum().rename("QT_VOTOS_2022_CG"),
                    on="NR_VOTAVEL", how="left").fillna({"QT_VOTOS_2022_CG": 0})

# --- Malhas simplificadas para o mapa -----------------------------------------
def simplificar(g: gpd.GeoDataFrame, cols: list[str]) -> gpd.GeoDataFrame:
    g = g[cols + ["geometry"]].copy()
    g["geometry"] = g.to_crs(5880).simplify(TOLERANCIA_SIMPLIFICACAO_M).to_crs(4326)
    return g


SAIDA.mkdir(parents=True, exist_ok=True)
arquivos = {
    "cg_locais_votacao_2026.csv": locais,
    "cg_votos_top50_por_local_2026.csv": votos_top,
    "cg_candidatos_2022.csv": pares,
    "cg_votos_2022_top50_por_local_2026.csv": votos22,
    "cg_validos_2022_por_local_2026.csv": validos22,
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
