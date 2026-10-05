"""Agendamento semanal com APScheduler (cron), retentativas e execução opcional no boot."""
from __future__ import annotations

import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from radar.application.extrair_snapshot import ExtrairSnapshotSemanal

log = logging.getLogger(__name__)


def executar_com_retentativas(caso_de_uso: ExtrairSnapshotSemanal, tentativas: int, espera_s: int) -> None:
    for n in range(1, tentativas + 1):
        try:
            r = caso_de_uso.executar()
            log.info("OK: snapshot %s (%s)", r.snapshot.id, "cache" if r.do_cache else "novo")
            return
        except Exception:
            log.exception("Tentativa %d/%d falhou", n, tentativas)
            if n < tentativas:
                time.sleep(espera_s * n)  # backoff linear
    log.error("Extração semanal falhou após %d tentativas", tentativas)


def iniciar(caso_de_uso: ExtrairSnapshotSemanal, cron: str, timezone: str,
            tentativas: int, espera_s: int, executar_ao_iniciar: bool) -> None:
    job = lambda: executar_com_retentativas(caso_de_uso, tentativas, espera_s)
    if executar_ao_iniciar:
        job()  # cache evita reconsulta se a semana já foi extraída

    sched = BlockingScheduler(timezone=timezone)
    sched.add_job(job, CronTrigger.from_crontab(cron, timezone=timezone), id="extracao_semanal",
                  coalesce=True, max_instances=1, misfire_grace_time=6 * 3600)
    log.info("Agendado: '%s' (%s)", cron, timezone)
    sched.start()
