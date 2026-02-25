#!/usr/bin/env python3
"""
AE Brain Module Backend API Testing - C8 Transition Matrix Focus
Tests all endpoints related to the AE Brain module with focus on C8 Transition Matrix implementation
"""

import requests
import json
import sys
import time
from datetime import datetime

class AeBrainBackendTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.transition_matrix = None

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
        
        self.log_test("GET /api/health - should return ok: true", passed, details)
        return passed

    def test_ae_brain_health(self):
        """Test /api/ae/health - AE Brain module health"""
        try:
            response = requests.get(f"{self.base_url}/api/ae/health", timeout=10)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed:
                data = response.json()
                module = data.get('module', '')
                ok_status = data.get('ok', False)
                version = data.get('version', '')
                components = data.get('components', [])
                
                # Check required fields
                passed = (ok_status == True and 
                         module == 'ae-brain' and 
                         len(components) > 0)
                
                details += f", module: {module}, ok: {ok_status}, version: {version}, components: {len(components)}"
                if components:
                    details += f" [{', '.join(components)}]"
                    
            else:
                details += f", Response: {response.text[:200]}"
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("GET /api/ae/health - AE Brain module health", passed, details)
        return passed

    def test_ae_terminal_full_pack(self):
        """Test /api/ae/terminal - full AE terminal pack with C1-C8 components"""
        try:
            response = requests.get(f"{self.base_url}/api/ae/terminal", timeout=30)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                
                # Check required components (C1-C8)
                required_components = ['state', 'regime', 'causal', 'scenarios', 'novelty']
                optional_components = ['cluster', 'transition']  # C7, C8
                
                missing_components = []
                for comp in required_components:
                    if comp not in data:
                        missing_components.append(comp)
                
                present_optional = []
                for comp in optional_components:
                    if comp in data and data[comp] is not None:
                        present_optional.append(comp)
                
                passed = ok_status and len(missing_components) == 0
                details += f", ok: {ok_status}, required_components: {len(required_components) - len(missing_components)}/{len(required_components)}"
                details += f", optional_components: {present_optional}"
                
                if missing_components:
                    details += f", missing: {missing_components}"
                
                # Check specific C8 transition info if present
                if 'transition' in data and data['transition']:
                    transition = data['transition']
                    required_transition_fields = ['currentLabel', 'mostLikelyNext', 'riskToStress']
                    has_transition_fields = all(field in transition for field in required_transition_fields)
                    if has_transition_fields:
                        risk_to_stress = transition['riskToStress']
                        has_risk_periods = all(period in risk_to_stress for period in ['p1w', 'p2w', 'p4w'])
                        details += f", C8_transition: {has_transition_fields and has_risk_periods}"
                    
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("GET /api/ae/terminal - full AE terminal pack with C1-C8", passed, details)
        return passed

    def test_transition_matrix_compute(self):
        """Test POST /api/ae/admin/transition/compute - compute transition matrix"""
        try:
            # Test with default parameters first
            payload = {
                "from": "2020-01-01",
                "to": "2025-12-31", 
                "stepDays": 7,
                "alpha": 1
            }
            
            response = requests.post(
                f"{self.base_url}/api/ae/admin/transition/compute",
                json=payload,
                timeout=45
            )
            
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                matrix_data = data.get('matrix', {})
                
                if ok_status and matrix_data:
                    # Store matrix for later tests
                    self.transition_matrix = matrix_data
                    
                    meta = matrix_data.get('meta', {})
                    matrix = matrix_data.get('matrix', [])
                    row_sums = matrix_data.get('rowSums', [])
                    labels = meta.get('labels', [])
                    samples = meta.get('samples', 0)
                    
                    passed = (len(matrix) > 0 and 
                             len(labels) > 0 and 
                             samples > 0 and
                             len(row_sums) == len(matrix))
                    
                    details += f", ok: {ok_status}, labels: {len(labels)} {labels}"
                    details += f", matrix_size: {len(matrix)}x{len(matrix[0]) if matrix else 0}"
                    details += f", samples: {samples}"
                else:
                    passed = False
                    details += f", ok: {ok_status}, matrix_present: {bool(matrix_data)}"
                    
            else:
                details += f", Response: {response.text[:300]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("POST /api/ae/admin/transition/compute - compute matrix", passed, details)
        return passed

    def test_transition_current_matrix(self):
        """Test GET /api/ae/transition/current - get matrix with derived metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/ae/transition/current", timeout=20)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                
                # Check for matrix, derived, and durations
                has_matrix = 'matrix' in data and data['matrix'] is not None
                has_derived = 'derived' in data and data['derived'] is not None
                has_durations = 'durations' in data and data['durations'] is not None
                
                passed = ok_status and has_matrix and has_derived
                details += f", ok: {ok_status}, matrix: {has_matrix}, derived: {has_derived}, durations: {has_durations}"
                
                if has_derived:
                    derived = data['derived']
                    current_label = derived.get('currentLabel', '')
                    risk_to_stress = derived.get('riskToStress', {})
                    stress_labels = derived.get('stressLabels', [])
                    
                    has_risk_periods = all(period in risk_to_stress for period in ['p1w', 'p2w', 'p4w'])
                    details += f", currentLabel: {current_label}, stressLabels: {len(stress_labels)}"
                    details += f", riskToStress_periods: {has_risk_periods}"
                    
                    if has_risk_periods:
                        p1w = risk_to_stress.get('p1w', 0)
                        p2w = risk_to_stress.get('p2w', 0) 
                        p4w = risk_to_stress.get('p4w', 0)
                        details += f", p1w: {p1w:.4f}, p2w: {p2w:.4f}, p4w: {p4w:.4f}"
                    
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("GET /api/ae/transition/current - matrix with derived metrics", passed, details)
        return passed

    def test_transition_raw_matrix(self):
        """Test GET /api/ae/transition/matrix - get raw transition matrix"""
        try:
            response = requests.get(f"{self.base_url}/api/ae/transition/matrix", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                matrix_data = data.get('matrix', {})
                
                if ok_status and matrix_data:
                    meta = matrix_data.get('meta', {})
                    matrix = matrix_data.get('matrix', [])
                    row_sums = matrix_data.get('rowSums', [])
                    labels = meta.get('labels', [])
                    
                    # Check for 3 expected labels
                    expected_labels = ['LIQUIDITY_EXPANSION', 'RISK_OFF_STRESS', 'TIGHTENING_USD_SUPPORTIVE']
                    has_expected_labels = all(label in labels for label in expected_labels)
                    
                    # Check row sums are approximately 1.0 (within tolerance)
                    row_sums_valid = all(abs(sum_val - 1.0) < 0.01 for sum_val in row_sums)
                    
                    passed = (ok_status and 
                             len(labels) >= 3 and
                             has_expected_labels and 
                             len(matrix) == len(labels) and
                             row_sums_valid)
                    
                    details += f", ok: {ok_status}, labels: {len(labels)} {labels}"
                    details += f", expected_labels_present: {has_expected_labels}"
                    details += f", matrix_size: {len(matrix)}x{len(matrix[0]) if matrix else 0}"
                    details += f", row_sums_valid (~1.0): {row_sums_valid}"
                    
                    if row_sums:
                        details += f", row_sums: {[f'{s:.4f}' for s in row_sums]}"
                    
                else:
                    passed = False
                    details += f", ok: {ok_status}, matrix_present: {bool(matrix_data)}"
                    
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("GET /api/ae/transition/matrix - raw matrix with 3 labels & row sums ~1.0", passed, details)
        return passed

    def test_transition_durations(self):
        """Test GET /api/ae/transition/durations - get regime duration stats"""
        try:
            response = requests.get(f"{self.base_url}/api/ae/transition/durations", timeout=15)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if passed:
                data = response.json()
                ok_status = data.get('ok', False)
                durations = data.get('durations', [])
                
                passed = ok_status and len(durations) > 0
                details += f", ok: {ok_status}, duration_stats: {len(durations)}"
                
                if durations:
                    # Check structure of duration stats
                    first_duration = durations[0]
                    required_fields = ['label', 'count', 'medianWeeks', 'meanWeeks', 'maxWeeks']
                    has_all_fields = all(field in first_duration for field in required_fields)
                    
                    if not has_all_fields:
                        passed = False
                        missing = [f for f in required_fields if f not in first_duration]
                        details += f", missing_fields: {missing}"
                    else:
                        # Show duration stats for each regime
                        duration_summary = []
                        for dur in durations[:3]:  # Top 3 most common regimes
                            label = dur.get('label', '')
                            median = dur.get('medianWeeks', 0)
                            count = dur.get('count', 0)
                            duration_summary.append(f"{label}: {median}w median ({count} episodes)")
                        details += f", regime_durations: {'; '.join(duration_summary)}"
                    
            else:
                details += f", Response: {response.text[:200]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("GET /api/ae/transition/durations - regime duration stats", passed, details)
        return passed

    def test_transition_matrix_validation(self):
        """Validate transition matrix properties and riskToStress metrics"""
        if not self.transition_matrix:
            self.log_test("Transition Matrix Validation - matrix properties", False, "No matrix data available from compute test")
            return False
            
        try:
            meta = self.transition_matrix.get('meta', {})
            matrix = self.transition_matrix.get('matrix', [])
            row_sums = self.transition_matrix.get('rowSums', [])
            labels = meta.get('labels', [])
            
            # Validate labels contain expected regimes
            expected_labels = ['LIQUIDITY_EXPANSION', 'RISK_OFF_STRESS', 'TIGHTENING_USD_SUPPORTIVE']
            has_expected_labels = all(label in labels for label in expected_labels)
            
            # Validate row sums are approximately 1.0
            row_sums_valid = all(abs(sum_val - 1.0) < 0.01 for sum_val in row_sums)
            
            # Validate matrix is square
            is_square = len(matrix) == len(labels) and all(len(row) == len(labels) for row in matrix)
            
            # Validate probabilities are in [0, 1]
            valid_probabilities = all(
                0.0 <= prob <= 1.0 
                for row in matrix 
                for prob in row
            )
            
            passed = (has_expected_labels and 
                     row_sums_valid and 
                     is_square and 
                     valid_probabilities)
            
            details = f"expected_labels: {has_expected_labels}, row_sums_valid: {row_sums_valid}"
            details += f", square_matrix: {is_square}, valid_probabilities: {valid_probabilities}"
            details += f", labels: {labels}, matrix_size: {len(matrix)}x{len(matrix[0]) if matrix else 0}"
            
            if row_sums:
                details += f", row_sums: {[f'{s:.4f}' for s in row_sums]}"
                
        except Exception as e:
            passed = False
            details = f"Error: {str(e)}"
        
        self.log_test("Transition Matrix Validation - matrix properties", passed, details)
        return passed

    def run_all_tests(self):
        """Run all AE Brain backend tests with focus on C8 Transition Matrix"""
        print("🚀 Starting AE Brain Backend API Tests - C8 Transition Matrix Focus")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test order - health checks first, then matrix computation, then validation
        test_methods = [
            self.test_basic_health_check,
            self.test_ae_brain_health,
            self.test_ae_terminal_full_pack,
            self.test_transition_matrix_compute,  # Compute matrix first
            self.test_transition_current_matrix,  # Then get with derived metrics
            self.test_transition_raw_matrix,      # Validate raw matrix properties
            self.test_transition_durations,      # Get duration stats
            self.test_transition_matrix_validation,  # Final validation
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Test execution error: {str(e)}")
            
            time.sleep(1)  # Pause between tests for API stability
        
        print("\n" + "=" * 80)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   - {result['test_name']}: {result['details']}")
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = AeBrainBackendTester()
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
    
    with open('/app/backend/ae_brain_test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend/ae_brain_test_results.json")
    
    # Return exit code based on success
    critical_tests = [
        'GET /api/health - should return ok: true',
        'GET /api/ae/health - AE Brain module health', 
        'POST /api/ae/admin/transition/compute - compute matrix',
        'GET /api/ae/transition/matrix - raw matrix with 3 labels & row sums ~1.0'
    ]
    critical_failures = [r for r in results if r['test_name'] in critical_tests and not r['passed']]
    
    if critical_failures:
        print(f"\n🚨 Critical test failures detected!")
        for failure in critical_failures:
            print(f"   - {failure['test_name']}")
        return 1
    
    if passed / total < 0.75:  # Less than 75% pass rate
        print(f"\n⚠️  Low success rate: {passed}/{total}")
        return 1
    
    print(f"\n✅ AE Brain backend tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())