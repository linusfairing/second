import json
from app.models.profile import UserProfile


DIMENSION_WEIGHTS = {
    "values": 0.30,
    "relationship_goals": 0.25,
    "interests": 0.15,
    "personality_traits": 0.15,
    "communication_style": 0.15,
}


def _tokenize(text: str) -> set[str]:
    """Split a string into lowercase word tokens for fuzzy matching."""
    import re
    words = re.split(r'[\s,;/&|]+', text.lower().strip())
    # Strip leading/trailing punctuation from each token
    return {w for w in (re.sub(r'^[^\w]+|[^\w]+$', '', t) for t in words) if w}


def _parse_field(value: str | None) -> set[str]:
    if not value:
        return set()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            tokens: set[str] = set()
            for item in parsed:
                tokens |= _tokenize(str(item))
            return tokens
        if isinstance(parsed, str):
            return _tokenize(parsed)
        if isinstance(parsed, dict):
            tokens = set()
            for v in parsed.values():
                tokens |= _tokenize(str(v))
            return tokens
    except (json.JSONDecodeError, TypeError):
        return _tokenize(value)
    return set()


def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def calculate_compatibility(profile1: UserProfile, profile2: UserProfile) -> float:
    if not profile1 or not profile2:
        return 0.0

    scores = {}
    for dimension, weight in DIMENSION_WEIGHTS.items():
        val1 = getattr(profile1, dimension, None)
        val2 = getattr(profile2, dimension, None)
        set1 = _parse_field(val1)
        set2 = _parse_field(val2)
        if set1 and set2:
            scores[dimension] = jaccard_similarity(set1, set2)

    if not scores:
        return 0.0

    # Renormalize weights for available dimensions
    available_weights = {k: DIMENSION_WEIGHTS[k] for k in scores}
    total_weight = sum(available_weights.values())

    weighted_sum = sum(scores[k] * available_weights[k] for k in scores)
    return weighted_sum / total_weight if total_weight > 0 else 0.0
