#!/usr/bin/env python3
"""
settings.py
Purpose: Application configuration management
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Environment-specific configuration settings and database connection management
"""

import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "sqlite:///C:/Users/write/Projects/AI_Collab_Online/instance/ai_collab.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pooling for better performance (PostgreSQL only)
    if os.environ.get("DATABASE_URL") and "postgresql" in os.environ.get("DATABASE_URL", ""):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'max_overflow': 20
        }
    else:
        # SQLite configuration (no pooling needed)
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # Static asset configuration for production
    STATIC_FOLDER = "static"
    STATIC_URL_PATH = "/static"

    # Cache configuration for mobile assets
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static assets

    # Caching configuration
    CACHE_TYPE = "simple"  # Use Redis in production
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = "ai_collab_"
    
    # Session caching
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Mobile-specific settings
    MOBILE_CACHE_VERSION = "2.0"  # Version for cache busting
    MOBILE_FEATURES_ENABLED = True

    # Production-specific settings
    PRODUCTION_MODE = os.environ.get("FLASK_ENV") == "production"

    # Asset compression settings
    COMPRESS_HTML = True
    COMPRESS_CSS = True
    COMPRESS_JS = True

    # AI Service settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")

    # Rate limiting settings
    REDIS_URL = os.getenv("REDIS_URL")

    # Feature flags
    REFINE_V2_ENABLED = os.getenv("REFINE_V2_ENABLED", "false").lower() == "true"

    # Trial mode (scaffold)
    TRIAL_ENABLED = os.getenv("TRIAL_ENABLED", "false").lower() == "true"
    TRIAL_TTL_DAYS = int(os.getenv("TRIAL_TTL_DAYS", "7") or 7)
    TRIAL_MAX_REFINES = int(os.getenv("TRIAL_MAX_REFINES", "3") or 3)

    # Room limits
    ROOM_MAX_CHATS = int(os.getenv("ROOM_MAX_CHATS", "25") or 25)

    # Google Docs settings
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "service-account-key.json"
    )

    # Production settings
    DEBUG = False
    TESTING = False

    # Security settings
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Logging
    LOG_LEVEL = "INFO"
    
    # Enhanced logging configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'file': {
                'level': 'INFO',
                'formatter': 'detailed',
                'class': 'logging.FileHandler',
                'filename': 'logs/ai_collab.log',
                'mode': 'a',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': True
            },
            'src': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
        }
    }

    @staticmethod
    def init_app(app):
        """Initialize application-specific settings."""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False

    # Development-specific mobile settings
    MOBILE_CACHE_VERSION = "dev"
    MOBILE_FEATURES_ENABLED = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False

    # Production-specific mobile settings
    MOBILE_CACHE_VERSION = "2.0"
    MOBILE_FEATURES_ENABLED = True

    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Static asset optimization
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year

    # Production logging
    LOG_LEVEL = "WARNING"

    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings."""
        Config.init_app(app)

        # Production logging setup
        import logging
        from logging.handlers import RotatingFileHandler

        if not app.debug and not app.testing:
            # File logging
            if not os.path.exists("logs"):
                os.makedirs("logs", exist_ok=True)
            file_handler = RotatingFileHandler(
                "logs/ai_collab.log", maxBytes=10240, backupCount=10
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info("AI Collab Online startup")


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Disable mobile features for testing
    MOBILE_FEATURES_ENABLED = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
