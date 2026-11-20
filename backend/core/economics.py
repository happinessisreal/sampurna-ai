"""Deterministic 1,000 kg Factory Batch & Institutional RMG Canteen Scale Economics Simulator."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.core.baselines import compare_to_baselines
from backend.core.scoring import BlendScore

# EPA average passenger car CO2e emission (~4.6 metric tons CO2e / year)
CAR_TONNES_CO2E_PER_YEAR = 4.6


class EconomicsRequest(BaseModel):
    batch_size_kg: float = Field(default=1000.0, ge=50.0, le=50000.0)
    processing_packaging_bdt_per_kg: float = Field(default=18.0, ge=0.0, le=200.0)
    wholesale_price_bdt_per_kg: float = Field(default=245.0, ge=50.0, le=2000.0)
    daily_servings: int = Field(default=10000, ge=100, le=500000)
    operating_days_per_year: int = Field(default=250, ge=30, le=365)


class EconomicsReport(BaseModel):
    epistemic_tier: str = "VERIFIED_COMPUTED"
    batch_size_kg: float
    servings_per_batch: int
    raw_ingredient_cogs_per_kg_bdt: float
    total_cogs_per_kg_bdt: float
    batch_total_cost_bdt: float
    wholesale_price_bdt_per_kg: float
    gross_margin_pct: float
    batch_gross_profit_bdt: float
    daily_servings: int
    operating_days_per_year: int
    annual_servings: int
    annual_dry_tonnes_required: float
    annual_bdt_saved_vs_chicken: float
    annual_co2e_avoided_tonnes_vs_chicken: float
    annual_water_saved_million_l_vs_chicken: float
    equivalent_cars_removed: int


def simulate_factory_economics(
    blend_score: BlendScore,
    params: EconomicsRequest | None = None,
) -> EconomicsReport:
    """Compute batch manufacturing unit economics and annual institutional RMG canteen impact."""
    req = params or EconomicsRequest()
    comparisons = compare_to_baselines(
        blend_score,
        standard=blend_score.standard,
        price_tier=blend_score.price_tier,
    )
    chicken = next(c for c in comparisons if c.baseline_id == "chicken_broiler")

    raw_cogs_kg = blend_score.cost_per_kg_dry_bdt
    total_cogs_kg = raw_cogs_kg + req.processing_packaging_bdt_per_kg
    batch_cost = total_cogs_kg * req.batch_size_kg
    batch_rev = req.wholesale_price_bdt_per_kg * req.batch_size_kg
    gross_profit = batch_rev - batch_cost
    gross_margin_pct = (gross_profit / max(batch_rev, 1e-6)) * 100.0

    serving_mass_g = blend_score.total_mass_g * (20.0 / max(blend_score.total_protein_g, 1e-6))
    servings_per_batch = int((req.batch_size_kg * 1000.0) / max(serving_mass_g, 1.0))

    # Institutional canteen buying at wholesale price vs. edible chicken baseline
    wholesale_cost_per_serving = (serving_mass_g / 1000.0) * req.wholesale_price_bdt_per_kg
    savings_per_serving_bdt = chicken.cost_bdt - wholesale_cost_per_serving

    annual_servings = req.daily_servings * req.operating_days_per_year
    annual_dry_tonnes = (annual_servings * serving_mass_g) / 1_000_000.0
    annual_bdt_saved = annual_servings * savings_per_serving_bdt

    co2_saved_tonnes = (annual_servings * chicken.co2e_savings_g) / 1_000_000.0
    water_saved_m_l = (annual_servings * (chicken.water_l - blend_score.water_per_20g_protein_l)) / 1_000_000.0
    cars_eq = max(0, round(co2_saved_tonnes / CAR_TONNES_CO2E_PER_YEAR))

    return EconomicsReport(
        batch_size_kg=req.batch_size_kg,
        servings_per_batch=servings_per_batch,
        raw_ingredient_cogs_per_kg_bdt=round(raw_cogs_kg, 2),
        total_cogs_per_kg_bdt=round(total_cogs_kg, 2),
        batch_total_cost_bdt=round(batch_cost, 2),
        wholesale_price_bdt_per_kg=round(req.wholesale_price_bdt_per_kg, 2),
        gross_margin_pct=round(gross_margin_pct, 1),
        batch_gross_profit_bdt=round(gross_profit, 2),
        daily_servings=req.daily_servings,
        operating_days_per_year=req.operating_days_per_year,
        annual_servings=annual_servings,
        annual_dry_tonnes_required=round(annual_dry_tonnes, 1),
        annual_bdt_saved_vs_chicken=round(annual_bdt_saved, 0),
        annual_co2e_avoided_tonnes_vs_chicken=round(co2_saved_tonnes, 1),
        annual_water_saved_million_l_vs_chicken=round(water_saved_m_l, 2),
        equivalent_cars_removed=cars_eq,
    )
