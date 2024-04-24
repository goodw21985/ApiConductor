# llmPython

Wrapper for IronPython that makes it practical for LLMs to write python code for custom API operations.

If you have code that has access to both an LLM and an API you will be calling, then you are an orchestrator.  LLmPython is a nuget package that you can use in the orchestrator to run specialized python code.

Goals of LlmPython:

# Safety
All code will pre-pended with an include statement of our own which ensures safety afterwards.  

Since this code will run in the cloud, we have a white list of allowed modules, with the following explicitly always inappropriate:  system, io   

# code transformation

LLmPython code will be transforms into IronPython code to add functionality:

## Call backs of API functions from python to C# code in the orchestrator, with asynchronous completions

i.e. SearchEmail() function should be forwarded to the orchestrator for execution

## Implicit parallelization

An LLM should not have to write async code, if two parallel calls to the orchestrator are placed in order, and there is no dependency, they should accor in parallel

## Implicit imports

we don't want LLMs creating unnecessary tokens, so a list of fixes imports may also be prepended

## Extensibility Client Library

clients of LLmPython can provide a python module of functions that will be usable at the root name space.  This library will also be transformed, to be able to use the above new capabilities.

### Creating function signatures for calls that are forwarded to the orchestrator

```
def search_email(keywords=None, start:str=None, end:str=None):
    ...
```

when this code is interpreted in python, a string containing the code with resolved values will be forwarded to the orchestrator with the arguments in a dictionary. 
The orchestrator will be expected to respond asynchronously when the action is completed.

Note, orchestrator function signatures are NOT async/await, but are transformed to async/await functionality through code analysis and dependency tracking.  Where ever possible, orchestrator functions are called in parallel.   

Only orchestrator functions are parallelized implicitly

### Adding your own functions to your library

although your library exists as a module, all the functions will be translated to the root namespace, because an LLM is not likely to want to create its own function definitions, but rather reuse existing ones.

client library code can do anything that is legal in python (or rather that is supported by Iron Python), plus may also use orchestrator functions.

# Things to figure out:

## JSON interop

## Debuggability from logs.

If the orchestrator creates logs, there needs to be a mechanism to scrape those logs, and be able to rerun the query in visual studio python with the search results repopulating the appropriate function calls

## Implicit return statement








