"""
RAG Policy Knowledge Retriever.
Indexes and retrieves insurance policy clauses, coverage guidelines, and exclusion rules
from the enterprise policy document knowledge base (PDFs).
"""

from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from src.models.schemas import PolicyCitation


class PolicyKnowledgeRetriever:
    """
    RAG Retriever querying insurance policy handbooks for coverage rules & exclusions.
    Supports local indexed chunk retrieval with metadata & citations, and optional
    vector search when an LLM / embedding provider is available.
    """

    def __init__(self, knowledge_base_dir: Optional[str | Path] = None):
        if knowledge_base_dir:
            self.kb_dir = Path(knowledge_base_dir)
        else:
            # Resolve relative to project root
            base_path = Path(__file__).resolve().parent.parent.parent
            self.kb_dir = base_path / "knowledge_base" / "policies"

        self.cache_file = self.kb_dir.parent / "policy_chunks_cache.json"
        self.chunks: List[Dict[str, Any]] = []
        self._load_or_build_index()

    def _load_or_build_index(self) -> None:
        """Loads cached chunks or extracts them from PDFs in the knowledge base."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                if self.chunks:
                    return
            except Exception:
                pass

        self._build_index_from_documents()

    def _build_index_from_documents(self) -> None:
        """Extracts text chunks from PDFs in knowledge base directory."""
        self.chunks = []
        if not self.kb_dir.exists():
            return

        try:
            from pypdf import PdfReader
        except ImportError:
            return

        for pdf_path in self.kb_dir.glob("*.pdf"):
            # Avoid re-chunking huge medical bills as policy handbooks
            if "bill" in pdf_path.name.lower():
                continue

            try:
                reader = PdfReader(str(pdf_path))
                for page_idx, page in enumerate(reader.pages):
                    page_num = page_idx + 1
                    raw_text = page.extract_text() or ""
                    
                    # Clean special characters
                    cleaned_text = re.sub(r'[\r\t]', ' ', raw_text)
                    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

                    if not cleaned_text:
                        continue

                    # Identify section headings per page
                    text_lower = cleaned_text.lower()
                    if "general exclusion" in text_lower or (pdf_path.name == "MembershipHandbook.pdf" and page_num in [22, 23]):
                        current_section = "General Exclusions (Section 4)"
                    elif "schedule of surgical" in text_lower:
                        current_section = "Schedule of Surgical Operations"
                    elif "claim procedure" in text_lower or "how to claim" in text_lower:
                        current_section = "Claim Submission & Procedures"
                    elif "glossary of terms" in text_lower:
                        current_section = "Definitions & Glossary"
                    else:
                        current_section = f"{pdf_path.stem} (Page {page_num})"

                    # Split page into logical paragraphs or numbered clauses
                    clauses = re.split(r'(?=\b\d{1,2}\.\s+[A-Z])', cleaned_text)
                    for clause in clauses:
                        clause_str = clause.strip()
                        if len(clause_str) > 40:
                            self.chunks.append({
                                "document_name": pdf_path.name,
                                "page_number": page_num,
                                "section_title": current_section,
                                "text": clause_str
                            })
            except Exception:
                pass

        # Save cache if we extracted chunks
        if self.chunks:
            try:
                self.kb_dir.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.chunks, f, indent=2)
            except Exception:
                pass

    def search(self, query: str, top_k: int = 3) -> List[PolicyCitation]:
        """
        Retrieves the top-k most relevant policy clauses for a given search query.
        Calculates lexical relevance score based on token overlap and phrase matching.
        """
        if not self.chunks:
            self._load_or_build_index()

        if not self.chunks:
            return []

        query_tokens = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
        if not query_tokens:
            return []

        scored_chunks = []
        query_lower = query.lower()

        for chunk in self.chunks:
            text_lower = chunk["text"].lower()
            score = 0.0

            # Exact phrase match boost
            if query_lower in text_lower:
                score += 5.0

            # Token overlap scoring
            for token in query_tokens:
                if token in text_lower:
                    score += 1.0
                    # Additional boost if token appears in section title
                    if token in chunk.get("section_title", "").lower():
                        score += 0.5

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        citations = []
        for score, chunk in scored_chunks[:top_k]:
            excerpt = chunk["text"]
            if len(excerpt) > 300:
                excerpt = excerpt[:297] + "..."

            citations.append(PolicyCitation(
                document_name=chunk["document_name"],
                page_number=chunk["page_number"],
                section_title=chunk["section_title"],
                excerpt=excerpt,
                relevance_score=round(min(1.0, score / 6.0), 2)
            ))

        return citations

    def check_exclusion(
        self,
        raw_text: str,
        diagnosis_code: Optional[str] = None,
        procedure_code: Optional[str] = None
    ) -> Tuple[bool, Optional[PolicyCitation]]:
        """
        Evaluates whether a claim involves an excluded condition, procedure, or policy breach.
        Cross-references with General Exclusions in the Membership Handbook (Pages 22-23).
        """
        combined_text = f"{raw_text} {diagnosis_code or ''} {procedure_code or ''}".lower()

        # Core exclusion patterns mapped to policy handbook sections
        exclusion_patterns = [
            (
                r"\b(alzheimer|dementia|parkinson)\b",
                "MembershipHandbook.pdf",
                23,
                "General Exclusions (Clause 14: Senile Dementia & Parkinson's)",
                "Clause 14. Senile Dementia (including Alzheimer's disease) and Parkinson's disease are strictly excluded under standard scheme benefits."
            ),
            (
                r"\b(hiv|aids|human immunodeficiency)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 8: HIV Infection)",
                "Clause 8. Treatment that commenced during the first five (5) years from Coverage Commencement Date attributable to or consequential upon Human Immunodeficiency Virus (HIV) Infection."
            ),
            (
                r"\b(cosmetic|rhinoplasty|liposuction|breast augmentation)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 5: Cosmetic Surgery)",
                "Clause 5. Any charges in respect of surgical or non-surgical cosmetic treatment (unless necessitated by injury caused by an Accident)."
            ),
            (
                r"\b(pregnancy|maternity|childbirth|abortion|miscarriage|infertility|ivf)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 10: Pregnancy & Maternity)",
                "Clause 10. Treatment relating to pregnancy, including diagnostic tests, childbirth, abortion, miscarriage, or infertility / in-vitro fertilisation."
            ),
            (
                r"\b(substance abuse|drug overdose|alcohol intoxication|self-inflicted)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 11: Substance Abuse & Self-Inflicted Injury)",
                "Clause 11. Misuse or overdose of drugs or being under the influence of alcohol, self-inflicted injuries or attempted suicide."
            ),
            (
                r"\b(holistic|acupuncture|massage therapy|aromatherapy|herbalist|naturopathy)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 13: Alternative Medicine)",
                "Clause 13. Alternative treatment including but not limited to Chinese Medicines treatment, acupuncture, acupressure, massage therapy, and aromatherapy."
            ),
            (
                r"\b(experimental|unproven therapy|investigational procedure|unlisted holistic)\b",
                "MembershipHandbook.pdf",
                23,
                "General Exclusions (Clause 19: Experimental Treatments)",
                "Clause 19. Expenses incurred for experimental or unproven medical technology or procedure not in accordance with accepted medical practice standards."
            ),
            (
                r"\b(pre-existing condition|prior condition)\b",
                "MembershipHandbook.pdf",
                22,
                "General Exclusions (Clause 1: Pre-existing Conditions)",
                "Clause 1. Pre-existing conditions: illness or injury that commenced or presented signs/symptoms prior to the coverage commencement date."
            ),
        ]

        # 1. First check explicit exclusion clauses
        for regex_pattern, doc_name, page, section, clause_text in exclusion_patterns:
            if re.search(regex_pattern, combined_text, re.IGNORECASE):
                citation = PolicyCitation(
                    document_name=doc_name,
                    page_number=page,
                    section_title=section,
                    excerpt=clause_text,
                    relevance_score=1.0
                )
                return True, citation

        # 2. Dynamic RAG search over indexed document chunks if specific diagnosis/procedure code is provided
        query_terms = f"{diagnosis_code or ''} {procedure_code or ''}".strip()
        if query_terms:
            search_results = self.search(query_terms, top_k=3)
            for c in search_results:
                text_low = c.excerpt.lower()
                is_exclusion_chunk = (
                    "general exclusion" in c.section_title.lower()
                    or "shall not cover" in text_low
                    or "not covered" in text_low
                )
                if is_exclusion_chunk and c.relevance_score >= 0.8:
                    return True, c

        return False, None
