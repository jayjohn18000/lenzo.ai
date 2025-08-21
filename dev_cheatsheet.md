
# Developer Command Cheatsheet

## Python Virtual Environment (venv)

### Create venv
```bash
python3 -m venv .venv
```

### Activate venv
- macOS/Linux (bash/zsh):
```bash
source .venv/bin/activate
```
- Fish shell:
```bash
source .venv/bin/activate.fish
```
- Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```
- Windows (cmd):
```cmd
.venv\Scripts\activate.bat
```

### Deactivate venv
```bash
deactivate
```

---

## Git Commands

### Initial Setup
```bash
git init
git remote add origin <repo-url>
git branch -M main
```

### Check Repo Status
```bash
git status
git branch -vv
git remote -v
```

### Stage and Commit Changes
```bash
git add -A
git commit -m "your message"
```

### Push Changes
```bash
git push origin main
```

### Pull Changes (sync with remote)
```bash
git pull --rebase origin main
```

### Fix Non-Fast-Forward Push Error
```bash
git fetch origin
git pull --rebase origin main
# resolve conflicts if any
git push origin main
```

### Reset Local Branch to Remote (danger: discards local changes)
```bash
git fetch origin
git reset --hard origin/main
```

---

## Useful Helpers

### Show Commit History
```bash
git log --oneline --graph --decorate --all
```

### Show Tracked Files
```bash
git ls-files
```

### Show Ignored Files
```bash
git status --ignored
```

---

## VS Code Integration

- Open folder at project root: **File → Open Folder**
- Ensure Python interpreter is set to `.venv`:
  - `Ctrl+Shift+P` → "Python: Select Interpreter" → choose `.venv`

---

## Safety Backup Branch (before risky operations)
```bash
git switch -c backup/$(date +%Y%m%d-%H%M)
```
