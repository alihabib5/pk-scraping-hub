from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = SERVER_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Database & Filesystem
    # Placeholder only — the real URL comes from DATABASE_URL in server/.env.
    database_url: str = "postgresql+psycopg2://postgres:password@localhost:5432/pk-hub"
    # Archived workbooks go to <data_dir>/archives, the JSONL mirror to <data_dir>/ppra.
    data_dir: str = "../data"
    scrape_concurrency: int = 3
    public_base_url: str = "http://localhost:8000"

    # Browser & Network
    dns_over_https: bool = True
    dns_over_https_templates: str = "https://dns.google/dns-query https://cloudflare-dns.com/dns-query"

    # Email notification (optional — nothing is sent unless these are set)
    recipient_emails: str = ""
    aws_region: str = "us-east-1"
    aws_ses_from_email: str = ""
    aws_ses_username: str = ""
    aws_ses_password: str = ""

    # PPRA Federal (Public Procurement Regulatory Authority)
    # Target URL: https://epms.ppra.gov.pk/public/tenders/active-tenders
    ppra_base_url: str = "https://epms.ppra.gov.pk"
    ppra_active_tenders_path: str = "/public/tenders/active-tenders"
    ppra_delay_min_ms: int = 1000
    ppra_delay_max_ms: int = 2500
    ppra_local_mirror: bool = True

    @property
    def data_root(self) -> Path:
        path = Path(self.data_dir)
        if not path.is_absolute():
            path = SERVER_ROOT / path
        return path.resolve()

    @property
    def archive_root(self) -> Path:
        path = self.data_root / "archives"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
