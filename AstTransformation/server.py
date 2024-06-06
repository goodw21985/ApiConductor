from ast_transform import language_server
from ast_transform import common
import asyncio
import built_ins

async def main():
    config = common.Config()
    config.awaitable_functions = {"search_email":[], "search_teams":[], "search_meetings":[], "create_dict":[], "wrap_string":[]}
    config.exposed_functions = {'now'}
    config.built_ins_module = built_ins
    config.module_blacklist=None
    config.wrap_in_function_def =False
    config.single_function=True

    server = language_server.ApiConductorServer(config)
    await server.start()
    
    await server.wait_for_close()
    
asyncio.run(main())
