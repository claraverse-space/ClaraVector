from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # NVIDIA NIM Configuration
    nim_api_key: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "nvidia/nv-embedqa-e5-v5"
    nim_rpm_limit: int = 40
    nim_embedding_dim: int = 1024

    # Data directories
    data_dir: Path = Path("/home/claraverse/ClaraVector/data")

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 2

    # Processing limits
    max_file_size_mb: int = 10
    max_chunk_size: int = 300  # tokens - NIM has 512 token limit, using 300 for safety
    chunk_overlap: int = 30  # ~10% overlap

    # Queue settings
    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "sqlite" / "clara_vector.db"

    @property
    def lancedb_path(self) -> Path:
        return self.data_dir / "lancedb"

    @property
    def files_path(self) -> Path:
        return self.data_dir / "files"

    @property
    def min_request_interval(self) -> float:
        """Minimum seconds between NIM API requests."""
        return 60.0 / self.nim_rpm_limit


@lru_cache
def get_settings() -> Settings:
    return Settings()
