from enum import StrEnum
from pydantic import BaseModel, Field
from uuid import UUID


class TicketCategory(StrEnum):
    TECHNICAL = "Tecnico"
    BILLING = "Facturacion"
    COMMERCIAL = "Comercial"


class TicketSentiment(StrEnum):
    POSITIVE = "Positivo"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negativo"


class Ticket(BaseModel):
    id: UUID
    description: str
    category: TicketCategory | None = None
    sentiment: TicketSentiment | None = None
    processed: bool = False


class TicketAnalysis(BaseModel):
    category: TicketCategory = Field(..., description="Tecnico | Facturacion | Comercial")
    sentiment: TicketSentiment = Field(..., description="Positivo | Neutral | Negativo")
