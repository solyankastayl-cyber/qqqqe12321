/**
 * CRISIS GUARD SERVICE — B6 (2-Stage Guard)
 * 
 * Stress-aware layer that manages risk exposure:
 * - Does NOT change direction
 * - Does NOT touch fractal paths
 * - Only manages: confidenceMultiplier, sizeMultiplier, tradingAllowed
 * 
 * 🎯 Guard Hierarchy (top-down):
 *   1. BLOCK  (peak panic) — самый строгий
 *   2. CRISIS (systemic stress)
 *   3. WARN   (soft tightening / macro conflict)
 *   4. NONE
 * 
 * 📊 Acceptance Targets:
 *   - GFC 2008-09:     CRISIS ≥ 60%, BLOCK ≥ 20%
 *   - COVID 2020:      CRISIS ≥ 80%, BLOCK ≥ 40%
 *   - Tightening 2022: WARN ≤ 40%,   BLOCK ≤ 10%
 *   - Low Vol 2017:    NONE ≥ 80%,   BLOCK = 0%
 * 
 * ISOLATION: No imports from DXY/BTC/SPX fractal core
 */

import { buildCreditContext } from './credit_context.service.js';
import { getMacroSeriesPoints } from '../ingest/macro.ingest.service.js';

// ═══════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════

export type GuardLevel = 'NONE' | 'WARN' | 'CRISIS' | 'BLOCK';

export interface StressState {
  creditComposite: number;
  vix: number;
  macroScoreSigned: number;
  triggered: boolean;
  level: GuardLevel;
}

export interface GuardOutput {
  confidenceMultiplier: number;
  sizeMultiplier: number;
  tradingAllowed: boolean;
  level: GuardLevel;
}

export interface CrisisGuardResult {
  stress: StressState;
  guard: GuardOutput;
  baseOverlayMultiplier: number;
  finalConfidenceMultiplier: number;
}

// ═══════════════════════════════════════════════════════════════
// CONSTANTS — B6 Guard Thresholds (2-Stage)
// ═══════════════════════════════════════════════════════════════

// Stage 2: BLOCK (пик паники)
const BLOCK_CREDIT_THRESHOLD = 0.50;
const BLOCK_VIX_THRESHOLD = 32;

// Stage 1: CRISIS (системный стресс)  
const CRISIS_CREDIT_THRESHOLD = 0.25;
const CRISIS_VIX_THRESHOLD = 18;

// Stage 3: WARN (tightening / conflict)
const WARN_CREDIT_THRESHOLD = 0.30;
const WARN_MACRO_SCORE_THRESHOLD = 0.15;

// Guard Output Multipliers
const GUARD_MULTIPLIERS: Record<GuardLevel, { confidence: number; size: number; tradingAllowed: boolean }> = {
  NONE:   { confidence: 1.0,  size: 1.0, tradingAllowed: true },
  WARN:   { confidence: 0.75, size: 0.6, tradingAllowed: true },
  CRISIS: { confidence: 0.65, size: 0.4, tradingAllowed: true },
  BLOCK:  { confidence: 0.5,  size: 0,   tradingAllowed: false },
};

// ═══════════════════════════════════════════════════════════════
// HELPER: Get current VIX
// ═══════════════════════════════════════════════════════════════

async function getCurrentVix(): Promise<number> {
  try {
    const points = await getMacroSeriesPoints('VIXCLS');
    if (points.length === 0) return 20;  // Default neutral VIX
    
    // Get latest value
    const latest = points[points.length - 1];
    return latest.value;
  } catch (e) {
    console.warn('[Crisis Guard] Failed to get VIX:', (e as Error).message);
    return 20;  // Default
  }
}

/**
 * Get VIX at specific date (for historical validation)
 */
async function getVixAtDate(targetDate: string): Promise<number> {
  try {
    const points = await getMacroSeriesPoints('VIXCLS');
    if (points.length === 0) return 20;
    
    // LOCF: find last value <= targetDate
    let result = 20;
    for (const p of points) {
      if (p.date <= targetDate) {
        result = p.value;
      } else {
        break;
      }
    }
    return result;
  } catch (e) {
    return 20;
  }
}

// ═══════════════════════════════════════════════════════════════
// GUARD LEVEL CLASSIFICATION — B6 2-Stage
// ═══════════════════════════════════════════════════════════════

/**
 * Determine guard level based on stress conditions
 * 
 * 🎯 B6 2-Stage Guard Logic:
 * 
 * 1️⃣ BLOCK (пик паники):
 *    creditComposite > 0.55 AND VIX > 35
 * 
 * 2️⃣ CRISIS (системный стресс):
 *    creditComposite > 0.4 AND VIX > 25
 * 
 * 3️⃣ WARN (tightening / conflict):
 *    creditComposite > 0.35 AND macroScoreSigned > 0.2
 * 
 * 4️⃣ NONE (спокойствие)
 */
function classifyGuardLevel(
  creditComposite: number,
  vix: number,
  macroScoreSigned: number
): GuardLevel {
  // 1️⃣ BLOCK — пик паники (самый строгий)
  if (creditComposite > BLOCK_CREDIT_THRESHOLD && vix > BLOCK_VIX_THRESHOLD) {
    return 'BLOCK';
  }
  
  // 2️⃣ CRISIS — системный стресс
  if (creditComposite > CRISIS_CREDIT_THRESHOLD && vix > CRISIS_VIX_THRESHOLD) {
    return 'CRISIS';
  }
  
  // 3️⃣ WARN — tightening / conflict
  if (creditComposite > WARN_CREDIT_THRESHOLD && macroScoreSigned > WARN_MACRO_SCORE_THRESHOLD) {
    return 'WARN';
  }
  
  // 4️⃣ NONE — спокойствие
  return 'NONE';
}

/**
 * Map guard level to overlay outputs
 */
function mapModeToOverlay(
  level: GuardLevel,
  baseOverlayMultiplier: number
): GuardOutput & { finalConfidenceMultiplier: number } {
  const mult = GUARD_MULTIPLIERS[level];
  
  // Apply min() — overlay = min(baseOverlay, guardOverlay)
  const finalConfidenceMultiplier = Math.min(
    baseOverlayMultiplier,
    mult.confidence
  );
  
  return {
    confidenceMultiplier: mult.confidence,
    sizeMultiplier: mult.size,
    tradingAllowed: mult.tradingAllowed,
    level,
    finalConfidenceMultiplier,
  };
}

/**
 * Get guard output based on level
 */
function getGuardOutput(level: GuardLevel): GuardOutput {
  const mult = GUARD_MULTIPLIERS[level];
  return {
    confidenceMultiplier: mult.confidence,
    sizeMultiplier: mult.size,
    tradingAllowed: mult.tradingAllowed,
    level,
  };
}

// ═══════════════════════════════════════════════════════════════
// MAIN: Compute Crisis Guard
// ═══════════════════════════════════════════════════════════════

/**
 * Compute crisis guard for current state
 */
export async function computeCrisisGuard(
  macroScoreSigned: number,
  baseOverlayMultiplier: number = 1.0
): Promise<CrisisGuardResult> {
  // Get credit composite
  const creditContext = await buildCreditContext();
  const creditComposite = creditContext.composite.scoreSigned;
  
  // Get current VIX
  const vix = await getCurrentVix();
  
  // Classify guard level using B6 2-Stage logic
  const level = classifyGuardLevel(creditComposite, vix, macroScoreSigned);
  const triggered = level !== 'NONE';
  
  // Get guard output with final multiplier
  const overlay = mapModeToOverlay(level, baseOverlayMultiplier);
  
  return {
    stress: {
      creditComposite: Math.round(creditComposite * 1000) / 1000,
      vix: Math.round(vix * 100) / 100,
      macroScoreSigned: Math.round(macroScoreSigned * 1000) / 1000,
      triggered,
      level,
    },
    guard: {
      confidenceMultiplier: Math.round(overlay.confidenceMultiplier * 1000) / 1000,
      sizeMultiplier: overlay.sizeMultiplier,
      tradingAllowed: overlay.tradingAllowed,
      level,
    },
    baseOverlayMultiplier: Math.round(baseOverlayMultiplier * 1000) / 1000,
    finalConfidenceMultiplier: Math.round(overlay.finalConfidenceMultiplier * 1000) / 1000,
  };
}

/**
 * Compute crisis guard at specific date (for historical validation)
 */
export async function computeCrisisGuardAtDate(
  targetDate: string,
  creditComposite: number,
  macroScoreSigned: number
): Promise<{ level: GuardLevel; triggered: boolean; vix: number }> {
  const vix = await getVixAtDate(targetDate);
  const level = classifyGuardLevel(creditComposite, vix, macroScoreSigned);
  
  return {
    level,
    triggered: level !== 'NONE',
    vix,
  };
}

// ═══════════════════════════════════════════════════════════════
// VALIDATION HELPERS
// ═══════════════════════════════════════════════════════════════

export interface GuardValidationResult {
  period: { from: string; to: string };
  samples: number;
  guardCounts: {
    NONE: number;
    WARN: number;
    CRISIS: number;
    BLOCK: number;
  };
  percentages: {
    NONE: number;
    WARN: number;
    CRISIS: number;
    BLOCK: number;
  };
  flips: number;
  avgDurationDays: number;
}

/**
 * Validate guard behavior over a period
 */
export async function validateGuardPeriod(
  from: string,
  to: string,
  stepDays: number,
  samples: Array<{
    date: string;
    creditComposite: number;
    macroScoreSigned: number;
  }>
): Promise<GuardValidationResult> {
  const levels: GuardLevel[] = [];
  
  for (const sample of samples) {
    const vix = await getVixAtDate(sample.date);
    const level = classifyGuardLevel(sample.creditComposite, vix, sample.macroScoreSigned);
    levels.push(level);
  }
  
  // Count levels
  const counts = {
    NONE: levels.filter(l => l === 'NONE').length,
    WARN: levels.filter(l => l === 'WARN').length,
    CRISIS: levels.filter(l => l === 'CRISIS').length,
    BLOCK: levels.filter(l => l === 'BLOCK').length,
  };
  
  const total = levels.length;
  const percentages = {
    NONE: total > 0 ? Math.round((counts.NONE / total) * 1000) / 1000 : 0,
    WARN: total > 0 ? Math.round((counts.WARN / total) * 1000) / 1000 : 0,
    CRISIS: total > 0 ? Math.round((counts.CRISIS / total) * 1000) / 1000 : 0,
    BLOCK: total > 0 ? Math.round((counts.BLOCK / total) * 1000) / 1000 : 0,
  };
  
  // Count flips
  let flips = 0;
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] !== levels[i - 1]) flips++;
  }
  
  // Average duration
  const durations: number[] = [];
  let currentDuration = 1;
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] === levels[i - 1]) {
      currentDuration++;
    } else {
      durations.push(currentDuration * stepDays);
      currentDuration = 1;
    }
  }
  durations.push(currentDuration * stepDays);
  
  const avgDuration = durations.length > 0
    ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
    : 0;
  
  return {
    period: { from, to },
    samples: total,
    guardCounts: counts,
    percentages,
    flips,
    avgDurationDays: avgDuration,
  };
}

// ═══════════════════════════════════════════════════════════════
// EXPORT THRESHOLDS (for documentation)
// ═══════════════════════════════════════════════════════════════

export const GUARD_THRESHOLDS = {
  BLOCK: {
    credit: BLOCK_CREDIT_THRESHOLD,
    vix: BLOCK_VIX_THRESHOLD,
    description: 'Peak Panic — Trading Disabled',
  },
  CRISIS: {
    credit: CRISIS_CREDIT_THRESHOLD,
    vix: CRISIS_VIX_THRESHOLD,
    description: 'Systemic Stress — Reduced Size',
  },
  WARN: {
    credit: WARN_CREDIT_THRESHOLD,
    macroScore: WARN_MACRO_SCORE_THRESHOLD,
    description: 'Soft Tightening / Macro Conflict',
  },
};

// ═══════════════════════════════════════════════════════════════
// B6 ACCEPTANCE CRITERIA (for testing)
// ═══════════════════════════════════════════════════════════════

export const B6_ACCEPTANCE_CRITERIA = {
  GFC_2008_2009: {
    CRISIS_MIN: 0.60,  // ≥ 60%
    BLOCK_MIN: 0.20,   // ≥ 20%
  },
  COVID_2020: {
    CRISIS_MIN: 0.80,  // ≥ 80%
    BLOCK_MIN: 0.40,   // ≥ 40%
  },
  TIGHTENING_2022: {
    WARN_MAX: 0.40,    // ≤ 40%
    BLOCK_MAX: 0.10,   // ≤ 10%
  },
  LOW_VOL_2017: {
    NONE_MIN: 0.80,    // ≥ 80%
    BLOCK_MAX: 0,      // = 0%
  },
  STABILITY: {
    flipsPerYear: 4,     // ≤ 4
    medianDuration: 30,  // ≥ 30 days
  },
};
