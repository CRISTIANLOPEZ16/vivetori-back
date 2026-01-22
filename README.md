# AI Support Co-Pilot API

FastAPI service that classifies support tickets and writes results back to Supabase.
It uses an LLM first, then falls back to a local Hugging Face sentiment model and
keyword-based category heuristics if the LLM is unavailable or fails.

## What this service does
- Exposes a `/process-ticket` endpoint that accepts a ticket UUID and description.
- Classifies the ticket into:
  - category: `Tecnico | Facturacion | Comercial`
  - sentiment: `Positivo | Neutral | Negativo`
- Updates the `tickets` table in Supabase with `category`, `sentiment`, and `processed=true`.

## Classification flow (with fallbacks)
1. LLM classification (LangChain + OpenAI)
   - Structured output is enforced with a Pydantic parser.
   - If the provider is not configured or fails, it falls back.
2. Hugging Face sentiment + keyword-based category
   - Sentiment uses `cardiffnlp/twitter-xlm-roberta-base-sentiment`.
   - Category uses keyword matching for billing/technical; otherwise `Comercial`.
3. Last resort fallback
   - Category uses the same keyword matcher.
   - Sentiment defaults to `Neutral`.

Any classifier failure logs and triggers the next fallback until one succeeds.

## API

### Health check
`GET /health`

Response:
```
{"status":"ok"}
```

### Process ticket
`POST /process-ticket`

Request body:
```
{
  "ticket_id": "uuid",
  "description": "string"
}
```

Response:
```
{
  "ticket_id": "uuid",
  "category": "Tecnico|Facturacion|Comercial",
  "sentiment": "Positivo|Neutral|Negativo",
  "processed": true
}
```

## Error handling
Exceptions are mapped to HTTP status codes in `app/main.py`:
- `ValidationError` -> 422
- `NotFoundError` -> 404
- `RepositoryError` -> 502
- `ExternalServiceError` -> 503
- Unhandled exceptions -> 500

## Configuration
Settings are loaded from `.env` via `pydantic-settings` and `python-dotenv`.

Required:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional:
- `LLM_PROVIDER` (default: `openai`)
- `LLM_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_API_KEY` (required when `LLM_PROVIDER=openai`)
- `LOG_LEVEL` (default: `INFO`)

Note: Only `openai` is supported as a primary LLM provider today. Any other value
causes the LLM layer to be skipped and fallbacks to be used instead.

## Supabase expectations
This service updates the `tickets` table:
- `id` (UUID, used to locate the record)
- `category` (string)
- `sentiment` (string)
- `processed` (boolean)

If the record does not exist, the service returns 404.

## Local setup
1. Create a virtual environment and install dependencies:
```
python -m venv venv
.\venv\Scripts\activate
pip install -r app/requirements.txt
```

2. Create `.env` from `.env.example` and set real secrets:
```
Copy-Item .env.example .env
```

3. Run the API:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project layout
- `app/main.py`: FastAPI app setup and error handlers
- `app/api/routes.py`: API routes
- `app/api/schemas.py`: Request/response models
- `app/services/ticket_processor.py`: Use-case orchestration
- `app/infra/llm_classifier.py`: LLM + fallback classifier chain
- `app/infra/supabase_repo.py`: Supabase repository implementation
- `app/core/config.py`: Environment-driven settings
- `app/core/errors.py`: Domain errors

## Notes
- The HF fallback requires heavy ML dependencies (`transformers`, `torch`).
- LLM responses must match the expected schema; invalid responses trigger fallback.
