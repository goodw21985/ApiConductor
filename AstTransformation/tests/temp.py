import asyncio
import threading
import atexit
import time
from ast_transform import common, language_server

class AsyncTestCase:
    def __init__(self):
        # Configuration setup
        config = common.Config()
        config.awaitable_functions = {
            "search_email": [],
            "search_teams": [],
            "search_meetings": [],
            "create_dict": [],
            "wrap_string": []
        }
        config.module_blacklist = None
        config.wrap_in_function_def = False
        config.single_function = True
        
        # Initialize the server
        self.server = language_server.ApiConductorServer(config)
        
        # Create a new event loop
        self.loop = asyncio.new_event_loop()
        
        # Create and start the server thread
        self.server_thread = threading.Thread(target=self.start_server)
        self.server_thread.start()
        
        # Register the cleanup function
        atexit.register(self.cleanup)
        
    def start_server(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.server.start())
        
    def cleanup(self):
        # Stop the server and close the loop
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.server_thread.join()
        self.loop.close()

# Initialize AsyncTestCase instance
x = AsyncTestCase()
while True:
    time.sleep(.01)