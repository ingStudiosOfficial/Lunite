# Environment
# -----------

from core.errors import *

# ==========================================
# ENVIRONMENT
# ==========================================

class Environment:
    __slots__ = ('values', 'constants', 'parent', 'permissions')
    def __init__(self, parent=None):
        self.values = {}
        self.constants = set()
        self.permissions = {}
        self.parent = parent

    def get(self, name, line, col):
        current = self
        while current is not None:
            if name in current.values:
                return current.values[name]
            current = current.parent
            
        raise lunite_error("Runtime", f"Variable '{name}' is undefined", line, col)

    def define(self, name, value, is_const=False, is_public=True):
        self.values[name] = value
        self.permissions[name] = {'public': is_public}
        if is_const:
            self.constants.add(name)

    def is_public(self, name):
        if name in self.permissions:
            return self.permissions[name]['public']
        return True

    def assign(self, name, value, line, col):
        current = self
        while current is not None:
            if name in current.values:
                if name in current.constants:
                    raise lunite_error("Runtime", f"Cannot reassign constant '{name}'", line, col)
                current.values[name] = value
                return
            current = current.parent
            
        raise lunite_error("Runtime", f"Undefined variable '{name}' cannot be assigned a value", line, col)