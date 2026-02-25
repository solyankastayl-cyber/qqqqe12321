# DXY Fractal Module — PRD

## Status Summary (Updated 2026-02-25)

| Horizon | Train 2000-2016 | Val 2017-2020 | OOS 2021-2025 | Status |
|---------|-----------------|---------------|---------------|--------|
| **30d** | - | - | **56.1% hit, equity 1.22** | **✅ PRODUCTION** |
| **90d** | 57% hit, equity 1.49 | 57% hit, equity 1.39 | **38% hit, equity 0.56** | **❌ REGIME ONLY** |

## B4.1 Housing & Real Estate ✅ (NEW)

### Housing Series (FRED)
| Series | Name | Points | Coverage | Regime Logic |
|--------|------|--------|----------|--------------|
| MORTGAGE30US | 30Y Mortgage Rate | 2,865 | 1971-2026 | TIGHTENING/EASING |
| HOUST | Housing Starts | 804 | 1959-2026 | EXPANSION/CONTRACTION |
| PERMIT | Building Permits | 792 | 1960-2026 | EXPANSION/CONTRACTION |
| CSUSHPISA | Case-Shiller Index | 468 | 1987-2026 | OVERHEATING/COOLING |

### Housing Pressure Logic
```
mortgagePressure = clamp(z5y / 3, -1, 1)    # High → USD supportive
startsPressure = -clamp(z5y / 3, -1, 1)     # Strong → USD pressure
permitsPressure = -clamp(z5y / 3, -1, 1)    # Strong → USD pressure
homePricePressure = -clamp(z5y / 3, -1, 1)  # Rising → USD pressure

housingScore = 0.40 × mortgage + 0.20 × starts + 0.20 × permits + 0.20 × homePrice
```

### Current Housing State
| Metric | Value |
|--------|-------|
| Mortgage (MORTGAGE30US) | 6.07% (NEUTRAL) |
| Starts (HOUST) | 1,404k (CONTRACTION) |
| Permits (PERMIT) | 1,448k (NEUTRAL) |
| Home Price (CSUSHPISA) | 332 (NEUTRAL) |
| **Composite Score** | **0.025 (NEUTRAL)** |
| **Confidence** | **0.72** |

### Integration
- Housing weight in macro score: **15%**
- Added to `/api/dxy-macro-core/score` as HOUSING component
- Added to `/api/research/dxy/terminal` drivers
- New endpoint: `/api/dxy-macro-core/housing`

## D1 Macro Overlay Validation Results ✅

### OOS 2021-2025 (Primary Test)
| Metric | Mode A (Pure) | Mode B (Macro) | Delta |
|--------|---------------|----------------|-------|
| Trades | 79 | 79 | 0 |
| HitRate | 37.97% | 37.97% | 0% |
| Equity | 1.034 | 1.030 | -0.4% |
| MaxDD | 10.56% | 9.14% | **-13.5%** |
| **Status** | - | - | **✅ PASSED** |

## Architecture Summary

### Backend Stack (TypeScript/Fastify)
- **Entry**: `/app/backend/src/app.fractal.ts`
- **Port**: 8001
- **Database**: MongoDB
- **Version**: B4.1

### Macro Core Structure (B1 + B4.1)
```
/app/backend/src/modules/dxy-macro-core/
├── api/
│   └── macro.routes.ts          # Updated for housing
├── data/
│   └── macro_sources.registry.ts  # +4 housing series
├── services/
│   ├── macro_score.service.ts    # Integrates housing
│   ├── macro_context.service.ts
│   └── housing_context.service.ts  # B4.1 NEW
└── storage/
```

## API Endpoints

### Housing (B4.1) — NEW
- `GET /api/dxy-macro-core/housing` — Housing context + composite

### Research Terminal (B3)
- `GET /api/research/dxy/terminal` — Full research pack with housing

### DXY Terminal (A4)
- `GET /api/fractal/dxy/terminal` — Terminal (paths unchanged)

### Macro Core (B1)
- `GET /api/dxy-macro-core/score` — Score with HOUSING component
- `GET /api/dxy-macro-core/series` — 11 series (7 core + 4 housing)

## Data Sources

### Macro Series (11 total)
| Series | Role | Coverage | Status |
|--------|------|----------|--------|
| FEDFUNDS | rates | 71.5 years | ✅ B1 |
| CPIAUCSL | inflation | 76 years | ✅ B1 |
| CPILFESL | inflation | 69 years | ✅ B1 |
| UNRATE | labor | 76 years | ✅ B1 |
| PPIACO | inflation | 75.9 years | ✅ B1 |
| M2SL | liquidity | 67 years | ✅ B1 |
| T10Y2Y | curve | 49.7 years | ✅ B1 |
| MORTGAGE30US | housing | 55 years | ✅ **B4.1** |
| HOUST | housing | 67 years | ✅ **B4.1** |
| PERMIT | housing | 66 years | ✅ **B4.1** |
| CSUSHPISA | housing | 39 years | ✅ **B4.1** |

## Implementation Status

### Completed ✅
- A4 — Unified DXY Terminal
- B1 — Macro Data Platform (FRED API)
- B2 — Macro → DXY Integration
- D1 — Macro Overlay Validation
- B3 — DXY Research Terminal
- **B4.1 — Housing & Real Estate (NEW)**

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
6. B4.1 — Housing & Real Estate ✅ DONE
7. B4.2 — PMI & Economic Activity (next)
8. B4.3 — Credit & Financial Stress
9. B4.4 — Energy & Commodity
10. B5 — Historical Research Stability
```

## Next Steps

1. **B4.2** — PMI drivers (ISM, Industrial Production)
2. **B4.3** — Credit spreads (BAA10Y, HY Spread, Financial Stress)
3. **B4.4** — Energy (WTI, Natural Gas)
4. **B5** — Historical validation of extended drivers
