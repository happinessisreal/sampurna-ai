"""Unit tests for SciPy LP formulation optimizer and 3D Pareto frontier."""

from backend.core.optimizer import OptimizeRequest, compute_pareto_frontier, optimize_blend


def test_cheapest_and_greenest_modes_satisfy_all_constraints():
    for mode in ("cheapest", "greenest", "most_complete", "balanced", "meat_analogue"):
        res = optimize_blend(
            OptimizeRequest(
                mode=mode,  # type: ignore[arg-type]
                standard="fao_2013_diaas",
                min_score=1.0 if mode != "most_complete" else 0.9,
                excluded_allergens=["peanut"],
            )
        )
        assert res.feasible, f"Mode {mode} failed: {res.diagnostic_hint_en}"
        assert res.score is not None
        assert 19.8 <= res.score.total_protein_g <= 20.2
        assert res.score.total_mass_g <= 250.1
        assert "peanut" not in res.score.allergens_present
        if mode != "most_complete":
            assert res.score.diaas_score >= 0.995
        if mode == "meat_analogue":
            assert "oyster_mushroom" in res.grams_by_id


def test_soy_and_gluten_free_allergen_exclusion():
    res = optimize_blend(
        OptimizeRequest(
            mode="cheapest",
            standard="fao_2013_diaas",
            min_score=1.0,
            excluded_allergens=["soy", "gluten"],
        )
    )
    assert res.feasible, f"Soy+gluten free failed: {res.diagnostic_hint_en}"
    assert res.score is not None
    assert "soy" not in res.score.allergens_present
    assert "gluten" not in res.score.allergens_present
    assert res.score.diaas_score >= 0.995


def test_infeasible_budget_returns_clear_diagnostic():
    res = optimize_blend(
        OptimizeRequest(
            mode="cheapest",
            standard="fao_2013_diaas",
            min_score=1.05,
            max_budget_bdt=1.5,
        )
    )
    assert not res.feasible
    assert res.diagnostic_hint_en is not None
    assert "Minimum cost" in res.diagnostic_hint_en or "Maximum achievable" in res.diagnostic_hint_en


def test_pareto_frontier_returns_non_dominated_knee_point():
    pareto = compute_pareto_frontier(
        OptimizeRequest(
            standard="fao_2013_diaas",
            min_score=0.95,
            excluded_allergens=["peanut"],
        )
    )
    assert pareto.feasible
    assert len(pareto.points) >= 3
    assert pareto.knee_point_id is not None

    # Verify strict non-dominance across all returned Pareto points
    for i, pi in enumerate(pareto.points):
        for j, pj in enumerate(pareto.points):
            if i == j:
                continue
            dominates = (
                pj.cost_bdt <= pi.cost_bdt + 1e-6
                and pj.co2e_g <= pi.co2e_g + 1e-6
                and pj.quality_score >= pi.quality_score - 1e-6
                and (
                    pj.cost_bdt < pi.cost_bdt - 1e-3
                    or pj.co2e_g < pi.co2e_g - 0.1
                    or pj.quality_score > pi.quality_score + 1e-3
                )
            )
            assert not dominates, f"Point {pi.id} is dominated by {pj.id}"
