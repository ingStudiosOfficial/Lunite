#!/usr/bin/env python3
# /== == == == == == == == == == ==\
# |==  LUNITE - v1.9.6 - by ANW  ==|
# \== == == == == == == == == == ==/

import sys
import os
import shutil
import platform
import subprocess
import json
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class ColoramaFallback:
        def __getattr__(self, name): return ""
    Fore = Style = ColoramaFallback()

import core.constants as constants
from core.constants import *
from core.errors import *
from core.types import *
from core.ast import *
from core.lexer import *
from core.parser import *
from core.preprocessor import *

from runtime.interpreter import *
from runtime.environment import *

# ==========================================
# VENV DETECTION AND PYTHON PATH
# ==========================================

def get_python_venv():
    cwd = os.getcwd()
    venv_names = ["venv", ".venv", "env"]
    is_win = platform.system() == "Windows"
    
    for venv in venv_names:
        if is_win:
            path = os.path.join(cwd, venv, "Scripts", "python.exe")
        else:
            path = os.path.join(cwd, venv, "bin", "python")
            
        if os.path.exists(path):
            return path
            
    return sys.executable

# ==========================================
# CLI & BUILDER
# ==========================================

def run_code(source):
    try:
        preprocessor = Preprocessor()
        source = preprocessor.process(source)

        lexer = Lexer(source)
        tokens = []
        while True:
            tok = lexer.get_next_token()
            tokens.append(tok)
            if tok.type == TOKEN_EOF: break
        
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.visit(ast)

    except (LeapException, BreakException, AdvanceException, ReturnException) as e:
        print(f"{Fore.RED}Runtime Error: Control flow error ({type(e).__name__}){Style.RESET_ALL}")
    except Exception as e:
        print(str(e))

# [RUNTIME BINDED CODE END]

def start_repl():
    constants.CURRENT_FILE = "REPL"
    print(f"{Fore.CYAN}Lunite {LUNITE_VERSION_STR} REPL CLI{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{COPYRIGHT}{Style.RESET_ALL}")
    
    interpreter = Interpreter()
    preprocessor = Preprocessor()
    while True:
        try:
            text = input(f"{Fore.GREEN}lunite>{Style.RESET_ALL} ")
            if text.strip() in ["exit", "quit"]: break
            if text.strip() == "help":
                print("Lunite REPL Help")
                print("----------------")
                print()
                print("Commands:")
                print("  help              --> shows this help message")
                print("  exit              --> exit the REPL")
                print("  quit              --> same as exit")
                print()
                print("CLI commands:")
                print("  <no command>      --> start Lunite REPL CLI")
                print("  run <file.luna>   --> interpret a Lunite source code file")
                print("  build <file.luna> --> bind and compile code into an executable")
                print("  clean             --> deletes build directories")
                print("  version           --> display version information")
                print()
                print("Visit for more info:")
                print("  https://github.com/SubhrajitSain/Lunite")
                print()
                continue
            if not text.strip(): continue

            text = preprocessor.process(text)
            lexer = Lexer(text)
            tokens = []
            while True:
                t = lexer.get_next_token()
                tokens.append(t)
                if t.type == TOKEN_EOF: break
            
            ast = Parser(tokens).parse()
            if isinstance(ast, Block):
                for stmt in ast.statements:
                    res = interpreter.visit(stmt)
                    if res is not None:
                        print(interpreter.global_env.values.get('str')(res))
        except Exception as e:
            print(str(e))

def compile_code(filename):
    with open(filename, 'r') as f:
        print(f"Build: Opened source '{filename}' to read.")
        source = f.read()
        print(f"Build: Read source file.")

    print(f"Build: Preprocessing source...")
    preprocessor = Preprocessor()
    source = preprocessor.process(source)
    
    this_file = os.path.abspath(__file__)
    with open(this_file, 'r') as f:
        print(f"Build: Reading Lunite engine source: {this_file}")
        engine_code = f.read()
        print(f"Build: Read Lunite engine source.")

    print(f"Build: Sanitizing Lunite...")
    engine_code = engine_code.split("# [RUNTIME BINDED CODE END]")[0]
    print(f"Build: Lunite has been cleaned.")

    print(f"Build: Creating proper loader code...")
    loader_code = f"""
{engine_code}

if __name__ == "__main__":
    source_code = {json.dumps(source)}
    run_code(source_code)
"""
    print(f"Build: Created proper loader code.")

    dist_file = filename.replace('.luna', '.py')
    with open(dist_file, 'w') as f:
        print(f"Build: Writing loader code to '{dist_file}'")
        f.write(loader_code)
    
    print(f"Build: Created intermediate {dist_file}")
    
    py_bin = get_python_venv()
    if py_bin != sys.executable:
        print(f"Build: Detected virtual environment. Using: {py_bin}")
    else:
        print(f"Build: Venv not detected, using system python: {py_bin}")
        
    print("Build: Compiling with PyInstaller, this might take some time...")
    
    try:
        subprocess.check_call([py_bin, "-m", "PyInstaller", "--onefile", dist_file])
        print(f"Build: Success! Executable should be in the 'dist' folder.")
    except Exception as e:
        print(f"Build: Compilation failed: {e}")
    finally:
        if py_bin == sys.executable:
            print("Tip: If PyInstaller is installed in a venv, try activating it or creating a venv folder named 'venv', '.venv' or 'env'.")
        else:
            print("Tip: A venv (in 'venv', '.venv' or 'env' folder) was used to build your executable.")
        if os.path.exists(dist_file):
            os.remove(dist_file)
        if os.path.exists(filename.replace('.luna', '.spec')):
            os.remove(filename.replace('.luna', '.spec'))

def clean_build():
    try:
        print("Clean: Cleaning build directories...")
        shutil.rmtree("./build", ignore_errors=False)
        shutil.rmtree("./dist", ignore_errors=False)
        print("Clean: Cleanup successful.")
    except Exception as e:
        print(f"Clean error: {e}")

def main():
    if len(sys.argv) < 2:
        start_repl()
        return

    command = sys.argv[1]
    
    if command == 'run':
        if len(sys.argv) < 3:
            print("The Lunite Programming Language")
            print(LUNITE_VERSION_STR)
            print(COPYRIGHT)
            print("-------------------------------")
            print("Run failed: File not provided.")
            return
        path = sys.argv[2]
        constants.CURRENT_FILE = os.path.abspath(path)
        if os.path.exists(path):
            with open(path, 'r') as f:
                run_code(f.read())
        else:
            print("The Lunite Programming Language")
            print(LUNITE_VERSION_STR)
            print(COPYRIGHT)
            print("-------------------------------")
            print("Run failed: File not found.")

    elif command == 'build':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print("WARNING: Executable will be placed in './dist' after build by PyInstaller.")
        print("         Building can overwrite files in './build' and './dist'.")
        cnt_build = input("Continue with build? [Y/N]: ")
        if cnt_build.lower().startswith('y'):
            if len(sys.argv) < 3:
                print("Build failed: File not provided.")
                return
            print("-------------------------------")
            constants.CURRENT_FILE = os.path.abspath(sys.argv[2])
            compile_code(sys.argv[2])
        elif cnt_build.lower().startswith('n'):
            print("Build failed: Aborted by user.")
            return
        else:
            print("Build failed: Unknown choice for continue prompt, aborting.")
            return
        
    elif command == 'clean':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print("WARNING: Cleaning will remove the directories './build' and './dist'.")
        cnt_clean = input("Continue with clean? [Y/N]: ")
        if cnt_clean.lower().startswith('y'):
            print("-------------------------------")
            clean_build()
        elif cnt_clean.lower().startswith('n'):
            print("Clean failed: Aborted by user.")
            return
        else:
            print("Clean failed: Unknown choice for continue prompt, aborting.")
            return

    elif command == 'version':
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
    
    else:
        print("The Lunite Programming Language")
        print(LUNITE_VERSION_STR)
        print(COPYRIGHT)
        print("-------------------------------")
        print(f"Unknown command '{command}'.")
        
        print("\nPossible commands:")
        print("  <no command>      --> start Lunite REPL CLI")
        print("  run <file.luna>   --> interpret a Lunite source code file")
        print("  build <file.luna> --> bind and compile code into an executable")
        print("  clean             --> deletes build directories")
        print("  version           --> display version information")

if __name__ == "__main__":
    main()