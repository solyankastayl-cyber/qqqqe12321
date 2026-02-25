/**
 * DXY TERMINAL SERVICE — A4 + B2
 * 
 * Unified terminal builder for DXY Fractal Engine.
 * Returns complete pack: core + synthetic + replay + hybrid + meta + macro
 * 
 * B2: Added macro overlay integration
 * 
 * ISOLATION: No imports from /modules/btc or /modules/spx
 */

import {
  DxyTerminalPack,
  DxyTerminalParams,
  TerminalCorePack,
  TerminalSyntheticPack,
  TerminalReplayPack,
  TerminalHybridPack,
  TerminalMeta,
  TerminalMatchInfo,
  TerminalPathPoint,
  TerminalMacroPack,
} from '../contracts/dxy_terminal.contract.js';
import {
  resolveDxyConfig,
  getDxyMode,
  isDxyTradingEnabled,
  getDxyWarnings,
  type DxyFocus,
} from '../config/dxy.defaults.js';
import { buildDxyFocusPack } from './dxy-focus-pack.service.js';
import { buildDxySyntheticPack } from './dxy-synthetic.service.js';
import { buildDxyReplayPack, getDxyTopMatches } from './dxy-replay.service.js';
import { getDxyLatestPrice, getAllDxyCandles } from './dxy-chart.service.js';
import {
  computeReplayWeight,
  blendPathsPointByPoint,
  pctToAbsolutePath,
  computeHybridBreakdown,
  validatePath,
  hasNaN,
} from '../utils/hybrid_blend.js';
import { horizonToDays, type DxyHorizon } from '../contracts/dxy.types.js';

// B2: Macro imports
import { buildMacroOverlay } from './macro_overlay.service.js';
import { computeMacroScore } from '../../dxy-macro-core/services/macro_score.service.js';
import { buildMacroContext } from '../../dxy-macro-core/services/macro_context.service.js';

// ═══════════════════════════════════════════════════════════════
// HELPER: Generate match ID
// ═══════════════════════════════════════════════════════════════

function generateMatchId(startDate: string, endDate: string): string {
  return `${startDate}_${endDate}`;
}

// ═══════════════════════════════════════════════════════════════
// HELPER: Extract decade from date
// ═══════════════════════════════════════════════════════════════

function getDecade(dateStr: string): string {
  const year = parseInt(dateStr.substring(0, 4));
  const decade = Math.floor(year / 10) * 10;
  return `${decade}s`;
}

// ═══════════════════════════════════════════════════════════════
// BUILD DXY TERMINAL PACK
// ═══════════════════════════════════════════════════════════════

export async function buildDxyTerminalPack(
  params: DxyTerminalParams
): Promise<DxyTerminalPack> {
  const start = Date.now();
  const focus = (params.focus || '30d') as DxyFocus;
  const rank = params.rank ?? 1;
  
  // Resolve config from A3.8 defaults
  const config = resolveDxyConfig(focus);
  const windowLen = params.windowLen ?? config.windowLen;
  const topK = params.topK ?? config.topK;
  const focusDays = horizonToDays(focus as DxyHorizon);
  
  // Get mode/trading info
  const mode = getDxyMode(focus);
  const tradingEnabled = isDxyTradingEnabled(focus);
  const warnings: string[] = [...getDxyWarnings(focus)];
  
  // ═══════════════════════════════════════════════════════════════
  // 1) CORE: Get current price, matches, diagnostics
  // ═══════════════════════════════════════════════════════════════
  
  const latestPrice = await getDxyLatestPrice();
  const currentPrice = latestPrice?.price ?? 100;
  const currentDate = latestPrice?.date ?? new Date().toISOString().split('T')[0];
  
  // Get top matches
  const matchesResult = await getDxyTopMatches(focus, topK, windowLen);
  const matches: TerminalMatchInfo[] = matchesResult.matches.map(m => ({
    rank: m.rank,
    matchId: generateMatchId(m.date, m.date), // will be updated with proper dates
    startDate: m.date,
    endDate: m.date,
    similarity: Math.round(m.similarity * 10000) / 10000,
    decade: m.decade,
  }));
  
  // Get focus pack for diagnostics and decision
  const focusPack = await buildDxyFocusPack(focus);
  
  // Build diagnostics
  const diagnostics = {
    similarity: focusPack?.diagnostics?.similarity ?? 0,
    entropy: focusPack?.diagnostics?.entropy ?? 1,
    coverageYears: focusPack?.diagnostics?.coverageYears ?? 0,
    matchCount: focusPack?.diagnostics?.matchCount ?? 0,
    windowLen,
  };
  
  // ═══════════════════════════════════════════════════════════════
  // 2) SYNTHETIC: Get path + bands + forecast
  // ═══════════════════════════════════════════════════════════════
  
  const syntheticPack = await buildDxySyntheticPack(focus, topK, rank, windowLen);
  
  // Extract pct arrays for blending
  const synthPct = syntheticPack.pct.p50;
  
  // Helper: Convert PathPoint (price) to TerminalPathPoint (value)
  const toTerminalPath = (points: Array<{ t: number; date?: string; price: number; pctFromStart?: number }>): TerminalPathPoint[] => {
    return points.map(p => ({
      t: p.t,
      date: p.date,
      value: p.price,
      pct: p.pctFromStart,
    }));
  };
  
  // Build synthetic for terminal
  const synthetic: TerminalSyntheticPack = {
    path: toTerminalPath(syntheticPack.synthetic),
    bands: {
      p10: toTerminalPath(syntheticPack.bands.p10),
      p50: toTerminalPath(syntheticPack.bands.p50),
      p90: toTerminalPath(syntheticPack.bands.p90),
    },
    forecast: {
      bear: syntheticPack.pct.p10[syntheticPack.pct.p10.length - 1] ?? 0,
      base: syntheticPack.pct.p50[syntheticPack.pct.p50.length - 1] ?? 0,
      bull: syntheticPack.pct.p90[syntheticPack.pct.p90.length - 1] ?? 0,
    },
  };
  
  // ═══════════════════════════════════════════════════════════════
  // 3) REPLAY: Get window + continuation for selected rank
  // ═══════════════════════════════════════════════════════════════
  
  let replay: TerminalReplayPack;
  let replayPct: number[] = [];
  
  try {
    const replayPack = await buildDxyReplayPack(focus, rank, windowLen);
    
    replay = {
      matchId: generateMatchId(replayPack.match.startDate, replayPack.match.endDate),
      rank: replayPack.match.rank,
      similarity: replayPack.match.similarity,
      window: replayPack.window.map(p => ({
        t: p.t,
        date: p.date,
        value: p.price,
        pct: p.pctFromStart,
      })),
      continuation: replayPack.continuation.map(p => ({
        t: p.t,
        date: p.date,
        value: p.price,
        pct: p.pctFromStart,
      })),
    };
    
    // Get replay pct for hybrid blending (aftermath normalized)
    replayPct = replayPack.aftermathNormalized;
    
    // Update matches with proper dates from replay
    if (matches.length > 0 && replayPack.match) {
      const matchIdx = matches.findIndex(m => m.rank === rank);
      if (matchIdx >= 0) {
        matches[matchIdx].startDate = replayPack.match.startDate;
        matches[matchIdx].endDate = replayPack.match.endDate;
        matches[matchIdx].matchId = replay.matchId;
      }
    }
    
  } catch (err: any) {
    // No replay available
    warnings.push(`NO_REPLAY_MATCH: ${err.message}`);
    replay = {
      matchId: '',
      rank: 0,
      similarity: 0,
      window: [],
      continuation: [],
    };
    replayPct = [];
  }
  
  // ═══════════════════════════════════════════════════════════════
  // 4) HYBRID: Blend synthetic + replay
  // ═══════════════════════════════════════════════════════════════
  
  // Compute replay weight (clamped to 0.5)
  const similarity = replay.similarity || diagnostics.similarity;
  const entropy = diagnostics.entropy;
  const replayWeight = computeReplayWeight(similarity, entropy, 0.5);
  
  // Blend paths
  let hybridPct: number[];
  if (replayPct.length > 0 && !hasNaN(replayPct)) {
    hybridPct = blendPathsPointByPoint(synthPct, replayPct, replayWeight);
  } else {
    // Fallback to synthetic if no replay
    hybridPct = synthPct;
    if (replayPct.length === 0) {
      warnings.push('HYBRID_FALLBACK: Using synthetic only (no replay data)');
    }
  }
  
  // Validate hybrid for NaN
  if (hasNaN(hybridPct)) {
    warnings.push('HYBRID_NAN_DETECTED: Falling back to synthetic');
    hybridPct = synthPct;
  }
  
  // Convert to path points
  const hybridPath = pctToAbsolutePath(
    currentPrice,
    hybridPct,
    currentDate
  );
  
  // Compute breakdown
  const breakdown = computeHybridBreakdown(synthPct, replayPct, hybridPct, focusDays);
  
  const hybrid: TerminalHybridPack = {
    replayWeight: Math.round(replayWeight * 10000) / 10000,
    path: hybridPath,
    breakdown,
  };
  
  // ═══════════════════════════════════════════════════════════════
  // 5) DECISION: Build trading decision
  // ═══════════════════════════════════════════════════════════════
  
  const forecastReturn = synthetic.forecast.base;
  const regimeBias = forecastReturn >= 0 ? 'USD_STRENGTHENING' : 'USD_WEAKENING';
  
  let action: 'LONG' | 'SHORT' | 'HOLD';
  let size: number;
  const reasons: string[] = [];
  
  if (!tradingEnabled) {
    // Regime mode: no trading
    action = 'HOLD';
    size = 0;
    reasons.push('Regime horizon: trading disabled');
    reasons.push(`Bias filter: ${regimeBias}`);
  } else {
    // Tactical mode: generate signal
    action = forecastReturn >= 0 ? 'LONG' : 'SHORT';
    size = 1;
    reasons.push(`${focus} tactical signal`);
    reasons.push(`Forecast: ${(forecastReturn * 100).toFixed(2)}%`);
  }
  
  const decision = {
    action,
    size,
    confidence: Math.round(similarity * 100),
    entropy,
    reasons,
    regimeBias,
    forecastReturn: Math.round(forecastReturn * 10000) / 10000,
  };
  
  // ═══════════════════════════════════════════════════════════════
  // 6) B2: MACRO OVERLAY (if data available)
  // ═══════════════════════════════════════════════════════════════
  
  let macroPack: TerminalMacroPack | undefined;
  let macroTradingGuardTriggered = false;
  let macroAdjustedConfidence = decision.confidence;
  
  try {
    // Get macro score and contexts
    const macroScore = await computeMacroScore();
    
    if (macroScore.components.length > 0) {
      // Build contexts map for overlay calculation
      const contextMap: Record<string, any> = {};
      const seriesIds = ['FEDFUNDS', 'CPILFESL', 'T10Y2Y', 'UNRATE', 'M2SL'];
      
      for (const seriesId of seriesIds) {
        const ctx = await buildMacroContext(seriesId);
        if (ctx) {
          contextMap[seriesId] = ctx;
        }
      }
      
      // Build macro overlay
      const overlay = buildMacroOverlay(macroScore, contextMap, action);
      macroPack = overlay;
      
      // Apply guard if triggered
      if (overlay.overlay.tradingGuard.enabled) {
        macroTradingGuardTriggered = true;
        warnings.push(`MACRO_GUARD: ${overlay.overlay.tradingGuard.reason}`);
      }
      
      // Calculate macro-adjusted confidence
      macroAdjustedConfidence = Math.round(
        decision.confidence * overlay.overlay.confidenceMultiplier
      );
    }
  } catch (err: any) {
    console.log('[DXY Terminal] Macro overlay skipped:', err.message);
    warnings.push('MACRO_UNAVAILABLE: ' + err.message);
  }
  
  // Apply macro guard to trading (if triggered)
  let finalTradingEnabled = tradingEnabled;
  if (macroTradingGuardTriggered && tradingEnabled) {
    finalTradingEnabled = false;
    reasons.push('Macro guard: trading blocked');
  }
  
  // Update decision with macro-adjusted confidence
  const finalDecision = {
    ...decision,
    macroAdjustedConfidence,
  };
  
  // ═══════════════════════════════════════════════════════════════
  // 7) BUILD FINAL PACK
  // ═══════════════════════════════════════════════════════════════
  
  const core: TerminalCorePack = {
    current: {
      price: currentPrice,
      date: currentDate,
    },
    matches,
    diagnostics,
    decision: finalDecision,
  };
  
  const meta: TerminalMeta = {
    mode,
    tradingEnabled: finalTradingEnabled,
    configUsed: {
      focus,
      windowLen,
      threshold: config.threshold,
      weightMode: config.weightMode,
      topK,
    },
    warnings,
    macroOverlayEnabled: !!macroPack,
  };
  
  return {
    ok: true,
    asset: 'DXY',
    focus,
    ts: new Date().toISOString(),
    processingTimeMs: Date.now() - start,
    meta,
    core,
    synthetic,
    replay,
    hybrid,
    macro: macroPack,
  };
}
