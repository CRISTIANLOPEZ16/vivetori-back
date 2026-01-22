import logging
from uuid import UUID

from domain.models import TicketAnalysis
from domain.ports import TicketClassifier, TicketRepository

logger = logging.getLogger(__name__)


class TicketProcessorService:
    """
    Orchestrates the use-case:
    - classify ticket text
    - update ticket in repository (Supabase)
    """

    def __init__(self, repo: TicketRepository, classifier: TicketClassifier) -> None:
        self._repo = repo
        self._classifier = classifier

    def process(self, ticket_id: UUID, description: str) -> TicketAnalysis:
        analysis = self._classifier.classify(description)
        self._repo.mark_processed(ticket_id, analysis)
        return analysis
