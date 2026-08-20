"""可选 LLM 能力：OpenAI 兼容 Chat Completions（纯标准库）。

无 API Key 时使用提示词模式：打印结构化提示词，用户可粘贴到任意 AI 对话中。
配置：
  ERESUME_API_KEY    API Key（必填才会走 LLM）
  ERESUME_BASE_URL   接口地址，默认 https://api.openai.com/v1（可接 DeepSeek/通义/本地 Ollama 等）
  ERESUME_MODEL      模型名，默认 gpt-4o-mini
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

from .config import llm_config, proxy_config


def available() -> bool:
    return bool(llm_config()["api_key"])


def chat(prompt: str, system: str = "", temperature: float = 0.6, max_tokens: int = 4096) -> str:
    """调用 Chat Completions；失败抛出带原因的异常。"""
    cfg = llm_config()
    if not cfg["api_key"]:
        raise RuntimeError("未配置 ERESUME_API_KEY")

    body = {
        "model": cfg["model"],
        "messages": [],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        body["messages"].append({"role": "system", "content": system})
    body["messages"].append({"role": "user", "content": prompt})

    url = f"{cfg['base_url']}/chat/completions"
    data = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }

    opener = urllib.request.build_opener()
    proxy = proxy_config()
    if proxy:
        from urllib.request import ProxyHandler
        opener = urllib.request.build_opener(ProxyHandler({"https": proxy["url"], "http": proxy["url"]}))

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with opener.open(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise RuntimeError(f"LLM 接口返回 {e.code}: {detail}") from e
    except Exception as e:
        raise RuntimeError(f"LLM 请求失败: {e}") from e

    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"LLM 返回格式异常: {str(payload)[:300]}") from e


def run(prompt: str, system: str = "", mode: str = "auto", fallback: str = "") -> str:
    """统一入口：auto = 有 key 走 LLM，无 key 走提示词模式。"""
    if mode == "llm":
        return chat(prompt, system)
    if mode == "prompt":
        return fallback
    # auto
    if available():
        try:
            return chat(prompt, system)
        except Exception as e:
            return f"[LLM 调用失败，已回退到提示词模式: {e}]\n\n{fallback}"
    return fallback


def prompt_banner(title: str) -> str:
    """提示词模式的包装说明。"""
    return (
        f"\n════════ {title}（提示词模式）════════\n"
        "未配置 ERESUME_API_KEY，以下为可直接粘贴到任意 AI 对话（Claude/ChatGPT/DeepSeek）的提示词。\n"
        "配置 LLM 后（export ERESUME_API_KEY=...），本命令将直接输出 AI 结果。\n"
        "════════════════════════════════════════\n"
    )
