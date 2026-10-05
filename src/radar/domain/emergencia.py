"""Métricas e classificação de emergência (equivalente aos campos A1–A16 + AUX1–AUX4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .schema import TAXA_EVENTO_NOVO, Classificacao
from .semanas import Janelas


@dataclass(frozen=True)
class ParametrosEmergencia:
    semanas_recentes: int = 4            # paramSemanaCorte
    volume_minimo: int = 3               # paramVolumeMinimo (qtd recente)
    semanas_ativas_minimas: int = 2      # semanas com autorização no período recente
    max_historico: int | None = 5        # "eventos raros": ≤ N autorizações no histórico
    limiar_alta: float = 2.0             # taxa ≥ 200%
    limiar_moderada: float = 1.0         # taxa ≥ 100%
    cap_taxa: float = 5.0                # AUX2: limita a 500% no scatter/score
    # "absoluta" reproduz o QuickSight (soma histórica × soma recente).
    # "media_semanal" compara médias por semana — neutro ao tamanho das janelas.
    base_comparacao: Literal["absoluta", "media_semanal"] = "absoluta"
    limiar_semana_parcial: float = 0.5   # bordas com < 50% da mediana são descartadas


def calcular_metricas(df: pd.DataFrame, janelas: Janelas, chaves: list[str]) -> pd.DataFrame:
    """Volumes e semanas ativas por período, na granularidade `chaves`."""
    d = df.loc[df["semana_inicio"].isin(janelas.todas), [*chaves, "semana_inicio", "qtd_autorizacoes"]].copy()
    d["recente"] = d["semana_inicio"].isin(janelas.recentes)
    g = d.groupby([*chaves, "recente"], dropna=False).agg(
        qtd=("qtd_autorizacoes", "sum"), semanas=("semana_inicio", "nunique")
    )
    w = g.unstack("recente").reindex(
        columns=pd.MultiIndex.from_product([["qtd", "semanas"], [False, True]])
    ).fillna(0).astype("int64")

    out = pd.DataFrame(index=w.index)
    out["qtd_historico_evento"] = w[("qtd", False)]
    out["qtd_recente_evento"] = w[("qtd", True)]
    out["semanas_ativas_historico"] = w[("semanas", False)]
    out["semanas_ativas_recente"] = w[("semanas", True)]
    out["media_semanal_historico"] = out["qtd_historico_evento"] / len(janelas.historicas)
    out["media_semanal_recente"] = out["qtd_recente_evento"] / len(janelas.recentes)
    return out.reset_index()


def taxa_crescimento(m: pd.DataFrame, params: ParametrosEmergencia) -> pd.Series:
    """(recente − histórico) / histórico; 999 quando o histórico é zero."""
    if params.base_comparacao == "media_semanal":
        h, r = m["media_semanal_historico"], m["media_semanal_recente"]
    else:
        h, r = m["qtd_historico_evento"], m["qtd_recente_evento"]
    h_seguro = h.where(h > 0, 1)
    taxa = np.where(h > 0, (r - h) / h_seguro, np.where(r > 0, TAXA_EVENTO_NOVO, 0.0))
    return pd.Series(taxa, index=m.index, dtype="float64")


def classificar(m: pd.DataFrame, params: ParametrosEmergencia) -> pd.DataFrame:
    out = m.copy()
    hist, rec = out["qtd_historico_evento"], out["qtd_recente_evento"]
    taxa = taxa_crescimento(out, params)

    out["taxa_crescimento"] = taxa
    out["taxa_crescimento_pct"] = (taxa * 100).where(taxa != TAXA_EVENTO_NOVO)        # AUX1
    out["taxa_crescimento_capped"] = taxa.clip(upper=params.cap_taxa)                  # AUX2
    out["classificacao_emergencia"] = np.select(
        [(hist == 0) & (rec > 0), taxa >= params.limiar_alta, taxa >= params.limiar_moderada],
        [Classificacao.NOVO.value, Classificacao.ALTA.value, Classificacao.MODERADA.value],
        default=Classificacao.ESTAVEL.value,
    )
    # Score = volume recente × crescimento (capado): volume e velocidade pesam juntos
    out["score_emergencia"] = rec * out["taxa_crescimento_capped"].clip(lower=0)

    flag = (
        (out["classificacao_emergencia"] != Classificacao.ESTAVEL.value)
        & (rec >= params.volume_minimo)
        & (out["semanas_ativas_recente"] >= params.semanas_ativas_minimas)
    )
    if params.max_historico is not None:
        flag &= hist <= params.max_historico
    out["flag_emergente"] = flag                                                        # AUX4

    out["rank_emergencia"] = (
        out["score_emergencia"].where(flag)
        .rank(method="min", ascending=False).astype("Int64")
    )
    if "descricao_procedimento" in out:                                                 # AUX3
        novo = out["classificacao_emergencia"] == Classificacao.NOVO.value
        out["label_evento"] = out["descricao_procedimento"].where(~novo, out["descricao_procedimento"] + " 🔴NOVO")
    return out
