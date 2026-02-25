#!/usr/bin/env python3
"""
C7 Regime Clustering Backend API Testing
Tests k-means clustering on historical state vectors
"""

import requests
import json
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

class C7ClusteringTester:
    def __init__(self, base_url: str = "https://dxy-risk-overlay.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.failures: List[str] = []
        self.results = {}
        self.determinism_data = {}
        
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
        headers = {'Content-Type': 'application/json'}
        
        self.log(f"API {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
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
    
    def test_cluster_stats(self) -> bool:
        """Test /api/ae/cluster/stats shows totalRuns >= 1"""
        response = self.api_call('GET', '/api/ae/cluster/stats')
        
        if not response.get('ok'):
            self.log_test("Cluster Stats API", False, f"Error: {response.get('error')}")
            return False
        
        total_runs = response.get('totalRuns', 0)
        self.log(f"Total runs: {total_runs}")
        
        # Store for other tests
        self.results['stats_response'] = response
        
        success = total_runs >= 1
        self.log_test("Cluster stats shows totalRuns >= 1", success, f"totalRuns={total_runs}")
        return success

    def test_latest_returns_6_clusters(self) -> bool:
        """Test /api/ae/cluster/latest returns 6 clusters"""
        response = self.api_call('GET', '/api/ae/cluster/latest')
        
        if not response.get('ok'):
            self.log_test("Latest Clusters API", False, f"Error: {response.get('error')}")
            return False
        
        latest_run = response.get('latestRun')
        if not latest_run:
            self.log_test("Latest run data", False, "No latestRun found")
            return False
        
        clusters = latest_run.get('clusters', [])
        cluster_count = len(clusters)
        self.log(f"Found {cluster_count} clusters")
        
        # Store for other tests
        self.results['latest_run'] = latest_run
        
        success = cluster_count == 6
        self.log_test("Latest returns 6 clusters", success, f"cluster_count={cluster_count}")
        return success

    def test_current_2008_risk_off_stress(self) -> bool:
        """Test /api/ae/cluster/current?asOf=2008-10-11 returns RISK_OFF_STRESS"""
        response = self.api_call('GET', '/api/ae/cluster/current', params={'asOf': '2008-10-11'})
        
        if not response.get('ok'):
            self.log_test("Current 2008 API", False, f"Error: {response.get('error')}")
            return False
        
        label = response.get('label')
        cluster_id = response.get('clusterId')
        
        self.log(f"2008-10-11 cluster: {label} (ID: {cluster_id})")
        
        # Store for determinism test
        self.determinism_data['gfc_2008'] = {
            'clusterId': cluster_id,
            'label': label
        }
        
        success = label == 'RISK_OFF_STRESS'
        self.log_test("2008-10-11 returns RISK_OFF_STRESS", success, f"label={label}, clusterId={cluster_id}")
        return success

    def test_current_2020_risk_off_stress(self) -> bool:
        """Test /api/ae/cluster/current?asOf=2020-03-14 returns RISK_OFF_STRESS (same clusterId as GFC)"""
        response = self.api_call('GET', '/api/ae/cluster/current', params={'asOf': '2020-03-14'})
        
        if not response.get('ok'):
            self.log_test("Current 2020 API", False, f"Error: {response.get('error')}")
            return False
        
        label = response.get('label')
        cluster_id = response.get('clusterId')
        
        self.log(f"2020-03-14 cluster: {label} (ID: {cluster_id})")
        
        # Store for determinism test
        self.determinism_data['covid_2020'] = {
            'clusterId': cluster_id,
            'label': label
        }
        
        # Check if same as GFC 2008
        gfc_cluster_id = self.determinism_data.get('gfc_2008', {}).get('clusterId')
        same_cluster_as_gfc = cluster_id == gfc_cluster_id
        
        self.log(f"Same cluster as GFC 2008: {same_cluster_as_gfc}")
        
        success = label == 'RISK_OFF_STRESS' and same_cluster_as_gfc
        self.log_test("2020-03-14 returns RISK_OFF_STRESS (same cluster as GFC)", success, 
                     f"label={label}, clusterId={cluster_id}, same_as_gfc={same_cluster_as_gfc}")
        return success

    def test_current_2017_not_risk_off_stress(self) -> bool:
        """Test /api/ae/cluster/current?asOf=2017-07-01 returns not RISK_OFF_STRESS"""
        response = self.api_call('GET', '/api/ae/cluster/current', params={'asOf': '2017-07-01'})
        
        if not response.get('ok'):
            self.log_test("Current 2017 API", False, f"Error: {response.get('error')}")
            return False
        
        label = response.get('label')
        cluster_id = response.get('clusterId')
        
        self.log(f"2017-07-01 cluster: {label} (ID: {cluster_id})")
        
        success = label != 'RISK_OFF_STRESS'
        self.log_test("2017-07-01 returns not RISK_OFF_STRESS", success, f"label={label}")
        return success

    def test_timeline_points_count(self) -> bool:
        """Test /api/ae/cluster/timeline returns points.length >= 1300"""
        response = self.api_call('GET', '/api/ae/cluster/timeline')
        
        if not response.get('ok'):
            self.log_test("Timeline API", False, f"Error: {response.get('error')}")
            return False
        
        points = response.get('points', [])
        points_count = len(points)
        
        self.log(f"Timeline points count: {points_count}")
        
        # Store for cluster size validation
        self.results['timeline_points'] = points
        
        success = points_count >= 1300
        self.log_test("Timeline returns points.length >= 1300", success, f"points_count={points_count}")
        return success

    def test_cluster_sizes_sum_equals_snapshots(self) -> bool:
        """Test sum of cluster sizes = nSnapshots"""
        latest_run = self.results.get('latest_run')
        if not latest_run:
            self.log_test("Cluster sizes validation", False, "No latest run data available")
            return False
        
        clusters = latest_run.get('clusters', [])
        n_snapshots = latest_run.get('nSnapshots', 0)
        
        total_size = sum(cluster.get('size', 0) for cluster in clusters)
        
        self.log(f"Total cluster sizes: {total_size}, nSnapshots: {n_snapshots}")
        
        success = total_size == n_snapshots
        self.log_test("Sum of cluster sizes equals nSnapshots", success, 
                     f"total_size={total_size}, nSnapshots={n_snapshots}")
        return success

    def test_determinism_two_runs(self) -> bool:
        """Test two consecutive runs give identical results (determinism)"""
        self.log("Running first clustering...")
        
        # Run first clustering
        response1 = self.api_call('POST', '/api/ae/admin/cluster/run', params={'k': '6'})
        
        if not response1.get('ok'):
            self.log_test("Determinism - First run", False, f"Error: {response1.get('error')}")
            return False
        
        run1 = response1.get('latestRun')
        if not run1:
            self.log_test("Determinism - First run result", False, "No result from first run")
            return False
        
        # Wait a bit
        time.sleep(2)
        
        self.log("Running second clustering...")
        
        # Run second clustering
        response2 = self.api_call('POST', '/api/ae/admin/cluster/run', params={'k': '6'})
        
        if not response2.get('ok'):
            self.log_test("Determinism - Second run", False, f"Error: {response2.get('error')}")
            return False
        
        run2 = response2.get('latestRun')
        if not run2:
            self.log_test("Determinism - Second run result", False, "No result from second run")
            return False
        
        # Compare centroids (should be identical for deterministic algorithm)
        clusters1 = run1.get('clusters', [])
        clusters2 = run2.get('clusters', [])
        
        if len(clusters1) != len(clusters2):
            self.log_test("Determinism - Cluster count", False, 
                         f"Different cluster counts: {len(clusters1)} vs {len(clusters2)}")
            return False
        
        # Sort by clusterId to ensure consistent comparison
        clusters1_sorted = sorted(clusters1, key=lambda x: x.get('clusterId', 0))
        clusters2_sorted = sorted(clusters2, key=lambda x: x.get('clusterId', 0))
        
        identical = True
        details = []
        
        for c1, c2 in zip(clusters1_sorted, clusters2_sorted):
            centroid1 = c1.get('centroid', [])
            centroid2 = c2.get('centroid', [])
            label1 = c1.get('label', '')
            label2 = c2.get('label', '')
            
            if label1 != label2:
                details.append(f"Label diff cluster {c1.get('clusterId')}: {label1} vs {label2}")
                identical = False
            
            # Compare centroids with small tolerance
            if len(centroid1) != len(centroid2):
                details.append(f"Centroid dims diff cluster {c1.get('clusterId')}")
                identical = False
                continue
            
            for i, (v1, v2) in enumerate(zip(centroid1, centroid2)):
                if abs(v1 - v2) > 1e-6:
                    details.append(f"Centroid diff cluster {c1.get('clusterId')}, dim {i}: {v1} vs {v2}")
                    identical = False
                    break
        
        self.log_test("Two consecutive runs give identical results (determinism)", identical, 
                     "; ".join(details[:3]) if details else "All centroids identical")
        return identical

    def run_all_tests(self):
        """Run all C7 clustering tests"""
        self.log("=" * 60)
        self.log("Starting C7 Regime Clustering Backend Tests")
        self.log("=" * 60)
        
        # Test 1: Stats API
        success1 = self.test_cluster_stats()
        
        # Test 2: Latest run has 6 clusters
        success2 = self.test_latest_returns_6_clusters()
        
        # Test 3: 2008 GFC = RISK_OFF_STRESS
        success3 = self.test_current_2008_risk_off_stress()
        
        # Test 4: 2020 COVID = RISK_OFF_STRESS (same as GFC)
        success4 = self.test_current_2020_risk_off_stress()
        
        # Test 5: 2017 != RISK_OFF_STRESS
        success5 = self.test_current_2017_not_risk_off_stress()
        
        # Test 6: Timeline has >= 1300 points
        success6 = self.test_timeline_points_count()
        
        # Test 7: Cluster sizes sum = nSnapshots
        success7 = self.test_cluster_sizes_sum_equals_snapshots()
        
        # Test 8: Determinism (two identical runs)
        success8 = self.test_determinism_two_runs()
        
        # Print summary
        self.print_summary()
        
        return all([success1, success2, success3, success4, success5, success6, success7, success8])

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        self.log("-" * 60)
        self.log(f"📊 Tests passed: {self.tests_passed}/{self.tests_run} ({success_rate:.1f}%)")
        
        if self.failures:
            self.log(f"\n❌ Failures ({len(self.failures)}):")
            for failure in self.failures:
                self.log(f"  • {failure}")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All tests PASSED!")
        else:
            self.log("⚠️  Some tests FAILED")
        
        self.log("=" * 60)

def main():
    """Main test runner"""
    tester = C7ClusteringTester()
    
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())