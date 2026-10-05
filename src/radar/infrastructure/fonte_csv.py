"""Fonte local: exportações CSV (inclusive o formato com aspas duplicadas do export atual)."""
from __future__ import annotations

import hashlib
import io
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from radar.domain.schema import COLUNAS_ORIGEM
from radar.domain.semanas import preparar_base


def ler_csv(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho, dtype=str)
    if len(df.columns) == 1:
        # Export em que cada linha inteira veio entre aspas: desembrulha e relê
        texto = "\n".join([df.columns[0], *df.iloc[:, 0].tolist()])
        df = pd.read_csv(io.StringIO(texto), dtype=str)
    df.columns = [c.strip().strip('"') for c in df.columns]
    return df[COLUNAS_ORIGEM]


class FonteCsv:
    nome = "csv"

    def __init__(self, arquivos: list[Path]):
        self.arquivos = sorted(Path(a) for a in arquivos)
        self._df: pd.DataFrame | None = None

    def _carregar(self) -> pd.DataFrame:
        if self._df is None:
            self._df = pd.concat([ler_csv(a) for a in self.arquivos], ignore_index=True)
        return self._df

    def assinatura(self) -> str:
        h = hashlib.sha256()
        for a in self.arquivos:
            h.update(a.read_bytes())
        return h.hexdigest()[:16]

    def referencia_inferida(self) -> date:
        """Domingo seguinte à última semana presente no arquivo."""
        ultima = preparar_base(self._carregar())["semana_inicio"].max()
        return (ultima + timedelta(days=7)).date()

    def extrair(self, semana_referencia: date) -> pd.DataFrame:
        return self._carregar().copy()
