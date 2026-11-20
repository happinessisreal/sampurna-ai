"""Deterministic PubChem molecular flavor-bridge & protein functional matrix analyzer."""

from __future__ import annotations

from pydantic import BaseModel

from backend.core.data import load_ingredients, load_molecules


class MoleculeEvidence(BaseModel):
    key: str
    cid: int
    pubchem_url: str
    name: str
    name_bn: str
    formula: str
    mw: float
    role: str
    sensory_note: str
    sensory_note_bn: str
    mitigation: str
    source_ingredients: list[str]
    relative_intensity: float


class FunctionalTraits(BaseModel):
    water_holding: float
    emulsification: float
    gelation: float
    fibrous_anisotropy: float


class SensoryAnalysis(BaseModel):
    epistemic_tier: str = "MODEL_ESTIMATED"
    beany_off_note_risk_pct: float
    umami_synergy_score: float
    maillard_browning_potential: float
    overall_palatability_index: float
    functional_traits: FunctionalTraits
    detected_molecules: list[MoleculeEvidence]
    flavor_bridges_en: list[str]
    flavor_bridges_bn: list[str]
    process_mitigations_en: list[str]
    process_mitigations_bn: list[str]


def analyze_molecular_sensory(grams_by_id: dict[str, float]) -> SensoryAnalysis:
    """Evaluate volatile flavor compounds (PubChem CIDs), umami masking, and texture traits."""
    ingredients = load_ingredients()
    mol_db = load_molecules()
    compounds_meta: dict[str, dict] = mol_db["compounds"]
    profiles: dict[str, dict] = mol_db["ingredient_profiles"]

    cleaned = {k: float(v) for k, v in grams_by_id.items() if float(v) > 1e-6 and k in profiles}
    total_mass = sum(cleaned.values())
    if total_mass <= 1e-6:
        raise ValueError("Cannot analyze molecular profile of an empty blend.")

    beany_raw = 0.0
    umami_raw = 0.0
    maillard_raw = 0.0
    whc = 0.0
    emuls = 0.0
    gel = 0.0
    fibrous = 0.0

    compound_weights: dict[str, float] = {}
    compound_sources: dict[str, list[str]] = {}

    for ing_id, grams in cleaned.items():
        w = grams / total_mass
        prof = profiles[ing_id]
        ing = ingredients[ing_id]

        beany_raw += w * float(prof["beany_load"])
        umami_raw += w * float(prof["umami_load"])
        maillard_raw += w * float(prof["maillard_potential"])

        func = prof["functional"]
        whc += w * float(func["water_holding"])
        emuls += w * float(func["emulsification"])
        gel += w * float(func["gelation"])
        fibrous += w * float(func["fibrous_anisotropy"])

        for c_key in prof["compounds"]:
            compound_weights[c_key] = compound_weights.get(c_key, 0.0) + w
            compound_sources.setdefault(c_key, []).append(ing.name.split(" (")[0])

    # Umami glutamate + 5'-GMP synergy suppresses perceived hexanal off-notes
    has_glutamate = "l_glutamic_acid" in compound_weights
    has_gmp = "gmp" in compound_weights
    has_cys = "l_cysteine" in compound_weights
    has_xylose = "d_xylose" in compound_weights

    umami_boost = 18.0 if (has_glutamate and has_gmp) else 0.0
    umami_score = min(100.0, round(umami_raw * 92.0 + umami_boost, 1))
    maillard_bonus = 10.0 if (has_cys and has_xylose) else 0.0
    maillard_score = min(100.0, round(maillard_raw * 95.0 + maillard_bonus, 1))

    # Effective beany off-note risk drops substantially when umami + Maillard masking are present
    suppression_factor = max(0.32, 1.0 - (umami_score * 0.0042 + maillard_score * 0.0022))
    beany_risk_pct = min(100.0, max(3.0, round(beany_raw * 100.0 * suppression_factor, 1)))

    overall_palatability = min(
        100.0,
        max(
            20.0,
            round(
                0.35 * umami_score
                + 0.25 * maillard_score
                + 0.25 * (fibrous * 100.0)
                + 0.15 * (100.0 - beany_risk_pct),
                1,
            ),
        ),
    )

    detected: list[MoleculeEvidence] = []
    for c_key, weight in sorted(compound_weights.items(), key=lambda kv: kv[1], reverse=True):
        meta = compounds_meta[c_key]
        cid = int(meta["cid"])
        detected.append(
            MoleculeEvidence(
                key=c_key,
                cid=cid,
                pubchem_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                name=meta["name"],
                name_bn=meta["name_bn"],
                formula=meta["formula"],
                mw=float(meta["mw"]),
                role=meta["role"],
                sensory_note=meta["sensory_note"],
                sensory_note_bn=meta["sensory_note_bn"],
                mitigation=meta["mitigation"],
                source_ingredients=compound_sources[c_key],
                relative_intensity=round(min(1.0, weight * 1.4), 2),
            )
        )

    bridges_en: list[str] = []
    bridges_bn: list[str] = []
    mitigations_en: list[str] = []
    mitigations_bn: list[str] = []

    if has_glutamate and has_gmp:
        bridges_en.append("Umami Nucleotide Synergy: L-Glutamic Acid (CID 33032) + Fungal 5'-GMP (CID 135398631) amplify savory depth and mask legume hexanal.")
        bridges_bn.append("উমামি নিউক্লিওটাইড সিনার্জি: L-Glutamic Acid (CID 33032) + মাশরুম 5'-GMP (CID 135398631) মাংসল স্বাদ বাড়িয়ে ডালের কাঁচা গন্ধ ঢেকে দেয়।")
    if has_cys and has_xylose:
        bridges_en.append("Maillard Savory Bridge: L-Cysteine (CID 5862) + D-Xylose (CID 135191) generate meaty 2-Methyl-3-furanthiol (CID 34286) aroma above 140°C.")
        bridges_bn.append("মেইলার্ড স্বাদ-ব্রিজ: L-Cysteine (CID 5862) + D-Xylose (CID 135191) ১৪০°C তাপে মাংসের ঘ্রাণ (2-Methyl-3-furanthiol, CID 34286) তৈরি করে।")
    if not bridges_en:
        bridges_en.append("Grain-Pulse Aroma Bridge: Cereal Strecker aldehydes counterbalance pulse earthiness during dry toasting.")
        bridges_bn.append("শস্য-ডাল ঘ্রাণ ব্রিজ: হালকা ভাজা শস্য ডালের কাঁচা গন্ধ কমিয়ে সুষম স্বাদ আনে।")

    if beany_raw > 0.35:
        mitigations_en.append("Inactivate lipoxygenase (LOX) via 85°C hot-water blanching or 4-min dry pan-roast before grinding to cut Hexanal (CID 6184) generation.")
        mitigations_bn.append("হেক্সানাল (CID 6184) কমাতে রান্নার আগে ডাল/সয়া ৮৫°C গরম পানিতে ব্লাঞ্চ বা ৪ মিনিট শুকনো তাওয়ায় ভেজে নিন (LOX এনজাইম নিষ্ক্রিয় হবে)।")
    if not has_gmp:
        mitigations_en.append("Adding 8–12% dried oyster mushroom (Pleurotus ostreatus) introduces 5'-GMP (CID 135398631) to boost umami and fibrous bite.")
        mitigations_bn.append("উমামি ও মাংসল টেক্সচার বাড়াতে ব্লেন্ডে ৮–১২% শুকনো অয়েস্টার মাশরুম যোগ করা যেতে পারে।")
    if fibrous < 0.55:
        mitigations_en.append("Blend lacks high-anisotropy fiber; best suited for khichuri premix, nuggets, or patties rather than shredded keema unless TVP/jackfruit fiber is added.")
        mitigations_bn.append("এই ব্লেন্ডে ফাইব্রাস আঁশ কম; খিচুড়ি প্রিমিক্স বা নরম প্যাটির জন্য আদর্শ, তবে কিমার জন্য সয়া বড়ি বা কাঁচা কাঁঠাল ফাইবার যুক্ত করুন।")
    else:
        mitigations_en.append("Strong fibrous anisotropy (>55%) supports meat-like keema or burger patty shaping without synthetic methylcellulose binders.")
        mitigations_bn.append("উচ্চ ফাইব্রাস অ্যানাইসোট্রপি (>৫৫%) কৃত্রিম বাইন্ডার ছাড়াই কিমা বা বার্গার প্যাটি গঠনে সহায়ক।")

    return SensoryAnalysis(
        beany_off_note_risk_pct=beany_risk_pct,
        umami_synergy_score=umami_score,
        maillard_browning_potential=maillard_score,
        overall_palatability_index=overall_palatability,
        functional_traits=FunctionalTraits(
            water_holding=round(whc * 100.0, 1),
            emulsification=round(emuls * 100.0, 1),
            gelation=round(gel * 100.0, 1),
            fibrous_anisotropy=round(fibrous * 100.0, 1),
        ),
        detected_molecules=detected,
        flavor_bridges_en=bridges_en,
        flavor_bridges_bn=bridges_bn,
        process_mitigations_en=mitigations_en,
        process_mitigations_bn=mitigations_bn,
    )
