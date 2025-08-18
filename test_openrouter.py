#!/usr/bin/env python3
"""
Comprehensive OpenRouter model test
Tests multiple models to find all working options for your TruthRouter app
"""
import asyncio
import os
import json
import time
from typing import List, Dict, Optional

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system("pip install httpx")
    import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Installing python-dotenv...")
    os.system("pip install python-dotenv")
    from dotenv import load_dotenv
    load_dotenv()

class ModelTester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TruthRouter Local",
            "Content-Type": "application/json"
        }
        self.results = []
    
    async def test_model(self, model: str, category: str = "") -> Dict:
        """Test a single model and return detailed results"""
        print(f"🧪 Testing {category}: {model}")
        
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Respond with exactly: 'Test successful for [model_name]'"}],
            "max_tokens": 30
        }
        
        start_time = time.time()
        result = {
            "model": model,
            "category": category,
            "success": False,
            "response_time": 0,
            "error": None,
            "response_text": None,
            "tokens_used": 0,
            "cost_estimate": "unknown"
        }
        
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=self.headers,
                    json=body
                )
                
                result["response_time"] = round(time.time() - start_time, 2)
                
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    result.update({
                        "success": True,
                        "response_text": text.strip(),
                        "tokens_used": usage.get("total_tokens", 0),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0)
                    })
                    
                    print(f"   ✅ Success ({result['response_time']}s) - {usage.get('total_tokens', '?')} tokens")
                    print(f"      Response: {text.strip()[:60]}...")
                    
                else:
                    error_text = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_text)
                    except:
                        error_msg = error_text
                    
                    result["error"] = f"HTTP {response.status_code}: {error_msg}"
                    print(f"   ❌ Failed ({result['response_time']}s): {error_msg[:80]}...")
                    
        except asyncio.TimeoutError:
            result["error"] = "Timeout (45s)"
            result["response_time"] = 45.0
            print(f"   ⏱️  Timeout after 45 seconds")
        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = round(time.time() - start_time, 2)
            print(f"   ❌ Error: {str(e)[:80]}...")
        
        self.results.append(result)
        return result

    async def test_all_models(self):
        """Test a comprehensive list of models organized by provider"""
        
        models_to_test = [
            # OpenAI Models (most reliable)
            ("OpenAI GPT-4o", "openai/gpt-4o"),
            ("OpenAI GPT-4o Mini", "openai/gpt-4o-mini"),
            ("OpenAI GPT-4 Turbo", "openai/gpt-4-turbo"),
            ("OpenAI GPT-3.5 Turbo", "openai/gpt-3.5-turbo"),
            
            # Anthropic Claude Models
            ("Anthropic Claude 3.5 Sonnet", "anthropic/claude-3.5-sonnet"),
            ("Anthropic Claude 3 Opus", "anthropic/claude-3-opus"),
            ("Anthropic Claude 3 Sonnet", "anthropic/claude-3-sonnet"),
            ("Anthropic Claude 3 Haiku", "anthropic/claude-3-haiku"),
            
            # Google Models
            ("Google Gemini Pro 1.5", "google/gemini-pro-1.5"),
            ("Google Gemini Flash 1.5", "google/gemini-flash-1.5"),
            ("Google Gemini Pro", "google/gemini-pro"),
            
            # Meta Llama Models
            ("Meta Llama 3.1 70B", "meta-llama/llama-3.1-70b-instruct"),
            ("Meta Llama 3.1 8B", "meta-llama/llama-3.1-8b-instruct"),
            ("Meta Llama 3 70B", "meta-llama/llama-3-70b-instruct"),
            
            # Mistral Models  
            ("Mistral Large", "mistralai/mistral-large"),
            ("Mistral Medium", "mistralai/mistral-medium"),
            ("Mistral Small", "mistralai/mistral-small"),
            
            # Alternative models that might work
            ("Perplexity Llama 3.1 Sonar 70B", "perplexity/llama-3.1-sonar-large-128k-online"),
            ("Cohere Command R+", "cohere/command-r-plus"),
        ]
        
        print(f"\n🎯 Testing {len(models_to_test)} models...")
        print("=" * 60)
        
        # Test models with small delays to avoid rate limits
        for category, model in models_to_test:
            await self.test_model(model, category)
            await asyncio.sleep(1)  # Small delay between requests
        
        return self.results

    def print_summary(self):
        """Print a comprehensive summary of results"""
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        print(f"\n✅ Successful Models ({len(successful)}):")
        if successful:
            for result in successful:
                speed = "🚀" if result["response_time"] < 5 else "⚡" if result["response_time"] < 10 else "🐌"
                tokens = f"({result['tokens_used']} tokens)" if result['tokens_used'] else ""
                print(f"   {speed} {result['model']} - {result['response_time']}s {tokens}")
        else:
            print("   None")
        
        print(f"\n❌ Failed Models ({len(failed)}):")
        if failed:
            # Group failures by error type
            error_groups = {}
            for result in failed:
                error_key = result["error"][:50] if result["error"] else "Unknown error"
                if error_key not in error_groups:
                    error_groups[error_key] = []
                error_groups[error_key].append(result["model"])
            
            for error, models in error_groups.items():
                print(f"   🔸 {error}")
                for model in models:
                    print(f"     - {model}")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        
        if successful:
            # Categorize by speed and reliability
            fast_models = [r for r in successful if r["response_time"] < 5]
            reliable_models = [r for r in successful if "openai" in r["model"] or "anthropic" in r["model"]]
            
            print(f"\n🏆 Best for TruthRouter DEFAULT_MODELS (fast & reliable):")
            recommended = []
            
            # Prefer OpenAI and Anthropic for reliability
            for result in successful:
                if any(provider in result["model"] for provider in ["openai", "anthropic"]) and len(recommended) < 3:
                    recommended.append(result["model"])
            
            # Fill with other working models if needed
            for result in successful:
                if result["model"] not in recommended and len(recommended) < 3:
                    recommended.append(result["model"])
            
            for model in recommended:
                print(f"   - {model}")
            
            print(f"\n📝 Configuration for your config.py:")
            print(f"DEFAULT_MODELS = {json.dumps(recommended, indent=4)}")
            print(f"JUDGE_MODEL = \"{recommended[0]}\"")
            
            print(f"\n💡 Speed Comparison:")
            speed_sorted = sorted(successful, key=lambda x: x["response_time"])
            for i, result in enumerate(speed_sorted[:5]):
                medal = ["🥇", "🥈", "🥉", "🏅", "⭐"][min(i, 4)]
                print(f"   {medal} {result['model']}: {result['response_time']}s")
            
        else:
            print("   ❌ No models are working. Check your API key and credits.")
            print("   🔗 Visit: https://openrouter.ai/keys")
            print("   💳 Check credits: https://openrouter.ai/credits")

async def main():
    print("🔬 TruthRouter Comprehensive Model Test")
    print("This will test ~20 different models to find the best options")
    print("⏱️  This may take 2-3 minutes...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    
    tester = ModelTester(api_key)
    
    start_time = time.time()
    await tester.test_all_models()
    total_time = round(time.time() - start_time, 1)
    
    tester.print_summary()
    print(f"\n⏱️  Total test time: {total_time}s")
    print(f"🎉 Testing complete! Use the recommendations above for your app.")

if __name__ == "__main__":
    asyncio.run(main())