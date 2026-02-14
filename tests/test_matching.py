import json
import pytest
from types import SimpleNamespace

from app.services.matching_service import (
    DIMENSION_WEIGHTS,
    _parse_field,
    calculate_compatibility,
    jaccard_similarity,
)


# ---------------------------------------------------------------------------
# Helper to build a profile-like object with given dimension values.
# Uses SimpleNamespace to avoid SQLAlchemy instrumentation issues.
# calculate_compatibility only calls getattr(profile, dim, None) so any
# object with the right attributes works.
# ---------------------------------------------------------------------------
def _make_profile(**kwargs):
    attrs = {dim: kwargs.get(dim) for dim in DIMENSION_WEIGHTS}
    return SimpleNamespace(**attrs)


FULL_PROFILE_DATA = {
    "values": json.dumps(["honesty", "kindness", "growth"]),
    "relationship_goals": json.dumps(["long-term", "marriage"]),
    "interests": json.dumps(["hiking", "reading", "cooking"]),
    "personality_traits": json.dumps(["adventurous", "creative", "empathetic"]),
    "communication_style": json.dumps(["direct", "open"]),
}


# ===== _parse_field unit tests =============================================

class TestParseField:
    def test_none_returns_empty(self):
        assert _parse_field(None) == set()

    def test_empty_string_returns_empty(self):
        assert _parse_field("") == set()

    def test_json_list(self):
        assert _parse_field('["Hiking", "Reading"]') == {"hiking", "reading"}

    def test_json_string(self):
        # Word-level tokenization splits into individual words
        assert _parse_field('"Direct and open"') == {"direct", "and", "open"}

    def test_json_dict(self):
        assert _parse_field('{"a": "Honesty", "b": "Growth"}') == {"honesty", "growth"}

    def test_plain_string_fallback(self):
        assert _parse_field("Long-term relationship") == {"long-term", "relationship"}

    def test_strips_whitespace(self):
        assert _parse_field('["  hiking  ", " reading "]') == {"hiking", "reading"}


# ===== jaccard_similarity unit tests =======================================

class TestJaccardSimilarity:
    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        # intersection={a}, union={a,b,c} → 1/3
        assert jaccard_similarity({"a", "b"}, {"a", "c"}) == pytest.approx(1 / 3)

    def test_empty_first_set(self):
        assert jaccard_similarity(set(), {"a"}) == 0.0

    def test_empty_second_set(self):
        assert jaccard_similarity({"a"}, set()) == 0.0

    def test_both_empty(self):
        assert jaccard_similarity(set(), set()) == 0.0


# ===== calculate_compatibility tests =======================================

class TestIdenticalProfiles:
    """Two identical profiles should score 1.0."""

    def test_full_identical(self):
        p1 = _make_profile(**FULL_PROFILE_DATA)
        p2 = _make_profile(**FULL_PROFILE_DATA)
        assert calculate_compatibility(p1, p2) == pytest.approx(1.0)

    def test_single_dimension_identical(self):
        p1 = _make_profile(values='["honesty"]')
        p2 = _make_profile(values='["honesty"]')
        assert calculate_compatibility(p1, p2) == pytest.approx(1.0)


class TestCompletelyDifferentProfiles:
    """Two profiles with zero overlap should score 0.0."""

    def test_all_dimensions_disjoint(self):
        p1 = _make_profile(
            values='["honesty"]',
            relationship_goals='["long-term"]',
            interests='["hiking"]',
            personality_traits='["adventurous"]',
            communication_style='["direct"]',
        )
        p2 = _make_profile(
            values='["ambition"]',
            relationship_goals='["casual"]',
            interests='["gaming"]',
            personality_traits='["introverted"]',
            communication_style='["reserved"]',
        )
        assert calculate_compatibility(p1, p2) == pytest.approx(0.0)

    def test_single_dimension_disjoint(self):
        p1 = _make_profile(interests='["hiking"]')
        p2 = _make_profile(interests='["gaming"]')
        assert calculate_compatibility(p1, p2) == pytest.approx(0.0)


class TestPartialOverlap:
    """Partial overlap should produce proportional scores."""

    def test_half_overlap_single_dimension(self):
        # intersection={a,b}, union={a,b,c,d} → jaccard=0.5
        p1 = _make_profile(values='["a", "b", "c"]')
        p2 = _make_profile(values='["a", "b", "d"]')
        assert calculate_compatibility(p1, p2) == pytest.approx(0.5)

    def test_mixed_overlap_across_dimensions(self):
        # values: {honesty}∩{honesty,ambition} / {honesty,ambition} = 1/2
        # interests: {hiking,reading}∩{hiking} / {hiking,reading} = 1/2
        p1 = _make_profile(
            values='["honesty"]',
            interests='["hiking", "reading"]',
        )
        p2 = _make_profile(
            values='["honesty", "ambition"]',
            interests='["hiking"]',
        )
        # weights: values=0.30, interests=0.15 → renormalized: 0.30/0.45, 0.15/0.45
        expected = (0.5 * 0.30 + 0.5 * 0.15) / (0.30 + 0.15)
        assert calculate_compatibility(p1, p2) == pytest.approx(expected)

    def test_one_dimension_full_one_zero(self):
        # values: identical → 1.0, interests: disjoint → 0.0
        p1 = _make_profile(values='["honesty"]', interests='["hiking"]')
        p2 = _make_profile(values='["honesty"]', interests='["gaming"]')
        expected = (1.0 * 0.30 + 0.0 * 0.15) / (0.30 + 0.15)
        assert calculate_compatibility(p1, p2) == pytest.approx(expected)

    def test_score_between_zero_and_one(self):
        p1 = _make_profile(**FULL_PROFILE_DATA)
        p2 = _make_profile(
            values='["honesty", "ambition"]',
            relationship_goals='["casual"]',
            interests='["hiking", "gaming"]',
            personality_traits='["adventurous", "introverted"]',
            communication_style='["direct", "reserved"]',
        )
        score = calculate_compatibility(p1, p2)
        assert 0.0 < score < 1.0


class TestMissingDimensionsRenormalized:
    """Missing dimensions should be excluded and weights renormalized."""

    def test_only_values_populated(self):
        p1 = _make_profile(values='["honesty", "kindness"]')
        p2 = _make_profile(values='["honesty", "kindness"]')
        # Only 'values' present → renormalized weight = 1.0, jaccard = 1.0
        assert calculate_compatibility(p1, p2) == pytest.approx(1.0)

    def test_one_side_missing_dimension_excludes_it(self):
        # p1 has values + interests, p2 has only values
        # interests excluded because p2 is empty → only values counts
        p1 = _make_profile(values='["honesty"]', interests='["hiking"]')
        p2 = _make_profile(values='["honesty"]')
        assert calculate_compatibility(p1, p2) == pytest.approx(1.0)

    def test_two_of_five_dimensions(self):
        # Only relationship_goals and communication_style populated
        p1 = _make_profile(
            relationship_goals='["long-term", "marriage"]',
            communication_style='["direct"]',
        )
        p2 = _make_profile(
            relationship_goals='["long-term"]',
            communication_style='["direct", "open"]',
        )
        # relationship_goals: {long-term,marriage}∩{long-term}/{long-term,marriage} = 1/2
        # communication_style: {direct}∩{direct,open}/{direct,open} = 1/2
        rg_w, cs_w = 0.25, 0.15
        expected = (0.5 * rg_w + 0.5 * cs_w) / (rg_w + cs_w)
        assert calculate_compatibility(p1, p2) == pytest.approx(expected)

    def test_renormalized_weights_sum_behavior(self):
        """Identical profiles still score 1.0 regardless of how many dimensions are present."""
        for dim in DIMENSION_WEIGHTS:
            p1 = _make_profile(**{dim: '["x", "y"]'})
            p2 = _make_profile(**{dim: '["x", "y"]'})
            assert calculate_compatibility(p1, p2) == pytest.approx(1.0), f"Failed for dimension: {dim}"


class TestEmptyProfiles:
    """Empty or None profiles should return 0.0 gracefully."""

    def test_both_profiles_none(self):
        assert calculate_compatibility(None, None) == 0.0

    def test_first_profile_none(self):
        p = _make_profile(**FULL_PROFILE_DATA)
        assert calculate_compatibility(None, p) == 0.0

    def test_second_profile_none(self):
        p = _make_profile(**FULL_PROFILE_DATA)
        assert calculate_compatibility(p, None) == 0.0

    def test_all_dimensions_empty_strings(self):
        p1 = _make_profile(values="", interests="", relationship_goals="",
                           personality_traits="", communication_style="")
        p2 = _make_profile(values="", interests="", relationship_goals="",
                           personality_traits="", communication_style="")
        assert calculate_compatibility(p1, p2) == 0.0

    def test_all_dimensions_none(self):
        p1 = _make_profile()
        p2 = _make_profile()
        assert calculate_compatibility(p1, p2) == 0.0

    def test_all_dimensions_empty_json_arrays(self):
        p1 = _make_profile(values="[]", interests="[]", relationship_goals="[]",
                           personality_traits="[]", communication_style="[]")
        p2 = _make_profile(values="[]", interests="[]", relationship_goals="[]",
                           personality_traits="[]", communication_style="[]")
        assert calculate_compatibility(p1, p2) == 0.0
