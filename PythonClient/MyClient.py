import api_conductor_client
import asyncio
import time

class MyConversation(api_conductor_client.Conversation):
    def __init__(self, client, code):
        super().__init__(client, code)
        complete=False
        
    def on_new_code(self,value):
        print("on new code: "+value)        
    
    def on_call(self,value):
        print("on call: "+value)        
    
    def on_exception(self,value):
        print("on exception: "+value)        
    
    def on_complete(self):
        print("on complete ")        
        complete=True
    

if __name__ == '__main__':
    config = {'functions':{
        'search_email':['a','b','c'],
        'search_teams':['a','b','c'],
        'search_meetings':['a','b','c'],
        'wrap_string':['a','b','c'],
        }, 'module_blacklist':['io']}

    client = api_conductor_client.ApiConductorClient(config)

    src = """
x=0
a=search_email(x)
if (a<3):
    y=search_email(a+5)
else:
    y=search_email(a+10)
return y
"""
    conversation = MyConversation(client, src)

    while not conversation.complete:
        time.sleep(.1)  # Use time.sleep instead of asyncio.sleep in synchronous code

    client.stop()
