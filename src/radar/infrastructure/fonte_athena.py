"""Fonte de produção: executa a query parametrizada no Amazon Athena via PyAthena."""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from string import Template

import pandas as pd


class FonteAthena:
    nome = "athena"

    def __init__(self, caminho_sql: Path, s3_staging_dir: str, region: str, work_group: str):
        if not s3_staging_dir:
            raise ValueError("RADAR_ATHENA_S3_STAGING_DIR não configurado")
        self._sql = Template(Path(caminho_sql).read_text(encoding="utf-8"))
        self._conexao = dict(s3_staging_dir=s3_staging_dir, region_name=region, work_group=work_group)

    def assinatura(self) -> str:
        return hashlib.sha256(self._sql.template.encode()).hexdigest()[:16]

    def renderizar(self, semana_referencia: date) -> str:
        return self._sql.substitute(data_referencia=semana_referencia.isoformat())

    def extrair(self, semana_referencia: date) -> pd.DataFrame:
        from pyathena import connect
        from pyathena.pandas.cursor import PandasCursor

        with connect(cursor_class=PandasCursor, **self._conexao) as conn:
            return conn.cursor().execute(self.renderizar(semana_referencia)).as_pandas()
