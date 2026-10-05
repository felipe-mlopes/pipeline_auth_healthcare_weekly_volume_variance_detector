"""Portas (interfaces) que a infraestrutura implementa."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class Snapshot:
    id: str
    semana_referencia: date     # domingo da semana corrente no momento da extração (limite exclusivo)
    executado_em: datetime
    assinatura: str             # hash da query/arquivo que gerou o snapshot
    origem: str
    linhas: int
    caminho: str


class FonteAutorizacoes(Protocol):
    nome: str

    def assinatura(self) -> str: ...
    def extrair(self, semana_referencia: date) -> pd.DataFrame: ...


class RepositorioSnapshots(Protocol):
    def buscar(self, semana_referencia: date, assinatura: str) -> Snapshot | None: ...
    def salvar(self, df: pd.DataFrame, semana_referencia: date, assinatura: str, origem: str) -> Snapshot: ...
    def listar(self) -> list[Snapshot]: ...
    def carregar(self, snapshot_id: str) -> pd.DataFrame: ...
    def expurgar(self, manter: int) -> int: ...
