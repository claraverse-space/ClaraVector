from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Security
    api_key: str = ""  # Required for all endpoints if set

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

    # CORS Configuration
    # Comma-separated list of allowed origins, or "*" for all
    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

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

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_methods_list(self) -> list[str]:
        """Parse CORS methods from comma-separated string."""
        if self.cors_allow_methods == "*":
            return ["*"]
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    @property
    def cors_headers_list(self) -> list[str]:
        """Parse CORS headers from comma-separated string."""
        if self.cors_allow_headers == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
