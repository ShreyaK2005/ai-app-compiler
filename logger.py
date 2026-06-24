import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_compiler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("app_compiler")


def log_info(message: str):
    logger.info(message)


def log_error(message: str):
    logger.error(message)


def log_warning(message: str):
    logger.warning(message)


def log_debug(message: str):
    logger.debug(message)


def log_stage(stage_name: str, status: str):
    """Log a stage transition"""
    log_info(f"{'='*60}")
    log_info(f"STAGE: {stage_name.upper()} - {status}")
    log_info(f"{'='*60}")