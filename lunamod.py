#!/usr/bin/env python3
"""
Official Lunite Module Importer
Python helper module for importing Lunite (.luna) modules.
https://github.com/SubhrajitSain/Lunite
"""

import inspect
import os
from core.lexer import Lexer
from core.parser import Parser
from runtime.interpreter import Interpreter
import core.constants as constants

__all__ = ["import_module", "import_", "load", "from_import", "LunaModule"]

_loaded_modules = {}


def _caller_dir():
    for frame_info in inspect.stack()[2:]:
        frame_file = os.path.abspath(frame_info.filename)
        if frame_file != os.path.abspath(__file__):
            return os.path.dirname(frame_file)
    return os.getcwd()


def _res_path(module_name):
    if not isinstance(module_name, str):
        raise TypeError("module_name must be a string")

    if not module_name.endswith('.luna'):
        module_name = module_name + '.luna'

    if os.path.isabs(module_name):
        candidate = os.path.normpath(module_name)
        if os.path.exists(candidate):
            return candidate
        raise FileNotFoundError(f"Lunite module not found: {candidate}")

    cwd_candidate = os.path.normpath(os.path.join(os.getcwd(), module_name))
    caller_candidate = os.path.normpath(os.path.join(_caller_dir(), module_name))

    if os.path.exists(caller_candidate):
        return caller_candidate
    if os.path.exists(cwd_candidate):
        return cwd_candidate

    raise FileNotFoundError(f"Lunite module not found: {module_name}")


def _read_source(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


class LuniteMod:
    def __init__(self, path, exports):
        self.__path = os.path.abspath(path)
        self.__exports = exports
        for name, value in exports.items():
            setattr(self, name, value)

    def __repr__(self):
        return f"<Lunite module {os.path.basename(self.__path)}>"

    def __getitem__(self, name):
        return self.__exports[name]

    def __iter__(self):
        return iter(self.__exports)

    def keys(self):
        return list(self.__exports.keys())

    def items(self):
        return list(self.__exports.items())

    def values(self):
        return list(self.__exports.values())

    @property
    def path(self):
        return self.__path

    @property
    def exports(self):
        return dict(self.__exports)

    def __getattr__(self, name):
        if name in self.__exports:
            return self.__exports[name]
        raise AttributeError(f"Lunite module has no attribute '{name}'")


def _compile_mod(module_path):
    module_path = os.path.abspath(module_path)
    if module_path in _loaded_modules:
        return _loaded_modules[module_path]

    source = _read_source(module_path)
    interpreter = Interpreter()
    interpreter.global_env = interpreter.global_env

    builtin_names = set(interpreter.global_env.values.keys())

    old_file = constants.CURRENT_FILE
    try:
        constants.CURRENT_FILE = module_path
        lexer = Lexer(source)
        tokens = list(lexer)

        parser = Parser(tokens)
        ast = parser.parse()
        interpreter.visit(ast)
    finally:
        constants.CURRENT_FILE = old_file

    exports = {
        name: value
        for name, value in interpreter.global_env.values.items()
        if name not in builtin_names and interpreter.global_env.is_public(name)
    }

    module = LuniteMod(module_path, exports)
    _loaded_modules[module_path] = module
    return module

def import_module(module_name):
    """Import a Lunite module and return a Python wrapper object."""
    module_path = _res_path(module_name)
    return _compile_mod(module_path)

def load(module_name):
    """Alias for import_module"""
    return import_module(module_name)

def imp(module_name):
    """Alias for import_module"""
    return import_module(module_name)

def from_import(module_name, *names, into=None):
    """Import public names from a Lunite module into a mapping.

    If `into` is not provided, the function injects names into the caller's globals.
    Returns the dictionary of imported names.
    """
    module = import_module(module_name)
    if not names or names == ('*',):
        names = tuple(module.keys())

    selected = {}
    for name in names:
        if name not in module.keys():
            raise ImportError(f"Lunite module '{module_name}' does not export '{name}'")
        selected[name] = getattr(module, name)

    if into is None:
        caller_frame = inspect.currentframe().f_back
        try:
            into = caller_frame.f_globals
        finally:
            del caller_frame

    into.update(selected)
    return selected

def fimp(module_name, *names, into=None):
    """Alias for from_import"""
    from_import(module_name, *names, into)