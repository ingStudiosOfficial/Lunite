# Types
# -----

from core.constants import *
from core.errors import *

# ==========================================
# RUNTIME DATA TYPE WRAPPERS
# ==========================================

class LBit(int):
    def __new__(cls, value):
        val = int(value)
        if val not in (0, 1):
            raise ValueError("The Bit data type must be 0 or 1")
        return super().__new__(cls, val)
    def __repr__(self): return f"{int(self)}"

class LByte(int):
    def __new__(cls, value):
        val = int(value)
        if val < 0 or val > 255:
            raise ValueError("The Byte data type must be 0 to 255")
        return super().__new__(cls, val)
    def __repr__(self): return f"{int(self)}"

class LChar(str):
    def __new__(cls, value):
        if len(value) != 1:
            raise ValueError("The Char data type must be exactly of length 1")
        return super().__new__(cls, value)
    def __repr__(self): return f"'{self}'"

# ==========================================
# LUNITE INSTANCE
# ==========================================

class LuniteInstance:
    def __init__(self, mold_node):
        self.mold = mold_node
        self.fields = {}
        self.constants = set()
        self.methods = {}
    
    def get(self, name, line, col):
        if name in self.fields:
            return self.fields[name]
        if name in self.methods:
            return self.methods[name]
        raise lunite_error("Runtime", f"Class '{self.mold.name}' does not contain the property '{name}'", line, col)

    def set(self, name, val):
        if name in self.constants:
            raise Exception(f"Cannot reassign read-only property '{name}'")
        self.fields[name] = val

    def __repr__(self):
        return f"<Instance of {self.mold.name}>"
