# IconsAI Scraping - Web Scraping System

## 🚨 AVISOS CRÍTICOS - PROJETO PROBLEMÁTICO

### Principais Problemas Conhecidos
1. **Scrapers quebram frequentemente** → Sites mudam estrutura HTML
2. **Erros silenciosos** → Scraper falha mas não avisa adequadamente
3. **Falta retry logic** → Uma falha = scraping inteiro falha
4. **Logs insuficientes** → Difícil debugar quando quebra
5. **Código duplicado** → Lógica repetida entre scrapers

### ANTES DE QUALQUER ALTERAÇÃO

```markdown
1. ✅ LER completamente o código existente
2. ✅ RODAR testes antes de mudar qualquer coisa
3. ✅ CRIAR questionário de validação
4. ✅ PERGUNTAR sobre impactos em outros scrapers
5. ✅ NUNCA mudar código que não foi solicitado
```

---

## 📁 ESTRUTURA DO PROJETO

```
iconsai-scraping/
├── src/
│   ├── scrapers/           # Scrapers individuais
│   │   ├── base.py         # BaseScaper (NUNCA MUDAR sem consultar)
│   │   ├── siconfi.py      # SICONFI scraper
│   │   ├── tce.py          # TCE scraper
│   │   └── ...
│   ├── services/
│   │   ├── parser.py       # HTML parsing
│   │   ├── validator.py    # Data validation
│   │   └── storage.py      # DB operations
│   ├── database/
│   │   ├── schema.sql      # Database schema
│   │   └── models.py       # SQLAlchemy models
│   └── utils/
│       ├── retry.py        # Retry logic
│       └── logger.py       # Logging config
├── api/
│   ├── main.py             # FastAPI app
│   └── routes/             # API endpoints
├── tests/
│   ├── test_scrapers.py
│   └── test_api.py
├── config/
│   └── settings.py         # Configurações
└── requirements.txt
```

---

## 🎯 STACK & COMANDOS

### Stack
- **Python 3.11+**
- **FastAPI** (async API)
- **BeautifulSoup4** (HTML parsing)
- **httpx** (async HTTP client)
- **SQLAlchemy** (ORM)
- **Pydantic** (validation)
- **pytest** (testing)

### Comandos Principais
```bash
# Development
uvicorn api.main:app --reload     # Run API dev
python -m src.scrapers.siconfi    # Run scraper direto

# Testing
pytest                            # Run all tests
pytest tests/test_scrapers.py     # Test específico
pytest --cov                      # Com coverage
pytest -v -s                      # Verbose com print

# Linting
ruff check .                      # Check errors
ruff format .                     # Format code
mypy src/                         # Type checking
```

---

## 🚨 REGRAS CRÍTICAS - SCRAPING

### 1. NUNCA Hardcode Seletores CSS
```python
# ❌ ERRADO - Quebrará quando site mudar
def scrape_bad():
    soup = BeautifulSoup(html, 'html.parser')
    data = soup.select_one('#content > div.main > table > tr:nth-child(2)').text
    return data

# ✅ CORRETO - Usar seletores robustos + fallback
def scrape_good():
    soup = BeautifulSoup(html, 'html.parser')
    
    # Tentar múltiplas estratégias
    selectors = [
        ('id', 'data-table'),
        ('class', 'fiscal-data'),
        ('data-testid', 'main-table'),
    ]
    
    for selector_type, selector_value in selectors:
        if selector_type == 'id':
            element = soup.find(id=selector_value)
        elif selector_type == 'class':
            element = soup.find(class_=selector_value)
        elif selector_type == 'data-testid':
            element = soup.find(attrs={'data-testid': selector_value})
        
        if element:
            return element.text.strip()
    
    raise ScrapingError("Nenhum seletor encontrou dados")
```

### 2. SEMPRE Implementar Retry Logic
```python
# ✅ OBRIGATÓRIO em todos os scrapers
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def fetch_with_retry(url: str) -> str:
    """
    Faz requisição com retry automático.
    
    Tentativas: 3
    Backoff: exponencial (4s, 8s, 10s)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
```

### 3. SEMPRE Logar Operações Importantes
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def scrape_siconfi(codigo_ibge: str, exercicio: int):
    """Scrape SICONFI data for município."""
    
    logger.info(
        f"Iniciando scraping SICONFI",
        extra={
            'codigo_ibge': codigo_ibge,
            'exercicio': exercicio,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    
    try:
        url = build_url(codigo_ibge, exercicio)
        logger.debug(f"URL construída: {url}")
        
        html = await fetch_with_retry(url)
        logger.debug(f"HTML recebido: {len(html)} bytes")
        
        data = parse_html(html)
        logger.info(
            f"Scraping concluído com sucesso",
            extra={
                'codigo_ibge': codigo_ibge,
                'records_found': len(data)
            }
        )
        
        return data
        
    except Exception as e:
        logger.error(
            f"Erro no scraping SICONFI",
            extra={
                'codigo_ibge': codigo_ibge,
                'exercicio': exercicio,
                'error': str(e),
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        raise
```

### 4. SEMPRE Validar Dados Extraídos
```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class FiscalData(BaseModel):
    """Dados fiscais validados."""
    
    codigo_ibge: str = Field(..., regex=r'^\d{7}$')
    exercicio: int = Field(..., ge=2015, le=2030)
    rcl: float = Field(..., gt=0)
    despesa_pessoal: float = Field(..., ge=0)
    fonte_url: str = Field(..., min_length=10)
    data_coleta: datetime
    
    @validator('rcl')
    def rcl_must_be_reasonable(cls, v):
        """RCL não pode ser absurdamente alta/baixa."""
        if v > 100_000_000_000:  # 100 bilhões
            raise ValueError('RCL parece incorreta (muito alta)')
        if v < 1_000:  # 1 mil
            raise ValueError('RCL parece incorreta (muito baixa)')
        return v
    
    class Config:
        frozen = True

# Uso no scraper
def parse_and_validate(html: str, codigo_ibge: str) -> FiscalData:
    """Parse HTML e valida dados."""
    raw_data = extract_data_from_html(html)
    
    try:
        validated = FiscalData(
            codigo_ibge=codigo_ibge,
            exercicio=raw_data['ano'],
            rcl=float(raw_data['rcl'].replace('.', '').replace(',', '.')),
            despesa_pessoal=float(raw_data['dp'].replace('.', '').replace(',', '.')),
            fonte_url=raw_data['source_url'],
            data_coleta=datetime.utcnow()
        )
        return validated
    except ValidationError as e:
        logger.error(f"Validation failed for {codigo_ibge}: {e}")
        raise
```

### 5. SEMPRE Registrar Fonte dos Dados
```python
async def scrape_and_save(codigo_ibge: str):
    """Scrape e salva com registro de fonte."""
    
    # 1. Scrape
    data = await scrape_siconfi(codigo_ibge)
    
    # 2. Salvar dados
    await db.save_fiscal_data(data)
    
    # 3. OBRIGATÓRIO: Registrar fonte
    await db.execute(
        """
        INSERT INTO fontes_dados (
            nome,
            categoria,
            fonte_primaria,
            url,
            data_primeira_coleta,
            formato,
            observacoes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (nome, categoria) DO UPDATE
        SET data_ultima_atualizacao = NOW()
        """,
        'SICONFI - RREO',
        'fiscal',
        'Tesouro Nacional',
        f'https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra_municipios.jsf?codigo_ibge={codigo_ibge}',
        datetime.utcnow(),
        'HTML',
        f'Scraping automático para município {codigo_ibge}'
    )
```

---

## 🏗️ PADRÕES DE CÓDIGO

### BaseScaper (TEMPLATE OBRIGATÓRIO)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import httpx
import logging

class BaseScraper(ABC):
    """
    Base class para todos os scrapers.
    
    NUNCA MUDAR sem consultar - todos os scrapers herdam daqui.
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Método principal de scraping.
        
        Deve ser implementado por cada scraper específico.
        """
        pass
    
    @abstractmethod
    def parse_html(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse HTML para dados estruturados.
        
        Deve ser implementado por cada scraper específico.
        """
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch(self, url: str) -> str:
        """Fetch URL com retry automático."""
        self.logger.info(f"Fetching: {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    
    async def scrape_and_save(self, *args, **kwargs):
        """
        Scrape e salva no banco com registro de fonte.
        
        Template method - pode ser sobrescrito se necessário.
        """
        try:
            # 1. Scrape
            data = await self.scrape(*args, **kwargs)
            
            # 2. Validate
            validated_data = [self.validate(item) for item in data]
            
            # 3. Save
            await self.save_to_db(validated_data)
            
            # 4. Register source
            await self.register_data_source(*args, **kwargs)
            
            self.logger.info(f"Successfully scraped {len(validated_data)} records")
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}", exc_info=True)
            raise
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida um registro de dados."""
        pass
    
    @abstractmethod
    async def save_to_db(self, data: List[Dict[str, Any]]):
        """Salva dados no banco."""
        pass
    
    @abstractmethod
    async def register_data_source(self, *args, **kwargs):
        """Registra fonte dos dados na tabela fontes_dados."""
        pass
```

### Exemplo de Scraper Específico

```python
from .base import BaseScraper
from bs4 import BeautifulSoup
from pydantic import BaseModel

class SiconfiRREOScraper(BaseScraper):
    """Scraper para RREO do SICONFI."""
    
    def __init__(self):
        super().__init__(
            base_url='https://siconfi.tesouro.gov.br',
            timeout=60  # RREO pode ser lento
        )
    
    async def scrape(self, codigo_ibge: str, exercicio: int) -> List[Dict]:
        """
        Scrape RREO data.
        
        Args:
            codigo_ibge: Código IBGE 7 dígitos
            exercicio: Ano fiscal
            
        Returns:
            Lista de registros RREO
        """
        url = self._build_url(codigo_ibge, exercicio)
        html = await self.fetch(url)
        return self.parse_html(html)
    
    def parse_html(self, html: str) -> List[Dict]:
        """Parse HTML do SICONFI."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # IMPORTANTE: Usar múltiplas estratégias de seleção
        table = (
            soup.find('table', {'id': 'rreo-table'}) or
            soup.find('table', class_='table-rreo') or
            soup.find('table', attrs={'data-type': 'fiscal'})
        )
        
        if not table:
            raise ScrapingError("Tabela RREO não encontrada - site pode ter mudado")
        
        rows = table.find_all('tr')[1:]  # Skip header
        
        data = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                data.append({
                    'rubrica': cols[0].text.strip(),
                    'valor_previsto': self._parse_currency(cols[1].text),
                    'valor_realizado': self._parse_currency(cols[2].text),
                })
        
        return data
    
    def validate(self, data: Dict) -> Dict:
        """Valida registro RREO."""
        # Usar Pydantic para validação
        class RREORecord(BaseModel):
            rubrica: str
            valor_previsto: float
            valor_realizado: float
        
        return RREORecord(**data).dict()
    
    async def save_to_db(self, data: List[Dict]):
        """Salva RREO no banco."""
        query = """
            INSERT INTO rreo_data (rubrica, valor_previsto, valor_realizado)
            VALUES ($1, $2, $3)
            ON CONFLICT (rubrica) DO UPDATE
            SET valor_realizado = EXCLUDED.valor_realizado
        """
        
        for record in data:
            await db.execute(
                query,
                record['rubrica'],
                record['valor_previsto'],
                record['valor_realizado']
            )
    
    async def register_data_source(self, codigo_ibge: str, exercicio: int):
        """Registra fonte SICONFI."""
        await db.execute(
            """
            INSERT INTO fontes_dados (nome, categoria, fonte_primaria, url, data_primeira_coleta)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT DO NOTHING
            """,
            'SICONFI RREO',
            'fiscal',
            'Tesouro Nacional',
            self._build_url(codigo_ibge, exercicio)
        )
    
    def _build_url(self, codigo_ibge: str, exercicio: int) -> str:
        """Constrói URL do SICONFI."""
        return f"{self.base_url}/siconfi/pages/public/consulta_rreo.jsf?codigo_ibge={codigo_ibge}&exercicio={exercicio}"
    
    def _parse_currency(self, text: str) -> float:
        """Parse valor monetário brasileiro."""
        # Remove R$, pontos de milhar, troca vírgula por ponto
        clean = text.replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(clean)
```

---

## 🧪 TESTES (OBRIGATÓRIO)

### Testes de Scraper

```python
# tests/test_scrapers.py
import pytest
from src.scrapers.siconfi import SiconfiRREOScraper

@pytest.fixture
def mock_html():
    """HTML de exemplo do SICONFI."""
    return """
    <table id="rreo-table">
        <tr><th>Rubrica</th><th>Previsto</th><th>Realizado</th></tr>
        <tr>
            <td>Receita Tributária</td>
            <td>R$ 1.000.000,00</td>
            <td>R$ 950.000,00</td>
        </tr>
    </table>
    """

def test_parse_html(mock_html):
    """Testa parsing do HTML."""
    scraper = SiconfiRREOScraper()
    data = scraper.parse_html(mock_html)
    
    assert len(data) == 1
    assert data[0]['rubrica'] == 'Receita Tributária'
    assert data[0]['valor_previsto'] == 1_000_000.0
    assert data[0]['valor_realizado'] == 950_000.0

def test_parse_currency():
    """Testa conversão de moeda."""
    scraper = SiconfiRREOScraper()
    
    assert scraper._parse_currency('R$ 1.000,00') == 1000.0
    assert scraper._parse_currency('R$ 1.234.567,89') == 1234567.89

@pytest.mark.asyncio
async def test_scrape_with_invalid_codigo_ibge():
    """Testa erro com código IBGE inválido."""
    scraper = SiconfiRREOScraper()
    
    with pytest.raises(ValidationError):
        await scraper.scrape('123', 2024)  # Código curto demais
```

---

## ⚠️ TROUBLESHOOTING

### Problema: Scraper não encontra dados

```python
# DEBUG: Adicionar logs detalhados
soup = BeautifulSoup(html, 'html.parser')

# Salvar HTML para análise
with open(f'debug_{codigo_ibge}.html', 'w') as f:
    f.write(html)

# Listar todos os seletores possíveis
logger.debug("Tables found:", [t.get('id') for t in soup.find_all('table')])
logger.debug("Tables with class:", [t.get('class') for t in soup.find_all('table')])
```

### Problema: Dados extraídos estão incorretos

```python
# VALIDAR os dados imediatamente após parsing
def parse_html(self, html: str):
    data = extract_data(html)
    
    # Sanity checks
    for record in data:
        assert 'rubrica' in record, "Missing rubrica"
        assert isinstance(record['valor'], (int, float)), "Valor not numeric"
        assert record['valor'] >= 0, "Valor negativo"
    
    return data
```

### Problema: Site mudou estrutura

```python
# 1. Salvar HTML atual
# 2. Comparar com HTML anterior (se tiver)
# 3. Identificar o que mudou
# 4. Atualizar seletores CSS
# 5. Adicionar fallback para estrutura antiga (compatibilidade)

def find_table_robust(soup):
    """Tenta múltiplas estratégias."""
    strategies = [
        lambda: soup.find('table', id='rreo-table'),  # Nova estrutura
        lambda: soup.find('table', class_='fiscal-data'),  # Estrutura antiga
        lambda: soup.find('table', attrs={'data-report': 'rreo'}),  # Fallback
    ]
    
    for strategy in strategies:
        try:
            table = strategy()
            if table:
                return table
        except Exception as e:
            logger.debug(f"Strategy failed: {e}")
    
    raise ScrapingError("Table not found with any strategy")
```

---

## 🚀 MELHORIAS PRIORITÁRIAS

### 1. Implementar Circuit Breaker
```python
# TODO: Adicionar circuit breaker para evitar bombardear site que está fora
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def fetch_with_circuit_breaker(url: str):
    """Fetch com circuit breaker."""
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

### 2. Adicionar Cache de HTML
```python
# TODO: Cachear HTML por X horas para evitar scraping desnecessário
import aiofiles
from pathlib import Path

async def fetch_with_cache(url: str, cache_hours: int = 6):
    """Fetch com cache em disco."""
    cache_file = Path(f'cache/{hashlib.md5(url.encode()).hexdigest()}.html')
    
    if cache_file.exists():
        age_hours = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).total_seconds() / 3600
        
        if age_hours < cache_hours:
            async with aiofiles.open(cache_file, 'r') as f:
                return await f.read()
    
    # Cache miss - fetch
    html = await fetch(url)
    
    # Salvar cache
    cache_file.parent.mkdir(exist_ok=True)
    async with aiofiles.open(cache_file, 'w') as f:
        await f.write(html)
    
    return html
```

### 3. Melhorar Logs Estruturados
```python
# TODO: Usar structlog para logs JSON estruturados
import structlog

logger = structlog.get_logger()

logger.info(
    "scraping_started",
    codigo_ibge=codigo_ibge,
    exercicio=exercicio,
    scraper=self.__class__.__name__
)
```

---

## 📋 CHECKLIST ANTES DE COMMIT

```markdown
- [ ] Código segue padrão BaseScraper
- [ ] Implementa retry logic
- [ ] Logs estruturados adicionados
- [ ] Validação Pydantic implementada
- [ ] Fonte de dados registrada em fontes_dados
- [ ] Testes unitários criados
- [ ] Testes passam (pytest)
- [ ] Type hints completos (mypy passa)
- [ ] Linter OK (ruff check)
- [ ] Formatado (ruff format)
- [ ] Documentação atualizada
- [ ] HTML de exemplo salvo (para debugging futuro)
```

---

**Última atualização:** 08/02/2026
**Versão:** 1.0.0
**Status:** PROJETO PROBLEMÁTICO - CUIDADO EXTRA NECESSÁRIO
