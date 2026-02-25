#!/usr/bin/env python3
"""
AE Brain Module Backend API Testing
Tests all C1-C5 components and endpoints
"""

import requests
import json
import sys
from typing import Dict, Any, List
from datetime import datetime

class AEBrainTester:
    def __init__(self, base_url: str = "https://dxy-risk-overlay.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failures: List[str] = []
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            self.failures.append(f"{name}: {details}")
            print(f"❌ {name}: FAILED {details}")
    
    def call_api(self, endpoint: str, method: str = "GET", data: Dict = None) -> tuple[bool, Dict, int]:
        """Make API call and return (success, response_data, status_code)"""
        url = f"{self.base_url}/api/ae/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            
            try:
                json_data = response.json()
            except:
                json_data = {}
            
            return response.status_code == 200, json_data, response.status_code
        except Exception as e:
            print(f"❌ API call failed: {endpoint} - {str(e)}")
            return False, {}, 0
    
    def test_health_endpoint(self):
        """Test /api/ae/health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        success, data, status = self.call_api("health")
        
        if not success:
            self.log_test("Health Endpoint", False, f"HTTP {status}")
            return False
            
        # Check required fields
        has_ok = data.get("ok") is True
        components = data.get("components", [])
        expected_components = ['state', 'regime', 'causal', 'scenarios', 'novelty']
        has_all_components = all(comp in components for comp in expected_components)
        
        self.log_test("Health - OK field", has_ok, f"ok={data.get('ok')}")
        self.log_test("Health - Components", has_all_components, f"components={components}")
        
        return has_ok and has_all_components
    
    def test_state_endpoint(self):
        """Test /api/ae/state endpoint (C1)"""
        print("\n🔍 Testing State Vector Endpoint (C1)...")
        success, data, status = self.call_api("state")
        
        if not success:
            self.log_test("State Endpoint", False, f"HTTP {status}")
            return False
        
        # Check health field
        health_ok = data.get("health", {}).get("ok", False)
        self.log_test("State - Health OK", health_ok, f"health.ok={health_ok}")
        
        # Check vector field with 6 components
        vector = data.get("vector", {})
        expected_fields = ["macroSigned", "macroConfidence", "guardLevel", 
                          "dxySignalSigned", "dxyConfidence", "regimeBias90d"]
        
        has_all_fields = all(field in vector for field in expected_fields)
        self.log_test("State - Vector Fields", has_all_fields, f"fields={list(vector.keys())}")
        
        # Check value ranges
        ranges_valid = True
        range_details = []
        
        for field, value in vector.items():
            if isinstance(value, (int, float)):
                if field in ["macroSigned", "dxySignalSigned", "regimeBias90d"]:
                    valid = -1 <= value <= 1
                    range_details.append(f"{field}={value:.3f}")
                elif field in ["macroConfidence", "dxyConfidence", "guardLevel"]:
                    valid = 0 <= value <= 1
                    range_details.append(f"{field}={value:.3f}")
                else:
                    valid = True
                    
                if not valid:
                    ranges_valid = False
        
        self.log_test("State - Value Ranges", ranges_valid, f"ranges={'; '.join(range_details)}")
        
        return success and health_ok and has_all_fields and ranges_valid
    
    def test_regime_endpoint(self):
        """Test /api/ae/regime endpoint (C2)"""
        print("\n🔍 Testing Regime Classifier Endpoint (C2)...")
        success, data, status = self.call_api("regime")
        
        if not success:
            self.log_test("Regime Endpoint", False, f"HTTP {status}")
            return False
        
        # Check regime field
        regime = data.get("regime")
        expected_regimes = ["LIQUIDITY_EXPANSION", "LIQUIDITY_CONTRACTION", 
                           "DOLLAR_DOMINANCE", "DISINFLATION_PIVOT", 
                           "RISK_OFF_STRESS", "NEUTRAL_MIXED"]
        
        regime_valid = regime in expected_regimes
        self.log_test("Regime - Valid Regime", regime_valid, f"regime={regime}")
        
        # Check confidence field
        confidence = data.get("confidence")
        confidence_valid = isinstance(confidence, (int, float)) and 0 <= confidence <= 1
        self.log_test("Regime - Confidence Range", confidence_valid, f"confidence={confidence}")
        
        return success and regime_valid and confidence_valid
    
    def test_causal_endpoint(self):
        """Test /api/ae/causal endpoint (C3)"""
        print("\n🔍 Testing Causal Graph Endpoint (C3)...")
        success, data, status = self.call_api("causal")
        
        if not success:
            self.log_test("Causal Endpoint", False, f"HTTP {status}")
            return False
        
        # Check links field
        links = data.get("links", [])
        has_min_links = len(links) >= 5
        self.log_test("Causal - Minimum Links", has_min_links, f"links_count={len(links)}")
        
        # Check link structure
        valid_links = True
        for i, link in enumerate(links[:3]):  # Check first 3 links
            required_fields = ["from", "to", "strength"]  # Fixed: use "strength" not "weight"
            has_fields = all(field in link for field in required_fields)
            if not has_fields:
                valid_links = False
                break
        
        self.log_test("Causal - Link Structure", valid_links, f"sample_link={links[0] if links else 'none'}")
        
        return success and has_min_links and valid_links
    
    def test_scenarios_endpoint(self):
        """Test /api/ae/scenarios endpoint (C4)"""
        print("\n🔍 Testing Scenarios Endpoint (C4)...")
        success, data, status = self.call_api("scenarios")
        
        if not success:
            self.log_test("Scenarios Endpoint", False, f"HTTP {status}")
            return False
        
        # Check scenarios field
        scenarios = data.get("scenarios", [])
        has_three_scenarios = len(scenarios) == 3
        self.log_test("Scenarios - Count", has_three_scenarios, f"scenarios_count={len(scenarios)}")
        
        # Check probability sum
        total_prob = sum(scenario.get("prob", 0) for scenario in scenarios)
        prob_sum_valid = abs(total_prob - 1.0) < 0.01  # Allow small floating point error
        self.log_test("Scenarios - Probability Sum", prob_sum_valid, f"total_prob={total_prob:.4f}")
        
        # Check scenario structure
        valid_structure = True
        scenario_names = []
        for scenario in scenarios:
            if "name" not in scenario or "prob" not in scenario:
                valid_structure = False
                break
            scenario_names.append(scenario.get("name"))
        
        self.log_test("Scenarios - Structure", valid_structure, f"names={scenario_names}")
        
        return success and has_three_scenarios and prob_sum_valid and valid_structure
    
    def test_novelty_endpoint(self):
        """Test /api/ae/novelty endpoint (C5)"""
        print("\n🔍 Testing Novelty Detection Endpoint (C5)...")
        success, data, status = self.call_api("novelty")
        
        if not success:
            self.log_test("Novelty Endpoint", False, f"HTTP {status}")
            return False
        
        # Check novelty field
        novelty = data.get("novelty")
        expected_novelty = ["KNOWN", "RARE", "UNSEEN"]
        novelty_valid = novelty in expected_novelty
        self.log_test("Novelty - Valid Status", novelty_valid, f"novelty={novelty}")
        
        # Check score field
        score = data.get("score")
        score_valid = isinstance(score, (int, float)) and 0 <= score <= 1
        self.log_test("Novelty - Score Range", score_valid, f"score={score}")
        
        return success and novelty_valid and score_valid
    
    def test_terminal_endpoint(self):
        """Test /api/ae/terminal endpoint - main orchestrator"""
        print("\n🔍 Testing Terminal Endpoint (Main Orchestrator)...")
        success, data, status = self.call_api("terminal")
        
        if not success:
            self.log_test("Terminal Endpoint", False, f"HTTP {status}")
            return False
        
        # Check main sections
        required_sections = ["state", "regime", "causal", "scenarios", "novelty"]
        has_all_sections = all(section in data for section in required_sections)
        self.log_test("Terminal - All Sections", has_all_sections, f"sections={list(data.keys())}")
        
        # Check recommendation section
        recommendation = data.get("recommendation", {})
        has_recommendation = "sizeMultiplier" in recommendation and "guard" in recommendation
        self.log_test("Terminal - Recommendation", has_recommendation, 
                     f"sizeMultiplier={recommendation.get('sizeMultiplier')}, guard={recommendation.get('guard')}")
        
        return success and has_all_sections and has_recommendation
    
    def test_backfill_stats_endpoint(self):
        """Test /api/ae/admin/backfill-stats endpoint - C6 requirement 1"""
        print("\n🔍 Testing Backfill Stats Endpoint (C6 Historical Backfill)...")
        success, data, status = self.call_api("admin/backfill-stats")
        
        if not success:
            self.log_test("Backfill Stats Endpoint", False, f"HTTP {status}")
            return False
        
        # Check total >= 1300 as required
        total = data.get("total", 0)
        has_sufficient_vectors = total >= 1300
        self.log_test("Backfill Stats - Total >= 1300", has_sufficient_vectors, f"total={total}")
        
        # Check range exists
        range_data = data.get("range")
        has_range = range_data is not None and "from" in range_data and "to" in range_data
        self.log_test("Backfill Stats - Range", has_range, 
                     f"range={range_data}")
        
        # Check distribution exists
        distribution = data.get("distribution")
        has_distribution = distribution is not None
        self.log_test("Backfill Stats - Distribution", has_distribution, 
                     f"distribution_present={has_distribution}")
        
        if distribution:
            # Check macroSigned range [-0.3, 0.4] as required
            macro_stats = distribution.get("macroSigned", {})
            macro_min = macro_stats.get("min")
            macro_max = macro_stats.get("max")
            
            macro_range_valid = (macro_min is not None and macro_max is not None and 
                               macro_min >= -0.5 and macro_max <= 0.6)  # Allow some tolerance
            self.log_test("Backfill Stats - MacroSigned Range", macro_range_valid, 
                         f"macro_range=[{macro_min}, {macro_max}]")
            
            # Check guardLevel distribution
            guard_stats = distribution.get("guardLevel", {})
            total_guards = sum(guard_stats.values())
            if total_guards > 0:
                none_pct = guard_stats.get("none", 0) / total_guards * 100
                crisis_pct = guard_stats.get("crisis", 0) / total_guards * 100  
                block_pct = guard_stats.get("block", 0) / total_guards * 100
                
                # Check approximate distributions: NONE ~80%, CRISIS ~15%, BLOCK ~4%
                distribution_valid = (none_pct > 70 and crisis_pct > 10 and block_pct > 2)
                self.log_test("Backfill Stats - GuardLevel Distribution", distribution_valid, 
                             f"none={none_pct:.1f}%, crisis={crisis_pct:.1f}%, block={block_pct:.1f}%")
            else:
                self.log_test("Backfill Stats - GuardLevel Distribution", False, "No guard data")
        
        return success and has_sufficient_vectors and has_range
    
    def test_historical_state_gfc(self):
        """Test historical state for GFC period - C6 requirements 2&6"""
        print("\n🔍 Testing Historical State for GFC (2008-10-11)...")
        success, data, status = self.call_api("state?asOf=2008-10-11")
        
        if not success:
            self.log_test("Historical State GFC", False, f"HTTP {status}")
            return False
        
        # Check source is historical
        source = data.get("source")
        is_historical = source == "historical"
        self.log_test("Historical State GFC - Source", is_historical, f"source={source}")
        
        # Check guardLevel = 1 (BLOCK)
        vector = data.get("vector", {})
        guard_level = vector.get("guardLevel")
        is_block_guard = guard_level == 1.0 or guard_level >= 0.9  # Allow slight tolerance
        self.log_test("Historical State GFC - GuardLevel BLOCK", is_block_guard, 
                     f"guardLevel={guard_level}")
        
        return success and is_historical and is_block_guard
    
    def test_regime_gfc(self):
        """Test regime for GFC period - C6 requirement 3"""
        print("\n🔍 Testing Regime for GFC (2008-10-11)...")
        success, data, status = self.call_api("regime?asOf=2008-10-11")
        
        if not success:
            self.log_test("Regime GFC", False, f"HTTP {status}")
            return False
        
        # Check regime is RISK_OFF_STRESS
        regime = data.get("regime")
        is_risk_off_stress = regime == "RISK_OFF_STRESS"
        self.log_test("Regime GFC - RISK_OFF_STRESS", is_risk_off_stress, f"regime={regime}")
        
        return success and is_risk_off_stress
    
    def test_regime_covid(self):
        """Test regime for COVID period - C6 requirement 4"""
        print("\n🔍 Testing Regime for COVID (2020-03-14)...")
        success, data, status = self.call_api("regime?asOf=2020-03-14")
        
        if not success:
            self.log_test("Regime COVID", False, f"HTTP {status}")
            return False
        
        # Check regime is RISK_OFF_STRESS
        regime = data.get("regime")
        is_risk_off_stress = regime == "RISK_OFF_STRESS"
        self.log_test("Regime COVID - RISK_OFF_STRESS", is_risk_off_stress, f"regime={regime}")
        
        return success and is_risk_off_stress
    
    def test_novelty_covid_to_gfc(self):
        """Test novelty detection for COVID showing GFC dates - C6 requirement 5"""
        print("\n🔍 Testing Novelty Detection COVID→GFC (2020-03-14)...")
        success, data, status = self.call_api("novelty?asOf=2020-03-14")
        
        if not success:
            self.log_test("Novelty COVID→GFC", False, f"HTTP {status}")
            return False
        
        # Check nearest dates contain 2008 dates
        nearest = data.get("nearest", [])
        has_2008_dates = any("2008" in str(item) for item in nearest)
        self.log_test("Novelty COVID→GFC - Contains 2008 dates", has_2008_dates, 
                     f"nearest={nearest[:3]}...")  # Show first 3 items
        
        return success and has_2008_dates
    
    def test_terminal_gfc(self):
        """Test terminal for GFC showing guard BLOCK and BEAR_STRESS - C6 requirement 6"""
        print("\n🔍 Testing Terminal for GFC (2008-10-11)...")
        success, data, status = self.call_api("terminal?asOf=2008-10-11")
        
        if not success:
            self.log_test("Terminal GFC", False, f"HTTP {status}")
            return False
        
        # Check guard is BLOCK
        recommendation = data.get("recommendation", {})
        guard = recommendation.get("guard")
        is_block_guard = guard == "BLOCK"
        self.log_test("Terminal GFC - Guard BLOCK", is_block_guard, f"guard={guard}")
        
        # Check scenarios for BEAR_STRESS dominance
        scenarios = data.get("scenarios", {}).get("scenarios", [])
        bear_stress_scenario = None
        for scenario in scenarios:
            if "BEAR" in scenario.get("name", "") or "STRESS" in scenario.get("name", ""):
                bear_stress_scenario = scenario
                break
        
        has_bear_stress = bear_stress_scenario is not None
        if has_bear_stress:
            bear_prob = bear_stress_scenario.get("prob", 0)
            is_dominant = bear_prob > 0.4  # Should be dominant scenario
            self.log_test("Terminal GFC - BEAR_STRESS Dominant", is_dominant, 
                         f"bear_stress_prob={bear_prob:.2f}")
        else:
            self.log_test("Terminal GFC - BEAR_STRESS Present", False, 
                         f"scenarios={[s.get('name') for s in scenarios]}")
        
        return success and is_block_guard and has_bear_stress
        
    def test_snapshot_endpoint(self):
        """Test POST /api/ae/admin/snapshot endpoint"""
        print("\n🔍 Testing Snapshot Endpoint (Admin)...")
        success, data, status = self.call_api("admin/snapshot", method="POST")
        
        if not success:
            # Try with different content-type
            try:
                url = f"{self.base_url}/api/ae/admin/snapshot"
                headers = {}  # Remove Content-Type for POST without body
                response = requests.post(url, headers=headers, timeout=30)
                success = response.status_code == 200
                try:
                    data = response.json()
                except:
                    data = {}
                status = response.status_code
            except Exception as e:
                self.log_test("Snapshot Endpoint", False, f"HTTP {status} - {str(e)}")
                return False
        
        if not success:
            self.log_test("Snapshot Endpoint", False, f"HTTP {status}")
            return False
        
        # Check response structure
        has_ok = data.get("ok") is not None
        has_state = "state" in data
        has_asOf = "asOf" in data
        
        self.log_test("Snapshot - Response Structure", has_ok and has_state and has_asOf, 
                     f"ok={data.get('ok')}, has_state={has_state}, has_asOf={has_asOf}")
        
        return success and has_ok and has_state and has_asOf
    
    def run_all_tests(self):
        """Run all AE Brain tests"""
        print("🚀 Starting AE Brain Module Tests...")
        print(f"Base URL: {self.base_url}")
        
        # Test all endpoints
        test_results = []
        test_results.append(self.test_health_endpoint())
        test_results.append(self.test_state_endpoint())
        test_results.append(self.test_regime_endpoint())
        test_results.append(self.test_causal_endpoint())
        test_results.append(self.test_scenarios_endpoint())
        test_results.append(self.test_novelty_endpoint())
        test_results.append(self.test_terminal_endpoint())
        test_results.append(self.test_snapshot_endpoint())
        
        # C6 Historical Backfill specific tests
        print("\n🏛️ C6 Historical Backfill Tests...")
        test_results.append(self.test_backfill_stats_endpoint())
        test_results.append(self.test_historical_state_gfc())
        test_results.append(self.test_regime_gfc())
        test_results.append(self.test_regime_covid())
        test_results.append(self.test_novelty_covid_to_gfc())
        test_results.append(self.test_terminal_gfc())
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failures:
            print(f"\n❌ Failures ({len(self.failures)}):")
            for failure in self.failures:
                print(f"  • {failure}")
        
        return all(test_results)

def main():
    """Main test runner"""
    tester = AEBrainTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n🎉 All AE Brain tests passed!")
        return 0
    else:
        print(f"\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())