import builtins

# code to guarantee safety by only allowing white listed modules
# to be imported            
ALLOWED_MODULES = set([
    'math',
    'os',
    'warnings',
    '_io',
    'io',
    'socket',
    'sys',
    'base_events',
    'collections',
    'collections.abc',
    'concurrent.futures',
    'concurrent.futures._base',
    'logging',
    'time',
    're',         # todo: Set Timeouts in re.match() and re.search()
    'traceback',  # todo: logging intercepts?
    'weakref',
    'types',
    'string',
    'threading',  # statically blacklisted from client code
    'atexit',
    'errno',
    'subprocess', # statically blacklisted from client code
    'functools',
    'heapq',
    'itertools',
    'stat',
    'ssl',
    'enum',
    'inspect',
    'contextvars',
    'contextlib',
    '_contextvars',
    'signal',
    'reprlib',
    '_asyncio',   # covered by monkey patching io and threads and sockets
    'asyncio',    # covered by monkey patching io and threads and sockets
    'asyncio.events',
    'asyncio.base_futures',
    'asyncio.exceptions',
    'asyncio.base_tasks',
    'linecache',
    'asyncio.coroutines',
    'log',
    'typing',
    'coroutines',
    'events',
    'exceptions',
    'futures',
    'locks',
    'protocols',
    'runners',
    'queues',
    'streams',
    'tasks',
    'taskgroups',
    'timeouts',
    'threads',
    'transports',
    'windows_events',
    '_overlapped',
    '_socket',
    '_winapi',
    'msvcrt',
    'struct',
    'selectors',
    '_winapi',
    'msvcrt',
    'tempfile',
    'ast',
    'django.utils.datastructures',
    'django.forms',
    'ctypes',

])

ALLOWED_FROMLIST = set([
    'DefaultEventLoopPolicy',
    'constants',
    'coroutines',
    'events',
    'format_helpers',
    'base_futures',
    'exceptions',
    'futures',
    'protocols',
    'sslproto',
    'transports',
    'staggered',
    'locks',
    'mixins',
    'tasks',
    'base_tasks',
    'timeouts',
    'trsock',
    'streams',
    'base_subprocess',
    'proactor_events',
    'base_events',
    'selector_events',
    'base_events',
    'windows_utils',

])

ALLOWED_ASYNCIO_FROMLIST = [
    "sleep", "wait"
]


# Override the built-in __import__ function to enforce the whitelist
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in ALLOWED_MODULES:
        # If the module is in the whitelist, allow the import
        return __hiddenImport(name, globals, locals, fromlist, level)
    elif name == "" and len(fromlist)==1 and fromlist[0] in ALLOWED_FROMLIST:
        return __hiddenImport(name, globals, locals, fromlist, level)
    elif name == "asyncio" and len(fromlist)==1 and fromlist[0] in ALLOWED_ASYNCIO_FROMLIST:
        return __hiddenImport(name, globals, locals, fromlist, level)
    else: 
        # If the module is not in the whitelist, raise an ImportError
        raise ImportError(f"Import of module '{name}' is not allowed")

def disabled_FileIO(*args, **kwargs):
    raise PermissionError("Access to the file system is disabled")

def disabled_threading(*args, **kwargs):
    raise PermissionError("Access to the thread system is disabled")

# Replace the built-in __import__ function with the custom implementation
__hiddenImport = builtins.__import__
builtins.__import__ = safe_import
builtins.open = disabled_FileIO

# Required functions to support implicit awaiting for workflows
#
#

from asyncio import sleep
from asyncio import wait
from asyncio import BaseEventLoop
from asyncio import get_event_loop
from asyncio import FIRST_COMPLETED
from asyncio import create_task
import io
import threading
threading.Thread = disabled_threading
threading.Lock = disabled_threading
threading.RLock = disabled_threading
threading.Condition = disabled_threading
threading.Semaphore = disabled_threading
threading.BoundedSemaphore = disabled_threading
threading.Event = disabled_threading
threading.Timer = disabled_threading
# to allow socket library to be loaded safely, we need to effectively disable it
# the alternative to monkey patching is to create a custom evem
original_sock_connect = BaseEventLoop.sock_connect

async def restricted_sock_connect(self, sock, address):
    host, port = address
    if host not in ["localhost", "127.0.0.1"]:  # Allow only local connections
        raise ConnectionError("External connections are disabled.")
    await original_sock_connect(self, sock, address)

BaseEventLoop.sock_connect = restricted_sock_connect

io.FileIO = disabled_FileIO

__task_dispatch = {}
__task_list = []
__fake_event_loop = get_event_loop

def _add_task(task, dispatch):
    __task_dispatch[task]=dispatch
    __task_list.append(task)
  
def _dispatch():
    loop = get_event_loop()
    loop.run_until_complete(async_dispatch())
    loop.close()
    
def T(n):
    return create_task(n)

async def async_dispatch():
    while __task_list:
        done, _ = await wait(__task_list, return_when=FIRST_COMPLETED)
        # Handle completed tasks
        for task in done:
            await __task_dispatch[task]()

            # Remove the completed task from the list
            __task_list.remove(task)

async def search_email(a=0, b=0):
    await sleep(1)
    return "1"

async def search_meetings(a=0, b=0):
    await sleep(1)
    return "2"

async def search_teams(a=0, b=0):
    await sleep(1)
    return "3"

def Return(a):
    print(a)

# Class to allow operators to act the way we want on json
# like results coming back from API calls and manipulations on those objects
# we will broadly automate this conversion in classes that are inside
# classes maked with JObject attribute, or in LLM generated code.
#  a.b -> J(a).b  (through code transformation), unless we know a priori that the object is not a dictionary 
#
class J:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        if isinstance(self._data, dict):
            return self._data[key]
        else:
            return getattr(self._data, key)

    def __setitem__(self, key, value):
        if isinstance(self._data, dict):
            self._data[key] = value
        else:
            setattr(self._data, key, value)

    def __delitem__(self, key):
        if isinstance(self._data, dict):
            del self._data[key]
        else:
            delattr(self._data, key)   


