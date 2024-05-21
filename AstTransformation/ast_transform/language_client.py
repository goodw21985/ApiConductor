import threading
import websocket
import json
import time
import asyncio
import uuid
import inspect
from typing import get_type_hints

def managed_function(func):
    func._is_managed = True
    return func

class Action:
    def __init__(self, ev, value):
        self.ev = ev
        self.value = value

class Conversation:
    def __init__(self, client, code):
        self._event = asyncio.Event()
        self._queue = asyncio.Queue()
        self._done = False

        self.client = client
        self.conversation_id = str(uuid.uuid4())  # Generate a random GUID       
        self.code = code
        self.task = asyncio.create_task(self.run())
        
    async def run(self):
        self.client.send_message(self)
        async for action in self.dispatch():
            if action.ev == "new_code":
                self.on_new_code(action.value)
            elif action.ev == "call":
                result = self.on_call(action.value)
                self.complete(result[0], result[1])
            elif action.ev == "return":
                self.on_return(action.value)
            elif action.ev == "done":
                self.stop()
            elif action.ev == "exception":
                self.on_exception(action.value)
            else:
                raise ValueError
        self.on_complete()
        self.client.expire(self)
        
    def on_new_code(self,value):
        print("on new code: "+value)        
    
    def on_call(self,value):
        _fn=value["_fn"]
        _id = value["_id"]
        del value["_fn"]
        del value["_id"]
        result = None
        if _fn in self.client.function_lookup:
            result = self.client.function_lookup[_fn](self, **value) 
        return (_id, result)
    
    def on_return(self,value):
        print("on call: "+str(value))        
    
    def on_complete(self):
        print("on complete ")        
        
    def enqueue(self, value):
        future = asyncio.run_coroutine_threadsafe(self._enqueue(value), self.client.loop)
        
    async def _enqueue(self, value):
        self._queue.put_nowait(value)
        self._event.set()

    async def dispatch_safe(self):
        self._event.set()
        while not self._done or not self._queue.empty():
            await self._event.wait()

            while not self._queue.empty():
                value = await self._queue.get()
                yield value
                self._queue.task_done()
            self._event.clear()
            # double check for race condition
            if not self._queue.empty():
               self._event.set()
    
    async def dispatch(self):
        coroutine = self.dispatch_safe()
        while True:
            future = asyncio.run_coroutine_threadsafe(coroutine.__anext__(), self.client.loop)
            try:
                result = await asyncio.wrap_future(future)
                yield result  # Yield the result to the caller
            except StopAsyncIteration:
                break

    def stop(self):
        self._done = True
        self._event.set()

    def complete(self, action_id, result):
        message = {
            "conversation_id": self.conversation_id,
            "action_id": action_id,
            "result": result
        }
        asyncio.run_coroutine_threadsafe(self.client.send_result_message(message), self.client.loop)


class ApiConductorClient:
    def __init__(self, config, conv_cls, uri="ws://localhost:8765"):
        self.conversations = {}
        self.uri = uri
        self.ws = None
        self.config = config
        self.function_lookup={}
        self.build_function_table(conv_cls)
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.ready_event = threading.Event()
        self.loop = asyncio.get_event_loop()
        self.thread.start()
        
    def build_function_table(self, cls):
        function_list = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, "_is_managed") and method._is_managed:
                signature = inspect.signature(method)
                parameter_names = [param.name for param in signature.parameters.values()][1:]
                self.function_lookup[name]=method
                function_list[name]=parameter_names
                pass
        self.config["functions"]=function_list

    def on_message(self, ws, message):
        response_data = json.loads(message)
        conversation_id = response_data["conversation_id"]
        if conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            if "new_code" in response_data:
                conversation.enqueue(Action("new_code", response_data["new_code"]))
            elif "exception" in response_data:
                conversation.enqueue(Action("exception", response_data["exception"]))
            elif "call" in response_data:
                conversation.enqueue(Action("call", response_data["call"]))
            elif "done" in response_data:
                conversation.enqueue(Action("done", response_data["done"]))
            elif "return" in response_data:
                conversation.enqueue(Action("return", response_data["return"]))
            else:
                raise ValueError
                pass
            
    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")

    def on_open(self, ws):
        print("ws open")
        self.ws.send(json.dumps(self.config))
        self.ready_event.set()

    def expire(self, conversation):
        del self.conversations[conversation.conversation_id]
        
    def run(self):
        self.ws = websocket.WebSocketApp(self.uri,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         on_open=self.on_open)

        self.ws.run_forever()

    def close(self):
        self.ws.close()
        
    def send_message(self, conversation):
        self.conversations[conversation.conversation_id] = conversation
        message = {
            "conversation_id": conversation.conversation_id,
            "code": conversation.code
        }
        self.ready_event.wait()  # Wait until the connection is open
        self.ws.send(json.dumps(message))

    async def send_result_message(self, message):
        self.ws.send(json.dumps(message))
