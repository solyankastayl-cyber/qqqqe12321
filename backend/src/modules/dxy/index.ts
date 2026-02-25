/**
 * DXY MODULE INDEX — Main Entry Point
 * 
 * ISOLATION RULE:
 * - MUST NOT import from /modules/btc
 * - MUST NOT import from /modules/spx
 * - Only shared utilities allowed
 * 
 * A4: Added Terminal routes
 */

import { FastifyInstance } from 'fastify';
import { registerDxyChartRoutes } from './api/dxy.chart.routes.js';
import { registerDxyAdminRoutes } from './api/dxy.admin.routes.js';
import { registerDxyFractalRoutes } from './api/dxy.fractal.routes.js';
import { registerDxyForwardRoutes } from './api/dxy.forward.routes.js';
import { registerDxyTerminalRoutes } from './api/dxy.terminal.routes.js';
import { checkDxyIntegrity, ingestFromLocalCsv } from './services/dxy-ingest.service.js';
import fs from 'fs';

// ═══════════════════════════════════════════════════════════════
// COLD START — Auto-load data if missing
// ═══════════════════════════════════════════════════════════════

async function coldStartDxyData(): Promise<void> {
  console.log('[DXY] Cold Start: Checking data availability...');
  
  const integrity = await checkDxyIntegrity();
  console.log(`[DXY] Cold Start: ${integrity.count} candles, ${integrity.coverageYears.toFixed(1)} years`);
  
  if (!integrity.ok) {
    console.log('[DXY] Cold Start: Data insufficient, attempting CSV load...');
    
    const csvPath = '/app/data/dxy_stooq.csv';
    
    if (fs.existsSync(csvPath)) {
      try {
        const result = await ingestFromLocalCsv(csvPath);
        console.log(`[DXY] Cold Start: ✅ Loaded ${result.written} candles from CSV`);
      } catch (err) {
        console.error('[DXY] Cold Start: Failed to load CSV:', err);
      }
    } else {
      console.log(`[DXY] Cold Start: ⚠️ CSV not found at ${csvPath}`);
      console.log('[DXY] Cold Start: Run POST /api/fractal/v2.1/admin/dxy/ingest to fetch data');
    }
  } else {
    console.log('[DXY] Cold Start: ✅ Data OK');
  }
}

// ═══════════════════════════════════════════════════════════════
// REGISTER ALL DXY ROUTES
// ═══════════════════════════════════════════════════════════════

export async function registerDxyModule(fastify: FastifyInstance): Promise<void> {
  console.log('[DXY] ═══════════════════════════════════════════════════════');
  console.log('[DXY] Registering DXY Module v1.1.0 (A4 Terminal)');
  
  // Cold start data check
  await coldStartDxyData();
  
  // Register routes
  await registerDxyChartRoutes(fastify);
  await registerDxyAdminRoutes(fastify);
  await registerDxyFractalRoutes(fastify);
  await registerDxyForwardRoutes(fastify);
  
  // A4: Terminal route (unified API)
  await registerDxyTerminalRoutes(fastify);
  
  console.log('[DXY] ✅ DXY Module v1.1.0 registered successfully');
  console.log('[DXY] ═══════════════════════════════════════════════════════');
}

// Re-export types
export * from './contracts/dxy.types.js';
export * from './contracts/dxy_terminal.contract.js';

// Re-export services for testing
export { checkDxyIntegrity, getDxyMeta } from './services/dxy-ingest.service.js';
export { getDxyChart, getAllDxyCandles } from './services/dxy-chart.service.js';
export { scanDxyFractals } from './services/dxy-scan.service.js';
export { buildDxyFocusPack } from './services/dxy-focus-pack.service.js';
export { buildDxyTerminalPack } from './services/dxy_terminal.service.js';
