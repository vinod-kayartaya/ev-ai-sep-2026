import os
import json
import re
from typing import Optional, Dict, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from cve_analyzer.config import OPENAI_API_KEY, OPENAI_API_BASE, DEFAULT_MODEL
from cve_analyzer.models.vulnerability import VulnerabilityInfo


def get_llm(model: Optional[str] = None, temperature: float = 0.0) -> Optional[BaseChatModel]:
    """
    Returns an initialized LangChain ChatModel (OpenAI or Qwen / local model).
    If no API key is provided, returns None (triggering deterministic fallback).
    """
    api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    model_name = model or DEFAULT_MODEL
    kwargs: Dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "api_key": api_key,
    }
    if OPENAI_API_BASE:
        kwargs["base_url"] = OPENAI_API_BASE

    return ChatOpenAI(**kwargs)


def parse_vulnerability_with_fallback(cve_id: str, raw_text: Optional[str] = None, parsed_dict: Optional[dict] = None) -> VulnerabilityInfo:
    """
    Parses unstructured or structured CVE information into a validated VulnerabilityInfo model.
    Works deterministically using regex/JSON parsing when LLM is unavailable, or as fallback.
    """
    if parsed_dict:
        return VulnerabilityInfo(**parsed_dict)

    if not raw_text:
        return VulnerabilityInfo(
            cve_id=cve_id,
            artifact="unknown:unknown",
            affected_versions=[],
            affected_classes=[],
            affected_methods=[],
            description="No vulnerability details provided."
        )

    text = raw_text.strip()

    # Check if raw_text is JSON
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if "cve_id" not in data:
                data["cve_id"] = cve_id
            return VulnerabilityInfo(**data)
        except Exception:
            pass

    # Regex extraction
    artifact = "unknown:unknown"
    versions = []
    classes = []
    methods = []
    is_ambiguous = False
    ambiguity_reason = None

    # Check Artifact
    art_match = re.search(r"(?:artifact|package|dependency|library):\s*([a-zA-Z0-9_.:-]+)", text, re.I)
    if art_match:
        artifact = art_match.group(1).strip()
    else:
        # Look for group:artifact coordinate pattern
        coord_match = re.search(r"([a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+)", text)
        if coord_match:
            artifact = coord_match.group(1).strip()

    # Check Versions
    ver_match = re.search(r"(?:versions?|affected\s*versions?):\s*([0-9.,\s*<>=]+)", text, re.I)
    if ver_match:
        versions = [v.strip() for v in re.split(r"[,;\s]+", ver_match.group(1)) if v.strip()]
    else:
        # Search for version numbers e.g. 1.2.3
        standalone_ver = re.findall(r"\b(\d+\.\d+(?:\.\d+)?)\b", text)
        if standalone_ver:
            versions = standalone_ver

    # Check Classes
    class_match = re.findall(r"(?:class|affected_class):\s*([a-zA-Z0-9_.]+)", text, re.I)
    if class_match:
        classes = [c.strip() for c in class_match]
    else:
        # Look for Java package.Class patterns
        pkg_classes = re.findall(r"\b([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\.[A-Z][a-zA-Z0-9_]*)\b", text)
        if pkg_classes:
            classes = list(set(pkg_classes))

    # Check Methods
    method_match = re.findall(r"(?:method|affected_method):\s*([a-zA-Z0-9_]+(?:\(\))?)", text, re.I)
    if method_match:
        methods = [m.replace("()", "").strip() for m in method_match]
    else:
        # Look for methodInvocation() patterns
        code_methods = re.findall(r"\b([a-zA-Z][a-zA-Z0-9_]*)\(\)", text)
        clean_code_methods = [m for m in code_methods if m not in ("println", "equals", "toString", "hashCode", "main")]
        if clean_code_methods:
            methods = list(set(clean_code_methods))

    # Ambiguity detection:
    if len(classes) > 1 or len(methods) > 1:
        is_ambiguous = True
        ambiguity_reason = f"Multiple candidate symbols found (classes: {classes}, methods: {methods})"
    elif not classes and not methods:
        is_ambiguous = True
        ambiguity_reason = "No affected class or method identified in vulnerability description."

    return VulnerabilityInfo(
        cve_id=cve_id,
        artifact=artifact,
        affected_versions=versions or ["*"],
        affected_classes=classes,
        affected_methods=methods,
        description=text,
        raw_text=raw_text,
        is_ambiguous=is_ambiguous,
        ambiguity_reason=ambiguity_reason
    )
