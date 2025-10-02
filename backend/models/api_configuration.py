from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, Text
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict
from models.base import Base


class ApiProvider(Enum):
    NVD = "nvd"
    CISA_KEV = "cisa_kev"
    EXPLOITDB = "exploitdb"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class ApiConfiguration(Base):
    """Database model for API configuration"""
    __tablename__ = "api_configurations"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    rate_limit_calls = Column(Integer, nullable=False)
    rate_limit_period = Column(Integer, nullable=False)  # seconds
    timeout = Column(Integer, nullable=False)  # seconds
    retry_attempts = Column(Integer, default=3)
    circuit_breaker_threshold = Column(Integer, default=5)
    health_check_interval = Column(Integer, default=300)  # seconds
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ApiUsageMetrics(Base):
    """Database model for API usage tracking"""
    __tablename__ = "api_usage_metrics"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    calls_made = Column(Integer, default=0)
    calls_successful = Column(Integer, default=0)
    calls_failed = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)  # milliseconds
    quota_used = Column(Integer, nullable=True)
    quota_limit = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, default=func.now())


class ApiHealthStatus(Base):
    """Database model for API health monitoring"""
    __tablename__ = "api_health_status"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False)  # healthy, degraded, down
    last_check = Column(DateTime, default=func.now())
    consecutive_failures = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    response_time = Column(Float, nullable=True)  # milliseconds


# Pydantic models for API serialization
class ApiConfigurationResponse(BaseModel):
    id: str
    provider: str
    enabled: bool
    rate_limit_calls: int
    rate_limit_period: int
    timeout: int
    retry_attempts: int
    circuit_breaker_threshold: int
    health_check_interval: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiConfigurationUpdate(BaseModel):
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    rate_limit_calls: Optional[int] = None
    rate_limit_period: Optional[int] = None
    timeout: Optional[int] = None
    retry_attempts: Optional[int] = None
    circuit_breaker_threshold: Optional[int] = None
    health_check_interval: Optional[int] = None


class ApiUsageMetricsResponse(BaseModel):
    id: str
    provider: str
    calls_made: int
    calls_successful: int
    calls_failed: int
    average_response_time: float
    quota_used: Optional[int]
    quota_limit: Optional[int]
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiHealthStatusResponse(BaseModel):
    id: str
    provider: str
    status: str
    last_check: datetime
    consecutive_failures: int
    error_message: Optional[str]
    response_time: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class ApiProviderConfig(BaseModel):
    """Configuration constants for API providers"""
    provider: ApiProvider
    default_rate_limit_calls: int
    default_rate_limit_period: int
    default_timeout: int
    requires_api_key: bool


# Default configurations for each provider
DEFAULT_PROVIDER_CONFIGS = {
    ApiProvider.NVD: ApiProviderConfig(
        provider=ApiProvider.NVD,
        default_rate_limit_calls=1,
        default_rate_limit_period=6,  # 6-second delay as per NFR7
        default_timeout=30,
        requires_api_key=True
    ),
    ApiProvider.CISA_KEV: ApiProviderConfig(
        provider=ApiProvider.CISA_KEV,
        default_rate_limit_calls=10,
        default_rate_limit_period=60,  # 10 calls per minute
        default_timeout=30,
        requires_api_key=False
    ),
    ApiProvider.EXPLOITDB: ApiProviderConfig(
        provider=ApiProvider.EXPLOITDB,
        default_rate_limit_calls=30,
        default_rate_limit_period=60,  # 30 calls per minute
        default_timeout=30,
        requires_api_key=False
    )
}