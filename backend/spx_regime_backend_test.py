#!/usr/bin/env python3
"""
SPX REGIME ENGINE Backend Testing
Testing B6.11 + B6.12 implementation for Regime Matrix + Terminal Badge
"""

import requests
import json
import sys
from datetime import datetime

class SPXRegimeTester:
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

    def test_regimes_summary_api(self, preset="BALANCED"):
        """Test GET /api/spx/v2.1/admin/regimes/summary"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/summary"
        params = {"preset": preset} if preset != "BALANCED" else {}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Regime Summary API ({preset})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check required fields
            required_fields = ["ok", "data"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.log_test(
                    f"Regime Summary API ({preset})", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                return None
                
            if not data.get("ok", False):
                self.log_test(
                    f"Regime Summary API ({preset})", 
                    False, 
                    f"API returned ok=false, error: {data.get('error', 'Unknown error')}"
                )
                return None
                
            # Check data structure
            summary_data = data.get("data", {})
            required_data_fields = ["totalDays", "byRegime", "byVolBucket", "regimeDetails"]
            missing_data_fields = [f for f in required_data_fields if f not in summary_data]
            
            if missing_data_fields:
                self.log_test(
                    f"Regime Summary API ({preset})", 
                    False, 
                    f"Missing data fields: {missing_data_fields}"
                )
                return None
                
            total_days = summary_data.get("totalDays", 0)
            by_regime = summary_data.get("byRegime", {})
            by_vol_bucket = summary_data.get("byVolBucket", {})
            regime_details = summary_data.get("regimeDetails", [])
            
            self.log_test(
                f"Regime Summary API ({preset})", 
                True, 
                f"Total days: {total_days}, Regimes: {len(by_regime)}, Vol buckets: {len(by_vol_bucket)}, Details: {len(regime_details)}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Regime Summary API ({preset})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_regimes_current_api(self, preset="BALANCED"):
        """Test GET /api/spx/v2.1/admin/regimes/current"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/current"
        params = {"preset": preset} if preset != "BALANCED" else {}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Regime Current API ({preset})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check required fields
            required_fields = ["ok", "data"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.log_test(
                    f"Regime Current API ({preset})", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                return None
                
            if not data.get("ok", False):
                self.log_test(
                    f"Regime Current API ({preset})", 
                    False, 
                    f"API returned ok=false, error: {data.get('error', 'Unknown error')}"
                )
                return None
                
            # Check current regime data structure
            current_data = data.get("data")
            if current_data is None:
                self.log_test(
                    f"Regime Current API ({preset})", 
                    True, 
                    "No current regime data (expected if not computed yet)"
                )
                return data
                
            required_current_fields = ["date", "regimeTag", "description", "riskLevel", "features", "isModelUseful"]
            missing_current_fields = [f for f in required_current_fields if f not in current_data]
            
            if missing_current_fields:
                self.log_test(
                    f"Regime Current API ({preset})", 
                    False, 
                    f"Missing current data fields: {missing_current_fields}"
                )
                return None
                
            regime_tag = current_data.get("regimeTag", "")
            description = current_data.get("description", "")
            risk_level = current_data.get("riskLevel", "")
            is_model_useful = current_data.get("isModelUseful", False)
            
            self.log_test(
                f"Regime Current API ({preset})", 
                True, 
                f"Current regime: {regime_tag}, Risk: {risk_level}, Model useful: {is_model_useful}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Regime Current API ({preset})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_regimes_matrix_api(self, preset="BALANCED"):
        """Test GET /api/spx/v2.1/admin/regimes/matrix"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/matrix"
        params = {"preset": preset} if preset != "BALANCED" else {}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Regime Matrix API ({preset})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check required fields
            required_fields = ["ok", "data"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.log_test(
                    f"Regime Matrix API ({preset})", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                return None
                
            if not data.get("ok", False):
                self.log_test(
                    f"Regime Matrix API ({preset})", 
                    False, 
                    f"API returned ok=false, error: {data.get('error', 'Unknown error')}"
                )
                return None
                
            # Check matrix data structure
            matrix_data = data.get("data", {})
            required_matrix_fields = ["computedAt", "totalSamples", "regimes", "horizons", "cells", "summary"]
            missing_matrix_fields = [f for f in required_matrix_fields if f not in matrix_data]
            
            if missing_matrix_fields:
                self.log_test(
                    f"Regime Matrix API ({preset})", 
                    False, 
                    f"Missing matrix fields: {missing_matrix_fields}"
                )
                return None
                
            total_samples = matrix_data.get("totalSamples", 0)
            regimes = matrix_data.get("regimes", [])
            horizons = matrix_data.get("horizons", [])
            cells = matrix_data.get("cells", [])
            
            self.log_test(
                f"Regime Matrix API ({preset})", 
                True, 
                f"Total samples: {total_samples}, Regimes: {len(regimes)}, Horizons: {len(horizons)}, Cells: {len(cells)}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Regime Matrix API ({preset})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_regimes_recompute_api(self, preset="BALANCED", from_idx=60, chunk_size=1000):
        """Test POST /api/spx/v2.1/admin/regimes/recompute"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/recompute"
        
        # Small recompute to test functionality without long execution
        payload = {
            "preset": preset,
            "fromIdx": from_idx,
            "toIdx": from_idx + chunk_size,  # Only recompute 1000 records for testing
            "chunkSize": 500
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)  # Longer timeout for computation
            
            if response.status_code != 200:
                self.log_test(
                    f"Regime Recompute API ({preset})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check required fields
            required_fields = ["ok", "result"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.log_test(
                    f"Regime Recompute API ({preset})", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                return None
                
            if not data.get("ok", False):
                self.log_test(
                    f"Regime Recompute API ({preset})", 
                    False, 
                    f"API returned ok=false, error: {data.get('error', 'Unknown error')}"
                )
                return None
                
            # Check recompute result structure
            result_data = data.get("result", {})
            required_result_fields = ["processed", "written"]
            missing_result_fields = [f for f in required_result_fields if f not in result_data]
            
            if missing_result_fields:
                self.log_test(
                    f"Regime Recompute API ({preset})", 
                    False, 
                    f"Missing result fields: {missing_result_fields}"
                )
                return None
                
            processed = result_data.get("processed", 0)
            written = result_data.get("written", 0)
            
            self.log_test(
                f"Regime Recompute API ({preset})", 
                True, 
                f"Processed: {processed}, Written: {written}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Regime Recompute API ({preset})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_regime_data_quality(self, summary_data):
        """Test regime data quality and consistency"""
        if not summary_data:
            return
            
        data = summary_data.get("data", {})
        total_days = data.get("totalDays", 0)
        by_regime = data.get("byRegime", {})
        by_vol_bucket = data.get("byVolBucket", {})
        regime_details = data.get("regimeDetails", [])
        
        # Test 1: Total days should match sum of regimes
        regime_sum = sum(by_regime.values()) if by_regime else 0
        vol_bucket_sum = sum(by_vol_bucket.values()) if by_vol_bucket else 0
        
        regime_match = (regime_sum == total_days)
        vol_bucket_match = (vol_bucket_sum == total_days)
        
        self.log_test(
            "Regime Data Consistency - By Regime", 
            regime_match, 
            f"Total days: {total_days}, Regime sum: {regime_sum}"
        )
        
        self.log_test(
            "Regime Data Consistency - By Vol Bucket", 
            vol_bucket_match, 
            f"Total days: {total_days}, Vol bucket sum: {vol_bucket_sum}"
        )
        
        # Test 2: Check expected regime tags (B6.13.1 TRANSITION split)
        expected_regimes = [
            "LOWVOL_TREND_UP", "LOWVOL_TREND_DOWN", "LOWVOL_RANGE",
            "MEDVOL_TREND_UP", "MEDVOL_TREND_DOWN", "MEDVOL_RANGE", 
            "HIGHVOL_SLOW_DRAWDOWN", "HIGHVOL_FAST_SHOCK", "HIGHVOL_VSHAPE", "HIGHVOL_RECOVERY",
            "TRANSITION", "TRANSITION_VOL_UP", "TRANSITION_VOL_DOWN", 
            "TRANSITION_TREND_FLIP", "TRANSITION_RANGE_BREAK"
        ]
        
        found_regimes = set(by_regime.keys())
        expected_set = set(expected_regimes)
        missing_regimes = expected_set - found_regimes
        extra_regimes = found_regimes - expected_set
        
        # It's OK to have fewer regimes if some don't occur in the data
        has_core_regimes = all(r in found_regimes for r in ["LOWVOL_TREND_UP", "LOWVOL_TREND_DOWN"])
        
        self.log_test(
            "Regime Tags Structure", 
            has_core_regimes, 
            f"Found: {len(found_regimes)}, Expected core regimes present: {has_core_regimes}"
        )
        
        if missing_regimes:
            self.log_test(
                "Missing Regime Tags (Info)", 
                True,  # Not a failure, just info
                f"Missing: {sorted(missing_regimes)} (OK if not present in data)"
            )
        
        # Test 3: Check vol buckets
        expected_vol_buckets = ["LOW", "MEDIUM", "HIGH"]
        found_vol_buckets = set(by_vol_bucket.keys())
        missing_vol_buckets = set(expected_vol_buckets) - found_vol_buckets
        
        vol_buckets_complete = len(missing_vol_buckets) == 0
        self.log_test(
            "Vol Buckets Structure", 
            vol_buckets_complete, 
            f"Found buckets: {sorted(found_vol_buckets)}, Missing: {sorted(missing_vol_buckets)}"
        )
        
        # Test 4: Check regime details structure
        if regime_details:
            detail_fields = ["tag", "count", "description", "riskLevel", "isModelUseful"]
            first_detail = regime_details[0]
            has_all_fields = all(field in first_detail for field in detail_fields)
            
            self.log_test(
                "Regime Details Structure", 
                has_all_fields, 
                f"Detail fields present: {has_all_fields}, Sample detail keys: {list(first_detail.keys())}"
            )

    def test_current_regime_features(self, current_data):
        """Test current regime features structure"""
        if not current_data:
            return
            
        data = current_data.get("data")
        if not data:
            self.log_test("Current Regime Features", True, "No current data to test (OK)")
            return
            
        features = data.get("features", {})
        if not features:
            self.log_test("Current Regime Features", False, "Features missing from current regime")
            return
            
        # Check key feature fields
        expected_features = [
            "vol20", "vol60", "volBucket", "volBucket5dAgo", 
            "maxDD60", "ddSpeed", "trendDir", "trendPersistence30",
            "sma50", "sma50Slope", "isShock", "isVShape"
        ]
        
        found_features = set(features.keys())
        missing_features = set(expected_features) - found_features
        
        features_complete = len(missing_features) == 0
        self.log_test(
            "Current Regime Features Structure", 
            features_complete, 
            f"Found: {len(found_features)}, Missing: {sorted(missing_features)}"
        )
        
        # Check vol bucket values
        vol_bucket = features.get("volBucket", "")
        vol_bucket_5d_ago = features.get("volBucket5dAgo", "")
        valid_buckets = {"LOW", "MEDIUM", "HIGH"}
        
        vol_bucket_valid = vol_bucket in valid_buckets
        vol_bucket_5d_valid = vol_bucket_5d_ago in valid_buckets
        
        self.log_test(
            "Vol Bucket Values", 
            vol_bucket_valid and vol_bucket_5d_valid, 
            f"Current: {vol_bucket}, 5d ago: {vol_bucket_5d_ago}"
        )

    def run_all_tests(self):
        """Run all SPX Regime Engine tests"""
        print("=" * 60)
        print("SPX REGIME ENGINE BACKEND TESTING (B6.11 + B6.12)")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test all 4 endpoints with BALANCED preset
        preset = "BALANCED"
        
        print(f"Testing with preset: {preset}")
        print("-" * 40)
        
        # 1. Test summary endpoint
        summary_data = self.test_regimes_summary_api(preset)
        if summary_data:
            self.test_regime_data_quality(summary_data)
        
        # 2. Test current endpoint  
        current_data = self.test_regimes_current_api(preset)
        if current_data:
            self.test_current_regime_features(current_data)
        
        # 3. Test matrix endpoint
        matrix_data = self.test_regimes_matrix_api(preset)
        
        # 4. Test recompute endpoint (small test)
        print("\nTesting recompute (small batch)...")
        recompute_data = self.test_regimes_recompute_api(preset, from_idx=18000, chunk_size=100)
        
        # Test other presets quickly
        print("\nTesting other presets...")
        for test_preset in ["DEFENSIVE", "AGGRESSIVE"]:
            self.test_regimes_summary_api(test_preset)
            self.test_regimes_current_api(test_preset)
        
        print()
        print("=" * 60)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = SPXRegimeTester()
    passed, total, results = tester.run_all_tests()
    
    # Save results
    with open('/app/test_reports/spx_regime_backend_test_results.json', 'w') as f:
        json.dump({
            "summary": "SPX Regime Engine Backend Testing (B6.11 + B6.12)",
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "timestamp": datetime.now().isoformat(),
            "test_details": results
        }, f, indent=2)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())