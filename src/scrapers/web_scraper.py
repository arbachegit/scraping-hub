"""
Web Scraper Client
Scraping genérico de websites com suporte a JavaScript
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from bs4.element import Tag

logger = structlog.get_logger()


def _get_attr(tag: Tag, attr: str, default: str = "") -> str:
    """Extrai atributo de tag BeautifulSoup de forma type-safe"""
    value = tag.get(attr)
    if value is None:
        return default
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


class WebScraperClient:
    """
    Cliente para scraping genérico de websites

    Funcionalidades:
    - Scraping de conteúdo HTML
    - Extração de texto e metadados
    - Extração de links
    - Parsing de dados estruturados
    """

    # Metadados da fonte para rastreabilidade (CLAUDE.md)
    SOURCE_NAME = "Web Scraper - HTML"
    SOURCE_PROVIDER = "Web Scraping"
    SOURCE_CATEGORY = "scraping"
    SOURCE_COVERAGE = "Conteúdo HTML de websites"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._registered_urls: set = set()

        # Estatísticas
        self.stats = {"requests": 0, "success": 0, "errors": 0}

    async def _register_source_usage(self, url: str) -> None:
        """
        Registra uso da fonte de dados (website raspado).

        Conforme CLAUDE.md: ALWAYS registrar fontes de dados.
        """
        # Evitar registrar mesmo domínio múltiplas vezes
        domain = urlparse(url).netloc
        if domain in self._registered_urls:
            return

        try:
            from src.database.fontes_repository import registrar_fonte_scraping

            await registrar_fonte_scraping(
                nome=f"Website - {domain}", site=domain, url=url, cobertura="Conteúdo HTML extraído"
            )

            self._registered_urls.add(domain)
            logger.debug("scraping_source_registered", domain=domain)

        except Exception as e:
            logger.warning("scraping_source_registration_failed", error=str(e))

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy client initialization"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
        return self._client

    async def close(self):
        """Fecha o cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str) -> Optional[str]:
        """
        Faz fetch de uma URL

        Args:
            url: URL para buscar

        Returns:
            HTML da página ou None
        """
        self.stats["requests"] += 1

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            self.stats["success"] += 1
            return response.text

        except Exception as e:
            self.stats["errors"] += 1
            logger.error("web_scraper_fetch_error", url=url, error=str(e))
            return None

    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Faz scrape completo de uma URL

        Args:
            url: URL para fazer scrape

        Returns:
            Dados extraídos da página
        """
        logger.info("web_scraper_scrape", url=url)

        html = await self.fetch(url)
        if not html:
            return {"error": "Failed to fetch URL", "url": url}

        # Registrar uso da fonte (CLAUDE.md compliance)
        await self._register_source_usage(url)

        soup = BeautifulSoup(html, "html.parser")

        # Extrair metadados
        metadata = self._extract_metadata(soup, url)

        # Extrair conteúdo principal
        content = self._extract_content(soup)

        # Extrair links
        links = self._extract_links(soup, url)

        # Extrair dados estruturados
        structured_data = self._extract_structured_data(soup)

        return {
            "url": url,
            "metadata": metadata,
            "content": content,
            "links": links,
            "structured_data": structured_data,
        }

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrai metadados da página"""
        metadata = {"url": url, "domain": urlparse(url).netloc}

        # Título
        title_tag = soup.find("title")
        metadata["title"] = title_tag.get_text(strip=True) if title_tag else None

        # Meta tags
        for meta in soup.find_all("meta"):
            if not isinstance(meta, Tag):
                continue
            name = _get_attr(meta, "name").lower() or _get_attr(meta, "property").lower()
            content = _get_attr(meta, "content")

            if name == "description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = [k.strip() for k in content.split(",")]
            elif name == "author":
                metadata["author"] = content
            elif name == "og:title":
                metadata["og_title"] = content
            elif name == "og:description":
                metadata["og_description"] = content
            elif name == "og:image":
                metadata["og_image"] = content
            elif name == "og:type":
                metadata["og_type"] = content

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and isinstance(canonical, Tag):
            metadata["canonical_url"] = _get_attr(canonical, "href")

        # Favicon
        favicon = soup.find("link", rel=lambda x: x and "icon" in str(x))
        if favicon and isinstance(favicon, Tag):
            href = _get_attr(favicon, "href")
            if href:
                metadata["favicon"] = urljoin(url, href)

        # Idioma
        html_tag = soup.find("html")
        if html_tag and isinstance(html_tag, Tag):
            metadata["language"] = _get_attr(html_tag, "lang")

        return metadata

    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai conteúdo principal da página"""
        # Remover elementos não desejados
        for element in soup.find_all(
            ["script", "style", "nav", "header", "footer", "aside", "noscript"]
        ):
            element.decompose()

        # Tentar encontrar conteúdo principal
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|main|body", re.I))
            or soup.find("div", id=re.compile(r"content|main|body", re.I))
            or soup.body
        )

        if not main_content:
            return {"text": "", "html": ""}

        # Extrair texto
        text = main_content.get_text(separator="\n", strip=True)

        # Limpar texto
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        # Extrair headings
        headings = []
        for h in main_content.find_all(["h1", "h2", "h3"]):
            headings.append({"level": int(h.name[1]), "text": h.get_text(strip=True)})

        # Extrair parágrafos
        paragraphs = [
            p.get_text(strip=True)
            for p in main_content.find_all("p")
            if len(p.get_text(strip=True)) > 50
        ]

        # Extrair listas
        lists = []
        for ul in main_content.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            if items:
                lists.append(items)

        return {
            "text": text[:50000],  # Limitar tamanho
            "headings": headings,
            "paragraphs": paragraphs[:20],
            "lists": lists[:10],
            "word_count": len(text.split()),
        }

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extrai links da página"""
        internal_links = set()
        external_links = set()
        social_links = {}

        base_domain = urlparse(base_url).netloc

        social_patterns = {
            "linkedin": r"linkedin\.com",
            "twitter": r"twitter\.com|x\.com",
            "facebook": r"facebook\.com",
            "instagram": r"instagram\.com",
            "youtube": r"youtube\.com",
            "github": r"github\.com",
        }

        for a in soup.find_all("a", href=True):
            if not isinstance(a, Tag):
                continue
            href = _get_attr(a, "href")

            # Ignorar links vazios ou javascript
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Converter para URL absoluta
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Verificar se é link social
            for platform, pattern in social_patterns.items():
                if re.search(pattern, full_url, re.I):
                    social_links[platform] = full_url
                    break
            else:
                # Classificar como interno ou externo
                if parsed.netloc == base_domain:
                    internal_links.add(full_url)
                else:
                    external_links.add(full_url)

        return {
            "internal": list(internal_links)[:50],
            "external": list(external_links)[:50],
            "social": social_links,
        }

    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai dados estruturados (JSON-LD, Schema.org)"""
        structured_data = []

        # JSON-LD
        import json

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if script.string:
                    data = json.loads(script.string)
                    structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        return structured_data

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA EMPRESAS
    # ===========================================

    async def scrape_company_website(self, url: str) -> Dict[str, Any]:
        """
        Faz scrape do website de uma empresa

        Args:
            url: URL do website

        Returns:
            Dados extraídos
        """
        result = await self.scrape(url)

        if "error" in result:
            return result

        # Enriquecer com análise específica para empresas
        metadata = result.get("metadata", {})
        content = result.get("content", {})
        links = result.get("links", {})

        # Tentar encontrar páginas importantes
        important_pages = {
            "about": None,
            "contact": None,
            "products": None,
            "services": None,
            "team": None,
            "careers": None,
        }

        for link in links.get("internal", []):
            link_lower = link.lower()
            for page_type in important_pages:
                if page_type in link_lower or self._get_page_synonym(page_type) in link_lower:
                    important_pages[page_type] = link
                    break

        return {
            "url": url,
            "company_name": self._extract_company_name(metadata, content),
            "description": metadata.get("description") or metadata.get("og_description"),
            "content_summary": content.get("text", "")[:2000],
            "headings": content.get("headings", []),
            "social_media": links.get("social", {}),
            "important_pages": important_pages,
            "contact_info": self._extract_contact_info(content.get("text", "")),
            "technologies": self._detect_technologies(result),
            "metadata": metadata,
        }

    def _get_page_synonym(self, page_type: str) -> str:
        """Retorna sinônimos em português"""
        synonyms = {
            "about": "sobre",
            "contact": "contato",
            "products": "produtos",
            "services": "servicos",
            "team": "equipe",
            "careers": "carreiras",
        }
        return synonyms.get(page_type, page_type)

    def _extract_company_name(self, metadata: Dict, content: Dict) -> Optional[str]:
        """Extrai nome da empresa"""
        # Tentar do título
        title = metadata.get("title", "")
        if title:
            # Remover sufixos comuns
            for suffix in [" - Home", " | Home", " - Página Inicial", " | Official"]:
                if suffix in title:
                    return title.split(suffix)[0].strip()
            return title.split("|")[0].split("-")[0].strip()

        # Tentar do OG title
        og_title = metadata.get("og_title")
        if og_title:
            return og_title

        return None

    def _extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extrai informações de contato do texto"""
        contact = {}

        # Email
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        emails = re.findall(email_pattern, text)
        if emails:
            contact["emails"] = list(set(emails))[:5]

        # Telefone brasileiro
        phone_pattern = r"\(?\d{2}\)?\s*\d{4,5}[-.\s]?\d{4}"
        phones = re.findall(phone_pattern, text)
        if phones:
            contact["phones"] = list(set(phones))[:5]

        # CNPJ
        cnpj_pattern = r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"
        cnpjs = re.findall(cnpj_pattern, text)
        if cnpjs:
            contact["cnpj"] = cnpjs[0]

        # CEP
        cep_pattern = r"\d{5}-?\d{3}"
        ceps = re.findall(cep_pattern, text)
        if ceps:
            contact["ceps"] = list(set(ceps))[:3]

        return contact

    def _detect_technologies(self, scrape_result: Dict) -> List[str]:
        """Detecta tecnologias usadas no site"""
        technologies = set()

        # Verificar dados estruturados
        for data in scrape_result.get("structured_data", []):
            if isinstance(data, dict):
                if "@type" in data:
                    technologies.add(f"Schema.org/{data['@type']}")

        # Verificar links externos para CDNs conhecidas
        external_links = scrape_result.get("links", {}).get("external", [])
        for link in external_links:
            if "googleapis.com" in link or "gstatic.com" in link:
                technologies.add("Google APIs")
            elif "cloudflare" in link:
                technologies.add("Cloudflare")
            elif "amazonaws.com" in link or "aws" in link:
                technologies.add("AWS")
            elif "jsdelivr" in link or "cdnjs" in link:
                technologies.add("CDN")

        return list(technologies)

    # ===========================================
    # MÉTODOS UTILITÁRIOS
    # ===========================================

    async def get_page_text(self, url: str) -> str:
        """
        Retorna apenas o texto de uma página

        Args:
            url: URL da página

        Returns:
            Texto extraído
        """
        result = await self.scrape(url)
        return result.get("content", {}).get("text", "")

    async def get_all_links(self, url: str) -> List[str]:
        """
        Retorna todos os links de uma página

        Args:
            url: URL da página

        Returns:
            Lista de links
        """
        result = await self.scrape(url)
        links = result.get("links", {})
        return links.get("internal", []) + links.get("external", [])

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso"""
        return {
            **self.stats,
            "success_rate": (
                (self.stats["success"] / self.stats["requests"] * 100)
                if self.stats["requests"] > 0
                else 0
            ),
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
