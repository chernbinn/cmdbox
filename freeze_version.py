# freeze_version.py
from pathlib import Path
import sys
import logging
import logger_config

logger = logger_config.get_print_logger(__name__, logging.DEBUG)

_version_file = Path(__file__).parent / "src" / "cmdbox" / "_version.py"

def get_git_versioning_version():
    from git_versioning_callback import get_git_versioning_version
    version = get_git_versioning_version(_version_file)
    print(f"get_git_versioning_version: {version}")
    return version

def main():
    global _version_file

    version = None
    #version = get_detailed_version().get('full')
    #version = setuptools_scm_version()
    #from git_versioning_callback import setuptools_git_versioning_version
    #version = setuptools_git_versioning_version()

    from git_versioning_callback import check_msg_valid
    if not check_msg_valid(_version_file):
        return 1
    get_git_versioning_version()
    if version:
        version_file = _version_file
        with version_file.open('w') as f:
            f.write(f'__version__ = "{version}"\n')
    
        print(f"Version {version} written to {version_file}")
    return 0

if __name__ == '__main__':
    logger.debug(f"{__file__}:{__name__}")
    sys.exit(main())