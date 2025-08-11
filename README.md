# lenzo.ai — TruthRouter

**TruthRouter** is a FastAPI-powered backend that queries multiple large language models (LLMs) — including GPT-4, Claude, Gemini, and Mistral — evaluates their answers against defined traits, and returns the most accurate, trustworthy response.

## 🚀 Features
- Multi-LLM querying via OpenAI, OpenRouter, Anthropic, and more
- GPT-4-based scoring engine for truthfulness and clarity
- Configurable evaluation traits (accuracy, clarity, jargon control, etc.)
- Example prompts for testing and benchmarking
- Optional Streamlit or Next.js frontend
- Stripe integration for monetization
- Docker-ready for deployment

## 📦 Tech Stack
- **Backend:** FastAPI + Uvicorn (async)
- **LLM APIs:** OpenAI, Anthropic, Mistral, Gemini via OpenRouter
- **Scoring Engine:** GPT-4 judge, customizable evaluation metrics
- **Environment Management:** Python-dotenv
- **Schema Validation:** Pydantic

## 🛠 Setup

1. **Clone the repo**
```bash
git clone https://github.com/jayjohn18000/lenzo.ai.git
cd lenzo.ai
