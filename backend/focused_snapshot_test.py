#!/usr/bin/env python3
"""
Focused BTC Signal Snapshot Writer Test

Testing exactly what the requirements specify:
1. POST write-btc - first call should write 3 presets (written:3)
2. POST write-btc - repeat call should return skipped:3  
3. GET latest?symbol=BTC - should return found:true with data
4. GET count?symbol=BTC - should show active and shadow counts
"""

import requests
import sys
import json
from datetime import datetime, timedelta

def test_requirements():
    """Test the exact requirements from the review request"""
    base_url = "http://localhost:8002"
    test_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    print("🔍 Testing BTC Signal Snapshot Writer Requirements")
    print("=" * 60)
    
    results = {
        "passed": 0,
        "total": 0,
        "details": []
    }
    
    # Test 1: Write BTC snapshots (first call should write 3)
    print(f"\n✍️ Test 1: POST write-btc (first call) - Date: {test_date}")
    try:
        url = f"{base_url}/api/fractal/v2.1/admin/snapshot/write-btc?asofDate={test_date}"
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            written = data.get('written', 0)
            skipped = data.get('skipped', 0) 
            items = data.get('items', [])
            
            if written == 3 and skipped == 0:
                print(f"✅ PASSED - Written: {written}, Skipped: {skipped}")
                results["passed"] += 1
                results["details"].append(f"✅ First write call: written={written}, skipped={skipped}")
            elif written == 0 and skipped == 3:
                print(f"⚠️ WARNING - Snapshots already exist for {test_date}")
                print(f"   Written: {written}, Skipped: {skipped}")
                results["passed"] += 1  # This is still valid behavior
                results["details"].append(f"⚠️ First write call: already exists (written={written}, skipped={skipped})")
            else:
                print(f"❌ FAILED - Expected written=3, skipped=0 or written=0, skipped=3")
                print(f"   Got: written={written}, skipped={skipped}")
                results["details"].append(f"❌ First write call: unexpected counts")
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            results["details"].append(f"❌ First write call: HTTP {response.status_code}")
            
        results["total"] += 1
    except Exception as e:
        print(f"❌ FAILED - Exception: {e}")
        results["details"].append(f"❌ First write call: Exception: {e}")
        results["total"] += 1
    
    # Test 2: Repeat write call (should return skipped:3)
    print(f"\n🔄 Test 2: POST write-btc (repeat call) - Date: {test_date}")
    try:
        url = f"{base_url}/api/fractal/v2.1/admin/snapshot/write-btc?asofDate={test_date}"
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            written = data.get('written', 0)
            skipped = data.get('skipped', 0)
            
            if written == 0 and skipped == 3:
                print(f"✅ PASSED - Written: {written}, Skipped: {skipped}")
                results["passed"] += 1
                results["details"].append(f"✅ Repeat write call: written={written}, skipped={skipped}")
            else:
                print(f"❌ FAILED - Expected written=0, skipped=3")
                print(f"   Got: written={written}, skipped={skipped}")
                results["details"].append(f"❌ Repeat write call: unexpected counts")
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            results["details"].append(f"❌ Repeat write call: HTTP {response.status_code}")
            
        results["total"] += 1
    except Exception as e:
        print(f"❌ FAILED - Exception: {e}")
        results["details"].append(f"❌ Repeat write call: Exception: {e}")
        results["total"] += 1
    
    # Test 3: GET latest snapshot
    print(f"\n📋 Test 3: GET latest?symbol=BTC")
    try:
        url = f"{base_url}/api/fractal/v2.1/admin/snapshot/latest?symbol=BTC"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            found = data.get('found', False)
            
            if found and 'snapshot' in data:
                snapshot = data['snapshot']
                print(f"✅ PASSED - Found: {found}")
                print(f"   Latest snapshot: Date={snapshot.get('asofDate')}, Action={snapshot.get('action')}, Preset={snapshot.get('preset')}")
                results["passed"] += 1
                results["details"].append(f"✅ Latest snapshot: found={found} with data")
            else:
                print(f"❌ FAILED - Expected found=true with snapshot data")
                print(f"   Got: found={found}, snapshot exists={('snapshot' in data)}")
                results["details"].append(f"❌ Latest snapshot: not found or missing data")
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            results["details"].append(f"❌ Latest snapshot: HTTP {response.status_code}")
            
        results["total"] += 1
    except Exception as e:
        print(f"❌ FAILED - Exception: {e}")
        results["details"].append(f"❌ Latest snapshot: Exception: {e}")
        results["total"] += 1
    
    # Test 4: GET count 
    print(f"\n📊 Test 4: GET count?symbol=BTC")
    try:
        url = f"{base_url}/api/fractal/v2.1/admin/snapshot/count?symbol=BTC"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            active = data.get('active', 0)
            shadow = data.get('shadow', 0)
            total = data.get('total', 0)
            
            if active > 0 and shadow > 0:
                print(f"✅ PASSED - Active: {active}, Shadow: {shadow}, Total: {total}")
                results["passed"] += 1
                results["details"].append(f"✅ Snapshot counts: active={active}, shadow={shadow}")
            else:
                print(f"❌ FAILED - Expected active > 0 and shadow > 0")
                print(f"   Got: active={active}, shadow={shadow}")
                results["details"].append(f"❌ Snapshot counts: active={active}, shadow={shadow}")
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            results["details"].append(f"❌ Snapshot counts: HTTP {response.status_code}")
            
        results["total"] += 1
    except Exception as e:
        print(f"❌ FAILED - Exception: {e}")
        results["details"].append(f"❌ Snapshot counts: Exception: {e}")
        results["total"] += 1
    
    # Print final summary
    print("\n" + "=" * 60)
    print("📋 REQUIREMENTS TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {results['passed']}/{results['total']}")
    print(f"Success Rate: {(results['passed']/results['total'])*100:.1f}%")
    
    print(f"\nDetailed Results:")
    for detail in results['details']:
        print(f"  {detail}")
    
    print("\n" + "=" * 60)
    
    # Return success if all tests passed
    return results['passed'] == results['total']

if __name__ == "__main__":
    success = test_requirements()
    sys.exit(0 if success else 1)