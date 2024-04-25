from asyncio import wait
from asyncio import FIRST_COMPLETED
__task_dispatch = {}
__task_list = []

def AddTask(task, dispatch):
    __task_dispatch[task]=dispatch
    __task_list.Add(task)
    
async def dispatch():
    if not __task_list: return True
    done, _ = await wait(__task_list, return_when=FIRST_COMPLETED)
    # Handle completed tasks
    for task in done:
        result = task.result()
        await dispatch[task.coro](result)

        # Remove the completed task from the list
        __task_list.remove(task)
    return not __task_list

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