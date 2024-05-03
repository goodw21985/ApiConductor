import builtins

# safety.py is the only place that globals are used, or code is placed
# in global namespace.   This code will change how the interpreter
# acts for all clients, whether they use the safety module or not.

# client code is forcably scanned and modified such that 
# import orchestrator always is the first line of code
# orchestrators first line should be to import safety.py

# certain parts of the standard library are needed to manage tasks
# and do basic functionality independent of client code and so
# this safety module must permit them to run
# Parts of the standard library is monkey patched to disable functionality below:
# this disables this functionality for ALL python code, not just client code
#    file io. 
#    networking outside of local host
#    threading
#    modules can only be loaded if they are on the white list.

# there is static code analysis outside of safety.py that also specifically
# black lists some modules for client code, that otherwise can run, such as
# sys, os, subprocess (see module_blacklist)


# White listed modules
ALLOWED_MODULES = set([
    'math',
    'threading',
    'sys',
    '_thread',
    'time',
    'traceback',
    'linecache',
    'os',
    'tokenize',
    'builtins',
    'codecs',
    '_codecs',
    'collections',
    '_collections_abc',
    '_collections',
    'operator',
    '_operator',
    'keyword',
    'heapq',
    'itertools',
    '_heapq',
    '_weakref',
    'reprlib',
    'io',
    '_io',
    'abc',
    're',
    'token',
    '_weakrefset',
    'queue',
    'errno',
    'stat',
    '_stat',
    'nt',
    'ntpath',
    'genericpath',
    'os.path',
])


# modules that can be loaded as "from . import X"
ALLOWED_FROMLIST = set([
])

# Override the built-in __import__ function to enforce the whitelist
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in ALLOWED_MODULES:
        return __hiddenImport(name, globals, locals, fromlist, level)
    elif name == "" and len(fromlist)==1 and fromlist[0] in ALLOWED_FROMLIST:
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

if False:
    # disable fileio
    builtins.open = disabled_FileIO

# to allow socket library to be loaded safely, we need to effectively disable it
# the alternative to monkey patching is to create a custom evem
# original_sock_connect = asyncio.BaseEventLoop.sock_connect
# 
# async def restricted_sock_connect(self, sock, address):
#     host, port = address
#     if host not in ["localhost", "127.0.0.1"]:  # Allow only local connections
#         raise ConnectionError("External connections are disabled.")
#     await original_sock_connect(self, sock, address)
# 
# asyncio.BaseEventLoop.sock_connect = restricted_sock_connect

# import io
# io.FileIO = disabled_FileIO

