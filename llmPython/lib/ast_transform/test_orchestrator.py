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
        self._private_queue={}
        self.dag = None
        
    def _create_task(self, result):
        task = Task()
        task.Result=result
        return task

    def Task(self, node):
        return node
    
    def _completion(self, task, val):
        time.sleep(.01)  # Wait for 10
        task.Result = val
        id = self._task_id[task]
        if id in self._private_queue:
            self._private_queue[id].put(task)
        else:
            self.signal_queue.put(task)


    def _is_awaitable(self, id):
        with self.lock:
            seen=False
            for item in self.dag.values():
                for item2 in item:
                    if item2==id:
                        return True
                    if isinstance(item2, list):
                        for item3 in item2:
                            if item3==id:
                                return True

        return False

    def start_task(self, id, val):
        # Create a thread and start it
        task = Task()
        self._add_task(task, id)
        if not self._is_awaitable(id):
            self._private_queue[id]=queue.Queue()
            
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

    def _complete(self, task):
        self.signal_queue.put(task)

    def _wait(self, val, id):
        private_queue=self._private_queue[id]
        task = private_queue.get()  # Wait for a signal
        private_queue.task_done()  # Mark the signal as processed
        return val.Result

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
                   
                # check for an array within the array.   The inner array is removed id ANY entryies of the inner_array match
                # this represents when ANY event in that list is sufficient, rather than ALL events being needed   
                remove_element=None
                for element in targets:
                    if isinstance(element, list):
                        if task in element:
                            remove_element=element
                if remove_element:
                    targets.remove(remove_element)
                        

    def _dispatch(self, dag):
        self.dag = dag
        while self._dispatch_actions():
            task = self.signal_queue.get()  # Wait for a signal
            if isinstance(task, str):
                self._update_dag(task)
            else:
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


