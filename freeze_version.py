# freeze_version.py
import logging
import logger_config
import sys
from git_versioning_callback import (
    commit_update_version
)
logger = logger_config.get_print_logger(__name__, logging.DEBUG)
    
def main():
    version = commit_update_version()
    if not version:
        return 1
    logger.info(f"new_version: {version}")
    return 0

if __name__ == '__main__':
    logger.debug(f"{__file__}:{__name__}")
    sys.exit(main())