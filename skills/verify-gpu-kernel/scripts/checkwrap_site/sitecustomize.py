"""Apply the checkwrap.py patch in every Python process that a wrapped test starts.

checkwrap.py puts this directory first on PYTHONPATH and sets CHECKWRAP_MODE, so a
rank started by torch.multiprocessing.spawn or torchrun patches itself at startup.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# this file shadows the interpreter's own sitecustomize; run that one first
for d in sys.path:
    path = os.path.join(os.path.abspath(d or "."), "sitecustomize.py")
    if os.path.dirname(path) != HERE and os.path.isfile(path):
        with open(path) as f:
            exec(compile(f.read(), path, "exec"), {"__name__": "sitecustomize", "__file__": path})
        break

if os.environ.get("CHECKWRAP_MODE"):
    import importlib.util

    spec = importlib.util.spec_from_file_location("checkwrap", os.path.join(os.path.dirname(HERE), "checkwrap.py"))
    checkwrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checkwrap)
    checkwrap.install(os.environ["CHECKWRAP_MODE"])
