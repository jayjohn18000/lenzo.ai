
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

## Uvicorn (FastAPI/ASGI Server)

### Run app with reload (development)
```bash
python -m uvicorn backend.main:app --reload
```

### Specify host and port
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run with workers (production-style)
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Docker Commands

### Build Docker Image
```bash
docker build -t myapp:latest .
```

### Run Container
```bash
docker run -d -p 8000:8000 myapp:latest
```

### List Running Containers
```bash
docker ps
```

### Stop Container
```bash
docker stop <container_id>
```

### Remove Container
```bash
docker rm <container_id>
```

### Remove Image
```bash
docker rmi <image_id>
```

### View Logs
```bash
docker logs -f <container_id>
```

### Exec into Running Container
```bash
docker exec -it <container_id> /bin/bash
```

### Clean up unused resources
```bash
docker system prune -af
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
