from sqlalchemy import URL

from app.core.config import Settings


def test_settings_builds_database_url_from_db_fields() -> None:
    settings = Settings(
        database_url=None,
        db_host="localhost",
        db_port=5432,
        db_name="communiti_dev",
        db_user="postgres",
        db_password="p@ss/word:with#chars",
    )

    url = settings.sqlalchemy_database_url

    assert isinstance(url, URL)
    assert url.drivername == "postgresql+asyncpg"
    assert url.username == "postgres"
    assert url.password == "p@ss/word:with#chars"
    assert url.host == "localhost"
    assert url.port == 5432
    assert url.database == "communiti_dev"
