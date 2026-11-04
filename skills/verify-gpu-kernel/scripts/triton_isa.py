#!/usr/bin/env python3
"""Lay out a Triton cache as an isa.diff dump: OUT/<kernel symbol>/00_final_isa.s.

Triton names cache folders by a source hash, so base and head never match. Key
by the `.amdhsa_kernel` symbol instead: it stays stable across revisions, and it
carries the constexpr config only for kernels built with aiter's make_kernel_repr.

usage: triton_isa.py TRITON_CACHE_DIR OUT_DIR
       triton_isa.py --selftest
exit:  0 ok, 2 no kernel found or two different binaries share one symbol
"""

import hashlib
import pathlib
import re
import sys
import tempfile

SYM = re.compile(r"^\s*\.amdhsa_kernel\s+(\S+)", re.M)


def folder(sym):
    # filesystem names stop at 255 bytes; keep long symbols unique with a hash
    return sym if len(sym) <= 200 else sym[:190] + "_" + hashlib.sha1(sym.encode()).hexdigest()[:8]


def layout(cache, out):
    seen = {}
    for f in sorted(pathlib.Path(cache).rglob("*.amdgcn")):
        text = f.read_text(errors="replace")
        syms = SYM.findall(text)
        if not syms:
            print(f"skip {f}: no .amdhsa_kernel line")
            continue
        sym = syms[0]
        if sym in seen:
            if seen[sym] != text:
                print(f"ambiguous: two different binaries for {sym}. Narrow the run to one shape.")
                return 2
            continue
        seen[sym] = text
        d = pathlib.Path(out) / folder(sym)
        d.mkdir(parents=True, exist_ok=True)
        (d / "00_final_isa.s").write_text(text)
    print(f"{len(seen)} kernel(s) -> {out}")
    return 0 if seen else 2


def selftest():
    asm = "\t.amdhsa_kernel {s}\n\t.end_amdhsa_kernel\n{x}\n"
    with tempfile.TemporaryDirectory() as t:
        c = pathlib.Path(t, "cache")
        for h, s, x in [("H1", "_k_A_1", ""), ("H2", "_k_A_1", ""), ("H3", "_k_B_2", "")]:
            pathlib.Path(c, h).mkdir(parents=True)
            pathlib.Path(c, h, "k.amdgcn").write_text(asm.format(s=s, x=x))
        assert layout(c, pathlib.Path(t, "out")) == 0
        assert sorted(p.name for p in pathlib.Path(t, "out").iterdir()) == ["_k_A_1", "_k_B_2"]
        pathlib.Path(c, "H4").mkdir()
        pathlib.Path(c, "H4", "k.amdgcn").write_text(asm.format(s="_k_A_1", x="v_add"))
        assert layout(c, pathlib.Path(t, "out2")) == 2
        assert layout(pathlib.Path(t, "empty"), pathlib.Path(t, "out3")) == 2
    print("selftest OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(layout(sys.argv[1], sys.argv[2]))
