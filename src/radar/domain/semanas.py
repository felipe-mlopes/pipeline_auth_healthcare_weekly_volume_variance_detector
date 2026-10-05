"""Calendário semanal (domingo → sábado), saneamento e janelas de comparação."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .schema import PADROES_NULOS


def inicio_semana(d: date) -> date:
    """Domingo que inicia a semana de `d`."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def preparar_base(df: pd.DataFrame) -> pd.DataFrame:
    """Tipagem, nulos e correção do bug de domingo da query original.

    Na query original, `semana_autorizacao` usava date_trunc('week', data) - 1 dia
    (domingo ANTERIOR para autorizações feitas no domingo) enquanto `numero_semana`
    usava week(data + 1 dia) (semana SEGUINTE). Regra de correção, idempotente:
    se a ISO-week da segunda-feira seguinte ao início informado não bate com
    numero_semana, o início real é 7 dias depois. Dados já corretos não mudam.
    """
    d = df.copy()
    d["qtd_autorizacoes"] = pd.to_numeric(d["qtd_autorizacoes"]).astype("int64")
    d["numero_semana"] = pd.to_numeric(d["numero_semana"]).astype("int64")
    for col in ["cnpj_executante", "evento"]:
        d[col] = d[col].astype(str)
    d = d.fillna(PADROES_NULOS)

    inicio = pd.to_datetime(d["semana_autorizacao"]).dt.normalize()
    iso = (inicio + pd.Timedelta(days=1)).dt.isocalendar().week.astype("int64")
    d["semana_inicio"] = inicio.where(iso == d["numero_semana"], inicio + pd.Timedelta(days=7))

    dims = [c for c in d.columns if c not in ("qtd_autorizacoes", "semana_autorizacao")]
    return d.groupby(dims, as_index=False, dropna=False)["qtd_autorizacoes"].sum()


def semanas_parciais(df: pd.DataFrame, limiar: float) -> list[pd.Timestamp]:
    """Semanas das BORDAS com volume < limiar × mediana (extração cortada no meio).

    Só as bordas são avaliadas para não descartar uma semana legítima de baixo
    volume (feriado) no meio da série.
    """
    total = df.groupby("semana_inicio")["qtd_autorizacoes"].sum().sort_index()
    if len(total) < 3:
        return []
    corte = total.median() * limiar
    bordas = [total.index[0], total.index[-1]]
    return [s for s in bordas if total[s] < corte]


@dataclass(frozen=True)
class Janelas:
    historicas: tuple[pd.Timestamp, ...]
    recentes: tuple[pd.Timestamp, ...]

    @property
    def todas(self) -> tuple[pd.Timestamp, ...]:
        return self.historicas + self.recentes

    @property
    def inicio_recente(self) -> pd.Timestamp:
        return self.recentes[0]


def definir_janelas(semanas: list[pd.Timestamp], n_recentes: int) -> Janelas:
    semanas = sorted(set(semanas))
    if not 1 <= n_recentes < len(semanas):
        raise ValueError(f"semanas_recentes={n_recentes} inválido para {len(semanas)} semanas disponíveis")
    return Janelas(historicas=tuple(semanas[:-n_recentes]), recentes=tuple(semanas[-n_recentes:]))
