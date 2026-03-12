"""
Emendas Subnacionais Collector
Coleta emendas estaduais e municipais de portais de transparência.

Phase 1 Sources:
  - GO Estado: CKAN DataStore API (dadosabertos.go.gov.br)
  - MG Estado: ALMG CSV (mediaserver.almg.gov.br)
  - RJ Capital: Transparência Prefeitura (XLSX)
  - SP Capital: CKAN ODS (dados.prefeitura.sp.gov.br)

Usage:
  python -m scheduler.emendas_subnacionais_collector --source go_estado
  python -m scheduler.emendas_subnacionais_collector --source all
  python -m scheduler.emendas_subnacionais_collector --source go_estado --dry-run
"""

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog
from supabase import Client, create_client

from config.settings import settings

logger = structlog.get_logger()

# =============================================
# SOURCE DEFINITIONS
# =============================================

SOURCES = {
    'go_estado': {
        'name': 'Goiás Estado - Portal de Dados Abertos',
        'esfera': 'estadual',
        'uf': 'GO',
        'municipio': None,
        'url': 'https://dadosabertos.go.gov.br/api/3/action/datastore_search',
        'resource_id': 'da303bdf-8c77-4368-a5c6-ffb6dba4a364',
        'format': 'ckan_json',
    },
    'mg_estado': {
        'name': 'Minas Gerais Estado - ALMG',
        'esfera': 'estadual',
        'uf': 'MG',
        'municipio': None,
        'url': 'https://mediaserver.almg.gov.br/acervo/497/469/2497469.csv',
        'format': 'csv',
    },
    'rj_capital': {
        'name': 'Rio de Janeiro Capital - Transparência',
        'esfera': 'municipal',
        'uf': 'RJ',
        'municipio': 'Rio de Janeiro',
        'codigo_ibge': '3304557',
        'url': 'https://transparencia.prefeitura.rio/wp-content/uploads/sites/100/2023/07/Emendas-Pix-2025-3.xlsx',
        'format': 'xlsx',
    },
    'sp_capital': {
        'name': 'São Paulo Capital - Portal de Dados Abertos',
        'esfera': 'municipal',
        'uf': 'SP',
        'municipio': 'São Paulo',
        'codigo_ibge': '3550308',
        'url': 'https://dados.prefeitura.sp.gov.br/api/3/action/datastore_search',
        'format': 'ckan_json',
        'note': 'Limited to SMADS (social assistance)',
    },
}

# Data source registration for compliance (fontes_dados table)
DATA_SOURCE_REGISTRATIONS = {
    'go_estado': {
        'nome': 'Portal de Dados Abertos de Goiás - Emendas Parlamentares',
        'categoria': 'politico',
        'fonte_primaria': 'Assembleia Legislativa de Goiás',
        'url': 'https://dadosabertos.go.gov.br',
        'formato': 'JSON',
        'api_key_necessaria': False,
        'confiabilidade': 'alta',
        'cobertura_temporal': '2019-presente',
        'observacoes': 'CKAN DataStore API - Emendas parlamentares estaduais de Goiás',
    },
    'mg_estado': {
        'nome': 'ALMG - Emendas Parlamentares de Minas Gerais',
        'categoria': 'politico',
        'fonte_primaria': 'Assembleia Legislativa de Minas Gerais',
        'url': 'https://mediaserver.almg.gov.br',
        'formato': 'CSV',
        'api_key_necessaria': False,
        'confiabilidade': 'alta',
        'cobertura_temporal': '2019-presente',
        'observacoes': 'CSV direto do servidor da ALMG - atualização bimestral',
    },
    'rj_capital': {
        'nome': 'Transparência Rio - Emendas Impositivas PIX',
        'categoria': 'politico',
        'fonte_primaria': 'Prefeitura do Rio de Janeiro',
        'url': 'https://transparencia.prefeitura.rio',
        'formato': 'XLSX',
        'api_key_necessaria': False,
        'confiabilidade': 'alta',
        'cobertura_temporal': '2022-presente',
        'observacoes': 'Planilha XLSX com emendas impositivas PIX da Câmara Municipal do Rio',
    },
    'sp_capital': {
        'nome': 'Portal de Dados Abertos SP - Emendas SMADS',
        'categoria': 'politico',
        'fonte_primaria': 'Prefeitura de São Paulo',
        'url': 'https://dados.prefeitura.sp.gov.br',
        'formato': 'ODS/JSON',
        'api_key_necessaria': False,
        'confiabilidade': 'alta',
        'cobertura_temporal': '2021-presente',
        'observacoes': 'CKAN API - Emendas parlamentares da SMADS (assistência social)',
    },
}


class EmendasSubnacionaisCollector:
    """Collector for subnational parliamentary amendments."""

    def __init__(self):
        self._bdh: Optional[Client] = None
        if settings.has_brasil_data_hub:
            self._bdh = create_client(
                settings.brasil_data_hub_url,
                settings.brasil_data_hub_key,
            )
        self._main_supabase: Optional[Client] = None
        if settings.has_supabase:
            self._main_supabase = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
        self._http = httpx.AsyncClient(
            timeout=60.0,
            headers={
                'User-Agent': 'IconsAI-Collector/1.0 (scraping.iconsai.ai)',
            },
        )
        self._stats = {
            'fetched': 0,
            'inserted': 0,
            'skipped': 0,
            'errors': 0,
        }

    async def close(self):
        await self._http.aclose()

    # =============================================
    # MAIN ENTRY POINTS
    # =============================================

    async def collect_source(self, source_key: str, dry_run: bool = False) -> Dict[str, Any]:
        """Collect emendas from a single source."""
        if source_key not in SOURCES:
            raise ValueError(f"Unknown source: {source_key}. Available: {list(SOURCES.keys())}")

        source = SOURCES[source_key]
        logger.info('collect_source_start', source=source_key, name=source['name'])

        self._stats = {'fetched': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

        try:
            # Dispatch to appropriate collector
            if source['format'] == 'ckan_json':
                records = await self._collect_ckan(source_key, source)
            elif source['format'] == 'csv':
                records = await self._collect_csv(source_key, source)
            elif source['format'] == 'xlsx':
                records = await self._collect_xlsx(source_key, source)
            else:
                raise ValueError(f"Unsupported format: {source['format']}")

            self._stats['fetched'] = len(records)
            logger.info('records_fetched', source=source_key, count=len(records))

            if not dry_run and self._bdh and records:
                await self._upsert_records(records)

            # Register data source for compliance
            if not dry_run and self._bdh and source_key in DATA_SOURCE_REGISTRATIONS:
                await self._register_source(source_key)

        except Exception as e:
            logger.error('collect_source_error', source=source_key, error=str(e))
            self._stats['errors'] += 1

        result = {
            'source': source_key,
            'name': source['name'],
            'dry_run': dry_run,
            **self._stats,
        }
        logger.info('collect_source_complete', **result)
        return result

    async def collect_all(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Collect emendas from all configured sources."""
        results = []
        for source_key in SOURCES:
            try:
                result = await self.collect_source(source_key, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                logger.error('collect_all_source_error', source=source_key, error=str(e))
                results.append({'source': source_key, 'error': str(e)})
            # Rate limiting between sources
            await asyncio.sleep(2)
        return results

    # =============================================
    # COLLECTORS BY FORMAT
    # =============================================

    async def _collect_ckan(self, source_key: str, source: dict) -> List[dict]:
        """Collect from CKAN DataStore API with pagination."""
        records = []
        offset = 0
        limit = 1000  # CKAN default page size

        while True:
            params = {
                'resource_id': source['resource_id'],
                'limit': limit,
                'offset': offset,
            }

            resp = await self._http.get(source['url'], params=params)
            resp.raise_for_status()
            data = resp.json()

            result = data.get('result', {})
            raw_records = result.get('records', [])

            if not raw_records:
                break

            for raw in raw_records:
                record = self._normalize_ckan_go(raw, source) if source_key == 'go_estado' else self._normalize_ckan_sp(raw, source)
                if record:
                    records.append(record)

            total = result.get('total', 0)
            offset += limit

            logger.debug('ckan_page_fetched', source=source_key, offset=offset, total=total, page_records=len(raw_records))

            if offset >= total:
                break

            await asyncio.sleep(0.5)

        return records

    async def _collect_csv(self, source_key: str, source: dict) -> List[dict]:
        """Collect from direct CSV download."""
        resp = await self._http.get(source['url'])
        resp.raise_for_status()

        # Detect encoding (ALMG uses latin-1 typically)
        content = resp.content
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')

        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        records = []

        for row in reader:
            record = self._normalize_mg(row, source)
            if record:
                records.append(record)

        return records

    async def _collect_xlsx(self, source_key: str, source: dict) -> List[dict]:
        """Collect from XLSX download (requires openpyxl)."""
        try:
            import openpyxl
        except ImportError:
            logger.error('openpyxl_not_installed', hint='pip install openpyxl')
            return []

        resp = await self._http.get(source['url'])
        resp.raise_for_status()

        wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True)
        ws = wb.active
        records = []

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        # Find header row (first row where multiple cells have text values)
        header_idx = 0
        for i, row in enumerate(rows):
            non_none = sum(1 for v in row if v is not None)
            if non_none >= 5:
                header_idx = i
                break

        headers = [str(h).strip().lower() if h else f'col_{i}' for i, h in enumerate(rows[header_idx])]

        for row in rows[header_idx + 1:]:
            # Skip empty rows or rows with all None/asterisk
            if all(v is None or str(v).strip() == '*' for v in row):
                continue
            row_dict = dict(zip(headers, row))
            record = self._normalize_rj(row_dict, source)
            if record:
                records.append(record)

        wb.close()
        return records

    # =============================================
    # NORMALIZERS (raw → standard schema)
    # =============================================

    def _normalize_ckan_go(self, raw: dict, source: dict) -> Optional[dict]:
        """Normalize CKAN record from GO Portal de Dados Abertos."""
        try:
            # GO CKAN columns: Deputado, Partido, NEmenda, Valor, FuncaoProgramatica, etc.
            autor = raw.get('Deputado') or raw.get('deputado') or raw.get('DEPUTADO', '')
            partido = raw.get('Partido') or raw.get('partido') or raw.get('PARTIDO', '')
            numero = raw.get('NEmenda') or raw.get('nemenda') or raw.get('NEMENDA', '')
            valor_str = raw.get('Valor') or raw.get('valor') or raw.get('VALOR', '0')
            descricao = raw.get('DescricaoEmenda') or raw.get('descricaoemenda') or raw.get('Descricao') or ''
            funcao = raw.get('FuncaoProgramatica') or raw.get('funcaoprogramatica') or ''
            ano_raw = raw.get('Ano') or raw.get('ano') or raw.get('ANO')
            beneficiario = raw.get('Beneficiario') or raw.get('beneficiario') or ''

            # Parse valor
            valor = self._parse_valor(valor_str)
            ano = int(ano_raw) if ano_raw else datetime.now().year

            # Generate unique code — use _id from CKAN if available
            _id = raw.get('_id', '')
            if numero:
                codigo = f"GO-{numero}-{ano}"
            elif _id:
                codigo = f"GO-{_id}"
            else:
                # Fallback: hash of all identifying fields
                import hashlib
                h = hashlib.md5(f"{autor}{descricao}{valor_str}{beneficiario}".encode()).hexdigest()[:10]
                codigo = f"GO-{h}-{ano}"

            return {
                'codigo_emenda': codigo,
                'numero_emenda': str(numero) if numero else None,
                'esfera': source['esfera'],
                'uf': source['uf'],
                'municipio': source.get('municipio'),
                'codigo_ibge': source.get('codigo_ibge'),
                'autor': autor.strip() if autor else None,
                'partido': partido.strip() if partido else None,
                'tipo_autor': 'deputado_estadual',
                'tipo': 'individual',
                'descricao': descricao.strip() if descricao else None,
                'funcao': funcao.strip() if funcao else None,
                'beneficiario': beneficiario.strip() if beneficiario else None,
                'ano': ano,
                'valor_aprovado': valor,
                'fonte': 'go_ckan',
                'fonte_url': source['url'],
                'dados_extras': json.dumps({k: str(v) for k, v in raw.items() if v}),
            }
        except Exception as e:
            logger.warning('normalize_go_error', error=str(e), raw_keys=list(raw.keys()))
            return None

    def _normalize_ckan_sp(self, raw: dict, source: dict) -> Optional[dict]:
        """Normalize CKAN record from SP Portal de Dados Abertos."""
        try:
            autor = raw.get('Autor') or raw.get('autor') or raw.get('Parlamentar') or ''
            numero = raw.get('Emenda') or raw.get('emenda') or raw.get('NumeroEmenda') or ''
            valor_str = raw.get('Valor') or raw.get('valor') or '0'
            descricao = raw.get('Objeto') or raw.get('objeto') or raw.get('Descricao') or ''
            ano_raw = raw.get('Ano') or raw.get('ano')

            valor = self._parse_valor(valor_str)
            ano = int(ano_raw) if ano_raw else datetime.now().year

            codigo = f"SP-MUN-{numero}-{ano}" if numero else f"SP-MUN-{autor[:20]}-{ano}-{hash(descricao) % 10000}"

            return {
                'codigo_emenda': codigo,
                'numero_emenda': str(numero) if numero else None,
                'esfera': source['esfera'],
                'uf': source['uf'],
                'municipio': source['municipio'],
                'codigo_ibge': source.get('codigo_ibge'),
                'autor': autor.strip() if autor else None,
                'tipo_autor': 'vereador',
                'tipo': 'individual',
                'descricao': descricao.strip() if descricao else None,
                'ano': ano,
                'valor_aprovado': valor,
                'fonte': 'sp_ckan',
                'fonte_url': source['url'],
                'dados_extras': json.dumps({k: str(v) for k, v in raw.items() if v}),
            }
        except Exception as e:
            logger.warning('normalize_sp_error', error=str(e))
            return None

    def _normalize_mg(self, raw: dict, source: dict) -> Optional[dict]:
        """Normalize CSV record from ALMG (Minas Gerais).

        Real ALMG columns:
        'Ano da Indicação', 'Número da Indicação', 'Indicador de Impositividade',
        'Tipo de Indicação', 'Status da Indicação', 'Autor', 'Tipo de autoria',
        'Função Descrição', 'Descrição da Indicação', 'Município ',
        'Nome Beneficiário', 'Número do CNPJ do Beneficiário',
        'Valor Indicado', 'Valor Utilizado', 'Valor Empenhado no Ano', 'Valor Pago Atualizado'
        """
        try:
            autor = raw.get('Autor', '').strip()
            numero = raw.get('Número da Indicação', '').strip()
            ano_raw = raw.get('Ano da Indicação', '')
            tipo_autoria = raw.get('Tipo de autoria', '').strip()
            tipo_indicacao = raw.get('Tipo de Indicação', '').strip()
            descricao = raw.get('Descrição da Indicação', '').strip()
            funcao = raw.get('Função Descrição', '').strip()
            municipio_destino = raw.get('Município ', '').strip()  # Note: trailing space in header
            beneficiario = raw.get('Nome Beneficiário', '').strip()
            cnpj_benef = raw.get('Número do CNPJ do Beneficiário', '').strip()
            natureza = raw.get('Grupo de Despesa Descrição', '').strip()

            valor_indicado = self._parse_valor(raw.get('Valor Indicado', '0'))
            valor_empenhado = self._parse_valor(raw.get('Valor Empenhado no Ano', '0'))
            valor_pago = self._parse_valor(raw.get('Valor Pago Atualizado', '0'))

            ano = int(ano_raw) if ano_raw else datetime.now().year

            if not numero:
                return None  # Skip rows without identification

            codigo = f"MG-{numero}-{ano}"

            return {
                'codigo_emenda': codigo,
                'numero_emenda': numero,
                'esfera': source['esfera'],
                'uf': source['uf'],
                'municipio': municipio_destino if municipio_destino else None,
                'codigo_ibge': source.get('codigo_ibge'),
                'autor': autor if autor else None,
                'partido': None,  # Not in ALMG CSV
                'tipo_autor': 'deputado_estadual' if tipo_autoria == 'INDIVIDUAL' else tipo_autoria.lower() if tipo_autoria else 'deputado_estadual',
                'tipo': tipo_indicacao.lower() if tipo_indicacao else 'individual',
                'descricao': descricao if descricao else None,
                'funcao': funcao if funcao else None,
                'natureza_despesa': natureza if natureza else None,
                'beneficiario': beneficiario if beneficiario else None,
                'cnpj_beneficiario': cnpj_benef if cnpj_benef else None,
                'ano': ano,
                'valor_aprovado': valor_indicado,
                'valor_empenhado': valor_empenhado,
                'valor_pago': valor_pago,
                'fonte': 'mg_almg',
                'fonte_url': source['url'],
                'dados_extras': json.dumps({
                    'status': raw.get('Status da Indicação', ''),
                    'impositiva': raw.get('Indicador de Impositividade', ''),
                    'unidade_orcamentaria': raw.get('Unidade Orçamentária Descrição', ''),
                    'macrorregiao': raw.get('Macrorregião de Planejamento', ''),
                }),
            }
        except Exception as e:
            logger.warning('normalize_mg_error', error=str(e))
            return None

    def _normalize_rj(self, raw: dict, source: dict) -> Optional[dict]:
        """Normalize XLSX record from RJ Transparência.

        Real RJ XLSX columns (row 6 is header):
        'transferência especial - ano', 'nº emenda', 'parlamentar', 'gnd',
        'valor total da emenda', 'código da unidade', 'órgão', 'objeto',
        'ano \nempenho', 'empenho', 'valor\nempenho', 'empresa',
        'liquidado', 'pago', 'cnpj'
        """
        try:
            autor = raw.get('parlamentar', '')
            numero = raw.get('nº emenda', '') or raw.get('n\u00ba emenda', '')
            valor_total_str = raw.get('valor total da emenda', '0')
            descricao = raw.get('objeto', '')
            orgao = raw.get('órgão', '') or raw.get('\u00f3rg\u00e3o', '')
            gnd = raw.get('gnd', '')  # Grupo Natureza Despesa
            ano_raw = raw.get('transferência especial - ano', '') or raw.get('transfer\u00eancia especial - ano', '')
            empresa = raw.get('empresa', '')
            cnpj = raw.get('cnpj', '')
            valor_empenho_str = raw.get('valor\nempenho', '0')
            liquidado_str = raw.get('liquidado', '0')
            pago_str = raw.get('pago', '0')

            if not autor or str(autor).strip() == '*':
                return None

            valor_total = self._parse_valor(valor_total_str)
            valor_empenho = self._parse_valor(valor_empenho_str)
            valor_liquidado = self._parse_valor(liquidado_str)
            valor_pago = self._parse_valor(pago_str)
            ano = int(float(str(ano_raw))) if ano_raw else 2025

            numero_str = str(numero).strip() if numero else ''
            codigo = f"RJ-MUN-{numero_str}-{ano}" if numero_str else f"RJ-MUN-{str(autor)[:20]}-{ano}"

            return {
                'codigo_emenda': codigo,
                'numero_emenda': numero_str if numero_str else None,
                'esfera': source['esfera'],
                'uf': source['uf'],
                'municipio': source['municipio'],
                'codigo_ibge': source.get('codigo_ibge'),
                'autor': str(autor).strip(),
                'tipo_autor': 'parlamentar_federal',  # These are federal transfers to Rio
                'tipo': 'transferencia_especial',
                'descricao': str(descricao).strip() if descricao else None,
                'natureza_despesa': str(gnd).strip() if gnd else None,
                'beneficiario': str(empresa).strip() if empresa and str(empresa) != '*' else None,
                'cnpj_beneficiario': str(cnpj).strip() if cnpj and str(cnpj) != '*' else None,
                'ano': ano,
                'valor_aprovado': valor_total,
                'valor_empenhado': valor_empenho,
                'valor_liquidado': valor_liquidado,
                'valor_pago': valor_pago,
                'fonte': 'rj_transparencia',
                'fonte_url': source['url'],
                'dados_extras': json.dumps({
                    'orgao': str(orgao) if orgao else None,
                }),
            }
        except Exception as e:
            logger.warning('normalize_rj_error', error=str(e))
            return None

    # =============================================
    # HELPERS
    # =============================================

    def _parse_valor(self, val: Any) -> Optional[float]:
        """Parse Brazilian currency value to float."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s or s == '0':
            return 0.0
        # Remove R$, spaces
        s = s.replace('R$', '').replace(' ', '').strip()
        # Brazilian format: 1.234.567,89 → 1234567.89
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return None

    async def _upsert_records(self, records: List[dict]):
        """Upsert records into fato_emendas_subnacionais in batches."""
        # Deduplicate by unique key (fonte, codigo_emenda, ano) — keep last occurrence
        seen = {}
        for r in records:
            key = (r.get('fonte'), r.get('codigo_emenda'), r.get('ano'))
            seen[key] = r
        records = list(seen.values())
        logger.info('records_deduplicated', original=len(records) + (len(records) - len(seen)), unique=len(records))

        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            try:
                result = (
                    self._bdh.table('fato_emendas_subnacionais')
                    .upsert(batch, on_conflict='fonte,codigo_emenda,ano')
                    .execute()
                )
                inserted = len(result.data) if result.data else 0
                self._stats['inserted'] += inserted
                logger.info('batch_upserted', batch=i // batch_size + 1, count=inserted)
            except Exception as e:
                self._stats['errors'] += len(batch)
                logger.error('batch_upsert_error', batch=i // batch_size + 1, error=str(e))

    async def _register_source(self, source_key: str):
        """Register data source in fontes_dados for compliance (main Supabase instance)."""
        reg = DATA_SOURCE_REGISTRATIONS.get(source_key)
        if not reg or not self._main_supabase:
            return
        try:
            self._main_supabase.table('fontes_dados').upsert(
                {
                    **reg,
                    'data_primeira_coleta': datetime.now().isoformat(),
                    'data_ultima_atualizacao': datetime.now().isoformat(),
                    'periodicidade': 'mensal',
                },
                on_conflict='nome',
            ).execute()
            logger.info('source_registered', source=source_key)
        except Exception as e:
            logger.warning('source_registration_failed', source=source_key, error=str(e))


# =============================================
# CLI
# =============================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='IconsAI - Emendas Subnacionais Collector'
    )
    parser.add_argument(
        '--source',
        type=str,
        choices=list(SOURCES.keys()) + ['all'],
        required=True,
        help='Source to collect from (or "all" for all sources)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not save to database',
    )
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List all available sources and exit',
    )

    args = parser.parse_args()

    if args.list_sources:
        print('\nAvailable sources:')
        print('-' * 60)
        for key, src in SOURCES.items():
            print(f"  {key:15s}  {src['name']}")
            print(f"  {'':15s}  Esfera: {src['esfera']} | UF: {src['uf']} | Format: {src['format']}")
            print()
        return

    collector = EmendasSubnacionaisCollector()

    try:
        if args.source == 'all':
            results = await collector.collect_all(dry_run=args.dry_run)
            print('\n=== Collection Summary ===')
            total_fetched = 0
            total_inserted = 0
            for r in results:
                status = f"fetched={r.get('fetched', 0)}, inserted={r.get('inserted', 0)}"
                if r.get('error'):
                    status = f"ERROR: {r['error']}"
                print(f"  {r['source']:15s}  {status}")
                total_fetched += r.get('fetched', 0)
                total_inserted += r.get('inserted', 0)
            print(f"\n  TOTAL: fetched={total_fetched}, inserted={total_inserted}")
        else:
            result = await collector.collect_source(args.source, dry_run=args.dry_run)
            print(f"\nResult: {json.dumps(result, indent=2)}")
    finally:
        await collector.close()


if __name__ == '__main__':
    asyncio.run(main())
