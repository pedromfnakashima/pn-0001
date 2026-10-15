"""Gera o CSV reduzido usado pelo dashboard de Deputado Estadual (MS, Eleições 2026).

Agrega a votação por seção do TSE (≈200 MB) em votos por município e votável, já com
nome de urna, partido e código IBGE do município. Rodar novamente sempre que o TSE
atualizar os arquivos de origem:
    conda activate llm_001
    python notebooks-e-python/preparar_dados_dashboard.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_TSE = RAIZ / "dados/votacao_secao_2026_MS/votacao_secao_2026_MS.csv"
CSV_CAND = RAIZ / "dados/consulta_cand_2026/consulta_cand_2026_MS.csv"
CSV_CORRESP = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"
SAIDA = RAIZ / "dados/app/votos_dep_estadual_ms_2026.csv"

CD_CARGO_DEP_ESTADUAL = 7

cols = ["CD_CARGO", "CD_MUNICIPIO", "NR_VOTAVEL", "NM_VOTAVEL", "SQ_CANDIDATO", "QT_VOTOS"]
chaves = ["CD_MUNICIPIO", "NR_VOTAVEL", "NM_VOTAVEL", "SQ_CANDIDATO"]
partes = []
for chunk in pd.read_csv(CSV_TSE, sep=";", encoding="latin1", usecols=cols, chunksize=500_000):
    chunk = chunk[chunk["CD_CARGO"] == CD_CARGO_DEP_ESTADUAL]
    partes.append(chunk.groupby(chaves, as_index=False)["QT_VOTOS"].sum())
votos = pd.concat(partes).groupby(chaves, as_index=False)["QT_VOTOS"].sum()

# Nome de urna e partido vêm do cadastro de candidatos do TSE (consulta_cand).
cand = pd.read_csv(CSV_CAND, sep=";", encoding="latin1",
                   usecols=["CD_CARGO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"])
cand = cand[cand["CD_CARGO"] == CD_CARGO_DEP_ESTADUAL].drop(columns="CD_CARGO")
votos = votos.merge(cand, on="SQ_CANDIDATO", how="left")

corresp = pd.read_csv(CSV_CORRESP, dtype={"CD_MUNICIPIO_IBGE": str})
votos = votos.merge(corresp[["CD_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE"]],
                    left_on="CD_MUNICIPIO", right_on="CD_MUNICIPIO_TSE", how="left")
if votos["CD_MUNICIPIO_IBGE"].isna().any():
    raise SystemExit("Há municípios do TSE sem código IBGE na tabela de correspondência.")

votos = votos[["CD_MUNICIPIO_IBGE", "NR_VOTAVEL", "SQ_CANDIDATO", "NM_VOTAVEL",
               "NM_URNA_CANDIDATO", "SG_PARTIDO", "QT_VOTOS"]]
votos = votos.sort_values(["CD_MUNICIPIO_IBGE", "QT_VOTOS"], ascending=[True, False])

SAIDA.parent.mkdir(parents=True, exist_ok=True)
votos.to_csv(SAIDA, index=False, encoding="utf-8")
print(f"{len(votos):,} linhas · {SAIDA.stat().st_size / 1e6:.2f} MB → {SAIDA}")
