import unittest
import ast
import time
from ast_transform import astor_fork
from ast_transform import rewriter, splitter_analyzer, dependency_analyzer, variables_analyzer, language_client, language_server, common
import asyncio
from threading import Thread, Event
import time

import random

gport=random.randint(50000, 60000)

class AsyncTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_ready_event = Event()
        config = common.Config()
        config.awaitable_functions = {"search_email":[], "search_teams":[], "search_meetings":[], "create_dict":[], "wrap_string":[]}
        config.module_blacklist = None
        config.wrap_in_function_def = False
        config.single_function = True
        self.server = language_server.ApiConductorServer(config,gport)
        self.server_thread = Thread(target=self.start_server)
        self.server_thread.start()
        self.server_ready_event.wait()  # Wait until the server is ready
        pass
    
    def start_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        asyncio.run(self.server_task())

    async def server_task(self):
        await self.server.start()
        self.server_ready_event.set()  # Signal that the server is ready
        await self.server.wait_for_close()
             

class TestConversation(language_client.Conversation):
    def __init__(self, client, code):
        super().__init__(client, code)
        
    def on_new_code(self, value):
        print("on new code: " + value)        
    
    def on_exception(self, value):
        print("on exception: " + value)        
    
    def on_return(self, value):
        self.return_value = value
        print("on return: " + str(value))        
    
    def on_complete(self):
        print("on complete")        
    
    def on_call(self, value):
        _fn = value["_fn"]
        _id = value["_id"]
        del value["_fn"]
        del value["_id"]
        result = None
        if _fn == "search_email":
            result = self.search_email(**value)
        elif _fn == "search_teams":
            result = self.search_teams(**value)
        elif _fn == "search_meetings":
            result = self.search_meetings(**value)
        elif _fn == "wrap_string":
            result = self.wrap_string(**value)
        return (_id, result)
     
    def search_email(self, a=0, b=0, c=0):
        return a + 100
    
    def search_teams(self, a=0, b=0, c=0):
        return a + 100
    
    def search_meetings(self, a=0, b=0, c=0):
        return a + 100
    
    def wrap_string(self, a=0, b=0, c=0):
        return a + 100
    
class TestClientServerModule(AsyncTestCase):
    def create_client(self, config):
        client = language_client.ApiConductorClient(config, "ws://localhost:"+str(gport))
        return client
    
    def test_echo(self):
        async def run_test():
            config = {
                'functions': {
                    'search_email': ['a', 'b', 'c'],
                    'search_teams': ['a', 'b', 'c'],
                    'search_meetings': ['a', 'b', 'c'],
                    'wrap_string': ['a', 'b', 'c'],
                },
                'module_blacklist': ['io']
            }
            self.client = self.create_client(config)
            print("running test")
            src = """
x = 1
a = search_email(x)
if a < 3:
    y = search_email(a + 5)
else:
    y = search_email(a + 10)
return y
"""

            conversation = TestConversation(self.client, src)
            await conversation.task
            result = conversation.return_value  
            self.assertEqual(result, 211)  
            self.client.close()

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
