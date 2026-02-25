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

## B3 Research Terminal ✅ (NEW)

Unified research endpoint aggregating all DXY intelligence:

### Endpoint
`GET /api/research/dxy/terminal?focus=30d&rank=1`

### Response Structure
```json
{
  "terminal": { /* A4 Terminal Pack */ },
  "macroCore": { /* B1 Macro Score + Contexts */ },
  "overlay": { /* B2 Macro Overlay */ },
  "research": {
    "headline": "DXY: SHORT ↓ (86/100). Macro: NEUTRAL.",
    "takeaways": ["..."],
    "drivers": [{"key": "FEDFUNDS", "contribution": -0.088, "note": "..."}],
    "risks": ["⚠️ Signal conflicts with macro environment"],
    "dataFreshness": [{"key": "FEDFUNDS", "lagDays": 55}],
    "limits": ["Macro does NOT change direction"]
  }
}
```

### Debug Endpoint
`GET /api/research/dxy/terminal/debug`

## Architecture Summary

### Backend Stack (TypeScript/Fastify)
- **Entry**: `/app/backend/src/app.fractal.ts`
- **Port**: 8001
- **Database**: MongoDB

### DXY Module Structure
```
/app/backend/src/modules/dxy/
├── api/
│   ├── dxy.research_terminal.routes.ts  # B3 NEW
│   └── dxy.terminal.routes.ts           # A4
├── contracts/
│   ├── dxy_research_terminal.contract.ts  # B3 NEW
│   └── dxy_terminal.contract.ts           # A4
├── forward/
│   └── services/
│       └── dxy_macro_validation.service.ts  # D1
├── services/
│   ├── dxy_research_terminal.service.ts  # B3 NEW
│   ├── dxy_terminal.service.ts           # A4
│   └── macro_overlay.service.ts          # B2
└── index.ts
```

## API Endpoints

### Research Terminal (B3) — NEW
- `GET /api/research/dxy/terminal` — Full research pack
- `GET /api/research/dxy/terminal/debug` — Source info

### DXY Terminal (A4)
- `GET /api/fractal/dxy/terminal` — Unified terminal with macro

### D1 Macro Validation
- `POST /api/forward/dxy/admin/validate/macro` — Walk-forward comparison

### Macro Core (B1)
- `GET /api/dxy-macro-core/health` — Health check
- `GET /api/dxy-macro-core/series` — List all series
- `GET /api/dxy-macro-core/score` — Composite macro score
- `POST /api/dxy-macro-core/admin/ingest` — Load from FRED

## Data Sources

| Asset | Candles | Coverage | Source |
|-------|---------|----------|--------|
| DXY | 18,413 | 1952-2026 | Stooq + FRED |
| SPX | 19,242 | 1950-2026 | Stooq |
| BTC | 5,700+ | 2015-2026 | Coinbase |

### Macro Series (FRED)
| Series | Role | Coverage | Status |
|--------|------|----------|--------|
| FEDFUNDS | rates | 71.5 years | ✅ |
| CPIAUCSL | inflation | 76 years | ✅ |
| CPILFESL | inflation | 69 years | ✅ |
| UNRATE | labor | 76 years | ✅ |
| PPIACO | inflation | 75.9 years | ✅ |
| M2SL | liquidity | 67 years | ✅ |
| T10Y2Y | curve | 49.7 years | ✅ |

## Implementation Status

### Completed ✅
- A4 — Unified DXY Terminal
- B1 — Macro Data Platform (FRED API)
- B2 — Macro → DXY Integration
- D1 — Macro Overlay Validation
- **B3 — DXY Research Terminal (NEW)**

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
5. B3 — DXY Research Terminal ✅ DONE
6. B4 — Extended Drivers (housing/PMI/credit/oil) (next)
7. Integration — DXY → SPX → BTC cascade (later)
```

## Next Steps

1. **B4** — Extend macro drivers (housing, PMI, credit spreads, oil/energy)
2. **B5** — Historical research stability validation
3. **Cascade** — DXY regime → SPX → BTC pipeline (after DXY complete)
