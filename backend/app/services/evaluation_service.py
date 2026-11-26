import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.repositories.project_repository import project_repository, ProjectRepository
from app.repositories.file_repository import file_repository, FileRepository
from app.repositories.evaluation_repository import evaluation_repository, EvaluationRepository
from app.services.file_processing.pdf_extractor import extract_text_from_pdf
from app.services.file_processing.pptx_extractor import extract_text_from_pptx
from app.services.file_processing.media_extractor import extract_audio_bytes_from_video
from app.services.transcription.service import transcription_service, TranscriptionService
from app.services.ai_evaluator.pipeline import ai_evaluation_pipeline, AIEvaluationPipeline
from app.schemas.evaluation import EvaluationStatusResponse

logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(
        self,
        eval_repo: EvaluationRepository = evaluation_repository,
        file_repo: FileRepository = file_repository,
        transcriber: TranscriptionService = transcription_service,
        evaluator: AIEvaluationPipeline = ai_evaluation_pipeline,
        proj_repo: Optional[ProjectRepository] = None,
    ):
        self.eval_repo = eval_repo
        self.file_repo = file_repo
        self.transcriber = transcriber
        self.evaluator = evaluator
        self.proj_repo = proj_repo or project_repository

    async def get_file_bytes(self, storage_path: str) -> bytes:
        """Downloads private file bytes from Supabase storage."""
        dl_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/presentations/{storage_path}"
        headers = {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(dl_url, headers=headers)
            if resp.status_code == 200:
                return resp.content
            return b""

    async def start_evaluation(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Verifies ownership and initializes or retrieves the PENDING evaluation for this project."""
        project = await self.proj_repo.get_by_id(project_id, user_id)
        if not project:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Project not found or not owned by user.",
                status_code=404,
            )

        # Retrieve existing PENDING evaluation that has uploaded files attached
        eval_id = await self.file_repo.get_or_create_pending_evaluation(project_id, user_id)
        return {"id": eval_id, "status": "PENDING"}

    async def run_evaluation_pipeline(self, evaluation_id: str, project_id: str, user_id: str):
        """Asynchronous execution of extraction, transcription and AI evaluation."""
        try:
            await self.eval_repo.update_status(evaluation_id, "PROCESSING")

            # 1. Fetch project metadata
            project = await self.proj_repo.get_by_id(project_id, user_id)
            if not project:
                raise Exception("Project missing during evaluation processing")

            project_meta = project.model_dump()

            # 2. Fetch uploaded files
            files = await self.file_repo.list_files_by_evaluation(evaluation_id, user_id)

            slide_file = next((f for f in files if f.get("file_role") == "SLIDES"), None)
            media_file = next((f for f in files if f.get("file_role") in ("AUDIO", "VIDEO")), None)

            # 3. Extract slides text if present
            slide_pages = []
            if slide_file:
                file_bytes = await self.get_file_bytes(slide_file["storage_path"])
                if file_bytes:
                    ext = slide_file["original_filename"].split(".")[-1].lower()
                    if ext == "pdf":
                        slide_pages = extract_text_from_pdf(file_bytes)
                    elif ext == "pptx":
                        slide_pages = extract_text_from_pptx(file_bytes)

            # 4. Transcribe audio if media file present
            transcript_data = {"full_text": "", "segments": []}
            if media_file:
                media_bytes = await self.get_file_bytes(media_file["storage_path"])
                if media_bytes:
                    original_name = media_file["original_filename"]
                    ext = original_name.split(".")[-1].lower()

                    # Video in MVP is an audio source only: extract audio track to MP3
                    if media_file.get("file_role") == "VIDEO" or ext == "mp4":
                        audio_payload = extract_audio_bytes_from_video(media_bytes)
                        audio_filename = "extracted_audio.mp3"
                    else:
                        audio_payload = media_bytes
                        audio_filename = original_name

                    transcript_res = await self.transcriber.transcribe_audio(
                        audio_bytes=audio_payload,
                        filename=audio_filename,
                    )
                    transcript_data = transcript_res
                    # Save transcript
                    await self.eval_repo.save_transcript(
                        evaluation_id=evaluation_id,
                        language=transcript_res.get("language", "en"),
                        full_text=transcript_res.get("full_text", ""),
                        segments=transcript_res.get("segments", []),
                        provider=transcript_res.get("provider", "whisper"),
                    )

            # 5. Run AI Evaluator Pipeline
            report = await self.evaluator.evaluate_presentation(
                project_meta=project_meta,
                slide_pages=slide_pages,
                transcript=transcript_data,
            )

            # 6. Save Analysis Report
            eval_count = report.evaluation_summary.evidence_coverage.evaluated_criteria
            not_eval_count = report.evaluation_summary.evidence_coverage.not_evaluated_criteria

            await self.eval_repo.save_analysis_report(
                evaluation_id=evaluation_id,
                report_json=report.model_dump(),
                evaluated_count=eval_count,
                not_evaluated_count=not_eval_count,
                version=1,
            )

            # 7. Final status
            final_status = "PARTIAL" if not_eval_count > 0 else "COMPLETED"
            await self.eval_repo.update_status(evaluation_id, final_status)

        except Exception as e:
            logger.error(f"Evaluation pipeline failed for {evaluation_id}: {str(e)}", exc_info=True)
            await self.eval_repo.update_status(
                evaluation_id=evaluation_id,
                status="FAILED",
                error_code="PIPELINE_ERROR",
                error_message=f"Evaluation failed: {str(e)[:400]}",
            )

    async def get_evaluation_status(self, evaluation_id: str, user_id: str) -> EvaluationStatusResponse:
        eval_row = await self.eval_repo.get_by_id(evaluation_id, user_id)
        if not eval_row:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Evaluation not found or not owned by user.",
                status_code=404,
            )
        return EvaluationStatusResponse(**eval_row)

    async def get_latest_report(self, evaluation_id: str, user_id: str) -> Dict[str, Any]:
        report_row = await self.eval_repo.get_latest_report(evaluation_id, user_id)
        if not report_row:
            eval_row = await self.get_evaluation_status(evaluation_id, user_id)
            if eval_row.status in ("PENDING", "PROCESSING"):
                return {
                    "status": eval_row.status,
                    "message": "Evaluation is currently processing. Please check back shortly.",
                }
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Report not found for this evaluation.",
                status_code=404,
            )
        return report_row

    async def list_user_evaluations(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        evals = await self.eval_repo.list_by_user(user_id, limit)
        successful_evals = [e for e in evals if e.get("status") in ("COMPLETED", "PARTIAL")]
        projects = await self.proj_repo.list_by_user(user_id)
        proj_map = {str(p.id): p for p in projects}
        results = []
        for e in successful_evals:
            p = proj_map.get(str(e.get("project_id")), None)
            e_dict = dict(e)
            e_dict["project_title"] = p.title if p else "Presentation Project"
            e_dict["presentation_type"] = p.presentation_type if p else "INDIVIDUAL"
            results.append(e_dict)
        return results

    async def list_project_evaluations(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        project = await self.proj_repo.get_by_id(project_id, user_id)
        if not project:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Project not found or not owned by user.",
                status_code=404,
            )
        evals = await self.eval_repo.list_by_project(project_id, user_id)
        successful_evals = [e for e in evals if e.get("status") in ("COMPLETED", "PARTIAL")]
        results = []
        for e in successful_evals:
            e_dict = dict(e)
            e_dict["project_title"] = project.title
            e_dict["presentation_type"] = project.presentation_type
            results.append(e_dict)
        return results

    async def get_transcript(self, evaluation_id: str, user_id: str) -> Dict[str, Any]:
        """Verify ownership before returning transcript so unauthorized callers receive 404."""
        await self.get_evaluation_status(evaluation_id, user_id)
        transcript = await self.eval_repo.get_transcript(evaluation_id, user_id)
        if not transcript:
            return {"transcript": None}
        return transcript

    async def delete_evaluation(self, evaluation_id: str, user_id: str) -> Dict[str, str]:
        """Delete an owned evaluation and clean up associated private storage objects."""
        await self.get_evaluation_status(evaluation_id, user_id)
        files = await self.file_repo.list_files_by_evaluation(evaluation_id, user_id)
        storage_paths = [f["storage_path"] for f in files if f.get("storage_path")]
        if storage_paths:
            try:
                await self.file_repo.delete_from_storage(storage_paths)
            except Exception as e:
                logger.warning(f"Failed to cleanup storage objects for evaluation {evaluation_id}: {e}")

        deleted = await self.eval_repo.delete(evaluation_id, user_id)
        if not deleted:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Evaluation not found or not owned by user.",
                status_code=404,
            )
        return {"status": "deleted"}


evaluation_service = EvaluationService()
