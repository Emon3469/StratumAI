import re

ASSISTANT_SCOPE = (
    "Kubernetes workloads and operations (jobs, cron jobs, work queues, autoscaling, monitoring), "
    "cloud-native architecture, systems and hardware engineering, networking, and general software engineering"
)

MAX_INPUT_CHARS = 4000

INJECTION_PATTERNS = [
    r"\bignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)",
    r"\bdisregard (all |any |your )?(previous |prior )?(instructions|training|rules|guidelines)",
    r"\bforget (all |your )?(previous |prior )?(instructions|system prompt|rules)",
    r"\b(reveal|print|show|repeat|leak)\b.{0,40}\b(system prompt|hidden prompt|initial instructions)",
    r"\byou are now (dan|in developer mode|an unrestricted)",
    r"\b(jailbreak|do anything now)\b",
    r"\bact as (an? )?(unrestricted|unfiltered|uncensored)",
    r"\b(bypass|override|disable) (your |the )?(safety|guardrails|filters|guidelines|restrictions)",
    r"\bpretend (that )?you (have no|are not bound by) (restrictions|rules|guidelines)",
]

_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

RESPONSES = {
    "injection": (
        "I can't change how I operate or reveal internal instructions. "
        "I'm happy to help with Kubernetes, infrastructure, networking or engineering questions though, "
        "what are you working on?"
    ),
    "too_long": (
        f"That message is a bit long for me to process safely. Please keep it under {MAX_INPUT_CHARS:,} "
        "characters, or split it into smaller questions."
    ),
    "off_topic": (
        "That's outside what I'm set up for. I focus on "
        f"{ASSISTANT_SCOPE}. Ask me anything in those areas and I'll dig into the knowledge base for you."
    ),
}


def matches_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))
