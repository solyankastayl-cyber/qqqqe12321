#!/usr/bin/env python3
"""
FP6 - Equity Curve Testing for SPX Forward Performance
Test the specific endpoints needed for FP6 implementation
"""

import requests
import json
import sys
from datetime import datetime

class FP6Tester:
    def __init__(self, base_url="http://127.0.0.1:8002"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": test_name,
            "passed": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")

    def test_spx_forward_summary(self):
        """Test SPX Forward Performance Summary (FP5)"""
        try:
            url = f"{self.base_url}/api/fractal/spx/forward/summary"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}"
            else:
                data = response.json()
                if not data.get('ok'):
                    passed = False
                    details = f"API Error: {data.get('error')}"
                else:
                    overall = data.get('overall', {})
                    by_horizon = data.get('byHorizon', [])
                    
                    hit_rate = overall.get('hitRate', 0) * 100
                    sample_size = overall.get('sampleSize', 0)
                    horizons = len(by_horizon)
                    
                    passed = True
                    details = f"Hit Rate: {hit_rate:.1f}%, Samples: {sample_size}, Horizons: {horizons}"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("SPX Forward Summary (FP5)", passed, details)
        return passed

    def test_spx_forward_equity(self):
        """Test SPX Forward Equity Curve (FP6)"""
        try:
            url = f"{self.base_url}/api/fractal/spx/forward/equity"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}"
            else:
                data = response.json()
                if not data.get('ok'):
                    passed = False
                    details = f"API Error: {data.get('error')}"
                else:
                    equity = data.get('equity', [])
                    metrics = data.get('metrics', {})
                    
                    trades = metrics.get('trades', 0)
                    win_rate = metrics.get('winRate', 0) * 100
                    max_dd = metrics.get('maxDrawdown', 0) * 100
                    final_equity = metrics.get('finalEquity', 0)
                    
                    # Validate equity curve structure
                    if len(equity) > 0:
                        first_point = equity[0]
                        required_fields = ['date', 'value', 'hit', 'action']
                        missing_fields = [f for f in required_fields if f not in first_point]
                        
                        if missing_fields:
                            passed = False
                            details = f"Missing fields: {missing_fields}"
                        else:
                            passed = True
                            details = f"Trades: {trades}, Win Rate: {win_rate:.1f}%, Max DD: {max_dd:.1f}%, Final: {final_equity:.3f}, Points: {len(equity)}"
                    else:
                        passed = False
                        details = "No equity curve data"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("SPX Forward Equity Curve (FP6)", passed, details)
        return passed

    def test_health_check(self):
        """Test basic API health"""
        try:
            url = f"{self.base_url}/api/health"
            response = requests.get(url, timeout=5)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed:
                data = response.json()
                details += f", Mode: {data.get('mode', 'unknown')}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Backend Health Check", passed, details)
        return passed

    def run_all_tests(self):
        """Run all FP6 tests"""
        print("🚀 Starting FP6 - Equity Curve Testing")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Critical FP6 tests
        test_methods = [
            self.test_health_check,
            self.test_spx_forward_summary,
            self.test_spx_forward_equity,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Test execution error: {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"📊 FP6 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   - {result['test_name']}: {result['details']}")
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = FP6Tester()
    passed, total, results = tester.run_all_tests()
    
    # Save detailed results
    test_results = {
        "test_type": "FP6_Equity_Curve",
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "passed": passed,
            "total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        },
        "tests": results
    }
    
    with open('/app/backend/fp6_test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 FP6 results saved to: /app/backend/fp6_test_results.json")
    
    # Return exit code based on success
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())