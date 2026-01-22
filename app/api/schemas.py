from pydantic import BaseModel, Field
from uuid import UUID

from app.domain.models import TicketAnalysis, TicketCategory, TicketSentiment


class ProcessTicketRequest(BaseModel):
    ticket_id: UUID = Field(..., description="Supabase ticket UUID")
    description: str = Field(..., min_length=1, description="Ticket text content")


class ProcessTicketResponse(BaseModel):
    ticket_id: UUID
    category: TicketCategory
    sentiment: TicketSentiment
    processed: bool = True

    @staticmethod
    def from_analysis(ticket_id: UUID, analysis: TicketAnalysis) -> "ProcessTicketResponse":
        return ProcessTicketResponse(
            ticket_id=ticket_id,
            category=analysis.category,
            sentiment=analysis.sentiment,
            processed=True,
        )
