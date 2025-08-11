# lenzo.ai — TruthRouter

**TruthRouter** is a FastAPI-powered backend that queries multiple large language models (via OpenRouter and other APIs), evaluates their answers against defined traits, and returns the most accurate, trustworthy response.

🚀 Features:
- Multi-LLM querying (OpenAI, Anthropic, Mistral, and more)
- Customizable scoring logic (clarity, accuracy, non-hallucination, etc.)
- Example prompts for testing
- Docker-ready for easy deployment

📦 Tech Stack:
- FastAPI + Uvicorn
- HTTPX
- OpenRouter API
- Pydantic for schema validation
- Python-dotenv for environment configuration
