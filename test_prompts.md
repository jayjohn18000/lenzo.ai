{
  "optimized_tests": [
    {
      "name": "Speed Test - Fastest Models",
      "description": "Test the fastest models from your results",
      "payload": {
        "prompt": "What is artificial intelligence?",
        "options": {
          "model_selection_mode": "speed",
          "models": [
            "mistralai/mistral-small",
            "google/gemini-flash-1.5", 
            "openai/gpt-3.5-turbo"
          ]
        }
      }
    },
    {
      "name": "Quality Test - Premium Models",  
      "description": "Test highest quality models",
      "payload": {
        "prompt": "Explain quantum computing and its potential applications in cryptography",
        "options": {
          "model_selection_mode": "quality",
          "models": [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus"
          ]
        }
      }
    },
    {
      "name": "Cost-Optimized Test",
      "description": "Test most cost-effective models",
      "payload": {
        "prompt": "Summarize the benefits of renewable energy",
        "options": {
          "model_selection_mode": "cost",
          "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "mistralai/mistral-small"
          ]
        }
      }
    },
    {
      "name": "Balanced Mix Test",
      "description": "Test the recommended balanced configuration",
      "payload": {
        "prompt": "Compare different machine learning algorithms",
        "options": {
          "model_selection_mode": "balanced"
        }
      }
    },
    {
      "name": "Provider Diversity Test",
      "description": "Test one model from each working provider",
      "payload": {
        "prompt": "What are the latest trends in software development?",
        "options": {
          "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku", 
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-small"
          ]
        }
      }
    },
    {
      "name": "Fallback Test",
      "description": "Test with fallback models",
      "payload": {
        "prompt": "Explain climate change",
        "options": {
          "models": [
            "openai/gpt-3.5-turbo",
            "meta-llama/llama-3-70b-instruct",
            "mistralai/mistral-large",
            "cohere/command-r-plus"
          ]
        }
      }
    }
  ],
  
  "performance_benchmarks": [
    {
      "name": "Speed Benchmark",
      "curl": "curl -X POST \"http://localhost:8000/route\" -H \"Content-Type: application/json\" -d '{\"prompt\": \"Hello world\", \"options\": {\"model_selection_mode\": \"speed\"}}'"
    },
    {
      "name": "Quality Benchmark", 
      "curl": "curl -X POST \"http://localhost:8000/route\" -H \"Content-Type: application/json\" -d '{\"prompt\": \"Explain machine learning\", \"options\": {\"model_selection_mode\": \"quality\"}}'"
    }
  ]
}