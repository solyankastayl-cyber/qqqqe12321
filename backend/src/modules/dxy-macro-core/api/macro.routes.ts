/**
 * MACRO API ROUTES — B1
 * 
 * API endpoints for macro data platform.
 * 
 * ISOLATION: No imports from DXY/BTC/SPX modules
 */

import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import {
  ingestAllMacroSeries,
  ingestMacroSeries,
  getAllSeriesMeta,
  getMacroSeriesPoints,
} from '../ingest/macro.ingest.service.js';
import { buildMacroContext, buildAllMacroContexts } from '../services/macro_context.service.js';
import { computeMacroScore } from '../services/macro_score.service.js';
import { buildHousingContext } from '../services/housing_context.service.js';
import { buildActivityContext } from '../services/activity_context.service.js';
import { buildCreditContext } from '../services/credit_context.service.js';
import { validateStability, validateEpisodes } from '../services/macro_stability_validation.service.js';
import { getDefaultMacroSeries, MACRO_SERIES_REGISTRY } from '../data/macro_sources.registry.js';
import { checkFredHealth, hasFredApiKey } from '../ingest/fred.client.js';

// ═══════════════════════════════════════════════════════════════
// REGISTER ROUTES
// ═══════════════════════════════════════════════════════════════

export async function registerMacroRoutes(fastify: FastifyInstance): Promise<void> {
  const prefix = '/api/dxy-macro-core';
  
  // ─────────────────────────────────────────────────────────────
  // Health check
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/health`, async (req, reply) => {
    const fredHealth = await checkFredHealth();
    const seriesMeta = await getAllSeriesMeta();
    
    return {
      ok: true,
      module: 'dxy-macro-core',
      version: 'B4.3',  // Updated for credit
      fred: {
        ...fredHealth,
        hasApiKey: hasFredApiKey(),
        keyHelp: 'Get free key at https://fred.stlouisfed.org/docs/api/api_key.html',
      },
      seriesLoaded: seriesMeta.length,
      defaultSeries: getDefaultMacroSeries().length,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /series — List all available series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/series`, async (req, reply) => {
    const metas = await getAllSeriesMeta();
    const registry = MACRO_SERIES_REGISTRY;
    
    // Combine registry info with loaded data info
    const series = registry.map(spec => {
      const meta = metas.find(m => m.seriesId === spec.seriesId);
      return {
        seriesId: spec.seriesId,
        displayName: spec.displayName,
        frequency: spec.frequency,
        role: spec.role,
        units: spec.units,
        enabledByDefault: spec.enabledByDefault,
        loaded: !!meta,
        pointCount: meta?.pointCount ?? 0,
        firstDate: meta?.firstDate ?? null,
        lastDate: meta?.lastDate ?? null,
        coverageYears: meta?.coverageYears ?? 0,
      };
    });
    
    return {
      ok: true,
      total: registry.length,
      enabled: registry.filter(s => s.enabledByDefault).length,
      loaded: metas.length,
      series,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /context — Get context for a single series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/context`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as { seriesId?: string };
    const seriesId = query.seriesId;
    
    if (!seriesId) {
      // Return all contexts
      const contexts = await buildAllMacroContexts();
      return {
        ok: true,
        count: contexts.length,
        contexts,
      };
    }
    
    // Single series context
    const context = await buildMacroContext(seriesId);
    
    if (!context) {
      return reply.code(404).send({
        ok: false,
        error: 'NOT_FOUND',
        message: `Series ${seriesId} not found or insufficient data`,
      });
    }
    
    return {
      ok: true,
      context,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /score — Get composite macro score
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/score`, async (req, reply) => {
    const score = await computeMacroScore();
    
    return {
      ok: true,
      score,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /housing — Get housing context (B4.1)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/housing`, async (req, reply) => {
    const housing = await buildHousingContext();
    
    return {
      ok: true,
      housing,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /activity — Get economic activity context (B4.2)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/activity`, async (req, reply) => {
    const activity = await buildActivityContext();
    
    return {
      ok: true,
      activity,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /credit — Get credit & financial stress context (B4.3)
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/credit`, async (req, reply) => {
    const credit = await buildCreditContext();
    
    return {
      ok: true,
      credit,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // GET /history — Get historical data for a series
  // ─────────────────────────────────────────────────────────────
  
  fastify.get(`${prefix}/history`, async (req: FastifyRequest, reply: FastifyReply) => {
    const query = req.query as { seriesId?: string; from?: string; to?: string };
    const { seriesId, from, to } = query;
    
    if (!seriesId) {
      return reply.code(400).send({
        ok: false,
        error: 'MISSING_PARAM',
        message: 'seriesId is required',
      });
    }
    
    const points = await getMacroSeriesPoints(seriesId, from, to);
    
    return {
      ok: true,
      seriesId,
      count: points.length,
      from: points[0]?.date ?? null,
      to: points[points.length - 1]?.date ?? null,
      points,
    };
  });
  
  // ─────────────────────────────────────────────────────────────
  // POST /admin/ingest — Ingest macro data from FRED
  // ─────────────────────────────────────────────────────────────
  
  fastify.post(`${prefix}/admin/ingest`, async (req: FastifyRequest, reply: FastifyReply) => {
    const body = req.body as { series?: string[] } | undefined;
    const seriesIds = body?.series;
    
    console.log(`[Macro API] Ingest request: ${seriesIds?.length ? seriesIds.join(', ') : 'all default'}`);
    
    const result = await ingestAllMacroSeries(seriesIds);
    
    return result;
  });
  
  // ─────────────────────────────────────────────────────────────
  // POST /admin/ingest/:seriesId — Ingest single series
  // ─────────────────────────────────────────────────────────────
  
  fastify.post(`${prefix}/admin/ingest/:seriesId`, async (req: FastifyRequest, reply: FastifyReply) => {
    const params = req.params as { seriesId: string };
    const { seriesId } = params;
    
    console.log(`[Macro API] Single ingest: ${seriesId}`);
    
    const result = await ingestMacroSeries(seriesId);
    
    return result;
  });
  
  console.log(`[Macro] Routes registered at ${prefix}/*`);
}
