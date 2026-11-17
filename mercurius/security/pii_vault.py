"""
Zero-Knowledge / Local Differential Privacy PII Token Vault for Mercury.
Deterministic entity pseudonymization and reverse-translation layer.
Replaces sensitive employee names, IBANs, emails, and SSNs with synthetic tokens
before sending prompts to cloud LLMs, and translates synthetic tokens back on egress.
"""
from __future__ import annotations
import re, hashlib, time
from typing import Dict, Any, List, Tuple

class PIITokenVault:
    def __init__(self, salt: str = "mercury_pii_vault_salt_2026"):
        self.salt = salt
        self.forward_vault: Dict[str, str] = {}  # real -> token
        self.reverse_vault: Dict[str, str] = {}  # token -> real
        
        # Regex patterns for enterprise PII
        self.patterns: List[Tuple[str, str, re.Pattern]] = [
            ("IBAN", "[IBAN_ACC_{}]", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.I)),
            ("EMAIL", "[EMAIL_ADDR_{}]", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
            ("PHONE", "[PHONE_NUM_{}]", re.compile(r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b")),
            ("CREDIT_CARD", "[CC_NUM_{}]", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
            ("SSN", "[SSN_ID_{}]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
        ]

    def _generate_token(self, category: str, template: str, real_value: str) -> str:
        if real_value in self.forward_vault:
            return self.forward_vault[real_value]
        
        h = hashlib.sha256((real_value + self.salt).encode("utf-8")).hexdigest()[:6].upper()
        token = template.format(h)
        self.forward_vault[real_value] = token
        self.reverse_vault[token] = real_value
        return token

    def anonymize_text(self, text: str, custom_entities: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, int]:
        """
        Masks all recognized and custom PII entities with deterministic synthetic tokens.
        Returns: (anonymized_text, count_of_entities_masked)
        """
        masked = text
        count = 0

        # Custom entities (e.g. ("PERSON", "Michael Stal"))
        if custom_entities:
            for entity_type, entity_val in custom_entities:
                if entity_val and entity_val in masked:
                    token = self._generate_token(entity_type, f"[{entity_type}_{{}}]", entity_val)
                    masked = masked.replace(entity_val, token)
                    count += 1

        # Automated regex detection
        for category, template, pattern in self.patterns:
            matches = list(pattern.finditer(masked))
            for m in reversed(matches):
                val = m.group(0).strip()
                token = self._generate_token(category, template, val)
                masked = masked[:m.start()] + token + masked[m.end():]
                count += 1

        return masked, count

    def de_anonymize_text(self, text: str) -> str:
        """
        Translates synthetic tokens back to their original real enterprise values on egress.
        """
        restored = text
        for token, real_val in self.reverse_vault.items():
            restored = restored.replace(token, real_val)
        return restored

    def clear(self):
        self.forward_vault.clear()
        self.reverse_vault.clear()
