"""Gera os arquivos reduzidos da comparação 2026 − 2022 por município (Deputado Estadual, MS).

Cada um dos 50 candidatos mais votados de 2026 é procurado nas candidaturas de 2022 pelo CPF
(qualquer cargo com votação própria, 1º turno). O CPF é usado só aqui e não é gravado.
Os códigos de município do TSE são os mesmos em 2022 e 2026.

Fontes brutas (não versionadas): votação por seção 2022 (MS) e candidatos 2022/2026 (MS) do TSE.

Rodar depois de preparar_dados_dashboard.py e antes de preparar_dados_campo_grande.py:
    conda activate llm_001
    python notebooks-e-python/preparar_dados_ms_2022.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_TSE_2022 = RAIZ / "dados/votacao_secao_2022_MS/votacao_secao_2022_MS.csv"
CSV_CAND_2022 = RAIZ / "dados/consulta_cand_2022/consulta_cand_2022_MS.csv"
CSV_CAND_2026 = RAIZ / "dados/consulta_cand_2026/consulta_cand_2026_MS.csv"
CSV_VOTOS_MUN = RAIZ / "dados/app/votos_dep_estadual_ms_2026.csv"
CSV_CORRESP = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"
SAIDA = RAIZ / "dados/app"

CD_CARGO_DEP_ESTADUAL = 7
CARGOS_COM_VOTO_2022 = {3, 5, 6, 7}  # governador, senador, dep. federal, dep. estadual
VOTOS_NAO_VALIDOS = {95, 96}  # branco, nulo
TOP_N = 50

# --- Candidatos: top 50 de 2026 × candidaturas de 2022 (pelo CPF) ---------------
votos_mun = pd.read_csv(CSV_VOTOS_MUN)
top = votos_mun[votos_mun["NR_VOTAVEL"] >= 1000].groupby("NR_VOTAVEL")["QT_VOTOS"].sum().nlargest(TOP_N).index

cand26 = pd.read_csv(CSV_CAND_2026, sep=";", encoding="latin1", dtype={"NR_CPF_CANDIDATO": str},
                     usecols=["CD_CARGO", "NR_CANDIDATO", "NR_CPF_CANDIDATO"])
cand26 = cand26[(cand26["CD_CARGO"] == CD_CARGO_DEP_ESTADUAL) & cand26["NR_CANDIDATO"].isin(top)]
cand22 = pd.read_csv(CSV_CAND_2022, sep=";", encoding="latin1", dtype={"NR_CPF_CANDIDATO": str},
                     usecols=["NR_TURNO", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO",
                              "NM_URNA_CANDIDATO", "SG_PARTIDO", "NR_CPF_CANDIDATO"])
cand22 = cand22[(cand22["NR_TURNO"] == 1) & cand22["CD_CARGO"].isin(CARGOS_COM_VOTO_2022)]
pares = cand26.merge(cand22.drop(columns="NR_TURNO"), on="NR_CPF_CANDIDATO", suffixes=("_2026", "_2022"))
if pares["NR_CANDIDATO_2026"].duplicated().any():
    raise SystemExit("Candidato de 2026 com mais de uma candidatura com votos em 2022.")
pares = pares.drop(columns=["NR_CPF_CANDIDATO", "CD_CARGO_2026"]).rename(columns={
    "NR_CANDIDATO_2026": "NR_VOTAVEL", "NR_CANDIDATO_2022": "NR_VOTAVEL_2022",
    "SQ_CANDIDATO": "SQ_CANDIDATO_2022", "DS_CARGO": "DS_CARGO_2022", "NM_URNA_CANDIDATO": "NM_URNA_2022",
    "SG_PARTIDO": "SG_PARTIDO_2022"})

# --- Votação de 2022 por município --------------------------------------------
cols = ["NR_TURNO", "CD_CARGO", "CD_MUNICIPIO", "NR_VOTAVEL", "QT_VOTOS"]
chaves = ["CD_MUNICIPIO", "CD_CARGO", "NR_VOTAVEL"]
partes = []
for chunk in pd.read_csv(CSV_TSE_2022, sep=";", encoding="latin1", usecols=cols, chunksize=500_000):
    chunk = chunk[(chunk["NR_TURNO"] == 1) & chunk["CD_CARGO"].isin(CARGOS_COM_VOTO_2022)]
    partes.append(chunk.groupby(chaves, as_index=False)["QT_VOTOS"].sum())
v22 = pd.concat(partes).groupby(chaves, as_index=False)["QT_VOTOS"].sum()

corresp = pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str})
v22 = v22.merge(corresp[["CD_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE"]],
                left_on="CD_MUNICIPIO", right_on="CD_MUNICIPIO_TSE", how="left")
if v22["CD_MUNICIPIO_IBGE"].isna().any():
    raise SystemExit("Há municípios de 2022 sem código IBGE na tabela de correspondência.")

validos = (v22[~v22["NR_VOTAVEL"].isin(VOTOS_NAO_VALIDOS)]
           .groupby(["CD_MUNICIPIO_IBGE", "CD_CARGO"], as_index=False)["QT_VOTOS"].sum()
           .rename(columns={"CD_CARGO": "CD_CARGO_2022", "QT_VOTOS": "QT_VALIDOS_2022"}))
votos = (v22.merge(pares[["NR_VOTAVEL", "CD_CARGO_2022", "NR_VOTAVEL_2022"]],
                   left_on=["CD_CARGO", "NR_VOTAVEL"], right_on=["CD_CARGO_2022", "NR_VOTAVEL_2022"],
                   suffixes=("_X", ""))
         [["CD_MUNICIPIO_IBGE", "NR_VOTAVEL", "QT_VOTOS"]]
         .rename(columns={"QT_VOTOS": "QT_VOTOS_2022"})
         .sort_values(["CD_MUNICIPIO_IBGE", "NR_VOTAVEL"]))
pares = pares.merge(votos.groupby("NR_VOTAVEL")["QT_VOTOS_2022"].sum().rename("QT_VOTOS_2022_MS"),
                    on="NR_VOTAVEL", how="left").fillna({"QT_VOTOS_2022_MS": 0})

arquivos = {
    "candidatos_2022.csv": pares,
    "votos_2022_por_municipio.csv": votos,
    "validos_2022_por_municipio.csv": validos,
}
for nome, df in arquivos.items():
    df.to_csv(SAIDA / nome, index=False, encoding="utf-8")
    print(f"  {(SAIDA / nome).stat().st_size / 1e3:8.0f} kB  {nome}")
print(f"{len(pares)} de {TOP_N} candidatos de 2026 tiveram votação própria em 2022")
