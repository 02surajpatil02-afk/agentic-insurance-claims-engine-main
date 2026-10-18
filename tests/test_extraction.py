"""
Unit tests for Entity Extractor.
"""

from pathlib import Path
from src.extraction.extractor import ClaimEntityExtractor


def test_extraction_clean_approve():
    sample_file = Path("sample_claims/clean_approve.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Sarah Jenkins"
    assert entities.policy_number == "POL-8829104"
    assert entities.claim_amount == 3450.00
    assert confidence == 1.0
    assert len(warnings) == 0


def test_extraction_over_threshold():
    sample_file = Path("sample_claims/over_threshold.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Robert T. Chen"
    assert entities.policy_number == "POL-4401928"
    assert entities.claim_amount == 45200.00
    assert len(entities.line_items) == 3


def test_extraction_conflicting_data():
    sample_file = Path("sample_claims/conflicting_data.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Elena Rostova"
    assert entities.policy_number == "POL-5539201"
    assert len(warnings) > 0  # Should detect name variance & conflicting amounts
    assert confidence < 1.0


def test_extraction_clean_reject():
    sample_file = Path("sample_claims/clean_reject.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Marcus Vance"
    assert entities.policy_number == "INVALID_9999"  # Must NOT be decoy POL-XXXXXXX placeholder!
    assert entities.claim_amount == 0.0


def test_llm_extractor_prompt_formatting_and_fallback(monkeypatch):
    """
    Ensures that when OPENAI_API_KEY is set, try_llm_extract formats the prompt correctly
    (no f-string unescaped brace ValueError) and falls back cleanly if API is unavailable.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    extractor = ClaimEntityExtractor()
    
    # Should not raise ValueError format specifier exception
    entities, confidence, warnings = extractor.extract_with_provider_fallback("Sample text with Policy Number: POL-1234567")
    assert entities.policy_number == "POL-1234567"


def test_extraction_policy_renewal_conflict():
    sample_file = Path("sample_claims/policy_renewal_conflict.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Diane Okafor"
    assert entities.policy_number == "POL-7734410"
    assert entities.claim_amount == 10050.75
    assert confidence == 1.0


def test_extraction_multiple_policy_refs():
    sample_file = Path("sample_claims/multiple_policy_refs.txt")
    assert sample_file.exists()
    
    with open(sample_file, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract(text)

    assert entities.claimant_name == "Miguel Santos"
    assert entities.claim_amount == 640.00
    assert len(warnings) == 1
    assert "Multiple policy numbers detected" in warnings[0]
    assert confidence == 0.8



