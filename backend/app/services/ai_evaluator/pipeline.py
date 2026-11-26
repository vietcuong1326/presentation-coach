import json
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.schemas.feedback import AnalysisReportPayload, CriterionResult
from app.services.ai_evaluator.rubric_data import RUBRIC_CRITERIA, RUBRIC_LEVELS


SYSTEM_EVALUATION_PROMPT = """You are an expert English Presentation Coach evaluating a student's presentation according to official rubric standards.

CORE PRODUCT PRINCIPLES:
1. FEEDBACK-FIRST, SCORE-SECOND: Your primary purpose is to provide clear, actionable coaching. Scores are strictly secondary.
2. EVIDENCE-BASED: Never criticize without observable evidence from the slide text or transcript. Quote phrases or reference timestamps/slides.
3. MISSING EVIDENCE MEANS NOT_EVALUATED: If a criterion cannot be evaluated due to missing evidence or because it is outside MVP scope (e.g., EYE_CONTACT_POSTURE, PUNCTUALITY, MCQ_TEST), you MUST set status to 'NOT_EVALUATED' and score to null. NEVER assign score 0 or 1 for missing data!
4. NON-REDUNDANT: Do not repeat the same feedback item under multiple criteria. Merge duplicate observations into one clear improvement item.
5. NO HALLUCINATION: Never invent timestamps, transcript quotes, slide content, or student names.
6. CONSTRUCTIVE & ACTIONABLE: Every improvement must include observation, impact on audience, practical recommendation, and a concrete example rewrite.

You must output a single valid JSON object adhering strictly to the schema provided."""


class AIEvaluationPipeline:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_EVALUATION_MODEL or "gpt-4o-mini"

    def build_user_prompt(
        self,
        project_meta: Dict[str, Any],
        slide_pages: List[Dict[str, Any]],
        transcript: Dict[str, Any],
    ) -> str:
        members_text = ""
        if project_meta.get("members"):
            members_text = "\nGroup Members & Approximate Time Ranges:\n"
            for m in project_meta["members"]:
                members_text += f"- {m.get('name')}: {m.get('start_time_seconds')}s - {m.get('end_time_seconds')}s\n"

        slides_text = "Presentation Slides:\n"
        if slide_pages:
            for s in slide_pages:
                slides_text += f"[Slide {s.get('page_number')}]: {s.get('text')}\n"
        else:
            slides_text += "(No slide text provided)\n"

        transcript_text = "Speech Transcript (from Audio):\n"
        full_text = transcript.get("full_text", "")
        if full_text:
            transcript_text += full_text[:4000] + ("..." if len(full_text) > 4000 else "")
            if transcript.get("segments"):
                transcript_text += "\n\nKey Timestamped Segments:\n"
                for seg in transcript["segments"][:30]:
                    transcript_text += f"[{seg.get('start')}s - {seg.get('end')}s]: {seg.get('text')}\n"
        else:
            transcript_text += "(No audio transcript available)\n"

        prompt = f"""EVALUATE THIS PRESENTATION:

Project Information:
- Title: {project_meta.get('title')}
- Topic: {project_meta.get('topic', 'N/A')}
- Objectives: {project_meta.get('objectives', 'N/A')}
- Target Audience: {project_meta.get('target_audience', 'N/A')}
- Presentation Type: {project_meta.get('presentation_type', 'INDIVIDUAL')}
- Expected Duration: {project_meta.get('expected_duration_seconds', 'Flexible')}s
{members_text}

{slides_text}

{transcript_text}

RUBRIC CRITERIA TO EVALUATE (1 to 5 scale: 5=SUPERIOR, 4=EXCELLENT, 3=VERY_GOOD, 2=SATISFACTORY, 1=UNACCEPTABLE):
1. PREPARATION (Attitude - Group)
2. COOPERATION (Attitude - Group)
3. PUNCTUALITY (Attitude - Group - NOTE: Must be NOT_EVALUATED if submission metadata is absent)
4. ENTHUSIASM (Attitude - Individual)
5. CONTENT (Project - Group)
6. LOGICALITY (Project - Group)
7. CREATIVITY (Project - Group)
8. EFFECTIVENESS (Project - Group)
9. MEANINGFULNESS (Project - Group)
10. REFERENCES (Project - Group)
11. SCALE (Project - Group)
12. LAYOUT (Presentation - Group)
13. ENGAGING_AUDIENCE (Presentation - Individual)
14. SPEECH_VOLUME_SPEED (Presentation - Individual)
15. LANGUAGE_SKILLS (Presentation - Individual)
16. PRONUNCIATION (Presentation - Individual)
17. EYE_CONTACT_POSTURE (Presentation - Individual - NOTE: Must be NOT_EVALUATED, visual video analysis outside MVP)
18. ACTIVE_PARTICIPATION (Presentation - Individual)
19. MCQ_TEST (Presentation - Group - NOTE: Must be NOT_EVALUATED if quiz data is absent)
20. REPORT (Presentation - Group - NOTE: Evaluate only if written report is present, otherwise NOT_EVALUATED)

JSON Output Structure:
{{
  "evaluation_summary": {{
    "headline": "Short 1-sentence verdict",
    "overall_feedback": "Constructive 2-3 paragraph coaching summary grounded in materials",
    "evidence_coverage": {{
      "evaluated_criteria": <int>,
      "not_evaluated_criteria": <int>
    }}
  }},
  "strengths": [
    {{
      "title": "Clear strength title",
      "description": "Specific explanation with evidence",
      "evidence_ids": ["ev-1"],
      "related_criteria": ["CONTENT"]
    }}
  ],
  "improvements": [
    {{
      "id": "fb-1",
      "title": "Clear action-oriented title",
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "scope": "GROUP" | "INDIVIDUAL",
      "member_id": null,
      "observation": "What was observed in slide or speech",
      "impact": "Why it affects audience understanding",
      "recommendation": "Concrete suggestion to improve",
      "example": "Sample phrase or slide rewrite",
      "evidence_ids": ["ev-2"],
      "related_criteria": ["LOGICALITY"]
    }}
  ],
  "criterion_results": [
    {{
      "criterion_id": "CRITERION_NAME",
      "scope": "GROUP" | "INDIVIDUAL",
      "member_id": null,
      "status": "EVALUATED" | "NOT_EVALUATED",
      "score": 1..5 or null,
      "level": "SUPERIOR" | "EXCELLENT" | "VERY_GOOD" | "SATISFACTORY" | "UNACCEPTABLE" or null,
      "reason": "Clear explanation grounded in evidence or explaining why not evaluated",
      "evidence_ids": [],
      "confidence": 0.0 to 1.0 or null
    }}
  ],
  "priority_actions": [
    {{
      "title": "Action title",
      "steps": ["Step 1", "Step 2"],
      "related_feedback_ids": ["fb-1"]
    }}
  ]
}}
"""
        return prompt

    async def evaluate_presentation(
        self,
        project_meta: Dict[str, Any],
        slide_pages: List[Dict[str, Any]],
        transcript: Dict[str, Any],
    ) -> AnalysisReportPayload:
        is_gemini = (settings.AI_PROVIDER or "").lower().strip() == "gemini" or (bool(settings.GEMINI_API_KEY) and not self.api_key)
        if is_gemini:
            return await self.evaluate_with_gemini(project_meta, slide_pages, transcript)
        return await self.evaluate_with_openai(project_meta, slide_pages, transcript)

    async def evaluate_with_openai(
        self,
        project_meta: Dict[str, Any],
        slide_pages: List[Dict[str, Any]],
        transcript: Dict[str, Any],
    ) -> AnalysisReportPayload:
        if not self.api_key:
            raise AppException(
                code="API_KEY_MISSING",
                message="OpenAI API key is required for AI evaluation.",
                status_code=500,
            )

        user_prompt = self.build_user_prompt(project_meta, slide_pages, transcript)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_EVALUATION_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    err_text = resp.text
                    try:
                        err_json = resp.json()
                        err_detail = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_detail = err_text[:200]
                    raise AppException(
                        code="AI_EVALUATION_ERROR",
                        message=f"OpenAI evaluation failed ({resp.status_code}): {err_detail}",
                        status_code=500,
                    )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content)
                return self._parse_and_validate_report(parsed_json)
        except json.JSONDecodeError as e:
            raise AppException(
                code="AI_OUTPUT_FORMAT_ERROR",
                message=f"Model output could not be parsed as JSON: {str(e)}",
                status_code=500,
            )
        except httpx.RequestError as e:
            raise AppException(
                code="AI_NETWORK_ERROR",
                message=f"Network error communicating with AI evaluation service: {str(e)}",
                status_code=500,
            )

    async def evaluate_with_gemini(
        self,
        project_meta: Dict[str, Any],
        slide_pages: List[Dict[str, Any]],
        transcript: Dict[str, Any],
    ) -> AnalysisReportPayload:
        if not settings.GEMINI_API_KEY:
            raise AppException(
                code="API_KEY_MISSING",
                message="Google Gemini API key is required when AI_PROVIDER is set to 'gemini'.",
                status_code=500,
            )

        user_prompt = self.build_user_prompt(project_meta, slide_pages, transcript)

        model_name = settings.GEMINI_MODEL or "gemini-3.5-flash"
        candidates = [model_name]
        for fallback in ("gemini-3.5-flash", "gemini-3-flash-preview"):
            if fallback not in candidates:
                candidates.append(fallback)

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_EVALUATION_PROMPT}],
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }

        last_error = None
        for candidate in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed_json = json.loads(content)
                        return self._parse_and_validate_report(parsed_json)

                    err_text = resp.text
                    try:
                        err_json = resp.json()
                        err_detail = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_detail = err_text[:200]
                    last_error = f"Gemini evaluation failed on {candidate} ({resp.status_code}): {err_detail}"
                    if resp.status_code in (404, 503) and candidate != candidates[-1]:
                        continue
                    raise AppException(
                        code="AI_EVALUATION_ERROR",
                        message=last_error,
                        status_code=500,
                    )
            except json.JSONDecodeError as e:
                raise AppException(
                    code="AI_OUTPUT_FORMAT_ERROR",
                    message=f"Model output could not be parsed as JSON: {str(e)}",
                    status_code=500,
                )
            except httpx.RequestError as e:
                last_error = f"Network error communicating with Gemini evaluation service on {candidate}: {str(e)}"
                if candidate != candidates[-1]:
                    continue
                raise AppException(
                    code="AI_NETWORK_ERROR",
                    message=last_error,
                    status_code=500,
                )

        raise AppException(
            code="AI_EVALUATION_ERROR",
            message=last_error or "All candidate Gemini models failed for evaluation.",
            status_code=500,
        )

    def _parse_and_validate_report(self, parsed_json: Dict[str, Any]) -> AnalysisReportPayload:
        # Post-process: Guarantee EYE_CONTACT_POSTURE is NOT_EVALUATED
        for crit in parsed_json.get("criterion_results", []):
            if crit.get("criterion_id") in ("EYE_CONTACT_POSTURE", "PUNCTUALITY", "MCQ_TEST"):
                crit["status"] = "NOT_EVALUATED"
                crit["score"] = None
                crit["level"] = None
                crit["confidence"] = None

        # Calculate counts
        eval_count = sum(1 for c in parsed_json.get("criterion_results", []) if c.get("status") == "EVALUATED")
        not_eval_count = sum(1 for c in parsed_json.get("criterion_results", []) if c.get("status") == "NOT_EVALUATED")
        if "evidence_coverage" in parsed_json.get("evaluation_summary", {}):
            parsed_json["evaluation_summary"]["evidence_coverage"]["evaluated_criteria"] = eval_count
            parsed_json["evaluation_summary"]["evidence_coverage"]["not_evaluated_criteria"] = not_eval_count

        # Validate with Pydantic
        return AnalysisReportPayload(**parsed_json)


ai_evaluation_pipeline = AIEvaluationPipeline()

