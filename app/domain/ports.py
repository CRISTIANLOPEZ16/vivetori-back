from typing import Protocol
from uuid import UUID
from app.domain.models import TicketAnalysis


class TicketRepository(Protocol):
    def mark_processed(self, ticket_id: UUID, analysis: TicketAnalysis) -> None: ...


class TicketClassifier(Protocol):
    def classify(self, description: str) -> TicketAnalysis: ...
