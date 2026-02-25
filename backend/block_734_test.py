#!/usr/bin/env python3
"""
BLOCK 73.3 & 73.4 Testing Suite
Tests Unified Path Builder and Interactive Match Replay features
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class Block734Tester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: Dict[str, Any]):
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

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, timeout: int = 60) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            # Try to parse JSON response
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

    def test_unified_path_focus_pack(self):
        """BLOCK 73.3: Test unifiedPath with syntheticPath[0]=NOW"""
        params = {"symbol": "BTC", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
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
                forecast = focus_pack.get("forecast", {})
                
                # Check for unified path in forecast
                unified_path = forecast.get("unifiedPath")
                if not unified_path:
                    success = False
                    details["error"] = "Expected 'unifiedPath' in forecast"
                else:
                    # Check syntheticPath structure
                    synthetic_path = unified_path.get("syntheticPath", [])
                    if not synthetic_path:
                        success = False
                        details["error"] = "Expected 'syntheticPath' in unifiedPath"
                    else:
                        # BLOCK 73.3: Verify t=0 is NOW (anchorPrice)
                        first_point = synthetic_path[0]
                        anchor_price = unified_path.get("anchorPrice")
                        
                        if first_point.get("t") != 0:
                            success = False
                            details["error"] = f"Expected syntheticPath[0].t = 0, got {first_point.get('t')}"
                        elif first_point.get("pct") != 0:
                            success = False
                            details["error"] = f"Expected syntheticPath[0].pct = 0, got {first_point.get('pct')}"
                        elif first_point.get("price") != anchor_price:
                            success = False
                            details["error"] = f"Expected syntheticPath[0].price = anchorPrice ({anchor_price}), got {first_point.get('price')}"
                        else:
                            # Check path length is N+1 (t=0..N)
                            horizon_days = unified_path.get("horizonDays")
                            expected_length = horizon_days + 1 if horizon_days else None
                            actual_length = len(synthetic_path)
                            
                            if expected_length and actual_length != expected_length:
                                success = False
                                details["error"] = f"Expected syntheticPath length {expected_length} (N+1), got {actual_length}"
                            else:
                                details["unified_path_verified"] = {
                                    "anchorPrice": anchor_price,
                                    "horizonDays": horizon_days,
                                    "syntheticPath_length": actual_length,
                                    "t0_price": first_point.get("price"),
                                    "t0_pct": first_point.get("pct"),
                                }
                                details["note"] = f"UnifiedPath verified: t=0 = NOW (${anchor_price}), path length = {actual_length}"
        
        self.log_test("BLOCK 73.3: UnifiedPath with syntheticPath[0]=NOW", success, details)
        return success

    def test_replay_pack_endpoint(self):
        """BLOCK 73.4: Test /api/fractal/v2.1/replay-pack endpoint"""
        # First, get a focus pack to find available matches
        focus_params = {"symbol": "BTC", "focus": "30d"}
        focus_success, focus_details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=focus_params)
        
        if not focus_success:
            success = False
            details = {"error": "Failed to get focus pack for match ID"}
        else:
            focus_data = focus_details.get("response_data", {})
            focus_pack = focus_data.get("focusPack", {})
            overlay = focus_pack.get("overlay", {})
            matches = overlay.get("matches", [])
            
            if not matches:
                success = False
                details = {"error": "No matches found in focus pack"}
            else:
                # Test replay-pack with first match
                match_id = matches[0].get("id")
                if not match_id:
                    success = False
                    details = {"error": "Match ID not found in first match"}
                else:
                    # Test replay-pack endpoint
                    replay_params = {
                        "symbol": "BTC", 
                        "focus": "30d",
                        "matchId": match_id
                    }
                    success, details = self.make_request("GET", "/api/fractal/v2.1/replay-pack", params=replay_params)
                    
                    if success:
                        data = details.get("response_data", {})
                        if not data.get("ok"):
                            success = False
                            details["error"] = "Expected 'ok': true"
                        elif "replayPack" not in data:
                            success = False
                            details["error"] = "Expected 'replayPack' field"
                        else:
                            replay_pack = data["replayPack"]
                            
                            # Verify replay pack structure
                            required_fields = ["matchId", "matchMeta", "replayPath", "outcomes", "divergence"]
                            missing_fields = [f for f in required_fields if f not in replay_pack]
                            
                            if missing_fields:
                                success = False
                                details["error"] = f"Missing fields in replayPack: {missing_fields}"
                            else:
                                # Verify replay path structure
                                replay_path = replay_pack.get("replayPath", [])
                                if not replay_path:
                                    success = False
                                    details["error"] = "Empty replayPath"
                                else:
                                    # Check t=0 = NOW in replay path
                                    first_point = replay_path[0]
                                    if first_point.get("t") != 0:
                                        success = False
                                        details["error"] = f"Expected replayPath[0].t = 0, got {first_point.get('t')}"
                                    elif first_point.get("pct") != 0:
                                        success = False
                                        details["error"] = f"Expected replayPath[0].pct = 0, got {first_point.get('pct')}"
                                    else:
                                        details["replay_pack_verified"] = {
                                            "matchId": replay_pack.get("matchId"),
                                            "replayPath_length": len(replay_path),
                                            "outcomes_count": len(replay_pack.get("outcomes", [])),
                                            "divergence_available": "divergence" in replay_pack,
                                            "match_similarity": replay_pack.get("matchMeta", {}).get("similarity"),
                                        }
                                        details["note"] = f"ReplayPack verified for match {match_id}"
        
        self.log_test("BLOCK 73.4: Replay Pack Endpoint", success, details)
        return success

    def test_replay_pack_different_matches(self):
        """Test replay-pack with multiple different match IDs"""
        # Get focus pack to find multiple matches
        focus_params = {"symbol": "BTC", "focus": "30d"}
        focus_success, focus_details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=focus_params)
        
        if not focus_success:
            success = False
            details = {"error": "Failed to get focus pack for matches"}
        else:
            focus_data = focus_details.get("response_data", {})
            focus_pack = focus_data.get("focusPack", {})
            overlay = focus_pack.get("overlay", {})
            matches = overlay.get("matches", [])
            
            if len(matches) < 2:
                success = False
                details = {"error": f"Need at least 2 matches for testing, found {len(matches)}"}
            else:
                success = True
                details = {"tested_matches": []}
                
                # Test first 3 matches or all if fewer
                test_matches = matches[:3]
                
                for i, match in enumerate(test_matches):
                    match_id = match.get("id")
                    if not match_id:
                        continue
                        
                    replay_params = {
                        "symbol": "BTC", 
                        "focus": "30d",
                        "matchId": match_id
                    }
                    match_success, match_details = self.make_request("GET", "/api/fractal/v2.1/replay-pack", params=replay_params)
                    
                    if match_success:
                        data = match_details.get("response_data", {})
                        if data.get("ok") and "replayPack" in data:
                            replay_pack = data["replayPack"]
                            details["tested_matches"].append({
                                "matchId": match_id,
                                "similarity": match.get("similarity"),
                                "replayPath_length": len(replay_pack.get("replayPath", [])),
                                "divergence_score": replay_pack.get("divergence", {}).get("score"),
                                "success": True
                            })
                        else:
                            details["tested_matches"].append({
                                "matchId": match_id,
                                "error": "Failed to get valid replay pack",
                                "success": False
                            })
                            success = False
                    else:
                        details["tested_matches"].append({
                            "matchId": match_id,
                            "error": match_details.get("error"),
                            "success": False
                        })
                        success = False
                
                if success:
                    details["note"] = f"Successfully tested replay packs for {len(details['tested_matches'])} matches"
        
        self.log_test("BLOCK 73.4: Multiple Match Replay Packs", success, details)
        return success

    def test_replay_pack_error_handling(self):
        """Test replay-pack error handling for invalid inputs"""
        test_cases = [
            {
                "name": "Missing matchId",
                "params": {"symbol": "BTC", "focus": "30d"},
                "expected_error": "MATCH_ID_REQUIRED"
            },
            {
                "name": "Invalid symbol", 
                "params": {"symbol": "INVALID", "focus": "30d", "matchId": "test"},
                "expected_error": "BTC_ONLY"
            },
            {
                "name": "Invalid focus",
                "params": {"symbol": "BTC", "focus": "invalid", "matchId": "test"},
                "expected_error": "INVALID_HORIZON"
            },
            {
                "name": "Non-existent matchId",
                "params": {"symbol": "BTC", "focus": "30d", "matchId": "nonexistent-match-id"},
                "expected_error": "MATCH_NOT_FOUND"
            }
        ]
        
        success = True
        details = {"error_tests": []}
        
        for test_case in test_cases:
            case_success, case_details = self.make_request("GET", "/api/fractal/v2.1/replay-pack", params=test_case["params"])
            
            # For error cases, we expect the request to return with error
            data = case_details.get("response_data", {})
            error_code = data.get("error")
            
            if test_case["expected_error"] == error_code:
                details["error_tests"].append({
                    "name": test_case["name"],
                    "expected_error": test_case["expected_error"],
                    "actual_error": error_code,
                    "success": True
                })
            else:
                details["error_tests"].append({
                    "name": test_case["name"],
                    "expected_error": test_case["expected_error"],
                    "actual_error": error_code,
                    "success": False
                })
                success = False
        
        if success:
            details["note"] = "All error handling tests passed"
        
        self.log_test("BLOCK 73.4: Replay Pack Error Handling", success, details)
        return success

def main():
    """Run BLOCK 73.3 & 73.4 tests"""
    print("🔬 Starting BLOCK 73.3 & 73.4 Tests...")
    print("=" * 60)
    
    tester = Block734Tester()
    
    # Run all tests
    tests = [
        tester.test_unified_path_focus_pack,
        tester.test_replay_pack_endpoint,
        tester.test_replay_pack_different_matches,
        tester.test_replay_pack_error_handling
    ]
    
    for test in tests:
        try:
            test()
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
    
    # Print summary
    print("=" * 60)
    print(f"📊 BLOCK 73.3 & 73.4 Tests Summary:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    # Save detailed results
    with open("/app/backend/block_734_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "tests_run": tester.tests_run,
                "tests_passed": tester.tests_passed,
                "success_rate": tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0
            },
            "test_results": tester.test_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())