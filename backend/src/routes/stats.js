import { Router } from 'express';
import { createClient } from '@supabase/supabase-js';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';

const router = Router();

// Cliente Supabase para brasil-data-hub (políticos e mandatos)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

/**
 * GET /stats
 * Returns counts for all main entities
 * - empresas, pessoas, noticias: from local Supabase
 * - politicos, mandatos: from brasil-data-hub
 */
router.get('/', async (req, res) => {
  try {
    // Local Supabase counts
    const localPromises = [
      supabase.from('dim_empresas').select('id', { count: 'exact', head: true }),
      supabase.from('dim_pessoas').select('id', { count: 'exact', head: true }),
      supabase.from('fato_noticias').select('id', { count: 'exact', head: true }),
    ];

    // Brasil Data Hub counts (if configured)
    const brasilDataHubPromises = brasilDataHub
      ? [
          brasilDataHub.from('dim_politicos').select('id', { count: 'exact', head: true }),
          brasilDataHub.from('fato_politicos_mandatos').select('id', { count: 'exact', head: true }),
        ]
      : [Promise.resolve({ count: 0 }), Promise.resolve({ count: 0 })];

    const [empresas, pessoas, noticias, politicos, mandatos] = await Promise.all([
      ...localPromises,
      ...brasilDataHubPromises,
    ]);

    const stats = {
      empresas: empresas.count || 0,
      pessoas: pessoas.count || 0,
      politicos: politicos.count || 0,
      mandatos: mandatos.count || 0,
      noticias: noticias.count || 0,
    };

    logger.info('Stats fetched', stats);

    res.json({
      success: true,
      stats,
      sources: {
        local: ['empresas', 'pessoas', 'noticias'],
        brasil_data_hub: brasilDataHub ? ['politicos', 'mandatos'] : [],
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    logger.error('Error fetching stats', { error: error.message });
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stats',
    });
  }
});

export default router;
