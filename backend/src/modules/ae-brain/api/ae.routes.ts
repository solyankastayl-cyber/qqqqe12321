/**
 * AE Brain API Routes
 * 
 * Endpoints:
 * - GET  /api/ae/health
 * - GET  /api/ae/state
 * - GET  /api/ae/regime
 * - GET  /api/ae/causal
 * - GET  /api/ae/scenarios
 * - GET  /api/ae/novelty
 * - GET  /api/ae/terminal
 * - POST /api/ae/admin/snapshot
 */

import { FastifyInstance } from 'fastify';
import { buildAeState } from '../services/ae_state.service.js';
import { classifyRegime } from '../services/ae_regime.service.js';
import { buildCausalGraph } from '../services/ae_causal.service.js';
import { buildScenarios } from '../services/ae_scenarios.service.js';
import { computeNovelty, snapshotState, getNoveltyStats } from '../services/ae_novelty.service.js';
import { buildAeTerminal, getAeBrainHealth } from '../services/ae_terminal.service.js';

export async function registerAeRoutes(fastify: FastifyInstance): Promise<void> {
  
  // ═══════════════════════════════════════════════════════════════
  // HEALTH
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get('/api/ae/health', async (request, reply) => {
    const health = await getAeBrainHealth();
    const noveltyStats = await getNoveltyStats();
    
    return {
      ...health,
      noveltyStats,
    };
  });
  
  // ═══════════════════════════════════════════════════════════════
  // C1: STATE VECTOR
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/state',
    async (request, reply) => {
      const { asOf } = request.query;
      
      try {
        const state = await buildAeState(asOf);
        return { ok: true, ...state };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // C2: REGIME CLASSIFIER
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/regime',
    async (request, reply) => {
      const { asOf } = request.query;
      
      try {
        const state = await buildAeState(asOf);
        const regime = classifyRegime(state);
        return { ok: true, asOf: state.asOf, ...regime };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // C3: CAUSAL GRAPH
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/causal',
    async (request, reply) => {
      const { asOf } = request.query;
      
      try {
        const state = await buildAeState(asOf);
        const causal = buildCausalGraph(state);
        return { ok: true, asOf: state.asOf, ...causal };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // C4: SCENARIOS
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/scenarios',
    async (request, reply) => {
      const { asOf } = request.query;
      
      try {
        const state = await buildAeState(asOf);
        const regime = classifyRegime(state);
        const scenarios = buildScenarios(state, regime);
        return { ok: true, asOf: state.asOf, ...scenarios };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // C5: NOVELTY
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/novelty',
    async (request, reply) => {
      const { asOf } = request.query;
      const today = asOf || new Date().toISOString().split('T')[0];
      
      try {
        const novelty = await computeNovelty(today);
        return { ok: true, asOf: today, ...novelty };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // TERMINAL (MAIN)
  // ═══════════════════════════════════════════════════════════════
  
  fastify.get<{ Querystring: { asOf?: string } }>(
    '/api/ae/terminal',
    async (request, reply) => {
      const { asOf } = request.query;
      
      try {
        const terminal = await buildAeTerminal(asOf);
        return terminal;
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // ADMIN: SNAPSHOT
  // ═══════════════════════════════════════════════════════════════
  
  fastify.post<{ Querystring: { asOf?: string } }>(
    '/api/ae/admin/snapshot',
    async (request, reply) => {
      const { asOf } = request.query;
      const today = asOf || new Date().toISOString().split('T')[0];
      
      try {
        // Build current state
        const state = await buildAeState(today);
        
        // Snapshot to database
        const result = await snapshotState(state);
        
        return {
          ok: result.ok,
          asOf: today,
          created: result.created,
          state: state.vector,
        };
      } catch (e) {
        return reply.status(500).send({
          ok: false,
          error: (e as Error).message,
        });
      }
    }
  );
  
  // ═══════════════════════════════════════════════════════════════
  // ADMIN: BULK SNAPSHOT (for historical backfill)
  // ═══════════════════════════════════════════════════════════════
  
  fastify.post<{ Body: { dates: string[] } }>(
    '/api/ae/admin/snapshot-bulk',
    async (request, reply) => {
      const { dates } = request.body || {};
      
      if (!dates || !Array.isArray(dates) || dates.length === 0) {
        return reply.status(400).send({
          ok: false,
          error: 'dates array required',
        });
      }
      
      const results: Array<{ asOf: string; ok: boolean; created: boolean }> = [];
      
      for (const asOf of dates) {
        try {
          const state = await buildAeState(asOf);
          const result = await snapshotState(state);
          results.push({ asOf, ok: result.ok, created: result.created });
        } catch (e) {
          results.push({ asOf, ok: false, created: false });
        }
      }
      
      return {
        ok: true,
        processed: results.length,
        created: results.filter(r => r.created).length,
        results,
      };
    }
  );
  
  console.log('[AE Brain] Routes registered:');
  console.log('  GET  /api/ae/health');
  console.log('  GET  /api/ae/state');
  console.log('  GET  /api/ae/regime');
  console.log('  GET  /api/ae/causal');
  console.log('  GET  /api/ae/scenarios');
  console.log('  GET  /api/ae/novelty');
  console.log('  GET  /api/ae/terminal');
  console.log('  POST /api/ae/admin/snapshot');
}
