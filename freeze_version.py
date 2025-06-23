# freeze_version.py
from pathlib import Path
import sys
import logging
import logger_config
from git_versioning_callback import (
    check_staged_msg_valid,
    setup_git_versioning_version
)

logger = logger_config.get_print_logger(__name__, logging.DEBUG)

_version_file = Path(__file__).parent / "src" / "cmdbox" / "_version.py"

def get_git_versioning_version():
    if not check_staged_msg_valid(_version_file):
        return 1
    version = setup_git_versioning_version(_version_file)
    logger.info(f"get_git_versioning_version: {version}")
    return 0

def main():
    return get_git_versioning_version()

if __name__ == '__main__':
    logger.debug(f"{__file__}:{__name__}")
    sys.exit(main())