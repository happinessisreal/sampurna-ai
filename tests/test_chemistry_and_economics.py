"""Unit tests for molecular sensory matrix, baselines, and 1,000 kg factory unit economics."""

from backend.core.baselines import compare_to_baselines
from backend.core.chemistry import analyze_molecular_sensory
from backend.core.economics import EconomicsRequest, simulate_factory_economics
from backend.core.optimizer import OptimizeRequest, optimize_blend


def test_mushroom_reduces_beany_off_note_and_adds_pubchem_umami():
    no_mush = analyze_molecular_sensory({"soy_tvp": 25.0, "red_lentil": 20.0})
    with_mush = analyze_molecular_sensory({"soy_tvp": 24.0, "red_lentil": 18.0, "oyster_mushroom": 10.0, "wheat_atta": 6.0})

    cids = {m.cid for m in with_mush.detected_molecules}
    assert 33032 in cids  # L-Glutamic Acid
    assert 135398631 in cids  # 5'-GMP
    assert 6184 in cids  # Hexanal
    assert with_mush.umami_synergy_score > no_mush.umami_synergy_score
    assert with_mush.beany_off_note_risk_pct < no_mush.beany_off_note_risk_pct


def test_baselines_and_factory_economics_savings():
    res = optimize_blend(OptimizeRequest(mode="meat_analogue", min_score=1.0, excluded_allergens=["peanut"]))
    assert res.feasible and res.score is not None

    comps = {c.baseline_id: c for c in compare_to_baselines(res.score)}
    assert comps["chicken_broiler"].cost_change_pct < -40.0
    assert comps["chicken_broiler"].co2e_change_pct < -70.0
    assert comps["beef_boneless"].co2e_change_pct < -95.0

    econ = simulate_factory_economics(
        res.score,
        EconomicsRequest(batch_size_kg=1000.0, wholesale_price_bdt_per_kg=250.0, daily_servings=10000),
    )
    assert econ.servings_per_batch > 10000
    assert econ.gross_margin_pct > 0
    assert econ.annual_bdt_saved_vs_chicken > 10_000_000
    assert econ.annual_co2e_avoided_tonnes_vs_chicken > 500
