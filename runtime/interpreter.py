# Interpreter
# -----------

import os
import urllib.request
import json
import sys
import platform
import subprocess
import math
import random
import time
import datetime
import getpass
import hashlib
import base64
import importlib
import asyncio
import threading
import ctypes

try:
    import psutil
except ImportError:
    psutil = None

from core.errors import *
import core.constants as constants
from core.ast import *
from core.types import *
from core.parser import *

from runtime.environment import *

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class ColoramaFallback:
        def __getattr__(self, name): return ""
    Fore = Style = ColoramaFallback()


class SafeModeResourceMonitor:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.stop_event = threading.Event()
        self.prev_cpu = time.process_time()
        self.prev_time = time.time()
        self.prev_disk = self._get_disk_io_bytes()
        self.prev_net = self._get_network_io_bytes()

    def _get_memory_mb(self):
        if psutil:
            try:
                return psutil.Process().memory_info().rss / 1024.0 / 1024.0
            except Exception:
                pass

        if platform.system() == 'Windows':
            try:
                class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ('cb', ctypes.c_ulong),
                        ('PageFaultCount', ctypes.c_ulong),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t),
                    ]
                counters = PROCESS_MEMORY_COUNTERS()
                counters.cb = ctypes.sizeof(counters)
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                psapi = ctypes.WinDLL('psapi', use_last_error=True)
                hProcess = kernel32.GetCurrentProcess()
                if psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(counters), counters.cb):
                    return counters.WorkingSetSize / 1024.0 / 1024.0
            except Exception:
                pass
            return 0.0

        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        except Exception:
            return 0.0

    def _get_disk_io_bytes(self):
        if psutil:
            try:
                io = psutil.Process().io_counters()
                return (io.read_bytes + io.write_bytes)
            except Exception:
                pass

        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return (usage.ru_inblock + usage.ru_oublock) * 512
        except Exception:
            return 0

    def _get_network_io_bytes(self):
        if psutil:
            try:
                p = psutil.Process()
                if hasattr(p, 'net_io_counters'):
                    net = p.net_io_counters()
                    return net.bytes_sent + net.bytes_recv
            except Exception:
                pass
        return 0

    def _build_reason(self, cpu_pct, memory_mb, disk_delta_mb, net_delta_mb):
        if cpu_pct > constants.SAFE_MAX_CPU_PERCENT:
            return f"Sandbox limit exceeded: CPU usage above {constants.SAFE_MAX_CPU_PERCENT}% ({cpu_pct:.1f}%)"
        if memory_mb > constants.SAFE_MAX_MEMORY_MB:
            return f"Sandbox limit exceeded: memory usage above {constants.SAFE_MAX_MEMORY_MB} MB ({memory_mb:.1f} MB)"
        if disk_delta_mb > constants.SAFE_MAX_DISK_IO_MB:
            return f"Sandbox limit exceeded: disk I/O above {constants.SAFE_MAX_DISK_IO_MB} MB/s ({disk_delta_mb:.2f} MB)"
        if net_delta_mb > constants.SAFE_MAX_NETWORK_IO_MB:
            return f"Sandbox limit exceeded: network I/O above {constants.SAFE_MAX_NETWORK_IO_MB} MB/s ({net_delta_mb:.2f} MB)"
        return None

    def _terminate(self, reason):
        try:
            print(f"[SANDBOX] {reason}")
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(1)

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.wait(constants.SAFE_MONITOR_INTERVAL):
            if not self.interpreter.safe_mode:
                continue

            now = time.time()
            cpu_now = time.process_time()
            elapsed = now - self.prev_time
            if elapsed <= 0:
                self.prev_time = now
                continue

            cpu_pct = max(0.0, (cpu_now - self.prev_cpu) / elapsed * 100.0)
            self.prev_cpu = cpu_now
            self.prev_time = now

            memory_mb = self._get_memory_mb()
            disk_io = self._get_disk_io_bytes()
            net_io = self._get_network_io_bytes()

            disk_delta_mb = max(0.0, (disk_io - self.prev_disk) / 1024.0 / 1024.0 / elapsed)
            net_delta_mb = max(0.0, (net_io - self.prev_net) / 1024.0 / 1024.0 / elapsed)
            self.prev_disk = disk_io
            self.prev_net = net_io

            reason = self._build_reason(cpu_pct, memory_mb, disk_delta_mb, net_delta_mb)
            if reason:
                self.interpreter.safe_violation_reason = reason
                self._terminate(reason)


# ==========================================
# LUNITE INTERPRETER
# ==========================================

class Interpreter:
    def __init__(self, imported_files=None, safe_mode=False, debug=False):
        self.global_env = Environment()
        self.safe_mode = bool(safe_mode)
        self.debug = bool(debug)
        self.safe_violation_reason = None
        self.safe_monitor = None
        self.setup_std_lib()
        self.env = self.global_env
        self.imported_files = imported_files if imported_files else {}
        self.visit_cache = {}

        if self.safe_mode:
            self.safe_monitor = SafeModeResourceMonitor(self)
            self.safe_monitor.start()

    def debug_print(self, *args, **kwargs):
        if self.debug:
            print("[LUNITE DEBUG]", *args, **kwargs)

    def _get_target_env(self, is_global):
        if not is_global:
            return self.env
        
        target = self.env
        while target.parent is not None and target.parent != self.global_env:
            target = target.parent
        return target

    def _call_callback(self, func, args, line, col):
        if isinstance(func, (FunctionDef, LambdaExpr)):
            prev_env = self.env
            method_env = Environment(self.global_env) 
            
            f_params = func.params
            if isinstance(func, LambdaExpr):
                f_params = [(p, None) for p in f_params]

            for i, (p_name, p_default) in enumerate(f_params):
                if i < len(args):
                    method_env.define(p_name, args[i])
                elif p_default is not None:
                    val = self.visit(p_default)
                    method_env.define(p_name, val)
                else:
                    raise lunite_error("Callback", f"Missing argument '{p_name}'", line, col)

            old_file = constants.CURRENT_FILE
            if hasattr(func, 'source_file'): constants.CURRENT_FILE = func.source_file

            self.env = method_env
            try:
                if isinstance(func.body, Block):
                    self.visit(func.body)
                else:
                    return self.visit(func.body)
            except ReturnException as e:
                return e.value
            finally:
                self.env = prev_env
                constants.CURRENT_FILE = old_file
            return None

        if callable(func):
            try:
                return func(*args)
            except Exception as e:
                raise lunite_error("Callback", str(e), line, col)
            
        raise lunite_error("Type", f"'{type(func).__name__}' is not callable", line, col)

    def execute_node_as_call(self, func_node, args, kwargs):
        prev_env = self.env
        
        closure_env = getattr(func_node, 'closure', self.global_env)
        new_env = Environment(closure_env)
        
        f_params = func_node.params
        for i, param_data in enumerate(f_params):
            p_name = param_data[0] if isinstance(param_data, (list, tuple)) else param_data
            
            if i < len(args):
                new_env.define(p_name, args[i])
            elif isinstance(param_data, (list, tuple)) and param_data[1] is not None:
                new_env.define(p_name, self.visit(param_data[1]))
        self.env = new_env
        try:
            if isinstance(func_node.body, Block):
                self.visit(func_node.body)
            else:
                return self.visit(func_node.body)
        except ReturnException as e:
            return e.value
        finally:
            self.env = prev_env
        return None

    def setup_std_lib(self):
        def clean_str(val):
            if isinstance(val, bool): return "true" if val else "false"
            if isinstance(val, float): 
                if val.is_integer(): return str(int(val))
                return f"{val:.12g}"
            if val is None: return "null"
            if isinstance(val, (bytes, bytearray)): return f"<Bytes len={len(val)}>"
            if isinstance(val, (set, tuple)): return str(val)
            return str(val)

        def make_static_lib(name, wrapper_cls, fields=None):
            obj = LuniteInstance(ClassDef(name, Block([]), None))
            for method in dir(wrapper_cls):
                if not method.startswith('__'):
                    obj.methods[method] = getattr(wrapper_cls, method)
            if fields:
                for k, v in fields.items():
                    obj.fields[k] = v
                    obj.constants.add(k)
            self.global_env.define(name, obj)

        def register_static_lib(name, wrapper_cls, fields=None, safe=True):
            if self.safe_mode and not safe:
                return
            make_static_lib(name, wrapper_cls, fields)

        # [ Static Libraries ]

        # --- File IO & System ---
        class FileWrapper:
            @staticmethod
            def read(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f: return f.read()
                except Exception as e: raise lunite_error("File", str(e))
            @staticmethod
            def write(path, content):
                try:
                    with open(path, 'w', encoding='utf-8') as f: f.write(clean_str(content))
                except Exception as e: raise lunite_error("File", str(e))
            @staticmethod
            def append(path, content):
                try:
                    with open(path, 'a', encoding='utf-8') as f: f.write(clean_str(content))
                except Exception as e: raise lunite_error("File", str(e))
            @staticmethod
            def read_bytes(path):
                try:
                    with open(path, 'rb') as f: return f.read()
                except Exception as e: return None
            @staticmethod
            def write_bytes(path, data):
                try:
                    if isinstance(data, str): data = data.encode('utf-8')
                    with open(path, 'wb') as f: f.write(data)
                except Exception as e: raise lunite_error("File", str(e))
            @staticmethod
            def exists(p): return os.path.exists(str(p))
            @staticmethod
            def is_file(p): return os.path.isfile(str(p))
            @staticmethod
            def is_dir(p): return os.path.isdir(str(p))
            @staticmethod
            def mkdir(p): os.makedirs(str(p), exist_ok=True)
            @staticmethod
            def rmdir(p): os.rmdir(str(p))
            @staticmethod
            def remove(p): os.remove(str(p))
            @staticmethod
            def list(p): return os.listdir(str(p))
            @staticmethod
            def join(*args): return os.path.join(*(str(a) for a in args))
            @staticmethod
            def abs(p): return os.path.abspath(str(p))
            @staticmethod
            def base(p): return os.path.basename(str(p))
            @staticmethod
            def ext(p): return os.path.splitext(str(p))[1]
            @staticmethod
            def size(p): return os.path.getsize(str(p))
            @staticmethod
            def cwd(): return os.getcwd()
        
        register_static_lib("File", FileWrapper, safe=False)

        # --- Network ---
        class NetWrapper:
            @staticmethod
            def get(url):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': LUNITE_USER_AGENT})
                    with urllib.request.urlopen(req) as r: return r.read().decode('utf-8')
                except Exception as e: raise lunite_error("Net", str(e))
            @staticmethod
            def post(url, data):
                try:
                    if isinstance(data, (dict, list)):
                        payload = json.dumps(data).encode('utf-8')
                        headers = {'Content-Type': 'application/json', 'User-Agent': LUNITE_USER_AGENT}
                    else:
                        payload = clean_str(data).encode('utf-8')
                        headers = {'User-Agent': LUNITE_USER_AGENT}
                    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                    with urllib.request.urlopen(req) as r: return r.read().decode('utf-8')
                except Exception as e: raise lunite_error("Net", str(e))
            @staticmethod
            def download(url, path):
                try:
                    urllib.request.urlretrieve(url, path)
                except Exception as e: raise lunite_error("Net", str(e))

        register_static_lib("Net", NetWrapper, safe=False)

        class JsonWrapper:
            @staticmethod
            def encode(o): return json.dumps(o, default=str)
            @staticmethod
            def decode(s): return json.loads(s)
        
        make_static_lib("Json", JsonWrapper)

        # --- Crypto ---
        class CryptoWrapper:
            @staticmethod
            def sha256(value):
                return hashlib.sha256(str(value).encode('utf-8')).hexdigest()
            @staticmethod
            def md5(value):
                return hashlib.md5(str(value).encode('utf-8')).hexdigest()
            @staticmethod
            def hmac_sha256(key, message):
                import hmac
                return hmac.new(str(key).encode('utf-8'), str(message).encode('utf-8'), hashlib.sha256).hexdigest()
            @staticmethod
            def base64_encode(value):
                return base64.b64encode(str(value).encode('utf-8')).decode('utf-8')
            @staticmethod
            def base64_decode(value):
                try:
                    return base64.b64decode(str(value)).decode('utf-8')
                except Exception:
                    return None

        make_static_lib("Crypto", CryptoWrapper)

        # --- System ---
        class SysWrapper:
            @staticmethod
            def cmd(c): return subprocess.getoutput(c)
            @staticmethod
            def os(): return platform.system()
            @staticmethod
            def arch(): return platform.machine()
            @staticmethod
            def args(): return sys.argv
            @staticmethod
            def env(k): return os.environ.get(str(k), None)
            @staticmethod
            def set_env(k, v): os.environ[str(k)] = str(v)
            @staticmethod
            def exit(c=0): sys.exit(int(c))

        register_static_lib("Sys", SysWrapper, safe=False)

        # --- Lunite Metadata ---
        class LuniteMetaWrapper:
            @staticmethod
            def version(): return LUNITE_VERSION_STR
            @staticmethod
            def copyright(): return COPYRIGHT
            @staticmethod
            def user_agent(): return LUNITE_USER_AGENT
            @staticmethod
            def current_file(): return constants.CURRENT_FILE
            @staticmethod
            def keywords(): return KEYWORDS
            @staticmethod
            def regex_num(): return RE_NUMBER
            @staticmethod
            def regex_id(): return RE_ID

        make_static_lib("LuniteMeta", LuniteMetaWrapper)

        # --- Math ---
        class MathWrapper:
            @staticmethod
            def sin(x): return math.sin(x)
            @staticmethod
            def cos(x): return math.cos(x)
            @staticmethod
            def tan(x): return math.tan(x)
            @staticmethod
            def asin(x): return math.asin(x)
            @staticmethod
            def acos(x): return math.acos(x)
            @staticmethod
            def atan(x): return math.atan(x)
            @staticmethod
            def sqrt(x): return math.sqrt(x)
            @staticmethod
            def pow(x, y): return math.pow(x, y)
            @staticmethod
            def abs(x): return abs(x)
            @staticmethod
            def round(x): return round(x)
            @staticmethod
            def floor(x): return math.floor(x)
            @staticmethod
            def ceil(x): return math.ceil(x)
            @staticmethod
            def log(x): return math.log(x)
            @staticmethod
            def log10(x): return math.log10(x)
            @staticmethod
            def rad(x): return math.radians(x)
            @staticmethod
            def deg(x): return math.degrees(x)
            @staticmethod
            def clamp(n, smallest, largest): return max(smallest, min(n, largest))
            @staticmethod
            def max(*args): return max(args) if args else 0
            @staticmethod
            def min(*args): return min(args) if args else 0
            @staticmethod
            def factorial(x): return math.factorial(int(x))
            @staticmethod
            def gcd(a, b): return math.gcd(int(a), int(b))
            @staticmethod
            def lcm(a, b): return math.lcm(int(a), int(b))
            @staticmethod
            def hypot(x, y): return math.hypot(x, y)
        
        make_static_lib("Math", MathWrapper, {'pi': math.pi, 'e': math.e, 'tau': math.tau, 'inf': math.inf})

        # --- Random ---
        class RandomWrapper:
            @staticmethod
            def random(): return random.random()
            @staticmethod
            def randint(a, b): return random.randint(int(a), int(b))
            @staticmethod
            def uniform(a, b): return random.uniform(float(a), float(b))
            @staticmethod
            def randrange(start, stop, step=1): return random.randrange(int(start), int(stop), int(step))
            @staticmethod
            def seed(a=None): random.seed(a)
            @staticmethod
            def choice(l):
                if isinstance(l, (list, tuple, str)) and len(l) > 0: return random.choice(l)
                return None
            @staticmethod
            def shuffle(l):
                if isinstance(l, list): random.shuffle(l); return l
                raise lunite_error("Type", "shuffle() expects a list")
            @staticmethod
            def sample(l, k):
                if isinstance(l, (list, tuple, str)): return random.sample(l, int(k))
                raise lunite_error("Type", "sample() expects a sequence")

        make_static_lib("Random", RandomWrapper)

        # --- Time ---
        class TimeWrapper:
            @staticmethod
            def now(): return time.time()
            @staticmethod
            def sleep(s): time.sleep(s)
            @staticmethod
            def struct(ts=None):
                if ts is None: ts = time.time()
                dt = datetime.datetime.fromtimestamp(ts)
                return {
                    "year": dt.year, "month": dt.month, "day": dt.day,
                    "hour": dt.hour, "minute": dt.minute, "second": dt.second,
                    "weekday": dt.weekday(), "iso": dt.isoformat()
                }
            @staticmethod
            def format(fmt="%Y-%m-%d %H:%M:%S"):
                return datetime.datetime.now().strftime(fmt)

        make_static_lib("Time", TimeWrapper)

        # --- String ---
        class StringWrapper:
            @staticmethod
            def upper(s): return clean_str(s).upper()
            @staticmethod
            def lower(s): return clean_str(s).lower()
            @staticmethod
            def trim(s): return clean_str(s).strip()
            @staticmethod
            def replace(s, o, n): return clean_str(s).replace(clean_str(o), clean_str(n))
            @staticmethod
            def split(s, d): return clean_str(s).split(clean_str(d))
            @staticmethod
            def join(l, d): return clean_str(d).join([clean_str(i) for i in l])
            @staticmethod
            def starts_with(s, p): return clean_str(s).startswith(clean_str(p))
            @staticmethod
            def ends_with(s, p): return clean_str(s).endswith(clean_str(p))
            @staticmethod
            def includes(s, sub): return clean_str(sub) in clean_str(s)
            @staticmethod
            def index(s, sub): return clean_str(s).find(clean_str(sub))
            @staticmethod
            def is_alpha(s): return clean_str(s).isalpha()
            @staticmethod
            def is_digit(s): return clean_str(s).isdigit()
            @staticmethod
            def char_at(s, i): 
                try: return LChar(clean_str(s)[int(i)])
                except: return ""
            @staticmethod
            def pad_start(s, width, char=" "): return clean_str(s).rjust(int(width), str(char))
            @staticmethod
            def pad_end(s, width, char=" "): return clean_str(s).ljust(int(width), str(char))

        make_static_lib("String", StringWrapper)
        
        # --- List Utils ---
        class ListWrapper:
            @staticmethod
            def push(l, x): 
                if isinstance(l, list): l.append(x); return l
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def pop(l, i=-1): 
                if isinstance(l, list): return l.pop(i)
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def sort(l): 
                if isinstance(l, list): l.sort(); return l
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def reverse(l): 
                if isinstance(l, list): l.reverse(); return l
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def copy(l): 
                if isinstance(l, list): return l.copy()
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def clear(l): 
                if isinstance(l, list): l.clear()
                raise lunite_error("Type", "Expected list")
            @staticmethod
            def contains(l, item):
                return item in l
            @staticmethod
            def index(l, x): 
                if x in l: return l.index(x)
                return -1
            @staticmethod
            def count(l, x): return l.count(x)
            @staticmethod
            def extend(l, other): 
                if isinstance(l, list) and isinstance(other, list): l.extend(other)
                return l
        
        make_static_lib("List", ListWrapper)

        # --- Dictionary Utils ---
        class DictWrapper:
            @staticmethod
            def keys(d): return list(d.keys()) if isinstance(d, dict) else []
            @staticmethod
            def values(d): return list(d.values()) if isinstance(d, dict) else []
            @staticmethod
            def items(d): return [[k, v] for k, v in d.items()] if isinstance(d, dict) else []
            @staticmethod
            def merge(d1, d2): 
                if isinstance(d1, dict) and isinstance(d2, dict): return {**d1, **d2}
                return d1
            @staticmethod
            def has(d, k): return k in d
            @staticmethod
            def remove(d, k): 
                if k in d: del d[k]
        
        make_static_lib("Dict", DictWrapper)

        # --- Set Utils ---
        class SetWrapper:
            @staticmethod
            def add(s, v): 
                if isinstance(s, set): s.add(v); return s
                raise lunite_error("Type", "Expected set")
            @staticmethod
            def remove(s, v): 
                if isinstance(s, set) and v in s: s.remove(v)
                return s
            @staticmethod
            def has(s, v): return v in s
            @staticmethod
            def union(s1, s2): 
                if isinstance(s1, set) and isinstance(s2, set): return s1.union(s2)
                return s1
            @staticmethod
            def intersect(s1, s2):
                if isinstance(s1, set) and isinstance(s2, set): return s1.intersection(s2)
                return set()
            @staticmethod
            def diff(s1, s2):
                if isinstance(s1, set) and isinstance(s2, set): return s1.difference(s2)
                return s1
            @staticmethod
            def list(s): return list(s)

        make_static_lib("Set", SetWrapper)

        # --- Console Utils ---
        class ConsoleWrapper:
            @staticmethod
            def clear():
                os.system('cls' if os.name == 'nt' else 'clear')
            @staticmethod
            def read_pass(prompt=""):
                return getpass.getpass(str(prompt))
            @staticmethod
            def size():
                try:
                    sz = os.get_terminal_size()
                    return {"columns": sz.columns, "lines": sz.lines}
                except: return {"columns": 80, "lines": 24}
            @staticmethod
            def title(t):
                if os.name == 'nt': os.system(f'title {str(t)}')
                else: sys.stdout.write(f"\x1b]2;{str(t)}\x07")
        
        make_static_lib("Console", ConsoleWrapper)

        # --- Base64 ---
        class Base64Wrapper:
            @staticmethod
            def encode(s): return base64.b64encode(str(s).encode('utf-8')).decode('utf-8')
            @staticmethod
            def decode(s): return base64.b64decode(str(s)).decode('utf-8')
        
        make_static_lib("Base64", Base64Wrapper)

        # --- Hashing ---
        class HashWrapper:
            @staticmethod
            def sha256(s): return hashlib.sha256(str(s).encode()).hexdigest()
            @staticmethod
            def md5(s): return hashlib.md5(str(s).encode()).hexdigest()
        
        make_static_lib("Hash", HashWrapper)

        # --- Regex ---
        class RegexWrapper:
            @staticmethod
            def match(p, s): return bool(re.match(p, s))
            @staticmethod
            def search(p, s): 
                m = re.search(p, s)
                return m.groups() if m else None
            @staticmethod
            def find_all(p, s): return re.findall(p, s)
            @staticmethod
            def replace(p, r, s): return re.sub(p, r, s)
        
        make_static_lib("Regex", RegexWrapper)

        # [ Global Functions ]
        
        # --- IO ---
        self.global_env.define('out', lambda x: print(clean_str(x)))
        
        def lunite_input(prompt, type_hint="string"):
            if type_hint == "pass":
                return getpass.getpass(clean_str(prompt))

            text = input(clean_str(prompt))
            
            try:
                if type_hint == "int": return int(text)
                if type_hint == "float": return float(text)
                if type_hint == "bool": return text.lower() in ("true", "1", "yes", "on")
                if type_hint == "bit": return LBit(text)
                if type_hint == "byte": return LByte(text)
                if type_hint == "char": return LChar(text)
                return text
            except ValueError:
                raise lunite_error("Input", f"Failed to convert '{text}' to type {type_hint}")
                
        self.global_env.define('in', lunite_input)

        self.global_env.define('range', lambda a, b: list(range(int(a), int(b) + 1)))
        self.global_env.define('str', lambda x: clean_str(x))
        self.global_env.define('int', lambda x: int(x))
        self.global_env.define('float', lambda x: float(x))
        self.global_env.define('bit', lambda x: LBit(x))
        self.global_env.define('byte', lambda x: LByte(x))
        self.global_env.define('char', lambda x: LChar(str(x)) if isinstance(x, (int, float)) else LChar(x))
        self.global_env.define('bytes', lambda lst: bytes(lst))
        
        def create_list_impl(n, hint="null"):
            try: count = int(n)
            except: raise Exception("List size must be an integer")
            default_val = None
            if hint == "int": default_val = 0
            elif hint == "float": default_val = 0.0
            elif hint == "bool": default_val = False
            elif hint == "str": default_val = ""
            elif hint == "list": return [[] for _ in range(count)]
            elif hint == "dict": return [{} for _ in range(count)]
            return [default_val] * count

        self.global_env.define('list', create_list_impl)
        
        def get_type(x):
            if isinstance(x, LBit): return "Bit"
            if isinstance(x, LByte): return "Byte"
            if isinstance(x, LChar): return "Char"
            if isinstance(x, bool): return "Bool"
            if isinstance(x, int): return "Int"
            if isinstance(x, float): return "Float"
            if isinstance(x, str): return "String"
            if isinstance(x, list): return "List"
            if isinstance(x, dict): return "Dict"
            if isinstance(x, set): return "Set"
            if isinstance(x, tuple): return "Tuple"
            if isinstance(x, LuniteInstance): return x.mold.name
            if x is None: return "Null"
            return "Unknown"
    
        self.global_env.define('len', lambda x: len(x))
        self.global_env.define('type', get_type)
        self.global_env.define('raise', lambda msg: (_ for _ in ()).throw(Exception(msg)))
    
    def visit(self, node):
        if self.safe_mode and self.safe_violation_reason:
            raise lunite_error("Sandbox", self.safe_violation_reason, getattr(node, 'line', 0), getattr(node, 'col', 0))

        node_type = type(node)
        method = self.visit_cache.get(node_type)
        
        if method is None:
            method_name = f'visit_{node_type.__name__}'
            method = getattr(self, method_name, self.no_visit)
            self.visit_cache[node_type] = method
        
        try:
            return method(node)
        except Exception as e:
            if isinstance(e, (ReturnException, BreakException, AdvanceException, LeapException)):
                raise e
            
            if hasattr(e, "has_location") and e.has_location:
                if isinstance(node, (FunctionCall, MethodCall, NewInstance)):
                    stack_trace = f"\n{Fore.YELLOW}   called from:{Style.RESET_ALL} {constants.CURRENT_FILE}:{node.line}:{node.col}"
                    
                    if e.args:
                        new_msg = e.args[0] + stack_trace
                        e.args = (new_msg,) + e.args[1:]
                raise e

            err = lunite_error("Runtime", str(e), node.line, node.col)
            raise err

    def no_visit(self, node):
        raise lunite_error("Internal Lunite", f"No visit_{type(node).__name__} method defined in Lunite", node.line, node.col)

    def visit_Block(self, node):
        result = None
        statements = node.statements
        i = 0
        while i < len(statements):
            stmt = statements[i]
            try:
                result = self.visit(stmt)
                i += 1
            except LeapException as e:
                target = e.target
                found = False
                
                for idx, s in enumerate(statements):
                    if isinstance(target, str): 
                        if isinstance(s, LabelDef) and s.name == target:
                            i = idx
                            found = True
                            break
                    elif isinstance(target, int):
                        if s.line >= target:
                            i = idx
                            found = True
                            break
                
                if found:
                    continue
                else:
                    raise e
        return result
    
    def visit_Number(self, node):
        return node.token.value

    def visit_String(self, node):
        return node.token.value
    
    def visit_Char(self, node):
        return LChar(node.token.value)

    def visit_Boolean(self, node):
        return node.value

    def visit_Null(self, node):
        return None

    def visit_ListLiteral(self, node):
        return [self.visit(e) for e in node.elements]

    def visit_DictLiteral(self, node):
        return {self.visit(k): self.visit(v) for k, v in node.pairs}

    def visit_Identifier(self, node):
        return self.env.get(node.token.value, node.line, node.col)

    def visit_MatchCase(self, node):
        return self.visit(node.value)

    def visit_MatchStatement(self, node):
        subject_val = self.visit(node.subject)
        matched = False
        
        try:
            for case in node.cases:
                case_val = self.visit_MatchCase(case)
                
                if subject_val == case_val:
                    self.visit(case.body)
                    matched = True
                    break
            
            if not matched and node.default_block:
                self.visit(node.default_block)

        except BreakException:
            pass
    
    def visit_UnaryOp(self, node):
        op = node.op.type
        val = self.visit(node.expr)
        
        if op == TOKEN_MINUS: return -val
        if op == TOKEN_PLUS: return +val
        if op == TOKEN_BIT_NOT: return ~val
        if op == TOKEN_NOT: return not val
        return val
    
    def visit_BinaryOp(self, node):
        op = node.op.type

        if op == TOKEN_AND:
            left = self.visit(node.left)
            if not left: return False
            return self.visit(node.right)
            
        if op == TOKEN_OR:
            left = self.visit(node.left)
            if left: return True
            return self.visit(node.right)

        left = self.visit(node.left)
        right = self.visit(node.right)

        # Math
        try:
            if op == TOKEN_PLUS: return left + right
            if op == TOKEN_MINUS: return left - right
            if op == TOKEN_MUL: return left * right
            if op == TOKEN_DIV: return left / right
            if op == TOKEN_MOD: 
                val = math.fmod(left, right)
                if isinstance(left, int) and isinstance(right, int):
                    return int(val)
                return val
        except TypeError:
            raise lunite_error(
                "Type", 
                f"Unsupported operand types for '{op}': '{type(left).__name__}' and '{type(right).__name__}'", 
                node.line, 
                node.col
            )
        except ZeroDivisionError:
             raise lunite_error("Math", "Division by zero", node.line, node.col)
        
        # Bitwise
        if op == TOKEN_BIT_AND: return left & right
        if op == TOKEN_BIT_OR:  return left | right
        if op == TOKEN_BIT_XOR: return left ^ right
        if op == TOKEN_LSHIFT:  return left << right
        if op == TOKEN_RSHIFT:  return left >> right
        
        # Comparison
        if op == TOKEN_GT: return left > right
        if op == TOKEN_LT: return left < right
        if op == TOKEN_GE: return left >= right
        if op == TOKEN_LE: return left <= right
        if op == TOKEN_EQ: return left == right
        if op == TOKEN_NEQ: return left != right

        # in keyword
        if op.type == TOKEN_KEYWORD and op.value == 'in': return left in right
        
        return None
    
    def visit_TernaryOp(self, node):
        if self.visit(node.condition):
            return self.visit(node.true_expr)
        else:
            return self.visit(node.false_expr)

    def visit_VarDecl(self, node):
        val = self.visit(node.value)
        target_env = self._get_target_env(node.is_global)
        target_env.define(node.name, val, is_const=node.is_const, is_public=node.is_public)
        return val

    def visit_Assign(self, node):
        val = self.visit(node.value)
        
        if isinstance(node.left, Identifier):
            self.env.assign(node.left.token.value, val, node.line, node.col)
        
        elif isinstance(node.left, MemberAccess):
            obj = self.visit(node.left.obj)
            if isinstance(obj, LuniteInstance):
                obj.set(node.left.member_name, val)
            else:
                raise lunite_error("Assignment", "Cannot set a property on a non-instance", node.line, node.col)
        
        elif isinstance(node.left, IndexAccess):
            indices = []
            current_node = node.left
            
            while isinstance(current_node, IndexAccess):
                indices.append(self.visit(current_node.index))
                current_node = current_node.target
            
            current_context = self.visit(current_node)
            indices.reverse()

            for i in range(len(indices) - 1):
                idx = indices[i]
                
                if isinstance(current_context, dict):
                    if idx not in current_context:
                        current_context[idx] = {}
                    current_context = current_context[idx]
                    
                elif isinstance(current_context, list):
                    try:
                        current_context = current_context[idx]
                    except IndexError:
                        raise lunite_error("Index", f"Index '{idx}' is out of bounds (no list autovivification)", node.line, node.col)
                    except TypeError:
                         raise lunite_error("Type", f"Invalid list index type", node.line, node.col)
                else:
                    raise lunite_error("Type", f"Cannot index into type '{type(current_context).__name__}'", node.line, node.col)

            final_index = indices[-1]
            try:
                current_context[final_index] = val
            except TypeError:
                raise lunite_error("Type", "Target container does not support item assignment", node.line, node.col)
            except IndexError:
                raise lunite_error("Index", f"Index '{final_index}' is out of bounds", node.line, node.col)

        else:
            raise lunite_error("Assignment", "No such assignment target", node.line, node.col)

        return val

    def visit_CompoundAssign(self, node):
        curr_val = 0
        if isinstance(node.left, Identifier):
            curr_val = self.env.get(node.left.token.value, node.line, node.col)
        elif isinstance(node.left, MemberAccess):
            obj = self.visit(node.left.obj)
            curr_val = obj.get(node.left.member_name)
        elif isinstance(node.left, IndexAccess):
            target = self.visit(node.left.target)
            index = self.visit(node.left.index)
            curr_val = target[index]
        else:
            raise lunite_error("Assignment", "Invalid target for compound assignment", node.line, node.col)

        right_val = self.visit(node.value)
        op = node.op.type
        new_val = curr_val
        
        if op == TOKEN_PLUSEQ: new_val += right_val
        if op == TOKEN_MINUSEQ: new_val -= right_val
        if op == TOKEN_MULEQ: new_val *= right_val
        if op == TOKEN_DIVEQ: new_val /= right_val
        if op == TOKEN_MODEQ: 
            val = math.fmod(curr_val, right_val)
            if isinstance(curr_val, int) and isinstance(right_val, int):
                new_val = int(val)
            else:
                new_val = val

        if isinstance(node.left, Identifier):
            self.env.assign(node.left.token.value, new_val, node.left.token.line, node.left.token.col)
        elif isinstance(node.left, MemberAccess):
            obj.set(node.left.member_name, new_val)
        elif isinstance(node.left, IndexAccess):
            target[self.visit(node.left.index)] = new_val
            
        return new_val

    def visit_IfStatement(self, node):
        if self.visit(node.condition):
            prev = self.env
            self.env = Environment(prev)
            try:
                return self.visit(node.true_block)
            finally:
                self.env = prev
        elif node.false_block:
            prev = self.env
            self.env = Environment(prev)
            try:
                return self.visit(node.false_block)
            finally:
                self.env = prev

    def visit_WhileStatement(self, node):
        while self.visit(node.condition):
            prev = self.env
            self.env = Environment(prev)
            try:
                self.visit(node.body)
            except BreakException:
                self.env = prev
                break
            except AdvanceException:
                self.env = prev
                continue
            finally:
                self.env = prev
    
    def visit_ForStatement(self, node):
        iterable = self.visit(node.iterable)
        if not hasattr(iterable, '__iter__'):
            raise lunite_error("Loop", "Expected iterable for 'for' loop", node.line, node.col)

        prev_env = self.env
        for item in iterable:
            loop_env = Environment(prev_env)
            loop_env.define(node.iterator_name, item)
            self.env = loop_env
            try:
                self.visit(node.body)
            except ReturnException as e:
                self.env = prev_env
                raise e 
            except BreakException:
                self.env = prev_env
                break
            except AdvanceException:
                self.env = prev_env
                continue
        self.env = prev_env

    def visit_BreakStatement(self, node):
        raise BreakException()

    def visit_AdvanceStatement(self, node):
        raise AdvanceException()

    def visit_LeapStatement(self, node):
        if isinstance(node.target, Identifier):
            raise LeapException(node.target.token.value)
        elif isinstance(node.target, Number):
            raise LeapException(node.target.token.value)

    def visit_LabelDef(self, node):
        pass

    def visit_TryCatchStatement(self, node):
        try:
            prev = self.env
            self.env = Environment(prev)
            try:
                return self.visit(node.try_block)
            finally:
                self.env = prev
        except Exception as e:
            if isinstance(e, (ReturnException)): raise e
            
            prev = self.env
            rescue_env = Environment(prev)
            msg = str(e)
            if hasattr(e, "message_only"): msg = e.message_only
            
            rescue_env.define(node.error_var, msg)
            self.env = rescue_env
            try:
                return self.visit(node.catch_block)
            finally:
                self.env = prev
        finally:
            if node.finally_block:
                prev = self.env
                self.env = Environment(prev)
                try:
                    self.visit(node.finally_block)
                finally:
                    self.env = prev

    def visit_ImportStatement(self, node):
        ctx_dir = os.path.dirname(os.path.abspath(constants.CURRENT_FILE)) if constants.CURRENT_FILE != "REPL" else os.getcwd()
        target_file = ""

        if node.source_package:
            base_dir = node.source_package
            mod_name = node.module_name
            if not mod_name.endswith('.luna'): mod_name += '.luna'
            target_file = os.path.join(base_dir, mod_name)
        elif node.module_name.startswith('.'):
             target_file = os.path.join(ctx_dir, node.module_name)
             if not target_file.endswith('.luna'): target_file += '.luna'
        else:
            target_file = node.module_name
            if not target_file.endswith('.luna'): target_file += '.luna'
        
        target_file = os.path.normpath(target_file)
        
        if not os.path.exists(target_file):
             if os.path.exists(node.module_name + ".luna"):
                 target_file = os.path.abspath(node.module_name + ".luna")
             else:
                 raise lunite_error("Import", f"Module '{node.module_name}' not found", node.line, node.col)

        if target_file in self.imported_files:
            module_obj = self.imported_files[target_file]
            alias = os.path.splitext(os.path.basename(node.module_name))[0]
            self.env.define(alias, module_obj)
            return 

        try:
            with open(target_file, 'r') as f:
                code = f.read()
        except Exception as e:
            raise lunite_error("Import", f"Failed to read file: {str(e)}", node.line, node.col)

        alias = os.path.splitext(os.path.basename(node.module_name))[0]
        module_def = ClassDef(alias, Block([]), None)
        module_obj = LuniteInstance(module_def)
        
        self.imported_files[target_file] = module_obj
        self.env.define(alias, module_obj)

        module_env = Environment(self.global_env)
        
        old_env = self.env
        old_file = constants.CURRENT_FILE
        
        self.env = module_env
        constants.CURRENT_FILE = target_file
        
        try:
            lexer = Lexer(code)
            tokens = list(lexer)
            parser = Parser(tokens)
            ast = parser.parse()
            self.visit(ast)
        finally:
            self.env = old_env
            constants.CURRENT_FILE = old_file

        for name, value in module_env.values.items():
            if module_env.is_public(name):
                module_obj.fields[name] = value
            
        self.imported_files[target_file] = module_obj
        self.env.define(alias, module_obj)

    def visit_DecoratedFunc(self, node):
        decorator = self.visit(node.decorator)
        self.visit(node.function)
        original_func = self.env.get(node.function.name, node.line, node.col)

        if asyncio.iscoroutinefunction(original_func) or isinstance(node.function, AsyncFuncDef):
            pass
        
        if callable(decorator):
            wrapped_func = decorator(original_func)
        elif isinstance(decorator, (FunctionDef, LambdaExpr)):
            prev_env = self.env
            new_env = Environment(getattr(decorator, 'closure', self.global_env))
            if decorator.params:
                param_name = decorator.params[0][0] if isinstance(decorator.params[0], tuple) else decorator.params[0]
                new_env.define(param_name, original_func)
            self.env = new_env
            try:
                if isinstance(decorator.body, Block):
                    wrapped_func = self.visit(decorator.body)
                else:
                    wrapped_func = self.visit(decorator.body)
            except ReturnException as e:
                wrapped_func = e.value
            finally:
                self.env = prev_env
        else:
            raise lunite_error("Decorator", "Provided decorator is not callable", node.line, node.col)
        self.env.assign(node.function.name, wrapped_func, node.line, node.col)
        return wrapped_func
    
    def visit_FunctionDef(self, node):
        reserved_types = {
            'int', 'float', 'str', 'bool', 'bit', 'byte', 
            'char', 'bytes', 'list', 'dict', 'set', 'tuple'
        }
        if node.name in reserved_types:
            raise lunite_error("Function Definition", f"Cannot override built-in type constructor '{node.name}'", node.line, node.col)

        node.source_file = constants.CURRENT_FILE
        target_env = self._get_target_env(node.is_global)
        target_env.define(node.name, node, is_public=node.is_public)
        node.param_names = [p[0] if isinstance(p, tuple) else p for p in node.params]
        node.closure = self.env 
        node.interpreter = self
        node.__name__ = node.name
        node.__qualname__ = node.name
        if self.env is not target_env:
            self.env.define(node.name, node, is_public=node.is_public)
        return node

    def visit_AsyncFuncDef(self, node):
        node.closure = self.env
        node.__name__ = node.name
        node.__qualname__ = node.name
        async def async_wrapper(*args, **kwargs):
            return self.execute_node_as_call(node, list(args), kwargs)
        self.env.define(node.name, async_wrapper)
        return async_wrapper

    import asyncio

    def visit_AwaitExpr(self, node):
        result = self.visit(node.expr)
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return result
                else:
                    return asyncio.run(result)
            except Exception as e:
                raise lunite_error("Async", str(e), node.line, node.col)
        return result

    def visit_ClassDef(self, node):
        node.source_file = constants.CURRENT_FILE
        for stmt in node.body.statements:
            if isinstance(stmt, FunctionDef):
                stmt.source_file = constants.CURRENT_FILE
        
        target_env = self._get_target_env(node.is_global)
        target_env.define(node.name, node, is_public=node.is_public)
        return node

    def visit_ReturnStatement(self, node):
        val = self.visit(node.value)
        raise ReturnException(val)

    def _evaluate_arguments(self, arg_nodes):
        pos_args = []
        kw_args = {}
        for node in arg_nodes:
            if isinstance(node, Assign) and isinstance(node.left, Identifier):
                key = node.left.token.value
                val = self.visit(node.value)
                kw_args[key] = val
            else:
                if kw_args:
                    raise lunite_error("Syntax", "Positional argument follows keyword argument", node.line, node.col)
                pos_args.append(self.visit(node))
        return pos_args, kw_args

    def visit_FunctionCall(self, node):
        func = self.env.get(node.name, node.line, node.col)
        
        if isinstance(func, (FunctionDef, LambdaExpr)):
            prev_env = self.env
            closure_env = getattr(func, 'closure', self.global_env)
            new_env = Environment(closure_env)
            f_params = func.params
            
            if isinstance(func, LambdaExpr):
                f_params = [(p, None) for p in f_params]

            pos_args, kw_args = self._evaluate_arguments(node.args)

            if len(pos_args) > len(f_params):
                raise lunite_error("Function", f"Too many positional arguments", node.line, node.col)

            for i, (p_name, p_default) in enumerate(f_params):
                if i < len(pos_args):
                    if p_name in kw_args:
                        raise lunite_error("Function", f"Multiple values for argument '{p_name}'", node.line, node.col)
                    new_env.define(p_name, pos_args[i])
                elif p_name in kw_args:
                    new_env.define(p_name, kw_args[p_name])
                elif p_default is not None:
                    val = self.visit(p_default)
                    new_env.define(p_name, val)
                else:
                    raise lunite_error("Function", f"Missing argument for '{p_name}'", node.line, node.col)
            
            old_file = constants.CURRENT_FILE
            if hasattr(func, 'source_file'): constants.CURRENT_FILE = func.source_file

            self.env = new_env
            try:
                if isinstance(func.body, Block):
                    self.visit(func.body)
                else:
                    return self.visit(func.body)
            except ReturnException as e:
                return e.value
            finally:
                self.env = prev_env
                constants.CURRENT_FILE = old_file
            return None
        
        if callable(func):
            try:
                pos_args, kw_args = self._evaluate_arguments(node.args)
                return func(*pos_args, **kw_args)
            except Exception as e:
                if hasattr(e, "has_location") and e.has_location: raise e
                raise lunite_error("Function", str(e), node.line, node.col)
        
        raise lunite_error("Function", f"'{node.name}' is not a function", node.line, node.col)

    def visit_LambdaExpr(self, node):
        return node
    
    def visit_TypeCheckOp(self, node):
        val = self.visit(node.expr)
        
        target = node.target_type
        type_name = ""
        
        if isinstance(target, Identifier):
            type_name = target.token.value
        
        if type_name == 'int': return isinstance(val, int) and not isinstance(val, bool)
        if type_name == 'float': return isinstance(val, float)
        if type_name == 'str': return isinstance(val, str) and not isinstance(val, LChar)
        if type_name == 'bool': return isinstance(val, bool)
        if type_name == 'list': return isinstance(val, list)
        if type_name == 'dict': return isinstance(val, dict)
        if type_name == 'char': return isinstance(val, LChar)
        if type_name == 'bit': return isinstance(val, LBit)
        if type_name == 'byte': return isinstance(val, LByte)
        
        if isinstance(val, LuniteInstance):
            if isinstance(target, Identifier):
                curr_def = val.mold
                while curr_def:
                    if curr_def.name == type_name:
                        return True
                    
                    if curr_def.superclass:
                        curr_def = self.env.get(curr_def.superclass, node.line, node.col)
                        if not isinstance(curr_def, ClassDef):
                            break
                    else:
                        break
                
        return False

    def _resolve_class_members(self, class_def):
        members = {'fields': {}, 'methods': {}}
        
        if class_def.superclass:
            super_node = self.env.get(class_def.superclass, class_def.line, class_def.col)
            if isinstance(super_node, ClassDef):
                super_members = self._resolve_class_members(super_node)
                members['fields'].update(super_members['fields'])
                members['methods'].update(super_members['methods'])
            else:
                raise lunite_error("Class", f"Superclass {class_def.superclass} is not a valid class", class_def.line, class_def.col)

        prev_env = self.env
        class_env = Environment(self.global_env)
        self.env = class_env
        
        for stmt in class_def.body.statements:
            if isinstance(stmt, FunctionDef):
                members['methods'][stmt.name] = stmt
            elif isinstance(stmt, VarDecl):
                self.visit(stmt)
                members['fields'][stmt.name] = class_env.values[stmt.name]
            else:
                self.visit(stmt)

        self.env = prev_env
        return members
    
    def visit_NewInstance(self, node):
        cls_def = self.visit(node.class_expr)
        
        if not isinstance(cls_def, ClassDef):
            name_hint = "Expression"
            if isinstance(node.class_expr, Identifier): name_hint = node.class_expr.token.value
            elif isinstance(node.class_expr, MemberAccess): name_hint = node.class_expr.member_name
            raise lunite_error("Class", f"'{name_hint}' is not a class", node.line, node.col)
        
        instance = LuniteInstance(cls_def)
        members = self._resolve_class_members(cls_def)
        instance.fields = members['fields']
        instance.methods = members['methods']
        
        if 'init' in instance.methods:
            init_method = instance.methods['init']
            prev_env = self.env
            method_env = Environment(self.global_env)
            method_env.define('this', instance)
            
            pos_args, kw_args = self._evaluate_arguments(node.args)
            
            if len(pos_args) > len(init_method.params):
                raise lunite_error("Class", "Too many constructor arguments", node.line, node.col)

            for i, (p_name, p_default) in enumerate(init_method.params):
                if i < len(pos_args):
                    if p_name in kw_args: raise lunite_error("Class", f"Multiple values for '{p_name}'", node.line, node.col)
                    method_env.define(p_name, pos_args[i])
                elif p_name in kw_args:
                    method_env.define(p_name, kw_args[p_name])
                elif p_default is not None:
                    val = self.visit(p_default)
                    method_env.define(p_name, val)
                else:
                    raise lunite_error("Class", f"Missing constructor argument '{p_name}'", node.line, node.col)

            self.env = method_env
            try:
                self.visit(init_method.body)
            except ReturnException:
                pass
            finally:
                self.env = prev_env
                
        return instance
    
    def visit_MethodCall(self, node):
        obj = self.visit(node.obj)
        
        if isinstance(obj, list):
            if node.method_name == 'map':
                if len(node.args) != 1: raise lunite_error("Method", "map() expects 1 argument (function)", node.line, node.col)
                callback = self.visit(node.args[0])
                res = []
                for item in obj:
                    res.append(self._call_callback(callback, [item], node.line, node.col))
                return res

            elif node.method_name == 'filter':
                if len(node.args) != 1: raise lunite_error("Method", "filter() expects 1 argument (function)", node.line, node.col)
                callback = self.visit(node.args[0])
                res = []
                for item in obj:
                    if self._call_callback(callback, [item], node.line, node.col):
                        res.append(item)
                return res

            elif node.method_name == 'each':
                if len(node.args) != 1: raise lunite_error("Method", "each() expects 1 argument (function)", node.line, node.col)
                callback = self.visit(node.args[0])
                for item in obj:
                    self._call_callback(callback, [item], node.line, node.col)
                return None

        if isinstance(obj, dict):
            if node.method_name == 'get':
                args = [self.visit(arg) for arg in node.args]
                if len(args) < 1: raise lunite_error("Method", "get() expects at least 1 argument", node.line, node.col)
                key = args[0]
                default = args[1] if len(args) > 1 else None
                return obj.get(key, default)
        
        if isinstance(obj, LuniteInstance):
            method = obj.methods.get(node.method_name)

            if method and isinstance(method, FunctionDef):
                prev_env = self.env
                method_env = Environment(self.global_env)
                method_env.define('this', obj)
                
                pos_args, kw_args = self._evaluate_arguments(node.args)

                if len(pos_args) > len(method.params):
                     raise lunite_error("Method", f"Too many positional arguments for '{node.method_name}'", node.line, node.col)

                for i, (p_name, p_default) in enumerate(method.params):
                    if i < len(pos_args):
                        if p_name in kw_args: raise lunite_error("Method", f"Multiple values for '{p_name}'", node.line, node.col)
                        method_env.define(p_name, pos_args[i])
                    elif p_name in kw_args:
                        method_env.define(p_name, kw_args[p_name])
                    elif p_default is not None:
                        val = self.visit(p_default)
                        method_env.define(p_name, val)
                    else:
                        raise lunite_error("Method", f"Missing argument for '{p_name}'", node.line, node.col)

                old_file = constants.CURRENT_FILE
                if hasattr(method, 'source_file'):
                    constants.CURRENT_FILE = method.source_file
                elif hasattr(obj.mold, 'source_file'):
                    constants.CURRENT_FILE = obj.mold.source_file

                self.env = method_env
                try:
                    self.visit(method.body)
                except ReturnException as e:
                    return e.value
                finally:
                    self.env = prev_env
                    constants.CURRENT_FILE = old_file
                return None

            if method and callable(method):
                try:
                    pos_args, kw_args = self._evaluate_arguments(node.args)
                    return method(*pos_args, **kw_args)
                except Exception as e:
                     raise lunite_error("Method", str(e), node.line, node.col)

            field = obj.fields.get(node.method_name)
            if field and callable(field):
                try:
                    pos_args, kw_args = self._evaluate_arguments(node.args)
                    return field(*pos_args, **kw_args)
                except Exception as e:
                        raise lunite_error("Method", str(e), node.line, node.col)
            
            raise lunite_error("Method", f"Method '{node.method_name}' not found", node.line, node.col)

        if hasattr(obj, node.method_name):
            py_method = getattr(obj, node.method_name)
            if callable(py_method):
                try:
                    pos_args, kw_args = self._evaluate_arguments(node.args)
                    return py_method(*pos_args, **kw_args)
                except IndexError:
                    raise lunite_error("Index", "List index out of range", node.line, node.col)
                except Exception as e:
                    raise lunite_error("Interop", str(e), node.line, node.col)
        
        raise lunite_error("Method", f"Method '{node.method_name}' not found on '{type(obj).__name__}'", node.line, node.col)

    def visit_MemberAccess(self, node):
        obj = self.visit(node.obj)

        if isinstance(obj, (FunctionDef, LambdaExpr)):
            if node.member_name == 'name':
                return getattr(obj, 'name', 'anonymous')
            if node.member_name == 'params':
                return getattr(obj, 'param_names', [])
            if node.member_name == 'is_lambda':
                return isinstance(obj, LambdaExpr)
        if isinstance(obj, LuniteInstance):
            return obj.get(node.member_name, node.line, node.col)
        
        try:
            if hasattr(obj, node.member_name):
                return getattr(obj, node.member_name)
        except Exception:
            pass

        raise lunite_error("Member", f"Property '{node.member_name}' does not exist on type '{type(obj).__name__}'", node.line, node.col)

    def visit_IndexAccess(self, node):
        target = self.visit(node.target)
        index = self.visit(node.index)
        try:
            return target[index]
        except KeyError:
            raise lunite_error("Key", f"Key '{index}' not found in dictionary", node.line, node.col)
        except IndexError:
            raise lunite_error("Index", f"Index '{index}' out of bounds", node.line, node.col)
        except Exception as e:
            raise lunite_error("Index", f"Invalid access operation: {str(e)}", node.line, node.col)

    def visit_SliceAccess(self, node):
        target = self.visit(node.target)
        start = self.visit(node.start) if node.start else None
        end = self.visit(node.end) if node.end else None
        
        try:
            return target[start:end]
        except Exception as e:
            raise lunite_error("Slice", str(e), node.line, node.col)
        
    def visit_ImportPyStatement(self, node):
        ctx_dir = os.path.dirname(os.path.abspath(constants.CURRENT_FILE)) if constants.CURRENT_FILE != "REPL" else os.getcwd()
        
        try:
            if node.source_package:
                mod = importlib.import_module(node.source_package)
                val = getattr(mod, node.module_name)
                self.env.define(node.alias, val)
                
            else:
                target_name = node.module_name
                
                if target_name.startswith('.'):
                    abs_path = os.path.abspath(os.path.join(ctx_dir, target_name))
                    directory = os.path.dirname(abs_path)
                    filename = os.path.basename(abs_path)
                    
                    if filename.endswith('.py'):
                        module_name_stripped = filename[:-3]
                    else:
                        module_name_stripped = filename
                        
                    sys.path.insert(0, directory)
                    mod = importlib.import_module(module_name_stripped)
                    self.env.define(node.alias, mod)
                    
                else:
                    mod = importlib.import_module(target_name)
                    self.env.define(node.alias, mod)

        except ImportError as e:
            raise lunite_error("Import", f"Python module import failed: {str(e)}", node.line, node.col)
        except AttributeError as e:
            raise lunite_error("Import", f"Python module attribute error: {str(e)}", node.line, node.col)
        except Exception as e:
            raise lunite_error("Import", f"Python module integration error: {str(e)}", node.line, node.col)
    
    def visit_SetLiteral(self, node):
        elements = [self.visit(e) for e in node.elements]
        try:
            return set(elements)
        except TypeError as e:
            if "unhashable" in str(e):
                raise lunite_error(
                    "Type",
                    "Sets cannot contain mutable objects (like dicts or lists). Did you mean to use a List '[...]' instead of a Set '{...}'?",
                    node.line,
                    node.col
                )
            raise lunite_error("Runtime", str(e), node.line, node.col)

    def visit_TupleLiteral(self, node):
        elements = [self.visit(e) for e in node.elements]
        return tuple(elements)
    
    def visit_EnumDef(self, node):
        enum_val = LuniteInstance(ClassDef(node.name, Block([]), None))
        for i, member in enumerate(node.members):
            enum_val.fields[member] = i
        self.env.define(node.name, enum_val, is_const=True)
        return enum_val
    
    def visit_DestructuringDecl(self, node):
        val = self.visit(node.value)
        if not hasattr(val, '__getitem__') or not hasattr(val, '__len__'):
            raise lunite_error("Destructuring", "Value is not iterable", node.line, node.col)
        if len(val) < len(node.names):
            raise lunite_error("Destructuring", f"Not enough values to unpack (expected {len(node.names)}, got {len(val)})", node.line, node.col)
        target_env = self._get_target_env(node.is_global)
        for i, name in enumerate(node.names):
            target_env.define(name, val[i], is_const=node.is_const, is_public=node.is_public)
        return val

    def visit_AssertStatement(self, node):
        if not self.visit(node.condition):
            msg = "Assertion failed"
            if node.message:
                msg = f"Assertion failed: {self.visit(node.message)}"
            raise lunite_error("Assertion", msg, node.line, node.col)

    def visit_UpdateExpr(self, node):
        curr_val = 0
        if isinstance(node.target, Identifier):
            curr_val = self.env.get(node.target.token.value, node.line, node.col)
        elif isinstance(node.target, MemberAccess):
            obj = self.visit(node.target.obj)
            curr_val = obj.get(node.target.member_name, node.line, node.col)
        elif isinstance(node.target, IndexAccess):
            container = self.visit(node.target.target)
            idx = self.visit(node.target.index)
            try:
                curr_val = container[idx]
            except Exception:
                raise lunite_error("Index", "Invalid index access during update", node.line, node.col)
        else:
            raise lunite_error("Syntax", "Invalid target for increment/decrement", node.line, node.col)

        if not isinstance(curr_val, (int, float)):
            raise lunite_error("Type", "Cannot increment/decrement non-numeric value", node.line, node.col)

        delta = 1 if node.op.type == TOKEN_INC else -1
        new_val = curr_val + delta

        if isinstance(node.target, Identifier):
            self.env.assign(node.target.token.value, new_val, node.line, node.col)
        elif isinstance(node.target, MemberAccess):
            obj.set(node.target.member_name, new_val)
        elif isinstance(node.target, IndexAccess):
            container[idx] = new_val

        return new_val if node.is_prefix else curr_val
