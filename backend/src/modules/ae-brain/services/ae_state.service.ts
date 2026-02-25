/**
 * C1 — State Vector Aggregator Service
 * Builds normalized state vector from DXY terminal + macro + guard
 */

import type { AeStateVector } from '../contracts/ae_state.contract.js';
import { GUARD_LEVEL_MAP, ACTION_SIGN_MAP } from '../contracts/ae_state.contract.js';
import { clamp, safeNumber } from '../utils/ae_math.js';

// Import from dxy-macro-core (read-only)
import { computeMacroScore } from '../../dxy-macro-core/services/macro_score.service.js';
import { computeCrisisGuard } from '../../dxy-macro-core/services/crisis_guard.service.js';

// Import from dxy fractal terminal (read-only)
import { buildDxyTerminalPack } from '../../dxy/services/dxy_terminal_pack.service.js';

/**
 * Build AE State Vector
 * Aggregates macro, guard, and DXY terminal into normalized vector
 */
export async function buildAeState(asOf?: string): Promise<AeStateVector> {
  const missing: string[] = [];
  const today = asOf || new Date().toISOString().split('T')[0];
  
  // Default vector (neutral)
  const vector = {
    macroSigned: 0,
    macroConfidence: 0.5,
    guardLevel: 0,
    dxySignalSigned: 0,
    dxyConfidence: 0.5,
    regimeBias90d: 0,
  };
  
  // 1. Get Macro Score
  try {
    const macroResult = await computeMacroScore();
    if (macroResult.ok && macroResult.score) {
      vector.macroSigned = clamp(safeNumber(macroResult.score.scoreSigned), -1, 1);
      vector.macroConfidence = clamp(safeNumber(macroResult.score.confidence, 0.5), 0, 1);
    } else {
      missing.push('macro_score');
    }
  } catch (e) {
    console.warn('[AE State] Macro score unavailable:', (e as Error).message);
    missing.push('macro_score');
  }
  
  // 2. Get Crisis Guard
  try {
    const guardResult = await computeCrisisGuard(vector.macroSigned);
    if (guardResult.stress) {
      const level = guardResult.stress.level || 'NONE';
      vector.guardLevel = GUARD_LEVEL_MAP[level] ?? 0;
    }
  } catch (e) {
    console.warn('[AE State] Guard unavailable:', (e as Error).message);
    missing.push('guard');
  }
  
  // 3. Get DXY Terminal
  try {
    const dxyPack = await buildDxyTerminalPack();
    if (dxyPack.ok && dxyPack.decision) {
      // Action to signed signal
      const action = dxyPack.decision.action || 'HOLD';
      const actionSign = ACTION_SIGN_MAP[action] ?? 0;
      
      // Scale by forecast return (tanh normalization, k=0.03)
      const forecastReturn = safeNumber(dxyPack.decision.forecastReturn, 0);
      const returnScale = Math.tanh(Math.abs(forecastReturn) / 0.03);
      
      vector.dxySignalSigned = clamp(actionSign * returnScale, -1, 1);
      
      // Confidence
      const confidence = dxyPack.decision.macroAdjustedConfidence 
        || dxyPack.decision.confidence 
        || 0.5;
      vector.dxyConfidence = clamp(safeNumber(confidence), 0, 1);
      
      // 90d regime bias
      if (dxyPack.decision.regimeBias !== undefined) {
        vector.regimeBias90d = clamp(safeNumber(dxyPack.decision.regimeBias), -1, 1);
      }
    } else {
      missing.push('dxy_terminal');
    }
  } catch (e) {
    console.warn('[AE State] DXY terminal unavailable:', (e as Error).message);
    missing.push('dxy_terminal');
  }
  
  return {
    asOf: today,
    vector,
    health: {
      ok: missing.length === 0,
      missing,
    },
  };
}

/**
 * Convert state vector to array (for KNN)
 */
export function stateVectorToArray(v: AeStateVector['vector']): number[] {
  return [
    v.macroSigned,
    v.macroConfidence,
    v.guardLevel,
    v.dxySignalSigned,
    v.dxyConfidence,
    v.regimeBias90d,
  ];
}
