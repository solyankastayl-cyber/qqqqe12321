# DXY Fractal Module — PRD

## Status Summary (Updated 2026-02-25)

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

---

## C-Track: AE Brain — IMPLEMENTED ✅

### Architecture
AE Brain is the intelligence layer aggregating all system state:

| Component | Description | Status |
|-----------|-------------|--------|
| **C1** | State Vector Aggregator | ✅ |
| **C2** | Regime Classifier | ✅ |
| **C3** | Causal Graph | ✅ |
| **C4** | Scenario Engine | ✅ |
| **C5** | Novelty Detection | ✅ |
| **C6** | Historical Backfill | ✅ NEW |

### C6 Historical Backfill — VALIDATED ✅ NEW

**Stats (2026-02-25):**
- **Total vectors**: 1358
- **Date range**: 2000-01-01 → 2025-12-31
- **Step**: 7 days (weekly)

**Distribution:**
| Metric | Value |
|--------|-------|
| macroSigned | [-0.271, +0.341], avg = -0.012 |
| NONE | 82% (1112) |
| CRISIS | 15% (197) |
| BLOCK | 4% (49) |

**Crisis Detection Validation:**
| Period | Regime | Guard | Nearest |
|--------|--------|-------|---------|
| GFC 2008-10-11 | RISK_OFF_STRESS | BLOCK | COVID 2020 |
| COVID 2020-03-14 | RISK_OFF_STRESS | BLOCK | GFC 2008 |
| 2017-07-01 | NEUTRAL_MIXED | NONE | 2003, 2016 |

---

### C1 State Vector
Normalized state from macro + guard + DXY terminal:
```json
{
  "macroSigned": [-1..1],
  "macroConfidence": [0..1],
  "guardLevel": [0..1],
  "dxySignalSigned": [-1..1],
  "dxyConfidence": [0..1],
  "regimeBias90d": [-1..1]
}
```

### C2 Regime Classifier
State machine with 6 regimes:
- `LIQUIDITY_EXPANSION` — Fed easing, risk-on
- `LIQUIDITY_CONTRACTION` — Fed tightening, credit rising
- `DOLLAR_DOMINANCE` — Strong USD, hawkish policy
- `DISINFLATION_PIVOT` — Falling inflation, potential pivot
- `RISK_OFF_STRESS` — Crisis mode (guard >= CRISIS)
- `NEUTRAL_MIXED` — No dominant signal

### C3 Causal Graph
Fixed rule graph with 10 links:
- Rates → USD (+)
- CreditStress → SPX (-)
- Liquidity → BTC (+)
- USD → BTC (-)

Strength = baseWeight × guardMultiplier × confidenceMultiplier

### C4 Scenario Engine
3 scenarios with softmax probabilities:
| Scenario | Trigger | Tilts |
|----------|---------|-------|
| BASE | Neutral state | DXY/SPX/BTC FLAT |
| BULL_RISK_ON | Low stress, dovish | DXY↓ SPX↑ BTC↑ |
| BEAR_STRESS | High stress | DXY↑ SPX↓ BTC↓ |

### C5 Novelty Detection
KNN cosine distance (K=20):
- `KNOWN` (< 0.12)
- `RARE` (0.12-0.18)
- `UNSEEN` (> 0.18)

### AE Brain API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ae/health` | Module health |
| GET | `/api/ae/state` | C1 state vector |
| GET | `/api/ae/regime` | C2 regime |
| GET | `/api/ae/causal` | C3 causal links |
| GET | `/api/ae/scenarios` | C4 scenarios |
| GET | `/api/ae/novelty` | C5 novelty |
| GET | `/api/ae/terminal` | Full pack |
| POST | `/api/ae/admin/snapshot` | Save state |
| POST | `/api/ae/admin/backfill` | C6 backfill |
| GET | `/api/ae/admin/backfill-stats` | C6 stats |

---

## B6 2-Stage Guard — VALIDATED ✅

### Guard Hierarchy
1. **BLOCK** (peak panic): `credit > 0.50 AND VIX > 32`
2. **CRISIS** (systemic stress): `credit > 0.25 AND VIX > 18`
3. **WARN** (soft tightening): `credit > 0.30 AND macroScore > 0.15`
4. **NONE** — normal operation

### Episode Validation Results (2026-02-25)
| Episode | Period | CRISIS+BLOCK | Target | Status |
|---------|--------|--------------|--------|--------|
| GFC | 2008-2009 | **80%** | ≥60% | ✅ |
| COVID | Feb-Jun 2020 | **82%** | ≥80% | ✅ |
| Tightening | 2022-2023 | 21% | BLOCK ≤10% | ✅ |
| Low Vol | 2017 | 0% | NONE ≥80% | ✅ |

### Stability Metrics (2000-2025)
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Guard flips/year | **3.65** | < 4 | ✅ |
| Median duration | **21 days** | > 30 | ⚠️ |

---

## Implementation Status

### Completed ✅
- A4 — Unified DXY Terminal
- B1 — Macro Data Platform
- B2 — Macro → DXY Integration
- B3 — DXY Research Terminal
- B4.1 — Housing & Real Estate
- B4.2 — Economic Activity
- B4.3 — Credit & Financial Stress
- B5.1 — Stability Validation
- B5.2 — Episode Validation
- **B6 — 2-Stage Crisis Guard** ✅
- **C1 — State Vector Aggregator** ✅
- **C2 — Regime Classifier** ✅
- **C3 — Causal Graph** ✅
- **C4 — Scenario Engine** ✅
- **C5 — Novelty Detection** ✅
- **C6 — Historical Backfill** ✅ NEW

### Frozen ❄️
- SPX Module
- BTC Module
- Frontend

---

## Next Steps

### Immediate (D-Track)
1. **C7** — Regime Clustering (k-means on state vectors) — Optional
2. **D1** — SPX Cascade Integration (DXY → SPX)
3. **D2** — BTC Cascade Integration (DXY → SPX → BTC)

### Backlog
- Hysteresis — Reduce guard flaps (median 21d → 30d)
- Regime Transition Matrix — probability of regime switches
- B4.4 — Energy & Commodity (optional)

---

## Tech Stack
- Backend: TypeScript + Fastify (port 8001)
- Database: MongoDB
- Data Source: FRED API
- Modules: `dxy-macro-core`, `ae-brain`
