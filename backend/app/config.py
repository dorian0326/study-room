"""应用配置：通过环境变量（前缀 STUDYROOM_）或 .env 覆盖。"""

from functools import lru_cache

from pydantic import Field
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
    # 未签到预约的后台检查间隔；0 关闭后台检查（例如测试），请求仍会补做检查。
    reservation_sweep_interval_seconds: float = Field(10, ge=0)

    # ---- 认证（#6）----
    # 登录会话有效期（分钟），默认 12 小时
    session_ttl_minutes: int = 12 * 60
    # 学号格式（HD-45 要求校验，具体格式待确认，先用 6–20 位字母数字）
    student_no_pattern: str = r"^[0-9A-Za-z]{6,20}$"
    # 密码策略：最短长度，且须同时包含字母和数字
    password_min_length: int = 8
    # bcrypt 成本因子（测试中调低以加速）
    bcrypt_rounds: int = 12
    # 管理员签发的密码重置码有效期（分钟）
    password_reset_ttl_minutes: int = 30

    # ---- 日志（#8）----
    # 操作日志、登录日志保留天数（BR-105：保留一个学期，按 180 天计）
    log_retention_days: int = 180
    backup_dir: str = "./data/backups"
    backup_keep: int = 14


@lru_cache
def get_settings() -> Settings:
    return Settings()
