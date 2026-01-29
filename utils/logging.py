import logging
import sys

# Configure Global Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log")
    ]
)

logger = logging.getLogger("PhillySniper")

def log(step, message):
    """
    Log messages using the standard logging framework.
    Maps legacy 'step' categories to log prefixes.
    """
    prefix = f"[{step}]"
    logger.info(f"{prefix} {message}")

def log_error(step, message):
    """Explicit error logging."""
    logger.error(f"[{step}] {message}")
