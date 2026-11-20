"""Deterministic scientific core modules for Sampurna AI."""

from backend.core.data import load_ingredients, load_molecules, load_reference_patterns
from backend.core.scoring import score_blend
from backend.core.optimizer import optimize_blend, compute_pareto_frontier
from backend.core.chemistry import analyze_molecular_sensory
from backend.core.baselines import compare_to_baselines
from backend.core.economics import simulate_factory_economics

__all__ = [
    "load_ingredients",
    "load_molecules",
    "load_reference_patterns",
    "score_blend",
    "optimize_blend",
    "compute_pareto_frontier",
    "analyze_molecular_sensory",
    "compare_to_baselines",
    "simulate_factory_economics",
]
