"""Official Model Context Protocol (MCP) Server exposing Sampurna AI formulation tools."""

from __future__ import annotations

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover — fallback for mcp<2
    from mcp.server.fastmcp import FastMCP as MCPServer

from backend.agent.rag import search_literature as rag_search
from backend.core.chemistry import analyze_molecular_sensory as core_chemistry
from backend.core.data import PriceTier, ScoringStandard
from backend.core.optimizer import (
    OptimizationMode,
    OptimizeRequest,
    compute_pareto_frontier as core_pareto,
    optimize_blend as core_optimize,
)
from backend.core.report import generate_impact_report as core_report

mcp = MCPServer("sampurna-formulation-mcp")


@mcp.tool()
def optimize_protein_blend(
    mode: OptimizationMode = "cheapest",
    standard: ScoringStandard = "fao_2013_diaas",
    price_tier: PriceTier = "open_market",
    min_score: float = 1.0,
    max_budget_bdt: float | None = None,
    excluded_allergens: list[str] | None = None,
    include_ids: list[str] | None = None,
) -> dict:
    """Optimize a 20g complete plant/fungal protein blend via deterministic SciPy HiGHS LP."""
    res = core_optimize(
        OptimizeRequest(
            mode=mode,
            standard=standard,
            price_tier=price_tier,
            min_score=min_score,
            max_budget_bdt=max_budget_bdt,
            excluded_allergens=excluded_allergens or [],
            include_ids=include_ids or [],
        )
    )
    return res.model_dump()


@mcp.tool()
def compute_pareto_frontier(
    standard: ScoringStandard = "fao_2013_diaas",
    price_tier: PriceTier = "open_market",
    min_score: float = 0.95,
    excluded_allergens: list[str] | None = None,
) -> dict:
    """Compute non-dominated Cost × CO2e × Protein Quality Pareto-optimal formulations."""
    res = core_pareto(
        OptimizeRequest(
            standard=standard,
            price_tier=price_tier,
            min_score=min_score,
            excluded_allergens=excluded_allergens or [],
        )
    )
    return res.model_dump()


@mcp.tool()
def analyze_molecular_sensory(grams_by_id: dict[str, float]) -> dict:
    """Analyze PubChem volatile compounds (hexanal risk, glutamate/GMP umami, Maillard) and texture traits."""
    return core_chemistry(grams_by_id).model_dump()


@mcp.tool()
def search_food_literature(query: str, top_k: int = 3) -> list[dict]:
    """Search verified open-access food-science papers (PMC/FAO/Science DOIs) for texture and flavor masking."""
    return [hit.model_dump() for hit in rag_search(query, top_k=top_k)]


@mcp.tool()
def generate_impact_report(
    product_name: str,
    product_format: str,
    target_customer: str,
    grams_by_id: dict[str, float],
) -> str:
    """Generate a data-backed Markdown Impact Report with baseline comparisons and epistemic provenance."""
    return core_report(
        product_name=product_name,
        product_format=product_format,
        target_customer=target_customer,
        grams_by_id=grams_by_id,
    )


def get_mcp_manifest() -> dict:
    """Return structured MCP tool metadata for the UI and external MCP clients."""
    tools = [
        {
            "name": "optimize_protein_blend",
            "description": "SciPy HiGHS LP formulation optimizer across 14 local ingredients and 9 essential amino acids.",
            "args": ["mode", "standard", "price_tier", "min_score", "max_budget_bdt", "excluded_allergens", "include_ids"],
        },
        {
            "name": "compute_pareto_frontier",
            "description": "3D Cost × CO2e × DIAAS Pareto frontier generator with Utopia knee-point selector.",
            "args": ["standard", "price_tier", "min_score", "excluded_allergens"],
        },
        {
            "name": "analyze_molecular_sensory",
            "description": "PubChem CID volatile off-note (Hexanal) vs. Umami (5'-GMP + Glu) & Maillard chemistry engine.",
            "args": ["grams_by_id"],
        },
        {
            "name": "search_food_literature",
            "description": "TF-IDF cosine RAG retriever over 10 verified open-access food science papers with DOIs.",
            "args": ["query", "top_k"],
        },
        {
            "name": "generate_impact_report",
            "description": "Deterministic Markdown Impact Report generator comparing vs. chicken, beef, egg, fish, and lentils.",
            "args": ["product_name", "product_format", "target_customer", "grams_by_id"],
        },
    ]
    return {
        "server_name": "sampurna-formulation-mcp",
        "transport": "stdio / FastMCP",
        "command": "uv run python -m backend.mcp_server",
        "tool_count": len(tools),
        "tools": tools,
    }


if __name__ == "__main__":
    mcp.run()
