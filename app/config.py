import pydantic_settings import BaseSettings, SettingsConfig

class PostgresSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="PSQL_DB_")

    username: str
    password: str
    host: str
    database: str

postgres_settings = PostgresSettings()


DATABASE_URL = "postgres://{}:{}@{}:{}/{}".format(
    postgres_settings.username,
    postgres_settings.password,
    postgres_settings.host,
    postgres_settings.port,
    postgres_settings.database,
)

models = ["app.authentication.models", "aerich.models"]