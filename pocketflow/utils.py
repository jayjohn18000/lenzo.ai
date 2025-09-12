# pocketflow/utils.py
import subprocess, os, re, sys
from typing import Tuple


def run(cmd: str, cwd: str = None, check: bool = True) -> Tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {cmd}\n{err}")
    return proc.returncode, out, err


def replace_in_file(
    path: str, pattern: str, repl: str, flags=re.MULTILINE | re.DOTALL
) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    new = re.sub(pattern, repl, content, flags=flags)
    if new != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    return False


def ensure_import(path: str, import_line: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if import_line not in content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(import_line + "\n" + content)
        return True
    return False


def ensure_text_block(path: str, marker: str, block: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if marker in content:
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\n" + block + "\n")
    return True


def file_exists(path: str) -> bool:
    return os.path.exists(path)
