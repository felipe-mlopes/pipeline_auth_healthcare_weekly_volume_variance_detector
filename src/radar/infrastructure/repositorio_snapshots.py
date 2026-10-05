"""Cache de consultas: cada extração vira um Parquet imutável + uma linha no catálogo SQLite.

Layout:
    data/
      catalogo.sqlite
      snapshots/semana_referencia=2026-09-27/20260927_20260928T060012.parquet

SQLite (e não DuckDB) no catálogo porque o agendador escreve e o Streamlit lê
em processos diferentes; SQLite lida bem com esse leitor/escritor concorrente.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from radar.application.ports import Snapshot

_DDL = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                TEXT PRIMARY KEY,
    semana_referencia TEXT NOT NULL,
    executado_em      TEXT NOT NULL,
    assinatura        TEXT NOT NULL,
    origem            TEXT NOT NULL,
    linhas            INTEGER NOT NULL,
    caminho           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ref ON snapshots (semana_referencia, assinatura);
"""
_COLS = "id, semana_referencia, executado_em, assinatura, origem, linhas, caminho"


class RepositorioSnapshotsParquet:
    def __init__(self, diretorio: Path):
        self.dir = Path(diretorio)
        (self.dir / "snapshots").mkdir(parents=True, exist_ok=True)
        self._db = self.dir / "catalogo.sqlite"
        with closing(self._conn()) as c, c:
            c.executescript(_DDL)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._db, timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    @staticmethod
    def _linha(r: tuple) -> Snapshot:
        return Snapshot(r[0], date.fromisoformat(r[1]), datetime.fromisoformat(r[2]), r[3], r[4], r[5], r[6])

    def buscar(self, semana_referencia: date, assinatura: str) -> Snapshot | None:
        with closing(self._conn()) as c:
            r = c.execute(
                f"SELECT {_COLS} FROM snapshots WHERE semana_referencia=? AND assinatura=? "
                "ORDER BY executado_em DESC LIMIT 1",
                (semana_referencia.isoformat(), assinatura),
            ).fetchone()
        return self._linha(r) if r and Path(r[6]).exists() else None

    def salvar(self, df: pd.DataFrame, semana_referencia: date, assinatura: str, origem: str) -> Snapshot:
        agora = datetime.now()
        sid = f"{semana_referencia:%Y%m%d}_{agora:%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:6]}"
        pasta = self.dir / "snapshots" / f"semana_referencia={semana_referencia.isoformat()}"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{sid}.parquet"

        tmp = destino.with_suffix(".tmp")
        df.to_parquet(tmp, index=False)
        os.replace(tmp, destino)  # escrita atômica: o leitor nunca vê arquivo pela metade

        snap = Snapshot(sid, semana_referencia, agora, assinatura, origem, len(df), str(destino))
        with closing(self._conn()) as c, c:
            c.execute(f"INSERT INTO snapshots ({_COLS}) VALUES (?,?,?,?,?,?,?)",
                      (sid, semana_referencia.isoformat(), agora.isoformat(), assinatura, origem, len(df), str(destino)))
        return snap

    def listar(self) -> list[Snapshot]:
        with closing(self._conn()) as c:
            rows = c.execute(f"SELECT {_COLS} FROM snapshots ORDER BY semana_referencia DESC, executado_em DESC").fetchall()
        return [self._linha(r) for r in rows]

    def carregar(self, snapshot_id: str) -> pd.DataFrame:
        with closing(self._conn()) as c:
            r = c.execute("SELECT caminho FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if not r:
            raise KeyError(f"Snapshot {snapshot_id} não encontrado")
        return pd.read_parquet(r[0])

    def expurgar(self, manter: int) -> int:
        excedentes = self.listar()[manter:]
        with closing(self._conn()) as c, c:
            for s in excedentes:
                Path(s.caminho).unlink(missing_ok=True)
                c.execute("DELETE FROM snapshots WHERE id=?", (s.id,))
        return len(excedentes)
