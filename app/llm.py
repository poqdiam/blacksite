"""
app/llm.py — BLACKSITE LLM Integration Module

Provides RAG-based GRC assistant using a configurable LLM backend.
Supports Ollama (local), OpenAI-compatible API, and Anthropic.

Architecture:
  1. Query arrives from chat endpoint with user context
  2. Context is assembled: system prompt + role-specific additions + runtime snapshots
  3. RAG retrieves relevant knowledge chunks (BM25 search over knowledge base)
  4. Few-shot examples are selected for the query type
  5. Full prompt is assembled and sent to the LLM backend
  6. Response is returned with source citations

Usage:
  from app.llm import LLMEngine
  engine = LLMEngine()
  response = await engine.ask(query="What is AC-2?", user_context={...})
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml

logger = logging.getLogger("blacksite.llm")

# ---------------------------------------------------------------------------
# GRC Topic Filter
# ---------------------------------------------------------------------------

# Terms that signal a GRC-related query (broad — false negatives are worse than false positives)
_GRC_KEYWORDS: frozenset = frozenset([
    # Frameworks & standards
    "rmf", "nist", "fedramp", "fisma", "hipaa", "cmmc", "soc2", "soc 2", "iso27001", "iso 27001",
    "pci", "gdpr", "csf", "fips", "disa", "dod", "oscal", "ato", "dato",
    # Documents & artifacts
    "ssp", "poam", "poa&m", "sar", "rar", "cto", "conmon", "iscp", "bcp", "coop",
    "authorization", "accreditation", "certification", "assessment", "audit",
    "control", "baseline", "overlay", "tailoring", "inheritance", "implementation",
    "narrative", "evidence", "artifact", "finding", "weakness", "deviation", "waiver",
    "milestone", "remediation", "closure", "risk acceptance",
    # Roles
    "isso", "issm", "sca", "ao", "ciso", "authorizing official", "system owner",
    "security officer", "assessor", "privacy officer",
    # Security concepts
    "vulnerability", "scan", "patch", "cvss", "cve", "acas", "nessus", "openscap",
    "access control", "account management", "audit log", "configuration management",
    "incident", "contingency", "recovery", "continuity", "bcdr",
    "encryption", "cryptography", "pki", "mfa", "multifactor", "authentication",
    "boundary", "categorization", "impact level", "cia triad",
    "confidentiality", "integrity", "availability",
    "penetration test", "pentest", "red team",
    # NIST control families (any two-letter family prefix)
    " ac-", " au-", " ca-", " cm-", " cp-", " ia-", " ir-", " ma-", " mp-",
    " pe-", " pl-", " pm-", " ps-", " pt-", " ra-", " sa-", " sc-", " si-", " sr-",
    "ac ", "au ", "ca ", "cm ", "cp ", "ia ", "ir ", "ma ", "mp ",
    "pe ", "pl ", "pm ", "ps ", "pt ", "ra ", "sa ", "sc ", "si ", "sr ",
    # BLACKSITE platform
    "blacksite", "daily ops", "logbook", "control narrative",
    # General compliance
    "compliance", "regulation", "policy", "procedure", "privacy", "breach",
    "safeguard", "security plan", "risk management", "risk assessment",
])

# Phrases that strongly signal off-topic intent (checked after keyword miss)
_OFF_TOPIC_SIGNALS: tuple = (
    "write me a", "write a poem", "tell me a joke", "recipe for", "cook ",
    "sports", "weather", "stock price", "movie", "song lyrics", "translate ",
    "what is the capital", "who won", "how do i fix my car", "javascript tutorial",
    "python tutorial", "how to code", "write code for", "debug my",
)

_GRC_REFUSAL = (
    "I'm specialized in GRC compliance and BLACKSITE workflows only. "
    "I can't help with that topic, but I can assist you with RMF processes, "
    "NIST SP 800-53 controls, POA&M management, FedRAMP compliance, or any "
    "BLACKSITE feature. What GRC question can I answer?"
)


def _is_grc_query(query: str) -> bool:
    """
    Returns True if the query appears GRC-related.
    Uses keyword presence as the primary signal; falls back to checking
    for explicit off-topic phrases. Errs on the side of allowing ambiguous queries
    through to let the system prompt handle them.
    """
    q_lower = query.lower()

    # Fast pass: any GRC keyword present → allow through
    for kw in _GRC_KEYWORDS:
        if kw in q_lower:
            return True

    # Check for explicit off-topic signals only when no GRC keywords found
    for phrase in _OFF_TOPIC_SIGNALS:
        if phrase in q_lower:
            return False

    # Short queries with no GRC signal but no explicit off-topic signal:
    # allow through — the system prompt handles them
    if len(query.split()) < 8:
        return True

    # Longer query with no GRC signal at all → treat as off-topic
    return False


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).resolve().parent   # resolve() follows symlinks → always real blacksite/app/
_REPO_ROOT = _APP_DIR.parent
_LLM_DIR = _REPO_ROOT / "llm"
_CONFIG_PATH = _LLM_DIR / "config" / "llm_config--model-rag-endpoint-settings.yaml"
_KNOWLEDGE_DIR = _LLM_DIR / "knowledge"
_RUNTIME_DIR = _LLM_DIR / "runtime"
_PROMPTS_DIR = _LLM_DIR / "prompts"

# ---------------------------------------------------------------------------
# BM25 implementation (no external deps required)
# ---------------------------------------------------------------------------

class BM25:
    """Minimal BM25 retriever. k1=1.5, b=0.75."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[str] = []
        self.doc_ids: List[str] = []
        self.idf: Dict[str, float] = {}
        self.tf: List[Dict[str, int]] = []
        self.avgdl: float = 0.0
        self.N: int = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9\-_]+", text.lower())

    def index(self, documents: List[str], doc_ids: List[str]) -> None:
        self.corpus = documents
        self.doc_ids = doc_ids
        self.N = len(documents)

        # Term frequencies per document
        self.tf = []
        df: Dict[str, int] = defaultdict(int)
        total_len = 0
        for doc in documents:
            tokens = self._tokenize(doc)
            total_len += len(tokens)
            freq: Dict[str, int] = defaultdict(int)
            for t in tokens:
                freq[t] += 1
            self.tf.append(dict(freq))
            for t in set(freq):
                df[t] += 1

        self.avgdl = total_len / max(self.N, 1)

        # IDF
        for term, n in df.items():
            self.idf[term] = math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def search(self, query: str, top_k: int = 6) -> List[Tuple[str, float]]:
        """Return (doc_id, score) sorted by descending score."""
        q_terms = self._tokenize(query)
        scores: Dict[str, float] = defaultdict(float)

        for i, tf_doc in enumerate(self.tf):
            dl = sum(tf_doc.values())
            for term in q_terms:
                if term not in tf_doc:
                    continue
                idf = self.idf.get(term, 0.0)
                tf_val = tf_doc[term]
                num = tf_val * (self.k1 + 1)
                denom = tf_val + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[self.doc_ids[i]] += idf * (num / denom)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


# ---------------------------------------------------------------------------
# Knowledge Base Loader
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """Loads and chunks knowledge base documents for RAG retrieval."""

    def __init__(self, knowledge_dir: Path, runtime_dir: Path, chunk_size: int = 1000, overlap: int = 200):
        self.knowledge_dir = knowledge_dir
        self.runtime_dir = runtime_dir
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[str] = []
        self.chunk_ids: List[str] = []
        self.chunk_meta: List[Dict[str, Any]] = []
        self.bm25 = BM25()
        self._loaded = False
        self._excluded_dirs: set = set()   # framework short_names whose knowledge dirs are suppressed

    def _chunk_text(self, text: str, source: str) -> List[Tuple[str, Dict]]:
        """Split text into overlapping chunks."""
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 2 > self.chunk_size:
                if current.strip():
                    chunks.append(current.strip())
                # Keep overlap from end of current chunk
                if self.overlap > 0 and current:
                    overlap_text = current[-self.overlap:]
                    current = overlap_text + "\n\n" + para
                else:
                    current = para
            else:
                current = (current + "\n\n" + para).strip()
        if current.strip():
            chunks.append(current.strip())

        result = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{source}::{i}"
            meta = {
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "char_count": len(chunk),
            }
            result.append((chunk, meta))
        return result

    def load(self) -> None:
        """Load all knowledge base documents and build BM25 index."""
        if self._loaded:
            return

        self.chunks = []
        self.chunk_ids = []
        self.chunk_meta = []

        # Load knowledge base markdown/txt files
        if self.knowledge_dir.exists():
            for path in sorted(self.knowledge_dir.rglob("*")):
                if path.suffix not in (".md", ".txt", ".json"):
                    continue
                if path.stat().st_size > 5 * 1024 * 1024:  # Skip files > 5MB
                    continue
                # Skip any path component that matches a disabled framework short_name
                if self._excluded_dirs:
                    rel_parts = set(path.relative_to(self.knowledge_dir).parts)
                    if rel_parts & self._excluded_dirs:
                        continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    if path.suffix == ".json":
                        # Extract text content from JSON knowledge docs
                        try:
                            data = json.loads(text)
                            text = json.dumps(data, indent=2)[:50000]  # Cap at 50K chars
                        except Exception:
                            pass
                    rel_path = str(path.relative_to(self.knowledge_dir))
                    for chunk, meta in self._chunk_text(text, rel_path):
                        self.chunks.append(chunk)
                        self.chunk_ids.append(f"kb::{rel_path}::{meta['chunk_index']}")
                        self.chunk_meta.append(meta)
                except Exception as e:
                    logger.warning(f"Failed to load knowledge file {path}: {e}")

        # Load runtime snapshots
        if self.runtime_dir.exists():
            for path in self.runtime_dir.glob("*.json"):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    rel_path = f"runtime/{path.name}"
                    for chunk, meta in self._chunk_text(text, rel_path):
                        self.chunks.append(chunk)
                        self.chunk_ids.append(f"runtime::{path.stem}::{meta['chunk_index']}")
                        self.chunk_meta.append(meta)
                except Exception as e:
                    logger.warning(f"Failed to load runtime snapshot {path}: {e}")

        logger.info(f"Knowledge base loaded: {len(self.chunks)} chunks from {self.knowledge_dir}")
        self.bm25.index(self.chunks, self.chunk_ids)
        self._loaded = True

    def search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """Search knowledge base and return top chunks with metadata."""
        if not self._loaded:
            self.load()
        results = self.bm25.search(query, top_k=top_k)
        output = []
        for chunk_id, score in results:
            if score < 0.05:
                continue
            idx = self.chunk_ids.index(chunk_id)
            output.append({
                "chunk_id": chunk_id,
                "score": round(score, 4),
                "content": self.chunks[idx],
                "meta": self.chunk_meta[idx],
            })
        return output

    def reload(self) -> None:
        """Force reload of knowledge base (after knowledge update)."""
        self._loaded = False
        self.load()

    def reload_with_exclusions(self, excluded_dirs: set) -> None:
        """
        Reload knowledge base excluding directories whose name matches any entry
        in excluded_dirs (matched against each path component, not full path).
        Used by OrgEnabledFramework disable/enable to keep LLM scoped to
        only the frameworks the org has active.
        """
        self._excluded_dirs = set(excluded_dirs)
        self._loaded = False
        self.load()


# ---------------------------------------------------------------------------
# LLM Backend Clients
# ---------------------------------------------------------------------------

class OllamaClient:
    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.1:8b")
        self.options = config.get("options", {})

    async def complete(self, messages: List[Dict], timeout: int = 180) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": -1,   # Keep model resident in RAM indefinitely (eliminates 7-8s cold-load)
            "options": self.options,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class OpenAIClient:
    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4o-mini")
        self.options = config.get("options", {})
        api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")

    async def complete(self, messages: List[Dict], timeout: int = 180) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            **self.options,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            if not resp.is_success:
                logger.error(f"OpenAI/Groq API error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        return bool(self.api_key)


class AnthropicClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "claude-haiku-4-5-20251001")
        self.options = config.get("options", {})
        api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")

    async def complete(self, messages: List[Dict], timeout: int = 180) -> str:
        # Extract system message from messages list
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_messages.append(m)

        payload = {
            "model": self.model,
            "max_tokens": self.options.get("max_tokens", 1024),
            "system": system,
            "messages": chat_messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# LLM Engine
# ---------------------------------------------------------------------------

class LLMEngine:
    """Main BLACKSITE LLM integration engine."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or _CONFIG_PATH
        self._config: Dict = {}
        self._client = None
        self._kb: Optional[KnowledgeBase] = None
        self._few_shot: List[Dict] = []
        self._base_prompt: str = ""
        self._role_prompts: Dict[str, str] = {}
        self._ready = False

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            logger.warning(f"LLM config not found at {self._config_path}, using defaults")
            return {
                "backend": "ollama",
                "ollama": {"base_url": "http://localhost:11434", "model": "llama3.1:8b"},
            }
        with self._config_path.open() as f:
            return yaml.safe_load(f) or {}

    def _build_client(self, config: dict):
        backend = config.get("backend", "ollama")
        if backend == "ollama":
            return OllamaClient(config.get("ollama", {}))
        elif backend == "openai":
            return OpenAIClient(config.get("openai", {}))
        elif backend == "anthropic":
            return AnthropicClient(config.get("anthropic", {}))
        else:
            raise ValueError(f"Unknown LLM backend: {backend}")

    def _load_prompts(self) -> None:
        prompt_config = self._config.get("prompts", {})
        base_path = _REPO_ROOT / prompt_config.get("base_prompt", "")
        if base_path.is_file():
            self._base_prompt = base_path.read_text(encoding="utf-8")
        else:
            self._base_prompt = "You are a GRC assistant for BLACKSITE. Answer accurately and cite sources."

        role_prompt_paths = prompt_config.get("role_prompts", {})
        for role, rel_path in role_prompt_paths.items():
            p = _REPO_ROOT / rel_path
            if p.is_file():
                self._role_prompts[role] = p.read_text(encoding="utf-8")

        few_shot_path_str = prompt_config.get("few_shot_file", "")
        if few_shot_path_str:
            few_shot_path = _REPO_ROOT / few_shot_path_str
            if few_shot_path.exists():
                try:
                    data = json.loads(few_shot_path.read_text(encoding="utf-8"))
                    self._few_shot = data.get("examples", [])
                except Exception as e:
                    logger.warning(f"Failed to load few-shot examples: {e}")

    def initialize(self) -> None:
        """Initialize the engine (called once at startup)."""
        self._config = self._load_config()
        self._client = self._build_client(self._config)
        self._load_prompts()

        rag_config = self._config.get("rag", {})
        chunk_size = rag_config.get("chunk_size", 1000)
        overlap = rag_config.get("chunk_overlap", 200)
        self._kb = KnowledgeBase(
            knowledge_dir=_KNOWLEDGE_DIR,
            runtime_dir=_RUNTIME_DIR,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        if rag_config.get("enabled", True):
            self._kb.load()

        self._ready = True
        logger.info(f"LLM engine initialized: backend={self._config.get('backend')}")

    def _redact_sensitive(self, text: str) -> str:
        """Remove obviously sensitive content from text before sending to LLM."""
        safety = self._config.get("safety", {})
        for rule in safety.get("redact_patterns", []):
            pattern = rule.get("pattern", "")
            action = rule.get("action", "redact")
            try:
                if action == "redact":
                    text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
                elif action == "hash":
                    def _hash_match(m):
                        return hashlib.sha256(m.group().encode()).hexdigest()[:8]
                    text = re.sub(pattern, _hash_match, text)
            except re.error:
                pass
        return text

    def _build_system_prompt(self, user_context: Dict) -> str:
        """Build role-specific system prompt with template variable substitution."""
        role = user_context.get("role", "employee")
        prompt = self._role_prompts.get(role, self._base_prompt)

        # Replace {{VARIABLE}} placeholders
        replacements = {
            "ROLE": role.upper(),
            "SYSTEM_NAME": user_context.get("system_name", "Not specified"),
            "SYSTEM_ABBR": user_context.get("system_abbr", ""),
            "IMPACT_LEVEL": user_context.get("impact_level", "Unknown"),
            "TODAY": datetime.now().strftime("%Y-%m-%d"),
            "OPEN_POAM_COUNT": str(user_context.get("open_poam_count", "Unknown")),
            "ATO_EXPIRY": user_context.get("ato_expiry", "Unknown"),
        }
        for key, val in replacements.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", val)

        return prompt

    def _select_few_shot(self, query: str, role: str, max_examples: int = 3) -> List[Dict]:
        """Select relevant few-shot examples based on role and query."""
        if not self._few_shot:
            return []

        # First filter by role
        role_examples = [e for e in self._few_shot if e.get("role") == role]
        if not role_examples:
            role_examples = self._few_shot

        # Simple keyword matching for relevance
        query_words = set(query.lower().split())
        scored = []
        for ex in role_examples:
            q_words = set(ex.get("question", "").lower().split())
            overlap = len(query_words & q_words)
            scored.append((overlap, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:max_examples]]

    def _format_few_shot(self, examples: List[Dict]) -> str:
        """Format few-shot examples as conversation history."""
        parts = []
        for ex in examples:
            parts.append(f"Example Q: {ex['question']}\nExample A: {ex['answer']}")
        return "\n\n".join(parts)

    def _assemble_context(self, query: str, user_context: Dict) -> Tuple[str, List[str]]:
        """
        Retrieve relevant knowledge chunks and format context block.
        All retrieved content is from the general GRC knowledge base (NIST docs,
        framework guidance) — no system-specific data is injected here.
        System-specific data (POA&M count, ATO expiry, impact level) flows only
        through the system prompt template variables, keeping it scoped to the
        authorized system.
        """
        if not self._kb or not self._config.get("rag", {}).get("enabled", True):
            return "", []

        max_chunks = self._config.get("rag", {}).get("max_chunks_per_query", 6)
        results = self._kb.search(query, top_k=max_chunks)

        sources = []
        context_parts = []
        for r in results:
            source = r["meta"]["source"]
            # Skip runtime snapshots that contain system-level operational data —
            # those may contain aggregate info from all systems (e.g., db_schema,
            # job_status). General NIST/framework docs are safe to include for all users.
            if source.startswith("runtime/") and source not in (
                "runtime/audit_vocab.json",   # vocabulary definitions — not system data
                "runtime/route_map.json",     # UI navigation — not system data
            ):
                continue
            sources.append(source)
            context_parts.append(f"[Source: {source}]\n{r['content']}")

        # Always include configured paths (general reference docs only)
        always_include = self._config.get("rag", {}).get("always_include", [])
        for rel_path in always_include:
            full_path = _REPO_ROOT / rel_path
            if full_path.exists():
                try:
                    text = full_path.read_text(encoding="utf-8", errors="replace")[:3000]
                    context_parts.insert(0, f"[Source: {rel_path} (always included)]\n{text}")
                    sources.insert(0, rel_path)
                except Exception:
                    pass

        context_text = "\n\n---\n\n".join(context_parts)
        return context_text, list(dict.fromkeys(sources))  # deduplicated sources

    async def ask(
        self,
        query: str,
        user_context: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
        system_prompt_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point: answer a GRC question.

        Args:
            query: The user's question
            user_context: Dict with keys: role, system_name, system_abbr,
                          impact_level, open_poam_count, ato_expiry, system_id
            history: List of prior conversation turns [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            Dict with: answer (str), sources (List[str]), elapsed_ms (int),
                       chunks_used (int), error (str|None)
        """
        if not self._ready:
            self.initialize()

        user_context = user_context or {}
        history = history or []
        role = user_context.get("role", "employee")

        start = time.monotonic()

        # Safety check
        max_len = self._config.get("safety", {}).get("max_query_length", 2000)
        if len(query) > max_len:
            query = query[:max_len] + "...[truncated]"
        query = self._redact_sensitive(query)

        # GRC topic pre-filter — reject clearly off-topic queries before calling the API
        if not _is_grc_query(query):
            return {
                "answer": _GRC_REFUSAL,
                "sources": [],
                "chunks_used": 0,
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "model": "topic-filter",
                "error": None,
            }

        try:
            # 1. Build system prompt (override replaces entirely — used in demo mode)
            system_prompt = system_prompt_override if system_prompt_override else self._build_system_prompt(user_context)

            # 2. Retrieve knowledge context
            rag_context, sources = self._assemble_context(query, user_context)

            # 3. Select few-shot examples
            max_fs = self._config.get("prompts", {}).get("max_few_shot_examples", 3)
            few_shot = self._select_few_shot(query, role, max_fs)
            few_shot_text = self._format_few_shot(few_shot)

            # 4. Assemble messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add knowledge context as user message (RAG injection)
            if rag_context:
                context_msg = (
                    "Below is relevant reference information to help answer the question:\n\n"
                    f"{rag_context}\n\n"
                    "Use this information to ground your answer. Cite the source when referencing it."
                )
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "Understood. I'll use this reference information to provide accurate, cited answers."})

            # Add few-shot examples
            if few_shot_text:
                messages.append({"role": "user", "content": f"Here are some example Q&A pairs for this type of question:\n\n{few_shot_text}\n\nNow answer the following question in the same style."})
                messages.append({"role": "assistant", "content": "I'll follow the same structured, citation-backed format."})

            # Add conversation history (most recent N turns)
            # Strip to only role+content — extra fields (sources, ts) break strict APIs (Groq)
            max_turns = self._config.get("chat", {}).get("history_turns", 6)
            if history:
                for turn in history[-(max_turns * 2):]:
                    role = turn.get("role", "")
                    content = turn.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})

            # Add current query
            messages.append({"role": "user", "content": query})

            # 5. Call LLM
            answer = await self._client.complete(messages)

            elapsed_ms = int((time.monotonic() - start) * 1000)

            return {
                "answer": answer,
                "sources": sources[:8],  # cap at 8 sources in response
                "chunks_used": len(sources),
                "elapsed_ms": elapsed_ms,
                "model": getattr(self._client, "model", "unknown"),
                "error": None,
            }

        except Exception as e:
            logger.exception(f"LLM ask() failed: {e}")
            return {
                "answer": "I'm unable to answer right now. The AI assistant may be unavailable or still loading. Please try again in a moment.",
                "sources": [],
                "chunks_used": 0,
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "model": "unknown",
                "error": str(e),
            }

    async def is_available(self) -> bool:
        """Check if the configured LLM backend is reachable."""
        if not self._ready:
            try:
                self.initialize()
            except Exception:
                return False
        if self._client is None:
            return False
        try:
            return await self._client.is_available()
        except Exception:
            return False

    def reload_knowledge(self) -> None:
        """Reload knowledge base (e.g., after knowledge update)."""
        if self._kb:
            self._kb.reload()
            logger.info("Knowledge base reloaded")


# ---------------------------------------------------------------------------
# Singleton engine instance
# ---------------------------------------------------------------------------
_engine_instance: Optional[LLMEngine] = None


def get_engine() -> LLMEngine:
    """Get or create the singleton LLM engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LLMEngine()
        _engine_instance.initialize()
    return _engine_instance
