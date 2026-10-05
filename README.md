# 📡 Radar de Procedimentos Emergentes na Autorizações — pipeline semanal + Streamlit

| Camada | Ferramenta |
|---|---|
| Extração | **PyAthena** (query parametrizada em `sql/`) |
| Cache de consultas | **Parquet** (snapshots imutáveis) + catálogo **SQLite** |
| Agendamento | **APScheduler** (cron semanal, retentativas com backoff) |
| Regras de negócio | **pandas** puro, testado com **pytest** |
| Visualização | **Streamlit** + **Plotly** |
| Deploy | **Docker Compose** (agendador + dashboard, volume compartilhado) |

## Arquitetura (clean architecture)

```
extractions/
├── sql/autorizacoes_semanais.py  query parametrizada (fonte Athena)
└── csv/                          exports CSV para importação manual (fora do git) 
src/radar/
├── domain/                 ← regras puras, zero I/O
│   ├── schema.py           contrato de colunas, Classificacao, validação
│   ├── semanas.py          calendário dom→sáb, semanas parciais, janelas
│   └── emergencia.py       métricas e classificação (equivalente a A1–A16 + AUX1–AUX4)
├── application/            ← casos de uso; dependem só do domínio e de Protocols
│   ├── ports.py            FonteAutorizacoes, RepositorioSnapshots, Snapshot
│   ├── extrair_snapshot.py ExtrairSnapshotSemanal (idempotente, com cache)
│   └── montar_radar.py     snapshot bruto → Radar (eventos + drill-downs)
├── infrastructure/         ← adaptadores concretos
│   ├── fonte_athena.py     produção
│   ├── fonte_csv.py        exports locais (inclusive o formato com aspas duplicadas)
│   ├── repositorio_snapshots.py
│   └── agendador.py
├── presentation/streamlit/ ← view (só chama casos de uso)
│   ├── app.py              barra lateral global = parâmetros/controles do roadmap
│   └── paginas/            radar.py (Sheet 1) · uf.py (Sheet 2) · prestador.py (Sheet 3) · execucoes.py
└── cli.py                  composition root
```

A regra de dependência só aponta para dentro: trocar Athena por Postgres/Trino, ou Streamlit
por outra UI, não toca `domain/` nem `application/`.

## Como rodar

Todo o projeto roda isolado num ambiente virtual `.venv`, com versões travadas em
`requirements.lock` (o mesmo lock é usado no Docker).

**1. Criar o ambiente (uma vez)**

```bash
./setup.sh --dev              # Linux / macOS / WSL / Git Bash
```
```powershell
.\setup.ps1 -Dev             # Windows PowerShell
```

O script cria o `.venv`, instala as dependências travadas, instala o projeto em modo
editável e copia `.env.example` → `.env` (preencha `RADAR_ATHENA_S3_STAGING_DIR`).

**2.1. Ativar e usar via make**

Sem ativar, via `make` (Linux/macOS): `make test`, `make dashboard`, `make agendar`,
`make importar ARQUIVOS="a.csv b.csv"`. O `make` cria o `.venv` sozinho se faltar.

**2.2. Ativa e usar manualmente**

```bash
source .venv/bin/activate                               # Windows: .\.venv\Scripts\Activate.ps1

radar importar-csv                                      # importa todos os .csv de extractions/csv
radar extrair                                           # extrai agora (usa cache se a semana já foi extraída)
radar extrair --data-referencia yyyy-mm-dd              # backfill de uma data anterior, de preferência da semana passada
radar extrair --forcar                                  # ignora o cache
radar snapshots                                         # lista o cache
radar sql                                               # mostra a query renderizada

radar agendar --executar-ao-iniciar                     # processo contínuo (segunda 11:00)
radar dev                                               # sobe a view do Streamlit localmente                 
radar dashboard
pytest -q
```

Sem ativar, via `make` (Linux/macOS): `make test`, `make dashboard`, `make agendar`,
`make importar ARQUIVOS="a.csv b.csv"`. O `make` cria o `.venv` sozinho se faltar.

**Atualizar dependências:** edite `pyproject.toml`, rode `make lock` e depois `./setup.sh`.

**Container:** `docker compose up -d` → dashboard em http://localhost:8501.

## Como o cache funciona

Cada extração vira `data/snapshots/semana_referencia=AAAA-MM-DD/<id>.parquet` + uma linha em
`data/catalogo.sqlite` com a **assinatura** (hash) da query. Se a mesma semana já foi extraída
com a mesma query, a fonte não é consultada. Se a query mudar, a assinatura muda e um novo
snapshot é criado sem apagar o anterior. A retenção (padrão 52) expurga os mais antigos.
No dashboard, o seletor **Snapshot** permite abrir o radar de qualquer semana anterior.