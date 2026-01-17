import time
import sys
import os
import importlib
import contextlib
import io
from colorama import Fore, Back, Style
from tqdm import tqdm

if not os.path.exists("lunite.py"):
    print(f"{Fore.RED}Error: lunite.py not found in this directory.{Style.RESET_ALL}")
    sys.exit(1)

def benchmark_import(iterations=10):
    print(f"{Fore.CYAN}[ Module Import Speed ({iterations} runs) ]{Style.RESET_ALL}")
    times = []

    for _ in tqdm(range(iterations), desc="Importing", colour="cyan"):
        if 'lunite' in sys.modules:
            del sys.modules['lunite']
        
        start = time.perf_counter()
        import lunite
        end = time.perf_counter()
        times.append((end - start) * 1000)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"{Fore.GREEN}Average: {avg_time:.4f} ms{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Best   : {min_time:.4f} ms{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Worst  : {max_time:.4f} ms{Style.RESET_ALL}")
    print("")

def benchmark_lexer(iterations=20):
    print(f"{Fore.CYAN}[ Lexer Throughput ({iterations} runs) ]{Style.RESET_ALL}")
    
    code = """
    let x = 100.50;
    let name = "Lunite Speed Test";
    func calculate(a, b) { return a + b * 10; }
    class Test { func init() { this.val = true; } }
    """ * 1000

    import lunite
    
    times = []
    token_count = 0

    for _ in tqdm(range(iterations), desc="Lexing", colour="cyan"):
        start = time.perf_counter()
        
        lexer = lunite.Lexer(code)
        count = 0
        while True:
            t = lexer.get_next_token()
            count += 1
            if t.type == lunite.TOKEN_EOF: break
        
        end = time.perf_counter()
        times.append((end - start) * 1000)
        token_count = count

    avg_time = sum(times) / len(times)
    print(f"{Fore.BLUE}Source Size : {len(code) / 1024:.2f} KB (Generated){Style.RESET_ALL}")
    print(f"{Fore.BLUE}Token Count : {token_count} tokens{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Average Time: {avg_time:.4f} ms{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Speed       : {token_count / (avg_time/1000):.0f} tokens/sec{Style.RESET_ALL}")
    print("")

def benchmark_execution(iterations=3):
    filename = "demos/stresstest.luna"
    
    if not os.path.exists(filename):
        print(f"{Fore.CYAN}[ Full Stress Test Execution Speed ]{Style.RESET_ALL}")
        print(f"{Fore.RED}Error: '{filename}' not found. Cannot run execution benchmark.{Style.RESET_ALL}")
        return

    with open(filename, "r") as f:
        luna_code = f.read()

    print(f"{Fore.CYAN}[ Full Execution Speed ({iterations} runs) ]{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Target File : {filename}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}File Size   : {len(luna_code)} bytes{Style.RESET_ALL}")
    
    import lunite
    times = []

    for _ in tqdm(range(iterations), desc="Executing", colour="cyan"):
        with contextlib.redirect_stdout(io.StringIO()):
            start = time.perf_counter()
            lunite.run_code(luna_code)
            end = time.perf_counter()
            times.append((end - start) * 1000)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"{Fore.GREEN}Average Time: {avg_time:.4f} ms{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Best Run    : {min_time:.4f} ms{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Worst Run   : {max_time:.4f} ms{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.YELLOW}{Style.BRIGHT}Starting Lunite Speed Test...{Style.RESET_ALL}\n")
    try:
        benchmark_import()
        benchmark_lexer()
        benchmark_execution()
    except KeyboardInterrupt:
        print("\nAborted.")