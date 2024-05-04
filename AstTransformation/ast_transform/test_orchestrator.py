import threading
import time
import io
import queue

class Task:
    def __init__(self):
        self.Result = None
        
class Orchestrator:
    def __init__(self):
        self._task_id = {}
        self.lock = threading.Lock()
        self.signal_queue = queue.Queue()
        self.dag = None

    def Task(self, node):
        return node
    
    def _completion(self, task, val):
        time.sleep(.01)  # Wait for 10
        task.Result = val
        self.signal_queue.put(task)
        
    def start_task(self, id, val):
        # Create a thread and start it
        task = Task()
        self._add_task(task, id)
        thread = threading.Thread(target=self._completion, args=(task,val))
        thread.start()    # client accessable functions 
        return task
    
    def search_email(self, a=0, b=0, _id=None):
        return self.task(_id, str(a)+ "1")

    def search_meetings(self, a=0, b=0, _id=None):
        return self.task(_id, str(a)+"2")

    def search_teams(self, a=0, b=0, _id=None):
        return self.task(_id, str(b)+"3")

    def Return(self, a):
        print(a)

    # dispatch loop functions for concurrency
    def _add_task(self, task, id):
        with self.lock:
            self._task_id[task]=id
    
    def _dispatch_actions(self):
        actions_to_take = []
        with self.lock:
            for action in self.dag.keys():
                if len(self.dag[action])==0:
                    actions_to_take.append(action)
                    
            for key in actions_to_take:
                del self.dag[key]
            
        for action in actions_to_take:
            action()
            
        return self.dag
        
    def _update_dag(self, task):
        with self.lock:
            for targets in self.dag.values():
                if task in targets:
                   targets.remove(task)

    def _dispatch(self, dag):
        self.dag = dag
        while self._dispatch_actions():
            task = self.signal_queue.get()  # Wait for a signal
            self._update_dag(self._task_id[task])
        
            self.signal_queue.task_done()  # Mark the signal as processed


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


