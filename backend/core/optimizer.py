"""SciPy HiGHS Linear Programming & 3D Pareto Frontier optimizer for protein blends."""

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, Field
from scipy.optimize import linprog

from backend.core.data import (
    ESSENTIAL_AMINO_ACIDS,
    Ingredient,
    PriceTier,
    ScoringStandard,
    list_plant_ingredients,
    load_reference_patterns,
)
from backend.core.scoring import BlendScore, score_blend

OptimizationMode = Literal[
    "cheapest",
    "greenest",
    "most_complete",
    "balanced",
    "meat_analogue",
]

MEAT_ANALOGUE_FIBROUS_IDS = frozenset({"soy_tvp", "oyster_mushroom", "green_jackfruit"})
UMAMI_FUNGI_IDS = frozenset({"oyster_mushroom"})


class OptimizeRequest(BaseModel):
    mode: OptimizationMode = "cheapest"
    standard: ScoringStandard = "fao_2013_diaas"
    price_tier: PriceTier = "open_market"
    min_score: float = Field(default=1.0, ge=0.5, le=1.35)
    max_budget_bdt: float | None = Field(default=None, gt=0.0, le=500.0)
    max_mass_g: float = Field(default=250.0, ge=35.0, le=500.0)
    protein_target_g: float = Field(default=20.0, ge=5.0, le=100.0)
    cost_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    excluded_allergens: list[str] = Field(default_factory=list)
    include_ids: list[str] = Field(default_factory=list)
    exclude_ids: list[str] = Field(default_factory=list)
    price_overrides: dict[str, float] = Field(default_factory=dict)
    min_fibrous_share: float = Field(default=0.35, ge=0.0, le=0.8)


class OptimizeResponse(BaseModel):
    feasible: bool
    mode: OptimizationMode
    message_en: str
    message_bn: str
    grams_by_id: dict[str, float] = Field(default_factory=dict)
    score: BlendScore | None = None
    diagnostic_hint_en: str | None = None
    diagnostic_hint_bn: str | None = None


class ParetoPoint(BaseModel):
    id: str
    cost_bdt: float
    co2e_g: float
    quality_score: float
    total_mass_g: float
    is_knee_point: bool = False
    label_en: str
    label_bn: str
    grams_by_id: dict[str, float]
    score: BlendScore


class ParetoResponse(BaseModel):
    feasible: bool
    standard: ScoringStandard
    price_tier: PriceTier
    points: list[ParetoPoint]
    knee_point_id: str | None = None


def _eligible_ingredients(req: OptimizeRequest) -> tuple[list[Ingredient], list[str]]:
    all_plant = list_plant_ingredients()
    excluded_set = set(req.exclude_ids)
    excluded_allergens = {a.strip().lower() for a in req.excluded_allergens}
    eligible: list[Ingredient] = []
    removed_reasons: list[str] = []

    for ing in all_plant:
        if ing.id in excluded_set:
            removed_reasons.append(f"{ing.name} excluded by user")
            continue
        if excluded_allergens & set(ing.allergens):
            removed_reasons.append(f"{ing.name} excluded due to allergen")
            continue
        eligible.append(ing)
    return eligible, removed_reasons


def _solve_lp(
    eligible: list[Ingredient],
    req: OptimizeRequest,
    *,
    co2e_cap_g: float | None = None,
    override_min_score: float | None = None,
) -> tuple[bool, dict[str, float], str]:
    n = len(eligible)
    if n == 0:
        return False, {}, "All plant ingredients were excluded by allergen or exclusion filters."

    ref = load_reference_patterns()[req.standard]
    target_p = req.protein_target_g
    min_s = req.min_score if override_min_score is None else override_min_score

    # Decision variables: [x_0, ..., x_{n-1}] (grams) + optionally auxiliary score s at index n
    use_aux_s = req.mode == "most_complete"
    num_vars = n + (1 if use_aux_s else 0)

    prot_frac = np.array([ing.protein_g_per_100g / 100.0 for ing in eligible], dtype=float)
    cost_per_g = np.array([ing.price_for_tier(req.price_tier, req.price_overrides) / 1000.0 for ing in eligible], dtype=float)
    co2_per_g = np.array([ing.co2e_kg_per_kg for ing in eligible], dtype=float)
    dig = np.array([ing.digestibility_for_standard(req.standard) for ing in eligible], dtype=float)
    max_shares = np.array([ing.max_share for ing in eligible], dtype=float)

    # Equality constraint: sum(prot_frac_i * x_i) == protein_target_g
    A_eq = np.zeros((1, num_vars), dtype=float)
    A_eq[0, :n] = prot_frac
    b_eq = np.array([target_p], dtype=float)

    ineq_rows: list[np.ndarray] = []
    ineq_rhs: list[float] = []

    # 1. Total mass <= max_mass_g
    row_mass = np.zeros(num_vars, dtype=float)
    row_mass[:n] = 1.0
    ineq_rows.append(row_mass)
    ineq_rhs.append(req.max_mass_g)

    # 2. Palatability share caps: x_i - max_share_i * sum(x_j) <= 0
    for i in range(n):
        r = np.full(num_vars, -max_shares[i], dtype=float)
        if use_aux_s:
            r[n] = 0.0
        r[i] += 1.0
        ineq_rows.append(r)
        ineq_rhs.append(0.0)

    # 3. Forced included ingredients: enforce at least 5% mass share when user pins them
    id_to_idx = {ing.id: i for i, ing in enumerate(eligible)}
    for inc_id in req.include_ids:
        if inc_id not in id_to_idx:
            return False, {}, f"Included ingredient '{inc_id}' conflicts with exclusions or allergens."
        idx = id_to_idx[inc_id]
        r = np.full(num_vars, 0.05, dtype=float)
        if use_aux_s:
            r[n] = 0.0
        r[idx] -= 1.0
        ineq_rows.append(r)
        ineq_rhs.append(0.0)

    # 4. Essential Amino Acid completeness constraints (linearized digestible AA)
    for aa in ESSENTIAL_AMINO_ACIDS:
        ref_val = float(getattr(ref, aa))
        aa_vals = np.array([float(getattr(ing, aa)) for ing in eligible], dtype=float)
        contrib = aa_vals * dig * prot_frac  # mg digestible AA per gram ingredient
        r = np.zeros(num_vars, dtype=float)
        r[:n] = -contrib
        if use_aux_s:
            r[n] = ref_val * target_p
            ineq_rows.append(r)
            ineq_rhs.append(0.0)
        else:
            ineq_rows.append(r)
            ineq_rhs.append(-min_s * ref_val * target_p)

    # 5. Optional max budget constraint
    if req.max_budget_bdt is not None:
        r_bud = np.zeros(num_vars, dtype=float)
        r_bud[:n] = cost_per_g
        ineq_rows.append(r_bud)
        ineq_rhs.append(req.max_budget_bdt)

    # 6. Optional CO2e epsilon cap (used for Pareto sweep)
    if co2e_cap_g is not None:
        r_co2 = np.zeros(num_vars, dtype=float)
        r_co2[:n] = co2_per_g
        ineq_rows.append(r_co2)
        ineq_rhs.append(co2e_cap_g)

    # 7. Meat-Analogue textural scaffold & palatability constraints
    if req.mode == "meat_analogue":
        fib_mask = np.array([1.0 if ing.id in MEAT_ANALOGUE_FIBROUS_IDS else 0.0 for ing in eligible])
        if fib_mask.sum() > 0:
            # sum(fib_i * x_i) >= min_fibrous_share * sum(x_j)
            r_fib = np.full(num_vars, req.min_fibrous_share, dtype=float)
            if use_aux_s:
                r_fib[n] = 0.0
            r_fib[:n] -= fib_mask
            ineq_rows.append(r_fib)
            ineq_rhs.append(0.0)
        # Prevent excessive soy dominance (>50% combined soy+TVP causes chalky/beany flavor)
        soy_mask = np.array([1.0 if ing.id in {"soy_tvp", "soybean_dry"} else 0.0 for ing in eligible])
        if soy_mask.sum() > 0:
            r_soy = np.full(num_vars, -0.50, dtype=float)
            if use_aux_s:
                r_soy[n] = 0.0
            r_soy[:n] += soy_mask
            ineq_rows.append(r_soy)
            ineq_rhs.append(0.0)
        if "oyster_mushroom" in id_to_idx:
            # At least 10% oyster mushroom for umami hexanal masking
            m_idx = id_to_idx["oyster_mushroom"]
            r_mush = np.full(num_vars, 0.10, dtype=float)
            if use_aux_s:
                r_mush[n] = 0.0
            r_mush[m_idx] -= 1.0
            ineq_rows.append(r_mush)
            ineq_rhs.append(0.0)

    # Objective vector c
    c = np.zeros(num_vars, dtype=float)
    if req.mode == "cheapest":
        c[:n] = cost_per_g + 1e-5 * co2_per_g
    elif req.mode == "greenest":
        c[:n] = co2_per_g + 1e-4 * cost_per_g
    elif req.mode == "most_complete":
        c[n] = -1.0
        c[:n] = 1e-4 * cost_per_g
    else:  # balanced or meat_analogue
        # Normalize cost (~15 BDT reference) & carbon (~180 g reference)
        w_c = req.cost_weight
        c[:n] = w_c * (cost_per_g / 0.15) + (1.0 - w_c) * (co2_per_g / 1.8)

    bounds = [(0.0, req.max_mass_g) for _ in range(n)]
    if use_aux_s:
        bounds.append((0.0, 1.5))

    res = linprog(
        c,
        A_ub=np.vstack(ineq_rows),
        b_ub=np.array(ineq_rhs, dtype=float),
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not res.success:
        return False, {}, res.message

    grams = {
        eligible[i].id: round(float(res.x[i]), 2)
        for i in range(n)
        if float(res.x[i]) > 0.25
    }
    if not grams:
        return False, {}, "Solver returned empty formulation."
    return True, grams, "Optimal solution found."


def _diagnose_infeasibility(eligible: list[Ingredient], req: OptimizeRequest) -> tuple[str, str]:
    """Run a quick unconstrained max-completeness check to tell the user exactly why constraints failed."""
    probe_req = req.model_copy(update={"mode": "most_complete", "max_budget_bdt": None})
    ok, grams, _ = _solve_lp(eligible, probe_req)
    if not ok:
        return (
            "No combination satisfies the current allergen/exclusion/mass limits for 20g protein.",
            "বর্তমান অ্যালার্জেন, বাদ দেওয়া উপাদান বা সর্বোচ্চ ওজন সীমার মধ্যে ২০g প্রোটিন তৈরি সম্ভব নয়। অনুগ্রহ করে কিছু সীমা শিথিল করুন।",
        )
    max_score_obj = score_blend(grams, standard=req.standard, price_tier=req.price_tier, price_overrides=req.price_overrides)
    if max_score_obj.active_quality_score + 1e-3 < req.min_score:
        return (
            f"Maximum achievable {req.standard.upper()} score with current filters is {max_score_obj.active_quality_score:.2f} (below requested {req.min_score:.2f}). Lower Min Score or re-enable soy/sesame.",
            f"নির্বাচিত উপাদান দিয়ে সর্বোচ্চ অর্জনযোগ্য প্রোটিন স্কোর {max_score_obj.active_quality_score:.2f} (আপনার লক্ষ্য {req.min_score:.2f}-এর নিচে)। স্কোর কমান বা সয়া/তিল চালু করুন।",
        )
    if req.max_budget_bdt is not None:
        cheap_req = req.model_copy(update={"mode": "cheapest", "max_budget_bdt": None})
        ok_c, grams_c, _ = _solve_lp(eligible, cheap_req)
        if ok_c:
            c_score = score_blend(grams_c, standard=req.standard, price_tier=req.price_tier, price_overrides=req.price_overrides)
            return (
                f"Minimum cost at score {req.min_score:.2f} is ৳{c_score.cost_bdt:.2f} (exceeds budget ৳{req.max_budget_bdt:.2f}). Increase budget or try TCB Subsidized prices.",
                f"{req.min_score:.2f} স্কোরে সর্বনিম্ন খরচ ৳{c_score.cost_bdt:.2f} (বাজেট ৳{req.max_budget_bdt:.2f}-এর বেশি)। বাজেট বাড়ান অথবা TCB ভর্তুকি দর ব্যবহার করুন।",
            )
    return (
        "Constraints conflict (likely forced ingredient shares vs. meat-analogue fiber cap).",
        "শর্তগুলোর মধ্যে সাংঘর্ষিক সীমা তৈরি হয়েছে। অনুগ্রহ করে বাধ্যতামূলক উপাদান বা ফাইবার সীমা সমন্বয় করুন।",
    )


def optimize_blend(req: OptimizeRequest) -> OptimizeResponse:
    """Optimize a plant/fungal protein blend under strict nutritional, palatability, allergen, and cost constraints."""
    eligible, _ = _eligible_ingredients(req)
    ok, grams, _raw_msg = _solve_lp(eligible, req)
    if not ok:
        hint_en, hint_bn = _diagnose_infeasibility(eligible, req)
        return OptimizeResponse(
            feasible=False,
            mode=req.mode,
            message_en="Infeasible formulation under current constraints.",
            message_bn="বর্তমান শর্তাবলীর অধীনে কোনো বৈধ ফর্মুলেশন পাওয়া যায়নি।",
            diagnostic_hint_en=hint_en,
            diagnostic_hint_bn=hint_bn,
        )

    scored = score_blend(
        grams,
        standard=req.standard,
        price_tier=req.price_tier,
        price_overrides=req.price_overrides,
    )
    return OptimizeResponse(
        feasible=True,
        mode=req.mode,
        message_en=f"Found optimal {req.mode} blend ({scored.total_mass_g:.1f}g dry, ৳{scored.cost_bdt:.2f}, {scored.co2e_g:.0f}g CO2e, score {scored.active_quality_score:.2f}).",
        message_bn=f"অপ্টিমাল ব্লেন্ড প্রস্তুত ({scored.total_mass_g:.1f} গ্রাম, ৳{scored.cost_bdt:.2f}, {scored.co2e_g:.0f}g CO₂e, স্কোর {scored.active_quality_score:.2f})।",
        grams_by_id=grams,
        score=scored,
    )


def compute_pareto_frontier(req: OptimizeRequest, num_steps: int = 18) -> ParetoResponse:
    """Compute a 3D non-dominated Pareto frontier (Cost × CO2e × Protein Quality) via epsilon-constraint sweeps."""
    eligible, _ = _eligible_ingredients(req)

    # Anchor 1: Greenest at min_score
    green_req = req.model_copy(update={"mode": "greenest", "max_budget_bdt": None})
    ok_g, grams_g, _ = _solve_lp(eligible, green_req)
    # Anchor 2: Cheapest at min_score
    cheap_req = req.model_copy(update={"mode": "cheapest", "max_budget_bdt": None})
    ok_c, grams_c, _ = _solve_lp(eligible, cheap_req)
    # Anchor 3: Most complete
    comp_req = req.model_copy(update={"mode": "most_complete", "max_budget_bdt": None})
    ok_m, grams_m, _ = _solve_lp(eligible, comp_req)

    if not (ok_g and ok_c):
        return ParetoResponse(feasible=False, standard=req.standard, price_tier=req.price_tier, points=[])

    sg = score_blend(grams_g, req.standard, req.price_tier, req.price_overrides)
    sc = score_blend(grams_c, req.standard, req.price_tier, req.price_overrides)

    candidates: list[tuple[dict[str, float], BlendScore]] = [(grams_g, sg), (grams_c, sc)]
    if ok_m:
        sm = score_blend(grams_m, req.standard, req.price_tier, req.price_overrides)
        candidates.append((grams_m, sm))

    # Sweep CO2e epsilon caps between min CO2e and cheapest CO2e across quality tiers
    co2_min = sg.co2e_g
    co2_max = max(sc.co2e_g, co2_min + 20.0)
    co2_grid = np.linspace(co2_min, co2_max, max(8, num_steps // 2))

    max_q = candidates[-1][1].active_quality_score if ok_m else req.min_score
    score_levels = sorted({round(req.min_score, 3), round(min(max_q, req.min_score + 0.05), 3), round(max_q - 0.01, 3)})

    for s_lvl in score_levels:
        if s_lvl < req.min_score - 1e-4:
            continue
        for cap in co2_grid:
            sweep_req = req.model_copy(update={"mode": "cheapest", "max_budget_bdt": None})
            ok, g_sol, _ = _solve_lp(eligible, sweep_req, co2e_cap_g=float(cap), override_min_score=s_lvl)
            if ok:
                sol_score = score_blend(g_sol, req.standard, req.price_tier, req.price_overrides)
                if req.max_budget_bdt is None or sol_score.cost_bdt <= req.max_budget_bdt + 0.01:
                    candidates.append((g_sol, sol_score))

    # Deduplicate near-identical points and filter strict Pareto non-dominated set
    unique: list[tuple[dict[str, float], BlendScore]] = []
    for g_sol, sol in candidates:
        is_dup = any(
            abs(sol.cost_bdt - u[1].cost_bdt) < 0.08
            and abs(sol.co2e_g - u[1].co2e_g) < 1.5
            and abs(sol.active_quality_score - u[1].active_quality_score) < 0.008
            for u in unique
        )
        if not is_dup:
            unique.append((g_sol, sol))

    non_dominated: list[tuple[dict[str, float], BlendScore]] = []
    for i, (gi, si) in enumerate(unique):
        dominated = False
        for j, (_gj, sj) in enumerate(unique):
            if i == j:
                continue
            better_or_eq = (
                sj.cost_bdt <= si.cost_bdt + 1e-6
                and sj.co2e_g <= si.co2e_g + 1e-6
                and sj.active_quality_score >= si.active_quality_score - 1e-6
            )
            strictly_better = (
                sj.cost_bdt < si.cost_bdt - 1e-3
                or sj.co2e_g < si.co2e_g - 0.1
                or sj.active_quality_score > si.active_quality_score + 1e-3
            )
            if better_or_eq and strictly_better:
                dominated = True
                break
        if not dominated:
            non_dominated.append((gi, si))

    non_dominated.sort(key=lambda pair: (pair[1].cost_bdt, pair[1].co2e_g))

    # Identify Utopia Knee Point in normalized (cost, co2e, -quality) space
    costs = [p[1].cost_bdt for p in non_dominated]
    co2s = [p[1].co2e_g for p in non_dominated]
    quals = [p[1].active_quality_score for p in non_dominated]

    c_min, c_span = min(costs), max(max(costs) - min(costs), 1e-3)
    e_min, e_span = min(co2s), max(max(co2s) - min(co2s), 1e-3)
    q_max, q_span = max(quals), max(max(quals) - min(quals), 1e-3)

    best_idx = 0
    best_dist = float("inf")
    for idx, (_g, sol) in enumerate(non_dominated):
        dc = (sol.cost_bdt - c_min) / c_span
        de = (sol.co2e_g - e_min) / e_span
        dq = (q_max - sol.active_quality_score) / q_span
        dist = dc * dc + de * de + 0.6 * dq * dq
        if dist < best_dist:
            best_dist = dist
            best_idx = idx

    points: list[ParetoPoint] = []
    for idx, (g_sol, sol) in enumerate(non_dominated):
        pid = f"pareto_{idx + 1}"
        is_knee = idx == best_idx
        top_ing = ", ".join(item.name.split(" (")[0] for item in sol.items[:3])
        top_ing_bn = ", ".join(item.name_bn.split(" (")[0] for item in sol.items[:3])
        points.append(
            ParetoPoint(
                id=pid,
                cost_bdt=sol.cost_bdt,
                co2e_g=sol.co2e_g,
                quality_score=sol.active_quality_score,
                total_mass_g=sol.total_mass_g,
                is_knee_point=is_knee,
                label_en=("★ Knee Optimal: " if is_knee else "") + top_ing,
                label_bn=("★ নির্বাচিত ব্যালান্স: " if is_knee else "") + top_ing_bn,
                grams_by_id=g_sol,
                score=sol,
            )
        )

    return ParetoResponse(
        feasible=True,
        standard=req.standard,
        price_tier=req.price_tier,
        points=points,
        knee_point_id=points[best_idx].id if points else None,
    )
