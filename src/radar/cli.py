from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

from radar.application.extrair_snapshot import ExtrairSnapshotSemanal
from radar.config import get_settings
from radar.infrastructure.repositorio_snapshots import RepositorioSnapshotsParquet

def _resolver_csvs(arquivos: list[Path]) -> list[Path]:
    pasta = get_settings().diretorio_csv

    if not arquivos:
        encontrados = sorted(pasta.glob("*.csv"))
        
        if not encontrados:
            raise SystemExit(f"Nenhum .csv encontrado em {pasta}")
        
        return encontrados

    resolvidos = []

    for a in arquivos:
        candidato = a if a.exists() else pasta / a
        
        if not candidato.exists():
            raise SystemExit(f"Arquivo não encontrado: {a} (procurado na pasta atual e em {pasta})")
        
        resolvidos.append(candidato)

    return resolvidos

def _repo():
    return RepositorioSnapshotsParquet(get_settings().diretorio_dados)


def _caso_athena() -> ExtrairSnapshotSemanal:
    from radar.infrastructure.fonte_athena import FonteAthena

    s = get_settings()
    fonte = FonteAthena(s.caminho_sql, s.athena_s3_staging_dir, s.athena_region, s.athena_work_group)
    return ExtrairSnapshotSemanal(fonte, _repo(), s.retencao_snapshots)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extrair", help="Executa a extração agora (usa cache se já houver)")
    e.add_argument("--data-referencia", type=date.fromisoformat, help="YYYY-MM-DD (backfill)")
    e.add_argument("--forcar", action="store_true", help="Ignora o cache")

    i = sub.add_parser("importar-csv", help="Carrega exportações CSV como snapshot "
                                        "(sem argumentos: todos os .csv de extractions/csv)")
    i.add_argument("arquivos", nargs="+", type=Path)
    i.add_argument("--forcar", action="store_true")

    a = sub.add_parser("agendar", help="Sobe o agendador semanal (processo contínuo)")
    a.add_argument("--executar-ao-iniciar", action="store_true")

    sub.add_parser("snapshots", help="Lista o cache")
    sub.add_parser("sql", help="Mostra a query renderizada para a semana atual")

    args = p.parse_args(argv)
    s = get_settings()

    if args.cmd == "extrair":
        r = _caso_athena().executar(args.data_referencia, forcar=args.forcar)
        print(f"{r.snapshot.id} ({'cache' if r.do_cache else 'novo'}) — {r.snapshot.linhas} linhas")

    elif args.cmd == "importar-csv":
        from radar.infrastructure.fonte_csv import FonteCsv

        arquivos = _resolver_csvs(args.arquivos)
        print("Importando:", *[f" {a}" for a in arquivos], sep="\n")
        fonte = FonteCsv(arquivos)
        caso = ExtrairSnapshotSemanal(fonte, _repo(), s.retencao_snapshots)
        r = caso.executar(fonte.referencia_inferida(), forcar=args.forcar)
        print(f"{r.snapshot.id} ({'cache' if r.do_cache else 'novo'}) — {r.snapshot.linhas} linhas")

    elif args.cmd == "agendar":
        from radar.infrastructure.agendador import iniciar

        iniciar(_caso_athena(), s.cron, s.timezone, s.tentativas, s.espera_entre_tentativas_s,
                args.executar_ao_iniciar)

    elif args.cmd == "snapshots":
        for sn in _repo().listar():
            print(f"{sn.id}  ref={sn.semana_referencia}  {sn.origem:<6} {sn.linhas:>8} linhas  sig={sn.assinatura}")

    elif args.cmd == "sql":
        from radar.domain.semanas import inicio_semana
        from radar.infrastructure.fonte_athena import FonteAthena

        print(FonteAthena(s.caminho_sql, s.athena_s3_staging_dir or "s3://-/", s.athena_region,
                          s.athena_work_group).renderizar(inicio_semana(date.today())))


if __name__ == "__main__":
    main()
