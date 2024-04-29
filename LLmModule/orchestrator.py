import builtins

# Required functions to support implicit awaiting for workflows
#
#
from asyncio import wait
from asyncio import FIRST_COMPLETED
__task_dispatch = {}
__task_list = []

def _add_task(task, dispatch):
    __task_dispatch[task]=dispatch
    __task_list.Add(task)
    
async def _dispatch():
    while __task_list:
        done, _ = await wait(__task_list, return_when=FIRST_COMPLETED)
        # Handle completed tasks
        for task in done:
            result = task.result()
            await dispatch[task.coro](result)

            # Remove the completed task from the list
            __task_list.remove(task)

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


# code to guarantee safety by only allowing white listed modules
# to be imported            
ALLOWED_MODULES = [
    'math',
    'os',
    # Add more modules as needed
]


# Override the built-in __import__ function to enforce the whitelist
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in ALLOWED_MODULES:
        # If the module is in the whitelist, allow the import
        return __builtins__.__import__(name, globals, locals, fromlist, level)
    else:
        # If the module is not in the whitelist, raise an ImportError
        raise ImportError(f"Import of module '{name}' is not allowed")

# Replace the built-in __import__ function with the custom implementation
builtins.__import__ = safe_import


