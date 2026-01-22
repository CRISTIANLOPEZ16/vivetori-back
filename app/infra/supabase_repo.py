import logging
from uuid import UUID

from supabase import create_client, Client

from app.core.errors import NotFoundError, RepositoryError
from app.domain.models import TicketAnalysis
from app.domain.ports import TicketRepository


logger = logging.getLogger(__name__)


class SupabaseTicketRepository(TicketRepository):
    def __init__(self, supabase_url: str, supabase_service_role_key: str) -> None:
        self._client: Client = create_client(supabase_url, supabase_service_role_key)

    def mark_processed(self, ticket_id: UUID, analysis: TicketAnalysis) -> None:
        try:
            resp = (
                self._client.table("tickets")
                .update(
                    {
                        "category": analysis.category.value,
                        "sentiment": analysis.sentiment.value,
                        "processed": True,
                    }
                )
                .eq("id", str(ticket_id))
                .execute()
            )

            data = getattr(resp, "data", None)
            if not data:
                raise NotFoundError(f"Ticket not found: {ticket_id}")

        except NotFoundError:
            raise
        except Exception as e:
            logger.exception("Supabase update failed")
            raise RepositoryError("Failed to update ticket in Supabase") from e
