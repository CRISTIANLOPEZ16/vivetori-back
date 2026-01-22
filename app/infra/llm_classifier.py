import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Final, Sequence

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.config import settings
from core.errors import ExternalServiceError, ValidationError
from domain.models import TicketAnalysis, TicketCategory, TicketSentiment
from domain.ports import TicketClassifier

logger = logging.getLogger(__name__)

_HF_MODEL_ID: Final[str] = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_HF_LABEL_MAP: Final[dict[str, TicketSentiment]] = {
    "negative": TicketSentiment.NEGATIVE,
    "neutral": TicketSentiment.NEUTRAL,
    "positive": TicketSentiment.POSITIVE,
    "label_0": TicketSentiment.NEGATIVE,
    "label_1": TicketSentiment.NEUTRAL,
    "label_2": TicketSentiment.POSITIVE,
}
_BILLING_KEYWORDS: Final[tuple[str, ...]] = (
    "factura",
    "facturacion",
    "cobro",
    "pago",
    "invoice",
    "billing",
    "refund",
    "reembolso",
)
_TECHNICAL_KEYWORDS: Final[tuple[str, ...]] = (
    "error",
    "fallo",
    "falla",
    "bug",
    "crash",
    "no funciona",
    "no responde",
    "cae",
    "lento",
    "lentitud",
    "instal",
    "login",
    "acceso",
)


def _build_llm():
    provider = settings.llm_provider.lower().strip()

    if provider == "openai":
        if not settings.openai_api_key:
            raise ExternalServiceError("OPENAI_API_KEY is required for LLM_PROVIDER=openai")

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            temperature=0,
            timeout=20,
            max_retries=2,
            api_key=settings.openai_api_key,
        )

    raise ExternalServiceError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


@lru_cache(maxsize=1)
def _get_hf_sentiment_pipeline():
    try:
        from transformers import pipeline
    except Exception as e:
        logger.exception("Failed to import transformers for HF fallback")
        raise ExternalServiceError("transformers is required for the HF fallback") from e

    return pipeline("sentiment-analysis", model=_HF_MODEL_ID)


def _hf_sentiment(description: str) -> TicketSentiment:
    try:
        pipeline = _get_hf_sentiment_pipeline()
        result = pipeline(description)
    except Exception as e:
        logger.exception("HF sentiment inference failed")
        raise ExternalServiceError("HF sentiment model failed during inference") from e

    if not result:
        raise ExternalServiceError("HF sentiment model returned no results")

    label = str(result[0].get("label", "")).strip().lower()
    sentiment = _HF_LABEL_MAP.get(label)
    if not sentiment:
        raise ExternalServiceError(f"HF sentiment model returned unknown label: {label}")

    return sentiment


def _fallback_category(description: str) -> TicketCategory:
    text = description.lower()
    if any(keyword in text for keyword in _BILLING_KEYWORDS):
        return TicketCategory.BILLING
    if any(keyword in text for keyword in _TECHNICAL_KEYWORDS):
        return TicketCategory.TECHNICAL
    return TicketCategory.COMMERCIAL


def _category_values() -> str:
    return ", ".join(category.value for category in TicketCategory)


def _sentiment_values() -> str:
    return ", ".join(sentiment.value for sentiment in TicketSentiment)


@dataclass(frozen=True)
class _ClassifierEntry:
    name: str
    classifier: TicketClassifier


class LLMStructuredClassifier(TicketClassifier):
    def __init__(self) -> None:
        self._llm = _build_llm()
        self._parser = PydanticOutputParser(pydantic_object=TicketAnalysis)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente de soporte. Debes clasificar tickets con precision.\n"
                    "Reglas:\n"
                    f"- category SOLO puede ser: {_category_values()}\n"
                    f"- sentiment SOLO puede ser: {_sentiment_values()}\n"
                    "- Responde unicamente en el formato solicitado.\n"
                    "{format_instructions}",
                ),
                ("human", "Ticket:\n{description}"),
            ]
        )
        self._chain = self._prompt | self._llm | self._parser

    def classify(self, description: str) -> TicketAnalysis:
        try:
            return self._chain.invoke(
                {
                    "description": description,
                    "format_instructions": self._parser.get_format_instructions(),
                }
            )
        except OutputParserException as e:
            raise ExternalServiceError("LLM returned an invalid structured response") from e
        except Exception as e:
            raise ExternalServiceError("LLM provider failed during classification") from e


class HFTicketClassifier(TicketClassifier):
    def classify(self, description: str) -> TicketAnalysis:
        return TicketAnalysis(
            category=_fallback_category(description),
            sentiment=_hf_sentiment(description),
        )


class LastResortTicketClassifier(TicketClassifier):
    def __init__(self, default_sentiment: TicketSentiment = TicketSentiment.NEUTRAL) -> None:
        self._default_sentiment = default_sentiment

    def classify(self, description: str) -> TicketAnalysis:
        return TicketAnalysis(
            category=_fallback_category(description),
            sentiment=self._default_sentiment,
        )


class FallbackTicketClassifier(TicketClassifier):
    def __init__(self, primary: TicketClassifier | None, fallbacks: Sequence[_ClassifierEntry]) -> None:
        self._primary = primary
        self._fallbacks = tuple(fallbacks)

    def classify(self, description: str) -> TicketAnalysis:
        if not description or not description.strip():
            raise ValidationError("description is empty")

        cleaned = description.strip()
        candidates: list[_ClassifierEntry] = []
        if self._primary is not None:
            candidates.append(_ClassifierEntry("llm", self._primary))
        candidates.extend(self._fallbacks)

        for entry in candidates:
            try:
                if entry.name != "llm":
                    logger.info("Using %s fallback for ticket classification", entry.name)
                return entry.classifier.classify(cleaned)
            except ExternalServiceError as e:
                logger.warning("%s classifier failed; falling back. Reason: %s", entry.name, e)
            except Exception:
                logger.exception("%s classifier failed unexpectedly; falling back", entry.name)

        raise ExternalServiceError("All classifiers failed")


class LangChainTicketClassifier(TicketClassifier):
    """
    Single responsibility: classify a ticket with an LLM and return strongly-typed output.
    """

    def __init__(self) -> None:
        primary: TicketClassifier | None = None
        try:
            primary = LLMStructuredClassifier()
        except ExternalServiceError as e:
            logger.warning("LLM provider unavailable; will use HF fallback. Reason: %s", e)
        fallbacks = (
            _ClassifierEntry("hf", HFTicketClassifier()),
            _ClassifierEntry("last_resort", LastResortTicketClassifier()),
        )
        self._classifier = FallbackTicketClassifier(primary=primary, fallbacks=fallbacks)

    def classify(self, description: str) -> TicketAnalysis:
        return self._classifier.classify(description)
