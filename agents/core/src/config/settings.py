# src/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, ClassVar

class Settings(BaseSettings):
    # Database settings
    POSTGRES_USER: str = "athena"
    POSTGRES_PASSWORD: str = "athenapassword" 
    POSTGRES_DB: str = "athenadb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # PgAdmin settings
    PGADMIN_EMAIL: str = "admin@athena.ai"
    PGADMIN_PASSWORD: str = "admin"

    # Service settings
    LOKI_URL: str = "http://localhost:3100"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_AUTH_TOKEN: Optional[str] = None
    OLLAMA_HOST: str = "localhost"
    OLLAMA_PORT: int = 11434
    MODEL_NAME: str = "mistral"
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "athenapass"

    # Metrics configuration
    METRIC_CONFIG: ClassVar[Dict[str, Any]] = {
        'model_dir': 'models/metrics',
        'min_training_samples': 24,
        'training_frequency_hours': 24,
        'default_prediction_horizon': 24
    }
    
    PROPHET_CONFIG: ClassVar[Dict[str, Any]] = {
        'changepoint_prior_scale': 0.05,
        'seasonality_prior_scale': 10.0,
        'holidays_prior_scale': 10.0,
        'seasonality_mode': 'multiplicative'
    }
    
    METRIC_THRESHOLDS: ClassVar[Dict[str, float]] = {
        'cpu_usage': 80.0,
        'memory_usage': 85.0,
        'disk_usage': 90.0,
        'default': 75.0
    }

    def get_database_url(self) -> str:
        """Get the database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from env file

# Instance singleton
settings = Settings()