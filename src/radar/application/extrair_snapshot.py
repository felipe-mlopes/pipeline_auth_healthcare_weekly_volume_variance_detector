"""Caso de uso: extração semanal com cache de consultas anteriores."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from radar.domain.schema import validar_schema
from radar.domain.semanas import inicio_semana

from .ports import FonteAutorizacoes, RepositorioSnapshots, Snapshot

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoExtracao:
    snapshot: Snapshot
    do_cache: bool


class ExtrairSnapshotSemanal:
    """Idempotente: a mesma (semana_referencia, assinatura da query) não consulta a fonte duas vezes.

    Mudou a query? A assinatura muda e a próxima execução refaz a extração,
    preservando o snapshot antigo para comparação.
    """

    def __init__(self, fonte: FonteAutorizacoes, repositorio: RepositorioSnapshots, retencao: int = 52):
        self.fonte = fonte
        self.repo = repositorio
        self.retencao = retencao

    def executar(self, data_referencia: date | None = None, forcar: bool = False) -> ResultadoExtracao:
        ref = inicio_semana(data_referencia or date.today())
        assinatura = self.fonte.assinatura()

        if not forcar and (cache := self.repo.buscar(ref, assinatura)):
            log.info("Cache hit: snapshot %s (ref %s) — fonte não consultada", cache.id, ref)
            return ResultadoExtracao(cache, do_cache=True)

        log.info("Extraindo de %s para semana de referência %s", self.fonte.nome, ref)
        df = self.fonte.extrair(ref)
        validar_schema(df)
        snap = self.repo.salvar(df, ref, assinatura, self.fonte.nome)
        removidos = self.repo.expurgar(self.retencao)
        log.info("Snapshot %s salvo (%d linhas); %d antigos expurgados", snap.id, snap.linhas, removidos)
        return ResultadoExtracao(snap, do_cache=False)
