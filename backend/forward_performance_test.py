#!/usr/bin/env python3
"""
Forward Performance Testing for Fractal Module
Tests snapshot generation, Forward Performance API, and preset mode calculations
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta

class ForwardPerformanceTester:
    def __init__(self, base_url="http://localhost:8002"):
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
            response = requests.get(f"{self.base_url}/api/system/health", timeout=10)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed and response.text:
                details += f", Response: {response.text[:100]}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Health Check", passed, details)
        return passed

    def test_generate_snapshots_endpoint(self):
        """Test POST /api/fractal/v2.1/admin/test/generate-snapshots"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/admin/test/generate-snapshots"
            
            # Test snapshot generation with specific parameters
            payload = {
                "symbol": "BTC",
                "count": 10,
                "presets": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"],
                "roles": ["ACTIVE"],
                "clearExisting": False
            }
            
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                
                # Check required response fields
                required_fields = ['ok', 'generated', 'config']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    passed = False
                    details = f"Missing response fields: {missing_fields}"
                elif not data.get('ok'):
                    passed = False
                    details = f"API returned ok: false"
                else:
                    passed = True
                    generated = data.get('generated', 0)
                    expected = 10 * 3 * 1  # count × presets × roles
                    details = f"Generated: {generated} snapshots (expected: {expected})"
                    
                    if generated != expected:
                        details += f" - WARNING: Count mismatch"
                        
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Generate Snapshots Endpoint", passed, details)
        return passed

    def test_snapshot_stats_endpoint(self):
        """Test GET /api/fractal/v2.1/admin/test/snapshot-stats"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/admin/test/snapshot-stats?symbol=BTC"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                
                # Check required fields
                required_fields = ['symbol', 'total', 'breakdown']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    passed = False
                    details = f"Missing fields: {missing_fields}"
                else:
                    passed = True
                    total = data.get('total', 0)
                    breakdown = data.get('breakdown', [])
                    resolved_count = sum(item.get('resolved', 0) for item in breakdown)
                    details = f"Total: {total}, Resolved: {resolved_count}, Presets: {len(breakdown)}"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Snapshot Stats Endpoint", passed, details)
        return passed

    def test_forward_equity_presets(self):
        """Test Forward Performance API with different presets"""
        presets = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE']
        horizons = [7, 14, 30]
        roles = ['ACTIVE']
        
        all_passed = True
        details_list = []
        cagr_values = {}
        
        for preset in presets:
            for horizon in horizons:
                for role in roles:
                    try:
                        params = f"symbol=BTC&preset={preset}&horizon={horizon}&role={role}"
                        url = f"{self.base_url}/api/fractal/v2.1/admin/forward-equity?{params}"
                        response = requests.get(url, timeout=30)
                        
                        if response.status_code != 200:
                            all_passed = False
                            details_list.append(f"{preset}-{horizon}D: HTTP {response.status_code}")
                        else:
                            data = response.json()
                            if data.get('error'):
                                all_passed = False
                                details_list.append(f"{preset}-{horizon}D: API Error")
                            else:
                                metrics = data.get('metrics', {})
                                cagr = metrics.get('cagr', 0)
                                resolved = data.get('summary', {}).get('resolved', 0)
                                
                                cagr_values[f"{preset}-{horizon}D"] = cagr
                                details_list.append(f"{preset}-{horizon}D: CAGR={cagr:.1%}, Resolved={resolved}")
                                
                    except Exception as e:
                        all_passed = False
                        details_list.append(f"{preset}-{horizon}D: Error {str(e)}")
        
        # Check if different presets show different CAGR values (key requirement)
        conservative_cagrs = [cagr_values.get(f"CONSERVATIVE-{h}D", 0) for h in horizons]
        balanced_cagrs = [cagr_values.get(f"BALANCED-{h}D", 0) for h in horizons]
        aggressive_cagrs = [cagr_values.get(f"AGGRESSIVE-{h}D", 0) for h in horizons]
        
        # Check that presets show different behaviors
        presets_differ = (
            any(c != 0 for c in conservative_cagrs) or
            any(b != 0 for b in balanced_cagrs) or
            any(a != 0 for a in aggressive_cagrs)
        )
        
        if not presets_differ:
            details_list.append("WARNING: All presets show 0% CAGR - may need more resolved data")
        
        details = "; ".join(details_list[:5])  # Limit output
        if len(details_list) > 5:
            details += f" ... and {len(details_list) - 5} more"
            
        self.log_test("Forward Equity All Presets", all_passed, details)
        return all_passed

    def test_forward_equity_response_structure(self):
        """Test Forward Equity response structure for completeness"""
        try:
            params = "symbol=BTC&preset=BALANCED&horizon=7&role=ACTIVE"
            url = f"{self.base_url}/api/fractal/v2.1/admin/forward-equity?{params}"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                
                if data.get('error'):
                    passed = False
                    details = f"API Error: {data.get('error')}"
                else:
                    # Check required top-level fields
                    required_fields = ['meta', 'summary', 'equity', 'drawdown', 'metrics', 'ledger']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if missing_fields:
                        passed = False
                        details = f"Missing top-level fields: {missing_fields}"
                    else:
                        # Check metrics fields
                        metrics = data.get('metrics', {})
                        required_metrics = ['cagr', 'sharpe', 'maxDD', 'winRate', 'trades']
                        missing_metrics = [m for m in required_metrics if m not in metrics]
                        
                        if missing_metrics:
                            passed = False
                            details = f"Missing metrics: {missing_metrics}"
                        else:
                            passed = True
                            equity_points = len(data.get('equity', []))
                            ledger_entries = len(data.get('ledger', []))
                            resolved = data.get('summary', {}).get('resolved', 0)
                            details = f"Equity points: {equity_points}, Ledger: {ledger_entries}, Resolved: {resolved}"
                            
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Forward Equity Response Structure", passed, details)
        return passed

    def test_clear_snapshots_endpoint(self):
        """Test DELETE /api/fractal/v2.1/admin/test/clear-snapshots (optional cleanup test)"""
        try:
            url = f"{self.base_url}/api/fractal/v2.1/admin/test/clear-snapshots?symbol=BTC_TEST"
            response = requests.delete(url, timeout=30)
            
            if response.status_code != 200:
                passed = False
                details = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                data = response.json()
                
                if not data.get('ok'):
                    passed = False
                    details = f"API returned ok: false"
                else:
                    passed = True
                    deleted = data.get('deleted', 0)
                    details = f"Deleted: {deleted} snapshots for BTC_TEST"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Clear Snapshots Endpoint (Test Symbol)", passed, details)
        return passed

    def test_preset_mode_calculations(self):
        """Test that preset modes show different calculated metrics"""
        try:
            presets = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE']
            results = {}
            
            for preset in presets:
                params = f"symbol=BTC&preset={preset}&horizon=7&role=ACTIVE"
                url = f"{self.base_url}/api/fractal/v2.1/admin/forward-equity?{params}"
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data.get('error'):
                        metrics = data.get('metrics', {})
                        results[preset] = {
                            'cagr': metrics.get('cagr', 0),
                            'winRate': metrics.get('winRate', 0),
                            'maxDD': metrics.get('maxDD', 0),
                            'sharpe': metrics.get('sharpe', 0),
                            'trades': metrics.get('trades', 0)
                        }
            
            # Check if we have data for all presets
            if len(results) != 3:
                passed = False
                details = f"Could only get data for {list(results.keys())}"
            else:
                # Check for differences between presets
                conservative = results.get('CONSERVATIVE', {})
                balanced = results.get('BALANCED', {})
                aggressive = results.get('AGGRESSIVE', {})
                
                # At least one metric should differ between presets
                metrics_differ = (
                    conservative.get('cagr') != balanced.get('cagr') or
                    balanced.get('cagr') != aggressive.get('cagr') or
                    conservative.get('winRate') != balanced.get('winRate') or
                    conservative.get('maxDD') != balanced.get('maxDD')
                )
                
                passed = metrics_differ
                if passed:
                    details = f"Conservative CAGR: {conservative.get('cagr', 0):.1%}, "
                    details += f"Balanced CAGR: {balanced.get('cagr', 0):.1%}, "
                    details += f"Aggressive CAGR: {aggressive.get('cagr', 0):.1%}"
                else:
                    details = "All presets show identical metrics - may need more resolved data or different test configuration"
                    
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Preset Mode Calculations Differ", passed, details)
        return passed

    def run_all_tests(self):
        """Run all Forward Performance tests"""
        print("🚀 Starting Forward Performance Tests")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test order - critical tests first
        test_methods = [
            self.test_health_check,
            self.test_generate_snapshots_endpoint,
            self.test_snapshot_stats_endpoint,
            self.test_forward_equity_response_structure,
            self.test_forward_equity_presets,
            self.test_preset_mode_calculations,
            self.test_clear_snapshots_endpoint
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Test execution error: {str(e)}")
            
            time.sleep(1)  # Pause between tests
        
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
    tester = ForwardPerformanceTester()
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
    
    with open('/app/backend/forward_performance_test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend/forward_performance_test_results.json")
    
    # Return exit code based on success
    critical_tests = ['Generate Snapshots Endpoint', 'Forward Equity All Presets', 'Preset Mode Calculations Differ']
    critical_failures = [r for r in results if r['test_name'] in critical_tests and not r['passed']]
    
    if critical_failures:
        print(f"\n🚨 Critical test failures detected!")
        return 1
    
    if passed / total < 0.7:  # Less than 70% pass rate
        print(f"\n⚠️  Low success rate: {passed}/{total}")
        return 1
    
    print(f"\n✅ Forward Performance tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())