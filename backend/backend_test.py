#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for DXY Macro Platform - B6 2-Stage Guard
Tests all endpoints related to the DXY Macro Core and Crisis Guard functionality
"""

import requests
import json
import sys
import time
from datetime import datetime

class DXYMacroBackendTester:
    def __init__(self, base_url="https://dxy-risk-overlay.preview.emergentagent.com"):
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

    def test_health_check(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed and response.text:
                details += f", Response: {response.text[:100]}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Health Check", passed, details)
        return passed

    def test_fractal_overlay_basic(self):
        """Test fractal overlay endpoint with default parameters"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/overlay"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                # Check required fields
                required_fields = ['symbol', 'currentWindow', 'matches']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    passed = False
                    details = f"Missing fields: {missing_fields}"
                else:
                    passed = True
                    matches_count = len(data.get('matches', []))
                    details = f"Symbol: {data.get('symbol')}, Matches: {matches_count}"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Fractal Overlay Basic", passed, details)
        return passed

    def test_fractal_overlay_horizon_30d(self):
        """Test fractal overlay with 30D horizon"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/overlay?symbol=BTC&aftermathDays=30"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                matches = data.get('matches', [])
                if matches:
                    first_match = matches[0]
                    aftermath_len = len(first_match.get('aftermathNormalized', []))
                    passed = aftermath_len >= 20
                    details = f"Matches: {len(matches)}, Aftermath length: {aftermath_len}"
                else:
                    passed = False
                    details = "No matches returned"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Fractal Overlay 30D Horizon", passed, details)
        return passed

    def test_fractal_overlay_horizon_180d(self):
        """Test fractal overlay with 180D horizon"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/overlay?symbol=BTC&aftermathDays=180"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                matches = data.get('matches', [])
                if matches:
                    first_match = matches[0]
                    aftermath_len = len(first_match.get('aftermathNormalized', []))
                    passed = aftermath_len >= 150
                    details = f"Matches: {len(matches)}, Aftermath length: {aftermath_len}"
                else:
                    passed = False
                    details = "No matches returned"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Fractal Overlay 180D Horizon", passed, details)
        return passed

    def test_fractal_overlay_horizon_365d(self):
        """Test fractal overlay with 365D horizon (CRITICAL)"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/overlay?symbol=BTC&aftermathDays=365"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                matches = data.get('matches', [])
                if matches:
                    first_match = matches[0]
                    aftermath_len = len(first_match.get('aftermathNormalized', []))
                    passed = aftermath_len >= 300
                    details = f"Matches: {len(matches)}, Aftermath length: {aftermath_len}"
                    
                    # Also check distribution series
                    dist_series = data.get('distributionSeries')
                    if dist_series:
                        p10_len = len(dist_series.get('p10', []))
                        details += f", Distribution series length: {p10_len}"
                else:
                    passed = False
                    details = "No matches returned"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Fractal Overlay 365D Horizon", passed, details)
        return passed

    def test_strategy_endpoint(self):
        """Test strategy endpoint with different modes"""
        modes = ['conservative', 'balanced', 'aggressive']
        all_passed = True
        details_list = []
        
        for mode in modes:
            try:
                url = f"{self.base_url}/api/fractal/v2.1/strategy?symbol=BTC&preset={mode}"
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    all_passed = False
                    details_list.append(f"{mode}: HTTP {response.status_code}")
                else:
                    data = response.json()
                    # Check required fields
                    required_fields = ['decision', 'edge', 'diagnostics', 'regime']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if missing_fields:
                        all_passed = False
                        details_list.append(f"{mode}: Missing fields {missing_fields}")
                    else:
                        details_list.append(f"{mode}: OK")
                        
            except Exception as e:
                all_passed = False
                details_list.append(f"{mode}: Error {str(e)}")
        
        details = "; ".join(details_list)
        self.log_test("Strategy Endpoint (All Modes)", all_passed, details)
        return all_passed

    def test_forward_equity_endpoint(self):
        """Test forward equity endpoint with different parameters"""
        test_cases = [
            {'preset': 'BALANCED', 'horizon': 7, 'role': 'ACTIVE'},
            {'preset': 'CONSERVATIVE', 'horizon': 14, 'role': 'SHADOW'},
            {'preset': 'AGGRESSIVE', 'horizon': 30, 'role': 'ACTIVE'}
        ]
        
        all_passed = True
        details_list = []
        
        for case in test_cases:
            try:
                params = f"symbol=BTC&preset={case['preset']}&horizon={case['horizon']}&role={case['role']}"
                url = f"{self.base_url}/api/fractal/v2.1/admin/forward-equity?{params}"
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    all_passed = False
                    details_list.append(f"{case['preset']}-{case['horizon']}D: HTTP {response.status_code}")
                else:
                    data = response.json()
                    if data.get('error'):
                        all_passed = False
                        details_list.append(f"{case['preset']}-{case['horizon']}D: API Error {data.get('error')}")
                    else:
                        # Check if we have equity data or empty result
                        equity_len = len(data.get('equity', []))
                        details_list.append(f"{case['preset']}-{case['horizon']}D: {equity_len} points")
                        
            except Exception as e:
                all_passed = False
                details_list.append(f"{case['preset']}-{case['horizon']}D: Error {str(e)}")
        
        details = "; ".join(details_list)
        self.log_test("Forward Equity Endpoint (All Params)", all_passed, details)
        return all_passed

    def test_spx_forward_summary_endpoint(self):
        """Test SPX forward performance summary endpoint (FP4)"""
        try:
            url = f"{self.base_url}/api/fractal/spx/forward/summary"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                if not data.get('ok'):
                    passed = False 
                    details = f"API Error: {data.get('error', 'Unknown error')}"
                else:
                    # Check required fields for FP5
                    overall = data.get('overall', {})
                    by_horizon = data.get('byHorizon', [])
                    
                    required_overall = ['hitRate', 'avgRealizedReturn', 'bias', 'sampleSize']
                    missing_overall = [f for f in required_overall if f not in overall]
                    
                    if missing_overall or not by_horizon:
                        passed = False
                        details = f"Missing fields in overall: {missing_overall}, byHorizon length: {len(by_horizon)}"
                    else:
                        passed = True
                        hit_rate = (overall.get('hitRate', 0) * 100)
                        sample_size = overall.get('sampleSize', 0)
                        details = f"Hit Rate: {hit_rate:.1f}%, Samples: {sample_size}, Horizons: {len(by_horizon)}"
                        
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("SPX Forward Summary Endpoint", passed, details)
        return passed

    def test_spx_forward_equity_endpoint(self):
        """Test SPX forward equity curve endpoint (FP6)"""
        try:
            url = f"{self.base_url}/api/fractal/spx/forward/equity"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                if not data.get('ok'):
                    passed = False
                    details = f"API Error: {data.get('error', 'Unknown error')}"
                else:
                    # Check equity curve structure for FP6
                    equity = data.get('equity', [])
                    metrics = data.get('metrics', {})
                    
                    required_metrics = ['trades', 'winRate', 'maxDrawdown', 'finalEquity']
                    missing_metrics = [f for f in required_metrics if f not in metrics]
                    
                    if missing_metrics:
                        passed = False
                        details = f"Missing metrics: {missing_metrics}"
                    elif not equity:
                        passed = False
                        details = "No equity curve data returned"
                    else:
                        # Validate equity curve structure
                        first_point = equity[0] if equity else {}
                        required_point_fields = ['date', 'value', 'hit', 'action']
                        missing_point_fields = [f for f in required_point_fields if f not in first_point]
                        
                        if missing_point_fields:
                            passed = False
                            details = f"Missing equity point fields: {missing_point_fields}"
                        else:
                            passed = True
                            trades = metrics.get('trades', 0)
                            win_rate = (metrics.get('winRate', 0) * 100)
                            max_dd = (metrics.get('maxDrawdown', 0) * 100)
                            final_equity = metrics.get('finalEquity', 0)
                            details = f"Trades: {trades}, Win Rate: {win_rate:.1f}%, Max DD: {max_dd:.1f}%, Final: {final_equity:.3f}, Points: {len(equity)}"
                        
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("SPX Forward Equity Endpoint", passed, details)
        return passed

    def test_admin_endpoint(self):
        """Test if admin endpoint is accessible"""
        try:
            endpoints = [
                f"{self.base_url}/admin/fractal",
                f"{self.base_url}/api/admin/fractal"
            ]
            
            passed = False
            details = ""
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code in [200, 401, 403]:
                        passed = True
                        details += f"{endpoint}: HTTP {response.status_code}; "
                    else:
                        details += f"{endpoint}: HTTP {response.status_code}; "
                except Exception as e:
                    details += f"{endpoint}: {str(e)}; "
                    
            if not passed:
                details = f"All admin endpoints failed: {details}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Admin Endpoint Accessibility", passed, details)
        
    def run_all_tests(self):
        """Run all fractal backend tests"""
        print("🚀 Starting Fractal Backend API Tests")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test order - critical tests first
        test_methods = [
            self.test_health_check,
            self.test_spx_forward_summary_endpoint,  # FP5 - Critical for Forward Performance
            self.test_spx_forward_equity_endpoint,   # FP6 - Critical for Equity Curve
            self.test_strategy_endpoint,  # NEW - Critical for Strategy Controls
            self.test_forward_equity_endpoint,  # NEW - Critical for Forward Performance
            self.test_fractal_overlay_basic,
            self.test_fractal_overlay_horizon_30d,
            self.test_fractal_overlay_horizon_180d,
            self.test_fractal_overlay_horizon_365d,  # Critical test
            self.test_admin_endpoint
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Test execution error: {str(e)}")
            
            time.sleep(0.5)  # Brief pause between tests
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   - {result['test_name']}: {result['details']}")
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = FractalBackendTester()
    passed, total, results = tester.run_all_tests()
    
    # Save detailed results
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "passed": passed,
            "total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        },
        "tests": results
    }
    
    with open('/app/backend/backend_test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend/backend_test_results.json")
    
    # Return exit code based on success
    critical_tests = ['SPX Forward Summary Endpoint', 'SPX Forward Equity Endpoint', 'Strategy Endpoint (All Modes)', 'Forward Equity Endpoint (All Params)', 'Fractal Overlay Basic']
    critical_failures = [r for r in results if r['test_name'] in critical_tests and not r['passed']]
    
    if critical_failures:
        print(f"\n🚨 Critical test failures detected!")
        return 1
    
    if passed / total < 0.7:  # Less than 70% pass rate
        print(f"\n⚠️  Low success rate: {passed}/{total}")
        return 1
    
    print(f"\n✅ Backend tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())