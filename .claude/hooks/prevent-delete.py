#!/usr/bin/env python3
"""
PreToolUse hook to prevent file deletion.
This hook blocks:
- rm, rmdir, unlink, shred
- find ... -delete / -exec rm
- git clean, git rm
Exit codes:
- 0: Allow the command to proceed
- 2: Block the command and show error message to Claude
"""

import json
import sys
import re

def main():
    # Read the PreToolUse input from stdin
    input_data = json.load(sys.stdin)

    # Extract tool information
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check Bash tool commands
    if tool_name != "Bash":
        sys.exit(0)

    # Check for delete patterns
    delete_patterns = [
        r'(^|[;&|(`\s])(sudo\s+)?(rm|rmdir|unlink|shred)\b',
        r'\bfind\b.*\s-delete\b',
        r'\bfind\b.*-exec\s+(rm|unlink)\b',
        r'\bgit\s+(clean|rm)\b'
    ]

    for pattern in delete_patterns:
        if re.search(pattern, command):
            print("🗑️ Blocked: deleting files is not allowed.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Please ask the user to delete files themselves.", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
