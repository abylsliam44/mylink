from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartbot_db"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/smartbot_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # App
    DEBUG: bool = True
    # Strict production frontend origin(s)
    ALLOWED_ORIGINS: str = "https://mylink-rouge.vercel.app,https://mylink.systems,https://www.mylink.systems,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    # Allow any subdomain on mylink.systems and vercel.app
    ALLOWED_ORIGIN_REGEX: str | None = r"^https://([a-z0-9-]+\.)?(mylink\.systems|vercel\.app)$"

    # AI / OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 2

    # Qdrant
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # AI policy
    AI_APPROVAL_THRESHOLD: int = 70
    AI_MAX_QUESTIONS: int = 3
    AI_TONE: str = "professional"
    
    # Autonomous Agents
    AGENT_HEALTH_CHECK_INTERVAL: int = 30
    AGENT_MAX_RETRIES: int = 3
    AGENT_QUEUE_SIZE: int = 1000
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

