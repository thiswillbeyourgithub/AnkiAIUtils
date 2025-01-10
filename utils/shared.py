import sys
from typing import Optional, Any
from dataclasses import MISSING

def is_verbose() -> bool:
    cmd = " ".join(sys.argv)
    if " -v " in cmd or " --verbose " in cmd:
        return True
    else:
        return False

class SharedModule:
    """module used to store information between python files"""
    # things that are not changed when self.reset is called
    VERSION: str = "1.0"
    _instance: Optional[Any] = None  # to make a singleton
    red = MISSING
    yellow = MISSING
    reset = MISSING
    white = MISSING
    purple = MISSING

    verbose = is_verbose()

    def __new__(cls):
        "make sure the instance will be a singleton"
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            return cls._instance
        else:
            raise Exception("Tried to create another instance of SharedModule")

    def __setattr__(self, name: str, value) -> None:
        "forbid creation of new attributes."
        if hasattr(self, name):
            assert getattr(self, name) is MISSING, f"tried to declare twice the attribute '{name}'"
            object.__setattr__(self, name, value)
        else:
            raise TypeError(f'SharedModule forbids the creation of unexpected attribute "{name}"')

shared = SharedModule()
