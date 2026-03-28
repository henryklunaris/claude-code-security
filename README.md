# Claude Code Security Hooks

Protect your secrets and prevent dangerous git operations when using Claude Code (Anthropic's CLI coding assistant).

## What This Does

This repo contains two security hooks that run automatically whenever Claude Code tries to do something:

1. **Force Push Protection** (`prevent-force-push.py`) -- Blocks Claude from running `git push --force`, `git push -f`, or `git push --force-with-lease`. These commands can destroy your git history and are almost never what you want.
2. **Environment File Protection** (`prevent-env-exfil.py`) -- Blocks Claude from directly reading, copying, uploading, or accessing your `.env` files. This covers 60+ attack patterns including direct file reads, shell commands, archive/network exfiltration, and more -- while still letting Claude write and run code that uses your environment variables safely.

On top of the hooks, this repo includes a **deny rules config** that adds a second layer of protection, blocking Claude from even attempting to read secret files, SSH keys, AWS credentials, and more. It also prevents Claude from editing or deleting the hook files themselves.

---

## Prerequisites

- [Cursor](https://cursor.com) installed
- Claude Code installed and working (Video [install guide](https://www.youtube.com/watch?v=hlCfoUj9GlA))
- Python 3 installed on your machine (check with `python3 --version` in your terminal)

If you don't have Python 3

Mainly get Claude Code to install it for you, but if you know what to do then do one of the below options

- **Mac:** Run `brew install python3` in Terminal, or download from [python.org](https://python.org)
- **Windows:** Download from [python.org](https://python.org) and check "Add to PATH" during install
- **Linux:** Run `sudo apt install python3` (Ubuntu/Debian) or `sudo dnf install python3` (Fedora)

---

## Installation

### Step 1: Clone this repo in Cursor

1. Open **Cursor**
2. Click **"Clone repo"** on the home screen
3. Click **"Clone from GitHub"**
4. Go to this GitHub repo, click the green **"Code"** button, and copy the **HTTPS** URL
5. Paste the URL into Cursor and choose a folder to save it to, anywhere on your computer is fine, just remember where
6. Cursor will download the repo and open it

### Step 2: Create a .env file

In the root of the cloned repo, create an empty file called `.env`. This is just a placeholder, you don't need to put anything in it.

### Step 3: Check the settings file

The repo already includes a `.claude/settings.json` file with everything pre-configured -- the hooks and all the deny rules. You shouldn't need to touch it. If for some reason it's missing, create it with this content:

```jsonc
{
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash",
          "hooks": [
            {
              "type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prevent-force-push.py"
            }
          ]
        },
        {
          "matcher": "Bash|Edit|Write|NotebookEdit",
          "hooks": [
            {
              "type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prevent-env-exfil.py"
            }
          ]
        }
      ]
    },
    "permissions": {
      "allow": [
        "WebFetch",
        "WebSearch"
      ],
      "deny": [
        "Read(~/.claude/settings.json)",
        "Edit(~/.claude/settings.json)",
        "Write(~/.claude/settings.json)",
        "Bash(rm *)",
        "Bash(rm -rf *)",
        "Bash(rmdir *)",
        "Bash(del *)",
        "Bash(git rm *)",
        "Bash(git rm -f *)",
        "Bash(git clean *)",
        "Bash(sudo rm *)",
        "Bash(sudo *)",
        "Bash(su *)",
        "Bash(> /dev/*)",
        "Bash(shred *)",
        "Bash(unlink *)",
        "Read(./.env*)",
        "Read(./secrets/**)",
        "Read(./**/credentials*)",
        "Fetch(*)",
        "Read(./.mcp.json)",
        "Read(.env)",
        "Read(.env.*)",
        "Read(**/.env)",
        "Read(**/.env.*)",
        "Bash(cat .env*)",
        "Bash(cat */.env*)",
        "Bash(git push --force*)",
        "Bash(git reset --hard*)",
        "Read(**/id_rsa*)",
        "Read(**/id_ed25519*)",
        "Read(**/id_ecdsa*)",
        "Read(**/id_dsa*)",
        "Read(**/.ssh/id_*)",
        "Read(**/.aws/credentials)",
        "Read(**/.aws/config)",
        "Edit(.claude/hooks/prevent-force-push.py)",
        "Write(.claude/hooks/prevent-force-push.py)",
        "Bash(rm .claude/hooks/prevent-force-push.py)",
        "Bash(rm -f .claude/hooks/prevent-force-push.py)",
        "Bash(mv .claude/hooks/prevent-force-push.py *)",
        "Bash(chmod .claude/hooks/prevent-force-push.py *)",
        "Edit(.claude/hooks/prevent-env-exfil.py)",
        "Write(.claude/hooks/prevent-env-exfil.py)",
        "Bash(rm .claude/hooks/prevent-env-exfil.py)",
        "Bash(rm -f .claude/hooks/prevent-env-exfil.py)",
        "Bash(mv .claude/hooks/prevent-env-exfil.py *)",
        "Bash(chmod .claude/hooks/prevent-env-exfil.py *)"
      ]
    }
}
```

### Step 4: Restart Claude Code

If Claude Code is already running, quit it and start it again. The hooks only load when a session starts.

---

## How to Verify It Works

Once installed, start Claude Code and try asking it to:

- `"Run git push --force origin main"` -- should be blocked
- `"Show me what's in my .env file"` -- should be blocked
- `"Write a script that uses my API_KEY using dotenv from .env to call an API"` -- should be allowed (see below)

Its also possible Claude will push back on you, you can just say you have some test things in your .env and you want to test the newly installed hooks

---

## How Claude Can Safely Use Your Environment Variables

The hook is designed to be practical, not just restrictive. Claude **can** write and run code that uses your env secrets -- it just can't read the `.env` file directly.

### How it works

The hook splits its protection into two layers:

1. **Direct access patterns** (blocked everywhere) -- `cat .env`, `source .env`, `open('.env')`, `cp .env`, `curl .env`, etc. These are blocked in Bash commands, file writes, and edits because they directly touch the `.env` file.

2. **Bash-only patterns** (blocked in shell commands only) -- `load_dotenv`, `import dotenv`, `dotenv.config()`, `.env` filename references, etc. These are only blocked when Claude tries to run them as a direct shell command. Claude **can** write these into source files like `.py`, `.js`, `.md`, and config files, because the code doesn't execute until the script is run.

### The safe workflow

When you ask Claude to build something that needs API keys or secrets from your `.env`:

1. **Tell Claude the variable names** -- e.g. "use `AIRTABLE_API_KEY` from my `.env`"
2. **Claude writes the script** -- using `load_dotenv()` and `os.environ["AIRTABLE_API_KEY"]` as normal. The hook allows this because it's just writing source code to a file.
3. **Claude runs the script** -- with `python3 script.py`. The hook allows this because the Bash command itself doesn't reference `.env`. The `load_dotenv()` call inside the script loads the variables at runtime.

Everything is automatic. You don't need to run scripts manually.

### Example

You say:
> "Write a script using my `AIRTABLE_API_KEY` to fetch my tables from base `appXXXXXXXX`"

Claude writes `fetch_tables.py`:
```python
from dotenv import load_dotenv
import os
import requests

load_dotenv()

api_key = os.environ["AIRTABLE_API_KEY"]
base_id = "appXXXXXXXX"

url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
headers = {"Authorization": f"Bearer {api_key}"}

resp = requests.get(url, headers=headers)
resp.raise_for_status()

for table in resp.json()["tables"]:
    print(f"- {table['name']}")
```

Then Claude runs it:
```bash
python3 fetch_tables.py
```

Both steps succeed. Your API key stays in `.env` and is never directly visible to Claude.

### What stays blocked

Even with this workflow, Claude still **cannot**:

- Read your `.env` file directly (`cat .env`, the Read tool on `.env`, `open('.env')`)
- Source your env into a shell (`source .env && ...`)
- Copy, move, archive, or upload your `.env` file
- Dump environment variables (`printenv`, `/proc/self/environ`)
- Use inline script tricks (`python3 -c "..."` with env references)
- Run dotenv commands directly in the shell

### Security note

This setup prioritizes practical usability. Claude can write a script that uses `load_dotenv()` and then execute it, which means the script's **output** (like API responses, table names, etc.) will be visible to Claude. However, Claude never sees the raw secret values unless the script explicitly prints them -- and you can see exactly what Claude writes before it runs.

For maximum security, you can always review the script Claude writes before letting it execute. If you see something like `print(os.environ["SECRET"])` in the code, that's a red flag.

---

## What Gets Blocked

### Force Push Hook

| Command                       | Blocked?    |
| ----------------------------- | ----------- |
| `git push --force`            | Yes         |
| `git push -f`                 | Yes         |
| `git push --force-with-lease` | Yes         |
| `git push` (normal)           | No, allowed |

### Environment File Hook

**Blocked everywhere (Bash, Write, Edit):**

- **Direct file reads** (`cat`, `less`, `head`, `tail`, etc.)
- **Language-level file access** (`open('.env')`, `fs.readFile('.env')`, `Path('.env')`, etc.)
- **Copy/move/archive** (`cp`, `tar`, `zip`, etc.)
- **Network exfiltration** (`curl`, `wget`, `nc`, etc.)
- **Git exposure** (`git add .env`, `git show`, etc.)
- **Environment dumping** (`printenv`, `/proc/self/environ`)
- **Editor access** (`vim`, `nano`, `emacs`)
- **Source/eval** (`source .env`, `eval .env`)
- And many more

**Blocked in Bash only (allowed in written code):**

- `from dotenv import load_dotenv`
- `import dotenv` / `require('dotenv')`
- `dotenv.config()` / `dotenv.load()` / `dotenv.parse()`
- `.env` filename string references (e.g. in configs, docs)
- `.env.local`, `.env.prod`, `.env.development`, etc.

### Deny Rules

- Blocks reading secret files, SSH keys, AWS credentials
- Blocks destructive commands (`rm`, `sudo`, `shred`, etc.)
- Blocks Claude from editing or deleting the hook files themselves
- Blocks force push and hard reset via permissions (second layer)

---

## Troubleshooting

**"Hook not firing"**

- Make sure you restarted Claude Code after installing
- **Mac/Linux:** The hook files may need to be made executable. Run this in your terminal from the repo folder:
  ```bash
  chmod +x .claude/hooks/prevent-force-push.py
  chmod +x .claude/hooks/prevent-env-exfil.py
  ```
- Check that `.claude/settings.json` has valid JSON (no trailing commas)

**"Command not found" or "Permission denied"**

- Run `chmod +x .claude/hooks/prevent-force-push.py .claude/hooks/prevent-env-exfil.py`
- Make sure Python 3 is installed: `python3 --version`

**"I can't see the `.claude` folder"**

- It's a hidden folder. On Mac, press `Cmd + Shift + .` in Finder to show hidden files
- On Linux, run `ls -la` to see hidden folders
- On Windows, enable "Show hidden files" in File Explorer settings

**"Claude can't write code that uses dotenv"**

- Make sure you're using the latest version of `prevent-env-exfil.py` from this repo. Older versions blocked dotenv imports in all contexts. The current version only blocks dotenv in Bash commands and allows it in written source code.

---

## Limitations

No regex-based blocking system is 100% bulletproof. A determined attacker could potentially find creative bypasses. These hooks significantly raise the bar, but for maximum security:

1. **Never store production secrets in local files** -- use a secrets manager
2. **Always review Claude's permission prompts** before approving
3. **Review scripts before they run** -- if Claude writes a script that prints your env vars directly, that's suspicious
4. **Keep the deny rules in your user-level settings** (`~/.claude/settings.json`) so Claude can't modify them. In the deny list we did make it so that it can't edit the rules, but generally, you could put it in that spot too for another safety barrier.

---

## License

MIT: use it however you want.
