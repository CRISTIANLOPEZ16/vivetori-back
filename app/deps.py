from functools import lru_cache

from core.config import settings
from infra.supabase_repo import SupabaseTicketRepository
from infra.llm_classifier import LangChainTicketClassifier
from services.ticket_processor import TicketProcessorService


@lru_cache(maxsize=1)
def get_ticket_repository() -> SupabaseTicketRepository:
    return SupabaseTicketRepository(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache(maxsize=1)
def get_ticket_classifier() -> LangChainTicketClassifier:
    return LangChainTicketClassifier()


def get_ticket_service() -> TicketProcessorService:
    return TicketProcessorService(repo=get_ticket_repository(), classifier=get_ticket_classifier())
