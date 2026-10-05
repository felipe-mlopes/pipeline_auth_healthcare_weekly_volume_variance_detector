"""Caso de uso: transforma um snapshot bruto no Radar (eventos classificados + drill-downs)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from radar.domain.emergencia import (
    ParametrosEmergencia,
    calcular_metricas,
    classificar,
    taxa_crescimento,
)
from radar.domain.schema import CHAVES_EVENTO
from radar.domain.semanas import (
    Janelas,
    definir_janelas,
    preparar_base,
    semanas_parciais,
)

# Colunas da classificação no nível EVENTO herdadas pelos drill-downs
_HERDADAS = ["classificacao_emergencia", "flag_emergente", "score_emergencia", "rank_emergencia", "label_evento"]


@dataclass
class Radar:
    base: pd.DataFrame                    # linhas saneadas, só semanas da janela
    eventos: pd.DataFrame                 # 1 linha por evento, classificado
    janelas: Janelas
    params: ParametrosEmergencia
    semanas_descartadas: list[pd.Timestamp] = field(default_factory=list)

    @property
    def emergentes(self) -> pd.DataFrame:
        return self.eventos[self.eventos["flag_emergente"]].sort_values("rank_emergencia")

    def detalhe(self, chaves: list[str]) -> pd.DataFrame:
        """Métricas na granularidade evento × `chaves` (UF, prestador...).

        Volumes e taxa são LOCAIS (daquele prestador/UF); classificação e flag
        vêm do evento global — o mesmo critério da Sheet 1 governa os drill-downs.
        """
        m = calcular_metricas(self.base, self.janelas, [*chaves, "evento"])
        m["taxa_crescimento_pct"] = (taxa_crescimento(m, self.params) * 100).where(m["qtd_historico_evento"] > 0)
        return m.merge(self.eventos[[*CHAVES_EVENTO, *_HERDADAS]], on="evento", how="left")


def montar_radar(bruto: pd.DataFrame, params: ParametrosEmergencia) -> Radar:
    base = preparar_base(bruto)
    descartadas = semanas_parciais(base, params.limiar_semana_parcial)
    base = base[~base["semana_inicio"].isin(descartadas)]

    janelas = definir_janelas(base["semana_inicio"].unique().tolist(), params.semanas_recentes)
    base = base[base["semana_inicio"].isin(janelas.todas)].reset_index(drop=True)

    eventos = classificar(calcular_metricas(base, janelas, CHAVES_EVENTO), params)
    return Radar(base=base, eventos=eventos, janelas=janelas, params=params, semanas_descartadas=descartadas)
