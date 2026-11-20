"""Data loading and Pydantic validation for ingredients, scoring patterns, and molecular profiles."""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

ESSENTIAL_AMINO_ACIDS: tuple[str, ...] = (
    "his",
    "ile",
    "leu",
    "lys",
    "met_cys",
    "phe_tyr",
    "thr",
    "trp",
    "val",
)

AA_LABELS: dict[str, dict[str, str]] = {
    "his": {"en": "Histidine (His)", "bn": "হিস্টিডিন (His)", "short": "His"},
    "ile": {"en": "Isoleucine (Ile)", "bn": "আইসোলিউসিন (Ile)", "short": "Ile"},
    "leu": {"en": "Leucine (Leu)", "bn": "লিউসিন (Leu)", "short": "Leu"},
    "lys": {"en": "Lysine (Lys)", "bn": "লাইসিন (Lys)", "short": "Lys"},
    "met_cys": {"en": "Met + Cys (SAA)", "bn": "মিথিওনিন + সিস্টেইন (SAA)", "short": "SAA"},
    "phe_tyr": {"en": "Phe + Tyr (AAA)", "bn": "ফিনাইলঅ্যালানিন + টাইরোসিন (AAA)", "short": "AAA"},
    "thr": {"en": "Threonine (Thr)", "bn": "থ্রিওনিন (Thr)", "short": "Thr"},
    "trp": {"en": "Tryptophan (Trp)", "bn": "ট্রিপ্টোফ্যান (Trp)", "short": "Trp"},
    "val": {"en": "Valine (Val)", "bn": "ভ্যালিন (Val)", "short": "Val"},
}

PriceTier = Literal["open_market", "tcb_subsidized"]
ScoringStandard = Literal["fao_2013_diaas", "who_2007_pdcaas"]


class Ingredient(BaseModel):
    id: str
    name: str
    name_bn: str
    category: str
    is_baseline: bool
    protein_g_per_100g: float = Field(ge=0.0)
    carbs_g_per_100g: float = Field(ge=0.0)
    fat_g_per_100g: float = Field(ge=0.0)
    fiber_g_per_100g: float = Field(ge=0.0)
    iron_mg_per_100g: float = Field(ge=0.0)
    zinc_mg_per_100g: float = Field(ge=0.0)
    his: float = Field(ge=0.0)
    ile: float = Field(ge=0.0)
    leu: float = Field(ge=0.0)
    lys: float = Field(ge=0.0)
    met_cys: float = Field(ge=0.0)
    phe_tyr: float = Field(ge=0.0)
    thr: float = Field(ge=0.0)
    trp: float = Field(ge=0.0)
    val: float = Field(ge=0.0)
    digestibility_pdcaas: float = Field(gt=0.0, le=1.0)
    diaas_ileal_factor: float = Field(gt=0.0, le=1.3)
    price_bdt_per_kg_open: float = Field(gt=0.0)
    price_bdt_per_kg_tcb: float = Field(gt=0.0)
    co2e_kg_per_kg: float = Field(ge=0.0)
    water_l_per_kg: float = Field(ge=0.0)
    max_share: float = Field(gt=0.0, le=1.0)
    allergens: list[str]
    functional_role: str
    source_nutrition: str
    source_price: str
    source_co2e: str
    verified: bool

    def aa_dict(self) -> dict[str, float]:
        return {aa: float(getattr(self, aa)) for aa in ESSENTIAL_AMINO_ACIDS}

    def price_for_tier(self, tier: PriceTier = "open_market", overrides: dict[str, float] | None = None) -> float:
        if overrides and self.id in overrides:
            return float(overrides[self.id])
        return self.price_bdt_per_kg_tcb if tier == "tcb_subsidized" else self.price_bdt_per_kg_open

    def digestibility_for_standard(self, standard: ScoringStandard = "fao_2013_diaas") -> float:
        return self.diaas_ileal_factor if standard == "fao_2013_diaas" else self.digestibility_pdcaas


class ReferencePattern(BaseModel):
    pattern_id: ScoringStandard
    name: str
    name_bn: str
    his: float
    ile: float
    leu: float
    lys: float
    met_cys: float
    phe_tyr: float
    thr: float
    trp: float
    val: float
    citation: str

    def aa_dict(self) -> dict[str, float]:
        return {aa: float(getattr(self, aa)) for aa in ESSENTIAL_AMINO_ACIDS}


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"true", "1", "yes"}


def _parse_allergens(raw: str) -> list[str]:
    cleaned = raw.strip().lower()
    if not cleaned or cleaned == "none":
        return []
    return [item.strip() for item in cleaned.split("|") if item.strip()]


@lru_cache(maxsize=1)
def load_ingredients() -> dict[str, Ingredient]:
    path = DATA_DIR / "ingredients.csv"
    items: dict[str, Ingredient] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = Ingredient(
                id=row["id"].strip(),
                name=row["name"].strip(),
                name_bn=row["name_bn"].strip(),
                category=row["category"].strip(),
                is_baseline=_parse_bool(row["is_baseline"]),
                protein_g_per_100g=float(row["protein_g_per_100g"]),
                carbs_g_per_100g=float(row["carbs_g_per_100g"]),
                fat_g_per_100g=float(row["fat_g_per_100g"]),
                fiber_g_per_100g=float(row["fiber_g_per_100g"]),
                iron_mg_per_100g=float(row["iron_mg_per_100g"]),
                zinc_mg_per_100g=float(row["zinc_mg_per_100g"]),
                his=float(row["his"]),
                ile=float(row["ile"]),
                leu=float(row["leu"]),
                lys=float(row["lys"]),
                met_cys=float(row["met_cys"]),
                phe_tyr=float(row["phe_tyr"]),
                thr=float(row["thr"]),
                trp=float(row["trp"]),
                val=float(row["val"]),
                digestibility_pdcaas=float(row["digestibility_pdcaas"]),
                diaas_ileal_factor=float(row["diaas_ileal_factor"]),
                price_bdt_per_kg_open=float(row["price_bdt_per_kg_open"]),
                price_bdt_per_kg_tcb=float(row["price_bdt_per_kg_tcb"]),
                co2e_kg_per_kg=float(row["co2e_kg_per_kg"]),
                water_l_per_kg=float(row["water_l_per_kg"]),
                max_share=float(row["max_share"]),
                allergens=_parse_allergens(row["allergens"]),
                functional_role=row["functional_role"].strip(),
                source_nutrition=row["source_nutrition"].strip(),
                source_price=row["source_price"].strip(),
                source_co2e=row["source_co2e"].strip(),
                verified=_parse_bool(row["verified"]),
            )
            items[item.id] = item
    return items


@lru_cache(maxsize=1)
def load_reference_patterns() -> dict[str, ReferencePattern]:
    path = DATA_DIR / "reference_patterns.csv"
    patterns: dict[str, ReferencePattern] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["pattern_id"].strip()
            patterns[pid] = ReferencePattern(
                pattern_id=pid,  # type: ignore[arg-type]
                name=row["name"].strip(),
                name_bn=row["name_bn"].strip(),
                his=float(row["his"]),
                ile=float(row["ile"]),
                leu=float(row["leu"]),
                lys=float(row["lys"]),
                met_cys=float(row["met_cys"]),
                phe_tyr=float(row["phe_tyr"]),
                thr=float(row["thr"]),
                trp=float(row["trp"]),
                val=float(row["val"]),
                citation=row["citation"].strip(),
            )
    return patterns


@lru_cache(maxsize=1)
def load_molecules() -> dict[str, Any]:
    path = DATA_DIR / "molecules.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_plant_ingredients() -> list[Ingredient]:
    return [ing for ing in load_ingredients().values() if not ing.is_baseline]


def list_baseline_ingredients() -> list[Ingredient]:
    return [ing for ing in load_ingredients().values() if ing.is_baseline]
