from asyncio import wait
__task_dispatch = {}
__task_list = []

def AddTask(task, dispatch):
    __task_dispatch[task]=dispatch
    __task_list.Add(task)
    
async def dispatch():
    if not __task_list: return True
    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    # Handle completed tasks
    for task in done:
        result = task.result()
        await dispatch[task.coro](result)

        # Remove the completed task from the list
        tasks.remove(task)
    return not __task_list

# trick class to allow us to use attribute syntax on a dictionary, when 
# it is ambiguous whehter the object is a dictionary or class
#
#  a.b -> DictWrapper(a).b  (through code transformation), unless we know a priori that the object is not a dictionary 
#
class DictWrapper:
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