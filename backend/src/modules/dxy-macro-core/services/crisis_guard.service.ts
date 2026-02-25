/**
 * CRISIS GUARD SERVICE — B6
 * 
 * Stress-aware layer that manages risk exposure:
 * - Does NOT change direction
 * - Does NOT touch fractal paths
 * - Only manages: confidenceMultiplier, sizeMultiplier, tradingAllowed
 * 
 * ISOLATION: No imports from DXY/BTC/SPX fractal core
 */

import { buildCreditContext } from './credit_context.service.js';
import { getMacroSeriesPoints } from '../ingest/macro.ingest.service.js';

// ═══════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════

export type GuardLevel = 'NONE' | 'WARN' | 'BLOCK';

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
// CONSTANTS — Guard Thresholds
// ═══════════════════════════════════════════════════════════════

// Primary Trigger: BLOCK
const BLOCK_CREDIT_THRESHOLD = 0.5;
const BLOCK_VIX_THRESHOLD = 35;

// Secondary Trigger: WARN
const WARN_CREDIT_THRESHOLD = 0.4;
const WARN_MACRO_SCORE_THRESHOLD = 0.2;

// Guard Output Multipliers
const GUARD_MULTIPLIERS = {
  NONE: { confidence: 1.0, size: 1.0, tradingAllowed: true },
  WARN: { confidence: 0.7, size: 0.5, tradingAllowed: true },
  BLOCK: { confidence: 0.5, size: 0, tradingAllowed: false },
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
// GUARD LEVEL CLASSIFICATION
// ═══════════════════════════════════════════════════════════════

/**
 * Determine guard level based on stress conditions
 * 
 * BLOCK: creditComposite > 0.5 AND VIX > 35
 * WARN:  creditComposite > 0.4 AND macroScoreSigned > 0.2
 * NONE:  otherwise
 */
function classifyGuardLevel(
  creditComposite: number,
  vix: number,
  macroScoreSigned: number
): GuardLevel {
  // Primary Trigger: BLOCK
  if (creditComposite > BLOCK_CREDIT_THRESHOLD && vix > BLOCK_VIX_THRESHOLD) {
    return 'BLOCK';
  }
  
  // Secondary Trigger: WARN
  if (creditComposite > WARN_CREDIT_THRESHOLD && macroScoreSigned > WARN_MACRO_SCORE_THRESHOLD) {
    return 'WARN';
  }
  
  return 'NONE';
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
  
  // Classify guard level
  const level = classifyGuardLevel(creditComposite, vix, macroScoreSigned);
  const triggered = level !== 'NONE';
  
  // Get guard output
  const guard = getGuardOutput(level);
  
  // Apply min() to confidence multiplier
  const finalConfidenceMultiplier = Math.min(
    baseOverlayMultiplier,
    guard.confidenceMultiplier
  );
  
  return {
    stress: {
      creditComposite: Math.round(creditComposite * 1000) / 1000,
      vix: Math.round(vix * 100) / 100,
      macroScoreSigned: Math.round(macroScoreSigned * 1000) / 1000,
      triggered,
      level,
    },
    guard: {
      ...guard,
      confidenceMultiplier: Math.round(guard.confidenceMultiplier * 1000) / 1000,
    },
    baseOverlayMultiplier: Math.round(baseOverlayMultiplier * 1000) / 1000,
    finalConfidenceMultiplier: Math.round(finalConfidenceMultiplier * 1000) / 1000,
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
    BLOCK: number;
  };
  percentages: {
    NONE: number;
    WARN: number;
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
    BLOCK: levels.filter(l => l === 'BLOCK').length,
  };
  
  const total = levels.length;
  const percentages = {
    NONE: total > 0 ? Math.round((counts.NONE / total) * 1000) / 1000 : 0,
    WARN: total > 0 ? Math.round((counts.WARN / total) * 1000) / 1000 : 0,
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
  },
  WARN: {
    credit: WARN_CREDIT_THRESHOLD,
    macroScore: WARN_MACRO_SCORE_THRESHOLD,
  },
};
