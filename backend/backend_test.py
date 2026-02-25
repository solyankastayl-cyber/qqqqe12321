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
    def __init__(self, base_url="http://localhost:8001"):
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

    def test_basic_health_check(self):
        """Test /api/health endpoint returns ok: true"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                passed = ok_status == True
                details += f", ok: {ok_status}"
            else:
                details += f", Response: {response.text[:100]}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("/api/health returns ok: true", passed, details)
        return passed

    def test_dxy_macro_core_health(self):
        """Test /api/dxy-macro-core/health returns module: dxy-macro-core"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/health", timeout=10)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed:
                data = response.json()
                module = data.get('module', '')
                passed = module == 'dxy-macro-core'
                details += f", module: {module}"
                
                # Additional checks
                ok_status = data.get('ok', False)
                version = data.get('version', '')
                fred_health = data.get('fred', {})
                details += f", ok: {ok_status}, version: {version}, FRED: {fred_health.get('status', 'N/A')}"
            else:
                details += f", Response: {response.text[:200]}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("/api/dxy-macro-core/health returns module: dxy-macro-core", passed, details)
        return passed

    def test_episodes_validation(self):
        """Test /api/dxy-macro-core/validate/episodes returns all 4 episodes with verdict.pass = true"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/validate/episodes", timeout=30)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                episodes = data.get('episodes', [])
                passed = len(episodes) == 4
                details += f", Episodes count: {len(episodes)}"
                
                if passed:
                    # Check that all episodes have verdict.pass = true
                    all_pass = True
                    episode_details = []
                    for ep in episodes:
                        verdict_pass = ep.get('verdict', {}).get('pass', False)
                        episode_key = ep.get('key', 'Unknown')
                        episode_details.append(f"{episode_key}: {verdict_pass}")
                        if not verdict_pass:
                            all_pass = False
                    
                    passed = all_pass
                    details += f", All episodes pass: {all_pass}, Episodes: {', '.join(episode_details)}"
                    
                    # Check guard criteria for specific episodes
                    guard_checks = []
                    for ep in episodes:
                        key = ep.get('key', '')
                        guard_stats = ep.get('stats', {}).get('guard', {})
                        
                        if key == 'GFC_2008_2009':
                            crisis_block = guard_stats.get('CRISIS', 0) + guard_stats.get('BLOCK', 0)
                            gfc_pass = crisis_block >= 0.60
                            guard_checks.append(f"GFC CRISIS+BLOCK {crisis_block:.2f} >= 0.60: {gfc_pass}")
                            if not gfc_pass:
                                passed = False
                                
                        elif key == 'COVID_2020_SPIKE':
                            crisis_block = guard_stats.get('CRISIS', 0) + guard_stats.get('BLOCK', 0)
                            covid_pass = crisis_block >= 0.80
                            guard_checks.append(f"COVID CRISIS+BLOCK {crisis_block:.2f} >= 0.80: {covid_pass}")
                            if not covid_pass:
                                passed = False
                                
                        elif key == 'TIGHTENING_2022':
                            block_pct = guard_stats.get('BLOCK', 0)
                            tight_pass = block_pct <= 0.10
                            guard_checks.append(f"Tightening BLOCK {block_pct:.2f} <= 0.10: {tight_pass}")
                            if not tight_pass:
                                passed = False
                                
                        elif key == 'LOW_VOL_2017':
                            none_pct = guard_stats.get('NONE', 0)
                            vol_pass = none_pct >= 0.80
                            guard_checks.append(f"2017 NONE {none_pct:.2f} >= 0.80: {vol_pass}")
                            if not vol_pass:
                                passed = False
                    
                    if guard_checks:
                        details += f", Guard criteria: {'; '.join(guard_checks)}"
                        
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Episodes validation - 4 episodes with guard criteria", passed, details)
        return passed

    def test_stability_validation(self):
        """Test /api/dxy-macro-core/validate/stability returns guard.flips.perYear <= 4"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/validate/stability", timeout=30)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                guard_flips = data.get('guard', {}).get('flips', {})
                flips_per_year = guard_flips.get('perYear', 999)
                
                passed = flips_per_year <= 4
                details += f", Guard flips per year: {flips_per_year} (target: <= 4)"
                
                # Additional stability metrics
                total_flips = guard_flips.get('total', 0)
                median_duration = data.get('guard', {}).get('medianDurationDays', 0)
                samples = data.get('range', {}).get('samples', 0)
                
                details += f", Total flips: {total_flips}, Median duration: {median_duration}d, Samples: {samples}"
                
                # Check acceptance criteria
                acceptance = data.get('acceptance', {})
                acceptance_pass = acceptance.get('pass', False)
                if not acceptance_pass:
                    details += f", Overall acceptance: {acceptance_pass}"
                    
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Stability validation - guard flips <= 4 per year", passed, details)
        return passed

    def test_macro_core_score(self):
        """Test /api/dxy-macro-core/score endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/score", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                score = data.get('score', {})
                score_signed = score.get('scoreSigned', None)
                components = score.get('components', [])
                
                passed = score_signed is not None and len(components) > 0
                details += f", Score: {score_signed}, Components: {len(components)}"
                
                # Check component structure
                if components:
                    first_comp = components[0]
                    required_fields = ['seriesId', 'weight', 'rawPressure', 'normalizedPressure']
                    has_all_fields = all(field in first_comp for field in required_fields)
                    if not has_all_fields:
                        passed = False
                        details += ", Missing component fields"
                        
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Macro score endpoint", passed, details)
        return passed

    def test_credit_context(self):
        """Test /api/dxy-macro-core/credit endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/credit", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                credit = data.get('credit', {})
                composite = credit.get('composite', {})
                
                score_signed = composite.get('scoreSigned', None)
                passed = score_signed is not None
                details += f", Credit composite score: {score_signed}"
                
                # Check components
                components = credit.get('components', [])
                details += f", Components: {len(components)}"
                
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Credit context endpoint", passed, details)
        return passed

    def test_housing_context(self):
        """Test /api/dxy-macro-core/housing endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/housing", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                housing = data.get('housing', {})
                composite = housing.get('composite', {})
                
                score_signed = composite.get('scoreSigned', None)
                passed = score_signed is not None
                details += f", Housing composite score: {score_signed}"
                
                # Check components
                components = housing.get('components', [])
                details += f", Components: {len(components)}"
                
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Housing context endpoint", passed, details)
        return passed

    def test_activity_context(self):
        """Test /api/dxy-macro-core/activity endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/activity", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                activity = data.get('activity', {})
                composite = activity.get('composite', {})
                
                score_signed = composite.get('scoreSigned', None)
                passed = score_signed is not None
                details += f", Activity composite score: {score_signed}"
                
                # Check components  
                components = activity.get('components', [])
                details += f", Components: {len(components)}"
                
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Activity context endpoint", passed, details)
        return passed

    def test_macro_series_list(self):
        """Test /api/dxy-macro-core/series endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/dxy-macro-core/series", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                series = data.get('series', [])
                total = data.get('total', 0)
                loaded = data.get('loaded', 0)
                
                passed = len(series) > 0 and total > 0
                details += f", Total series: {total}, Loaded: {loaded}, Series count: {len(series)}"
                
                # Check series structure
                if series:
                    first_series = series[0]
                    required_fields = ['seriesId', 'displayName', 'frequency', 'role']
                    has_all_fields = all(field in first_series for field in required_fields)
                    if not has_all_fields:
                        passed = False
                        details += ", Missing series fields"
                        
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Macro series list endpoint", passed, details)
        return passed

    def run_all_tests(self):
        """Run all DXY Macro Platform backend tests"""
        print("🚀 Starting DXY Macro Platform Backend API Tests")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test order - critical tests first
        test_methods = [
            self.test_basic_health_check,
            self.test_dxy_macro_core_health,
            self.test_episodes_validation,  # CRITICAL - B6 Guard criteria
            self.test_stability_validation,  # CRITICAL - Guard stability
            self.test_macro_core_score,
            self.test_credit_context,
            self.test_housing_context,
            self.test_activity_context,
            self.test_macro_series_list,
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
    tester = DXYMacroBackendTester()
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
    critical_tests = [
        '/api/health returns ok: true',
        '/api/dxy-macro-core/health returns module: dxy-macro-core',
        'Episodes validation - 4 episodes with guard criteria',
        'Stability validation - guard flips <= 4 per year'
    ]
    critical_failures = [r for r in results if r['test_name'] in critical_tests and not r['passed']]
    
    if critical_failures:
        print(f"\n🚨 Critical test failures detected!")
        for failure in critical_failures:
            print(f"   - {failure['test_name']}")
        return 1
    
    if passed / total < 0.7:  # Less than 70% pass rate
        print(f"\n⚠️  Low success rate: {passed}/{total}")
        return 1
    
    print(f"\n✅ Backend tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())