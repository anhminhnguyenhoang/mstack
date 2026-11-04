#!/usr/bin/env python3
"""Run a kernel test with its comparison functions wrapped.

Kernel tests hard-code their tolerances and print no SNR, so this patches the
comparison functions before the test module imports them:
aiter.test_common.checkAllclose (when aiter imports) and
torch.testing.assert_close. Ranks that the test spawns get the same patch
through checkwrap_site/sitecustomize.py.

usage (inside the container, from the tree under test):
  checkwrap.py snr   op_tests/test_x.py [test args...]    # measure: [snr_db=X] per check, a pass line per assert_close
  checkwrap.py shift op_tests/test_x.py [test args...]    # negative control: reference + 1, every check must fail
  checkwrap.py zero  ...                                  # negative control: rtol=atol=0, fails unless bit-exact
  checkwrap.py <mode> -m pytest <target> [pytest args...] # same, for pytest targets
"""

import importlib.abc
import importlib.util
import inspect
import math
import os
import runpy
import sys

MODES = ("snr", "shift", "zero")
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkwrap_site")


def snr_db(out, ref):
    import torch

    if not (torch.is_tensor(out) and torch.is_tensor(ref)) or out.shape != ref.shape:
        return None
    o, r = out.detach().to(torch.float64), ref.detach().to(torch.float64)
    noise = (o - r).pow(2).sum().item()
    signal = r.pow(2).sum().item()
    if math.isnan(noise) or math.isnan(signal):
        return math.nan
    return math.inf if noise == 0 else 10 * math.log10(signal / noise) if signal else -math.inf


class PostImport(importlib.abc.MetaPathFinder):
    def __init__(self, hooks):
        self.hooks = hooks

    def find_spec(self, name, path=None, target=None):
        if name not in self.hooks:
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(name)
        finally:
            sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return spec
        exec_module, hook = spec.loader.exec_module, self.hooks.pop(name)

        def run_then_patch(module):
            exec_module(module)
            hook(module)

        spec.loader.exec_module = run_then_patch
        return spec


def install(mode):
    """Patch the comparisons when this process imports them, and never import anything itself.

    Every Python a wrapped test starts runs this, including tool scripts such as
    rocm_agent_enumerator; importing torch or aiter there would recurse into the arch probe.
    """
    # pytest captures fd 1 per test; a dup taken now still reaches the saved log
    log = os.fdopen(os.dup(1), "w", buffering=1)

    def report(out, ref, msg=""):
        s = snr_db(out, ref)
        if s is not None:
            print(f"[snr_db={s:.2f}] {msg}".rstrip(), file=log)

    def patch_aiter(tc):
        orig = tc.checkAllclose
        sig = inspect.signature(orig)

        def patched(*args, **kwargs):
            ba = sig.bind(*args, **kwargs)
            ba.apply_defaults()
            if mode == "snr":
                report(ba.arguments["a"], ba.arguments["b"], ba.arguments.get("msg", ""))
                return orig(*args, **kwargs)
            if mode == "shift":
                ba.arguments["b"] = ba.arguments["b"] + 1
            ba.arguments.update(rtol=0, atol=0, tol_err_ratio=0)
            ba.arguments["msg"] = f"[checkwrap {mode}] {ba.arguments['msg']}"
            return orig(*ba.args, **ba.kwargs)

        tc.checkAllclose = patched

    def patch_torch_testing(testing):
        orig_assert_close = testing.assert_close

        def patched_assert_close(actual, expected, *args, **kwargs):
            if mode == "snr":
                report(actual, expected, "assert_close")
                orig_assert_close(actual, expected, *args, **kwargs)
                print("[checkwrap] assert_close passed", file=log)
                return None
            if mode == "shift":
                expected = expected + 1
            kwargs.update(rtol=0, atol=0)
            return orig_assert_close(actual, expected, *args, **kwargs)

        testing.assert_close = patched_assert_close

    hooks = {"aiter.test_common": patch_aiter, "torch.testing": patch_torch_testing}
    for name in list(hooks):
        if name in sys.modules:
            hooks.pop(name)(sys.modules[name])
    sys.meta_path.insert(0, PostImport(hooks))


def main():
    mode, *rest = sys.argv[1:] or [None]
    assert mode in MODES and rest, __doc__
    os.environ["CHECKWRAP_MODE"] = mode
    os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (SITE, os.environ.get("PYTHONPATH")) if p)
    install(mode)
    if rest[0] == "-m":
        module, *args = rest[1:]
        sys.argv = [module, *args]
        sys.path.insert(0, os.getcwd())
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    else:
        script, *args = rest
        sys.argv = [script, *args]
        sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
        runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
