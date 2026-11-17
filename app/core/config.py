"""Application configuration, loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Natives API"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "*"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/natives"

    # Supabase
    supabase_url: str = ""
    # New-style API keys (sb_publishable_... / sb_secret_...).
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""

    # JWT verification.
    # Supabase now signs access tokens with asymmetric keys (ES256) exposed via
    # JWKS, so ES256 is the default and no shared secret is needed. For legacy
    # projects still on the shared HS256 secret, set JWT_ALGORITHM=HS256 and
    # provide SUPABASE_JWT_SECRET.
    jwt_algorithm: str = "ES256"
    jwt_audience: str = "authenticated"
    jwt_verify_issuer: bool = True
    supabase_jwt_secret: str = ""  # legacy HS256 only

    # Storage
    listing_images_bucket: str = "listing-images"
    avatars_bucket: str = "avatars"

    # Admin bootstrap
    bootstrap_admin_email: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_base_url(self) -> str:
        return self.supabase_url.rstrip("/")

    @property
    def jwks_url(self) -> str:
        """Supabase GoTrue JWKS endpoint (public signing keys)."""
        return f"{self.supabase_base_url}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_base_url}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
