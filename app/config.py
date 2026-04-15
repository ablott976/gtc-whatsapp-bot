from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WhatsApp
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # Admin
    admin_password: str = "admin123"

    # Database
    database_url: str = "sqlite+aiosqlite:///./gtc_bot.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
