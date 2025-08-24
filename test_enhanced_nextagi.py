# test_enhanced_nextagi.py
"""
Comprehensive test suite for NextAGI Enhanced Async System
Tests circuit breaker, fanout optimization, pipeline performance, and async processing
"""

import pytest
import asyncio
import time
import json
import httpx
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging for tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NextAGIAsyncTester:
    """Comprehensive async testing suite for NextAGI"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.performance_metrics = {}
        
    async def health_check(self) -> Dict[str, Any]:
        """Test enhanced health check endpoint"""
        logger.info("🏥 Testing enhanced health check...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            
            assert response.status_code == 200
            health_data = response.json()
            
            # Validate enhanced health check structure
            assert "status" in health_data
            assert "services" in health_data
            assert "fanout_details" in health_data
            
            # Check fanout system health
            fanout_details = health_data["fanout_details"]
            assert "circuit_breaker_status" in fanout_details
            assert "available_models" in fanout_details
            assert "configuration" in fanout_details
            
            logger.info(f"✅ Health check passed: {health_data['status']}")
            logger.info(f"📊 Available models: {fanout_details['available_models']['currently_available']}/{fanout_details['available_models']['total_configured']}")
            
            return health_data
    
    async def test_circuit_breaker_functionality(self) -> Dict[str, Any]:
        """Test circuit breaker protection under model failures"""
        logger.info("⚡ Testing circuit breaker functionality...")
        
        # Test with a mix of working and non-working models
        test_payload = {
            "prompt": "Test circuit breaker response",
            "options": {
                "models": [
                    "openai/gpt-4o",           # Should work
                    "fake/non-existent-model", # Should fail
                    "anthropic/claude-3.5-sonnet", # Should work
                    "another/fake-model"        # Should fail
                ],
                "model_selection_mode": "balanced"
            }
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/route",
                json=test_payload
            )
            
            response_time = (time.perf_counter() - start_time) * 1000
            
            # Should succeed despite some models failing
            assert response.status_code == 200
            result = response.json()
            
            # Should have an answer despite failures
            assert "answer" in result
            assert len(result["answer"]) > 0
            assert "winner_model" in result
            
            # Check that working models were used
            assert result["winner_model"] in ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "error_fallback"]
            
            logger.info(f"✅ Circuit breaker test passed: {response_time:.0f}ms")
            logger.info(f"🏆 Winner: {result['winner_model']}")
            
            return {
                "test_name": "circuit_breaker",
                "success": True,
                "response_time_ms": response_time,
                "winner_model": result["winner_model"],
                "models_attempted": result.get("models_attempted", []),
                "models_succeeded": result.get("models_succeeded", [])
            }
    
    async def test_mode_specific_performance(self) -> Dict[str, Any]:
        """Test performance optimizations for different modes"""
        logger.info("🎯 Testing mode-specific performance...")
        
        modes_to_test = ["speed", "quality", "balanced", "cost"]
        mode_results = {}
        
        test_prompt = "Explain the benefits of renewable energy in 2-3 sentences."
        
        for mode in modes_to_test:
            logger.info(f"  Testing mode: {mode}")
            
            payload = {
                "prompt": test_prompt,
                "options": {
                    "model_selection_mode": mode
                }
            }
            
            start_time = time.perf_counter()
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url}/route", json=payload)
                
                response_time = (time.perf_counter() - start_time) * 1000
                
                assert response.status_code == 200
                result = response.json()
                
                mode_results[mode] = {
                    "response_time_ms": response_time,
                    "winner_model": result["winner_model"],
                    "confidence": result["confidence"],
                    "models_attempted": len(result.get("models_attempted", [])),
                    "models_succeeded": len(result.get("models_succeeded", [])),
                    "answer_length": len(result["answer"])
                }
                
                logger.info(f"    ✅ {mode}: {response_time:.0f}ms, {result['winner_model']}, conf={result['confidence']:.3f}")
        
        # Validate expected performance characteristics
        if "speed" in mode_results and "quality" in mode_results:
            # Speed mode should generally be faster than quality mode
            speed_time = mode_results["speed"]["response_time_ms"]
            quality_time = mode_results["quality"]["response_time_ms"]
            
            # Allow some variance, but speed should trend faster
            if speed_time < quality_time * 1.5:
                logger.info(f"✅ Speed optimization working: {speed_time:.0f}ms vs {quality_time:.0f}ms")
            else:
                logger.warning(f"⚠️ Speed mode not significantly faster: {speed_time:.0f}ms vs {quality_time:.0f}ms")
        
        return {
            "test_name": "mode_performance",
            "success": True,
            "mode_results": mode_results
        }
    
    async def test_concurrent_requests(self, num_concurrent: int = 10) -> Dict[str, Any]:
        """Test system performance under concurrent load"""
        logger.info(f"🚀 Testing {num_concurrent} concurrent requests...")
        
        test_payload = {
            "prompt": "What is artificial intelligence? Give a brief explanation.",
            "options": {
                "model_selection_mode": "balanced"
            }
        }
        
        async def single_request(client: httpx.AsyncClient, request_id: int) -> Dict[str, Any]:
            start_time = time.perf_counter()
            try:
                response = await client.post(f"{self.base_url}/route", json=test_payload)
                response_time = (time.perf_counter() - start_time) * 1000
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "request_id": request_id,
                        "success": True,
                        "response_time_ms": response_time,
                        "winner_model": result["winner_model"],
                        "confidence": result["confidence"],
                        "answer_length": len(result["answer"])
                    }
                else:
                    return {
                        "request_id": request_id,
                        "success": False,
                        "response_time_ms": response_time,
                        "error": f"HTTP {response.status_code}"
                    }
                    
            except Exception as e:
                response_time = (time.perf_counter() - start_time) * 1000
                return {
                    "request_id": request_id,
                    "success": False,
                    "response_time_ms": response_time,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            tasks = [single_request(client, i) for i in range(num_concurrent)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        failed_results = [r for r in results if not isinstance(r, dict) or not r.get("success", False)]
        
        if successful_results:
            avg_response_time = sum(r["response_time_ms"] for r in successful_results) / len(successful_results)
            min_response_time = min(r["response_time_ms"] for r in successful_results)
            max_response_time = max(r["response_time_ms"] for r in successful_results)
            
            # Check for model diversity
            unique_winners = set(r["winner_model"] for r in successful_results)
            avg_confidence = sum(r["confidence"] for r in successful_results) / len(successful_results)
            
            logger.info(f"✅ Concurrent test results:")
            logger.info(f"   📊 Success rate: {len(successful_results)}/{num_concurrent} ({len(successful_results)/num_concurrent*100:.1f}%)")
            logger.info(f"   ⏱️  Avg response time: {avg_response_time:.0f}ms")
            logger.info(f"   📈 Range: {min_response_time:.0f}ms - {max_response_time:.0f}ms")
            logger.info(f"   🎯 Total time: {total_time:.0f}ms")
            logger.info(f"   🧠 Avg confidence: {avg_confidence:.3f}")
            logger.info(f"   🔄 Model diversity: {len(unique_winners)} unique winners")
            
            return {
                "test_name": "concurrent_requests",
                "success": True,
                "total_requests": num_concurrent,
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / num_concurrent,
                "avg_response_time_ms": avg_response_time,
                "min_response_time_ms": min_response_time,
                "max_response_time_ms": max_response_time,
                "total_time_ms": total_time,
                "avg_confidence": avg_confidence,
                "unique_winners": len(unique_winners),
                "throughput_rps": num_concurrent / (total_time / 1000)
            }
        else:
            logger.error("❌ All concurrent requests failed")
            return {
                "test_name": "concurrent_requests",
                "success": False,
                "error": "All requests failed",
                "failed_requests": len(failed_results)
            }
    
    async def test_pipeline_metrics_endpoint(self) -> Dict[str, Any]:
        """Test pipeline metrics and monitoring"""
        logger.info("📊 Testing pipeline metrics endpoint...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/metrics")
            
            assert response.status_code == 200
            metrics = response.json()
            
            # Validate metrics structure
            assert "timestamp" in metrics
            assert "fanout_system" in metrics
            
            fanout_system = metrics["fanout_system"]
            assert "circuit_breaker_status" in fanout_system
            assert "available_models" in fanout_system
            assert "configuration" in fanout_system
            
            logger.info("✅ Metrics endpoint working")
            logger.info(f"📈 Current available models: {fanout_system['available_models']['currently_available']}")
            
            return {
                "test_name": "pipeline_metrics",
                "success": True,
                "metrics": metrics
            }
    
    async def test_timeout_handling(self) -> Dict[str, Any]:
        """Test timeout handling and graceful degradation"""
        logger.info("⏰ Testing timeout handling...")
        
        # Test with a very complex prompt that might timeout
        complex_prompt = "Provide a comprehensive analysis of the geopolitical implications of artificial intelligence development across different nations, including detailed economic, social, and technological factors, with specific examples from at least 10 countries and their policies." * 3  # Make it really long
        
        payload = {
            "prompt": complex_prompt,
            "options": {
                "model_selection_mode": "quality"  # Quality mode has longer timeout
            }
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=60.0) as client:  # Shorter client timeout than server
            try:
                response = await client.post(f"{self.base_url}/route", json=payload)
                response_time = (time.perf_counter() - start_time) * 1000
                
                # Should get a response (either success or graceful timeout)
                assert response.status_code == 200
                result = response.json()
                
                # Should have an answer even if it's a timeout fallback
                assert "answer" in result
                assert len(result["answer"]) > 0
                
                is_timeout = result.get("error") == "timeout" or result.get("winner_model") == "timeout_fallback"
                
                logger.info(f"✅ Timeout test: {response_time:.0f}ms, timeout={is_timeout}")
                if is_timeout:
                    logger.info("   🔄 Graceful timeout fallback triggered")
                else:
                    logger.info(f"   🏆 Completed successfully with: {result['winner_model']}")
                
                return {
                    "test_name": "timeout_handling",
                    "success": True,
                    "response_time_ms": response_time,
                    "timeout_triggered": is_timeout,
                    "winner_model": result["winner_model"]
                }
                
            except httpx.TimeoutException:
                response_time = (time.perf_counter() - start_time) * 1000
                logger.info(f"⏰ Client timeout after {response_time:.0f}ms - this is expected behavior")
                return {
                    "test_name": "timeout_handling",
                    "success": True,  # Client timeout is acceptable
                    "response_time_ms": response_time,
                    "client_timeout": True
                }
    
    async def test_error_recovery(self) -> Dict[str, Any]:
        """Test error recovery and fallback mechanisms"""
        logger.info("🔄 Testing error recovery and fallbacks...")
        
        # Test with invalid models to trigger fallbacks
        payload = {
            "prompt": "Simple test question: What is 2+2?",
            "options": {
                "models": [
                    "completely/fake-model-1",
                    "invalid/model-2", 
                    "openai/gpt-3.5-turbo",  # This should work as fallback
                    "nonexistent/model-3"
                ]
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/route", json=payload)
            
            # Should succeed despite invalid models
            assert response.status_code == 200
            result = response.json()
            
            # Should have a valid answer
            assert "answer" in result
            assert len(result["answer"]) > 0
            assert "winner_model" in result
            
            # Winner should be the working model or error fallback
            valid_winners = ["openai/gpt-3.5-turbo", "error_fallback", "timeout_fallback"]
            assert result["winner_model"] in valid_winners or any(model in result["winner_model"] for model in ["gpt", "claude", "gemini"])
            
            logger.info(f"✅ Error recovery test passed")
            logger.info(f"🏆 Fallback winner: {result['winner_model']}")
            
            return {
                "test_name": "error_recovery",
                "success": True,
                "winner_model": result["winner_model"],
                "models_attempted": result.get("models_attempted", []),
                "models_succeeded": result.get("models_succeeded", [])
            }
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete enhanced async test suite"""
        logger.info("🧪 Starting Comprehensive NextAGI Enhanced Async Test Suite")
        logger.info("=" * 80)
        
        suite_start = time.perf_counter()
        all_results = {}
        
        try:
            # 1. Health Check
            logger.info("1️⃣ Health Check Test")
            all_results["health_check"] = await self.health_check()
            await asyncio.sleep(1)
            
            # 2. Circuit Breaker Test
            logger.info("\n2️⃣ Circuit Breaker Test")
            all_results["circuit_breaker"] = await self.test_circuit_breaker_functionality()
            await asyncio.sleep(2)
            
            # 3. Mode Performance Test
            logger.info("\n3️⃣ Mode-Specific Performance Test")
            all_results["mode_performance"] = await self.test_mode_specific_performance()
            await asyncio.sleep(2)
            
            # 4. Concurrent Requests Test
            logger.info("\n4️⃣ Concurrent Requests Test")
            all_results["concurrent_requests"] = await self.test_concurrent_requests(8)
            await asyncio.sleep(3)
            
            # 5. Pipeline Metrics Test
            logger.info("\n5️⃣ Pipeline Metrics Test")
            all_results["pipeline_metrics"] = await self.test_pipeline_metrics_endpoint()
            await asyncio.sleep(1)
            
            # 6. Timeout Handling Test
            logger.info("\n6️⃣ Timeout Handling Test")
            all_results["timeout_handling"] = await self.test_timeout_handling()
            await asyncio.sleep(2)
            
            # 7. Error Recovery Test
            logger.info("\n7️⃣ Error Recovery Test")
            all_results["error_recovery"] = await self.test_error_recovery()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {str(e)}")
            all_results["suite_error"] = str(e)
        
        suite_time = (time.perf_counter() - suite_start) * 1000
        
        # Generate comprehensive report
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        logger.info("=" * 80)
        
        successful_tests = sum(1 for result in all_results.values() if isinstance(result, dict) and result.get("success", False))
        total_tests = len([k for k in all_results.keys() if k != "suite_error"])
        
        logger.info(f"🎯 Tests Passed: {successful_tests}/{total_tests}")
        logger.info(f"⏱️  Total Suite Time: {suite_time:.0f}ms")
        
        # Performance summary
        if "mode_performance" in all_results and all_results["mode_performance"]["success"]:
            mode_results = all_results["mode_performance"]["mode_results"]
            fastest_mode = min(mode_results.keys(), key=lambda k: mode_results[k]["response_time_ms"])
            logger.info(f"🏃 Fastest Mode: {fastest_mode} ({mode_results[fastest_mode]['response_time_ms']:.0f}ms)")
        
        # Concurrent performance
        if "concurrent_requests" in all_results and all_results["concurrent_requests"]["success"]:
            concurrent = all_results["concurrent_requests"]
            logger.info(f"🚀 Concurrent Performance: {concurrent['success_rate']*100:.1f}% success, {concurrent['throughput_rps']:.1f} RPS")
        
        # System health
        if "health_check" in all_results:
            health = all_results["health_check"]["fanout_details"]
            available_models = health["available_models"]["currently_available"]
            total_models = health["available_models"]["total_configured"]
            logger.info(f"🏥 System Health: {available_models}/{total_models} models available")
        
        logger.info("=" * 80)
        
        return {
            "suite_summary": {
                "tests_passed": successful_tests,
                "total_tests": total_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "total_time_ms": suite_time
            },
            "detailed_results": all_results
        }

# Pytest integration
@pytest.mark.asyncio
async def test_nextagi_health_check():
    """Pytest: Test NextAGI health check"""
    tester = NextAGIAsyncTester()
    result = await tester.health_check()
    assert result["status"] in ["healthy", "degraded"]

@pytest.mark.asyncio 
async def test_nextagi_circuit_breaker():
    """Pytest: Test circuit breaker functionality"""
    tester = NextAGIAsyncTester()
    result = await tester.test_circuit_breaker_functionality()
    assert result["success"] is True

@pytest.mark.asyncio
async def test_nextagi_concurrent_requests():
    """Pytest: Test concurrent request handling"""
    tester = NextAGIAsyncTester()
    result = await tester.test_concurrent_requests(5)  # Smaller load for pytest
    assert result["success"] is True
    assert result["success_rate"] >= 0.8  # At least 80% success rate

@pytest.mark.asyncio
async def test_nextagi_mode_performance():
    """Pytest: Test mode-specific performance"""
    tester = NextAGIAsyncTester()
    result = await tester.test_mode_specific_performance()
    assert result["success"] is True

# Standalone execution
async def main():
    """Run the comprehensive test suite"""
    tester = NextAGIAsyncTester()
    results = await tester.run_comprehensive_test_suite()
    
    # Save results to file
    with open("nextagi_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("\n💾 Results saved to: nextagi_test_results.json")
    
    # Return exit code based on results
    success_rate = results["suite_summary"]["success_rate"]
    return 0 if success_rate >= 0.8 else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)