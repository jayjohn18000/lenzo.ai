# reset_circuit_breaker.py
"""
NextAGI Circuit Breaker Reset & Diagnostic Tool
Fixes the "0 models available" issue by resetting circuit breaker and checking config
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CircuitBreakerDiagnostic:
    """Diagnostic and reset tool for NextAGI circuit breaker"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        logger.info("🔍 Checking system status...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}", "details": response.text}
            except Exception as e:
                return {"error": str(e)}

    async def check_configuration_mismatch(self) -> Dict[str, Any]:
        """Check for configuration mismatches"""
        logger.info("⚙️ Checking configuration...")
        
        # Try to get metrics which should show configuration
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/metrics")
                if response.status_code == 200:
                    metrics = response.json()
                    return {
                        "success": True,
                        "metrics": metrics
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "details": response.text
                    }
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def test_single_model_directly(self) -> Dict[str, Any]:
        """Test a single known model directly to bypass circuit breaker"""
        logger.info("🧪 Testing single model directly...")
        
        # Test with a simple, reliable model
        test_models = [
            "openai/gpt-4o-mini",
            "openai/gpt-3.5-turbo", 
            "anthropic/claude-3-haiku",
            "google/gemini-flash-1.5"
        ]
        
        results = {}
        
        for model in test_models:
            logger.info(f"  Testing {model}...")
            
            payload = {
                "prompt": "Say 'Test successful' and nothing else.",
                "options": {
                    "models": [model],  # Force specific model
                    "model_selection_mode": "balanced"
                }
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{self.base_url}/route", json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        results[model] = {
                            "success": True,
                            "winner_model": result.get("winner_model"),
                            "answer": result.get("answer", "")[:50],
                            "confidence": result.get("confidence", 0)
                        }
                        logger.info(f"    ✅ {model}: Success")
                        break  # Found a working model
                    else:
                        results[model] = {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "details": response.text[:100]
                        }
                        logger.info(f"    ❌ {model}: Failed")
            except Exception as e:
                results[model] = {
                    "success": False,
                    "error": str(e)
                }
                logger.info(f"    ❌ {model}: Exception - {str(e)[:50]}")
        
        return results

    async def reset_circuit_breaker_via_restart(self) -> bool:
        """Suggest circuit breaker reset by restarting the server"""
        logger.info("🔄 Circuit breaker reset requires server restart...")
        logger.info("   💡 The circuit breaker state is in memory and will reset on restart")
        return True

    def generate_config_fix(self) -> str:
        """Generate configuration fix recommendations"""
        config_fix = """
# CONFIGURATION FIX for backend/judge/config.py
# Replace your current DEFAULT_MODELS with these working models:

DEFAULT_MODELS: List[str] = [
    "openai/gpt-4o-mini",           # Fast and reliable
    "openai/gpt-3.5-turbo",         # Backup OpenAI
    "anthropic/claude-3-haiku",     # Fast Anthropic
    "google/gemini-flash-1.5",      # Google option
    "meta-llama/llama-3.1-70b-instruct",  # Open source
]

FALLBACK_MODELS: List[str] = [
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet", 
    "mistralai/mistral-7b-instruct",
]

# Add these circuit breaker settings:
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
CIRCUIT_BREAKER_RECOVERY_TIME: int = Field(default=120, env="CIRCUIT_BREAKER_RECOVERY_TIME")
"""
        return config_fix

    def generate_quick_fix_script(self) -> str:
        """Generate a quick fix script"""
        return """
# QUICK FIX SCRIPT - Save as fix_nextagi.py and run it

import sys
import subprocess
import time

def restart_server():
    print("🔄 Restarting NextAGI server to reset circuit breaker...")
    print("   Press Ctrl+C in the server terminal, then run:")
    print("   python -m uvicorn backend.main:app --reload")
    print("   Or use: kill -9 $(ps aux | grep 'uvicorn.*backend.main:app' | awk '{print $2}')")

if __name__ == "__main__":
    restart_server()
"""

    async def full_diagnostic(self) -> Dict[str, Any]:
        """Run complete diagnostic and provide recommendations"""
        logger.info("🔧 Running full NextAGI diagnostic...")
        logger.info("=" * 60)
        
        diagnostic_results = {}
        
        # 1. System Status
        logger.info("1️⃣ System Status Check")
        system_status = await self.get_system_status()
        diagnostic_results["system_status"] = system_status
        
        if "error" in system_status:
            logger.error(f"❌ System not accessible: {system_status['error']}")
            return diagnostic_results
        
        # 2. Configuration Check
        logger.info("\n2️⃣ Configuration Check")
        config_check = await self.check_configuration_mismatch()
        diagnostic_results["configuration"] = config_check
        
        # 3. Individual Model Test
        logger.info("\n3️⃣ Individual Model Test")
        model_test = await self.test_single_model_directly()
        diagnostic_results["model_tests"] = model_test
        
        # 4. Analysis and Recommendations
        logger.info("\n4️⃣ Analysis & Recommendations")
        recommendations = self.analyze_and_recommend(diagnostic_results)
        diagnostic_results["recommendations"] = recommendations
        
        # Print summary
        self.print_diagnostic_summary(diagnostic_results)
        
        return diagnostic_results

    def analyze_and_recommend(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze results and provide recommendations"""
        recommendations = {
            "priority": "high",
            "issues": [],
            "fixes": [],
            "status": "unknown"
        }
        
        system_status = results.get("system_status", {})
        model_tests = results.get("model_tests", {})
        
        # Check if system is responding
        if "error" in system_status:
            recommendations["issues"].append("Server not responding")
            recommendations["fixes"].append("Start server: python -m uvicorn backend.main:app --reload")
            recommendations["status"] = "server_down"
            return recommendations
        
        # Check fanout details
        fanout_details = system_status.get("fanout_details", {})
        available_models = fanout_details.get("available_models", {})
        current_available = available_models.get("currently_available", 0)
        total_configured = available_models.get("total_configured", 0)
        
        if current_available == 0:
            recommendations["issues"].append("Circuit breaker has blocked all models")
            recommendations["fixes"].append("Restart server to reset circuit breaker")
            
            # Check if any models work individually
            working_models = [m for m, r in model_tests.items() if r.get("success", False)]
            if working_models:
                recommendations["issues"].append("Models work individually but circuit breaker blocks them")
                recommendations["fixes"].append(f"Working models found: {working_models}")
                recommendations["status"] = "circuit_breaker_issue"
            else:
                recommendations["issues"].append("No models are working - check API keys and configuration")
                recommendations["fixes"].append("Check OPENROUTER_API_KEY and model names")
                recommendations["status"] = "configuration_issue"
        else:
            recommendations["status"] = "healthy"
        
        return recommendations

    def print_diagnostic_summary(self, results: Dict[str, Any]):
        """Print diagnostic summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)
        
        system_status = results.get("system_status", {})
        recommendations = results.get("recommendations", {})
        
        # System status
        if "error" not in system_status:
            fanout_details = system_status.get("fanout_details", {})
            available_models = fanout_details.get("available_models", {})
            current_available = available_models.get("currently_available", 0)
            total_configured = available_models.get("total_configured", 0)
            
            logger.info(f"🏥 System Status: {system_status.get('status', 'unknown')}")
            logger.info(f"📊 Models Available: {current_available}/{total_configured}")
        else:
            logger.info(f"❌ System Error: {system_status['error']}")
        
        # Issues and fixes
        issues = recommendations.get("issues", [])
        fixes = recommendations.get("fixes", [])
        status = recommendations.get("status", "unknown")
        
        logger.info(f"\n🎯 Diagnosis: {status.replace('_', ' ').title()}")
        
        if issues:
            logger.info("\n❌ Issues Found:")
            for i, issue in enumerate(issues, 1):
                logger.info(f"   {i}. {issue}")
        
        if fixes:
            logger.info("\n💡 Recommended Fixes:")
            for i, fix in enumerate(fixes, 1):
                logger.info(f"   {i}. {fix}")
        
        # Quick fix instructions
        logger.info("\n🚀 QUICK FIX INSTRUCTIONS:")
        logger.info("   1. Stop your NextAGI server (Ctrl+C)")
        logger.info("   2. Restart with: python -m uvicorn backend.main:app --reload")
        logger.info("   3. Wait 10 seconds, then run: python run_tests.py --quick")
        logger.info("   4. If still failing, check your OPENROUTER_API_KEY")

async def main():
    """Run the diagnostic tool"""
    print("🔧 NextAGI Circuit Breaker Diagnostic & Reset Tool")
    print("=" * 60)
    
    diagnostic = CircuitBreakerDiagnostic()
    results = await diagnostic.full_diagnostic()
    
    # Save diagnostic results
    with open("diagnostic_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\n💾 Diagnostic results saved to: diagnostic_results.json")
    
    # Determine exit code
    status = results.get("recommendations", {}).get("status", "unknown")
    return 0 if status == "healthy" else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)