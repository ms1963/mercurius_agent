"""
Semantic Vector Cache and Similarity Engine for Mercurius Agent.
Features:
1. High-speed cosine similarity over normalized dense vectors.
2. Character n-gram hashing and dense term frequency feature embedding with zero external dependencies.
3. Semantic Cache with configurable similarity threshold (e.g. 0.85).
4. Direct TTL expiry and hit/miss observability telemetry.
"""
from __future__ import annotations
import math, time, hashlib, re
from typing import Dict, Any, List, Optional, Tuple

def compute_dense_text_vector(text: str, dim: int = 128) -> List[float]:
    """
    Computes a deterministic, normalized dense vector embedding using
    sub-word character 3-gram feature hashing and term frequency.
    Pure Python: Zero external torch/transformers/numpy dependencies.
    """
    cleaned = re.sub(r"[^\w\s]", "", text.lower()).strip()
    words = cleaned.split()
    vec = [0.0] * dim
    
    if not words:
        return vec

    # Word unigrams and character 3-grams
    tokens = list(words)
    for word in words:
        if len(word) >= 3:
            for i in range(len(word) - 2):
                tokens.append(word[i:i+3])

    for t in tokens:
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[idx] += sign

    # L2 Normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [x / norm for x in vec]
    return vec

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two normalized vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    return sum(a * b for a, b in zip(v1, v2))

class SemanticCacheEntry:
    def __init__(self, key: str, query: str, vector: List[float], response: Any, ttl_sec: float):
        self.key = key
        self.query = query
        self.vector = vector
        self.response = response
        self.created_at = time.time()
        self.ttl_sec = ttl_sec

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_sec

class SemanticCache:
    """
    Semantic Vector Cache that intercepts prompts or tool inputs and returns
    cached outputs when cosine similarity exceeds similarity_threshold.
    """
    def __init__(self, similarity_threshold: float = 0.88, default_ttl_sec: float = 3600.0):
        self.similarity_threshold = similarity_threshold
        self.default_ttl_sec = default_ttl_sec
        self.entries: List[SemanticCacheEntry] = []
        self.stats = {"hits": 0, "misses": 0, "entries": 0}

    def get(self, query: str) -> Optional[Tuple[Any, float]]:
        """Look up query. Returns (response, similarity_score) if semantic hit found, else None."""
        self._purge_expired()
        q_vec = compute_dense_text_vector(query)
        
        best_entry: Optional[SemanticCacheEntry] = None
        best_sim: float = -1.0

        for entry in self.entries:
            sim = cosine_similarity(q_vec, entry.vector)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        if best_entry and best_sim >= self.similarity_threshold:
            self.stats["hits"] += 1
            return best_entry.response, best_sim

        self.stats["misses"] += 1
        return None

    def set(self, query: str, response: Any, ttl_sec: Optional[float] = None):
        """Stores query, embedding vector, and response in cache."""
        self._purge_expired()
        ttl = ttl_sec or self.default_ttl_sec
        vec = compute_dense_text_vector(query)
        entry = SemanticCacheEntry(
            key=hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
            query=query,
            vector=vec,
            response=response,
            ttl_sec=ttl
        )
        self.entries.append(entry)
        self.stats["entries"] = len(self.entries)

    def _purge_expired(self):
        self.entries = [e for e in self.entries if not e.is_expired()]
        self.stats["entries"] = len(self.entries)

    def clear(self):
        self.entries.clear()
        self.stats = {"hits": 0, "misses": 0, "entries": 0}
