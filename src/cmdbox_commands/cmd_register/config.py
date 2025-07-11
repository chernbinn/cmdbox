import os

def is_debug():
    return os.environ.get('CMD_REGISTER_DEBUG', '0') == '1'



