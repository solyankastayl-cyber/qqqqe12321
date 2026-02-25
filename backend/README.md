# Fractal ML Module - Isolated Development Environment

Минимальная, изолированная конфигурация для разработки Fractal + ML + MongoDB.

## Что запущено

- ✅ MongoDB (localhost:27017)
- ✅ Node.js Backend (Fractal ONLY mode, port 8003)
- ✅ Python Gateway (proxy на port 8001)
- ✅ Python ML Scripts

## Что НЕ запущено (отключено)

- ❌ Exchange providers
- ❌ WebSocket
- ❌ Market Context Layer
- ❌ External APIs
- ❌ Neural
- ❌ Sentiment
- ❌ On-chain
- ❌ Telegram
- ❌ UI

## Доступные Endpoints

### Health & Status
```bash
GET  /api/health                         # Gateway health
GET  /api/fractal/health                 # Fractal module health
```

### Core Signal
```bash
GET  /api/fractal/signal                 # Ensemble signal (Rule + ML + Regime Gate)
GET  /api/fractal/match                  # Pattern match (GET)
POST /api/fractal/match                  # Pattern match (POST)
GET  /api/fractal/explain                # Human-readable explanation
GET  /api/fractal/explain/detailed       # Detailed explainability (Block 13)
GET  /api/fractal/overlay                # Overlay visualization data
```

### Admin - Bootstrap & Data
```bash
POST /api/fractal/admin/bootstrap        # Trigger bootstrap
POST /api/fractal/admin/force-update     # Force incremental update
POST /api/fractal/admin/scan-continuity  # Scan data continuity
POST /api/fractal/admin/auto-fix-gaps    # Auto-fix gaps
POST /api/fractal/admin/invalidate-cache # Invalidate cache
POST /api/fractal/admin/rebuild-index    # Rebuild index
```

### Admin - ML Dataset
```bash
GET  /api/fractal/admin/dataset          # Export ML dataset
GET  /api/fractal/admin/dataset-info     # Dataset statistics
GET  /api/fractal/admin/dataset-stats    # Window store stats
POST /api/fractal/admin/update-labels    # Update labels
POST /api/fractal/admin/backfill-dataset # Backfill ML dataset
```

### Admin - ML Model
```bash
GET  /api/fractal/admin/ml-model         # Get model info
POST /api/fractal/admin/ml-model         # Save model weights
```

### Admin - Backtest & Calibration
```bash
POST /api/fractal/admin/backtest         # Run shadow backtest
GET  /api/fractal/admin/calibration      # Confidence calibration report
POST /api/fractal/admin/auto-calibrate   # Auto-calibrate confidence
```

### Admin - AutoLearn (Block 29)
```bash
POST /api/fractal/admin/autolearn/run      # Full autolearn cycle
POST /api/fractal/admin/autolearn/monitor  # Check degradation
GET  /api/fractal/admin/autolearn/state    # Get autolearn state
GET  /api/fractal/admin/autolearn/registry # Model registry
POST /api/fractal/admin/autolearn/rollback # Rollback to last version
POST /api/fractal/admin/autolearn/retrain  # Manual retrain
```

### Admin - Optimization
```bash
POST /api/fractal/admin/optimize-weights   # Optimize ensemble weights
GET  /api/fractal/admin/ensemble           # Get ensemble settings
POST /api/fractal/admin/auto-adjust        # Auto-adjust parameters
GET  /api/fractal/admin/settings           # Get auto-tune settings
GET  /api/fractal/admin/performance-metrics # Get performance metrics
POST /api/fractal/admin/ingest-performance  # Ingest performance records
```

## Запуск

### Вариант 1: Через supervisor (текущий)
Backend уже запущен через supervisor. Python gateway проксирует запросы к Node.js.

### Вариант 2: Прямой запуск Node.js
```bash
cd /app/backend
npm run fractal
```

### Вариант 3: Изолированный entrypoint
```bash
cd /app/backend
npx tsx src/app.fractal.ts
```

## Python ML Scripts

### Training
```bash
cd /app/ml
python3 fractal_train_baseline.py    # Train LogisticRegression model
python3 fractal_train_logreg.py      # Alternative training script
```

### Dependencies
```bash
pip install scikit-learn numpy requests
```

## Environment Variables (.env)

```env
NODE_ENV=development
PORT=8001
MONGODB_URI=mongodb://localhost:27017/fractal_dev

FRACTAL_ENABLED=true
FRACTAL_ONLY=1
MINIMAL_BOOT=1

WS_ENABLED=false
EXCHANGE_ENABLED=false
ONCHAIN_ENABLED=false
SENTIMENT_ENABLED=false
```

## Проверка работоспособности

```bash
# Health check
curl http://localhost:8001/api/health

# Fractal health
curl http://localhost:8001/api/fractal/health

# Get signal
curl http://localhost:8001/api/fractal/signal

# Run backtest
curl -X POST http://localhost:8001/api/fractal/admin/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC", "windowLen": 60, "horizonDays": 30}'

# Run autolearn
curl -X POST http://localhost:8001/api/fractal/admin/autolearn/run \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC"}'
```

## Данные

- CSV данные: `/app/backend/data/fractal/bootstrap/BTCUSD_daily.csv`
- MongoDB: `fractal_dev` database
- Collections: 
  - `fractal_canonical` - ценовые свечи
  - `fractal_windows` - ML dataset
  - `fractal_settings` - настройки
  - `fractal_models` - ML модели
