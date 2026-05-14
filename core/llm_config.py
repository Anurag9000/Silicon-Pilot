"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SILICON-PILOT  ·  CENTRAL LLM CONFIGURATION                   ║
║                                                                              ║
║  ▸ Change LLM_PROVIDER to switch ALL calls repo-wide in one edit.           ║
║  ▸ Change LLM_MODEL to use a different local Ollama model everywhere.       ║
║  ▸ All files import from here — nothing is hardcoded elsewhere.             ║
╚══════════════════════════════════════════════════════════════════════════════╝

QUICK CHEAT-SHEET
─────────────────
  Switch to Ollama (default, no API key needed):
      LLM_PROVIDER = "ollama"
      LLM_MODEL    = "qwen2.5:7b"   # or any name from `ollama list`

  Switch to OpenAI:
      LLM_PROVIDER = "openai"
      LLM_MODEL    = "gpt-4o-mini"
      # set env: export OPENAI_API_KEY=sk-...

  Switch to a faster/smaller local model:
      LLM_MODEL = "qwen2.5:1.5b"    # 986 MB — very fast
      LLM_MODEL = "llama3.2"        # 2.0 GB
      LLM_MODEL = "mistral"         # 4.4 GB
      LLM_MODEL = "qwen2.5:7b"      # 4.7 GB — best quality
      LLM_MODEL = "deepseek-r1:8b"  # 5.2 GB — strong reasoning

Available Ollama models on this machine (from `ollama list`):
  qwen2.5:0.5b      397  MB  ← fastest, lowest quality
  qwen2.5:1.5b      986  MB  ← DEFAULT: fully GPU-resident on RTX 3050 6GB 
  llama3.2          2.0  GB
  mistral           4.4  GB
  qwen2.5:7b        4.7  GB  ← HIGH QUALITY but tight on 6 GB VRAM 
  deepseek-r1:8b    5.2  GB  ← may spill to CPU RAM on 6 GB GPU
  qwen2.5vl:7b      6.0  GB  ← multimodal, will NOT fit in 6 GB

VRAM BUDGET (RTX 3050 6 GB Laptop):
  OS/driver overhead  ~0.5–1.0 GB
  Available for model ~5.0–5.5 GB usable
  qwen2.5:1.5b Q4     ~1.0 GB  → 100% GPU, 2–5s inference   RECOMMENDED
  qwen2.5:7b   Q4     ~5.2 GB  → barely fits, may spill to CPU RAM, fans 
  deepseek-r1:8b Q4   ~5.4 GB  → likely CPU spill, slow 
"""

from __future__ import annotations
import os

# ══════════════════════════════════════════════════════════════════════════════
#  PRIMARY SETTINGS  ←  EDIT THESE TO CHANGE EVERYTHING AT ONCE
# ══════════════════════════════════════════════════════════════════════════════

# Provider: "ollama" | "openai"
LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "ollama")

# Model name — must exist in your Ollama library or be a valid OpenAI model ID
# qwen2.5:0.5b = 397 MB  — lightning fast, fully GPU, sub-second on RTX 3050  DEFAULT
# qwen2.5:1.5b = 986 MB  — fast, fully GPU, 2-5s
# qwen2.5:7b   = 4.7 GB  — may spill to CPU RAM on 6 GB GPU → slow (60-90s)
LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:0.5b")

# Ollama server URL (default: local)
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# OpenAI base URL — override to point at any OpenAI-compatible API
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

# OpenAI API key — only required when LLM_PROVIDER="openai"
OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")

# ══════════════════════════════════════════════════════════════════════════════
#  PER-TASK MODEL OVERRIDES
#  Use a smaller model for fast/cheap tasks and a larger one for deep reasoning.
#  Each defaults to LLM_MODEL unless overridden here or via env var.
# ══════════════════════════════════════════════════════════════════════════════

# ── FAST tasks (latency-critical, 1.5b fits fully in VRAM → 2–5s) ────────────
# Fast intent/constraint parsing
MODEL_PARSER: str = os.environ.get("LLM_MODEL_PARSER", "qwen2.5:1.5b")

# MCU ranking explanation (runs after hard filter, needs to be snappy)
MODEL_RANKER: str = os.environ.get("LLM_MODEL_RANKER", "qwen2.5:1.5b")

# PDF ingestion extraction (batch job, fast > quality)
MODEL_INGESTION: str = os.environ.get("LLM_MODEL_INGESTION", "qwen2.5:1.5b")

# ── QUALITY tasks (heavier reasoning, user waits explicitly) ─────────────────
# Architect debate (multiple virtual experts — user clicks a button, OK to wait)
MODEL_DEBATE: str = os.environ.get("LLM_MODEL_DEBATE", "qwen2.5:7b")

# Peer review / exhaustive DRC analysis (user-initiated deep dive)
MODEL_REVIEW: str = os.environ.get("LLM_MODEL_REVIEW", "qwen2.5:7b")

# Firmware + reference design recommendations
MODEL_FIRMWARE: str = os.environ.get("LLM_MODEL_FIRMWARE", "qwen2.5:1.5b")

# ══════════════════════════════════════════════════════════════════════════════
#  GENERATION PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

TEMPERATURE: float   = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
MAX_TOKENS: int      = int(os.environ.get("LLM_MAX_TOKENS",    "2048"))
# 300s timeout — qwen2.5:1.5b should finish in 2–10s, but 7b may take 90s+
TIMEOUT_SECS: float  = float(os.environ.get("LLM_TIMEOUT",     "300"))

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT FACTORY  — the single function every module calls
# ══════════════════════════════════════════════════════════════════════════════

def get_openai_client(model: str | None = None):
    """
    Return an openai.OpenAI (sync) client pointed at either Ollama or OpenAI.
    The openai SDK is used for both because Ollama exposes an OpenAI-compatible
    /v1 endpoint — so callers work identically regardless of provider.

    Usage:
        from core.llm_config import get_openai_client, LLM_MODEL
        client = get_openai_client()
        resp = client.chat.completions.create(model=LLM_MODEL, messages=[...])
    """
    from openai import OpenAI  # type: ignore[import]
    if LLM_PROVIDER == "ollama":
        return OpenAI(
            api_key="ollama",                          # Ollama ignores the key
            base_url=f"{OLLAMA_BASE_URL}/v1",
        )
    return OpenAI(
        api_key=OPENAI_API_KEY or "missing-key",
        base_url=OPENAI_BASE_URL,
    )


def get_async_openai_client(model: str | None = None):
    """
    Return an openai.AsyncOpenAI client (async/await compatible).

    Usage:
        from core.llm_config import get_async_openai_client, LLM_MODEL
        client = get_async_openai_client()
        resp = await client.chat.completions.create(model=LLM_MODEL, messages=[...])
    """
    from openai import AsyncOpenAI  # type: ignore[import]
    if LLM_PROVIDER == "ollama":
        return AsyncOpenAI(
            api_key="ollama",
            base_url=f"{OLLAMA_BASE_URL}/v1",
        )
    return AsyncOpenAI(
        api_key=OPENAI_API_KEY or "missing-key",
        base_url=OPENAI_BASE_URL,
    )


def chat(messages: list[dict], model: str | None = None,
         temperature: float | None = None,
         max_tokens: int | None = None) -> str:
    """
    Synchronous convenience wrapper — call the configured LLM and return the
    text of the first choice. All args fall back to global config defaults.

    Usage:
        from core.llm_config import chat
        text = chat([{"role":"user","content":"What is 2+2?"}])
    """
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=model or LLM_MODEL,
        messages=messages,
        temperature=temperature if temperature is not None else TEMPERATURE,
        max_tokens=max_tokens or MAX_TOKENS,
        extra_body={"keep_alive": 0} if LLM_PROVIDER == "ollama" else None,
    )
    return resp.choices[0].message.content or ""


async def achat(messages: list[dict], model: str | None = None,
                temperature: float | None = None,
                max_tokens: int | None = None) -> str:
    """
    Async convenience wrapper — same as chat() but awaitable.

    Usage:
        from core.llm_config import achat
        text = await achat([{"role":"user","content":"Summarise this spec..."}])
    """
    client = get_async_openai_client()
    resp = await client.chat.completions.create(
        model=model or LLM_MODEL,
        messages=messages,
        temperature=temperature if temperature is not None else TEMPERATURE,
        max_tokens=max_tokens or MAX_TOKENS,
        extra_body={"keep_alive": 0} if LLM_PROVIDER == "ollama" else None,
    )
    return resp.choices[0].message.content or ""


# ══════════════════════════════════════════════════════════════════════════════
#  DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════════

def print_config() -> None:
    """Print the active LLM configuration — call at server startup."""
    print("┌─────────────────────────────────────────────┐")
    print("│         Silicon-Pilot LLM Config            │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  Provider : {LLM_PROVIDER:<32}│")
    print(f"│  Model    : {LLM_MODEL:<32}│")
    if LLM_PROVIDER == "ollama":
        print(f"│  Base URL : {OLLAMA_BASE_URL:<32}│")
    else:
        key_status = "SET ✓" if OPENAI_API_KEY else "NOT SET ✗"
        print(f"│  API Key  : {key_status:<32}│")
    print(f"│  Temp     : {TEMPERATURE:<32}│")
    print(f"│  MaxTokens: {MAX_TOKENS:<32}│")
    print(f"│  Timeout  : {TIMEOUT_SECS}s{'':<29}│")
    print("├─────────────────────────────────────────────┤")
    print(f"│  parser   : {MODEL_PARSER:<32}│")
    print(f"│  ranker   : {MODEL_RANKER:<32}│")
    print(f"│  debate   : {MODEL_DEBATE:<32}│")
    print(f"│  review   : {MODEL_REVIEW:<32}│")
    print(f"│  ingestion: {MODEL_INGESTION:<32}│")
    print("└─────────────────────────────────────────────┘")


async def health_check() -> dict:
    """Ping the configured LLM and return a status dict."""
    import time
    t0 = time.monotonic()
    try:
        text = await achat(
            [{"role": "user", "content": "Reply with exactly: OK"}],
            model=LLM_MODEL,
            max_tokens=5,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "status": "ok" if "ok" in text.lower() else "degraded",
            "response": text.strip(),
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "status": "error",
            "error": str(exc),
        }
