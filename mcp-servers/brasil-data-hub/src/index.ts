#!/usr/bin/env node
/**
 * Brasil Data Hub MCP Server
 *
 * Provides access to politicians and mandates data from brasil-data-hub Supabase.
 * Following /skill-mcp-guardrails for security and rate limiting.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load environment variables
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../../.env') });

import {
  listPoliticosInputSchema,
  getPoliticoInputSchema,
  listMandatosInputSchema,
  getMandatoInputSchema,
  searchPoliticosInputSchema,
} from './schemas.js';
import * as db from './database.js';

// ============================================
// MCP GUARDRAILS
// ============================================

const RATE_LIMIT_WINDOW_MS = 60_000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 100;
const requestCounts = new Map<string, { count: number; resetTime: number }>();

function checkRateLimit(toolName: string): boolean {
  const now = Date.now();
  const key = toolName;

  const record = requestCounts.get(key);
  if (!record || now > record.resetTime) {
    requestCounts.set(key, { count: 1, resetTime: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (record.count >= RATE_LIMIT_MAX_REQUESTS) {
    return false;
  }

  record.count++;
  return true;
}

// ============================================
// TOOL DEFINITIONS
// ============================================

const TOOLS: Tool[] = [
  {
    name: 'list_politicos',
    description:
      'Lista políticos do Brasil com filtros opcionais. Retorna dados do dim_politicos.',
    inputSchema: {
      type: 'object',
      properties: {
        nome: {
          type: 'string',
          description: 'Filtrar por nome (busca parcial)',
          maxLength: 200,
        },
        partido: {
          type: 'string',
          description: 'Filtrar por sigla do partido',
          maxLength: 50,
        },
        uf: {
          type: 'string',
          description: 'Filtrar por UF de nascimento (2 letras)',
          maxLength: 2,
        },
        cargo: {
          type: 'string',
          description: 'Filtrar por cargo atual',
          maxLength: 100,
        },
        limit: {
          type: 'number',
          description: 'Número máximo de resultados (default: 50, max: 500)',
          default: 50,
        },
        offset: {
          type: 'number',
          description: 'Offset para paginação (default: 0)',
          default: 0,
        },
      },
    },
  },
  {
    name: 'get_politico',
    description:
      'Busca um político específico por ID, incluindo todos os seus mandatos.',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'UUID do político',
          format: 'uuid',
        },
      },
      required: ['id'],
    },
  },
  {
    name: 'search_politicos',
    description:
      'Busca políticos por nome (busca fuzzy em nome_completo e nome_urna).',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Termo de busca (mínimo 2 caracteres)',
          minLength: 2,
          maxLength: 200,
        },
        limit: {
          type: 'number',
          description: 'Número máximo de resultados (default: 20, max: 100)',
          default: 20,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'list_mandatos',
    description:
      'Lista mandatos de políticos com filtros opcionais. Retorna dados do fato_politicos_mandatos.',
    inputSchema: {
      type: 'object',
      properties: {
        politico_id: {
          type: 'string',
          description: 'Filtrar por UUID do político',
          format: 'uuid',
        },
        legislatura: {
          type: 'number',
          description: 'Filtrar por número da legislatura',
        },
        cargo: {
          type: 'string',
          description: 'Filtrar por cargo (busca parcial)',
          maxLength: 100,
        },
        uf: {
          type: 'string',
          description: 'Filtrar por UF do mandato (2 letras)',
          maxLength: 2,
        },
        situacao: {
          type: 'string',
          description: 'Filtrar por situação: ativo, inativo, todos',
          enum: ['ativo', 'inativo', 'todos'],
          default: 'todos',
        },
        limit: {
          type: 'number',
          description: 'Número máximo de resultados (default: 50, max: 500)',
          default: 50,
        },
        offset: {
          type: 'number',
          description: 'Offset para paginação (default: 0)',
          default: 0,
        },
      },
    },
  },
  {
    name: 'get_mandato',
    description: 'Busca um mandato específico por ID.',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'UUID do mandato',
          format: 'uuid',
        },
      },
      required: ['id'],
    },
  },
  {
    name: 'get_stats',
    description: 'Retorna estatísticas: total de políticos e mandatos.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

// ============================================
// SERVER SETUP
// ============================================

const server = new Server(
  {
    name: 'brasil-data-hub-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Rate limit check
  if (!checkRateLimit(name)) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            error: 'Rate limit exceeded. Try again in 1 minute.',
          }),
        },
      ],
      isError: true,
    };
  }

  try {
    let result: unknown;

    switch (name) {
      case 'list_politicos': {
        const input = listPoliticosInputSchema.parse(args);
        result = await db.listPoliticos(input);
        break;
      }

      case 'get_politico': {
        const input = getPoliticoInputSchema.parse(args);
        result = await db.getPoliticoComMandatos(input.id);
        if (!result) {
          return {
            content: [
              { type: 'text', text: JSON.stringify({ error: 'Político não encontrado' }) },
            ],
            isError: true,
          };
        }
        break;
      }

      case 'search_politicos': {
        const input = searchPoliticosInputSchema.parse(args);
        result = await db.searchPoliticos(input.query, input.limit);
        break;
      }

      case 'list_mandatos': {
        const input = listMandatosInputSchema.parse(args);
        result = await db.listMandatos(input);
        break;
      }

      case 'get_mandato': {
        const input = getMandatoInputSchema.parse(args);
        result = await db.getMandato(input.id);
        if (!result) {
          return {
            content: [
              { type: 'text', text: JSON.stringify({ error: 'Mandato não encontrado' }) },
            ],
            isError: true,
          };
        }
        break;
      }

      case 'get_stats': {
        result = await db.getStats();
        break;
      }

      default:
        return {
          content: [
            { type: 'text', text: JSON.stringify({ error: `Unknown tool: ${name}` }) },
          ],
          isError: true,
        };
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[MCP] Error in ${name}:`, message);
    return {
      content: [{ type: 'text', text: JSON.stringify({ error: message }) }],
      isError: true,
    };
  }
});

// ============================================
// START SERVER
// ============================================

async function main() {
  console.error('[brasil-data-hub-mcp] Starting server...');

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('[brasil-data-hub-mcp] Server running on stdio');
}

main().catch((error) => {
  console.error('[brasil-data-hub-mcp] Fatal error:', error);
  process.exit(1);
});
