"""Unified LLM adapter (Gemini 4 Hydrogen primary, Azure Foundry Claude/OpenAI-compat, zero-key resilience)."""

from __future__ import annotations

import base64
from collections import OrderedDict
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

_MAX_CACHE_ENTRIES = 64
_TEXT_RESPONSE_CACHE: OrderedDict[tuple[str, ...], dict[str, Any]] = OrderedDict()
_CACHE_LOCK = threading.Lock()


def clear_llm_cache() -> None:
    """Clear the bounded in-memory LLM response cache (useful for tests)."""
    with _CACHE_LOCK:
        _TEXT_RESPONSE_CACHE.clear()


@dataclass
class FoundryStatus:
    provider: str  # "gemini" | "anthropic" | "openai_compatible" | "deterministic"
    configured: bool
    model: str
    fast_model: str
    vision_model: str
    resource: str | None = None


def get_foundry_status() -> FoundryStatus:
    provider = (os.getenv("AZURE_FOUNDRY_PROVIDER") or os.getenv("AI_PROVIDER") or "").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen").strip()
    gemini_fast = os.getenv("GEMINI_FAST_MODEL", gemini_model).strip()
    gemini_vision = os.getenv("GEMINI_VISION_MODEL", gemini_model).strip()

    foundry_key = os.getenv("AZURE_FOUNDRY_API_KEY", "").strip()
    foundry_resource = os.getenv("AZURE_FOUNDRY_RESOURCE", "").strip()
    foundry_base = os.getenv("AZURE_FOUNDRY_BASE_URL", "").strip()
    az_openai_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    az_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()

    model = os.getenv("AZURE_FOUNDRY_MODEL", "claude-sonnet-5-5").strip()
    fast_model = os.getenv("AZURE_FOUNDRY_FAST_MODEL", "claude-haiku-5-5").strip()
    vision_model = os.getenv("AZURE_FOUNDRY_VISION_MODEL", model).strip()

    if gemini_key and provider in ("", "gemini"):
        return FoundryStatus(
            provider="gemini",
            configured=True,
            model=gemini_model,
            fast_model=gemini_fast,
            vision_model=gemini_vision,
            resource="generativelanguage.googleapis.com",
        )
    if provider in ("", "anthropic") and foundry_key and (foundry_resource or foundry_base):
        return FoundryStatus(
            provider="anthropic",
            configured=True,
            model=model,
            fast_model=fast_model,
            vision_model=vision_model,
            resource=foundry_resource or foundry_base,
        )
    if provider in ("", "openai_compatible") and az_openai_key and az_openai_endpoint:
        dep = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini").strip()
        return FoundryStatus(
            provider="openai_compatible",
            configured=True,
            model=dep,
            fast_model=dep,
            vision_model=dep,
            resource=az_openai_endpoint,
        )
    return FoundryStatus(
        provider="deterministic",
        configured=False,
        model=f"deterministic-fallback ({gemini_model} ready)",
        fast_model="deterministic-rule-parser",
        vision_model="heuristic-vision-preview",
        resource=None,
    )


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    cleaned = raw_text.strip()
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return None
    return None


def _build_anthropic_client():
    import anthropic

    api_key = os.getenv("AZURE_FOUNDRY_API_KEY", "").strip()
    resource = os.getenv("AZURE_FOUNDRY_RESOURCE", "").strip()
    base_url = os.getenv("AZURE_FOUNDRY_BASE_URL", "").strip()

    if hasattr(anthropic, "AnthropicFoundry"):
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        elif resource:
            kwargs["resource"] = resource
        return anthropic.AnthropicFoundry(**kwargs)

    resolved_base = base_url or f"https://{resource}.services.ai.azure.com/anthropic/"
    return anthropic.Anthropic(api_key=api_key, base_url=resolved_base)


def _call_gemini_json(
    status: FoundryStatus,
    target_model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    use_fast: bool,
    max_tokens: int,
    image_bytes: bytes | None,
    image_mime: str,
) -> tuple[dict[str, Any] | None, str]:
    thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "LOW").strip().upper() or "LOW"
    cache_key: tuple[str, ...] | None = None
    if image_bytes is None:
        cache_key = (status.provider, target_model, thinking_level, system_prompt, user_prompt)
        with _CACHE_LOCK:
            cached = _TEXT_RESPONSE_CACHE.get(cache_key)
            if cached is not None:
                _TEXT_RESPONSE_CACHE.move_to_end(cache_key)
                return dict(cached), target_model

    if image_bytes is not None:
        max_output_tokens = min(max(max_tokens * 2, 1400), 2000)
    elif use_fast:
        max_output_tokens = min(max(max_tokens * 2, 1200), 1800)
    else:
        max_output_tokens = min(max(max_tokens * 2, 2400), 3600)

    parts: list[dict[str, Any]] = []
    if image_bytes is not None:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        parts.append({"inlineData": {"mimeType": image_mime, "data": b64}})
    parts.append({"text": user_prompt})

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingLevel": thinking_level},
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": os.getenv("GEMINI_API_KEY", "").strip(),
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    last_exc: Exception | None = None
    raw_resp: dict[str, Any] | None = None
    for attempt in range(2):
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                raw_resp = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 503 and attempt == 0:
                time.sleep(1.5)
                continue
            return None, f"{target_model} (fallback: HTTP{exc.code})"
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            return None, f"{target_model} (fallback: {type(exc).__name__})"

    if raw_resp is None:
        err_name = type(last_exc).__name__ if last_exc else "NoResponse"
        return None, f"{target_model} (fallback: {err_name})"

    candidates = raw_resp.get("candidates", [])
    if not candidates:
        return None, f"{target_model} (fallback: EmptyCandidates)"

    resp_parts = candidates[0].get("content", {}).get("parts", [])
    text_out = "".join(p.get("text", "") for p in resp_parts if not p.get("thought"))
    parsed = _extract_json_object(text_out)
    if parsed is None:
        return None, f"{target_model} (fallback: InvalidJSON)"

    if cache_key is not None:
        with _CACHE_LOCK:
            _TEXT_RESPONSE_CACHE[cache_key] = dict(parsed)
            _TEXT_RESPONSE_CACHE.move_to_end(cache_key)
            if len(_TEXT_RESPONSE_CACHE) > _MAX_CACHE_ENTRIES:
                _TEXT_RESPONSE_CACHE.popitem(last=False)

    return parsed, target_model


def call_foundry_json(
    system_prompt: str,
    user_prompt: str,
    *,
    use_fast: bool = False,
    max_tokens: int = 1600,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> tuple[dict[str, Any] | None, str]:
    """Call active LLM provider (Gemini 4 Hydrogen, Azure Foundry, or fallback) and parse JSON safely."""
    status = get_foundry_status()
    if not status.configured:
        return None, status.model

    target_model = status.vision_model if image_bytes else (status.fast_model if use_fast else status.model)

    try:
        if status.provider == "gemini":
            return _call_gemini_json(
                status,
                target_model,
                system_prompt,
                user_prompt,
                use_fast=use_fast,
                max_tokens=max_tokens,
                image_bytes=image_bytes,
                image_mime=image_mime,
            )

        if status.provider == "anthropic":
            client = _build_anthropic_client()
            content: list[dict[str, Any]] = []
            if image_bytes:
                b64 = base64.b64encode(image_bytes).decode("ascii")
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": image_mime, "data": b64},
                })
            content.append({"type": "text", "text": user_prompt})
            msg = client.messages.create(
                model=target_model,
                max_tokens=max_tokens,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            text_out = "".join(
                getattr(block, "text", "")
                for block in getattr(msg, "content", [])
                if getattr(block, "type", "") == "text"
            )
            return _extract_json_object(text_out), target_model

        if status.provider == "openai_compatible":
            from openai import AzureOpenAI

            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview").strip(),
            )
            user_content: Any = user_prompt
            if image_bytes:
                b64 = base64.b64encode(image_bytes).decode("ascii")
                user_content = [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64}"}},
                ]
            resp = client.chat.completions.create(
                model=target_model,
                temperature=0.2,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            text_out = resp.choices[0].message.content or ""
            return _extract_json_object(text_out), target_model
    except Exception as exc:  # noqa: BLE001 — graceful fallback on network/quota/API error
        return None, f"{target_model} (fallback: {type(exc).__name__})"

    return None, status.model
