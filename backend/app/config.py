"""应用配置：通过环境变量（前缀 STUDYROOM_）或 .env 覆盖。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDYROOM_", env_file=".env", extra="ignore")

    app_name: str = "study-room"
    # SQLite 数据库文件路径（相对 backend/ 目录）
    database_url: str = "sqlite:///./data/study_room.db"
    # 统一时间基准 Asia/Shanghai UTC+8（HD-39）
    timezone: str = "Asia/Shanghai"
    # SQLite 写锁等待时间（毫秒）
    sqlite_busy_timeout_ms: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
