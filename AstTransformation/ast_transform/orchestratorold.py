import safety
from asyncio import sleep
from asyncio import wait
from asyncio import BaseEventLoop
from asyncio import get_event_loop
from asyncio import FIRST_COMPLETED
from asyncio import create_task
import io

class Orchestrator:
    def __init__(self):
        self._task_dispatch = {}
        self._task_list = []
        pass
    
    # client accessable functions 
    
    async def search_email(self, a=0, b=0):
        await sleep(1)
        return "1"

    async def search_meetings(self, a=0, b=0):
        await sleep(1)
        return "2"

    async def search_teams(self, a=0, b=0):
        await sleep(1)
        return "3"

    def Return(self, a):
        print(a)

    # dispatch loop functions for concurrency
    def _add_task(self, task, dispatch):
        self._task_dispatch[task]=dispatch
        self._task_list.append(task)
  
    def _dispatch(self):
        loop = get_event_loop()
        loop.run_until_complete(self.__async_dispatch())
        loop.close()
    
    async def __async_dispatch(self):
        while self._task_list:
            done, _ = await wait(self.__task_list, return_when=FIRST_COMPLETED)
            # Handle completed tasks
            for task in done:
                await self.__task_dispatch[task]()

                # Remove the completed task from the list
                self.__task_list.remove(task)

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


