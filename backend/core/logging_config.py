"""
Logging configuration for the application to ensure logs are captured by CloudWatch.
"""
import logging
import sys


def setup_logging():
    """Configure application logging to output to stdout for CloudWatch."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing configuration
    )

    # Set specific loggers if needed
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('agentic-system').setLevel(logging.INFO)

    # Log that logging has been configured
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully for CloudWatch")

