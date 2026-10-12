#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import tempfile

RULE = "Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked."
LANES = re.compile(r"Ten lanes on `[^`<>]+` at the PR head")
SUB_BLOCKS = [
    "Depends on.",
    "Files.",
    "Build.",
    "You see.",
    "Verify, unit.",
    "Verify, live.",
    "Verify, perf.",
    "Review gate.",
    "Merge.",
]
PROGRAM_H3 = ["Arm the program", "Spawn owners", "PR mechanics", "Verdict and merge", "Boot recipe"]
PROGRAM_MARKERS = ["git show origin/main:", "/loop 1h", "status message"]
HOW_TO_READ_MARKERS = [
    "One box is one unit of work",
    "names the evidence",
    "Check a box only when its evidence exists",
    "playbooks/",
    RULE,
]
PERF_ITEMS = ["Metric.", "Probe.", "Baseline.", "Rule."]
BOX = re.compile(r"^\s*- \[[ x]\] ([^\n\r\u2028\u2029]*)$")
EOL = "\n\r\u2028\u2029"


def opening_fence(text):
    m = re.match(r"^ {0,3}(`{3,}|~{3,})([^" + EOL + r"]*)$", text)
    if not m or (m.group(1)[0] == "`" and "`" in m.group(2)):
        return None
    return (m.group(1)[0], len(m.group(1)))


def closing_fence(text, opening):
    m = re.match(r"^ {0,3}(`+|~+)[ \t]*$", text)
    return bool(m and m.group(1)[0] == opening[0] and len(m.group(1)) >= opening[1])


def check(file):
    with open(file, encoding="utf-8") as fh:
        raw = re.split(r"\r?\n", fh.read())
    problems = []

    def fail(line, message):
        problems.append(f"{file}:{line}: {message}")

    start = 0
    if raw[0] == "---":
        try:
            start = raw.index("---", 1) + 1
        except ValueError:
            start = 0

    lines = []
    fence = None
    for i in range(start, len(raw)):
        text = raw[i]
        n = i + 1
        code = fence is not None
        if fence is not None and closing_fence(text, fence):
            code = False
            fence = None
        elif fence is None:
            fence = opening_fence(text)
            code = fence is not None
        lines.append({"n": n, "text": text, "code": code})
        if code:
            continue
        prose = re.sub(r"`[^`]*`", "`", text)
        prose = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", prose)
        prose = re.sub(r"\]\([^)]*\)", "]", prose)
        if re.search("[\u2013\u2014]", prose):
            fail(n, "long dash")
        if re.search("[\u2018\u2019\u201c\u201d]", prose):
            fail(n, "curly quote")
        if re.search(r": \S", prose):
            fail(n, "mid-sentence colon")

    def h2(line):
        return line["text"][3:].strip() if not line["code"] and line["text"].startswith("## ") else None

    sections = []
    for line in lines:
        title = h2(line)
        if title is not None:
            sections.append({"title": title, "n": line["n"], "body": []})
        elif sections:
            sections[-1]["body"].append(line)

    def find(title):
        return next((s for s in sections if s["title"] == title), None)

    def body_text(section):
        return "\n".join(line["text"] for line in section["body"])

    def boxes(ls):
        out = []
        for line in ls:
            if line["code"]:
                continue
            m = BOX.match(line["text"])
            if m:
                out.append({"n": line["n"], "text": m.group(1)})
        return out

    h1 = next((i for i, line in enumerate(lines) if not line["code"] and line["text"].startswith("# ")), -1)
    if h1 == -1:
        fail(1, "no H1 title")
    how_to_read = find("How to read this")
    if not how_to_read:
        fail(1, 'no "## How to read this" section')
    if h1 != -1 and how_to_read:
        intro = [line for line in lines[h1 + 1:] if line["n"] < how_to_read["n"] and line["text"].strip() != ""]
        if len(intro) >= 10:
            fail(lines[h1]["n"], f"intro is {len(intro)} lines, under ten required")
        for marker in HOW_TO_READ_MARKERS:
            if marker not in body_text(how_to_read):
                fail(how_to_read["n"], f'How to read this lacks "{marker}"')

    program = find("Program checklist")
    if not program:
        fail(1, 'no "## Program checklist" section')
    else:
        h3s = [line["text"][4:].strip() for line in program["body"] if not line["code"] and line["text"].startswith("### ")]
        cursor = 0
        for name in PROGRAM_H3:
            at = next((i for i, t in enumerate(h3s) if i >= cursor and t.startswith(name)), -1)
            if at == -1:
                fail(program["n"], f'Program checklist lacks "### {name}" in order')
            else:
                cursor = at + 1
        for marker in PROGRAM_MARKERS:
            if marker not in body_text(program):
                fail(program["n"], f'Program checklist lacks "{marker}"')

    close = find("Close the program")
    if not close:
        fail(1, 'no "## Close the program" section')
    program_index = sections.index(program) if program else -1
    close_index = sections.index(close) if close else -1
    pr_sections = [] if program_index == -1 or close_index == -1 else sections[program_index + 1:close_index]
    if len(pr_sections) == 0:
        fail(1, "no PR sections between Program checklist and Close the program")

    report = []
    for pr in pr_sections:
        heads = []
        for line in pr["body"]:
            if line["code"]:
                continue
            m = re.match(r"^\*\*([^*]+)\*\*(.*)$", line["text"])
            if m and m.group(1) in SUB_BLOCKS:
                heads.append({"name": m.group(1), "n": line["n"], "rest": m.group(2).strip(), "lines": []})
            elif heads:
                heads[-1]["lines"].append(line)
        names = [h["name"] for h in heads]
        if "|".join(names) != "|".join(SUB_BLOCKS):
            fail(pr["n"], f"{pr['title']}: sub-blocks are [{', '.join(names)}], expected [{', '.join(SUB_BLOCKS)}]")

        def block(name):
            return next((h for h in heads if h["name"] == name), None)

        counts = {h["name"]: len(boxes(h["lines"])) for h in heads}

        depends = block("Depends on.")
        if depends and depends["rest"] == "":
            fail(depends["n"], f"{pr['title']}: Depends on names nothing")
        for name in ["Files.", "Build.", "You see.", "Verify, unit.", "Merge."]:
            b = block(name)
            if b and len(boxes(b["lines"])) == 0:
                fail(b["n"], f"{pr['title']}: {name} has no box")
        for name in ["Verify, unit.", "Verify, live.", "Verify, perf."]:
            b = block(name)
            if b and not b["rest"].startswith(RULE):
                fail(b["n"], f"{pr['title']}: {name} does not open with the rule")

        live = block("Verify, live.")
        if live:
            if not LANES.search(live["rest"]):
                fail(live["n"], f"{pr['title']}: Verify, live lacks \"Ten lanes on `<swarm workers model>` at the PR head\" with the model filled in")
            lanes = []
            for b in boxes(live["lines"]):
                lanes.append({**b, "m": re.match(r"^Lane (\d+)\. ", b["text"])})
            numbers = sorted(int(b["m"].group(1)) for b in lanes if b["m"])
            if ",".join(str(x) for x in numbers) != "1,2,3,4,5,6,7,8,9,10":
                fail(live["n"], f"{pr['title']}: lanes are [{','.join(str(x) for x in numbers)}], expected 1 to 10")
            for lane in lanes:
                if not lane["m"]:
                    fail(lane["n"], f"{pr['title']}: live box is not a lane")
                elif not re.search(r"Save `[^`]+`", lane["text"]):
                    fail(lane["n"], f"{pr['title']}: lane {lane['m'].group(1)} names no screenshot")
                elif "Pass when" not in lane["text"]:
                    fail(lane["n"], f"{pr['title']}: lane {lane['m'].group(1)} has no pass predicate")

        perf = block("Verify, perf.")
        if perf:
            items = [b["text"].split(" ")[0] for b in boxes(perf["lines"])]
            if "|".join(items) != "|".join(PERF_ITEMS):
                fail(perf["n"], f"{pr['title']}: perf boxes are [{', '.join(items)}], expected [{', '.join(PERF_ITEMS)}]")

        gate = block("Review gate.")
        if gate:
            gate_boxes = boxes(gate["lines"])
            if gate["rest"].startswith("None."):
                if gate_boxes:
                    fail(gate["n"], f"{pr['title']}: Review gate says None but has boxes")
            else:
                text = "\n".join(line["text"] for line in gate["lines"])
                if len(gate_boxes) == 0:
                    fail(gate["n"], f"{pr['title']}: Review gate has no box")
                for word in ["screenshot", "video", "operator"]:
                    if word not in text:
                        fail(gate["n"], f'{pr["title"]}: Review gate lacks "{word}"')

        total = len(boxes(pr["body"]))
        cells = [
            re.sub(r"-$", "", re.sub(r"[ ,.]+", "-", s)).lower() + "=" + str(counts.get(s, 0))
            for s in SUB_BLOCKS
            if s != "Depends on."
        ]
        report.append(f"{pr['title']}  boxes={total}  {' '.join(cells)}")

    if close_index != -1:
        tail = sections[close_index + 1:]
        for s in tail:
            if not s["title"].startswith("Appendix"):
                fail(s["n"], f'"## {s["title"]}" after Close the program is not an appendix')
        if not any("Prototype evidence" in s["title"] for s in tail):
            fail(close["n"], 'no "## Appendix ... Prototype evidence" section')

    return report, len(pr_sections), problems


VALID_PLAN = (
    "# Demo\n\n"
    "## How to read this\n"
    "One box is one unit of work and names the evidence. Check a box only when its evidence exists. See playbooks/.\n"
    + RULE
    + "\n\n"
    "## Program checklist\n"
    "### Arm the program\n"
    "### Spawn owners\n"
    "### PR mechanics\n"
    "### Verdict and merge\n"
    "### Boot recipe\n"
    "`git show origin/main:` /loop 1h status message\n\n"
    "## PR 1\n"
    "**Depends on.** None.\n"
    "**Files.**\n"
    "- [ ] Do the thing.\n"
    "**Build.**\n"
    "- [ ] Do the thing.\n"
    "**You see.**\n"
    "- [ ] Do the thing.\n"
    "**Verify, unit.** " + RULE + "\n"
    "- [ ] Check the thing.\n"
    "**Verify, live.** " + RULE + " Ten lanes on `example-model` at the PR head\n"
    + "\n".join(f"- [ ] Lane {i + 1}. Save `lane-{i + 1}.png`. Pass when evidence exists." for i in range(10))
    + "\n"
    "**Verify, perf.** " + RULE + "\n"
    "- [ ] Metric. Recorded.\n"
    "- [ ] Probe. Recorded.\n"
    "- [ ] Baseline. Recorded.\n"
    "- [ ] Rule. Recorded.\n"
    "**Review gate.** None.\n"
    "**Merge.**\n"
    "- [ ] Merge when approved.\n\n"
    "## Close the program\n"
    "Close.\n\n"
    "## Appendix Prototype evidence\n"
    "Recorded.\n"
)


def self_test():
    failures = []

    def run_plan(example, expected_exit):
        with tempfile.TemporaryDirectory(prefix="check-plan-test-") as directory:
            path = os.path.join(directory, "plan.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(VALID_PLAN + example)
            result = subprocess.run([sys.executable, os.path.abspath(__file__), path], capture_output=True, text=True)
        if result.returncode != expected_exit:
            failures.append(f"exit {result.returncode}, expected {expected_exit}, for {example!r}: {result.stderr.strip()}")
        return result

    def expect_in(result, needle, label):
        if needle not in result.stderr:
            failures.append(f"{label}: stderr lacks {needle!r}: {result.stderr.strip()}")

    cases = 0

    for indent in ["", " ", "  ", "   "]:
        run_plan(f"{indent}```markdown\n## Example only\n{indent}```\n", 0)
        cases += 1
    run_plan("```markdown\n## Example only\n````\n", 0)
    cases += 1

    run_plan("````markdown\n```markdown\n## Example only\n```\n````\n", 0)
    run_plan("~~~markdown `info`\n## Example only\n ~~~\n", 0)
    cases += 2

    run_plan("````markdown\n~~~\n## Example only\n````\n", 0)
    run_plan("````markdown\n```\n## Example only\n````\n", 0)
    run_plan("````markdown\n``` info\n## Example only\n````\n", 0)
    cases += 3

    for suffix in ["  ", "\t"]:
        heading = run_plan(f"```markdown\n## Example only\n```{suffix}\n## Example only\n", 1)
        expect_in(heading, '"## Example only" after Close the program is not an appendix', "heading")
        cases += 1
    prose = run_plan(
        "```markdown\nThis prose has a mid-sentence colon: inside code\n```\nThis prose has a mid-sentence colon: bad.\n",
        1,
    )
    expect_in(prose, "mid-sentence colon", "prose")
    cases += 1

    result = run_plan("```markdown `invalid`\n## Example only\n```\n", 1)
    expect_in(result, '"## Example only" after Close the program is not an appendix', "info string")
    cases += 1

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    print(f"{cases} cases, {len(failures)} failures")
    return 1 if failures else 0


def main(argv):
    if len(argv) > 1 and argv[1] == "--self-test":
        return self_test()
    if len(argv) < 2:
        print("Usage: python3 check_plan.py <plan.md> | --self-test", file=sys.stderr)
        return 2
    report, count, problems = check(argv[1])
    for line in report:
        print(line)
    print(f"{count} PR sections, {len(problems)} problems")
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
