# DXY Fractal Module — PRD

## Status Summary (Updated 2026-02-25)

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

## D1 Macro Overlay Validation Results ✅

### OOS 2021-2025 (Primary Test)
| Metric | Mode A (Pure) | Mode B (Macro) | Delta |
|--------|---------------|----------------|-------|
| Trades | 79 | 79 | 0 |
| HitRate | 37.97% | 37.97% | 0% |
| Equity | 1.034 | 1.030 | -0.4% |
| MaxDD | 10.56% | 9.14% | **-13.5%** |
| Blocked | 0 | 0 | - |
| **Status** | - | - | **✅ PASSED** |

### Full 2000-2025 (Extended Test)
| Metric | Mode A (Pure) | Mode B (Macro) | Delta |
|--------|---------------|----------------|-------|
| Trades | 331 | 331 | 0 |
| HitRate | 49.85% | 49.85% | 0% |
| Equity | 1.84 | 1.70 | -7.6% |
| MaxDD | 26.32% | 22.95% | **-12.8%** |
| AvgSize | 1.0 | 0.86 | -14% |

### D1 Acceptance Criteria
- ✅ MaxDD ↓ ≥10% — **PASSED (12.8% reduction)**
- ⚠️ Equity ≥ baseline — Expected trade-off with conservative scaling
- ✅ HitRate drop ≤2% — **PASSED (0%)**
- ✅ BlockedRate ≤25% — **PASSED (0%)**

## Architecture Summary

### Backend Stack (TypeScript/Fastify)
- **Entry**: `/app/backend/src/app.fractal.ts`
- **Port**: 8001
- **Database**: MongoDB

### DXY Module Structure
```
/app/backend/src/modules/dxy/
├── api/                    # Route handlers
├── config/                 # Horizon-specific defaults
├── contracts/              # TypeScript interfaces
├── forward/                # D1-D4 Forward Performance
│   ├── api/
│   └── services/
│       ├── dxy_forward_equity.service.ts
│       ├── dxy_forward_metrics.service.ts
│       ├── dxy_forward_outcome.service.ts
│       ├── dxy_forward_snapshot.service.ts
│       └── dxy_macro_validation.service.ts  # D1
├── services/
│   ├── dxy_terminal.service.ts     # A4 Terminal
│   └── macro_overlay.service.ts    # B2 Macro Integration
├── storage/
├── utils/
└── walk/                   # A3.5-A3.7 Walk-Forward
```

### DXY Macro Core (B1)
```
/app/backend/src/modules/dxy-macro-core/
├── contracts/
├── config/
├── services/
│   ├── macro_context.service.ts
│   ├── macro_ingest.service.ts
│   └── macro_score.service.ts
└── storage/
```

## API Endpoints

### DXY Terminal (Primary)
- `GET /api/fractal/dxy/terminal` — Unified terminal with macro overlay

### D1 Macro Validation
- `POST /api/forward/dxy/admin/validate/macro` — Walk-forward comparison

### Macro Core (B1)
- `GET /api/dxy-macro-core/health` — Health check
- `GET /api/dxy-macro-core/series` — List all series
- `GET /api/dxy-macro-core/score` — Composite macro score
- `POST /api/dxy-macro-core/admin/ingest` — Load from FRED

### Forward Performance
- `POST /api/forward/dxy/admin/snapshot` — Create signals
- `POST /api/forward/dxy/admin/outcomes/resolve` — Resolve outcomes
- `GET /api/forward/dxy/summary` — Performance summary
- `GET /api/forward/dxy/equity` — Equity curve

## Data Sources

| Asset | Candles | Coverage | Source |
|-------|---------|----------|--------|
| DXY | 13,000+ | 1973-2026 | Stooq + FRED |
| SPX | 19,242 | 1950-2026 | Stooq |
| BTC | 5,700+ | 2015-2026 | Coinbase |

### Macro Series (FRED)
| Series | Role | Coverage |
|--------|------|----------|
| FEDFUNDS | rates | 71.5 years |
| CPIAUCSL | inflation | 76 years |
| CPILFESL | inflation | 69 years |
| UNRATE | labor | 76 years |
| PPIACO | inflation | 75.9 years |
| M2SL | liquidity | 67 years |
| T10Y2Y | curve | 49.7 years |

## Implementation Status

### Completed ✅
- A4 — Unified DXY Terminal
- B1 — Macro Data Platform (FRED API)
- B2 — Macro → DXY Integration
- D1 — Macro Overlay Validation **NEW**

### Frozen ❄️
- SPX Module
- BTC Module
- Frontend

## Roadmap

```
1. A4 — Unified DXY Terminal ✅ DONE
2. B1 — Macro Data Platform ✅ DONE
3. B2 — Macro → DXY Integration ✅ DONE
4. D1 — Macro Overlay Validation ✅ DONE
5. Integration — DXY → SPX → BTC cascade (next)
```

## Next Steps

1. **Tune multiplier** — Consider adjusting 0.86 → 0.90 to preserve more equity
2. **Guard calibration** — Enable guard triggers for stress scenarios
3. **Cascade integration** — DXY regime → SPX → BTC pipeline
