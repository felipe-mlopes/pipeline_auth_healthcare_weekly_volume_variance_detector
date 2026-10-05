"""Estado compartilhado entre páginas + acesso cacheado aos casos de uso.

A view nunca toca Parquet/SQLite diretamente: passa pelo repositório e pelo caso
de uso `montar_radar`, exatamente como o CLI faz.
"""
from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from radar.application.montar_radar import Radar, montar_radar
from radar.config import get_settings
from radar.domain.emergencia import ParametrosEmergencia
from radar.domain.schema import Classificacao
from radar.infrastructure.repositorio_snapshots import RepositorioSnapshotsParquet

# Chaves de session_state (não-widget) usadas para navegação entre páginas
EVENTO_ALVO, UF_ALVO, PRESTADOR_ALVO = "evento_alvo", "uf_alvo", "prestador_alvo"
TODAS = "Todas"

CLASSIFICACOES_EMERGENTES = [Classificacao.NOVO.value, Classificacao.ALTA.value, Classificacao.MODERADA.value]
CHAVES_PRESTADOR = ["uf", "cidade", "prestador_executante", "cnpj_executante"]


@st.cache_resource
def repositorio() -> RepositorioSnapshotsParquet:
    return RepositorioSnapshotsParquet(get_settings().diretorio_dados)


@st.cache_data(ttl=300, show_spinner=False)
def listar_snapshots() -> list[dict]:
    return [asdict(s) for s in repositorio().listar()]


@st.cache_data(max_entries=6, show_spinner="Calculando radar…")
def _radar(snapshot_id: str, params_json: str) -> Radar:
    bruto = repositorio().carregar(snapshot_id)
    return montar_radar(bruto, ParametrosEmergencia(**json.loads(params_json)))


@st.cache_data(max_entries=6, show_spinner="Detalhando por prestador…")
def _detalhe(snapshot_id: str, params_json: str) -> pd.DataFrame:
    return _radar(snapshot_id, params_json).detalhe(CHAVES_PRESTADOR)


def _chave_cache() -> tuple[str, str]:
    p: ParametrosEmergencia = st.session_state["params"]
    return st.session_state["snapshot_id"], json.dumps(asdict(p), sort_keys=True)


def radar() -> Radar:
    return _radar(*_chave_cache())


def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["flag_emergente"].fillna(False).astype(bool)]
    if cls := st.session_state.get("filtro_classificacao"):
        df = df[df["classificacao_emergencia"].isin(cls)]
    if classes := st.session_state.get("filtro_classe"):
        df = df[df["classe_evento"].isin(classes)]
    return df


def emergentes_filtrados() -> pd.DataFrame:
    return _filtrar(radar().emergentes)


def detalhe_filtrado() -> pd.DataFrame:
    return _filtrar(_detalhe(*_chave_cache()))


def seletor(rotulo: str, opcoes: list[str], chave: str, **kw) -> str:
    """Selectbox cujo valor pode ser definido por outras páginas/cliques (via session_state[chave]).

    A key do widget inclui o valor atual: quando outra página muda `chave`,
    o widget é recriado já com o novo índice (evita o conflito widget × session_state).
    """
    valor = st.session_state.get(chave)
    if valor not in opcoes:
        valor = opcoes[0]
    novo = st.selectbox(rotulo, opcoes, index=opcoes.index(valor), key=f"_w_{chave}_{valor}", **kw)
    st.session_state[chave] = novo
    return novo
