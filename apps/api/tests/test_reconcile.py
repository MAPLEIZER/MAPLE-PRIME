from app.services.reconcile import Candidate, classify_score, normalize_legal_name, score_candidate


def test_normalize_legal_name():
    assert normalize_legal_name("Ceres Tech Limited") == "ceres tech"
    assert normalize_legal_name("CERES TECH LTD.") == "ceres tech"


def test_exact_name_plus_domain_is_high_confidence():
    left = Candidate("Example Credit Limited", frozenset({"example.co.ke"}))
    right = Candidate("Example Credit Ltd", frozenset({"example.co.ke"}))
    score = score_candidate(left, right)
    assert round(score, 6) >= 0.90
    assert classify_score(score) in {"manual_review", "auto_match_candidate"}


def test_unrelated_entities_do_not_auto_match():
    score = score_candidate(Candidate("Alpha Finance"), Candidate("Beta Technologies"))
    assert classify_score(score) == "unmatched"
