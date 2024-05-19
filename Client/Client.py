import threading
from xml.etree.ElementTree import QName
import websocket
import json
import time
import asyncio
import uuid

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

    def enqueue(self, value):
        self._queue.put_nowait(value)
        self._event.set()

    async def dispatch_async(self):
        self._event.set()
        while not self._done or not self._queue.empty():
            await self._event.wait()

            while not self._queue.empty():
                value = await self._queue.get()
                yield value
                self._queue.task_done()
            self._event.clear()

    def dispatch(self):
        coroutine = self.dispatch_async()
        while True:
            future = asyncio.run_coroutine_threadsafe(coroutine.__anext__(), self.client.loop)
            try:
                result = future.result()
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
        asyncio.run_coroutine_threadsafe(self.client.send_message(message), self.client.loop)


class WebSocketClient:
    def __init__(self, uri):
        self.conversations = {}
        self.uri = uri
        self.ws = None
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.ready_event = threading.Event()
        self.loop = asyncio.get_event_loop()

    def on_message(self, ws, message):
        response_data = json.loads(message)
        print(f"Received: {response_data}")
        conversation_id = response_data["conversation_id"]
        if conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            if "new_code" in response_data:
                conversation.enqueue(Action("new_code", response_data["new_code"]))
            else:
                pass
            
    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")

    def on_open(self, ws):
        print("ws open")
        self.ready_event.set()

    def run(self):
        self.ws = websocket.WebSocketApp(self.uri,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         on_open=self.on_open)
        self.ws.run_forever()

    def start(self):
        self.thread.start()

    def send_message(self, code):
        conversation = Conversation(self, code)
        self.conversations[conversation.conversation_id] = conversation
        message = {
            "conversation_id": conversation.conversation_id,
            "code": conversation.code
        }
        self.ready_event.wait()  # Wait until the connection is open
        self.ws.send(json.dumps(message))
        print("ws send")
        return conversation

# Usage
uri = "ws://localhost:8765"
client = WebSocketClient(uri)
client.start()

# Send a message
src = """
x=0
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
conversation = client.send_message(src)
for action in conversation.dispatch():
        print("*******")
        print(f"Consumed action: {action.ev}, value: {action.value}")
        print("*******")

# Keep the main thread running
while True:
    pass
