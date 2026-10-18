"""
Extraction Stage: Extracts structured entities from raw unstructured claim text.
Implements hybrid deterministic regex extraction + structured entity resolution,
candidate conflict detection, and confidence scoring.
"""

from __future__ import annotations
import os
import json
import re
from typing import Tuple, List, Optional, Dict, Any
from src.models.schemas import ExtractedEntities, LineItem, ClaimState, AuditEntry, WorkflowStatus
from datetime import datetime, timezone
import httpx

class ClaimEntityExtractor:
    """
    Hybrid entity extractor for healthcare & insurance claim documents.
    """

    POLICY_REGEX = re.compile(r'\b(POL-[A-Za-z0-9]{4,10})\b', re.IGNORECASE)
    DOLLAR_REGEX = re.compile(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|\.[0-9]{2}|[0-9]+(?:\.[0-9]{2})?)')
    
    # Key phrase extractors
    NAME_PATTERNS = [
        re.compile(r'(?:Claimant Name|Patient Name|Patient|Claimant)\s*:\s*([A-Za-z\.\-\'\s]+?)(?=\(|\n|$|Policy|Date|DOB|Contact)', re.IGNORECASE),
        re.compile(r'(?:Listed as|Patient Name)\s*:\s*([A-Za-z\.\-\'\s]+?)(?=\(|\n|$)', re.IGNORECASE)
    ]
    
    TOTAL_AMOUNT_PATTERNS = [
        re.compile(r'(?:TOTAL CLAIM AMOUNT|TOTAL CLAIMED AMOUNT|CLAIM AMOUNT REQUESTED|Page 1 Summary Total|Total Claimed)\s*:\s*\$\s*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE),
        re.compile(r'(?:TOTAL)\s*:\s*\$\s*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE)
    ]
    
    DATE_PATTERNS = [
        re.compile(r'(?:Date of Service|Service Date|Date of Incident|Date)\s*:\s*([A-Za-z0-9\s,/\-]+?)(?=\n|$|Healthcare|Provider|Group)', re.IGNORECASE)
    ]

    PROVIDER_PATTERNS = [
        re.compile(r'(?:Healthcare Provider|Provider|Hospital / Provider|Service Provider|Facility)\s*:\s*([A-Za-z0-9\.\,\-\'\s]+?)(?=\n|$|NPI|Attending|Date)', re.IGNORECASE)
    ]

    DIAGNOSIS_PATTERNS = [
        re.compile(r'(?:Primary Diagnosis|Diagnosis Code|Diagnosis)\s*:\s*([A-Za-z0-9\.\-\s\(\)]+?)(?=\n|$|Procedure)', re.IGNORECASE)
    ]

    PROCEDURE_PATTERNS = [
        re.compile(r'(?:Procedure Code|Procedure)\s*:\s*([A-Za-z0-9\.\-\s\(\)\+]+?)(?=\n|$|ITEMIZED|STATEMENT)', re.IGNORECASE)
    ]

    LINE_ITEM_REGEX = re.compile(r'^\s*(?:\d+\.|\-)\s*(.+?)\s*:\s*\$\s*([0-9,]+(?:\.[0-9]{2})?)', re.MULTILINE)

    def extract(self, raw_text: str) -> Tuple[ExtractedEntities, float, List[str]]:
        """
        Extracts structured entities, confidence score, and warnings from raw text.
        """
        warnings: List[str] = []
        confidence: float = 1.0

        # 1. Policy Number Extraction
        # Look for explicit key phrase line first (e.g., "Policy Number: POL-8829104" or "Policy Number: INVALID_9999")
        explicit_pol = re.search(r'(?:Policy Number|Policy ID|Policy #|Policy)\s*:\s*([A-Za-z0-9_\-]+)', raw_text, re.IGNORECASE)
        policy_number: Optional[str] = None
        
        # Helper to check if string is a generic template placeholder like POL-XXXXXXX
        def is_placeholder(val: str) -> bool:
            return bool(re.search(r'POL-[X|Y|0]{4,}', val, re.IGNORECASE))

        if explicit_pol:
            val = explicit_pol.group(1).strip()
            if not is_placeholder(val):
                policy_number = val.upper()
        
        # If no explicit valid policy field found, scan body for valid policy regex matches
        if not policy_number:
            policy_matches = [p.upper() for p in self.POLICY_REGEX.findall(raw_text) if not is_placeholder(p)]
            if policy_matches:
                policy_number = policy_matches[0]
                if len(set(policy_matches)) > 1:
                    warnings.append(f"Multiple policy numbers detected: {list(set(policy_matches))}")
                    confidence -= 0.2
            elif explicit_pol:
                # If explicit match was a placeholder or invalid format, use raw explicit value
                policy_number = explicit_pol.group(1).strip().upper()

        # 2. Claimant Name Extraction
        name_candidates: List[str] = []
        for pattern in self.NAME_PATTERNS:
            matches = pattern.findall(raw_text)
            for m in matches:
                clean_name = m.strip()
                if clean_name and clean_name not in name_candidates:
                    name_candidates.append(clean_name)
        
        claimant_name: Optional[str] = name_candidates[0] if name_candidates else None
        
        # Detect conflicting names in text (e.g. Elena Rostova vs Elena Rostov-Smith)
        if len(name_candidates) > 1:
            warnings.append(f"Conflicting claimant names extracted: {name_candidates}")
            confidence -= 0.25
        elif "Listed as" in raw_text or "variance" in raw_text.lower():
            warnings.append("Discrepancy noted in patient name across document pages")
            confidence -= 0.2

        # 3. Dollar Amounts & Total Extraction
        raw_amounts: List[float] = []
        for m in self.DOLLAR_REGEX.finditer(raw_text):
            val_str = m.group(1).replace(',', '')
            try:
                val = float(val_str)
                raw_amounts.append(val)
            except ValueError:
                pass

        primary_amount: Optional[float] = None
        for pattern in self.TOTAL_AMOUNT_PATTERNS:
            match = pattern.search(raw_text)
            if match:
                try:
                    primary_amount = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    pass
        
        if primary_amount is None and raw_amounts:
            # Fallback to max dollar amount or last mentioned
            primary_amount = max(raw_amounts)

        # Check for conflicting dollar totals (e.g. Page 1 Summary $8,200 vs Page 2 Itemized $12,500)
        summary_totals = re.findall(r'Total\s*:\s*\$\s*([0-9,]+(?:\.[0-9]{2})?)', raw_text, re.IGNORECASE)
        summary_vals = []
        for st in summary_totals:
            try:
                summary_vals.append(float(st.replace(',', '')))
            except ValueError:
                pass
        
        if len(set(summary_vals)) > 1:
            warnings.append(f"Conflicting claim total amounts identified: {[f'${v:,.2f}' for v in set(summary_vals)]}")
            confidence -= 0.35

        # 4. Line Items Extraction
        line_items: List[LineItem] = []
        for match in self.LINE_ITEM_REGEX.finditer(raw_text):
            desc = match.group(1).strip()
            amt_str = match.group(2).replace(',', '')
            try:
                amt = float(amt_str)
                line_items.append(LineItem(description=desc, amount=amt))
            except ValueError:
                pass

        # 5. Metadata fields
        date_match = self.DATE_PATTERNS[0].search(raw_text) if self.DATE_PATTERNS else None
        date_of_service = date_match.group(1).strip() if date_match else None

        provider_match = self.PROVIDER_PATTERNS[0].search(raw_text) if self.PROVIDER_PATTERNS else None
        provider_name = provider_match.group(1).strip() if provider_match else None

        diag_match = self.DIAGNOSIS_PATTERNS[0].search(raw_text) if self.DIAGNOSIS_PATTERNS else None
        diagnosis_code = diag_match.group(1).strip() if diag_match else None

        proc_match = self.PROCEDURE_PATTERNS[0].search(raw_text) if self.PROCEDURE_PATTERNS else None
        procedure_code = proc_match.group(1).strip() if proc_match else None

        entities = ExtractedEntities(
            claimant_name=claimant_name,
            policy_number=policy_number,
            claim_amount=primary_amount,
            date_of_service=date_of_service,
            provider_name=provider_name,
            diagnosis_code=diagnosis_code,
            procedure_code=procedure_code,
            line_items=line_items,
            raw_amount_candidates=raw_amounts,
            raw_name_candidates=name_candidates
        )

        return entities, max(0.1, round(confidence, 2)), warnings

    def try_llm_extract(self, raw_text: str) -> Optional[Tuple[ExtractedEntities, float, List[str]]]:
        """
        Attempts structured entity extraction using OpenAI / LiteLLM API if OPENAI_API_KEY or LLM_API_KEY is configured in environment.
        Returns None if no API key is set or if HTTP request fails.
        """
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None  # Seamless fallback to heuristic engine

        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

        try:
            prompt = f"""You are an enterprise medical insurance claim parser. Extract structured entities from the raw claim text below into a JSON object matching this schema:
{{
  "claimant_name": string or null,
  "policy_number": string or null,
  "claim_amount": number or null,
  "date_of_service": string or null,
  "provider_name": string or null,
  "diagnosis_code": string or null,
  "procedure_code": string or null,
  "line_items": [{{"description": string, "amount": number}}],
  "confidence": number (0.0 to 1.0),
  "warnings": [string]
}}

Raw Claim Text:
{raw_text}

Return ONLY valid JSON with no extra commentary."""
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }

            resp = httpx.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                
                line_items = [LineItem(description=i.get("description", ""), amount=float(i.get("amount", 0))) for i in parsed.get("line_items", [])]
                
                entities = ExtractedEntities(
                    claimant_name=parsed.get("claimant_name"),
                    policy_number=parsed.get("policy_number"),
                    claim_amount=float(parsed.get("claim_amount")) if parsed.get("claim_amount") is not None else None,
                    date_of_service=parsed.get("date_of_service"),
                    provider_name=parsed.get("provider_name"),
                    diagnosis_code=parsed.get("diagnosis_code"),
                    procedure_code=parsed.get("procedure_code"),
                    line_items=line_items
                )
                conf = float(parsed.get("confidence", 0.95))
                warnings = parsed.get("warnings", [])
                return entities, conf, warnings
        except Exception:
            pass  # Fall back to heuristic engine if API call fails

        return None

    def extract_with_provider_fallback(self, raw_text: str) -> Tuple[ExtractedEntities, float, List[str]]:
        """
        Tries LLM extraction first if API key configured, otherwise uses heuristic engine.
        """
        llm_res = self.try_llm_extract(raw_text)
        if llm_res is not None:
            return llm_res
        return self.extract(raw_text)


def process_extraction_stage(state: ClaimState) -> ClaimState:
    """
    Executes the Extraction stage on a ClaimState object.
    Uses live LLM extraction if OPENAI_API_KEY/GEMINI_API_KEY is configured,
    with zero-config heuristic fallback.
    """
    extractor = ClaimEntityExtractor()
    entities, confidence, warnings = extractor.extract_with_provider_fallback(state.raw_text)

    state.extracted_entities = entities
    state.extraction_confidence = confidence
    state.extraction_warnings = warnings
    state.status = WorkflowStatus.PENDING_VALIDATION
    state.updated_at = datetime.now(timezone.utc).isoformat()

    summary_msg = f"Extracted Name: '{entities.claimant_name}', Amount: ${entities.claim_amount or 0:,.2f}, Policy: '{entities.policy_number}' (Confidence: {confidence*100:.0f}%)"
    if warnings:
        summary_msg += f" with {len(warnings)} extraction warnings"

    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="EXTRACTION",
        summary=summary_msg,
        metadata={
            "confidence": confidence,
            "warning_count": len(warnings),
            "line_items_count": len(entities.line_items)
        }
    ))
    return state
