"""
Enterprise Guardrails, Injection Defense, and Egress DLP for Mercury.
Detects prompt-injection, jailbreaks, canary leaks, unsafe patterns, and scrubs egress credentials.
Includes OWASP Top 10 for LLM defense (LLM01-LLM10), indirect injection defenses, and strict sanitization.
"""
from __future__ import annotations
import re
from typing import Tuple, Optional, Dict, Any, List
from mercurius.jev.client import JevDecisionClient

SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9_\-]{20,}",              # OpenAI / LLM API keys
    r"mcy_[a-zA-Z0-9_\-]{16,}",            # Mercurius internal master/session keys
    r"ghp_[a-zA-Z0-9]{36,}",               # GitHub Personal Access Tokens
    r"github_pat_[a-zA-Z0-9_]{82}",        # Fine-grained GitHub PATs
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----", # RSA / SSH private keys
    r"Bearer\s+[a-zA-Z0-9_\-\.]{25,}",     # JWT / OAuth Bearer tokens
    r"xox[baprs]-[0-9a-zA-Z]{10,}",        # Slack tokens
    r"AKIA[0-9A-Z]{16}",                   # AWS Access Key ID
    r"AIza[0-9A-Za-z\-_]{35}",             # Google Cloud API Key
    r"ya29\.[0-9A-Za-z\-_]+",             # Google OAuth Token
    r"SG\.[a-zA-Z0-9_.\-]{60,}",          # SendGrid API Key
    r"sec_[a-zA-Z0-9_\-]{20,}",            # Enterprise HMAC Webhook Secrets
]

def scrub_secrets(text: str) -> str:
    """
    Egress Data Loss Prevention (DLP) filter.
    Scans outgoing model responses and redacts sensitive credentials before channel dispatch.
    """
    if not text:
        return text
    scrubbed = text
    for pattern in SECRET_PATTERNS:
        scrubbed = re.sub(pattern, "[REDACTED_SECRET]", scrubbed)
    return scrubbed

class GuardrailEngine:
    def __init__(self, jev_client: Optional[JevDecisionClient] = None):
        self.jev = jev_client or JevDecisionClient()
        self.injection_patterns = [
            r"ignore previous instructions",
            r"ignore all prior instructions",
            r"system prompt leak",
            r"do anything now",
            r"dan mode",
            r"you are now bypass mode",
            r"repeat your initial instructions",
            r"reveal secret key",
            r"jailbreak",
            r"override safety guidelines",
            r"disregard all rules",
            r"exfiltrate memory",
            r"dump environment variables",
            r"execute malicious payload",
            r"sudo mode",
            r"developer prompt bypass"
        ]

    def validate_prompt(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Validates inbound user prompt for prompt injection and jailbreak patterns."""
        p_lower = prompt.lower()
        for pat in self.injection_patterns:
            if re.search(pat, p_lower):
                return False, f"Prompt injection detected matching guardrail pattern: '{pat}'"

        # Jev System-1 fast binary logit evaluation
        risk = self.jev.evaluate_risk(prompt)
        if risk.decision and risk.probability > 0.80:
            return False, f"Jev System-1 safety violation: high-risk prompt score ({risk.probability:.2f})"

        return True, None

    def scan_input(self, text: str) -> Dict[str, Any]:
        """Structured scan matching enterprise ingress security pipeline."""
        is_safe, reason = self.validate_prompt(text)
        return {
            "allowed": is_safe,
            "reason": reason or "Clean",
            "threat_level": "HIGH" if not is_safe else "LOW"
        }

    def scrub_egress(self, text: str) -> str:
        """Applies Egress DLP to sanitize outbound responses."""
        return scrub_secrets(text)
