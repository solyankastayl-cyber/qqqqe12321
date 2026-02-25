# DXY Fractal Module — PRD

## Status Summary (Updated 2026-02-25)

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

## B4 Extended Drivers Complete ✅

### B4.1 Housing & Real Estate
| Series | Name | Points | Regime |
|--------|------|--------|--------|
| MORTGAGE30US | 30Y Mortgage Rate | 2,865 | NEUTRAL |
| HOUST | Housing Starts | 804 | CONTRACTION |
| PERMIT | Building Permits | 792 | NEUTRAL |
| CSUSHPISA | Case-Shiller Index | 468 | NEUTRAL |
| **Composite** | | | **score=0.025, regime=NEUTRAL** |

### B4.2 Economic Activity
| Series | Name | Points | Regime |
|--------|------|--------|--------|
| MANEMP | Manufacturing Employment | 913 | NEUTRAL |
| INDPRO | Industrial Production | 913 | EXPANSION |
| TCU | Capacity Utilization | 709 | NEUTRAL |
| **Composite** | | | **score=0.002, regime=EXPANSION** |

### B4.3 Credit & Financial Stress
| Series | Name | Points | Regime |
|--------|------|--------|--------|
| BAA10Y | Moody's Baa Spread | 10,035 | NEUTRAL |
| TEDRATE | TED Spread | 8,853 | NEUTRAL |
| VIXCLS | VIX Volatility | 9,129 | NEUTRAL |
| **Composite** | | | **score=0.134, regime=NEUTRAL** |

### Macro Score Integration
```
Core7 = 55%
Housing = 15%
Activity = 15%
Credit = 15%
```

**Current Score**: -0.035 (slightly USD bearish, driven by Fed easing)

## D1 Macro Overlay Validation ✅

| Metric | Mode A (Pure) | Mode B (Macro) | Delta |
|--------|---------------|----------------|-------|
| Trades | 79 | 79 | 0 |
| HitRate | 37.97% | 37.97% | 0% |
| Equity | 1.034 | 1.030 | -0.4% |
| MaxDD | 10.56% | 9.14% | **-13.5%** |

## API Endpoints

### Extended Drivers (B4)
- `GET /api/dxy-macro-core/housing` — Housing context
- `GET /api/dxy-macro-core/activity` — Activity context
- `GET /api/dxy-macro-core/credit` — Credit context

### Core
- `GET /api/dxy-macro-core/score` — Full macro score
- `GET /api/research/dxy/terminal` — Research terminal
- `GET /api/fractal/dxy/terminal` — DXY terminal

## Macro Series Registry (17 total)

| Series | Role | Weight |
|--------|------|--------|
| FEDFUNDS | rates | 18% |
| CPILFESL | inflation | 14% |
| CPIAUCSL | inflation | 14% |
| UNRATE | labor | 10% |
| M2SL | liquidity | 10% |
| T10Y2Y | curve | 10% |
| PPIACO | inflation | 5% |
| HOUSING | composite | 15% |
| ACTIVITY | composite | 15% |
| CREDIT | composite | 15% |

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

### Frozen ❄️
- SPX Module
- BTC Module
- Frontend

## Next Steps
1. B5 — Historical Research Stability
2. B4.4 — Energy & Commodity (optional)
3. Cascade — DXY → SPX → BTC (after DXY complete)
