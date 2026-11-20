"""FastAPI single-origin backend serving Sampurna AI APIs + React SPA."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agent.llm_client import get_foundry_status
from backend.agent.orchestrator import (
    FormulateAgentRequest,
    inspect_prototype_image,
    run_four_agent_formulation,
)
from backend.agent.rag import list_all_papers, search_literature
from backend.core.baselines import compare_to_baselines
from backend.core.chemistry import analyze_molecular_sensory
from backend.core.data import (
    ROOT_DIR,
    list_baseline_ingredients,
    list_plant_ingredients,
    load_reference_patterns,
)
from backend.core.economics import EconomicsRequest, simulate_factory_economics
from backend.core.optimizer import OptimizeRequest, compute_pareto_frontier, optimize_blend
from backend.core.report import generate_impact_report
from backend.core.scoring import score_blend
from backend.mcp_server import get_mcp_manifest

app = FastAPI(
    title="Sampurna AI — Plant-Protein Formulation API",
    version="0.1.0",
    description="Deterministic LP/Pareto protein formulation, PubChem sensory chemistry, 4-Agent R&D Copilot, and FastMCP server.",
)

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PRESETS: list[dict[str, Any]] = [
    {
        "id": "dhaka_keema",
        "name_bn": "ঢাকা সাশ্রয়ী কিমা",
        "name_en": "Dhaka Budget Keema",
        "subtitle_bn": "মুরগির চেয়ে ~৬৫% সাশ্রয়ী সম্পূর্ণ প্রোটিন কিমা",
        "subtitle_en": "Fibrous plant-fungal keema, ~65% cheaper than edible chicken",
        "request": OptimizeRequest(
            mode="meat_analogue",
            standard="fao_2013_diaas",
            price_tier="open_market",
            min_score=1.0,
            max_budget_bdt=16.0,
            excluded_allergens=["peanut"],
            include_ids=["red_lentil", "oyster_mushroom", "green_jackfruit"],
        ).model_dump(),
        "brief_bn": "ঢাকার মধ্যবিত্ত পরিবারের জন্য ১৬ টাকার মধ্যে ডাল-গন্ধহীন সম্পূর্ণ প্রোটিন উদ্ভিজ্জ কিমা ও বাংলা রেসিপি তৈরি করো",
        "brief_en": "Formulate a low-cost, zero-beany complete-protein plant keema under 16 BDT for Dhaka households",
    },
    {
        "id": "rmg_khichuri",
        "name_bn": "গার্মেন্টস খিচুড়ি প্রিমিক্স",
        "name_en": "RMG Canteen Khichuri Premix",
        "subtitle_bn": "দৈনিক ১০,০০০ কর্মীর জন্য TCB ভর্তুকি প্রিমিক্স",
        "subtitle_en": "Institutional fortified dal-rice premix for 10,000 RMG workers",
        "request": OptimizeRequest(
            mode="cheapest",
            standard="fao_2013_diaas",
            price_tier="tcb_subsidized",
            min_score=1.0,
            max_budget_bdt=14.0,
            excluded_allergens=["peanut"],
            include_ids=["red_lentil", "white_rice"],
        ).model_dump(),
        "brief_bn": "গার্মেন্টস কারখানার ক্যান্টিনে ১০,০০০ কর্মীর জন্য সাশ্রয়ী সম্পূর্ণ প্রোটিন খিচুড়ি প্রিমিক্স তৈরি করো",
        "brief_en": "Create an ultra-affordable fortified khichuri premix for a 10,000-worker RMG garment canteen",
    },
    {
        "id": "green_patty",
        "name_bn": "সর্বনিম্ন কার্বন প্যাটি",
        "name_en": "Ultra-Low-Carbon Patty",
        "subtitle_bn": "সর্বনিম্ন CO₂e ও কাঁঠাল-মাশরুম টেক্সচার",
        "subtitle_en": "Minimize LCA greenhouse gas emissions with jackfruit-mushroom bite",
        "request": OptimizeRequest(
            mode="greenest",
            standard="fao_2013_diaas",
            min_score=1.0,
            excluded_allergens=["peanut"],
            include_ids=["oyster_mushroom", "green_jackfruit"],
        ).model_dump(),
        "brief_bn": "সর্বনিম্ন কার্বন ফুটপ্রিন্টে কাঁচা কাঁঠাল ও অয়েস্টার মাশরুম দিয়ে বার্গার প্যাটি তৈরি করো",
        "brief_en": "Design an ultra-low-carbon plant burger patty using green jackfruit and oyster mushroom",
    },
    {
        "id": "allergen_free",
        "name_bn": "গ্লুটেন-ফ্রি হাই-DIAAS",
        "name_en": "Gluten & Soy-Free High-DIAAS",
        "subtitle_bn": "সয়া, গ্লুটেন ও বাদাম মুক্ত সম্পূর্ণ প্রোটিন",
        "subtitle_en": "100% soy-free, gluten-free, peanut-free complete amino profile",
        "request": OptimizeRequest(
            mode="cheapest",
            standard="fao_2013_diaas",
            min_score=1.0,
            excluded_allergens=["soy", "gluten", "peanut"],
            include_ids=["red_lentil", "oyster_mushroom"],
        ).model_dump(),
        "brief_bn": "সয়া, গ্লুটেন ও বাদাম ছাড়া উচ্চ DIAAS মানের সম্পূর্ণ উদ্ভিজ্জ প্রোটিন ব্লেন্ড তৈরি করো",
        "brief_en": "Formulate a soy-free, gluten-free, peanut-free complete protein blend with DIAAS >= 1.0",
    },
]


class FullOptimizeRequest(OptimizeRequest):
    economics: EconomicsRequest = Field(default_factory=EconomicsRequest)


class ScoreDirectRequest(BaseModel):
    grams_by_id: dict[str, float]
    standard: str = "fao_2013_diaas"
    price_tier: str = "open_market"
    price_overrides: dict[str, float] = Field(default_factory=dict)
    economics: EconomicsRequest = Field(default_factory=EconomicsRequest)


class ReportGenerateRequest(BaseModel):
    product_name: str = "Dhaka Sampurna Plant-Protein Keema"
    product_format: str = "Hydrated spiced meat-analogue keema"
    target_customer: str = "Dhaka middle-income families & RMG canteens"
    grams_by_id: dict[str, float]
    standard: str = "fao_2013_diaas"
    price_tier: str = "open_market"
    price_overrides: dict[str, float] = Field(default_factory=dict)
    economics: EconomicsRequest = Field(default_factory=EconomicsRequest)


@app.get("/api/health")
def health() -> dict[str, Any]:
    foundry = get_foundry_status()
    plant = list_plant_ingredients()
    verified_count = sum(1 for ing in plant if ing.verified)
    return {
        "status": "ok",
        "app": "Sampurna AI",
        "challenge": "Alternative Protein Formulation",
        "ai_foundry": {
            "provider": foundry.provider,
            "configured": foundry.configured,
            "model": foundry.model,
            "fast_model": foundry.fast_model,
            "vision_model": foundry.vision_model,
        },
        "dataset": {
            "plant_ingredients": len(plant),
            "verified_ingredients": verified_count,
            "unverified_proxy_ingredients": len(plant) - verified_count,
            "baselines": len(list_baseline_ingredients()),
            "papers": len(list_all_papers()),
        },
        "mcp_tools": get_mcp_manifest()["tool_count"],
    }


@app.get("/api/presets")
def presets() -> list[dict[str, Any]]:
    return PRESETS


@app.get("/api/ingredients")
def ingredients() -> dict[str, Any]:
    return {
        "plant_ingredients": [ing.model_dump() for ing in list_plant_ingredients()],
        "baselines": [ing.model_dump() for ing in list_baseline_ingredients()],
    }


@app.get("/api/reference-patterns")
def reference_patterns() -> dict[str, Any]:
    return {k: v.model_dump() for k, v in load_reference_patterns().items()}


@app.get("/api/papers")
def papers(q: str | None = None, top_k: int = 4) -> dict[str, Any]:
    if q and q.strip():
        return {"query": q, "hits": [h.model_dump() for h in search_literature(q, top_k=top_k)]}
    return {"papers": list_all_papers()}


@app.get("/api/mcp-manifest")
def mcp_manifest() -> dict[str, Any]:
    return get_mcp_manifest()


@app.post("/api/optimize")
def api_optimize(req: FullOptimizeRequest) -> dict[str, Any]:
    opt_res = optimize_blend(req)
    if not opt_res.feasible or opt_res.score is None:
        return opt_res.model_dump()
    baselines = compare_to_baselines(
        opt_res.score,
        standard=req.standard,
        price_tier=req.price_tier,
        price_overrides=req.price_overrides,
    )
    sensory = analyze_molecular_sensory(opt_res.grams_by_id)
    econ = simulate_factory_economics(opt_res.score, req.economics)
    return {
        **opt_res.model_dump(),
        "baselines": [b.model_dump() for b in baselines],
        "sensory": sensory.model_dump(),
        "economics": econ.model_dump(),
    }


@app.post("/api/score")
def api_score(req: ScoreDirectRequest) -> dict[str, Any]:
    try:
        sc = score_blend(
            req.grams_by_id,
            standard=req.standard,  # type: ignore[arg-type]
            price_tier=req.price_tier,  # type: ignore[arg-type]
            price_overrides=req.price_overrides,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    baselines = compare_to_baselines(
        sc,
        standard=sc.standard,
        price_tier=sc.price_tier,
        price_overrides=req.price_overrides,
    )
    sensory = analyze_molecular_sensory(req.grams_by_id)
    econ = simulate_factory_economics(sc, req.economics)
    return {
        "feasible": True,
        "grams_by_id": req.grams_by_id,
        "score": sc.model_dump(),
        "baselines": [b.model_dump() for b in baselines],
        "sensory": sensory.model_dump(),
        "economics": econ.model_dump(),
    }


@app.post("/api/pareto")
def api_pareto(req: OptimizeRequest) -> dict[str, Any]:
    return compute_pareto_frontier(req).model_dump()


@app.post("/api/agent/formulate")
def api_agent_formulate(req: FormulateAgentRequest) -> dict[str, Any]:
    return run_four_agent_formulation(req).model_dump()


@app.post("/api/vision/inspect")
async def api_vision_inspect(
    sample_id: str = Form("keema_prototype"),
    blend_context: str = Form("Soy TVP + Red Lentil + Oyster Mushroom + Green Jackfruit Keema"),
    file: UploadFile | None = File(None),
) -> dict[str, Any]:
    img_bytes = await file.read() if file is not None else None
    mime = (file.content_type or "image/jpeg") if file is not None else "image/jpeg"
    return inspect_prototype_image(
        image_bytes=img_bytes if img_bytes else None,
        image_mime=mime,
        sample_id=sample_id,
        blend_context=blend_context,
    ).model_dump()


@app.post("/api/report")
def api_report(req: ReportGenerateRequest) -> dict[str, Any]:
    sc = score_blend(
        req.grams_by_id,
        standard=req.standard,  # type: ignore[arg-type]
        price_tier=req.price_tier,  # type: ignore[arg-type]
        price_overrides=req.price_overrides,
    )
    md = generate_impact_report(
        product_name=req.product_name,
        product_format=req.product_format,
        target_customer=req.target_customer,
        grams_by_id=req.grams_by_id,
        blend_score=sc,
        econ_params=req.economics,
    )
    return {"markdown": md}


@app.post("/api/report/download", response_class=PlainTextResponse)
def api_report_download(req: ReportGenerateRequest) -> PlainTextResponse:
    sc = score_blend(
        req.grams_by_id,
        standard=req.standard,  # type: ignore[arg-type]
        price_tier=req.price_tier,  # type: ignore[arg-type]
        price_overrides=req.price_overrides,
    )
    md = generate_impact_report(
        product_name=req.product_name,
        product_format=req.product_format,
        target_customer=req.target_customer,
        grams_by_id=req.grams_by_id,
        blend_score=sc,
        econ_params=req.economics,
    )
    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="SAMPURNA_IMPACT_REPORT.md"'},
    )


# Serve built React SPA if present (single-origin container deployment)
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    fonts_dir = FRONTEND_DIST / "fonts"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if fonts_dir.exists():
        app.mount("/fonts", StaticFiles(directory=str(fonts_dir)), name="fonts")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
