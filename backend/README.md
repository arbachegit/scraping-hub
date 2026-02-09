# IconsAI Scraping Backend - Node.js

Backend Node.js para o sistema de Business Intelligence Brasil.

## Estrutura

```
backend/
├── src/
│   ├── index.js           # Entry point
│   ├── routes/
│   │   ├── companies.js   # Rotas de empresas
│   │   ├── people.js      # Rotas de pessoas
│   │   └── competitors.js # Rotas de concorrentes
│   ├── services/
│   │   ├── apiClients.js      # Apollo, Serper, Perplexity, BrasilAPI
│   │   ├── peopleService.js   # Busca de pessoas com fallback
│   │   └── competitorService.js # Busca de concorrentes
│   ├── database/
│   │   └── supabase.js    # Cliente e repositories
│   └── utils/
├── package.json
└── README.md
```

## Instalação

```bash
cd backend
npm install
```

## Execução

```bash
# Desenvolvimento (com auto-reload)
npm run dev

# Produção
npm start
```

## Endpoints

### Empresas

- `POST /api/v2/company/analyze-complete` - Análise completa
- `GET /api/v2/company/:id` - Buscar por ID
- `GET /api/v2/company/search?name=` - Buscar por nome

### Pessoas

- `POST /api/v2/people/search` - Buscar pessoas (Apollo → Perplexity → Google)
- `GET /api/v2/people/empresa/:empresaId` - Listar por empresa

### Concorrentes

- `POST /api/v2/competitors/search` - Buscar concorrentes
- `POST /api/v2/competitors/analyze` - Analisar e salvar
- `GET /api/v2/competitors/empresa/:empresaId` - Listar por empresa

## Lógica de Fallback

### Pessoas
1. **Apollo** (LinkedIn) - Fonte primária
2. **Perplexity** - Se Apollo falhar
3. **Google** - Se Perplexity falhar

### Concorrentes
1. **Google** (Serper) - Busca por localização, segmento, porte
2. **Perplexity** - Se Google não retornar resultados

## Variáveis de Ambiente

Usar o mesmo `.env` do projeto principal:

```env
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
APOLLO_API_KEY=...
SERPER_API_KEY=...
PERPLEXITY_API_KEY=...
BACKEND_PORT=3001
```

## Deploy no Droplet

```bash
# Instalar dependências
cd /opt/iconsai-scraping/backend
npm install --production

# Criar serviço systemd
sudo nano /etc/systemd/system/iconsai-scraping-backend.service
```

Conteúdo do serviço:
```ini
[Unit]
Description=IconsAI Scraping Backend Node.js
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/iconsai-scraping/backend
ExecStart=/usr/bin/node src/index.js
Restart=on-failure
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable iconsai-scraping-backend
sudo systemctl start iconsai-scraping-backend
```
