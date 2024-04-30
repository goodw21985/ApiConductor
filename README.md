# llmPython

Wrapper for IronPython and (later) CPython that makes it practical for LLMs to write python code for custom API operations.

If you have code that has access to both an LLM and an API you will be calling, then you are an orchestrator.  LLmPython is a nuget package that you can use in the orchestrator to run specialized python code.

Goals of LlmPython:

# Safety
See detailed safety section below
All code will pre-pended with an include statement of our own which ensures safety afterwards.  

Since this code will run in the cloud, we have a white list of allowed modules, with the following explicitly always inappropriate:  system, io   

# code transformation

LLmPython code will be transforms into IronPython code to add functionality:

## Allow for attribute syntax to be used on Dictionaries like Javascript.  

This willl likely require being aware of when literal arrays and objects need to be implicitly case to a class that implements attributes this is perhaps managed by type hints knowledge of when the syntax is ambiguous

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

# Details of safety

If an LLM is going to write python code it will hallucinate, but even more importantly it may be subject to an injection attack, where a malicious user could try to get the LLM to write code which is unsafe.

Unsafe can mean three things:  
1. it can do damage to the infrastructure or data stored in the infrastructure
2. it can capture sensitive information either from the system or other clients
3. it can destabilize the service through a denial of service attack

As a design principle, LlmPython reuses the python interpreter instance across many LLM calls, because initializing the interpreter (and loading all the libraries) is too much overhead.

It is not necessary to place the interpreter in an isolated process within a controlled container, although this is possible and offers an additional layer of security.  But even this still requires isolation 
within each invocation of the interpreter to make sure data is not leaked and the process is not destabilized.

Safety is implemented in layers:

## Code analysis and rewriting

Any python code that is written by an LLM is REWRITTEN.   This is done within python, using the python ast library.  
Client code is highly restricted, even if the standard library has more privilege within the interpreter
1. certain modules are blacklisted (sys, io, sockets, subprocess, eval, exec)   LlmPython is designed to write small (and chained) workflows, not full applications
2. the global statement is disallowed, and no client code runs in the global namespace, it always runs under a private module
3. one module is forcibly loaded, called orchestrator, which is how all client code must interact with the outside world.
4. the orchestrator module provides the functions that interact with the application, and the application (the orchestrator) manages LLM calls, and API access, and other IO.
5. the orchestrator module also handles concurrency through a dispatch module that the LLM itelf does not know about.

Code that does not compile, or does not pass code analysis will not be run.

## module library access

a copy of the python standard library is provided with LlmPython, and only this library can be used.   Different versions of the standard library from elsewhere on the host cannot be used.
the author of the orchestrator that links to LlmPython provides the orchestrator module, which allows other capability
no other modules are available to the interpreter at any time.

## use of double underlines and single underlines
function names and variables that are not intended for use by the LLM are given double underscore names because the interpreter will scramble theses symbol names internally

single underscores are used for internal values that are generated by client code.

it is expected that client code would not use underscores at all to avoid name collisions, but this is not enforced.

## Safety hooks and Monkey patching

when the client code forcibly does an import orchestrator, it loads a safety.py module.  This disables features in the standard library from ever running by the interpreter

It is the only code from LlmPython that uses global namespace and modifies system variables, and the client code is prevented from doing the same with static analysis.

The import capability of the interpreter is hooked, and through this only white listed modules can be loaded.   A lot of the library needs to be imported just to get async functionality to work,
and some of the imported functionality could be unsafe if used.

Some parts of the standard library are disabled with monkey-patching, meaning that entry points within the library are overwritten such that code cannot run.  The standard library itself is not modified, 

When newer versions of the standard library are included in LlmPython, the monkey patching needs to be re-evaluated.

Specifically the following things are disabled:
### file access
The interpreter will never read or write files from the file system located in the server

### network io
socket connections within the same box are allowed (and seem to be how concurrency works in python).  However any socket connections outside of localhost are blocked.

### threads
the entire threading library is disabled.   LlmPython should run entirely in one thread, and is not intended to be a large consumer of resources on a local box.

TODO: threading cannot be disabled if you are running code in the visual studio debugger, so a version that works in a debugger is needed

There probably will need to be a debug orchestrator anyway, so there can be different safety rules

## The orchestrator module
Client code must







