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
from core.lbvm import save_bytecode, run_bytecode
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

def run_code(source, debug=False, sandbox=False):
    try:
        preprocessor = Preprocessor()
        source = preprocessor.process(source)

        lexer = Lexer(source)
        tokens = list(lexer)

        parser = Parser(tokens)
        ast = parser.parse()

        if debug:
            print(f"{Fore.YELLOW}[DEBUG]{Style.RESET_ALL} Tokens:")
            for tok in tokens:
                print(f"  {tok.type} {tok.value!r} ({tok.line}:{tok.col})")
            print(f"{Fore.YELLOW}[DEBUG]{Style.RESET_ALL} AST:")
            print(ast)

        interpreter = Interpreter(safe_mode=sandbox, debug=debug)
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
    buffer = []
    prompt_main = f"{Fore.GREEN}lunite>{Style.RESET_ALL} "
    prompt_more = f"{Fore.YELLOW}......>{Style.RESET_ALL} "

    while True:
        try:
            prompt = prompt_main if not buffer else prompt_more
            line = input(prompt)
            if line.strip() in ["exit", "quit"]:
                break
            if line.strip() == "help":
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
                print("  compile <file.luna> --> compile code to .lunac")
                print("  sandbox <file.luna> --> run code in a safe environment")
                print("  debug <file.luna> --> run code with debug output")
                print("  build <file.luna> --> bind and compile code into an executable")
                print("  clean             --> deletes build directories")
                print("  version           --> display version information")
                print()
                print("Visit for more info:")
                print("  https://github.com/SubhrajitSain/Lunite")
                print()
                buffer = []
                continue

            if line.strip() == "":
                if not buffer:
                    continue
                source = "\n".join(buffer)
                buffer = []
            else:
                buffer.append(line)
                source = "\n".join(buffer)
                brace_balance = source.count("{") - source.count("}")
                if brace_balance > 0 or line.rstrip().endswith('\\'):
                    continue
                if brace_balance != 0 and not line.strip():
                    continue

            try:
                text = preprocessor.process(source)
                lexer = Lexer(text)
                tokens = list(lexer)
                ast = Parser(tokens).parse()

                if isinstance(ast, Block):
                    for stmt in ast.statements:
                        res = interpreter.visit(stmt)
                        if res is not None:
                            print(interpreter.global_env.values.get('str')(res))
                buffer = []
            except Exception as e:
                print(str(e))
                buffer = []
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            buffer = []
            continue


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

def compile_to_bytecode(filename):
    if not filename.lower().endswith('.luna'):
        raise ValueError(f"Compile: Not a .luna source file: '{filename}'")

    print("Compile: Reading source...")
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()

    print("Compile: Compiling, this may take a few seconds...")
    preprocessor = Preprocessor()
    source = preprocessor.process(source)

    bytecode_path = filename[:-5] + '.lunac'
    save_bytecode(bytecode_path, source, source_file=os.path.abspath(filename))
    print(f"Compile: Compiled to bytecode file: '{bytecode_path}'")
    return bytecode_path


def _print_header():
    print("The Lunite Programming Language")
    print(LUNITE_VERSION_STR)
    print(COPYRIGHT)
    print("-------------------------------")


def run_file_path(path, debug=False, sandbox=False):
    if path.lower().endswith('.lunac'):
        run_bytecode(path, debug=debug, sandbox=sandbox)
        return

    if not os.path.exists(path):
        raise FileNotFoundError(f"Run: File not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    constants.CURRENT_FILE = os.path.abspath(path)
    run_code(source, debug=debug, sandbox=sandbox)


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
    path = sys.argv[2] if len(sys.argv) > 2 else None

    if command == 'compile':
        if not path:
            print("Compile: File not provided.")
            return
        try:
            compile_to_bytecode(path)
        except Exception as e:
            print(str(e))
        return

    if command == 'run':
        if not path:
            print("Run: File not provided.")
            return
        try:
            run_file_path(path)
        except Exception as e:
            print(str(e))
        return

    if command == 'sandbox':
        if not path:
            print("Sandbox: File not provided.")
            return
        try:
            run_file_path(path, sandbox=True)
        except Exception as e:
            print(str(e))
        return

    if command == 'debug':
        if not path:
            print("Debug: File not provided.")
            return
        try:
            run_file_path(path, debug=True)
        except Exception as e:
            print(str(e))
        return

    if command == 'build':
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
            print("Build: Aborted by user.")
            return
        else:
            print("Build: Unknown choice for continue prompt, aborting.")
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
            print("Clean: Aborted by user.")
            return
        else:
            print("Clean: Unknown choice for continue prompt, aborting.")
            return

    elif command == 'version':
        _print_header()
        return

    if command.lower().endswith('.luna') or command.lower().endswith('.lunac'):
        try:
            run_file_path(command)
        except Exception as e:
            print(str(e))
        return
        
    print("The Lunite Programming Language")
    print(LUNITE_VERSION_STR)
    print(COPYRIGHT)
    print("-------------------------------")
    print(f"Unknown command '{command}'.")

    print("\nPossible commands:")
    print("  <no command>              --> start Lunite REPL CLI")
    print("  run <file.luna/lunac>     --> execute a Lunite source or bytecode file")
    print("  compile <file.luna>       --> compile source to .lunac")
    print("  sandbox <file.luna/lunac> --> run code in a safe environment")
    print("  debug <file.luna/lunac>   --> run code with debug output")
    print("  build <file.luna>         --> bind and compile code into an executable")
    print("  clean                     --> deletes build directories")
    print("  version                   --> display version information")

if __name__ == "__main__":
    main()