import { Router } from 'express';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';

const router = Router();

/**
 * GET /stats
 * Returns counts for all main entities
 */
router.get('/', async (req, res) => {
  try {
    // Run all counts in parallel
    const [empresas, pessoas, politicos, mandatos, noticias] = await Promise.all([
      supabase.from('dim_empresas').select('id', { count: 'exact', head: true }),
      supabase.from('dim_pessoas').select('id', { count: 'exact', head: true }),
      supabase.from('dim_politicos').select('id', { count: 'exact', head: true }),
      supabase.from('fato_mandatos').select('id', { count: 'exact', head: true }),
      supabase.from('fato_noticias').select('id', { count: 'exact', head: true }),
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
