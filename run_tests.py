# run_tests.py
"""
NextAGI Enhanced Async System - Test Runner and Quick Validation
This script provides an easy way to run all tests and get instant feedback
"""

import asyncio
import sys
import argparse
import json
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_banner():
    """Print a nice banner for the test runner"""
    print("=" * 80)
    print("🧪 NextAGI Enhanced Async System - Test Runner")
    print("   Testing: Circuit Breaker, Fanout, Async Pipeline, Performance")
    print("=" * 80)

async def quick_health_check(base_url: str = "http://localhost:8000"):
    """Quick health check to verify system is running"""
    logger.info("🏥 Quick health check...")
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                
                # Check fanout system
                fanout_details = health_data.get("fanout_details", {})
                available_models = fanout_details.get("available_models", {})
                current_models = available_models.get("currently_available", 0)
                total_models = available_models.get("total_configured", 0)
                
                logger.info(f"✅ System Status: {status}")
                logger.info(f"📊 Models Available: {current_models}/{total_models}")
                
                if status in ["healthy", "degraded"] and current_models > 0:
                    return True
                else:
                    logger.error(f"❌ System not ready: {status}, {current_models} models available")
                    return False
            else:
                logger.error(f"❌ Health check failed: HTTP {response.status_code}")
                return False
                
    except ImportError:
        logger.error("❌ httpx not installed. Please run: pip install httpx")
        return False
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

async def run_comprehensive_tests():
    """Run the comprehensive async test suite"""
    logger.info("🧪 Running comprehensive async tests...")
    
    try:
        # Import and run comprehensive tests
        from test_enhanced_nextagi import NextAGIAsyncTester
        
        tester = NextAGIAsyncTester()
        results = await tester.run_comprehensive_test_suite()
        
        # Save results
        results_file = f"test_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Test results saved to: {results_file}")
        
        # Return success status
        suite_summary = results.get("suite_summary", {})
        success_rate = suite_summary.get("success_rate", 0)
        
        return success_rate >= 0.8, results_file
        
    except ImportError as e:
        logger.error(f"❌ Could not import test modules: {e}")
        return False, None
    except Exception as e:
        logger.error(f"❌ Comprehensive tests failed: {e}")
        return False, None

async def run_performance_benchmark():
    """Run the performance benchmark suite"""
    logger.info("🎯 Running performance benchmarks...")
    
    try:
        # Import and run performance benchmarks
        from performance_benchmark import NextAGIBenchmark
        
        benchmark = NextAGIBenchmark()
        results = await benchmark.run_full_benchmark_suite()
        
        # Save results
        results_file = f"benchmark_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Benchmark results saved to: {results_file}")
        
        # Check if benchmarks passed
        if "error" not in results:
            detailed_results = results.get("detailed_results", [])
            if detailed_results:
                avg_success_rate = sum(r.get("success_rate", 0) for r in detailed_results) / len(detailed_results)
                return avg_success_rate >= 0.8, results_file
        
        return False, results_file
        
    except ImportError as e:
        logger.error(f"❌ Could not import benchmark modules: {e}")
        return False, None
    except Exception as e:
        logger.error(f"❌ Performance benchmarks failed: {e}")
        return False, None

async def run_quick_validation():
    """Run a quick validation test for basic functionality"""
    logger.info("⚡ Running quick validation...")
    
    try:
        import httpx
        
        # Test basic routing
        payload = {
            "prompt": "What is artificial intelligence?",
            "options": {"model_selection_mode": "balanced"}
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://localhost:8000/route", json=payload)
            response_time = (time.perf_counter() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                # Basic validation
                assert "answer" in result
                assert "winner_model" in result
                assert "confidence" in result
                assert len(result["answer"]) > 0
                
                logger.info(f"✅ Quick validation passed: {response_time:.0f}ms")
                logger.info(f"🏆 Winner: {result['winner_model']}")
                logger.info(f"🎯 Confidence: {result['confidence']:.3f}")
                logger.info(f"📝 Answer length: {len(result['answer'])} chars")
                
                return True
            else:
                logger.error(f"❌ Quick validation failed: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Quick validation failed: {e}")
        return False

def print_test_summary(comprehensive_passed: bool, benchmark_passed: bool, quick_passed: bool):
    """Print a summary of all test results"""
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    status_icon = lambda passed: "✅" if passed else "❌"
    
    print(f"{status_icon(quick_passed)} Quick Validation: {'PASSED' if quick_passed else 'FAILED'}")
    print(f"{status_icon(comprehensive_passed)} Comprehensive Tests: {'PASSED' if comprehensive_passed else 'FAILED'}")
    print(f"{status_icon(benchmark_passed)} Performance Benchmark: {'PASSED' if benchmark_passed else 'FAILED'}")
    
    all_passed = comprehensive_passed and benchmark_passed and quick_passed
    
    print(f"\n🎯 Overall Result: {'ALL TESTS PASSED! 🎉' if all_passed else 'SOME TESTS FAILED ❌'}")
    
    if all_passed:
        print("\n🏆 NextAGI Enhanced Async System is working perfectly!")
        print("   ✅ Circuit breaker protection active")
        print("   ✅ Async fanout optimization working")
        print("   ✅ Performance targets met")
        print("   ✅ Error handling robust")
    else:
        print("\n🔧 Issues detected - check logs above for details")
        print("   📋 Review test output files for detailed analysis")
        print("   🔍 Check system health and configuration")
    
    print("=" * 80)

async def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="NextAGI Enhanced Async System Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run only quick validation")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive tests only")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for NextAGI API")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific test selected
    if not any([args.quick, args.comprehensive, args.benchmark]):
        args.all = True
    
    print_banner()
    
    # Health check first
    logger.info("🔍 Checking system health...")
    if not await quick_health_check(args.base_url):
        logger.error("❌ System health check failed. Please ensure NextAGI is running.")
        logger.error("   💡 Start with: python -m uvicorn backend.main:app --reload")
        return 1
    
    logger.info("✅ System is healthy, proceeding with tests...\n")
    
    # Initialize results
    quick_passed = True
    comprehensive_passed = True  
    benchmark_passed = True
    
    # Run requested tests
    if args.quick or args.all:
        quick_passed = await run_quick_validation()
        print()
    
    if args.comprehensive or args.all:
        comprehensive_passed, _ = await run_comprehensive_tests()
        print()
    
    if args.benchmark or args.all:
        benchmark_passed, _ = await run_performance_benchmark()
        print()
    
    # Print summary
    print_test_summary(comprehensive_passed, benchmark_passed, quick_passed)
    
    # Determine exit code
    if args.quick:
        return 0 if quick_passed else 1
    elif args.comprehensive:
        return 0 if comprehensive_passed else 1
    elif args.benchmark:
        return 0 if benchmark_passed else 1
    else:  # args.all
        all_passed = quick_passed and comprehensive_passed and benchmark_passed
        return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        sys.exit(1)