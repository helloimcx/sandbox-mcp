"""Configuration management for the sandbox MCP server."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=16010, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Security
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    allowed_hosts: list[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Kernel configuration
    kernel_timeout: int = Field(default=300, env="KERNEL_TIMEOUT")
    max_kernels: int = Field(default=10, env="MAX_KERNELS")
    kernel_cleanup_interval: int = Field(default=60, env="KERNEL_CLEANUP_INTERVAL")
    
    # Resource limits
    max_execution_time: int = Field(default=30, env="MAX_EXECUTION_TIME")
    max_memory_mb: int = Field(default=512, env="MAX_MEMORY_MB")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()