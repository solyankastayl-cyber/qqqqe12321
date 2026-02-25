#!/usr/bin/env python3
"""
Phase Click Drilldown Feature Testing
Tests the BLOCK 73.5.2 Phase Filter functionality
"""

import requests
import json
import sys
from datetime import datetime

class PhaseFilterTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success and "error" in details:
            print(f"    Error: {details['error']}")
        if "note" in details:
            print(f"    Note: {details['note']}")
        print()

    def make_request(self, method, endpoint, params=None, timeout=30):
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            return response.status_code == 200, {
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_focus_pack_no_filter(self):
        """Test focus-pack without phaseId - should return all matches"""
        params = {"symbol": "BTC", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        all_matches_count = 0
        phases_found = set()
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                overlay = focus_pack.get("overlay", {})
                matches = overlay.get("matches", [])
                
                all_matches_count = len(matches)
                details["all_matches_count"] = all_matches_count
                
                if all_matches_count < 10:
                    success = False
                    details["error"] = f"Expected at least 10 matches without filter, got {all_matches_count}"
                
                # Should NOT have phaseFilter
                phase_filter = focus_pack.get("phaseFilter")
                if phase_filter is not None:
                    success = False
                    details["error"] = "Expected no phaseFilter when no phaseId provided"
                
                # Collect phase information
                for match in matches[:10]:  # Check first 10
                    if "phase" in match:
                        phases_found.add(match["phase"])
                
                details["phases_found"] = list(phases_found)
                if len(phases_found) < 2:
                    details["warning"] = f"Only found {len(phases_found)} unique phases"
        
        self.log_test("Focus Pack - No Phase Filter (All Matches)", success, details)
        return success, all_matches_count, phases_found

    def test_focus_pack_accumulation_filter(self):
        """Test focus-pack with ACCUMULATION phase filter"""
        params = {
            "symbol": "BTC", 
            "focus": "30d",
            "phaseId": "ACCUMULATION_2025-02-25_2025-03-01"
        }
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        filtered_matches_count = 0
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                overlay = focus_pack.get("overlay", {})
                matches = overlay.get("matches", [])
                
                filtered_matches_count = len(matches)
                details["filtered_matches_count"] = filtered_matches_count
                
                # Should have phaseFilter object
                phase_filter = focus_pack.get("phaseFilter")
                if not phase_filter:
                    success = False
                    details["error"] = "Expected phaseFilter object when phaseId provided"
                else:
                    # Validate phaseFilter structure
                    required_fields = ["phaseId", "phaseType", "filteredMatchCount", "active"]
                    missing_fields = [f for f in required_fields if f not in phase_filter]
                    if missing_fields:
                        success = False
                        details["error"] = f"Missing phaseFilter fields: {missing_fields}"
                    elif phase_filter["phaseId"] != "ACCUMULATION_2025-02-25_2025-03-01":
                        success = False
                        details["error"] = f"Expected phaseId 'ACCUMULATION_2025-02-25_2025-03-01', got '{phase_filter['phaseId']}'"
                    elif phase_filter["phaseType"] != "ACCUMULATION":
                        success = False
                        details["error"] = f"Expected phaseType 'ACCUMULATION', got '{phase_filter['phaseType']}'"
                    elif not phase_filter["active"]:
                        success = False
                        details["error"] = "Expected phaseFilter.active to be true"
                    elif phase_filter["filteredMatchCount"] != len(matches):
                        success = False
                        details["error"] = f"phaseFilter.filteredMatchCount ({phase_filter['filteredMatchCount']}) != matches length ({len(matches)})"
                    else:
                        details["phase_filter"] = phase_filter
                
                # All filtered matches should have ACCUMULATION phase
                if success and matches:
                    non_accumulation = [m for m in matches if m.get("phase") != "ACCUMULATION"]
                    if non_accumulation:
                        success = False
                        details["error"] = f"Found {len(non_accumulation)} non-ACCUMULATION matches in filtered results"
                    else:
                        details["note"] = f"✅ All {len(matches)} matches have ACCUMULATION phase"
        
        self.log_test("Focus Pack - ACCUMULATION Phase Filter", success, details)
        return success, filtered_matches_count

    def test_phase_filtering_effectiveness(self):
        """Test that phase filtering actually reduces match count"""
        print("🔍 Testing Phase Filter Effectiveness...")
        
        # Get all matches first
        success_all, all_count, phases_found = self.test_focus_pack_no_filter()
        
        if not success_all or all_count == 0:
            self.log_test("Phase Filter Effectiveness", False, {"error": "Failed to get baseline matches"})
            return False
        
        # Test filtering by first available phase
        if not phases_found:
            self.log_test("Phase Filter Effectiveness", False, {"error": "No phases found in matches"})
            return False
        
        test_phase = list(phases_found)[0]
        params = {
            "symbol": "BTC", 
            "focus": "30d",
            "phaseId": f"{test_phase}_2024-01-01_2024-02-01"
        }
        
        success_filtered, details_filtered = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        success = success_filtered
        details = {
            "all_matches_count": all_count,
            "test_phase": test_phase,
            "all_phases_found": list(phases_found)
        }
        
        if success:
            filtered_data = details_filtered.get("response_data", {})
            filtered_matches = filtered_data.get("focusPack", {}).get("overlay", {}).get("matches", [])
            filtered_count = len(filtered_matches)
            
            details["filtered_matches_count"] = filtered_count
            
            # Check effectiveness
            if filtered_count >= all_count:
                success = False
                details["error"] = f"Filter ineffective: {filtered_count} >= {all_count} (should reduce count)"
            elif filtered_count == 0:
                details["warning"] = f"No {test_phase} matches found - phase may not exist in current data"
                details["note"] = "Filter working (reduced to 0), but might need different phase for testing"
            else:
                # Validate all matches have correct phase
                wrong_phase = [m for m in filtered_matches if m.get("phase") != test_phase]
                if wrong_phase:
                    success = False
                    details["error"] = f"{len(wrong_phase)}/{filtered_count} matches have wrong phase"
                else:
                    reduction_pct = ((all_count - filtered_count) / all_count * 100)
                    details["note"] = f"✅ Filter effective: {all_count} → {filtered_count} ({reduction_pct:.1f}% reduction)"
                    details["effectiveness"] = f"{reduction_pct:.1f}% reduction"
        
        self.log_test("Phase Filter Effectiveness Test", success, details)
        return success

    def test_multiple_phase_filters(self):
        """Test filtering by different phase types"""
        print("🔄 Testing Multiple Phase Types...")
        
        phase_test_cases = [
            ("ACCUMULATION_2024-01-01_2024-02-01", "ACCUMULATION"),
            ("MARKUP_2024-03-01_2024-04-01", "MARKUP"),
            ("DISTRIBUTION_2024-05-01_2024-06-01", "DISTRIBUTION"),
            ("MARKDOWN_2024-07-01_2024-08-01", "MARKDOWN")
        ]
        
        results = {}
        overall_success = True
        
        for phase_id, expected_phase in phase_test_cases:
            params = {"symbol": "BTC", "focus": "30d", "phaseId": phase_id}
            success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
            
            if success:
                data = details.get("response_data", {})
                focus_pack = data.get("focusPack", {})
                matches = focus_pack.get("overlay", {}).get("matches", [])
                phase_filter = focus_pack.get("phaseFilter")
                
                results[expected_phase] = {
                    "matches_count": len(matches),
                    "filter_active": phase_filter and phase_filter.get("active", False),
                    "phase_type_correct": phase_filter and phase_filter.get("phaseType") == expected_phase
                }
                
                # Validate matches have correct phase (if any matches found)
                if matches:
                    wrong_phase_count = sum(1 for m in matches if m.get("phase") != expected_phase)
                    if wrong_phase_count > 0:
                        overall_success = False
                        results[expected_phase]["error"] = f"{wrong_phase_count}/{len(matches)} wrong phase"
            else:
                overall_success = False
                results[expected_phase] = {"error": f"Request failed: {details.get('error')}"}
        
        details = {"phase_results": results}
        if overall_success:
            working_phases = [p for p, r in results.items() if r.get("matches_count", 0) > 0]
            details["note"] = f"✅ Phase filters working for: {working_phases}" if working_phases else "⚠️ No matches found for any phase type"
        
        self.log_test("Multiple Phase Types Test", overall_success, details)
        return overall_success

    def run_all_tests(self):
        """Run all phase filter tests"""
        print("🚀 Phase Click Drilldown Feature Testing")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Basic functionality
        self.test_focus_pack_no_filter()
        
        # Test 2: ACCUMULATION filter
        self.test_focus_pack_accumulation_filter()
        
        # Test 3: Filter effectiveness
        self.test_phase_filtering_effectiveness()
        
        # Test 4: Multiple phase types
        self.test_multiple_phase_filters()
        
        # Summary
        print("=" * 60)
        print(f"📊 PHASE FILTER TEST SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("✅ ALL TESTS PASSED - Phase Click Drilldown working correctly!")
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            
        return self.tests_passed == self.tests_run

def main():
    tester = PhaseFilterTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())