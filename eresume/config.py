"""路径与配置：数据目录、LLM 连接、代理设置。"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "eresume"


def data_dir(create: bool = False) -> Path:
    """数据目录：默认 ~/.eresume，可用 ERESUME_DIR 覆盖（便于项目内演示）。
    create=False 时不创建目录（纯查询场景，如 config 命令）。"""
    override = os.environ.get("ERESUME_DIR", "").strip()
    if override:
        p = Path(override).expanduser()
    else:
        p = Path.home() / f".{APP_DIR_NAME}"
    if create:
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

# 市面常见厂商预设。绝大多数厂商提供 OpenAI 兼容端点（chat/completions），
# 因此同一套客户端即可接入；这里只是帮你免去记 base_url/模型名的麻烦。
# 用法：ERESUME_PROVIDER=deepseek，或 ERESUME_BASE_URL/ERESUME_MODEL 手动指定（优先）。
PROVIDERS: dict[str, dict] = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "note": "OpenAI 官方"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "note": "DeepSeek（中文性价比高，官方兼容 OpenAI）"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "note": "阿里通义千问（DashScope 兼容模式）"},
    "kimi": {"base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k", "note": "月之暗面 Kimi"},
    "zhipu": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash", "note": "智谱 GLM（有免费额度）"},
    "minimax": {"base_url": "https://api.minimax.chat/v1", "model": "abab6.5s-chat", "note": "MiniMax"},
    "hunyuan": {"base_url": "https://api.hunyuan.cloud.tencent.com/v1", "model": "hunyuan-lite", "note": "腾讯混元（OpenAI 兼容模式）"},
    "ernie": {"base_url": "https://qianfan.baidubce.com/v2", "model": "ernie-3.5-8k", "note": "百度千帆（v2 OpenAI 兼容）"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b", "note": "本地 Ollama（免费，需本地安装）"},
    "vllm": {"base_url": "http://localhost:8000/v1", "model": "Qwen/Qwen2.5-7B-Instruct", "note": "本地 vLLM"},
}


def provider_preset(name: str) -> dict | None:
    """按名称取厂商预设；找不到返回 None。"""
    key = name.strip().lower()
    if key in PROVIDERS:
        return dict(PROVIDERS[key])
    # 别名
    alias = {"通义": "qwen", "千问": "qwen", "dashscope": "qwen", "moonshot": "kimi",
             "glm": "zhipu", "智谱": "zhipu", "混元": "hunyuan", "文心": "ernie",
             "千帆": "ernie", "星火": "spark", "spark": "spark"}
    k = alias.get(key)
    if k and k in PROVIDERS:
        return dict(PROVIDERS[k])
    return None


def llm_config() -> dict:
    """解析 LLM 配置：显式环境变量优先，其次厂商预设。"""
    provider = os.environ.get("ERESUME_PROVIDER", "").strip()
    preset = provider_preset(provider) if provider else None
    base_url = os.environ.get("ERESUME_BASE_URL", "").strip() or (preset["base_url"] if preset else "https://api.openai.com/v1")
    model = os.environ.get("ERESUME_MODEL", "").strip() or (preset["model"] if preset else "gpt-4o-mini")
    return {
        "api_key": os.environ.get("ERESUME_API_KEY", "").strip(),
        "base_url": base_url.rstrip("/"),
        "model": model,
        "provider": provider or "openai(默认)",
        "note": preset["note"] if preset else "",
    }


def proxy_config() -> dict:
    """代理：优先 HTTPS_PROXY/HTTP_PROXY/ALL_PROXY 环境变量。"""
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        v = os.environ.get(key, "").strip()
        if v:
            return {"url": v}
    return {}
