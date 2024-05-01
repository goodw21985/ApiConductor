import clr
clr.AddReference("System")
from System.Threading import Thread, ThreadStart

def thread_proc():
    print("Hello from a thread!")

thread_start = ThreadStart(thread_proc)
thread = Thread(thread_start)
thread.Start()
thread.Join()
