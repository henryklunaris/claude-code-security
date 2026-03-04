#!/usr/bin/env python3
"""
PreToolUse hook to prevent writing or running code that reads .env files.
Blocks attempts to exfiltrate .env contents through scripts or commands.
Exit codes:
- 0: Allow the action
- 2: Block the action
"""

import json
import sys
import re

# Patterns that indicate reading .env file contents
ENV_READ_PATTERNS = [
      # === Language-level file reads ===
      r"""open\s*\(\s*['"]\.env""",
      r"""readFile.*['"]\.env""",
      r"""readFileSync.*['"]\.env""",
      r"""fs\.read.*['"]\.env""",
      r"""load_dotenv""",
      r"""dotenv\.config""",
      r"""dotenv\.load""",
      r"""dotenv\.parse""",
      r"""require\s*\(\s*['"]dotenv""",
      r"""import.*dotenv""",
      r"""from\s+dotenv""",
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

      # === Filename via variable / env variants ===
      r"""['"]\.env['"]""",
      r"""\.env\.local""",
      r"""\.env\.prod""",
      r"""\.env\.dev""",
      r"""\.env\.staging""",
      r"""\.env\.production""",
      r"""\.env\.development""",
  ]


def check_text(text):
    """Check if text contains patterns that read .env files."""
    for pattern in ENV_READ_PATTERNS:
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
    else:
        sys.exit(0)

    match = check_text(text_to_check)
    if match:
        print("🔒 Blocked: code that reads .env files is not allowed.", file=sys.stderr)
        print("", file=sys.stderr)
        print("This hook prevents writing or running code that accesses", file=sys.stderr)
        print(".env or .env.local files to protect secrets from exposure.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
