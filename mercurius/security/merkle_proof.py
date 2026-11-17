"""
Cryptographic Proof of Autonomous Reasoning & Merkle Execution Trees for Mercury.
Generates a verifiable Merkle Tree of agent reasoning steps, tool calls, and guardrail validations,
producing a standalone, tamper-evident .mercury-proof certificate.
"""
from __future__ import annotations
import hashlib, json, time
from typing import Dict, Any, List, Optional

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

class MerkleNode:
    def __init__(self, left: Optional[MerkleNode], right: Optional[MerkleNode], hash_val: str):
        self.left = left
        self.right = right
        self.hash_val = hash_val

class MerkleExecutionTree:
    def __init__(self, session_id: str = "mercury_exec"):
        self.session_id = session_id
        self.leaves: List[str] = []
        self.audit_steps: List[Dict[str, Any]] = []

    def record_step_hash(self, step_name: str, payload: Dict[str, Any]) -> str:
        canonical = json.dumps({"step": step_name, "payload": payload, "ts": time.time()}, sort_keys=True)
        h = sha256_hash(canonical)
        self.leaves.append(h)
        self.audit_steps.append({"step": step_name, "hash": h, "payload": payload})
        return h

    def compute_merkle_root(self) -> str:
        if not self.leaves:
            return sha256_hash("EMPTY_EXECUTION_TREE")

        current_level = list(self.leaves)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = sha256_hash(left + right)
                next_level.append(combined)
            current_level = next_level

        return current_level[0]

    def export_proof_certificate(self, agent_id: str = "mercury_v2.4") -> Dict[str, Any]:
        root = self.compute_merkle_root()
        return {
            "version": "1.0.0",
            "format": "mercury-proof",
            "agent_id": agent_id,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "merkle_root": root,
            "total_steps": len(self.leaves),
            "step_hashes": list(self.leaves),
            "audit_steps": self.audit_steps
        }

    @staticmethod
    def verify_proof_certificate(cert: Dict[str, Any]) -> bool:
        """Verifies mathematical consistency of the exported Merkle proof certificate."""
        leaves = cert.get("step_hashes", [])
        if not leaves:
            return cert.get("merkle_root") == sha256_hash("EMPTY_EXECUTION_TREE")

        current_level = list(leaves)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = sha256_hash(left + right)
                next_level.append(combined)
            current_level = next_level

        return current_level[0] == cert.get("merkle_root")
