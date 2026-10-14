import tempfile
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
    database_url: str = "postgresql+psycopg2://postgres:51214@localhost:5433/pk-hub"
    download_dir: str = "../data/documents"
    work_dir: str = ""
    archive_dir: str = "../data/archives"
    scrape_concurrency: int = 3
    public_base_url: str = "http://localhost:8000"

    # Browser & Network
    dns_over_https: bool = True
    dns_over_https_templates: str = "https://dns.google/dns-query https://cloudflare-dns.com/dns-query"

    # Notification & S3 (Optional)
    recipient_emails: str = ""
    aws_s3_bucket_name: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
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
    ppra_page_load_timeout_s: int = 45
    ppra_element_wait_timeout_s: int = 20
    ppra_max_retries: int = 3
    ppra_pause_idle_timeout_min: int = 30
    ppra_apply_closing_filter: bool = True
    ppra_deep_detail: bool = False
    ppra_local_mirror: bool = True
    ppra_filter_cache_ttl_hours: int = 24

    @property
    def documents_root(self) -> Path:
        path = Path(self.download_dir)
        if not path.is_absolute():
            path = SERVER_ROOT / path
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def work_root(self) -> Path:
        if self.work_dir:
            path = Path(self.work_dir)
            if not path.is_absolute():
                path = SERVER_ROOT / path
        else:
            path = Path(tempfile.gettempdir()) / "pk-hub-runs"
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def archive_root(self) -> Path:
        path = Path(self.archive_dir)
        if not path.is_absolute():
            path = SERVER_ROOT / path
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
