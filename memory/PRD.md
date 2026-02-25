# DXY Fractal Module — PRD

## Status Summary (Updated 2026-02-25)

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

## B6 2-Stage Guard — VALIDATED ✅

### Guard Hierarchy
1. **BLOCK** (peak panic): `credit > 0.50 AND VIX > 32`
   - Trading Disabled, Size = 0%, Confidence = 50%
2. **CRISIS** (systemic stress): `credit > 0.25 AND VIX > 18`
   - Trading Allowed, Size = 40%, Confidence = 65%
3. **WARN** (soft tightening): `credit > 0.30 AND macroScore > 0.15`
   - Trading Allowed, Size = 60%, Confidence = 75%
4. **NONE** — normal operation

### Episode Validation Results (2026-02-25)

| Episode | Period | CRISIS+BLOCK | Target | Status |
|---------|--------|--------------|--------|--------|
| GFC | 2008-2009 | **80%** | ≥60% | ✅ |
| COVID | Feb-Jun 2020 | **82%** | ≥80% | ✅ |
| Tightening | 2022-2023 | 21% (CRISIS only) | BLOCK ≤10% | ✅ |
| Low Vol | 2017 | 0% (NONE=100%) | NONE ≥80% | ✅ |

### Stability Metrics (2000-2025)
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Guard flips/year | **3.65** | < 4 | ✅ |
| Median duration | **21 days** | > 30 | ⚠️ |
| NONE % | 76.9% | - | - |
| CRISIS % | 18.1% | - | - |
| BLOCK % | 5.0% | - | - |

## B5 Historical Validation Complete ✅

### B5.1 Stability Metrics (2000-2025)
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Regime flips/year | **1.04** | < 12 | ✅ |
| Median duration (days) | **329** | > 20 | ✅ |
| Score std | **0.167** | 0.03-0.25 | ✅ |
| Score range | [-0.41, +0.57] | - | - |

### Driver Dominance
| Driver | Share | Avg Contribution |
|--------|-------|------------------|
| HOUSING | 43.6% | 0.40 |
| CREDIT | 32.9% | 0.34 |
| ACTIVITY | 13.0% | 0.29 |
| FED | 10.6% | 0.18 |

### B5.2 Episode Validation
| Episode | Period | Risk-Off | Credit | Fed | Status |
|---------|--------|----------|--------|-----|--------|
| GFC | 2008-2009 | **68%** | +0.58 | -0.35 | ✅ |
| COVID | Feb-Jun 2020 | **100%** | +0.53 | -0.56 | ✅ |
| Tightening | 2022-2023 | 0% | +0.13 | **+0.60** | ✅ |
| Low Vol | 2017 | 0% | **-0.56** | +0.13 | ✅ |

## B4 Extended Drivers

### Macro Score Weights
```
Core7 = 55% (Fed, CPI, UNRATE, M2, T10Y2Y, PPI)
Housing = 15% (Mortgage, Starts, Permits, Case-Shiller)
Activity = 15% (MANEMP, INDPRO, TCU)
Credit = 15% (BAA10Y, TEDRATE, VIX)
```

## API Endpoints

### B6 Crisis Guard
- `GET /api/dxy-macro-core/validate/episodes` — Episode validation with guard stats
- `GET /api/dxy-macro-core/validate/stability` — Stability report with guard metrics

### B5 Validation
- `GET /api/dxy-macro-core/validate/stability` — Stability report
- `GET /api/dxy-macro-core/validate/episodes` — Episode validation

### B4 Extended Drivers
- `GET /api/dxy-macro-core/housing`
- `GET /api/dxy-macro-core/activity`
- `GET /api/dxy-macro-core/credit`

### Core
- `GET /api/dxy-macro-core/score`
- `GET /api/research/dxy/terminal`
- `GET /api/fractal/dxy/terminal`

## Implementation Status

### Completed ✅
- A4 — Unified DXY Terminal
- B1 — Macro Data Platform
- B2 — Macro → DXY Integration
- D1 — Macro Overlay Validation
- B3 — DXY Research Terminal
- B4.1 — Housing & Real Estate
- B4.2 — Economic Activity
- B4.3 — Credit & Financial Stress
- **B5.1 — Stability Validation**
- **B5.2 — Episode Validation**
- **B6 — 2-Stage Crisis Guard** ✅ NEW

### Frozen ❄️
- SPX Module
- BTC Module
- Frontend

## Next Steps
1. ~~**Crisis Guard** — Auto-trigger при VIX > 35 + Credit spike~~ **DONE**
2. **Hysteresis** — Reduce guard duration flaps (median 21d → 30d target)
3. **B4.4** — Energy & Commodity (optional)
4. **Cascade** — DXY → SPX → BTC

## Tech Stack
- Backend: TypeScript + Fastify (port 8001)
- Database: MongoDB
- Data Source: FRED API
- Module: `dxy-macro-core`
