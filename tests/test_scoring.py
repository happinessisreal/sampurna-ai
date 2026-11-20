"""Unit tests for deterministic protein scoring (FAO 2013 DIAAS & WHO 2007 PDCAAS)."""

import pytest

from backend.core.scoring import score_blend


def test_lentil_limited_by_saa_and_rice_limited_by_lysine():
    lentil = score_blend({"red_lentil": 81.3}, standard="fao_2013_diaas")
    assert lentil.limiting_aa == "met_cys"
    assert lentil.diaas_score < 0.70

    rice = score_blend({"white_rice": 281.7}, standard="fao_2013_diaas")
    assert rice.limiting_aa == "lys"
    assert rice.diaas_score < 0.70


def test_lentil_plus_rice_complementarity_improves_score():
    lentil = score_blend({"red_lentil": 81.3}, standard="who_2007_pdcaas")
    rice = score_blend({"white_rice": 281.7}, standard="who_2007_pdcaas")
    # Classic South Asian khichuri complementarity (~40g lentil + 140g rice ~ 20g protein)
    blend = score_blend({"red_lentil": 42.0, "white_rice": 140.0}, standard="who_2007_pdcaas")

    assert blend.chemical_aa_score > lentil.chemical_aa_score
    assert blend.chemical_aa_score > rice.chemical_aa_score
    assert blend.pdcaas_score > lentil.pdcaas_score
    assert blend.pdcaas_score > rice.pdcaas_score


def test_empty_blend_raises_value_error():
    with pytest.raises(ValueError):
        score_blend({})
