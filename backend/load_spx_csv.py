"""
Load SPX data from local CSV file into MongoDB
"""
import os
import csv
from datetime import datetime
from pymongo import MongoClient

# Read MongoDB URL from environment or use default
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# CSV file path
CSV_PATH = '/app/data/spx_stooq.csv'

def pick_cohort(date_str):
    """Assign cohort based on date"""
    year = int(date_str.split('-')[0])
    if year < 1990:
        return 'V1950'
    elif year < 2008:
        return 'V1990'
    elif year < 2020:
        return 'V2008'
    elif year < 2024:
        return 'V2020'
    else:
        return 'LIVE'

def date_to_ts(date_str):
    """Convert YYYY-MM-DD to UTC timestamp in ms"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return int(dt.timestamp() * 1000)

def main():
    print(f"Connecting to MongoDB: {MONGO_URL}")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['spx_candles']
    
    # Check existing count
    existing = collection.count_documents({})
    print(f"Existing SPX candles in DB: {existing}")
    
    # Read CSV
    print(f"Reading CSV from: {CSV_PATH}")
    candles = []
    
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                date = row['Date']
                candle = {
                    'ts': date_to_ts(date),
                    'date': date,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'c': float(row['Close']),  # Alias for compatibility
                    'volume': int(float(row['Volume'])) if row.get('Volume') else None,
                    'symbol': 'SPX',
                    'source': 'STOOQ',
                    'cohort': pick_cohort(date),
                }
                candles.append(candle)
            except Exception as e:
                print(f"Error parsing row: {row}, error: {e}")
    
    print(f"Parsed {len(candles)} candles from CSV")
    
    if candles:
        # Sort by timestamp
        candles.sort(key=lambda x: x['ts'])
        
        # Assign idx for deterministic calibration
        for i, candle in enumerate(candles):
            candle['idx'] = i
        
        print(f"Date range: {candles[0]['date']} to {candles[-1]['date']}")
        
        # Bulk upsert
        from pymongo import UpdateOne
        ops = [
            UpdateOne(
                {'ts': c['ts']},
                {'$set': c},
                upsert=True
            )
            for c in candles
        ]
        
        print(f"Performing bulk upsert of {len(ops)} operations...")
        result = collection.bulk_write(ops, ordered=False)
        
        print(f"Inserted: {result.upserted_count}")
        print(f"Modified: {result.modified_count}")
        print(f"Matched: {result.matched_count}")
        
        # Create indexes
        print("Creating indexes...")
        collection.create_index([('ts', 1)], unique=True, name='uniq_ts')
        collection.create_index([('ts', -1)], name='ts_desc')
        collection.create_index([('cohort', 1), ('ts', 1)], name='cohort_ts')
        collection.create_index([('date', 1)], name='date_idx')
        collection.create_index([('idx', 1)], name='idx_asc')
        
        # Verify
        final_count = collection.count_documents({})
        print(f"Final SPX candle count: {final_count}")
        
        # Show sample
        sample = collection.find_one(sort=[('ts', -1)])
        print(f"Latest candle: {sample['date']} - close: {sample['close']}")
    
    client.close()
    print("Done!")

if __name__ == '__main__':
    main()
