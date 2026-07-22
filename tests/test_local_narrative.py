import json

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.reporting.local_narrative import LocalNarrativeGenerator


def prediction() -> dict[str, object]:
    return {
        "source_image": "/private/secret/road-owner-name.jpg",
        "counts": {"D00": 0, "D10": 0, "D20": 2, "D40": 0, "Repair": 3},
    }


def risk(*, review_required: bool = True) -> dict[str, object]:
    return {
        "risk_score": 19.8,
        "risk_level": "low",
        "decision_status": "review_required" if review_required else "scored",
        "review_required": review_required,
        "class_breakdown": [
            {
                "code": "D20",
                "count": 2,
                "coverage_ratio": 0.8088,
                "score_contribution": 19.8,
            }
        ],
        "evidence": {"quality": "low", "mean_detection_confidence": 0.434},
        "audit_flags": [{"code": "low_confidence_evidence", "en": "x", "zh": "y"}],
        "limitation": {"zh": "不是道路安全结论", "en": "Not a road-safety verdict"},
    }


def test_valid_ollama_response_uses_only_bounded_structured_facts() -> None:
    requests: list[dict[str, object]] = []
    generated = {
        "summary": {"zh": "证据需要人工复核。", "en": "The evidence needs human review."},
        "observations": [
            {"zh": "检测到网状裂缝。", "en": "Alligator cracking was detected."}
        ],
        "actions": [{"zh": "安排现场复核。", "en": "Arrange an on-site review."}],
    }

    def transport(payload: dict[str, object], timeout: float) -> bytes:
        requests.append(payload)
        assert timeout == 12.0
        return json.dumps({"response": json.dumps(generated, ensure_ascii=False)}).encode()

    narrative = LocalNarrativeGenerator(
        model="qwen3:4b", timeout_seconds=12, transport=transport
    ).generate(prediction(), risk())

    assert narrative["generator"]["mode"] == "ollama"
    assert narrative["generator"]["local_only"] is True
    assert narrative["summary"]["zh"] == "证据需要人工复核。"
    serialized_request = json.dumps(requests[0], ensure_ascii=False)
    assert "road-owner-name.jpg" not in serialized_request
    assert "/private/secret" not in serialized_request
    assert isinstance(requests[0]["prompt"], str)
    assert '"D20": 2' in requests[0]["prompt"]
    assert requests[0]["stream"] is False
    assert requests[0]["format"] == "json"


def test_unavailable_ollama_falls_back_without_hiding_uncertainty() -> None:
    def unavailable(_: dict[str, object], __: float) -> bytes:
        raise RuntimeError("offline")

    narrative = LocalNarrativeGenerator(transport=unavailable).generate(prediction(), risk())

    assert narrative["generator"]["mode"] == "template"
    assert narrative["generator"]["fallback_used"] is True
    assert narrative["generator"]["fallback_reason"] == "ollama_runtimeerror"
    assert "人工复核" in narrative["summary"]["zh"]
    assert "human review" in narrative["summary"]["en"]
    assert any("80.88%" in item["en"] for item in narrative["observations"])
    assert any("not scored" in item["en"] for item in narrative["observations"])


def test_template_mode_never_calls_transport() -> None:
    def forbidden(_: dict[str, object], __: float) -> bytes:
        raise AssertionError("transport must not run")

    narrative = LocalNarrativeGenerator(
        ollama_enabled=False, transport=forbidden
    ).generate(prediction(), risk(review_required=False))

    assert narrative["generator"]["fallback_reason"] == "template_mode"
    assert "19.8/100" in narrative["summary"]["en"]


@pytest.mark.parametrize("model", ("", "model name", "https://cloud.example/model", "../../secret"))
def test_model_name_rejects_unsafe_values(model: str) -> None:
    with pytest.raises(ProjectError, match="E302"):
        LocalNarrativeGenerator(model=model)


def test_invalid_generated_schema_uses_deterministic_fallback() -> None:
    def invalid(_: dict[str, object], __: float) -> bytes:
        return json.dumps({"response": '{"summary": "not bilingual"}'}).encode()

    narrative = LocalNarrativeGenerator(transport=invalid).generate(prediction(), risk())

    assert narrative["generator"]["mode"] == "template"
    assert narrative["generator"]["fallback_reason"] == "ollama_valueerror"
