"""Deterministic nutritional, amino acid, DIAAS/PDCAAS, cost, and LCA environmental scoring."""

from __future__ import annotations

from pydantic import BaseModel

from backend.core.data import (
    AA_LABELS,
    ESSENTIAL_AMINO_ACIDS,
    PriceTier,
    ScoringStandard,
    load_ingredients,
    load_reference_patterns,
)


class AminoAcidBreakdown(BaseModel):
    code: str
    short_label: str
    name_en: str
    name_bn: str
    blend_mg_per_g_protein: float
    digestible_mg_per_g_protein: float
    reference_mg_per_g_protein: float
    chemical_ratio: float
    digestible_ratio: float
    sufficiency_pct: float
    is_limiting: bool


class BlendIngredientItem(BaseModel):
    id: str
    name: str
    name_bn: str
    category: str
    grams: float
    mass_share_pct: float
    protein_g: float
    cost_bdt: float
    co2e_g: float
    water_l: float
    allergens: list[str]
    verified: bool
    unverified_notes: list[str]


class BlendScore(BaseModel):
    epistemic_tier: str = "VERIFIED_COMPUTED"
    standard: ScoringStandard
    price_tier: PriceTier
    total_mass_g: float
    total_protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    iron_mg: float
    zinc_mg: float
    cost_bdt: float
    cost_per_20g_protein_bdt: float
    cost_per_kg_dry_bdt: float
    co2e_g: float
    co2e_per_20g_protein_g: float
    water_l: float
    water_per_20g_protein_l: float
    chemical_aa_score: float
    weighted_digestibility: float
    diaas_score: float
    pdcaas_score: float
    active_quality_score: float
    limiting_aa: str
    limiting_aa_label_en: str
    limiting_aa_label_bn: str
    is_complete_protein: bool
    amino_acids: list[AminoAcidBreakdown]
    items: list[BlendIngredientItem]
    allergens_present: list[str]
    has_unverified_inputs: bool
    unverified_ingredients: list[str]


def score_blend(
    grams_by_id: dict[str, float],
    standard: ScoringStandard = "fao_2013_diaas",
    price_tier: PriceTier = "open_market",
    price_overrides: dict[str, float] | None = None,
) -> BlendScore:
    """Compute exact nutritional, amino acid, DIAAS/PDCAAS, cost, and carbon metrics for a blend."""
    ingredients = load_ingredients()
    patterns = load_reference_patterns()
    ref_fao = patterns["fao_2013_diaas"]
    ref_who = patterns["who_2007_pdcaas"]
    active_ref = ref_fao if standard == "fao_2013_diaas" else ref_who

    cleaned = {k: float(v) for k, v in grams_by_id.items() if float(v) > 1e-6}
    if not cleaned:
        raise ValueError("Blend must contain at least one ingredient with positive grams.")

    total_mass = sum(cleaned.values())
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    total_fiber = 0.0
    total_iron = 0.0
    total_zinc = 0.0
    total_cost = 0.0
    total_co2e_g = 0.0
    total_water_l = 0.0

    weighted_pdcaas_dig = 0.0
    weighted_diaas_dig = 0.0
    aa_total_mg = {aa: 0.0 for aa in ESSENTIAL_AMINO_ACIDS}
    aa_diaas_mg = {aa: 0.0 for aa in ESSENTIAL_AMINO_ACIDS}
    aa_pdcaas_mg = {aa: 0.0 for aa in ESSENTIAL_AMINO_ACIDS}

    items: list[BlendIngredientItem] = []
    allergens: set[str] = set()
    unverified_ids: list[str] = []

    for ing_id, grams in sorted(cleaned.items(), key=lambda kv: kv[1], reverse=True):
        if ing_id not in ingredients:
            raise KeyError(f"Unknown ingredient ID: {ing_id}")
        ing = ingredients[ing_id]
        factor = grams / 100.0
        protein_g = ing.protein_g_per_100g * factor
        price_kg = ing.price_for_tier(price_tier, price_overrides)
        cost_bdt = (grams / 1000.0) * price_kg
        co2e_g = grams * ing.co2e_kg_per_kg
        water_l = (grams / 1000.0) * ing.water_l_per_kg

        total_protein += protein_g
        total_carbs += ing.carbs_g_per_100g * factor
        total_fat += ing.fat_g_per_100g * factor
        total_fiber += ing.fiber_g_per_100g * factor
        total_iron += ing.iron_mg_per_100g * factor
        total_zinc += ing.zinc_mg_per_100g * factor
        total_cost += cost_bdt
        total_co2e_g += co2e_g
        total_water_l += water_l

        weighted_pdcaas_dig += protein_g * ing.digestibility_pdcaas
        weighted_diaas_dig += protein_g * ing.diaas_ileal_factor

        for aa in ESSENTIAL_AMINO_ACIDS:
            mg = protein_g * float(getattr(ing, aa))
            aa_total_mg[aa] += mg
            aa_diaas_mg[aa] += mg * ing.diaas_ileal_factor
            aa_pdcaas_mg[aa] += mg * ing.digestibility_pdcaas

        allergens.update(ing.allergens)
        unverified_notes: list[str] = []
        if not ing.verified:
            unverified_ids.append(ing.id)
            if "ESTIMATE" in ing.source_price:
                unverified_notes.append(ing.source_price)
            if "ESTIMATE" in ing.source_co2e:
                unverified_notes.append(ing.source_co2e)
            if not unverified_notes:
                unverified_notes.append("Estimated literature proxy — verify locally")

        items.append(
            BlendIngredientItem(
                id=ing.id,
                name=ing.name,
                name_bn=ing.name_bn,
                category=ing.category,
                grams=round(grams, 2),
                mass_share_pct=round((grams / total_mass) * 100.0, 1),
                protein_g=round(protein_g, 2),
                cost_bdt=round(cost_bdt, 2),
                co2e_g=round(co2e_g, 1),
                water_l=round(water_l, 1),
                allergens=ing.allergens,
                verified=ing.verified,
                unverified_notes=unverified_notes,
            )
        )

    if total_protein <= 1e-6:
        raise ValueError("Blend provides zero protein.")

    scale_20 = 20.0 / total_protein

    # Compute chemical AA score, FAO DIAAS-proxy (uncapped), and WHO PDCAAS (capped at 1.0)
    diaas_ratios: dict[str, float] = {}
    pdcaas_ratios: dict[str, float] = {}
    chem_ratios: dict[str, float] = {}

    for aa in ESSENTIAL_AMINO_ACIDS:
        mg_per_g = aa_total_mg[aa] / total_protein
        chem_ratios[aa] = mg_per_g / float(getattr(active_ref, aa))
        diaas_ratios[aa] = (aa_diaas_mg[aa] / total_protein) / float(getattr(ref_fao, aa))
        pdcaas_ratios[aa] = (aa_pdcaas_mg[aa] / total_protein) / float(getattr(ref_who, aa))

    active_ratios = diaas_ratios if standard == "fao_2013_diaas" else pdcaas_ratios
    limiting_aa = min(active_ratios, key=lambda k: active_ratios[k])

    diaas_score = round(min(diaas_ratios.values()), 3)
    pdcaas_score = round(min(1.0, min(pdcaas_ratios.values())), 3)
    chemical_aa_score = round(min(chem_ratios.values()), 3)
    active_quality_score = diaas_score if standard == "fao_2013_diaas" else pdcaas_score

    weighted_dig = (
        (weighted_diaas_dig / total_protein)
        if standard == "fao_2013_diaas"
        else (weighted_pdcaas_dig / total_protein)
    )

    aa_breakdown: list[AminoAcidBreakdown] = []
    for aa in ESSENTIAL_AMINO_ACIDS:
        ref_val = float(getattr(active_ref, aa))
        dig_mg = (
            aa_diaas_mg[aa] / total_protein
            if standard == "fao_2013_diaas"
            else aa_pdcaas_mg[aa] / total_protein
        )
        dig_ratio = active_ratios[aa]
        labels = AA_LABELS[aa]
        aa_breakdown.append(
            AminoAcidBreakdown(
                code=aa,
                short_label=labels["short"],
                name_en=labels["en"],
                name_bn=labels["bn"],
                blend_mg_per_g_protein=round(aa_total_mg[aa] / total_protein, 1),
                digestible_mg_per_g_protein=round(dig_mg, 1),
                reference_mg_per_g_protein=ref_val,
                chemical_ratio=round(chem_ratios[aa], 3),
                digestible_ratio=round(dig_ratio, 3),
                sufficiency_pct=round(dig_ratio * 100.0, 1),
                is_limiting=(aa == limiting_aa),
            )
        )

    lim_labels = AA_LABELS[limiting_aa]
    return BlendScore(
        standard=standard,
        price_tier=price_tier,
        total_mass_g=round(total_mass, 2),
        total_protein_g=round(total_protein, 2),
        carbs_g=round(total_carbs, 2),
        fat_g=round(total_fat, 2),
        fiber_g=round(total_fiber, 2),
        iron_mg=round(total_iron, 2),
        zinc_mg=round(total_zinc, 2),
        cost_bdt=round(total_cost, 2),
        cost_per_20g_protein_bdt=round(total_cost * scale_20, 2),
        cost_per_kg_dry_bdt=round((total_cost / total_mass) * 1000.0, 2),
        co2e_g=round(total_co2e_g, 1),
        co2e_per_20g_protein_g=round(total_co2e_g * scale_20, 1),
        water_l=round(total_water_l, 1),
        water_per_20g_protein_l=round(total_water_l * scale_20, 1),
        chemical_aa_score=chemical_aa_score,
        weighted_digestibility=round(weighted_dig, 3),
        diaas_score=diaas_score,
        pdcaas_score=pdcaas_score,
        active_quality_score=active_quality_score,
        limiting_aa=limiting_aa,
        limiting_aa_label_en=lim_labels["en"],
        limiting_aa_label_bn=lim_labels["bn"],
        is_complete_protein=(active_quality_score >= 1.0),
        amino_acids=aa_breakdown,
        items=items,
        allergens_present=sorted(allergens),
        has_unverified_inputs=bool(unverified_ids),
        unverified_ingredients=unverified_ids,
    )
