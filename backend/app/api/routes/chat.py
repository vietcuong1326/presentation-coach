from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, AuthenticatedUser
from app.schemas.chat import ChatMessageCreate, ChatResponse, ChatHistoryResponse
from app.services.chatbot.service import ChatbotService

router = APIRouter(tags=["Chatbot"])

_default_chatbot_service = ChatbotService()


def get_chatbot_service() -> ChatbotService:
    return _default_chatbot_service


@router.post(
    "/evaluations/{evaluation_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def send_chat_message(
    evaluation_id: str,
    payload: ChatMessageCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    """Ask a follow-up coaching question grounded in the evaluation report."""
    res = await service.chat(
        evaluation_id=evaluation_id,
        user_id=current_user.id,
        message=payload.message,
        session_id=str(payload.session_id) if payload.session_id else None,
    )
    return res


@router.get(
    "/evaluations/{evaluation_id}/chat",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_history(
    evaluation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    """Retrieve prior chat sessions and messages for this evaluation."""
    return await service.get_history(evaluation_id, current_user.id)

