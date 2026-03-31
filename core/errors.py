# Errors
# ------

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class ColoramaFallback:
        def __getattr__(self, name): return ""
    Fore = Style = ColoramaFallback()

import core.constants as constants
from core.constants import *


# ==========================================
# CUSTOM EXCEPTION FORMATTER
# ==========================================

def lunite_error(kind, message, line=None, col=None):
    loc = ""
    file = constants.CURRENT_FILE
    if line is not None and col is not None:
        loc = f"\n{Fore.MAGENTA}   File:{Style.RESET_ALL} {file}:{line}:{col}"

    e = Exception(f"{Fore.RED}{kind} Error:{Style.RESET_ALL} {message}{loc}")
    e.has_location = True
    e.message_only = message
    return e

# ==========================================
# JUMP EXCEPTIONS
# ==========================================

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class BreakException(Exception): pass

class AdvanceException(Exception): pass

class LeapException(Exception): 
    def __init__(self, target):
        self.target = target