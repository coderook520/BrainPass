"""Content sanitizer — §F1 (unforgeable XML envelope via html.escape).

The body of untrusted content is HTML-escaped before wrapping, so `<` and `>`
become `&lt;` and `&gt;`. A literal `</external_content>` cannot appear in
the output regardless of what the source page contains. Structural fix —
no regex mitigation necessary.
"""
from __future__ import annotations
import hashlib
import html
import re
import unicodedata

_INJECTION_PATTERNS = [
    r"ignore (all |any |the |)(previous|prior|above|earlier) (instructions?|prompt|context|messages?|directives?)",
    r"disregard .{0,50}(instructions?|prompt)",
    r"you are now .{0,200}",
    r"(new|updated|replacement) (system|instruction)s?:",
    r"<\|(im_start|im_end|end_of_turn|system|user|assistant)\|>",
    r"###\s*(system|user|assistant|instruction)",
    r"\[\[(system|instruction|prompt)\]\]",
    r"(from now on|henceforth|going forward)[^.]*?(you|your|answer|respond)",
    r"(the above|everything above).{0,100}(fake|test|lie|ignore)",
    r"jailbreak|DAN (mode|prompt)|pretend you are (not|no longer)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
_INVISIBLE_RE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff\u00ad]"
)
_MAX_RAW = 200_000
_MAX_CLEAN = 40_000


def sanitize(raw: str, source_domain: str) -> str:
    if len(raw) > _MAX_RAW:
        raw = raw[:_MAX_RAW]
    norm = unicodedata.normalize("NFKC", raw)
    norm = _INVISIBLE_RE.sub("", norm)
    text = _strip_tags(norm)
    text = _INJECTION_RE.sub("[REDACTED: instruction-like content]", text)
    if len(text) > _MAX_CLEAN:
        text = text[:_MAX_CLEAN] + "\n...[truncated]"
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    safe_domain = html.escape(source_domain, quote=True)
    safe_body = html.escape(text, quote=False)
    return (
        f'<external_content source="{safe_domain}" hash="{content_hash}">\n'
        f'{safe_body}\n'
        f'</external_content>'
    )


def _strip_tags(html_text: str) -> str:
    """Extract readable text. Uses BeautifulSoup when available, regex fallback otherwise."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "iframe", "object", "embed",
                          "form", "input", "meta", "link"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except ImportError:
        # Conservative regex fallback (bs4 is soft-required — module_ready()
        # disables research when absent, so we should rarely land here).
        stripped = re.sub(
            r"<(script|style|iframe|object|embed|form|input|meta|link)[^>]*>.*?</\1>",
            " ", html_text, flags=re.IGNORECASE | re.DOTALL,
        )
        return re.sub(r"<[^>]+>", " ", stripped)
