"""
Unit and Integration Tests for RAG Policy Knowledge Base & Retrieval.
"""

import pytest
from src.models.schemas import ClaimState, ExtractedEntities, RuleSeverity
from src.rag.retriever import PolicyKnowledgeRetriever
from src.validation.evaluator import RulesEngine
from src.letters.generator import LetterGenerator


def test_rag_retriever_initialization():
    retriever = PolicyKnowledgeRetriever()
    assert len(retriever.chunks) > 0, "Retriever should load indexed chunks from policy PDFs."


def test_rag_search():
    retriever = PolicyKnowledgeRetriever()
    results = retriever.search("claim submission procedures", top_k=2)
    assert len(results) > 0
    assert results[0].document_name.endswith(".pdf")
    assert results[0].page_number is not None
    assert len(results[0].excerpt) > 10


def test_rag_check_exclusion_alzheimers():
    retriever = PolicyKnowledgeRetriever()
    is_excl, citation = retriever.check_exclusion("Patient diagnosed with Alzheimer's disease.")
    assert is_excl is True
    assert citation is not None
    assert citation.document_name == "MembershipHandbook.pdf"
    assert citation.page_number == 23
    assert "Senile Dementia" in citation.excerpt or "Alzheimer" in citation.excerpt


def test_rag_check_exclusion_cosmetic():
    retriever = PolicyKnowledgeRetriever()
    is_excl, citation = retriever.check_exclusion("Elective rhinoplasty and cosmetic procedure.")
    assert is_excl is True
    assert citation is not None
    assert citation.document_name == "MembershipHandbook.pdf"
    assert citation.page_number == 22


def test_rag_covered_treatment():
    retriever = PolicyKnowledgeRetriever()
    is_excl, citation = retriever.check_exclusion("Emergency fracture repair and plaster cast for broken arm.")
    assert is_excl is False
    assert citation is None


def test_rule_r104_with_rag_citation():
    engine = RulesEngine()

    state = ClaimState(
        claim_id="TEST-RAG-001",
        raw_text="Claimant submitted invoice for experimental unproven therapy treatment.",
        extracted_entities=ExtractedEntities(
            claimant_name="Alice Smith",
            policy_number="POL-9921021",
            claim_amount=1500.00
        )
    )

    results = engine.evaluate_all(state)
    r104 = next(r for r in results if r.rule_id == "R104")

    assert r104.passed is False
    assert r104.severity == RuleSeverity.REJECT
    assert len(r104.citations) > 0
    assert "MembershipHandbook.pdf" in r104.citations[0].document_name
    assert "Clause 19" in r104.citations[0].section_title or "General Exclusions" in r104.citations[0].section_title


def test_rejection_letter_contains_rag_citation():
    engine = RulesEngine()
    generator = LetterGenerator()

    state = ClaimState(
        claim_id="TEST-RAG-002",
        raw_text="Patient diagnosed with Alzheimer's disease and dementia memory care.",
        extracted_entities=ExtractedEntities(
            claimant_name="Robert Taylor",
            policy_number="POL-4455667",
            claim_amount=4200.00
        )
    )

    results = engine.evaluate_all(state)
    state.validation_results = results

    rejection_letter = generator.generate_rejection_letter(state)
    assert "APPLICABLE POLICY PROVISIONS & CITATIONS:" in rejection_letter
    assert "MembershipHandbook.pdf" in rejection_letter
    assert "Page 23" in rejection_letter
