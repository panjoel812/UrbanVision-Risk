from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from http.client import HTTPConnection, HTTPException

from urbanvision_risk.errors import ProjectError

NARRATIVE_SCHEMA_VERSION = "local-narrative-v1.2.0"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "qwen3:4b"
MAX_RESPONSE_BYTES = 128 * 1024
MAX_TEXT_CHARACTERS = 900
MAX_LIST_ITEMS = 5
MODEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")

Transport = Callable[[dict[str, object], float], bytes]


def _validate_model_name(model: str) -> str:
    value = model.strip()
    if (
        not MODEL_PATTERN.fullmatch(value)
        or "://" in value
        or ".." in value
        or value.startswith(("/", "."))
    ):
        raise ProjectError(
            "E302",
            "本地 Ollama 模型名称无效",
            "The local Ollama model name is invalid",
            "使用例如 qwen3:4b；名称只能包含字母、数字、点、冒号、斜杠、下划线和连字符",
            (
                "Use a name such as qwen3:4b containing only letters, numbers, dots, colons, "
                "slashes, underscores, and hyphens"
            ),
            value,
        )
    return value


def _ollama_transport(payload: dict[str, object], timeout_seconds: float) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    connection = HTTPConnection("127.0.0.1", 11434, timeout=timeout_seconds)
    try:
        connection.request(
            "POST",
            "/api/generate",
            body=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise RuntimeError(f"ollama_http_{response.status}")
        content = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPException, OSError, TimeoutError) as error:
        raise RuntimeError(type(error).__name__) from error
    finally:
        connection.close()
    if len(content) > MAX_RESPONSE_BYTES:
        raise ValueError("Ollama response exceeded the local size limit")
    return content


def _bilingual(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a bilingual object")
    result: dict[str, str] = {}
    for language in ("zh", "en"):
        text = value.get(language)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{field}.{language} must be non-empty text")
        cleaned = " ".join(text.split())
        if len(cleaned) > MAX_TEXT_CHARACTERS:
            raise ValueError(f"{field}.{language} is too long")
        result[language] = cleaned
    return result


def _bilingual_items(value: object, field: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_LIST_ITEMS:
        raise ValueError(f"{field} must contain 1 to {MAX_LIST_ITEMS} items")
    return [_bilingual(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _safe_facts(
    prediction: Mapping[str, object], risk: Mapping[str, object]
) -> dict[str, object]:
    counts = prediction.get("counts")
    if not isinstance(counts, Mapping):
        counts = {}
    safe_counts = {
        code: int(counts.get(code, 0))
        for code in ("D00", "D10", "D20", "D40", "Repair")
    }
    breakdown: list[dict[str, object]] = []
    raw_breakdown = risk.get("class_breakdown")
    if isinstance(raw_breakdown, list):
        for item in raw_breakdown:
            if not isinstance(item, Mapping) or item.get("code") not in safe_counts:
                continue
            breakdown.append(
                {
                    "code": str(item["code"]),
                    "count": int(item.get("count", 0)),
                    "coverage_percent": round(float(item.get("coverage_ratio", 0.0)) * 100, 2),
                    "score_contribution": round(float(item.get("score_contribution", 0.0)), 1),
                }
            )
    evidence = risk.get("evidence")
    if not isinstance(evidence, Mapping):
        evidence = {}
    flags = risk.get("audit_flags")
    safe_flags = []
    if isinstance(flags, list):
        safe_flags = [
            str(item.get("code"))
            for item in flags
            if isinstance(item, Mapping) and isinstance(item.get("code"), str)
        ][:10]
    return {
        "counts": safe_counts,
        "class_breakdown": breakdown,
        "risk_score_audit_value": round(float(risk.get("risk_score", 0.0)), 1),
        "risk_level": str(risk.get("risk_level", "unknown")),
        "decision_status": str(risk.get("decision_status", "review_required")),
        "review_required": bool(risk.get("review_required", True)),
        "evidence_quality": str(evidence.get("quality", "not_applicable")),
        "mean_confidence": evidence.get("mean_detection_confidence"),
        "audit_flag_codes": safe_flags,
    }


def _fallback_narrative(
    facts: Mapping[str, object], *, reason: str, model: str
) -> dict[str, object]:
    counts = facts["counts"]
    assert isinstance(counts, Mapping)
    damage_count = sum(int(counts.get(code, 0)) for code in ("D00", "D10", "D20", "D40"))
    repair_count = int(counts.get("Repair", 0))
    review_required = bool(facts["review_required"])
    if review_required:
        summary = {
            "zh": (
                f"模型记录到 {damage_count} 个计分缺陷检测，但证据仍需要人工复核。"
                "页面中的数值仅用于审计，不能作为道路安全结论。"
            ),
            "en": (
                f"The model recorded {damage_count} scored damage detection(s), but the evidence "
                "still requires human review. The numeric value is for audit only and is not a "
                "road-safety conclusion."
            ),
        }
    else:
        summary = {
            "zh": (
                f"模型记录到 {damage_count} 个计分缺陷检测，审计维护优先级为 "
                f"{facts['risk_score_audit_value']}/100。该结果仍需由工程人员结合现场情况确认。"
            ),
            "en": (
                f"The model recorded {damage_count} scored damage detection(s), with an audited "
                f"maintenance priority of {facts['risk_score_audit_value']}/100. Engineering staff "
                "must still confirm the result on site."
            ),
        }

    observations: list[dict[str, str]] = []
    class_names = {
        "D00": ("纵向裂缝", "longitudinal crack"),
        "D10": ("横向裂缝", "transverse crack"),
        "D20": ("网状裂缝", "alligator crack"),
        "D40": ("坑洞", "pothole"),
    }
    for item in facts["class_breakdown"]:
        assert isinstance(item, Mapping)
        code = str(item["code"])
        count = int(item["count"])
        if count <= 0 or code not in class_names:
            continue
        zh_name, en_name = class_names[code]
        observations.append(
            {
                "zh": (
                    f"{code} {zh_name}: {count} 处，检测框联合覆盖率约 "
                    f"{item['coverage_percent']}%。"
                ),
                "en": (
                    f"{code} {en_name}: {count} detection(s), with approximately "
                    f"{item['coverage_percent']}% union box coverage."
                ),
            }
        )
    if not observations:
        observations.append(
            {
                "zh": "未获得受支持计分缺陷的可靠检测；这属于无法下结论的结果。",
                "en": (
                    "No reliable detection of a supported scored damage class was obtained; "
                    "the result is inconclusive."
                ),
            }
        )
    if repair_count:
        observations.append(
            {
                "zh": f"观察到 {repair_count} 个历史修补区域；该类别只作辅助观察，不参与计分。",
                "en": (
                    f"{repair_count} previously repaired area(s) were observed; this auxiliary "
                    "class is not scored."
                ),
            }
        )

    actions = [
        {
            "zh": "由具备资质的人员进行现场复核，并核对检测框与真实病害边界。",
            "en": (
                "Have qualified personnel perform an on-site review and compare the boxes with "
                "the true damage boundaries."
            ),
        },
        {
            "zh": "结合道路尺度、交通荷载、排水和历史维修记录决定检查与维修顺序。",
            "en": (
                "Use physical scale, traffic loading, drainage, and maintenance history to decide "
                "inspection and repair order."
            ),
        },
    ]
    if repair_count:
        actions.append(
            {
                "zh": "检查历史修补区域是否出现开裂、松散、沉陷或边缘剥离。",
                "en": (
                    "Inspect repaired areas for renewed cracking, raveling, settlement, or edge "
                    "separation."
                ),
            }
        )
    return {
        "schema_version": NARRATIVE_SCHEMA_VERSION,
        "generator": {
            "mode": "template",
            "model": model,
            "fallback_used": True,
            "fallback_reason": reason,
            "local_only": True,
        },
        "summary": summary,
        "observations": observations[:MAX_LIST_ITEMS],
        "actions": actions[:MAX_LIST_ITEMS],
    }


class LocalNarrativeGenerator:
    """Generate a bounded bilingual narrative through Ollama or an audited template."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_seconds: float = 30.0,
        ollama_enabled: bool = True,
        transport: Transport | None = None,
    ) -> None:
        self.model = _validate_model_name(model)
        if not 0.1 <= timeout_seconds <= 300:
            raise ProjectError(
                "E302",
                "本地说明生成超时必须位于 0.1 到 300 秒",
                "The local narrative timeout must be between 0.1 and 300 seconds",
                "使用例如 --ollama-timeout 30",
                "Use a value such as --ollama-timeout 30",
                str(timeout_seconds),
            )
        self.timeout_seconds = float(timeout_seconds)
        self.ollama_enabled = bool(ollama_enabled)
        self._transport = transport or _ollama_transport

    def health_payload(self) -> dict[str, object]:
        return {
            "mode": "auto" if self.ollama_enabled else "template",
            "model": self.model,
            "endpoint": "127.0.0.1:11434",
            "local_only": True,
            "cloud_api": False,
        }

    def generate(
        self, prediction: Mapping[str, object], risk: Mapping[str, object]
    ) -> dict[str, object]:
        facts = _safe_facts(prediction, risk)
        if not self.ollama_enabled:
            return _fallback_narrative(facts, reason="template_mode", model=self.model)

        prompt = (
            "You are a cautious bilingual road-inspection writing assistant. Use only the JSON "
            "facts below. Do not infer physical dimensions, road safety, structural capacity, or "
            "facts not supplied. Never call a low-confidence or zero-detection result safe. Return "
            "strict JSON with exactly these keys: summary (object with zh and en strings), "
            "observations (1-5 objects with zh and en strings), actions (1-5 objects with zh and "
            "en strings). Keep every item concise and state that humans make final decisions. "
            "Facts: "
            + json.dumps(facts, ensure_ascii=False, sort_keys=True)
        )
        request_payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "seed": 42},
        }
        try:
            response = json.loads(self._transport(request_payload, self.timeout_seconds))
            if not isinstance(response, Mapping) or not isinstance(response.get("response"), str):
                raise ValueError("Ollama response wrapper is invalid")
            generated = json.loads(response["response"])
            if not isinstance(generated, Mapping):
                raise ValueError("Generated narrative is not an object")
            return {
                "schema_version": NARRATIVE_SCHEMA_VERSION,
                "generator": {
                    "mode": "ollama",
                    "model": self.model,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "local_only": True,
                },
                "summary": _bilingual(generated.get("summary"), "summary"),
                "observations": _bilingual_items(
                    generated.get("observations"), "observations"
                ),
                "actions": _bilingual_items(generated.get("actions"), "actions"),
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
            return _fallback_narrative(
                facts,
                reason=f"ollama_{type(error).__name__.lower()}",
                model=self.model,
            )
