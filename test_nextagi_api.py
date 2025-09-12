#!/usr/bin/env python3
"""
NextAGI API Testing Script
Tests various endpoints and configurations
"""

import requests
import json
import time
from typing import Dict, List

API_URL = "http://localhost:8000"
API_KEY = "your-test-key"  # Replace with actual key


def test_query(payload: Dict) -> Dict:
    """Test the main query endpoint"""
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    start_time = time.time()
    response = requests.post(f"{API_URL}/api/v1/query", headers=headers, json=payload)
    end_time = time.time()

    print(f"⏱️  Request took: {end_time - start_time:.2f}s")
    print(f"📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Request ID: {data.get('request_id')}")
        print(f"🎯 Confidence: {data.get('confidence', 0) * 100:.1f}%")
        print(f"🏆 Winner Model: {data.get('winner_model')}")
        print(f"⚡ Response Time: {data.get('response_time_ms', 0) / 1000:.1f}s")
        print(f"🤖 Models Used: {', '.join(data.get('models_used', []))}")
        print(f"💰 Estimated Cost: ${data.get('estimated_cost', 0):.4f}")

        if "reasoning" in data:
            print(f"\n📝 Reasoning: {data['reasoning'][:200]}...")

        return data
    else:
        print(f"❌ Error: {response.text}")
        return {}


def run_test_suite():
    """Run comprehensive test suite"""

    tests = [
        {
            "name": "1. Speed Test - Simple Query",
            "payload": {
                "prompt": "What year was the iPhone first released?",
                "mode": "speed",
                "max_models": 2,
            },
        },
        {
            "name": "2. Quality Test - Complex Legal",
            "payload": {
                "prompt": "Analyze the implications of the Chevron doctrine and how it might change with recent Supreme Court challenges",
                "mode": "quality",
                "max_models": 5,
                "include_reasoning": True,
                "custom_models": [
                    "openai/gpt-4o",
                    "anthropic/claude-3.5-sonnet",
                    "google/gemini-pro",
                    "openai/gpt-4-turbo",
                    "anthropic/claude-3-opus",
                ],
            },
        },
        {
            "name": "3. Hallucination Test",
            "payload": {
                "prompt": "What was the holding in the Supreme Court case Johnson v. Microsoft (2019)?",
                "mode": "quality",
                "max_models": 4,
                "include_reasoning": True,
            },
        },
        {
            "name": "4. Cost-Optimized Query",
            "payload": {
                "prompt": "List the elements of a valid contract",
                "mode": "cost",
                "budget_limit": 0.01,
                "max_models": 2,
            },
        },
    ]

    for test in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test['name']}")
        print(f"{'='*60}")

        result = test_query(test["payload"])

        # Brief pause between tests
        time.sleep(2)


def test_health_endpoint():
    """Test the health check endpoint"""
    response = requests.get(f"{API_URL}/health")
    print(f"Health Check: {response.json()}")


if __name__ == "__main__":
    print("🚀 NextAGI API Test Suite")
    print("=" * 60)

    # Test health endpoint first
    test_health_endpoint()

    # Run main test suite
    run_test_suite()

    print("\n✅ Test suite completed!")
