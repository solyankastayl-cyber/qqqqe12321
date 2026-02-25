/**
 * DXY REPLAY SERVICE — A2
 * 
 * Builds unified ReplayPack for DXY matches.
 * Compatible with BTC/SPX replay format.
 * 
 * Core features:
 * - windowNormalized: historical window as pct returns
 * - aftermathNormalized: continuation as pct returns
 * - window: PathPoint[] mapped to CURRENT price space
 * - continuation: PathPoint[] for projection after window
 */

import { DxyCandleModel } from '../storage/dxy-candles.model.js';
import {
  DxyReplayPack,
  PathPoint,
  MatchInfo,
  FOCUS_TO_DAYS,
  DEFAULT_WINDOW_LEN,
} from '../contracts/dxy.replay.contract.js';
import {
  toPctFromFirst,
  toPctFromLast,
  mapPctToPrice,
  decadeFromISO,
  normalizeToRange,
  computeSimilarity,
} from '../utils/normalize.js';

// ═══════════════════════════════════════════════════════════════
// SCAN FOR TOP MATCHES (with startIndex)
// ═══════════════════════════════════════════════════════════════

async function scanTopMatches(
  candles: Array<{ date: string; close: number }>,
  windowLen: number,
  focusLen: number,
  topK: number = 10
): Promise<MatchInfo[]> {
  const n = candles.length;
  const minGap = Math.max(focusLen * 2, 120);
  
  if (n < windowLen + focusLen + minGap) {
    throw new Error('Insufficient candles for replay scan');
  }
  
  // Current window (last windowLen candles)
  const currentCloses = candles.slice(-windowLen).map(c => c.close);
  const currentNorm = normalizeToRange(currentCloses);
  
  const currentStartIdx = n - windowLen;
  const maxIdx = currentStartIdx - minGap - windowLen + 1;
  
  const matches: Array<{ startIndex: number; similarity: number; date: string }> = [];
  
  for (let i = 0; i < maxIdx; i++) {
    const candidateCloses = candles.slice(i, i + windowLen).map(c => c.close);
    const candidateNorm = normalizeToRange(candidateCloses);
    
    const similarity = computeSimilarity(currentNorm, candidateNorm);
    
    matches.push({
      startIndex: i,
      similarity,
      date: candles[i + windowLen - 1].date, // End date of window
    });
  }
  
  // Sort by similarity descending
  matches.sort((a, b) => b.similarity - a.similarity);
  
  // Take topK and add rank/decade
  return matches.slice(0, topK).map((m, idx) => ({
    rank: idx + 1,
    startIndex: m.startIndex,
    similarity: m.similarity,
    date: m.date,
    decade: decadeFromISO(m.date),
  }));
}

// ═══════════════════════════════════════════════════════════════
// BUILD REPLAY PACK
// ═══════════════════════════════════════════════════════════════

export async function buildDxyReplayPack(
  focus: string = '30d',
  rank: number = 1,
  windowLen: number = DEFAULT_WINDOW_LEN
): Promise<DxyReplayPack> {
  const start = Date.now();
  const focusLen = FOCUS_TO_DAYS[focus] || 30;
  
  // Load all candles sorted ascending
  const candles = await DxyCandleModel
    .find()
    .sort({ date: 1 })
    .select({ date: 1, close: 1, _id: 0 })
    .lean() as Array<{ date: string; close: number }>;
  
  const n = candles.length;
  
  if (n < windowLen + focusLen + 120) {
    throw new Error(`Insufficient candles: ${n}`);
  }
  
  // Get top matches with startIndex
  const topMatches = await scanTopMatches(candles, windowLen, focusLen, 10);
  
  // Find requested rank
  const match = topMatches.find(m => m.rank === rank) || topMatches[0];
  if (!match) {
    throw new Error('No matches found');
  }
  
  // Current window
  const currentWindowCandles = candles.slice(-windowLen);
  const currentCloses = currentWindowCandles.map(c => c.close);
  
  // Historical window and aftermath
  const i = match.startIndex;
  const histWindowCandles = candles.slice(i, i + windowLen);
  const histAfterCandles = candles.slice(i + windowLen, i + windowLen + focusLen);
  
  const histWindowPrices = histWindowCandles.map(c => c.close);
  const histAfterPrices = histAfterCandles.map(c => c.close);
  
  // Normalize
  const windowNormalized = toPctFromFirst(histWindowPrices);
  const aftermathNormalized = toPctFromLast(histWindowPrices, histAfterPrices);
  
  // Map historical WINDOW to CURRENT price space
  const currentBasePrice = currentCloses[0];
  const windowPoints: PathPoint[] = windowNormalized.map((pct, t) => ({
    t,
    date: currentWindowCandles[t]?.date,
    price: Math.round(mapPctToPrice(currentBasePrice, pct) * 10000) / 10000,
    pctFromStart: Math.round(pct * 10000) / 10000,
  }));
  
  // Map CONTINUATION to CURRENT price space
  // Anchor to LAST WINDOW POINT price (so no gap between window and continuation)
  const lastWindowPrice = windowPoints[windowLen - 1].price;
  const continuationPoints: PathPoint[] = aftermathNormalized.map((pct, j) => {
    const t = windowLen + j;
    const price = mapPctToPrice(lastWindowPrice, pct);
    return {
      t,
      price: Math.round(price * 10000) / 10000,
      pctFromStart: Math.round(((price / currentBasePrice) - 1) * 10000) / 10000,
    };
  });
  
  // Match metadata
  const histStartDate = histWindowCandles[0].date;
  const histEndDate = histWindowCandles[windowLen - 1].date;
  
  return {
    ok: true,
    asset: 'DXY',
    focus,
    windowLen,
    focusLen,
    match: {
      rank: match.rank,
      startDate: histStartDate,
      endDate: histEndDate,
      decade: decadeFromISO(histStartDate),
      similarity: Math.round(match.similarity * 10000) / 10000,
    },
    windowNormalized: windowNormalized.map(v => Math.round(v * 10000) / 10000),
    aftermathNormalized: aftermathNormalized.map(v => Math.round(v * 10000) / 10000),
    window: windowPoints,
    continuation: continuationPoints,
    currentWindowStart: currentWindowCandles[0].date,
    currentWindowEnd: currentWindowCandles[windowLen - 1].date,
    processingTimeMs: Date.now() - start,
  };
}

// ═══════════════════════════════════════════════════════════════
// GET ALL TOP MATCHES (for listing)
// ═══════════════════════════════════════════════════════════════

export async function getDxyTopMatches(
  focus: string = '30d',
  topK: number = 10,
  windowLen: number = DEFAULT_WINDOW_LEN
): Promise<{ ok: boolean; matches: MatchInfo[]; processingTimeMs: number }> {
  const start = Date.now();
  const focusLen = FOCUS_TO_DAYS[focus] || 30;
  
  const candles = await DxyCandleModel
    .find()
    .sort({ date: 1 })
    .select({ date: 1, close: 1, _id: 0 })
    .lean() as Array<{ date: string; close: number }>;
  
  const matches = await scanTopMatches(candles, windowLen, focusLen, topK);
  
  return {
    ok: true,
    matches,
    processingTimeMs: Date.now() - start,
  };
}

// ═══════════════════════════════════════════════════════════════
// LEGACY EXPORTS — For compatibility with dxy-focus-pack.service.ts
// ═══════════════════════════════════════════════════════════════

import type { DxyMatch, DxyReplayPack as LegacyReplayPack, DxyCandle } from '../contracts/dxy.types.js';

/**
 * Build replay packs from matches (legacy format for focus-pack)
 */
export function buildReplayPacks(
  candles: DxyCandle[],
  matches: DxyMatch[],
  horizonDays: number
): LegacyReplayPack[] {
  const closes = candles.map(c => c.close);
  
  return matches.map(match => {
    const windowPrices = closes.slice(match.startIndex, match.endIndex + 1);
    const afterPrices = closes.slice(match.endIndex + 1, match.endIndex + 1 + horizonDays);
    
    // Normalize window relative to first price
    const windowNormalized = toPctFromFirst(windowPrices);
    
    // Normalize aftermath relative to last window price
    const aftermathNormalized = toPctFromLast(windowPrices, afterPrices);
    
    return {
      windowNormalized,
      aftermathNormalized,
      similarity: match.similarity,
      startDate: match.startDate,
      endDate: match.endDate,
    };
  });
}

/**
 * Aggregate replay paths into mean path and percentile bands
 */
export function aggregateReplayPaths(
  replayPacks: LegacyReplayPack[],
  currentPrice: number
): {
  path: number[];
  bands: { p10: number[]; p50: number[]; p90: number[] };
} {
  if (replayPacks.length === 0) {
    return { path: [], bands: { p10: [], p50: [], p90: [] } };
  }
  
  // Find max aftermath length
  const maxLen = Math.max(...replayPacks.map(r => r.aftermathNormalized.length));
  
  if (maxLen === 0) {
    return { path: [], bands: { p10: [], p50: [], p90: [] } };
  }
  
  const path: number[] = [];
  const p10: number[] = [];
  const p50: number[] = [];
  const p90: number[] = [];
  
  for (let i = 0; i < maxLen; i++) {
    const values: number[] = [];
    
    for (const pack of replayPacks) {
      if (i < pack.aftermathNormalized.length) {
        // Convert pct return to price
        const price = currentPrice * (1 + pack.aftermathNormalized[i]);
        values.push(price);
      }
    }
    
    if (values.length === 0) continue;
    
    values.sort((a, b) => a - b);
    const n = values.length;
    
    // Mean
    const mean = values.reduce((a, b) => a + b, 0) / n;
    path.push(Math.round(mean * 10000) / 10000);
    
    // Percentiles
    p10.push(Math.round(values[Math.floor(n * 0.1)] * 10000) / 10000);
    p50.push(Math.round(values[Math.floor(n * 0.5)] * 10000) / 10000);
    p90.push(Math.round(values[Math.floor(n * 0.9)] * 10000) / 10000);
  }
  
  return { path, bands: { p10, p50, p90 } };
}

/**
 * Calculate expected return from replay packs
 */
export function calculateExpectedReturn(
  replayPacks: LegacyReplayPack[]
): { bear: number; base: number; bull: number } {
  if (replayPacks.length === 0) {
    return { bear: -0.02, base: 0, bull: 0.02 };
  }
  
  // Collect final returns
  const finalReturns: number[] = [];
  
  for (const pack of replayPacks) {
    if (pack.aftermathNormalized.length > 0) {
      finalReturns.push(pack.aftermathNormalized[pack.aftermathNormalized.length - 1]);
    }
  }
  
  if (finalReturns.length === 0) {
    return { bear: -0.02, base: 0, bull: 0.02 };
  }
  
  finalReturns.sort((a, b) => a - b);
  const n = finalReturns.length;
  
  const bear = finalReturns[Math.floor(n * 0.1)];
  const base = finalReturns[Math.floor(n * 0.5)];
  const bull = finalReturns[Math.floor(n * 0.9)];
  
  return {
    bear: Math.round(bear * 10000) / 10000,
    base: Math.round(base * 10000) / 10000,
    bull: Math.round(bull * 10000) / 10000,
  };
}
