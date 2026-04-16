from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WhatsApp
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_app_secret: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # Admin
    admin_user: str = "admin"
    admin_password: str = "admin123"
    admin_jwt_secret: str = "change-this-secret"

    # Database (PostgreSQL only)
    database_url: str = "postgresql://gtc:gtc@localhost:5432/gtc_bot"

    # Redis (message batching)
    redis_url: str = "redis://localhost:6379/0"

    # Batching
    batch_wait_ms: int = 3000

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
