/**
 * CREDIT CONTEXT SERVICE — B4.3
 * 
 * Computes context and pressure for credit & financial stress series:
 * - BAA10Y: Moody's BAA Corporate Spread
 * - BAMLH0A0HYM2: High Yield Spread (ICE BofA)
 * - STLFSI4: St. Louis Fed Financial Stress Index
 * 
 * ISOLATION: No imports from DXY/BTC/SPX modules
 */

import { getMacroSeriesPoints } from '../ingest/macro.ingest.service.js';
import { getMacroSeriesSpec } from '../data/macro_sources.registry.js';

// ═══════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════

export type CreditTrend = 'UP' | 'DOWN' | 'FLAT';
export type CreditRegime = 'STRESS' | 'CALM' | 'NEUTRAL' | 'HIGH_STRESS' | 'LOW_STRESS';

export interface CreditSeriesContext {
  seriesId: string;
  displayName: string;
  available: boolean;
  
  current: {
    value: number;
    date: string;
  } | null;
  
  deltas: {
    delta3m: number | null;
    delta12m: number | null;
  };
  
  stats: {
    mean5y: number;
    std5y: number;
    z5y: number;
  } | null;
  
  trend: CreditTrend;
  regime: CreditRegime;
  pressure: number;  // -1..+1 (positive = stress = USD supportive)
}

export interface CreditContext {
  baa: CreditSeriesContext;
  hy: CreditSeriesContext;
  fsi: CreditSeriesContext;
  
  composite: {
    scoreSigned: number;  // -1..+1 (positive = stress = USD supportive)
    confidence: number;   // 0..1
    regime: string;
    note: string;
  };
  
  computedAt: string;
}

// ═══════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════

const WEIGHTS = {
  BAA10Y: 0.40,
  BAMLH0A0HYM2: 0.35,
  STLFSI4: 0.25,
};

// ═══════════════════════════════════════════════════════════════
// STATISTICAL HELPERS
// ═══════════════════════════════════════════════════════════════

function mean(arr: number[]): number {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function stdDev(arr: number[]): number {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  const variance = arr.reduce((sum, v) => sum + Math.pow(v - m, 2), 0) / (arr.length - 1);
  return Math.sqrt(variance);
}

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

// ═══════════════════════════════════════════════════════════════
// TRANSFORM HELPERS
// ═══════════════════════════════════════════════════════════════

/**
 * Convert daily/weekly data to monthly averages
 */
function toMonthlyAverage(
  points: Array<{ date: string; value: number }>
): Array<{ date: string; value: number }> {
  const byMonth = new Map<string, number[]>();
  
  for (const p of points) {
    const monthKey = p.date.substring(0, 7);
    if (!byMonth.has(monthKey)) {
      byMonth.set(monthKey, []);
    }
    byMonth.get(monthKey)!.push(p.value);
  }
  
  const result: Array<{ date: string; value: number }> = [];
  for (const [month, values] of byMonth) {
    result.push({
      date: month + '-15',
      value: mean(values),
    });
  }
  
  return result.sort((a, b) => a.date.localeCompare(b.date));
}

function computeDelta(
  points: Array<{ date: string; value: number }>,
  current: number,
  months: number
): number | null {
  if (points.length < months) return null;
  const index = Math.max(0, points.length - months - 1);
  return current - points[index].value;
}

function compute5YearStats(
  points: Array<{ date: string; value: number }>,
  current: number
): { mean5y: number; std5y: number; z5y: number } | null {
  if (points.length < 60) return null;
  
  const last5y = points.slice(-60).map(p => p.value);
  const m = mean(last5y);
  const sd = stdDev(last5y);
  
  if (sd === 0) return { mean5y: m, std5y: 0, z5y: 0 };
  
  return {
    mean5y: Math.round(m * 1000) / 1000,
    std5y: Math.round(sd * 1000) / 1000,
    z5y: Math.round(((current - m) / sd) * 1000) / 1000,
  };
}

function classifyTrend(delta3m: number | null, std5y: number): CreditTrend {
  if (delta3m === null || std5y === 0) return 'FLAT';
  
  const threshold = std5y * 0.5;
  if (delta3m > threshold) return 'UP';
  if (delta3m < -threshold) return 'DOWN';
  return 'FLAT';
}

// ═══════════════════════════════════════════════════════════════
// REGIME CLASSIFICATION
// ═══════════════════════════════════════════════════════════════

/**
 * BAA/HY Spread regime: based on z-score
 * z5y > +1 = STRESS, z5y < -1 = CALM, else NEUTRAL
 */
function classifySpreadRegime(z5y: number | null): CreditRegime {
  if (z5y === null) return 'NEUTRAL';
  if (z5y > 1) return 'STRESS';
  if (z5y < -1) return 'CALM';
  return 'NEUTRAL';
}

/**
 * Financial Stress Index regime: based on level
 * > +1 = HIGH_STRESS, < -1 = LOW_STRESS, else NEUTRAL
 */
function classifyFsiRegime(value: number): CreditRegime {
  if (value > 1) return 'HIGH_STRESS';
  if (value < -1) return 'LOW_STRESS';
  return 'NEUTRAL';
}

// ═══════════════════════════════════════════════════════════════
// PRESSURE CALCULATION
// ═══════════════════════════════════════════════════════════════

/**
 * Spread pressure: z5y / 3, clamped to -1..+1
 * High spreads = stress = safe-haven bid = USD supportive (positive)
 */
function calcSpreadPressure(z5y: number | null): number {
  if (z5y === null) return 0;
  return clamp(z5y / 3, -1, 1);
}

/**
 * FSI pressure: current / 3, clamped to -1..+1
 * High stress = safe-haven bid = USD supportive (positive)
 */
function calcFsiPressure(value: number): number {
  return clamp(value / 3, -1, 1);
}

// ═══════════════════════════════════════════════════════════════
// BUILD SINGLE SERIES CONTEXT
// ═══════════════════════════════════════════════════════════════

async function buildBaaContext(): Promise<CreditSeriesContext> {
  const seriesId = 'BAA10Y';
  const spec = getMacroSeriesSpec(seriesId);
  const displayName = spec?.displayName ?? "Moody's Baa Spread";
  
  try {
    const points = await getMacroSeriesPoints(seriesId);
    
    if (points.length === 0) {
      return buildEmptyContext(seriesId, displayName);
    }
    
    const latestPoint = points[points.length - 1];
    const current = latestPoint.value;
    const currentDate = latestPoint.date;
    
    const delta3m = computeDelta(points, current, 3);
    const delta12m = computeDelta(points, current, 12);
    const stats = compute5YearStats(points, current);
    
    const trend = classifyTrend(delta3m, stats?.std5y ?? 0.5);
    const regime = classifySpreadRegime(stats?.z5y ?? null);
    const pressure = calcSpreadPressure(stats?.z5y ?? null);
    
    return {
      seriesId,
      displayName,
      available: true,
      current: { value: Math.round(current * 1000) / 1000, date: currentDate },
      deltas: {
        delta3m: delta3m !== null ? Math.round(delta3m * 1000) / 1000 : null,
        delta12m: delta12m !== null ? Math.round(delta12m * 1000) / 1000 : null,
      },
      stats,
      trend,
      regime,
      pressure: Math.round(pressure * 1000) / 1000,
    };
  } catch (error: any) {
    console.error(`[Credit] Failed to build BAA context:`, error.message);
    return buildEmptyContext(seriesId, displayName);
  }
}

async function buildHyContext(): Promise<CreditSeriesContext> {
  const seriesId = 'BAMLH0A0HYM2';
  const spec = getMacroSeriesSpec(seriesId);
  const displayName = spec?.displayName ?? 'High Yield Spread';
  
  try {
    let points = await getMacroSeriesPoints(seriesId);
    
    if (points.length === 0) {
      return buildEmptyContext(seriesId, displayName);
    }
    
    // Convert daily to monthly
    points = toMonthlyAverage(points);
    
    const latestPoint = points[points.length - 1];
    const current = latestPoint.value;
    const currentDate = latestPoint.date;
    
    const delta3m = computeDelta(points, current, 3);
    const delta12m = computeDelta(points, current, 12);
    const stats = compute5YearStats(points, current);
    
    const trend = classifyTrend(delta3m, stats?.std5y ?? 0.5);
    const regime = classifySpreadRegime(stats?.z5y ?? null);
    const pressure = calcSpreadPressure(stats?.z5y ?? null);
    
    return {
      seriesId,
      displayName,
      available: true,
      current: { value: Math.round(current * 1000) / 1000, date: currentDate },
      deltas: {
        delta3m: delta3m !== null ? Math.round(delta3m * 1000) / 1000 : null,
        delta12m: delta12m !== null ? Math.round(delta12m * 1000) / 1000 : null,
      },
      stats,
      trend,
      regime,
      pressure: Math.round(pressure * 1000) / 1000,
    };
  } catch (error: any) {
    console.error(`[Credit] Failed to build HY context:`, error.message);
    return buildEmptyContext(seriesId, displayName);
  }
}

async function buildFsiContext(): Promise<CreditSeriesContext> {
  const seriesId = 'STLFSI4';
  const spec = getMacroSeriesSpec(seriesId);
  const displayName = spec?.displayName ?? 'Financial Stress Index';
  
  try {
    let points = await getMacroSeriesPoints(seriesId);
    
    if (points.length === 0) {
      return buildEmptyContext(seriesId, displayName);
    }
    
    // Convert weekly to monthly
    points = toMonthlyAverage(points);
    
    const latestPoint = points[points.length - 1];
    const current = latestPoint.value;
    const currentDate = latestPoint.date;
    
    const delta3m = computeDelta(points, current, 3);
    const delta12m = computeDelta(points, current, 12);
    const stats = compute5YearStats(points, current);
    
    const trend = classifyTrend(delta3m, 0.5);
    const regime = classifyFsiRegime(current);
    const pressure = calcFsiPressure(current);
    
    return {
      seriesId,
      displayName,
      available: true,
      current: { value: Math.round(current * 1000) / 1000, date: currentDate },
      deltas: {
        delta3m: delta3m !== null ? Math.round(delta3m * 1000) / 1000 : null,
        delta12m: delta12m !== null ? Math.round(delta12m * 1000) / 1000 : null,
      },
      stats,
      trend,
      regime,
      pressure: Math.round(pressure * 1000) / 1000,
    };
  } catch (error: any) {
    console.error(`[Credit] Failed to build FSI context:`, error.message);
    return buildEmptyContext(seriesId, displayName);
  }
}

function buildEmptyContext(seriesId: string, displayName: string): CreditSeriesContext {
  return {
    seriesId,
    displayName,
    available: false,
    current: null,
    deltas: { delta3m: null, delta12m: null },
    stats: null,
    trend: 'FLAT',
    regime: 'NEUTRAL',
    pressure: 0,
  };
}

// ═══════════════════════════════════════════════════════════════
// BUILD COMPOSITE CREDIT CONTEXT
// ═══════════════════════════════════════════════════════════════

export async function buildCreditContext(): Promise<CreditContext> {
  const baa = await buildBaaContext();
  const hy = await buildHyContext();
  const fsi = await buildFsiContext();
  
  // Calculate composite score
  const pressures = [
    { weight: WEIGHTS.BAA10Y, pressure: baa.pressure, available: baa.available },
    { weight: WEIGHTS.BAMLH0A0HYM2, pressure: hy.pressure, available: hy.available },
    { weight: WEIGHTS.STLFSI4, pressure: fsi.pressure, available: fsi.available },
  ];
  
  const available = pressures.filter(p => p.available);
  const missingCount = 3 - available.length;
  
  let scoreSigned = 0;
  let totalWeight = 0;
  
  if (available.length > 0) {
    for (const p of available) {
      scoreSigned += p.pressure * p.weight;
      totalWeight += p.weight;
    }
    if (totalWeight > 0) {
      scoreSigned = scoreSigned / totalWeight;
    }
  }
  
  scoreSigned = clamp(scoreSigned, -1, 1);
  
  // Confidence based on missing series
  let confidence: number;
  if (missingCount >= 2) {
    confidence = 0.4;
  } else if (missingCount === 1) {
    confidence = 0.6;
  } else {
    const availablePressures = available.map(p => p.pressure);
    const pressureStd = stdDev(availablePressures);
    confidence = clamp(1 - pressureStd, 0.3, 1);
  }
  
  // Determine composite regime
  let regime: string;
  const stressCount = [baa.regime, hy.regime, fsi.regime].filter(
    r => r === 'STRESS' || r === 'HIGH_STRESS'
  ).length;
  const calmCount = [baa.regime, hy.regime, fsi.regime].filter(
    r => r === 'CALM' || r === 'LOW_STRESS'
  ).length;
  
  if (stressCount >= 2) {
    regime = 'STRESS';
  } else if (calmCount >= 2) {
    regime = 'CALM';
  } else {
    regime = 'NEUTRAL';
  }
  
  // Build note
  let note: string;
  if (regime === 'STRESS') {
    note = 'Rising spreads / financial stress → USD safe-haven bid';
  } else if (regime === 'CALM') {
    note = 'Compressed spreads / low stress → USD tailwind reduced';
  } else {
    note = 'Credit conditions neutral';
  }
  
  return {
    baa,
    hy,
    fsi,
    composite: {
      scoreSigned: Math.round(scoreSigned * 1000) / 1000,
      confidence: Math.round(confidence * 1000) / 1000,
      regime,
      note,
    },
    computedAt: new Date().toISOString(),
  };
}

/**
 * Get credit score component for macro score integration
 */
export async function getCreditScoreComponent(): Promise<{
  key: string;
  displayName: string;
  scoreSigned: number;
  weight: number;
  confidence: number;
  regime: string;
  available: boolean;
}> {
  const ctx = await buildCreditContext();
  
  const anyAvailable = ctx.baa.available || ctx.hy.available || ctx.fsi.available;
  
  return {
    key: 'CREDIT',
    displayName: 'Financial Stress & Credit Spreads',
    scoreSigned: ctx.composite.scoreSigned,
    weight: 0.15,
    confidence: ctx.composite.confidence,
    regime: ctx.composite.regime,
    available: anyAvailable,
  };
}
