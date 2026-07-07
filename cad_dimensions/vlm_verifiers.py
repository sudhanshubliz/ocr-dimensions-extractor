from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

from .backends import DisabledVLMVerifier, VLMVerification, VLMVerifierBackend


CAD_CROP_VERIFICATION_PROMPT = """Read only the CAD dimension annotation in this crop.
Return JSON only with these keys:
{
  "is_dimension": boolean,
  "visible_text": string,
  "nominal": string | null,
  "tolerance": string | null,
  "multiplicity": string | null,
  "needs_review": boolean,
  "confidence": number,
  "reason": string
}
Do not infer missing or hidden values. If unclear, set needs_review=true.
"""


def _json_from_text(text: str) -> dict:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _verification_from_payload(raw_text: str, payload: dict, reason_prefix: str = "") -> VLMVerification:
    confidence = payload.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence > 1:
        confidence = confidence / 100
    visible_text = str(payload.get("visible_text") or payload.get("text") or raw_text).strip()
    reason = str(payload.get("reason") or "").strip()
    if reason_prefix:
        reason = f"{reason_prefix}: {reason}".strip(": ")
    return VLMVerification(
        text=visible_text,
        needs_review=bool(payload.get("needs_review", True)),
        confidence=max(0.0, min(1.0, confidence)),
        reason=reason,
        payload=payload,
    )


class Qwen25VLVerifier(VLMVerifierBackend):
    name = "qwen2.5-vl-local"
    version = "transformers"

    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct") -> None:
        self.model_name = model_name
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        from qwen_vl_utils import process_vision_info

        self._process_vision_info = process_vision_info
        self._processor = AutoProcessor.from_pretrained(model_name)
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_name, device_map="auto")

    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(crop_path)},
                    {"type": "text", "text": CAD_CROP_VERIFICATION_PROMPT + f"\nOCR candidate: {ocr_text}"},
                ],
            }
        ]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = self._process_vision_info(messages)
        inputs = self._processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self._model.device)
        generated = self._model.generate(**inputs, max_new_tokens=256)
        output = self._processor.batch_decode(generated[:, inputs.input_ids.shape[1] :], skip_special_tokens=True)[0]
        payload = _json_from_text(output)
        return _verification_from_payload(output, payload, "qwen2.5-vl")


class DonutVerifier(VLMVerifierBackend):
    name = "donut-local"
    version = "transformers"

    def __init__(self, model_name: str = "naver-clova-ix/donut-base-finetuned-docvqa") -> None:
        from transformers import pipeline

        self._pipe = pipeline("document-question-answering", model=model_name)

    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        question = "What CAD dimension annotation is visible? Return nominal, tolerance, multiplicity, and uncertainty."
        result = self._pipe(image=str(crop_path), question=question)
        raw_text = json.dumps(result)
        answer = result[0].get("answer", "") if isinstance(result, list) and result else ""
        payload = {
            "visible_text": answer,
            "needs_review": True,
            "confidence": result[0].get("score", 0.0) if isinstance(result, list) and result else 0.0,
            "reason": "Donut verifier output is review evidence only.",
        }
        return _verification_from_payload(raw_text, payload, "donut")


class OpenAIVisionVerifier(VLMVerifierBackend):
    name = "openai-vision"
    version = "responses-api"

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI()

    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        image_b64 = base64.b64encode(crop_path.read_bytes()).decode("ascii")
        response = self._client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": CAD_CROP_VERIFICATION_PROMPT + f"\nOCR candidate: {ocr_text}"},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_b64}"},
                    ],
                }
            ],
        )
        raw_text = getattr(response, "output_text", "") or str(response)
        payload = _json_from_text(raw_text)
        return _verification_from_payload(raw_text, payload, "openai")


def select_vlm_verifier(engine: str = "disabled") -> VLMVerifierBackend:
    normalized = engine.lower()
    if normalized in {"disabled", "none", "off"}:
        return DisabledVLMVerifier()
    if normalized == "qwen":
        return Qwen25VLVerifier(os.getenv("CAD_QWEN_VL_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct"))
    if normalized == "donut":
        return DonutVerifier(os.getenv("CAD_DONUT_MODEL", "naver-clova-ix/donut-base-finetuned-docvqa"))
    if normalized == "openai":
        return OpenAIVisionVerifier(os.getenv("CAD_OPENAI_VISION_MODEL", "gpt-4.1-mini"))
    raise ValueError(f"Unknown VLM verifier: {engine}")
