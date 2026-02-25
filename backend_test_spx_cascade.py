#!/usr/bin/env python3
"""
SPX Cascade Backend API Testing - D1 Extended
Tests DXY/AE → SPX cascade overlay endpoints
"""

import requests
import json
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

class SpxCascadeTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.failures: List[str] = []
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            self.failures.append(f"{name}: {details}")
            print(f"❌ {name}: FAILED {details}")
    
    def api_call(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """Make API call and return JSON response"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        self.log(f"API {method} {url}")
        if params:
            self.log(f"Params: {params}")
        if data:
            self.log(f"Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                headers = {'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers, params=params, timeout=60)
            elif method == 'POST':
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, params=params, json=data, timeout=120)
            else:
                raise ValueError(f"Unsupported method: {method}")

            self.log(f"Response: {response.status_code}")
            
            if response.status_code >= 400:
                self.log(f"Error response: {response.text}", "ERROR")
                return {
                    'ok': False, 
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
            
            return response.json()
            
        except requests.exceptions.Timeout:
            return {'ok': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'ok': False, 'error': f'Request error: {str(e)}'}
        except json.JSONDecodeError:
            return {'ok': False, 'error': 'Invalid JSON response'}
    
    def test_cascade_health(self) -> bool:
        """Test GET /api/fractal/spx/cascade/health - module health check"""
        response = self.api_call('GET', '/api/fractal/spx/cascade/health')
        
        if not response.get('ok'):
            self.log_test("Cascade Health Check", False, f"Error: {response.get('error')}")
            return False
        
        # Verify health check response structure
        required_fields = ['module', 'version', 'status', 'components', 'guardCaps']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            self.log_test("Cascade Health Check", False, f"Missing fields: {missing_fields}")
            return False
        
        # Verify guard caps structure
        guard_caps = response.get('guardCaps', {})
        expected_guards = ['NONE', 'WARN', 'CRISIS', 'BLOCK']
        
        for guard in expected_guards:
            if guard not in guard_caps:
                self.log_test("Cascade Health Check", False, f"Missing guard cap: {guard}")
                return False
        
        # Verify specific guard values
        block_cap = guard_caps.get('BLOCK', -1)
        crisis_cap = guard_caps.get('CRISIS', -1)
        warn_cap = guard_caps.get('WARN', -1)
        
        if block_cap != 0.0:
            self.log_test("Cascade Health Check", False, f"BLOCK cap should be 0.0, got {block_cap}")
            return False
            
        if crisis_cap != 0.4:
            self.log_test("Cascade Health Check", False, f"CRISIS cap should be 0.4, got {crisis_cap}")
            return False
            
        if warn_cap != 0.75:
            self.log_test("Cascade Health Check", False, f"WARN cap should be 0.75, got {warn_cap}")
            return False
        
        self.log_test("Cascade Health Check", True, f"Module: {response.get('module')}, Version: {response.get('version')}")
        return True

    def test_cascade_only_endpoint(self) -> bool:
        """Test GET /api/fractal/spx/cascade?focus=30d - cascade-only data"""
        response = self.api_call('GET', '/api/fractal/spx/cascade', params={'focus': '30d'})
        
        if not response.get('ok'):
            self.log_test("Cascade Only Endpoint", False, f"Error: {response.get('error')}")
            return False
        
        # Verify cascade-only structure
        required_fields = ['symbol', 'focus', 'spxCore', 'cascade']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            self.log_test("Cascade Only Endpoint", False, f"Missing fields: {missing_fields}")
            return False
        
        # Store cascade data for other tests
        self.results['cascade_only'] = response
        
        # Verify SPX core signal
        spx_core = response.get('spxCore', {})
        if 'action' not in spx_core or 'confidence' not in spx_core:
            self.log_test("Cascade Only Endpoint", False, "Missing SPX core signal data")
            return False
        
        # Verify cascade structure
        cascade = response.get('cascade', {})
        cascade_fields = ['inputs', 'overlay', 'multipliers', 'decisionAdjusted', 'explain']
        missing_cascade_fields = [field for field in cascade_fields if field not in cascade]
        
        if missing_cascade_fields:
            self.log_test("Cascade Only Endpoint", False, f"Missing cascade fields: {missing_cascade_fields}")
            return False
        
        self.log_test("Cascade Only Endpoint", True, f"Symbol: {response.get('symbol')}, Focus: {response.get('focus')}")
        return True

    def test_full_terminal_with_cascade(self) -> bool:
        """Test GET /api/fractal/spx/terminal?focus=30d - full terminal with cascade section"""
        response = self.api_call('GET', '/api/fractal/spx/terminal', params={'focus': '30d'})
        
        if not response.get('ok'):
            self.log_test("Full Terminal with Cascade", False, f"Error: {response.get('error')}")
            return False
        
        # Verify full terminal structure
        required_fields = ['symbol', 'focus', 'contract', 'market', 'decision', 'diagnostics', 'cascade', 'meta']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            self.log_test("Full Terminal with Cascade", False, f"Missing fields: {missing_fields}")
            return False
        
        # Store terminal data
        self.results['full_terminal'] = response
        
        # Verify cascade is included
        cascade = response.get('cascade')
        if not cascade:
            self.log_test("Full Terminal with Cascade", False, "No cascade section found")
            return False
        
        # Verify decision has cascadeAdjusted
        decision = response.get('decision', {})
        cascade_adjusted = decision.get('cascadeAdjusted')
        
        if not cascade_adjusted:
            self.log_test("Full Terminal with Cascade", False, "No cascadeAdjusted in decision")
            return False
        
        # Verify meta has cascade info
        meta = response.get('meta', {})
        cascade_enabled = meta.get('cascadeEnabled')
        cascade_version = meta.get('cascadeVersion')
        
        if cascade_enabled is None or not cascade_version:
            self.log_test("Full Terminal with Cascade", False, "Missing cascade meta info")
            return False
        
        self.log_test("Full Terminal with Cascade", True, f"Cascade enabled: {cascade_enabled}, Version: {cascade_version}")
        return True

    def test_validate_block_guard(self) -> bool:
        """Test POST /api/fractal/spx/admin/cascade/validate with testCase=BLOCK - size must be 0"""
        data = {'testCase': 'BLOCK'}
        response = self.api_call('POST', '/api/fractal/spx/admin/cascade/validate', data=data)
        
        if not response.get('ok'):
            self.log_test("Validate BLOCK Guard", False, f"Error: {response.get('error')}")
            return False
        
        cascade = response.get('cascade', {})
        multipliers = cascade.get('multipliers', {})
        size_multiplier = multipliers.get('sizeMultiplier', -1)
        
        # BLOCK should result in size multiplier = 0
        if size_multiplier != 0.0:
            self.log_test("Validate BLOCK Guard", False, f"Expected size=0, got {size_multiplier}")
            return False
        
        # Verify validation checks
        validation = response.get('validation', {})
        guard_respected = validation.get('guardRespected', False)
        
        if not guard_respected:
            self.log_test("Validate BLOCK Guard", False, "Guard policy not respected")
            return False
        
        self.log_test("Validate BLOCK Guard", True, f"Size multiplier: {size_multiplier}")
        return True

    def test_validate_crisis_guard(self) -> bool:
        """Test POST /api/fractal/spx/admin/cascade/validate with testCase=CRISIS - size must be ≤0.4"""
        data = {'testCase': 'CRISIS'}
        response = self.api_call('POST', '/api/fractal/spx/admin/cascade/validate', data=data)
        
        if not response.get('ok'):
            self.log_test("Validate CRISIS Guard", False, f"Error: {response.get('error')}")
            return False
        
        cascade = response.get('cascade', {})
        multipliers = cascade.get('multipliers', {})
        size_multiplier = multipliers.get('sizeMultiplier', -1)
        
        # CRISIS should result in size multiplier ≤ 0.4
        if size_multiplier > 0.4:
            self.log_test("Validate CRISIS Guard", False, f"Expected size≤0.4, got {size_multiplier}")
            return False
        
        # Verify validation checks
        validation = response.get('validation', {})
        guard_respected = validation.get('guardRespected', False)
        
        if not guard_respected:
            self.log_test("Validate CRISIS Guard", False, "Guard policy not respected")
            return False
        
        self.log_test("Validate CRISIS Guard", True, f"Size multiplier: {size_multiplier} (≤0.4)")
        return True

    def test_validate_stress_multipliers(self) -> bool:
        """Test POST /api/fractal/spx/admin/cascade/validate with testCase=STRESS - stress multipliers applied"""
        data = {'testCase': 'STRESS'}
        response = self.api_call('POST', '/api/fractal/spx/admin/cascade/validate', data=data)
        
        if not response.get('ok'):
            self.log_test("Validate STRESS Multipliers", False, f"Error: {response.get('error')}")
            return False
        
        cascade = response.get('cascade', {})
        multipliers = cascade.get('multipliers', {})
        factors = multipliers.get('factors', {})
        
        m_stress = factors.get('mStress', 1.0)
        m_persist = factors.get('mPersist', 1.0)
        
        # In stress scenario, both stress and persistence multipliers should be < 1.0
        if m_stress >= 1.0:
            self.log_test("Validate STRESS Multipliers", False, f"Expected mStress<1.0, got {m_stress}")
            return False
            
        if m_persist >= 1.0:
            self.log_test("Validate STRESS Multipliers", False, f"Expected mPersist<1.0, got {m_persist}")
            return False
        
        # Verify inputs show stress regime
        inputs = cascade.get('inputs', {})
        ae_regime = inputs.get('ae', {}).get('regime', '')
        
        if 'STRESS' not in ae_regime.upper():
            self.log_test("Validate STRESS Multipliers", False, f"Expected stress regime, got {ae_regime}")
            return False
        
        self.log_test("Validate STRESS Multipliers", True, 
                     f"mStress: {m_stress:.3f}, mPersist: {m_persist:.3f}, Regime: {ae_regime}")
        return True

    def test_validate_rare_novelty(self) -> bool:
        """Test POST /api/fractal/spx/admin/cascade/validate with testCase=RARE - novelty haircut 0.85"""
        data = {'testCase': 'RARE'}
        response = self.api_call('POST', '/api/fractal/spx/admin/cascade/validate', data=data)
        
        if not response.get('ok'):
            self.log_test("Validate RARE Novelty", False, f"Error: {response.get('error')}")
            return False
        
        cascade = response.get('cascade', {})
        multipliers = cascade.get('multipliers', {})
        factors = multipliers.get('factors', {})
        
        m_novel = factors.get('mNovel', 1.0)
        
        # RARE novelty should result in 0.85 multiplier
        if abs(m_novel - 0.85) > 0.001:
            self.log_test("Validate RARE Novelty", False, f"Expected mNovel=0.85, got {m_novel}")
            return False
        
        # Verify inputs show RARE novelty
        inputs = cascade.get('inputs', {})
        novelty = inputs.get('ae', {}).get('novelty', {})
        novelty_label = novelty.get('label', '')
        
        if novelty_label != 'RARE':
            self.log_test("Validate RARE Novelty", False, f"Expected novelty=RARE, got {novelty_label}")
            return False
        
        self.log_test("Validate RARE Novelty", True, f"Novelty multiplier: {m_novel}, Label: {novelty_label}")
        return True

    def test_direction_preservation(self) -> bool:
        """Verify cascade.decisionAdjusted.action equals spxCore.action (direction preserved)"""
        # Use cascade-only data
        cascade_data = self.results.get('cascade_only')
        if not cascade_data:
            self.log_test("Direction Preservation", False, "No cascade data available")
            return False
        
        spx_core = cascade_data.get('spxCore', {})
        cascade = cascade_data.get('cascade', {})
        
        spx_action = spx_core.get('action')
        cascade_action = cascade.get('decisionAdjusted', {}).get('action')
        
        if not spx_action or not cascade_action:
            self.log_test("Direction Preservation", False, "Missing action data")
            return False
        
        # Actions must be identical - cascade never changes direction
        if spx_action != cascade_action:
            self.log_test("Direction Preservation", False, 
                         f"Direction changed: SPX={spx_action}, Cascade={cascade_action}")
            return False
        
        self.log_test("Direction Preservation", True, f"Action preserved: {spx_action}")
        return True

    def test_no_nan_negative_multipliers(self) -> bool:
        """Verify no NaN or negative values in multipliers"""
        cascade_data = self.results.get('cascade_only')
        if not cascade_data:
            self.log_test("No NaN/Negative Multipliers", False, "No cascade data available")
            return False
        
        cascade = cascade_data.get('cascade', {})
        multipliers = cascade.get('multipliers', {})
        
        # Check main multipliers
        size_multiplier = multipliers.get('sizeMultiplier', -1)
        confidence_multiplier = multipliers.get('confidenceMultiplier', -1)
        threshold_shift = multipliers.get('thresholdShift', -1)
        
        if size_multiplier < 0 or confidence_multiplier < 0 or threshold_shift < 0:
            self.log_test("No NaN/Negative Multipliers", False, 
                         f"Negative values: size={size_multiplier}, conf={confidence_multiplier}, thresh={threshold_shift}")
            return False
        
        # Check factors
        factors = multipliers.get('factors', {})
        for factor_name, factor_value in factors.items():
            if factor_value < 0 or str(factor_value) in ['NaN', 'Infinity', '-Infinity']:
                self.log_test("No NaN/Negative Multipliers", False, 
                             f"Invalid {factor_name}: {factor_value}")
                return False
        
        # Check for NaN in JSON serialization
        cascade_json = json.dumps(cascade)
        if 'NaN' in cascade_json or 'Infinity' in cascade_json:
            self.log_test("No NaN/Negative Multipliers", False, "NaN or Infinity found in cascade data")
            return False
        
        self.log_test("No NaN/Negative Multipliers", True, "All multipliers valid")
        return True

    def test_dxy_ae_inputs_populated(self) -> bool:
        """Verify cascade.inputs.dxy and cascade.inputs.ae are populated"""
        cascade_data = self.results.get('cascade_only')
        if not cascade_data:
            self.log_test("DXY/AE Inputs Populated", False, "No cascade data available")
            return False
        
        cascade = cascade_data.get('cascade', {})
        inputs = cascade.get('inputs', {})
        
        # Check DXY inputs
        dxy_inputs = inputs.get('dxy', {})
        required_dxy_fields = ['tacticalAction', 'tacticalConfidence01', 'regimeMode', 'regimeBiasSigned', 'guard']
        
        for field in required_dxy_fields:
            if field not in dxy_inputs:
                self.log_test("DXY/AE Inputs Populated", False, f"Missing DXY field: {field}")
                return False
        
        # Check AE inputs
        ae_inputs = inputs.get('ae', {})
        required_ae_fields = ['regime', 'regimeConfidence01', 'transition', 'durations', 'novelty', 'scenarios']
        
        for field in required_ae_fields:
            if field not in ae_inputs:
                self.log_test("DXY/AE Inputs Populated", False, f"Missing AE field: {field}")
                return False
        
        # Verify transition has required sub-fields
        transition = ae_inputs.get('transition', {})
        transition_fields = ['pStress1w', 'pStress4w', 'selfTransition']
        
        for field in transition_fields:
            if field not in transition:
                self.log_test("DXY/AE Inputs Populated", False, f"Missing transition field: {field}")
                return False
        
        dxy_action = dxy_inputs.get('tacticalAction')
        ae_regime = ae_inputs.get('regime')
        
        self.log_test("DXY/AE Inputs Populated", True, f"DXY: {dxy_action}, AE: {ae_regime}")
        return True

    def run_all_tests(self):
        """Run all SPX Cascade tests"""
        self.log("=" * 80)
        self.log("Starting SPX Cascade Backend Tests - D1 Extended")
        self.log("=" * 80)
        
        # Test 1: Health check
        success1 = self.test_cascade_health()
        
        # Test 2: Cascade-only endpoint
        success2 = self.test_cascade_only_endpoint()
        
        # Test 3: Full terminal with cascade
        success3 = self.test_full_terminal_with_cascade()
        
        # Test 4: BLOCK guard validation
        success4 = self.test_validate_block_guard()
        
        # Test 5: CRISIS guard validation
        success5 = self.test_validate_crisis_guard()
        
        # Test 6: STRESS multipliers
        success6 = self.test_validate_stress_multipliers()
        
        # Test 7: RARE novelty haircut
        success7 = self.test_validate_rare_novelty()
        
        # Test 8: Direction preservation
        success8 = self.test_direction_preservation()
        
        # Test 9: No NaN/negative multipliers
        success9 = self.test_no_nan_negative_multipliers()
        
        # Test 10: DXY/AE inputs populated
        success10 = self.test_dxy_ae_inputs_populated()
        
        # Print summary
        self.print_summary()
        
        return all([success1, success2, success3, success4, success5, success6, success7, success8, success9, success10])

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 80)
        self.log("SPX CASCADE TEST SUMMARY")
        self.log("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        self.log("-" * 80)
        self.log(f"📊 Tests passed: {self.tests_passed}/{self.tests_run} ({success_rate:.1f}%)")
        
        if self.failures:
            self.log(f"\n❌ Failures ({len(self.failures)}):")
            for failure in self.failures:
                self.log(f"  • {failure}")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All SPX Cascade tests PASSED!")
        else:
            self.log("⚠️  Some SPX Cascade tests FAILED")
        
        self.log("=" * 80)

def main():
    """Main test runner"""
    tester = SpxCascadeTester()
    
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())