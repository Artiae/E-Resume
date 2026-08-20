"""路径与配置：数据目录、LLM 连接、代理设置。"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "eresume"


def data_dir() -> Path:
    """数据目录：默认 ~/.eresume，可用 ERESUME_DIR 覆盖（便于项目内演示）。"""
    override = os.environ.get("ERESUME_DIR", "").strip()
    if override:
        p = Path(override).expanduser()
    else:
        p = Path.home() / f".{APP_DIR_NAME}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def repo_root() -> Path:
    """仓库根目录（用于定位模板、提示词、渠道数据）。"""
    return Path(__file__).resolve().parent.parent


def resolve_template(name: str) -> Path:
    """先在用户数据目录找，再回退到仓库模板目录。"""
    user = data_dir() / "templates" / name
    if user.exists():
        return user
    return repo_root() / "templates" / name


def resolve_prompt(name: str) -> Path:
    return repo_root() / "eresume" / "prompts" / name


def resolve_channels_data() -> Path:
    return repo_root() / "data" / "channels.json"


# ---- LLM 配置（OpenAI 兼容） ----

def llm_config() -> dict:
    return {
        "api_key": os.environ.get("ERESUME_API_KEY", "").strip(),
        "base_url": os.environ.get("ERESUME_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        "model": os.environ.get("ERESUME_MODEL", "gpt-4o-mini").strip(),
    }


def proxy_config() -> dict:
    """代理：优先 HTTPS_PROXY/HTTP_PROXY/ALL_PROXY 环境变量。"""
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        v = os.environ.get(key, "").strip()
        if v:
            return {"url": v}
    return {}
