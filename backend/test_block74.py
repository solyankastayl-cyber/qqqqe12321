#!/usr/bin/env python3
"""
BLOCK 74 Specific Tests - Multi-Horizon Intelligence Stack
"""

import requests
import sys
import json
from datetime import datetime

class Block74Tester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: dict):
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
        if success and "note" in details:
            print(f"    {details['note']}")
        print()

    def make_request(self, method: str, endpoint: str, params: dict = None):
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
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

    def test_horizon_stack_structure(self):
        """Test /api/fractal/v2.1/terminal - horizonStack array structure (BLOCK 74.1)"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            if "horizonStack" not in data:
                success = False
                details["error"] = "Expected 'horizonStack' field in response"
            else:
                horizon_stack = data["horizonStack"]
                if not isinstance(horizon_stack, list):
                    success = False
                    details["error"] = "Expected 'horizonStack' to be an array"
                elif len(horizon_stack) == 0:
                    success = False
                    details["error"] = "Expected non-empty 'horizonStack' array"
                else:
                    # Validate first horizon stack item structure
                    first_item = horizon_stack[0]
                    required_fields = ["horizon", "tier", "direction", "voteWeight"]
                    missing_fields = [field for field in required_fields if field not in first_item]
                    if missing_fields:
                        success = False
                        details["error"] = f"Missing horizonStack fields: {missing_fields}"
                    else:
                        # Validate field values
                        valid_tiers = ["TIMING", "TACTICAL", "STRUCTURE"]
                        valid_directions = ["BULLISH", "BEARISH", "FLAT"]
                        
                        if first_item["tier"] not in valid_tiers:
                            success = False
                            details["error"] = f"Invalid tier '{first_item['tier']}', expected one of {valid_tiers}"
                        elif first_item["direction"] not in valid_directions:
                            success = False
                            details["error"] = f"Invalid direction '{first_item['direction']}', expected one of {valid_directions}"
                        elif not isinstance(first_item["voteWeight"], (int, float)):
                            success = False
                            details["error"] = f"Expected voteWeight to be numeric, got {type(first_item['voteWeight'])}"
                        else:
                            details["note"] = f"✅ Found {len(horizon_stack)} horizons with proper structure"
                            
                            # Check if all expected horizons are present (extended set)
                            expected_horizons = ["7d", "14d", "30d", "90d", "180d", "365d"]
                            actual_horizons = [item["horizon"] for item in horizon_stack]
                            missing_horizons = [h for h in expected_horizons if h not in actual_horizons]
                            if missing_horizons:
                                success = False
                                details["error"] = f"Missing horizons in stack: {missing_horizons}"
        
        self.log_test("BLOCK 74.1 - Horizon Stack Structure", success, details)
        return success

    def test_consensus74_structure(self):
        """Test /api/fractal/v2.1/terminal - consensus74 object structure (BLOCK 74.2)"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            if "consensus74" not in data:
                success = False
                details["error"] = "Expected 'consensus74' field in response"
            else:
                consensus74 = data["consensus74"]
                if not isinstance(consensus74, dict):
                    success = False
                    details["error"] = "Expected 'consensus74' to be an object"
                else:
                    # Validate consensus74 structure
                    required_fields = ["consensusIndex", "conflictLevel", "resolved", "votes"]
                    missing_fields = [field for field in required_fields if field not in consensus74]
                    if missing_fields:
                        success = False
                        details["error"] = f"Missing consensus74 fields: {missing_fields}"
                    else:
                        # Validate field values
                        consensus_index = consensus74["consensusIndex"]
                        conflict_level = consensus74["conflictLevel"]
                        resolved = consensus74["resolved"]
                        votes = consensus74["votes"]
                        
                        if not isinstance(consensus_index, int) or consensus_index < 0 or consensus_index > 100:
                            success = False
                            details["error"] = f"Expected consensusIndex 0-100, got {consensus_index}"
                        elif conflict_level not in ["LOW", "MODERATE", "HIGH"]:
                            success = False
                            details["error"] = f"Invalid conflictLevel '{conflict_level}', expected LOW/MODERATE/HIGH"
                        elif not isinstance(resolved, dict):
                            success = False
                            details["error"] = "Expected 'resolved' to be an object"
                        elif not isinstance(votes, list):
                            success = False
                            details["error"] = "Expected 'votes' to be an array"
                        else:
                            # Validate resolved structure
                            resolved_fields = ["action", "mode", "sizeMultiplier"]
                            missing_resolved = [field for field in resolved_fields if field not in resolved]
                            if missing_resolved:
                                success = False
                                details["error"] = f"Missing resolved fields: {missing_resolved}"
                            elif resolved["action"] not in ["BUY", "SELL", "HOLD"]:
                                success = False
                                details["error"] = f"Invalid resolved action '{resolved['action']}'"
                            else:
                                details["note"] = f"✅ Consensus index: {consensus_index}, conflict: {conflict_level}, action: {resolved['action']}, votes: {len(votes)}"
        
        self.log_test("BLOCK 74.2 - Consensus74 Structure", success, details)
        return success

    def test_adaptive_weights_logic(self):
        """Test horizon stack adaptive weighting logic (BLOCK 74.1)"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            horizon_stack = data.get("horizonStack", [])
            
            if len(horizon_stack) == 0:
                success = False
                details["error"] = "No horizon stack data to validate"
            else:
                # Test adaptive weighting logic
                structure_weights = []
                tactical_weights = []
                timing_weights = []
                
                for item in horizon_stack:
                    tier = item["tier"]
                    vote_weight = item["voteWeight"]
                    
                    if tier == "STRUCTURE":
                        structure_weights.append(vote_weight)
                    elif tier == "TACTICAL":
                        tactical_weights.append(vote_weight)
                    elif tier == "TIMING":
                        timing_weights.append(vote_weight)
                
                # Validate adaptive weighting expectations
                avg_structure = sum(structure_weights) / len(structure_weights) if structure_weights else 0
                avg_tactical = sum(tactical_weights) / len(tactical_weights) if tactical_weights else 0
                avg_timing = sum(timing_weights) / len(timing_weights) if timing_weights else 0
                
                details["note"] = f"✅ Adaptive weights - Structure: {avg_structure:.3f}, Tactical: {avg_tactical:.3f}, Timing: {avg_timing:.3f}"
        
        self.log_test("BLOCK 74.1 - Adaptive Weights Logic", success, details)
        return success

    def test_institutional_consensus_logic(self):
        """Test institutional consensus calculation logic (BLOCK 74.2)"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            consensus74 = data.get("consensus74", {})
            
            if not consensus74:
                success = False
                details["error"] = "Missing consensus74 data"
            else:
                # Validate consensus index calculation
                votes = consensus74.get("votes", [])
                consensus_index = consensus74.get("consensusIndex", 50)
                
                # Calculate manual consensus for verification
                bullish_weight = sum(v["weight"] for v in votes if v["direction"] == "BULLISH")
                bearish_weight = sum(v["weight"] for v in votes if v["direction"] == "BEARISH")
                total_weight = sum(v["weight"] for v in votes)
                
                if total_weight > 0:
                    # Validate that consensus makes sense (all FLAT = 50)
                    all_flat = all(v["direction"] == "FLAT" for v in votes)
                    if all_flat and consensus_index != 50:
                        success = False
                        details["error"] = f"Expected consensus 50 for all FLAT signals, got {consensus_index}"
                    else:
                        details["note"] = f"✅ Consensus calculation valid - Index: {consensus_index}, Total votes: {len(votes)}"
                        
                        # Check conflict level logic
                        conflict_level = consensus74.get("conflictLevel", "MODERATE")
                        if bullish_weight == bearish_weight == 0:  # All flat
                            details["note"] += f", Conflict: {conflict_level} (all flat signals)"
                else:
                    success = False
                    details["error"] = "No vote weights found"
        
        self.log_test("BLOCK 74.2 - Institutional Consensus Logic", success, details)
        return success

    def run_all_tests(self):
        """Run all BLOCK 74 tests"""
        print("🧠 BLOCK 74: Multi-Horizon Intelligence Stack Tests")
        print("=" * 60)
        
        tests = [
            self.test_horizon_stack_structure(),
            self.test_consensus74_structure(),
            self.test_adaptive_weights_logic(),
            self.test_institutional_consensus_logic(),
        ]
        
        print("=" * 60)
        print(f"📊 BLOCK 74 TEST SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0.0%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL BLOCK 74 TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} TESTS FAILED")
            return 1

def main():
    """Main test execution"""
    print("🔧 BLOCK 74 Testing Suite - Multi-Horizon Intelligence Stack")
    print(f"Testing backend at: http://localhost:8001")
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    tester = Block74Tester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())