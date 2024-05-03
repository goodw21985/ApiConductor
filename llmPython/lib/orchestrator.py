import safety
import threading
import time
import io
import queue

class Task:
    def __init__(self):
        self.result = None
        
class Orchestrator:
    def __init__(self):
        self._task_dispatch = {}
        self._task_list = []
        self.task_lookup= {}
        self.lock = threading.Lock()
        self.signal_queue = queue.Queue()

    def Task(self, node):
        return node
    
    def _completion(self, task, val):
        time.sleep(1)  # Wait for one second
        task.Result = val
        self.signal_queue.put(task)
        
    def delayed_response(self, val):
        # Create a thread and start it
        task = Task()
        thread = threading.Thread(target=self._completion, args=(task,val))
        thread.start()    # client accessable functions 
        return task
    
    def search_email(self, a=0, b=0):
        return self.delayed_response(str(a)+ "1")

    def search_meetings(self, a=0, b=0):
        return self.delayed_response(str(a)+"2")

    def search_teams(self, a=0, b=0):
        return self.delayed_response(str(b)+"3")

    def Return(self, a):
        print(a)

    # dispatch loop functions for concurrency
    def _add_task(self, task, dispatch):
        with self.lock:
            self._task_dispatch[task]=dispatch
            self._task_list.append(task)
    
    def _dispatch(self, first):
        first()
        with self.lock:
            notDone = self._task_list
        while notDone:
            task = self.signal_queue.get()  # Wait for a signal
            with self.lock:
                fn = self._task_dispatch[task]
            fn()
        
            self.signal_queue.task_done()  # Mark the signal as processed

            # Remove the completed task from the list
            with self.lock:
                self._task_list.remove(task)
                notDone = self._task_list

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


