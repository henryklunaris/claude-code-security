#!/usr/bin/env python3
"""
PreToolUse hook to prevent direct access to .env files.
Blocks attempts to exfiltrate .env contents through commands or direct file reads.
ALLOWS writing source code that uses dotenv libraries (the code itself doesn't
leak secrets -- it only reads them at runtime when the user executes it).
Exit codes:
- 0: Allow the action
- 2: Block the action
"""

import json
import sys
import re

# -----------------------------------------------------------------------
# DIRECT ACCESS patterns -- blocked in ALL contexts (Bash, Write, Edit).
# These open/read the .env file directly, which could leak secrets.
# -----------------------------------------------------------------------
DIRECT_ACCESS_PATTERNS = [
      # === Language-level direct file reads of .env ===
      r"""open\s*\(\s*['"]\.env""",
      r"""readFile.*['"]\.env""",
      r"""readFileSync.*['"]\.env""",
      r"""fs\.read.*['"]\.env""",
      r"""pathlib.*\.env""",
      r"""Path\s*\(\s*['"]\.env""",

      # === Shell commands that read files ===
      r"""\bcat\s+.*\.env""",
      r"""\bless\s+.*\.env""",
      r"""\bmore\s+.*\.env""",
      r"""\bhead\s+.*\.env""",
      r"""\btail\s+.*\.env""",
      r"""\bgrep\s+.*\.env""",
      r"""\bawk\s+.*\.env""",
      r"""\bsed\s+.*\.env""",
      r"""\bsort\s+.*\.env""",
      r"""\bstrings\s+.*\.env""",
      r"""\bxxd\s+.*\.env""",
      r"""\bbase64\s+.*\.env""",
      r"""\bdd\s+.*if=.*\.env""",
      r"""\btee\s+.*\.env""",
      r"""<\s*\.env""",

      # === Editors ===
      r"""\bvim?\s+.*\.env""",
      r"""\bnano\s+.*\.env""",
      r"""\bemacs\s+.*\.env""",

      # === Source / eval ===
      r"""\bsource\s+.*\.env""",
      r"""\.\s+\.env""",
      r"""\beval\s+.*\.env""",

      # === Inline script tricks ===
      r"""python[23]?\s+-c\s+.*env""",
      r"""node\s+-e\s+.*env""",
      r"""ruby\s+-e\s+.*env""",
      r"""perl\s+-e\s+.*env""",
      r"""php\s+-r\s+.*env""",
      r"""\bpython.*['"]\.env""",
      r"""\bnode.*['"]\.env""",
      r"""\bruby.*['"]\.env""",
      r"""\bperl.*['"]\.env""",
      r"""\bphp.*['"]\.env""",

      # === Copy / move / link ===
      r"""\bcp\s+.*\.env""",
      r"""\bmv\s+.*\.env""",
      r"""\bln\s+.*\.env""",
      r"""\brsync\s+.*\.env""",

      # === Archive / compress ===
      r"""\btar\s+.*\.env""",
      r"""\bzip\s+.*\.env""",
      r"""\bgzip\s+.*\.env""",

      # === Network exfiltration ===
      r"""curl.*\.env""",
      r"""wget.*\.env""",
      r"""\bnc\s+.*\.env""",
      r"""\bnetcat\s+.*\.env""",

      # === Find + exec patterns ===
      r"""\bfind\s+.*\.env""",
      r"""\bxargs\s+.*\.env""",
      r"""\blocate\s+.*\.env""",

      # === Git exposure ===
      r"""\bgit\s+add\s+.*\.env""",
      r"""\bgit\s+show.*\.env""",
      r"""\bgit\s+diff.*\.env""",

      # === Glob / wildcard tricks ===
      r"""\bcat\s+\.e\*""",
      r"""\bcat\s+\.en.""",
      r"""\bcat\s+\.\*env""",

      # === Environment dumping ===
      r"""\bprintenv\b""",
      r"""\b/proc/self/environ""",
      r"""\b/proc/.*/environ""",

  ]

# -----------------------------------------------------------------------
# BASH-ONLY patterns -- only blocked when run as shell commands.
# These are safe in written source code (scripts, docs, configs) because
# they don't execute until the user runs them. Includes dotenv library
# imports and .env filename references that appear in normal code/docs.
# -----------------------------------------------------------------------
BASH_ONLY_PATTERNS = [
      # === dotenv library usage ===
      r"""load_dotenv""",
      r"""dotenv\.config""",
      r"""dotenv\.load""",
      r"""dotenv\.parse""",
      r"""require\s*\(\s*['"]dotenv""",
      r"""import.*dotenv""",
      r"""from\s+dotenv""",

      # === .env filename references (common in docs, configs, code) ===
      r"""['"]\.env['"]""",
      r"""\.env\.local""",
      r"""\.env\.prod""",
      r"""\.env\.dev""",
      r"""\.env\.staging""",
      r"""\.env\.production""",
      r"""\.env\.development""",
  ]


def check_patterns(text, patterns):
    """Check if text matches any of the given patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


def main():
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    text_to_check = ""

    if tool_name == "Bash":
        text_to_check = tool_input.get("command", "")
    elif tool_name in ("Edit", "Write"):
        # Check both new content being written and the file path
        text_to_check = tool_input.get("content", "")
        text_to_check += "\n" + tool_input.get("new_string", "")
    elif tool_name == "NotebookEdit":
        text_to_check = tool_input.get("new_source", "")
    elif tool_name in ("Read", "Grep", "Glob"):
        text_to_check = json.dumps(tool_input)
    else:
        sys.exit(0)

    # Always check direct access patterns (all tools)
    match = check_patterns(text_to_check, DIRECT_ACCESS_PATTERNS)
    if match:
        print("🔒 Blocked: direct .env file access is not allowed.", file=sys.stderr)
        print("", file=sys.stderr)
        print("This hook prevents reading, copying, or directly accessing", file=sys.stderr)
        print(".env files to protect secrets from exposure.", file=sys.stderr)
        sys.exit(2)

    # Only check bash-only patterns for Bash (immediate execution)
    if tool_name == "Bash":
        match = check_patterns(text_to_check, BASH_ONLY_PATTERNS)
        if match:
            print("🔒 Blocked: running dotenv in a shell command is not allowed.", file=sys.stderr)
            print("", file=sys.stderr)
            print("You can write code that uses dotenv, but Claude cannot", file=sys.stderr)
            print("execute it directly. Run the script yourself with:", file=sys.stderr)
            print("  ! python3 your_script.py", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
