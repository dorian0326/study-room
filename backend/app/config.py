"""应用配置：通过环境变量（前缀 STUDYROOM_）或 .env 覆盖。"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_GATE_SECRET = "local-development-only-change-this-secret"


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
    # 默认 60 秒；与 #33 的固定一分钟扫描兼容，测试中设为 0。
    reservation_sweep_interval_seconds: float = Field(60, ge=0)

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

    # 门禁同步采用脱敏 keyed hash；部署时必须通过 STUDYROOM_GATE_HMAC_SECRET 覆盖开发值。
    gate_hmac_secret: str = INSECURE_GATE_SECRET
    # 运行环境：dev / test 允许使用开发默认密钥，其他环境（如 prod）必须覆盖。
    env: str = "dev"

    @model_validator(mode="after")
    def _require_gate_secret(self) -> "Settings":
        """非开发/测试环境仍使用默认门禁密钥时拒绝启动。"""
        if self.env not in ("dev", "test") and self.gate_hmac_secret == INSECURE_GATE_SECRET:
            raise ValueError(
                "STUDYROOM_GATE_HMAC_SECRET 仍为不安全的开发默认值；"
                f"STUDYROOM_ENV={self.env} 时必须设置独立密钥。"
            )
        return self

    # ---- 登录锁定 ----
    # 连续失败次数阈值；0 表示关闭锁定。默认 5 次失败锁定 15 分钟。
    login_max_failures: int = Field(5, ge=0)
    login_lockout_minutes: int = Field(15, ge=1)

    # ---- 日志（#8）----
    # 操作日志、登录日志保留天数（BR-105：保留一个学期，按 180 天计）
    log_retention_days: int = 180
    backup_dir: str = "./data/backups"
    backup_keep: int = 14
    # 定时备份/日志清理间隔（秒）；0 关闭后台任务（测试默认 0）。生产建议 86400。
    backup_interval_seconds: float = Field(0, ge=0)
    log_purge_interval_seconds: float = Field(0, ge=0)


@lru_cache
def get_settings() -> Settings:
    """读取并缓存由环境变量及后端 .env 文件覆盖的运行配置。"""
    return Settings()
