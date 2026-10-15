"""Gera a tabela de correspondência entre códigos de município do TSE e do IBGE (MS).

O pareamento é feito pelo nome normalizado (maiúsculas, sem acentos e sem pontuação),
cruzando o CSV de votação por seção do TSE com a malha municipal do IBGE.
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_TSE = RAIZ / "dados/votacao_secao_2026_MS/votacao_secao_2026_MS.csv"
SHP_IBGE = RAIZ / "dados/ibge-mapas-e-dados/MS_Municipios_2025/MS_Municipios_2025.shp"
SAIDA = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"


def normalizar(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    nome = re.sub(r"[^A-Z ]", " ", nome.upper())
    return re.sub(r"\s+", " ", nome).strip()


tse = (
    pd.read_csv(CSV_TSE, sep=";", encoding="latin1", usecols=["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO"])
    .drop_duplicates()
    .rename(columns={"CD_MUNICIPIO": "CD_MUNICIPIO_TSE", "NM_MUNICIPIO": "NM_MUNICIPIO_TSE"})
)
ibge = (
    gpd.read_file(SHP_IBGE, ignore_geometry=True)[["CD_MUN", "NM_MUN"]]
    .rename(columns={"CD_MUN": "CD_MUNICIPIO_IBGE", "NM_MUN": "NM_MUNICIPIO_IBGE"})
)
tse["chave"] = tse["NM_MUNICIPIO_TSE"].map(normalizar)
ibge["chave"] = ibge["NM_MUNICIPIO_IBGE"].map(normalizar)

corr = tse.merge(ibge, on="chave", how="outer", indicator=True)
faltantes = corr[corr["_merge"] != "both"]
if not faltantes.empty:
    raise SystemExit(f"Municípios sem par:\n{faltantes}")

corr = corr[["SG_UF", "CD_MUNICIPIO_TSE", "NM_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE", "NM_MUNICIPIO_IBGE"]]
corr = corr.sort_values("NM_MUNICIPIO_IBGE")
corr.to_csv(SAIDA, index=False, encoding="utf-8")
print(f"{len(corr)} municípios gravados em {SAIDA}")
