import asyncio
import threading
import websockets
import json
import uuid
import time

class Action:
    def __init__(self, ev, value):
        self.ev=ev
        self.value=value

class Conversation:
    def __init__(self, client, code):
        self._event = asyncio.Event()
        self._queue = asyncio.Queue()
        self._done = False

        self.client=client
        self.conversation_id = str(uuid.uuid4())  # Generate a random GUID       
        self.code=code

    def set_event(self, value):
        self._queue.put_nowait(value)
        self._event.set()

    async def dispatch(self):
        self._event.set()
        while not self._done or not self._queue.empty():
            await self._event.wait()  # Wait until the event is set
            while not self._queue.empty():
                value = await self._queue.get()
                yield value
                self._queue.task_done()
            self._event.clear()  # Clear the event for the next iteration

    def stop(self):
        self._done = True
        self._event.set()  # Ensure the loop in dispatch can exit


    def complete(self, action_id, result):
        message = {
            "conversation_id": self.conversation_id,
            "action_id": action_id,
            "result": result
            }

        asyncio.run_coroutine_threadsafe(self.client.send_message(message), self.client.loop)
    
class ApiConductorClient:
    def __init__(self, uri="ws://localhost:8765"):
        self.conversations={}
        self.uri = uri
        self.loop = asyncio.get_event_loop()
        self.websocket = None
        self.loop.run_until_complete(self.connect())
        self.thread = threading.Thread(target=self.start_event_loop)
        self.thread.start()
        
    def start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        print(f"Connected to {self.uri}")
        # Start the listening task
        self.loop.create_task(self.listen())

    async def listen(self):
        async for message in self.websocket:
            response_data = json.loads(message)
            print(f"Received: {response_data}")
            print("----")
            conversation_id = response_data["conversation_id"]
            if conversation_id in self.conversations:
                conversation = self.conversations[conversation_id]
                if "new_code" in response_data:
                    conversation.set_event(Action("new_code",response_data["new_code"]))
    
    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))
        print(f"Sent: {message}")

    def start_conversation(self, code):
        conversation = Conversation(self, code)
        conversation.client = self
        self.conversations[conversation.conversation_id]=conversation
        
        message = {
            "conversation_id": conversation.conversation_id,
            "code": conversation.code
        }

        asyncio.run_coroutine_threadsafe(self.send_message(message), self.loop)
        print(f"Started conversation with ID: {conversation.conversation_id}")
        
        return conversation

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

async def consume(conversation):
    async for action in conversation.dispatch():
        print("*******")
        print(f"Consumed action: {action.ev}, value: {action.value}")
        print("*******")
    
async def process_conversation(client, src):
    conversation = client.start_conversation(src)
    consumer_task = asyncio.create_task(consume(conversation))
    try:
        await asyncio.wait_for(consumer_task, timeout=10)  # specify your desired timeout in seconds
    except asyncio.TimeoutError:
        print("The consumer task timed out")    
        # await consumer_task

if __name__ == '__main__':
    client = ApiConductorClient()
    src = """
x=0
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
    asyncio.run(process_conversation(client,src))

    asyncio.sleep(5)
    client.stop()

