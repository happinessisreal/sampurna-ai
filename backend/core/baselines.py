"""Deterministic comparison against animal & single-plant protein baselines per 20g protein."""

from __future__ import annotations

from pydantic import BaseModel

from backend.core.data import PriceTier, ScoringStandard, load_ingredients
from backend.core.scoring import BlendScore, score_blend

BASELINE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("chicken_broiler", "Broiler Chicken (Edible Meat)", "ব্রয়লার মুরগি (ভোজ্য মাংস)"),
    ("beef_boneless", "Beef (Boneless)", "গরুর মাংস (বোনলেস)"),
    ("egg_farm", "Farm Egg (Edible)", "ফার্মের ডিম"),
    ("fish_pangas_rohu", "Freshwater Fish (Edible)", "রুই/পাঙ্গাস মাছ (ভোজ্য)"),
    ("red_lentil", "Red Lentil Alone", "শুধু মসুর ডাল"),
    ("white_rice", "White Rice Alone", "শুধু সাদা চাল"),
)


class BaselineComparisonItem(BaseModel):
    baseline_id: str
    name: str
    name_bn: str
    serving_grams_for_20g_protein: float
    cost_bdt: float
    co2e_g: float
    water_l: float
    quality_score: float
    limiting_aa: str
    cost_change_pct: float
    co2e_change_pct: float
    water_change_pct: float
    quality_change_pct: float
    cost_savings_bdt: float
    co2e_savings_g: float


def compare_to_baselines(
    blend_score: BlendScore,
    standard: ScoringStandard = "fao_2013_diaas",
    price_tier: PriceTier = "open_market",
    price_overrides: dict[str, float] | None = None,
) -> list[BaselineComparisonItem]:
    """Compare a 20g-protein blend against animal and single-crop baselines."""
    ingredients = load_ingredients()
    results: list[BaselineComparisonItem] = []

    b_cost = blend_score.cost_per_20g_protein_bdt
    b_co2 = blend_score.co2e_per_20g_protein_g
    b_wat = blend_score.water_per_20g_protein_l
    b_qual = blend_score.active_quality_score

    for base_id, label_en, label_bn in BASELINE_SPECS:
        ing = ingredients[base_id]
        grams_20g = 2000.0 / ing.protein_g_per_100g
        ref_score = score_blend(
            {base_id: grams_20g},
            standard=standard,
            price_tier=price_tier,
            price_overrides=price_overrides,
        )
        r_cost = ref_score.cost_per_20g_protein_bdt
        r_co2 = ref_score.co2e_per_20g_protein_g
        r_wat = ref_score.water_per_20g_protein_l
        r_qual = ref_score.active_quality_score

        results.append(
            BaselineComparisonItem(
                baseline_id=base_id,
                name=label_en,
                name_bn=label_bn,
                serving_grams_for_20g_protein=round(grams_20g, 1),
                cost_bdt=r_cost,
                co2e_g=r_co2,
                water_l=r_wat,
                quality_score=r_qual,
                limiting_aa=ref_score.limiting_aa,
                cost_change_pct=round(((b_cost - r_cost) / max(r_cost, 1e-6)) * 100.0, 1),
                co2e_change_pct=round(((b_co2 - r_co2) / max(r_co2, 1e-6)) * 100.0, 1),
                water_change_pct=round(((b_wat - r_wat) / max(r_wat, 1e-6)) * 100.0, 1),
                quality_change_pct=round(((b_qual - r_qual) / max(r_qual, 1e-6)) * 100.0, 1),
                cost_savings_bdt=round(r_cost - b_cost, 2),
                co2e_savings_g=round(r_co2 - b_co2, 1),
            )
        )
    return results
