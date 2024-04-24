from asyncio import wait
__task_dispatch = {}
__task_list = []

def AddTask(task, dispatch):
    __task_dispatch[task]=dispatch
    __task_list.Add(task)
    
async def dispatch():
    if not __task_list: return True
    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    # Handle completed tasks
    for task in done:
        result = task.result()
        await dispatch[task.coro](result)

        # Remove the completed task from the list
        tasks.remove(task)
    return not __task_list

    