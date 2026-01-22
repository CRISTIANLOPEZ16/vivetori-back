from fastapi import APIRouter, Depends

from api.schemas import ProcessTicketRequest, ProcessTicketResponse
from services.ticket_processor import TicketProcessorService
from deps import get_ticket_service

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@router.post("/process-ticket", response_model=ProcessTicketResponse, tags=["tickets"])
def process_ticket(
    payload: ProcessTicketRequest,
    svc: TicketProcessorService = Depends(get_ticket_service),
):
    analysis = svc.process(payload.ticket_id, payload.description)
    return ProcessTicketResponse.from_analysis(payload.ticket_id, analysis)
