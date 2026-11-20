"""Integration tests for FastAPI endpoints, RAG literature retrieval, 4-agent pipeline, and FastMCP server."""

import json

from fastapi.testclient import TestClient

from backend.agent.rag import list_all_papers, search_literature
from backend.main import app
from backend.mcp_server import (
    analyze_molecular_sensory as mcp_chemistry,
    compute_pareto_frontier as mcp_pareto,
    generate_impact_report as mcp_report,
    optimize_protein_blend as mcp_optimize,
    search_food_literature as mcp_rag,
)

client = TestClient(app)


def test_health_and_reference_endpoints():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["dataset"]["plant_ingredients"] == 14
    assert data["dataset"]["papers"] == 10
    assert data["mcp_tools"] == 5

    presets = client.get("/api/presets").json()
    assert len(presets) == 4

    ings = client.get("/api/ingredients").json()
    assert len(ings["plant_ingredients"]) == 14
    assert len(ings["baselines"]) == 4

    patterns = client.get("/api/reference-patterns").json()
    assert "fao_2013_diaas" in patterns
    assert "who_2007_pdcaas" in patterns


def test_rag_literature_returns_real_dois():
    all_papers = list_all_papers()
    assert len(all_papers) == 10
    hits = search_literature("hexanal beany off-flavor oyster mushroom umami", top_k=3)
    assert len(hits) == 3
    assert any(h.doi for h in hits)


def test_optimize_pareto_agent_vision_and_report_endpoints():
    opt = client.post(
        "/api/optimize",
        json={
            "mode": "meat_analogue",
            "standard": "fao_2013_diaas",
            "min_score": 1.0,
            "excluded_allergens": ["peanut"],
            "include_ids": ["red_lentil", "oyster_mushroom"],
        },
    )
    assert opt.status_code == 200
    opt_data = opt.json()
    assert opt_data["feasible"]
    assert opt_data["score"]["diaas_score"] >= 1.0
    assert len(opt_data["baselines"]) == 6
    assert opt_data["economics"]["gross_margin_pct"] > 0

    par = client.post(
        "/api/pareto",
        json={"standard": "fao_2013_diaas", "min_score": 0.95, "excluded_allergens": ["peanut"]},
    )
    assert par.status_code == 200
    assert par.json()["feasible"]
    assert len(par.json()["points"]) >= 3

    agent_res = client.post(
        "/api/agent/formulate",
        json={"brief": "ঢাকার পরিবারের জন্য সাশ্রয়ী সম্পূর্ণ প্রোটিন কিমা ও বাংলা রেসিপি দাও"},
    )
    assert agent_res.status_code == 200
    ag = agent_res.json()
    assert ag["audit_passed"]
    assert len(ag["agent_trace"]) == 4
    assert len(ag["recipe_steps_bn"]) >= 3
    assert len(ag["hypotheses_to_test_bn"]) >= 2

    vis = client.post("/api/vision/inspect", data={"sample_id": "keema_prototype"})
    assert vis.status_code == 200
    assert vis.json()["epistemic_tier"] == "AI_HYPOTHESIS"

    rep = client.post(
        "/api/report/download",
        json={
            "product_name": "Dhaka Sampurna Keema",
            "product_format": "Keema",
            "target_customer": "Dhaka Families",
            "grams_by_id": opt_data["grams_by_id"],
        },
    )
    assert rep.status_code == 200
    assert "Sampurna AI — Data-Backed Impact Report" in rep.text


def test_nebius_kimi_client_and_cost_cache(monkeypatch):
    from types import SimpleNamespace
    import openai

    from backend.agent import llm_client

    for var in ("AZURE_FOUNDRY_PROVIDER", "AI_PROVIDER", "GEMINI_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_FOUNDRY_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key")
    monkeypatch.setenv("NEBIUS_MODEL", "moonshotai/Kimi-K3.1-Pro")
    llm_client.clear_llm_cache()

    status = llm_client.get_foundry_status()
    assert status.provider == "nebius"
    assert status.configured
    assert status.model == "moonshotai/Kimi-K3.1-Pro"
    assert status.resource == "https://api.tokenfactory.nebius.com/v1/"

    calls: list[dict] = []

    class _FakeOpenAI:
        def __init__(self, *, api_key, base_url, timeout, max_retries):
            calls.append({"api_key": api_key, "base_url": base_url, "timeout": timeout, "max_retries": max_retries})
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, **kwargs):
            calls[-1]["create_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true, "greeting_bn": "স্বাগতম"}'))]
            )

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)

    parsed, model = llm_client.call_foundry_json("Return JSON", "Say hello", use_fast=True, max_tokens=400)
    assert parsed == {"ok": True, "greeting_bn": "স্বাগতম"}
    assert model == "moonshotai/Kimi-K3.1-Pro"
    assert len(calls) == 1
    ck = calls[0]["create_kwargs"]
    assert ck["model"] == "moonshotai/Kimi-K3.1-Pro"
    assert ck["reasoning_effort"] == "low"
    assert ck["response_format"] == {"type": "json_object"}
    assert ck["max_completion_tokens"] <= 1800

    # Identical repeat call must hit in-memory cache with zero extra API calls
    parsed2, _ = llm_client.call_foundry_json("Return JSON", "Say hello", use_fast=True, max_tokens=400)
    assert parsed2 == parsed
    assert len(calls) == 1
    llm_client.clear_llm_cache()


def test_gemini_hydrogen_client_and_cost_cache(monkeypatch):
    import urllib.request

    from backend.agent import llm_client

    for var in ("AZURE_FOUNDRY_PROVIDER", "AI_PROVIDER", "AZURE_OPENAI_API_KEY", "AZURE_FOUNDRY_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-4-hydrogen")
    llm_client.clear_llm_cache()

    status = llm_client.get_foundry_status()
    assert status.provider == "gemini"
    assert status.configured
    assert status.model == "gemini-4-hydrogen"

    calls: list[dict] = []

    class _FakeResp:
        def __init__(self, payload: dict):
            self._raw = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append(
            {
                "url": req.full_url,
                "headers": {k.lower(): v for k, v in req.header_items()},
                "body": json.loads(req.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return _FakeResp(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "internal reasoning", "thought": True},
                                {"text": '{"ok": true, "greeting_bn": "স্বাগতম"}'},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    parsed, model = llm_client.call_foundry_json("Return JSON", "Say hello", use_fast=True, max_tokens=300)
    assert parsed == {"ok": True, "greeting_bn": "স্বাগতম"}
    assert model == "gemini-4-hydrogen"
    assert len(calls) == 1
    call = calls[0]
    assert "test-key" not in call["url"]
    assert call["headers"]["x-goog-api-key"] == "test-key"
    gen_cfg = call["body"]["generationConfig"]
    assert gen_cfg["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert gen_cfg["responseMimeType"] == "application/json"
    assert "thinkingBudget" not in json.dumps(call["body"])
    assert gen_cfg["maxOutputTokens"] <= 1800

    # Identical second call must be served from the in-memory cache (no extra API cost)
    parsed2, _ = llm_client.call_foundry_json("Return JSON", "Say hello", use_fast=True, max_tokens=300)
    assert parsed2 == parsed
    assert len(calls) == 1
    llm_client.clear_llm_cache()


def test_fastmcp_tools_execute_end_to_end():
    res = mcp_optimize(mode="cheapest", excluded_allergens=["peanut"])
    assert res["feasible"]
    grams = res["grams_by_id"]

    pareto = mcp_pareto(min_score=0.95)
    assert pareto["feasible"]

    chem = mcp_chemistry(grams)
    assert "detected_molecules" in chem

    lit = mcp_rag("jackfruit seed water holding capacity", top_k=2)
    assert len(lit) == 2

    md = mcp_report("Test SKU", "Premix", "RMG", grams)
    assert "VERIFIED COMPUTED" in md
    assert json.dumps(res)  # JSON-serializable output
