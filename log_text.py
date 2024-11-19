# log_text.py

import logging
from logging.handlers import RotatingFileHandler


LOG_FILE = "app_logs.txt"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5)  
    ]
)

logger = logging.getLogger("app_logger")
