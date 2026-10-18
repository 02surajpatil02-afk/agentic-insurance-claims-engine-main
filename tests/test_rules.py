"""
Unit tests for Business Rules Engine.
"""

from src.models.schemas import ClaimState, ExtractedEntities, RuleSeverity
from src.validation.evaluator import RulesEngine


def test_high_value_threshold_trigger():
    engine = RulesEngine()
    
    state = ClaimState(
        claim_id="TEST-001",
        raw_text="Sample text",
        extracted_entities=ExtractedEntities(
            claimant_name="John Doe",
            policy_number="POL-1234567",
            claim_amount=15000.00
        )
    )

    results = engine.evaluate_all(state)
    r105 = next(r for r in results if r.rule_id == "R105")

    assert r105.passed is False
    assert r105.severity == RuleSeverity.ESCALATE
    assert "exceeds the automated threshold limit of $10,000.00" in r105.message


def test_invalid_policy_number_trigger():
    engine = RulesEngine()

    state = ClaimState(
        claim_id="TEST-002",
        raw_text="Sample text",
        extracted_entities=ExtractedEntities(
            claimant_name="Jane Doe",
            policy_number="INVALID_POL_FORMAT",
            claim_amount=2500.00
        )
    )

    results = engine.evaluate_all(state)
    r101 = next(r for r in results if r.rule_id == "R101")

    assert r101.passed is False
    assert r101.severity == RuleSeverity.REJECT
