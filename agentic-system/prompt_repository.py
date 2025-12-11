"""
Prompt Repository for managing dynamic prompt loading from AWS S3.

This module implements the Repository pattern with caching for efficient
and reliable prompt management. It supports both S3-based dynamic prompts
and fallback to local hardcoded prompts.
"""
import logging
import time
from typing import Optional, Dict, Callable
from pathlib import Path
import sys

# Add parent directory to path to import backend.core.config
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl: int = 300):
        """
        Initialize the cache.

        :param ttl: Time-to-live in seconds (default: 5 minutes)
        """
        self._cache: Dict[str, tuple[str, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from cache if not expired.

        :param key: Cache key
        :return: Cached value or None if expired/missing
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache HIT for key: {key}")
                return value
            else:
                logger.debug(f"Cache EXPIRED for key: {key}")
                del self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        """
        Set a value in cache with current timestamp.

        :param key: Cache key
        :param value: Value to cache
        """
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache SET for key: {key}")

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info("Cache cleared")


class PromptRepository:
    """
    Repository for managing prompt loading from S3 with fallback support.

    This class implements a singleton pattern and provides:
    - Lazy loading from S3
    - In-memory caching with TTL
    - Automatic fallback to local prompts on errors
    - Graceful error handling
    """

    _instance: Optional['PromptRepository'] = None

    # Prompt file names mapping
    PROMPT_FILES = {
        'speech_vocabulary_worker': 'speech_vocabulary_worker.txt',
        'speech_grammar_worker': 'speech_grammar_worker.txt',
        'speech_interaction_worker': 'speech_interaction_worker.txt',
        'speech_comprehension_worker': 'speech_comprehension_worker.txt',
        'boredom_worker': 'boredom_worker.txt',
        'master': 'master.txt',
    }

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the repository (only once due to singleton)."""
        if self._initialized:
            return

        self._settings = get_settings()
        self._cache = PromptCache(ttl=self._settings.prompts_cache_ttl)
        self._s3_client = None
        self._fallback_prompts: Dict[str, Callable[[], str]] = {}
        self._initialized = True

        logger.info(f"PromptRepository initialized with USE_S3_PROMPTS={self._settings.use_s3_prompts}")

    def _get_s3_client(self):
        """
        Lazy initialization of S3 client for public bucket access.
        Uses unsigned requests (no credentials needed) for public buckets.

        :return: boto3 S3 client or None on error
        """
        if self._s3_client is not None:
            return self._s3_client

        if not self._settings.use_s3_prompts:
            logger.info("S3 prompts disabled via configuration")
            return None

        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.config import Config

            # Validate required settings
            if not self._settings.aws_s3_bucket_name:
                logger.warning("AWS_S3_BUCKET_NAME not configured, falling back to local prompts")
                return None

            # Create client with unsigned requests for public bucket access
            self._s3_client = boto3.client(
                's3',
                region_name=self._settings.aws_region,
                config=Config(signature_version=UNSIGNED)
            )

            logger.info(f"S3 client initialized for public bucket: {self._settings.aws_s3_bucket_name}")
            return self._s3_client

        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None

    def _fetch_from_s3(self, prompt_key: str) -> Optional[str]:
        """
        Fetch a prompt from S3.

        :param prompt_key: Key identifying the prompt
        :return: Prompt content or None on error
        """
        s3_client = self._get_s3_client()
        if s3_client is None:
            return None

        if prompt_key not in self.PROMPT_FILES:
            logger.error(f"Unknown prompt key: {prompt_key}")
            return None

        file_name = self.PROMPT_FILES[prompt_key]
        s3_key = f"{self._settings.aws_s3_prompts_prefix}{file_name}"

        try:
            logger.info(f"Fetching prompt from S3: s3://{self._settings.aws_s3_bucket_name}/{s3_key}")

            response = s3_client.get_object(
                Bucket=self._settings.aws_s3_bucket_name,
                Key=s3_key
            )

            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully fetched prompt from S3: {prompt_key} ({len(content)} bytes)")
            return content

        except s3_client.exceptions.NoSuchKey:
            logger.error(f"Prompt file not found in S3: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Error fetching prompt from S3: {e}")
            return None

    def register_fallback(self, prompt_key: str, fallback_func: Callable[[], str]) -> None:
        """
        Register a fallback function for a prompt.

        :param prompt_key: Key identifying the prompt
        :param fallback_func: Function that returns the fallback prompt
        """
        self._fallback_prompts[prompt_key] = fallback_func
        logger.debug(f"Registered fallback for: {prompt_key}")

    def get_prompt(self, prompt_key: str) -> str:
        """
        Get a prompt, trying S3 first, then cache, then fallback.

        :param prompt_key: Key identifying the prompt
        :return: Prompt content
        :raises ValueError: If prompt not found and no fallback registered
        """
        # Try cache first
        cached = self._cache.get(prompt_key)
        if cached is not None:
            return cached

        # Try S3 if enabled
        if self._settings.use_s3_prompts:
            s3_content = self._fetch_from_s3(prompt_key)
            if s3_content is not None:
                self._cache.set(prompt_key, s3_content)
                return s3_content
            logger.warning(f"Failed to fetch from S3, trying fallback for: {prompt_key}")

        # Fall back to local prompt
        if prompt_key in self._fallback_prompts:
            logger.info(f"Using fallback prompt for: {prompt_key}")
            fallback_content = self._fallback_prompts[prompt_key]()
            # Don't cache fallback to allow S3 recovery on next request
            return fallback_content

        raise ValueError(f"Prompt not found and no fallback registered: {prompt_key}")

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()

    def reload_prompt(self, prompt_key: str) -> str:
        """
        Force reload a prompt from S3, bypassing cache.

        :param prompt_key: Key identifying the prompt
        :return: Fresh prompt content
        """
        logger.info(f"Force reloading prompt: {prompt_key}")

        if self._settings.use_s3_prompts:
            s3_content = self._fetch_from_s3(prompt_key)
            if s3_content is not None:
                self._cache.set(prompt_key, s3_content)
                return s3_content

        # Fall back if S3 fails
        if prompt_key in self._fallback_prompts:
            return self._fallback_prompts[prompt_key]()

        raise ValueError(f"Prompt not found: {prompt_key}")


# Global repository instance
_repository = PromptRepository()


def get_prompt_repository() -> PromptRepository:
    """Get the global prompt repository instance."""
    return _repository
