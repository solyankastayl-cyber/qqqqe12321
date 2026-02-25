/**
 * MACRO SCORE SERVICE — B1 + B4.1 (Housing)
 * 
 * Computes composite macro score from all series.
 * B4.1: Added housing component (MORTGAGE30US, HOUST, PERMIT, CSUSHPISA)
 * 
 * ISOLATION: No imports from DXY/BTC/SPX modules
 */

import { buildAllMacroContexts, buildMacroContext } from './macro_context.service.js';
import { getHousingScoreComponent } from './housing_context.service.js';
import { getEnabledMacroSeries, MacroRole } from '../data/macro_sources.registry.js';
import {
  MacroScore,
  MacroScoreComponent,
  MacroContext,
  MacroConfidence,
} from '../contracts/macro.contracts.js';

// ═══════════════════════════════════════════════════════════════
// WEIGHTS BY ROLE
// ═══════════════════════════════════════════════════════════════

const ROLE_WEIGHTS: Record<MacroRole, number> = {
  rates: 0.22,        // Fed policy is primary driver (reduced from 0.25 for housing)
  inflation: 0.18,    // Split between headline and core
  labor: 0.14,        // Employment matters for policy
  liquidity: 0.14,    // M2 affects risk appetite
  curve: 0.14,        // Yield curve is leading indicator
  growth: 0.05,       // Secondary (not in B1 core)
  housing: 0.10,      // B4.1: Housing & Real Estate
  credit: 0.03,       // Secondary
};

// Housing weight (separate calculation)
const HOUSING_COMPOSITE_WEIGHT = 0.15;  // 15% of total score

// Per-series weight adjustments (within role)
const SERIES_WEIGHT_MULTIPLIERS: Record<string, number> = {
  'FEDFUNDS': 1.0,
  'CPIAUCSL': 0.4,    // Headline CPI
  'CPILFESL': 0.6,    // Core CPI (more important)
  'UNRATE': 1.0,
  'PPIACO': 0.3,      // PPI is part of inflation role
  'M2SL': 1.0,
  'T10Y2Y': 1.0,
};

// B4.1: Housing series to exclude from standard processing
const HOUSING_SERIES = ['MORTGAGE30US', 'HOUST', 'PERMIT', 'CSUSHPISA'];

// ═══════════════════════════════════════════════════════════════
// COMPUTE COMPOSITE SCORE
// ═══════════════════════════════════════════════════════════════

export async function computeMacroScore(): Promise<MacroScore> {
  const contexts = await buildAllMacroContexts();
  
  if (contexts.length === 0) {
    return buildEmptyScore();
  }
  
  // Build components
  const components: MacroScoreComponent[] = [];
  let totalWeight = 0;
  let weightedSum = 0;
  
  for (const ctx of contexts) {
    const roleWeight = ROLE_WEIGHTS[ctx.role] || 0.05;
    const seriesMultiplier = SERIES_WEIGHT_MULTIPLIERS[ctx.seriesId] ?? 1.0;
    const weight = roleWeight * seriesMultiplier;
    
    const normalizedPressure = ctx.pressure * weight;
    
    components.push({
      seriesId: ctx.seriesId,
      displayName: ctx.displayName,
      role: ctx.role,
      weight: Math.round(weight * 1000) / 1000,
      rawPressure: ctx.pressure,
      normalizedPressure: Math.round(normalizedPressure * 1000) / 1000,
      regime: ctx.regime,
    });
    
    totalWeight += weight;
    weightedSum += normalizedPressure;
  }
  
  // Normalize to -1..+1
  const scoreSigned = totalWeight > 0 ? weightedSum / totalWeight : 0;
  
  // Convert to 0..1 (0 = max risk-on, 1 = max risk-off)
  const score01 = (scoreSigned + 1) / 2;
  
  // Quality assessment
  const freshCount = contexts.filter(c => c.quality.freshness === 'FRESH').length;
  const staleCount = contexts.filter(c => c.quality.freshness === 'STALE').length;
  const avgCoverage = contexts.reduce((sum, c) => sum + c.quality.coverage, 0) / contexts.length;
  
  // Quality penalty (reduces confidence)
  let qualityPenalty = 0;
  if (staleCount > 2) qualityPenalty += 0.1 * (staleCount - 2);
  if (avgCoverage < 30) qualityPenalty += 0.1;
  qualityPenalty = Math.min(0.5, qualityPenalty);
  
  // Confidence
  const { confidence, confidenceReasons } = computeConfidence(
    contexts.length,
    freshCount,
    staleCount,
    qualityPenalty
  );
  
  // Summary
  const summary = buildSummary(components, contexts);
  
  return {
    score01: Math.round(score01 * 1000) / 1000,
    scoreSigned: Math.round(scoreSigned * 1000) / 1000,
    confidence,
    confidenceReasons,
    quality: {
      seriesCount: contexts.length,
      freshCount,
      staleCount,
      avgCoverage: Math.round(avgCoverage * 10) / 10,
      qualityPenalty: Math.round(qualityPenalty * 1000) / 1000,
    },
    components,
    summary,
    computedAt: new Date().toISOString(),
  };
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════

function computeConfidence(
  seriesCount: number,
  freshCount: number,
  staleCount: number,
  qualityPenalty: number
): { confidence: MacroConfidence; confidenceReasons: string[] } {
  const reasons: string[] = [];
  
  // Start with HIGH confidence
  let level = 3;  // 3=HIGH, 2=MEDIUM, 1=LOW
  
  // Check series count
  if (seriesCount < 5) {
    level = Math.min(level, 1);
    reasons.push(`Only ${seriesCount} series available (need 5+)`);
  } else if (seriesCount < 7) {
    level = Math.min(level, 2);
    reasons.push(`${seriesCount} series available (optimal: 7+)`);
  }
  
  // Check freshness
  if (freshCount < 4) {
    level = Math.min(level, 2);
    reasons.push(`Only ${freshCount} series are fresh`);
  }
  
  // Check quality penalty
  if (qualityPenalty > 0.2) {
    level = Math.min(level, 1);
    reasons.push(`High quality penalty: ${(qualityPenalty * 100).toFixed(0)}%`);
  } else if (qualityPenalty > 0.1) {
    level = Math.min(level, 2);
    reasons.push(`Moderate quality penalty: ${(qualityPenalty * 100).toFixed(0)}%`);
  }
  
  if (reasons.length === 0) {
    reasons.push('All quality checks passed');
  }
  
  const confidence: MacroConfidence = 
    level >= 3 ? 'HIGH' : 
    level >= 2 ? 'MEDIUM' : 
    'LOW';
  
  return { confidence, confidenceReasons: reasons };
}

function buildSummary(
  components: MacroScoreComponent[],
  contexts: MacroContext[]
): { dominantRegime: string; dominantRole: MacroRole; keyDrivers: string[] } {
  // Find dominant regime (most frequent)
  const regimeCounts: Record<string, number> = {};
  for (const c of components) {
    const r = String(c.regime);
    regimeCounts[r] = (regimeCounts[r] || 0) + 1;
  }
  const dominantRegime = Object.entries(regimeCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || 'UNKNOWN';
  
  // Find dominant role (highest absolute pressure contribution)
  const rolePressure: Record<MacroRole, number> = {} as any;
  for (const c of components) {
    rolePressure[c.role] = (rolePressure[c.role] || 0) + Math.abs(c.normalizedPressure);
  }
  const dominantRole = Object.entries(rolePressure)
    .sort((a, b) => b[1] - a[1])[0]?.[0] as MacroRole || 'rates';
  
  // Key drivers (top 3 by absolute pressure)
  const keyDrivers = components
    .sort((a, b) => Math.abs(b.normalizedPressure) - Math.abs(a.normalizedPressure))
    .slice(0, 3)
    .map(c => `${c.displayName}: ${c.regime} (${c.rawPressure > 0 ? '+' : ''}${c.rawPressure})`);
  
  return { dominantRegime, dominantRole, keyDrivers };
}

function buildEmptyScore(): MacroScore {
  return {
    score01: 0.5,
    scoreSigned: 0,
    confidence: 'LOW',
    confidenceReasons: ['No macro data available'],
    quality: {
      seriesCount: 0,
      freshCount: 0,
      staleCount: 0,
      avgCoverage: 0,
      qualityPenalty: 1,
    },
    components: [],
    summary: {
      dominantRegime: 'UNKNOWN',
      dominantRole: 'rates',
      keyDrivers: [],
    },
    computedAt: new Date().toISOString(),
  };
}
