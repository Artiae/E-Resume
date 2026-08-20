"""本地 JSON 存储：profile / preferences / postings / applications。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from .config import data_dir
from .models import Profile, Preferences, Posting, Application

FILES = ("profile.json", "preferences.json", "postings.json", "applications.json")


def _path(name: str) -> Path:
    return data_dir() / name


def _read_json(name: str, default: Any) -> Any:
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(name: str, obj: Any) -> None:
    p = _path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


# ---- Profile ----

def load_profile() -> Profile:
    return Profile.from_dict(_read_json("profile.json", {}))


def save_profile(profile: Profile) -> None:
    _write_json("profile.json", profile.to_dict())


# ---- Preferences ----

def load_preferences() -> Preferences:
    return Preferences.from_dict(_read_json("preferences.json", {}))


def save_preferences(prefs: Preferences) -> None:
    _write_json("preferences.json", prefs.to_dict())


# ---- Postings ----

def list_postings() -> list[Posting]:
    raw = _read_json("postings.json", [])
    return [Posting.from_dict(x) for x in raw if isinstance(x, dict)]


def get_posting(posting_id: str) -> Optional[Posting]:
    for p in list_postings():
        if p.id == posting_id:
            return p
    return None


def save_postings(postings: list[Posting]) -> None:
    _write_json("postings.json", [p.to_dict() for p in postings])


def upsert_posting(posting: Posting) -> bool:
    """新增或更新岗位；返回是否新增。"""
    postings = list_postings()
    for i, p in enumerate(postings):
        if p.id == posting.id:
            postings[i] = posting
            save_postings(postings)
            return False
    postings.append(posting)
    save_postings(postings)
    return True


# ---- Applications ----

def list_applications() -> list[Application]:
    raw = _read_json("applications.json", [])
    return [Application.from_dict(x) for x in raw if isinstance(x, dict)]


def save_applications(apps: list[Application]) -> None:
    _write_json("applications.json", [a.to_dict() for a in apps])


def upsert_application(app: Application) -> bool:
    apps = list_applications()
    for i, a in enumerate(apps):
        if a.id == app.id:
            apps[i] = app
            save_applications(apps)
            return False
    apps.append(app)
    save_applications(apps)
    return True


def init_workspace() -> None:
    """初始化数据目录与空文件。"""
    d = data_dir()
    (d / "templates").mkdir(parents=True, exist_ok=True)
    for name in FILES:
        p = _path(name)
        if not p.exists():
            _write_json(name, {} if name in ("profile.json", "preferences.json") else [])
    print(f"[E-Resume] 数据目录已就绪: {d}")
