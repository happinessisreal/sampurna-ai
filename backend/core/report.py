"""Deterministic Data-Backed Impact Report generator with 3-tier epistemic provenance."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from backend.core.baselines import compare_to_baselines
from backend.core.chemistry import analyze_molecular_sensory
from backend.core.data import load_ingredients
from backend.core.economics import EconomicsRequest, simulate_factory_economics
from backend.core.optimizer import OptimizeRequest, optimize_blend
from backend.core.scoring import BlendScore, score_blend


def generate_impact_report(
    product_name: str,
    product_format: str,
    target_customer: str,
    grams_by_id: dict[str, float],
    blend_score: BlendScore | None = None,
    econ_params: EconomicsRequest | None = None,
) -> str:
    """Build a complete Data-Backed Markdown Impact Report strictly from computed numbers."""
    score = blend_score or score_blend(grams_by_id)
    baselines = compare_to_baselines(score, standard=score.standard, price_tier=score.price_tier)
    sensory = analyze_molecular_sensory(grams_by_id)
    econ = simulate_factory_economics(score, econ_params)
    ing_map = load_ingredients()

    chicken = next(b for b in baselines if b.baseline_id == "chicken_broiler")
    beef = next(b for b in baselines if b.baseline_id == "beef_boneless")
    lentil = next(b for b in baselines if b.baseline_id == "red_lentil")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    std_label = "FAO (2013) DIAAS-Proxy" if score.standard == "fao_2013_diaas" else "WHO/FAO/UNU (2007) PDCAAS"

    lines: list[str] = [
        f"# Sampurna AI — Data-Backed Impact Report: {product_name}",
        "",
        f"> **Platform:** Sampurna AI — Molecular & Sustainable Plant-Protein Formulation  ",
        f"> **Generated:** {timestamp} | **Scoring Standard:** `{std_label}` | **Price Tier:** `{score.price_tier}`  ",
        f"> **Epistemic Integrity Contract:** All quantitative nutrition, cost, carbon, and unit-economic figures below are **VERIFIED COMPUTED** deterministically over cited datasets (`core/scoring.py`, `core/optimizer.py`). Sensory compatibility indices are **MODEL ESTIMATED** via PubChem compound profiles; culinary execution and shelf-life are **AI HYPOTHESES** awaiting wet-lab validation.",
        "",
        "## 1. Executive Summary (`VERIFIED COMPUTED`)",
        f"- **Product SKU:** {product_name} ({product_format})",
        f"- **Target Market:** {target_customer}",
        f"- **Standardized Serving (20 g Complete Protein):** `{score.total_mass_g:.1f} g` dry blend delivering `{score.active_quality_score:.3f}` {std_label} (limiting AA: **{score.limiting_aa_label_en}**), `৳{score.cost_per_20g_protein_bdt:.2f}`, and `{score.co2e_per_20g_protein_g:.1f} g CO2e`.",
        f"- **Improvement vs. Edible Broiler Chicken:** **{chicken.cost_change_pct:+.1f}% cost** (`৳{chicken.cost_bdt:.2f} → ৳{score.cost_per_20g_protein_bdt:.2f}`) and **{chicken.co2e_change_pct:+.1f}% GHG emissions** (`{chicken.co2e_g:.0f} g → {score.co2e_per_20g_protein_g:.1f} g CO2e`).",
        f"- **Improvement vs. Boneless Beef:** **{beef.cost_change_pct:+.1f}% cost** and **{beef.co2e_change_pct:+.1f}% GHG emissions**.",
        f"- **Protein Completeness Gain vs. Red Lentil Alone:** **{lentil.quality_change_pct:+.1f}% protein quality** (`{lentil.quality_score:.3f} → {score.active_quality_score:.3f}`).",
        "",
        "## 2. Optimized Formulation Sheet (Per 20 g Protein Serving)",
        "",
        "| Ingredient | Bangla Name | Dry Mass (g) | Share (%) | Protein (g) | Cost (BDT) | CO2e (g) | Data Verification |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]

    for item in score.items:
        flag = "VERIFIED" if item.verified else "ESTIMATE — Verify"
        lines.append(
            f"| {item.name} | {item.name_bn} | {item.grams:.2f} | {item.mass_share_pct:.1f}% | "
            f"{item.protein_g:.2f} | ৳{item.cost_bdt:.2f} | {item.co2e_g:.1f} | {flag} |"
        )

    lines.extend([
        "",
        f"- **Micronutrient & Fiber Co-Benefits (per 20 g protein serving):** `{score.fiber_g:.1f} g` dietary fiber, `{score.iron_mg:.2f} mg` iron, `{score.zinc_mg:.2f} mg` zinc.",
        f"- **Allergen Disclosure:** {', '.join(score.allergens_present) if score.allergens_present else 'None (top-8 major allergens excluded)'}.",
    ])

    if score.has_unverified_inputs:
        lines.extend([
            "",
            f"> **Verification Warning:** Unverified LCA/dry-price proxy estimates were used for: `{', '.join(score.unverified_ingredients)}`. See Section 7 for exact citation status.",
        ])

    lines.extend([
        "",
        "## 3. Essential Amino Acid Profile vs. Reference Pattern (`VERIFIED COMPUTED`)",
        "",
        "| Indispensable Amino Acid | Blend (mg/g protein) | Digestible (mg/g) | Reference (mg/g) | Sufficiency (%) | Status |",
        "| :--- | ---: | ---: | ---: | ---: | :---: |",
    ])
    for aa in score.amino_acids:
        st = "LIMITING" if aa.is_limiting else ("OK" if aa.sufficiency_pct >= 100 else "DEFICIT")
        lines.append(
            f"| {aa.name_en} | {aa.blend_mg_per_g_protein:.1f} | {aa.digestible_mg_per_g_protein:.1f} | "
            f"{aa.reference_mg_per_g_protein:.1f} | {aa.sufficiency_pct:.1f}% | {st} |"
        )

    lines.extend([
        "",
        "## 4. Baseline Comparison (Normalized per 20 g Protein)",
        "",
        "| Baseline | Mass (g) | Cost (BDT) | Cost Delta | CO2e (g) | CO2e Delta | Quality Score |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| **{product_name}** | {score.total_mass_g:.1f} | **৳{score.cost_per_20g_protein_bdt:.2f}** | — | **{score.co2e_per_20g_protein_g:.1f}** | — | **{score.active_quality_score:.3f}** |",
    ])
    for b in baselines:
        lines.append(
            f"| {b.name} | {b.serving_grams_for_20g_protein:.1f} | ৳{b.cost_bdt:.2f} | {b.cost_change_pct:+.1f}% | "
            f"{b.co2e_g:.1f} | {b.co2e_change_pct:+.1f}% | {b.quality_score:.3f} |"
        )

    lines.extend([
        "",
        "## 5. Molecular Flavor & Functional Chemistry (`MODEL ESTIMATED`)",
        f"- **Beany Off-Note Risk (Hexanal / 2-Pentylfuran):** `{sensory.beany_off_note_risk_pct:.1f}%` (suppressed via umami/Maillard synergy)",
        f"- **Umami & Maillard Synergy Index:** `{sensory.umami_synergy_score:.1f}/100` (Umami) · `{sensory.maillard_browning_potential:.1f}/100` (Maillard)",
        f"- **Functional Texture Matrix:** Water Holding `{sensory.functional_traits.water_holding:.0f}%` · Emulsification `{sensory.functional_traits.emulsification:.0f}%` · Gelation `{sensory.functional_traits.gelation:.0f}%` · Fibrous Anisotropy `{sensory.functional_traits.fibrous_anisotropy:.0f}%`",
        "- **Key PubChem Compounds:** " + ", ".join(f"{m.name} ([CID {m.cid}]({m.pubchem_url}))" for m in sensory.detected_molecules[:5]),
        "",
        "## 6. Manufacturing & Institutional RMG Scale Economics (`VERIFIED COMPUTED`)",
        f"- **1,000 kg Batch Raw COGS:** `৳{econ.raw_ingredient_cogs_per_kg_bdt:.2f}/kg` | **Total COGS (with ৳{econ_params.processing_packaging_bdt_per_kg if econ_params else 18.0:.0f}/kg processing):** `৳{econ.total_cogs_per_kg_bdt:.2f}/kg` (`৳{econ.batch_total_cost_bdt:,.0f}` per batch)",
        f"- **B2B Wholesale Price & Gross Margin:** `৳{econ.wholesale_price_bdt_per_kg:.2f}/kg` → **{econ.gross_margin_pct:.1f}% gross margin** (`৳{econ.batch_gross_profit_bdt:,.0f}` profit per 1,000 kg batch)",
        f"- **Institutional Impact ({econ.daily_servings:,} RMG canteen workers × {econ.operating_days_per_year} days/yr):**",
        f"  - Annual Cost Savings vs. Edible Chicken: **`৳{econ.annual_bdt_saved_vs_chicken:,.0f}/yr`**",
        f"  - Annual GHG Emissions Avoided: **`{econ.annual_co2e_avoided_tonnes_vs_chicken:,.1f} tonnes CO2e/yr`** (≈ `{econ.equivalent_cars_removed}` passenger cars removed)",
        f"  - Annual Freshwater Saved: **`{econ.annual_water_saved_million_l_vs_chicken:.2f} million liters/yr`**",
        "",
        "## 7. Data Sources & Explicit Responsible-AI Limitations",
        "### Data Sources Used",
    ])
    for item in score.items:
        ing = ing_map[item.id]
        lines.append(
            f"- **{ing.name}:** Nutrition: *{ing.source_nutrition}* | Price: *{ing.source_price}* | Carbon: *{ing.source_co2e}* | Verified: `{ing.verified}`"
        )
    lines.extend([
        "",
        "### Explicit Limitations & Phase 2 Validation Plan",
        "1. **No Wet-Lab / Sensory Testing Yet (Phase 2 Priority):** Flavor masking, extrusion/pan-cook texture, and 9-point hedonic acceptability require physical kitchen & 20-person blind sensory testing.",
        "2. **Digestibility Approximation:** FAO (2013) DIAAS / WHO (2007) PDCAAS coefficients use ingredient-level literature averages; final cooked matrix antinutrients (trypsin inhibitors, phytates) alter true ileal absorption.",
        "3. **Dynamic Market Prices:** Dhaka open retail and TCB prices fluctuate seasonally; the UI allows instant per-ingredient BDT/kg overrides.",
        "4. **Global LCA Averages:** CO2e factors derive from Poore & Nemecek (2018) global supply-chain averages rather than Bangladesh-specific farm/processing LCA audits.",
    ])

    return "\n".join(lines) + "\n"


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic docs/IMPACT_REPORT.md")
    parser.add_argument("--output", default="docs/IMPACT_REPORT.md")
    args = parser.parse_args()

    # Flagship Preset: Dhaka Complete Plant-Protein Keema (Meat-Analogue + Budget Complete)
    res = optimize_blend(
        OptimizeRequest(
            mode="meat_analogue",
            standard="fao_2013_diaas",
            price_tier="open_market",
            min_score=1.0,
            max_budget_bdt=16.0,
            excluded_allergens=["peanut"],
            include_ids=["red_lentil", "oyster_mushroom", "green_jackfruit"],
        )
    )
    if not res.feasible or res.score is None:
        raise SystemExit(f"Failed to compute flagship blend: {res.diagnostic_hint_en}")

    md = generate_impact_report(
        product_name="Dhaka Sampurna Plant-Protein Keema",
        product_format="Hydrated spiced meat-analogue keema dry premix",
        target_customer="Dhaka middle-income households & institutional RMG factory canteens",
        grams_by_id=res.grams_by_id,
        blend_score=res.score,
    )
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.output} ({len(md)} bytes) | Cost: BDT {res.score.cost_bdt:.2f} | CO2e: {res.score.co2e_g:.1f}g | DIAAS: {res.score.diaas_score:.3f}")


if __name__ == "__main__":
    _cli()
