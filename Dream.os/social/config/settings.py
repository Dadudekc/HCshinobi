"""
Centralized configuration for the Dream.OS social media pipeline.
Loads settings from environment variables and provides defaults.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base directories
BASE_DIR = Path(__file__).parent.parent
CONTENT_ROOT = os.getenv('CONTENT_ROOT', '/var/dreamos/content')
BLOG_OUTPUT_DIR = os.getenv('BLOG_OUTPUT_DIR', f"{CONTENT_ROOT}/posts")
SOCIAL_OUTPUT_DIR = os.getenv('SOCIAL_OUTPUT_DIR', f"{CONTENT_ROOT}/social")
TEMPLATE_DIR = os.getenv('TEMPLATE_DIR', str(BASE_DIR / 'templates'))

# Database
DB_CONFIG = {
    'type': os.getenv('DB_TYPE', 'sqlite'),
    'path': os.getenv('DB_PATH', '/var/dreamos/db/social_metrics.db')
}

# ChatGPT Scraper
CHATGPT_CONFIG = {
    'email': os.getenv('CHATGPT_EMAIL'),
    'password': os.getenv('CHATGPT_PASSWORD'),
    'session_token': os.getenv('CHATGPT_SESSION_TOKEN'),
    'headless': os.getenv('CHATGPT_HEADLESS', 'true').lower() == 'true',
    'timeout': int(os.getenv('CHATGPT_TIMEOUT', '30'))
}

# Social Media APIs
TWITTER_CONFIG = {
    'api_key': os.getenv('TWITTER_API_KEY'),
    'api_secret': os.getenv('TWITTER_API_SECRET'),
    'access_token': os.getenv('TWITTER_ACCESS_TOKEN'),
    'access_token_secret': os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
}

LINKEDIN_CONFIG = {
    'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
    'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET'),
    'access_token': os.getenv('LINKEDIN_ACCESS_TOKEN')
}

# Content Generation
CONTENT_CONFIG = {
    'max_posts_per_day': int(os.getenv('MAX_POSTS_PER_DAY', '5')),
    'min_post_interval': int(os.getenv('MIN_POST_INTERVAL', '3600')),
    'optimal_post_length': int(os.getenv('OPTIMAL_POST_LENGTH', '280')),
    'max_hashtags': int(os.getenv('MAX_HASHTAGS', '4'))
}

# Performance
PERFORMANCE_CONFIG = {
    'scraper_threads': int(os.getenv('SCRAPER_THREADS', '2')),
    'generator_threads': int(os.getenv('GENERATOR_THREADS', '2')),
    'dispatcher_threads': int(os.getenv('DISPATCHER_THREADS', '2')),
    'queue_size': int(os.getenv('QUEUE_SIZE', '100'))
}

# Monitoring
MONITORING_CONFIG = {
    'enable_metrics': os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
    'prometheus_port': int(os.getenv('PROMETHEUS_PORT', '9090')),
    'health_check_port': int(os.getenv('HEALTH_CHECK_PORT', '8080'))
}

# Retry Settings
RETRY_CONFIG = {
    'max_retries': int(os.getenv('MAX_RETRIES', '3')),
    'retry_delay': int(os.getenv('RETRY_DELAY', '300')),
    'backoff_factor': float(os.getenv('BACKOFF_FACTOR', '2.0'))
}

# Security
SECURITY_CONFIG = {
    'enable_ssl': os.getenv('ENABLE_SSL', 'true').lower() == 'true',
    'ssl_cert_path': os.getenv('SSL_CERT_PATH', '/etc/dreamos/ssl/cert.pem'),
    'ssl_key_path': os.getenv('SSL_KEY_PATH', '/etc/dreamos/ssl/key.pem')
}

# Rate Limiting
RATE_LIMIT_CONFIG = {
    'enabled': os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
    'requests': int(os.getenv('RATE_LIMIT_REQUESTS', '100')),
    'period': int(os.getenv('RATE_LIMIT_PERIOD', '3600'))
}

# Caching
CACHE_CONFIG = {
    'enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
    'type': os.getenv('CACHE_TYPE', 'redis'),
    'url': os.getenv('CACHE_URL', 'redis://localhost:6379/0'),
    'ttl': int(os.getenv('CACHE_TTL', '3600'))
}

# Cleanup
CLEANUP_CONFIG = {
    'enabled': os.getenv('CLEANUP_ENABLED', 'true').lower() == 'true',
    'interval': int(os.getenv('CLEANUP_INTERVAL', '86400')),
    'max_log_age': int(os.getenv('MAX_LOG_AGE', '2592000')),
    'max_content_age': int(os.getenv('MAX_CONTENT_AGE', '7776000'))
}

def get_all_config() -> Dict[str, Any]:
    """Get all configuration as a single dictionary."""
    return {
        'db': DB_CONFIG,
        'chatgpt': CHATGPT_CONFIG,
        'twitter': TWITTER_CONFIG,
        'linkedin': LINKEDIN_CONFIG,
        'content': CONTENT_CONFIG,
        'performance': PERFORMANCE_CONFIG,
        'monitoring': MONITORING_CONFIG,
        'retry': RETRY_CONFIG,
        'security': SECURITY_CONFIG,
        'rate_limit': RATE_LIMIT_CONFIG,
        'cache': CACHE_CONFIG,
        'cleanup': CLEANUP_CONFIG
    } 