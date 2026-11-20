"""Unified Azure AI Foundry client adapter (Claude primary, OpenAI-compat fallback, zero-key resilience)."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass
class FoundryStatus:
    provider: str  # "anthropic" | "openai_compatible" | "deterministic"
    configured: bool
    model: str
    fast_model: str
    vision_model: str
    resource: str | None = None


def get_foundry_status() -> FoundryStatus:
    provider = os.getenv("AZURE_FOUNDRY_PROVIDER", "anthropic").strip().lower()
    foundry_key = os.getenv("AZURE_FOUNDRY_API_KEY", "").strip()
    foundry_resource = os.getenv("AZURE_FOUNDRY_RESOURCE", "").strip()
    foundry_base = os.getenv("AZURE_FOUNDRY_BASE_URL", "").strip()
    az_openai_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    az_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()

    model = os.getenv("AZURE_FOUNDRY_MODEL", "claude-sonnet-5-5").strip()
    fast_model = os.getenv("AZURE_FOUNDRY_FAST_MODEL", "claude-haiku-5-5").strip()
    vision_model = os.getenv("AZURE_FOUNDRY_VISION_MODEL", model).strip()

    if provider == "anthropic" and foundry_key and (foundry_resource or foundry_base):
        return FoundryStatus(
            provider="anthropic",
            configured=True,
            model=model,
            fast_model=fast_model,
            vision_model=vision_model,
            resource=foundry_resource or foundry_base,
        )
    if (provider == "openai_compatible" or az_openai_key) and az_openai_key and az_openai_endpoint:
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
        model=f"deterministic-fallback ({model} ready)",
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


def call_foundry_json(
    system_prompt: str,
    user_prompt: str,
    *,
    use_fast: bool = False,
    max_tokens: int = 1600,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> tuple[dict[str, Any] | None, str]:
    """Call Azure AI Foundry (Claude primary or OpenAI-compatible) and parse JSON safely."""
    status = get_foundry_status()
    if not status.configured:
        return None, status.model

    target_model = status.vision_model if image_bytes else (status.fast_model if use_fast else status.model)

    try:
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
