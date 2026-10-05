"""Configuração via variáveis de ambiente (prefixo RADAR_) ou arquivo .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
DIR_EXTRACOES = RAIZ_PROJETO / "extractions"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RADAR_", 
        env_file=RAIZ_PROJETO / ".env", 
        extra="ignore"
    )

    # Fonte
    caminho_sql: Path = DIR_EXTRACOES / "sql" / "autorizacoes_semanais.sql"
    diretorio_csv: Path = DIR_EXTRACOES / "csv"
    athena_s3_staging_dir: str | None = None
    athena_region: str = "us-east-1"
    athena_work_group: str = "primary"

    # Cache
    diretorio_dados: Path = RAIZ_PROJETO / "data"
    retencao_snapshots: int = 52

    # Agendamento
    cron: str = "0 6 * * mon"
    timezone: str = "America/Sao_Paulo"
    tentativas: int = 3
    espera_entre_tentativas_s: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
