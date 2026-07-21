from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FSBackup"
    version: str = "0.1.0"
    debug: bool = True


settings = Settings()