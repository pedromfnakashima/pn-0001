"""Gera a tabela de correspondência entre códigos de município do TSE e do IBGE (MS).

Fonte principal: tabela oficial do TSE "Códigos oficiais de UF e municípios segundo o TSE e o
IBGE" (municipio_tse_ibge.csv). Como verificação independente, os municípios do arquivo de
votação são pareados pelo nome normalizado (maiúsculas, sem acentos e sem pontuação) com a
malha municipal do IBGE; o script falha se os dois métodos divergirem.
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_OFICIAL = RAIZ / "dados/tse_ibge_municipios/municipio_tse_ibge.csv"
CSV_TSE = RAIZ / "dados/votacao_secao_2026_MS/votacao_secao_2026_MS.csv"
SHP_IBGE = RAIZ / "dados/ibge-mapas-e-dados/MS_Municipios_2025/MS_Municipios_2025.shp"
SAIDA = RAIZ / "dados/ibge-mapas-e-dados/correspondencia_municipios_tse_ibge_MS.csv"


def normalizar(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    nome = re.sub(r"[^A-Z ]", " ", nome.upper())
    return re.sub(r"\s+", " ", nome).strip()


# 1) Tabela oficial do TSE
oficial = pd.read_csv(CSV_OFICIAL, sep=";", encoding="latin1",
                      usecols=["SG_UF", "CD_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE"])
oficial = oficial[oficial["SG_UF"] == "MS"].astype({"CD_MUNICIPIO_IBGE": str})

# 2) Verificação por nome: municípios do arquivo de votação × malha do IBGE
tse = (
    pd.read_csv(CSV_TSE, sep=";", encoding="latin1", usecols=["CD_MUNICIPIO", "NM_MUNICIPIO"])
    .drop_duplicates()
    .rename(columns={"CD_MUNICIPIO": "CD_MUNICIPIO_TSE", "NM_MUNICIPIO": "NM_MUNICIPIO_TSE"})
)
ibge = (
    gpd.read_file(SHP_IBGE, ignore_geometry=True)[["CD_MUN", "NM_MUN"]]
    .rename(columns={"CD_MUN": "CD_MUNICIPIO_IBGE", "NM_MUN": "NM_MUNICIPIO_IBGE"})
)
tse["chave"] = tse["NM_MUNICIPIO_TSE"].map(normalizar)
ibge["chave"] = ibge["NM_MUNICIPIO_IBGE"].map(normalizar)
por_nome = tse.merge(ibge, on="chave", how="outer", indicator=True)
if (por_nome["_merge"] != "both").any():
    raise SystemExit(f"Municípios sem par pelo nome:\n{por_nome[por_nome['_merge'] != 'both']}")

comp = por_nome.merge(oficial, on="CD_MUNICIPIO_TSE", how="outer", suffixes=("", "_OFICIAL"), indicator="_oficial")
divergentes = comp[(comp["_oficial"] != "both") | (comp["CD_MUNICIPIO_IBGE"] != comp["CD_MUNICIPIO_IBGE_OFICIAL"])]
if not divergentes.empty:
    raise SystemExit(f"Tabela oficial e pareamento por nome divergem:\n{divergentes}")

corr = comp[["SG_UF", "CD_MUNICIPIO_TSE", "NM_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE", "NM_MUNICIPIO_IBGE"]]
corr = corr.sort_values("NM_MUNICIPIO_IBGE")
corr.to_csv(SAIDA, index=False, encoding="utf-8")
print(f"{len(corr)} municípios gravados em {SAIDA} (tabela oficial TSE = pareamento por nome)")
