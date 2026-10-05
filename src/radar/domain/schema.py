"""Contrato de dados entre a fonte e o domínio."""
from enum import Enum

import pandas as pd

COLUNAS_ORIGEM = [
    "cnpj_executante", "prestador_executante", "cidade", "uf", "evento",
    "descricao_procedimento", "classe_evento", "semana_autorizacao",
    "numero_semana", "qtd_autorizacoes",
]

CHAVES_EVENTO = ["evento", "descricao_procedimento", "classe_evento"]

# Preenchimento de nulos (prestadores fora do livreto, eventos fora da TGE)
PADROES_NULOS = {
    "prestador_executante": "(não credenciado)",
    "cidade": "N/D",
    "uf": "N/D",
    "descricao_procedimento": "(sem descrição)",
    "classe_evento": "(sem classe)",
}

TAXA_EVENTO_NOVO = 999.0  # sentinela herdada do QuickSight


class Classificacao(str, Enum):
    NOVO = "🔴 NOVO"
    ALTA = "🟠 EM ALTA"
    MODERADA = "🟡 MODERADA"
    ESTAVEL = "⚪ ESTÁVEL OU DECLÍNIO"


class ErroSchema(ValueError):
    pass


def validar_schema(df: pd.DataFrame) -> None:
    faltantes = set(COLUNAS_ORIGEM) - set(df.columns)
    if faltantes:
        raise ErroSchema(f"Colunas ausentes na extração: {sorted(faltantes)}")
    if df.empty:
        raise ErroSchema("Extração retornou 0 linhas")
