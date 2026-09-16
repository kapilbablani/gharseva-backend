from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cognito_user_pool_id: str
    cognito_app_client_id: str
    aws_region: str

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
