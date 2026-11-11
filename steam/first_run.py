# SPDX-License-Identifier: MIT
"""Seed one compatibility fallback without reserializing Steam-owned settings."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile

TOKEN = re.compile(r'//[^\n]*|"(?:[^"\\]|\\.)*"|[{}]|[^\s{}"]+')

@dataclass
class Node:
    key: str
    children: list | None
    open: int | None
    close: int | None

def nodes(text):
    ts = [t for t in TOKEN.finditer(text) if not t[0].startswith('//')]
    i = 0
    def block():
        nonlocal i
        out = []
        while i < len(ts) and ts[i][0] != '}':
            key = ts[i][0].strip('"'); i += 1
            if i == len(ts): raise ValueError('Missing VDF value')
            value = ts[i][0]; i += 1
            if value == '{':
                start = ts[i - 1].end()
                children = block()
                if i == len(ts) or ts[i][0] != '}': raise ValueError('Unclosed VDF block')
                close = ts[i].start(); i += 1
            elif value == '}': raise ValueError('Unexpected VDF close')
            else: children, start, close = None, None, None
            out.append(Node(key, children, start, close))
        return out
    result = block()
    if i != len(ts): raise ValueError('Unexpected trailing VDF')
    return result

def seed_text(text, tool, priority, replaces=()):
    """Add a missing AppID 0 mapping to tool, and point mappings that name a
    tool in replaces (earlier names of the same tool) at tool."""
    for name in (tool, *replaces):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name): raise ValueError('Invalid tool name')
    if not isinstance(priority, int) or not 0 <= priority <= 1000: raise ValueError('Invalid priority')
    path = ['InstallConfigStore', 'Software', 'Valve', 'Steam', 'CompatToolMapping']
    if not text.strip(): text = '"InstallConfigStore"\n{\n}\n'
    for depth, key in enumerate(path):
        ns = nodes(text); parent = None
        for prior in path[:depth]:
            parent = next((n for n in ns if n.key.casefold() == prior.casefold()), None)
            if parent is None or parent.children is None: raise ValueError('Invalid settings path')
            ns = parent.children
        found = next((n for n in ns if n.key.casefold() == key.casefold()), None)
        if found is None:
            addition = f'\n"{key}"\n{{\n}}\n'
            where = len(text) if parent is None else parent.close
            text = text[:where] + addition + text[where:]
        elif found.children is None: raise ValueError('Settings path is a scalar')
    ns = nodes(text)
    for key in path:
        parent = next(n for n in ns if n.key.casefold() == key.casefold()); ns = parent.children
    renamed = False
    if replaces:
        old = '|'.join(map(re.escape, replaces))
        body, n = re.subn(r'("name"\s+)"(?:' + old + r')"', r'\1"' + tool + '"', text[parent.open:parent.close])
        if n:
            text = text[:parent.open] + body + text[parent.close:]
            renamed = True
            ns = nodes(text)
            for key in path:
                parent = next(n for n in ns if n.key.casefold() == key.casefold()); ns = parent.children
    if any(n.key == '0' for n in ns): return text, renamed
    addition = f'\n"0" {{ "name" "{tool}" "config" "" "priority" "{priority}" }}\n'
    return text[:parent.close] + addition + text[parent.close:], True

def seed_file(path: Path, tool: str, priority: int, replaces=()):
    # Caller holds the launcher lock and has checked that Steam is not running.
    if path.is_symlink(): raise ValueError('Refusing a symlinked config.vdf')
    old = path.read_text() if path.exists() else ''
    new, changed = seed_text(old, tool, priority, replaces)
    if not changed: return False
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, name = tempfile.mkstemp(prefix='.gravity-first-run-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as f:
            f.write(new); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
    return True
