"""Unit tests for app/services/din_utils.py -- the ONE shared helper pair
that converts between the app's canonical 8-digit DIN form and the SB2
sidecar's token form (Phase 2 spec: "write a unit test for the helper,"
round-trip with leading zeros must be exact)."""
import pytest

from app.services import din_utils


def test_to_sb2_token_strips_leading_zeros():
    assert din_utils.to_sb2_token("00013803") == "DIN13803"


def test_from_sb2_token_zero_pads_to_eight():
    assert din_utils.from_sb2_token("DIN13803") == "00013803"


def test_round_trip_canonical_to_token_to_canonical_preserves_leading_zeros():
    canonical = "00013803"
    token = din_utils.to_sb2_token(canonical)
    assert din_utils.from_sb2_token(token) == canonical


def test_round_trip_token_to_canonical_to_token():
    token = "DIN13803"
    canonical = din_utils.from_sb2_token(token)
    assert din_utils.to_sb2_token(canonical) == token


def test_round_trip_many_leading_zeros():
    # DIN "1" -- the extreme leading-zeros case.
    canonical = "00000001"
    assert din_utils.from_sb2_token(din_utils.to_sb2_token(canonical)) == canonical
    assert din_utils.to_sb2_token(din_utils.from_sb2_token("DIN1")) == "DIN1"


def test_from_sb2_token_case_insensitive_prefix():
    assert din_utils.from_sb2_token("din13803") == "00013803"


def test_to_sb2_token_rejects_non_numeric():
    with pytest.raises(ValueError):
        din_utils.to_sb2_token("ABC12345")


def test_to_sb2_token_rejects_too_long():
    with pytest.raises(ValueError):
        din_utils.to_sb2_token("123456789")


def test_from_sb2_token_rejects_missing_prefix():
    with pytest.raises(ValueError):
        din_utils.from_sb2_token("13803")


def test_from_sb2_token_rejects_empty():
    with pytest.raises(ValueError):
        din_utils.from_sb2_token("")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("00013803", "00013803"),
        ("13803", "00013803"),
        ("DIN13803", "00013803"),
        ("din13803", "00013803"),
        ("  DIN13803  ", "00013803"),
        ("DIN00013803", "00013803"),
    ],
)
def test_normalize_din_accepts_either_form(value, expected):
    assert din_utils.normalize_din(value) == expected


@pytest.mark.parametrize("value", ["", "   ", "ABC12345", "DIN", "DINabc", "123456789", None])
def test_normalize_din_rejects_invalid(value):
    with pytest.raises(ValueError):
        din_utils.normalize_din(value)
