#!/usr/bin/env bash
# Self-checks for shell-guard.py (the beforeShellExecution hook and the login lookup) and gh-as.sh.
# Offline: fixtures are local git repos, a fixture env.md, and a fake gh on PATH.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
G="$ROOT/scripts/shell-guard.py" GA="$ROOT/scripts/gh-as.sh"
export MSTACK_ENV="$T/env.md" HOME="$T/home" PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$T/bin"

cat > "$T/env.md" <<'EOF'
## PR tool

| Host or org | Push remote (name, scheme) | PR path (`gh` or MCP namespace) | Source |
| --- | --- | --- | --- |
| github.com (ROCm, triton-lang, fixture-fork) | origin = your fork (ssh) | gh (signed in as fixture-fork) | test |
| github.com (Acme-Internal: tool) | origin = Acme-Internal/tool (ssh) | gh as **fixture-work** only: `GH_TOKEN=$(gh auth token -u fixture-work) gh ...` | test |
| github.com (Empty-Org: empty) | origin = Empty-Org/empty (ssh) | gh (`gh auth token -u fixture-empty`) | test |
| gitlab.example.test (team) | origin (ssh) | MCP namespace fixture-mcp | test |

## Git

| Branch prefix | Public push | Source |
| --- | --- | --- |
| fixture | never | test |
EOF

mk() {
  git init -q "$T/repos/$1"
  if [ -n "${2:-}" ]; then git -C "$T/repos/$1" remote add origin "$2"; fi
  return 0
}
mk work git@github.com:Acme-Internal/tool.git
mk fork git@github.com:fixture-fork/mstack.git
mk other https://github.com/someone-else/x.git
mk empty git@github.com:Empty-Org/empty.git
mk gitlab git@gitlab.example.test:team/x.git
mk plain ""

hook() {
  python3 -c 'import json,sys; print(json.dumps({"command": sys.argv[1], "cwd": sys.argv[2]}))' "$1" "${2:-$T}" | python3 "$G" hook
}
perm() { hook "$1" "${2:-$T}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["permission"])'; }
says() { hook "$1" "${2:-$T}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("user_message", ""))'; }
expect() { local got; got=$(perm "$2" "${3:-$T}"); [ "$got" = "$1" ] || fail "$1 expected, got $got: $2"; }
quiet() { [ "$(perm "$1" "${2:-$T}")" = allow ] && [ -z "$(says "$1" "${2:-$T}")" ] || fail "allow with no message expected: $1"; }
warn() {
  [ "$(perm "$1" "${3:-$T}")" = allow ] || fail "warn must not block: $1"
  says "$1" "${3:-$T}" | grep -q -- "$2" || fail "warn for $1 lacks '$2'"
}

# --- sleep
for c in "sleep 30" "sleep 120" "sleep 300" "sleep 45.5" "sleep 30s" "sleep 1m" "sleep 0.5m" \
  "cd x && sleep 60" "make; sleep 45; ls" "bash -c 'sleep 90'" "(sleep 40)"; do
  expect deny "$c"
done
for c in "sleep 2" "sleep 10" "sleep 29" "sleep 2.5" "echo sleep 120"; do
  expect allow "$c"
done
expect deny "sleep 120 # shell-guard: allow pattern-kill"
quiet "sleep 120 # shell-guard: allow sleep"
hook "sleep 120" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["user_message"] and d["agent_message"]' \
  || fail "deny lacks user_message or agent_message"
hook "sleep 120" | grep -q "allow sleep" || fail "deny does not name the exception marker"
echo "ok sleep"

# --- pattern-kill
for c in "pkill -f python" "killall rocm-smi" "sudo pkill python" "kill \$(pgrep -f train.py)" \
  "kill -9 \$(pgrep -f train)" "kill \`pgrep train\`" "pgrep -f train | xargs kill -9"; do
  expect deny "$c"
done
for c in "kill 4242" "kill \$PID" "ps aux | grep pkill" "echo pkill"; do
  expect allow "$c"
done
quiet "pkill -f x # shell-guard: allow pattern-kill"
echo "ok pattern-kill"

# --- docker-user
for c in "docker exec -it anguyenh-s555 bash" "docker compose exec svc ls"; do
  warn "$c" "-u \$(id -u)"
done
for c in "docker exec -u 1000 c ls" "docker exec --user=1000 c ls" "docker exec -u1000 c ls" \
  "docker exec -it -u \$(id -u) c bash" "docker ps" "docker exec c ls # shell-guard: allow docker-user"; do
  quiet "$c"
done
echo "ok docker-user"

# --- gh-login
W="$T/repos/work" F="$T/repos/fork" O="$T/repos/other" P="$T/repos/plain" L="$T/repos/gitlab"
warn "gh pr view 3" fixture-work "$W"
warn "gh pr view 3" gh-as.sh "$W"
warn "gh api repos/x/y" fixture-fork "$F"
warn "gh pr view 3 -R Acme-Internal/tool" fixture-work "$P"
quiet "GH_TOKEN=\$(gh auth token -u fixture-work) gh pr view 3" "$W"
quiet "gh pr view 3" "$O"
quiet "gh pr view 3" "$L"
quiet "gh pr view 3" "$P"
quiet "gh auth status" "$W"
quiet "$GA -C x -- pr view 3" "$W"
quiet "gh pr view 3 # shell-guard: allow gh-login" "$W"
echo "ok gh-login"

# --- login
[ "$(python3 "$G" login "$W")" = fixture-work ] || fail "login for the work repo"
[ "$(python3 "$G" login "$F")" = fixture-fork ] || fail "login for the fork repo"
rc=0; python3 "$G" login "$O" >/dev/null 2>&1 || rc=$?; [ "$rc" = 3 ] || fail "login with no row: exit $rc, want 3"
rc=0; python3 "$G" login "$L" >/dev/null 2>&1 || rc=$?; [ "$rc" = 3 ] || fail "login on an MCP-only row: exit $rc, want 3"
echo "ok login"

# --- combined
expect deny "docker exec c ls; sleep 40"
expect deny "pkill -f x; docker exec c ls"
says "pkill -f x; docker exec c ls" | grep -q "allow docker-user" || fail "combined verdict drops a message"
echo "ok combined"

# --- fail-open
for bad in "garbage" "[1,2]" '{"command": 5}' ""; do
  out=$(echo "$bad" | python3 "$G" hook) || fail "hook exited non-zero on: $bad"
  [ "$out" = '{"permission": "allow"}' ] || fail "hook did not fail open on: $bad: $out"
done
echo "ok fail-open"

# --- ask
python3 - "$G" <<'EOF' || fail "ask action is not enforced"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("sg", sys.argv[1])
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)
sg.RULES[:] = [sg.Rule("probe", sg.re.compile("probe"), "ask", "ask probe", None)]
assert sg.decide("probe", "")["permission"] == "ask"
EOF
echo "ok ask"

# --- hooks.json
hook_cmd=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["hooks"]["beforeShellExecution"][0]["command"])' "$ROOT/hooks/hooks.json") \
  || fail "hooks.json has no beforeShellExecution entry"
out=$(cd /tmp && echo '{"command":"sleep 120","cwd":"/"}' | CURSOR_PLUGIN_ROOT="$ROOT" sh -c "$hook_cmd")
echo "$out" | python3 -c 'import json,sys; assert json.load(sys.stdin)["permission"] == "deny"' \
  || fail "beforeShellExecution hook is not wired to shell-guard.py"
echo "ok hooks.json"

# --- gh-as
cat > "$T/bin/gh" <<'EOF'
#!/usr/bin/env bash
if [ "$1 $2" = "auth token" ]; then
  case "$4" in
    fixture-work) echo tok-fixture-work ;;
    fixture-fork) echo tok-fixture-fork ;;
    fixture-empty) ;;
    *) echo "no account $4" >&2; exit 1 ;;
  esac
  exit 0
fi
echo "token=$GH_TOKEN args=$*"
EOF
chmod +x "$T/bin/gh"
export PATH="$T/bin:$PATH"
[ "$("$GA" -C "$W" -- pr view 3)" = "token=tok-fixture-work args=pr view 3" ] || fail "gh-as did not pass the work login's token"
[ "$("$GA" -C "$F" -- api user)" = "token=tok-fixture-fork args=api user" ] || fail "gh-as did not pass the fork login's token"
rc=0; "$GA" -C "$O" -- pr view 3 >/dev/null 2>&1 || rc=$?; [ "$rc" = 3 ] || fail "gh-as with no login row: exit $rc, want 3"
rc=0; "$GA" -C "$T/repos/empty" -- pr view 3 >/dev/null 2>&1 || rc=$?; [ "$rc" = 4 ] || fail "gh-as with an empty token: exit $rc, want 4"
rc=0; "$GA" -C "$W" pr view 3 >/dev/null 2>&1 || rc=$?; [ "$rc" = 2 ] || fail "gh-as without -- : exit $rc, want 2"
rc=0; "$GA" -C "$W" -- >/dev/null 2>&1 || rc=$?; [ "$rc" = 2 ] || fail "gh-as with no gh args: exit $rc, want 2"
echo "ok gh-as"

echo "ok shell-guard"
