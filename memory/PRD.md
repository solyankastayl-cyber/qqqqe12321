# DXY Fractal Module — PRD

## Status Summary

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

## Key Finding: 90d is Regime-Sensitive

The 90d horizon shows classic overfitting pattern:
- Excellent performance on Train/Val (2000-2020)
- Complete breakdown on OOS (2021-2025)

**Root cause:** Post-COVID 2021-2025 is a fundamentally different regime for DXY:
- Fed policy shift (QE → QT)
- Inflation shock
- Strong USD cycle

The model learned patterns from 2000-2020 that don't apply to 2021-2025.

## Architectural Decision

### 30d → Tactical Engine (PRODUCTION)
```json
{
  "threshold": 0.01,
  "weightMode": "W2",
  "windowLen": 180,
  "topK": 10
}
```
**Use for:** Directional trading signals

### 90d → Regime Engine (FILTER ONLY)
```json
{
  "threshold": 0.03,
  "weightMode": "W2",
  "windowLen": 600,
  "topK": 10
}
```
**Use for:**
- Bias indicator (not directional alpha)
- Macro alignment check
- NOT standalone trading

## Implementation Status

### A3.5 Walk-Forward Validation ✅
- Collections: `dxy_walk_signals`, `dxy_walk_outcomes`, `dxy_walk_metrics`
- API: `/api/fractal/dxy/walk/*`

### A3.6 Calibration Grid (30d) ✅
- Weight modes: W0/W1/W2/W3
- Best config found and applied

### A3.7 Calibration Grid (90d) ✅
- Grid-90d endpoint implemented
- Quality Gate + Winsorization added
- Finding: OOS 2021-2025 structurally broken

### A3.7.v2 Controlled Tightening ✅
- Train/Val/OOS split validation
- Quality Gate mechanism
- Replay Winsorization
- Confirmed: 90d is regime-sensitive, not calibration issue

### A3.8 Horizon-Specific Defaults ✅ (2026-02-25)
- **Config file:** `/backend/src/modules/dxy/config/dxy.defaults.ts`
- **Modes:** tactical (7d/14d/30d) vs regime (90d/180d/365d)
- **API fields added:**
  - `meta.mode`: "tactical" | "regime"
  - `meta.tradingEnabled`: boolean
  - `meta.configUsed`: full config object
  - `meta.warnings[]`: string array
  - `data.decision.regimeBias`: "USD_STRENGTHENING" | "USD_WEAKENING"

### A4 Unified DXY Terminal ✅ (2026-02-25)
- **PRIMARY Endpoint:** `GET /api/fractal/dxy/terminal`
- **Returns:** core + synthetic + replay + hybrid + meta in single request
- **Query params:** focus (default: 30d), rank (1..10), windowLen, topK
- **Behavior:**
  - 30d tactical: tradingEnabled=true, action=LONG/SHORT
  - 90d regime: tradingEnabled=false, action=HOLD, bias available
  - rank switches replay.matchId
  - bands: p10 <= p50 <= p90 (monotonic)
  - hybrid.replayWeight <= 0.5 (clamped)

### B1 Macro Data Platform ✅ (2026-02-25)
- **Module:** `/backend/src/modules/dxy-macro-core/`
- **Data source:** FRED API (7 core series)
- **Series loaded:**
  | Series | Role | Coverage |
  |--------|------|----------|
  | FEDFUNDS | rates | 71.5 years |
  | CPIAUCSL | inflation | 76 years |
  | CPILFESL | inflation | 69 years |
  | UNRATE | labor | 76 years |
  | PPIACO | inflation | 75.9 years |
  | M2SL | liquidity | 67 years |
  | T10Y2Y | curve | 49.7 years |
- **API endpoints:**
  - `GET /api/dxy-macro-core/health` — health + FRED status
  - `GET /api/dxy-macro-core/series` — list all series
  - `GET /api/dxy-macro-core/context?seriesId=X` — context per series
  - `GET /api/dxy-macro-core/score` — composite macro score
  - `GET /api/dxy-macro-core/history?seriesId=X` — historical data
  - `POST /api/dxy-macro-core/admin/ingest` — ingest from FRED

### B2 Macro → DXY Integration ✅ (2026-02-25)
- **Files:**
  - `/backend/src/modules/dxy/services/macro_overlay.service.ts`
  - Updated `dxy_terminal.service.ts`
- **Terminal `macro` section added:**
  - `score01`, `scoreSigned`, `confidence`
  - `regime`: { label, riskMode, agreementWithSignal, rates, inflation, curve, labor, liquidity }
  - `overlay`: { confidenceMultiplier, thresholdShift, tradingGuard }
- **Regime Classification:**
  - FEDFUNDS: TIGHTENING / EASING / PAUSE
  - Core CPI: REHEATING / DISINFLATION / STABLE
  - T10Y2Y: INVERTED / STEEP / NORMAL
  - UNRATE: TIGHT_LABOR / LABOR_STRESS / NORMAL
  - M2: LIQUIDITY_EXPANSION / LIQUIDITY_CONTRACTION / NEUTRAL
- **Risk Mode:** RISK_ON / RISK_OFF / NEUTRAL
- **Agreement:** ALIGNED / NEUTRAL / CONFLICT
- **Guard:** BLOCK if (INVERTED + TIGHTENING + CONTRACTION + confidence > 0.6)
- **Confidence Multiplier:** ALIGNED=1.10, NEUTRAL=1.00, CONFLICT=0.80
- **Key invariant:** Macro does NOT change direction (LONG/SHORT), does NOT modify synthetic/replay/hybrid paths
- **Debug endpoint:** `GET /api/fractal/dxy/macro/debug`

## Roadmap (FIXED)

```
1. A4 — Unified DXY Terminal ✅ DONE
2. B1 — Macro Data Platform ✅ DONE
3. B2 — Macro → DXY Integration ✅ DONE
4. Integration — DXY → SPX → BTC cascade (next)
```

## API Endpoints

### A4 Terminal (PRIMARY)
- `GET /api/fractal/dxy/terminal` — unified API (core+synthetic+replay+hybrid+meta)

### Fractal Core (Secondary)
- `GET /api/fractal/dxy` — legacy main endpoint
- `GET /api/fractal/dxy/synthetic` — Synthetic trajectory
- `GET /api/fractal/dxy/hybrid` — Hybrid (model + replay)
- `GET /api/fractal/dxy/horizons` — Available horizons
- `GET /api/fractal/dxy/replay` — Replay packs
- `GET /api/fractal/dxy/audit` — Audit diagnostics

### Walk-Forward
- `POST /api/fractal/dxy/walk/run`
- `POST /api/fractal/dxy/walk/resolve`
- `GET /api/fractal/dxy/walk/summary`
- `GET /api/fractal/dxy/walk/status`

### Calibration
- `POST /api/fractal/dxy/calibrate/grid-90d`
- `POST /api/fractal/dxy/calibrate/grid-90d-v2`
- `GET /api/fractal/dxy/calibrate/latest`

## Data Status

| Asset | Candles | Coverage | Source |
|-------|---------|----------|--------|
| DXY | 18,413 | 1952-2026 | Stooq/FRED |
| SPX | 19,242 | 1950-2026 | Stooq |
| BTC | 5,700+ | 2015-2026 | Coinbase |

## Next Steps

1. **B-Track** — Macro platform integration (Fed rates, CPI, UNRATE)
2. **DXY 90d regime** — Use as bias filter for SPX/BTC
3. **Integration** — DXY → SPX → BTC cascade

