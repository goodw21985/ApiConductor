import builtins


# Define a list of allowed module names
ALLOWED_MODULES = [
    'math',
    'os',
    # Add more modules as needed
]


# Override the built-in __import__ function to enforce the whitelist
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in ALLOWED_MODULES:
        # If the module is in the whitelist, allow the import
        return __builtins__.__import__(name, globals, locals, fromlist, level)
    elif name == "asyncio" and len(fromlist) == 1 and "wait" in fromlist:
        # If the module is in the whitelist, allow the import
        return __builtins__.__import__(name, globals, locals, fromlist, level)
    else:
        # If the module is not in the whitelist, raise an ImportError
        raise ImportError(f"Import of module '{name}' is not allowed")

# Replace the built-in __import__ function with the custom implementation
builtins.__import__ = safe_import

def log(name):
    print(name)    
