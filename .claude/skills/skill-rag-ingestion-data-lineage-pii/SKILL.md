# Skill: RAG Ingestion Data Lineage and PII

Auditor de pipeline RAG ingestion (ETL/chunk/embedding) para avaliar normalizacao de dados e governanca ISO 27701.

## Camada

**Camada 4** - RAG Ingestion (ETL, chunking, embeddings)

## Quando Usar

- Pipelines de ingestao de documentos
- Processamento de chunks
- Geracao de embeddings
- ETL para bases vetoriais

## Regras Inviolaveis

1. **Identificacao Estavel**: Cada documento tem:
   - `doc_id` estavel (UUID ou hash)
   - `content_hash` (SHA256 do conteudo)
   - `source` (origem)
   - `ingested_at` (timestamp)

2. **Chunking Versionado**: Chunking deve ser rastreavel:
   - `chunker_version` (ex: "recursive-v1.2")
   - Parametros documentados (chunk_size, overlap)
   - Chunk IDs deterministicos

3. **Embeddings Versionados**: Embeddings reproduziveis:
   - `embed_model` (ex: "text-embedding-3-small")
   - `embed_version` (ex: "2024-01")
   - Mesmo input = mesmo output

4. **PII Handling**: Detectar/remover/mascarar PII antes de indexar:
   - Emails mascarados
   - CPF/CNPJ removidos ou mascarados
   - Nomes proprios conforme classificacao

5. **Metadados Obrigatorios no Vetor**:
   - `classification` (publico/interno/confidencial)
   - `tenant` (multi-tenant)
   - `source`
   - `doc_hash`
   - `schema_version`

6. **Logs sem PII**: Logs com trilha de auditoria mas sem dados sensiveis.

## Exemplo de Implementacao Correta

```python
import hashlib
from datetime import datetime
from typing import List
from pydantic import BaseModel
import structlog
import re

logger = structlog.get_logger()

# Versoes do pipeline
CHUNKER_VERSION = "recursive-v1.2"
EMBED_MODEL = "text-embedding-3-small"
EMBED_VERSION = "2024-01"
SCHEMA_VERSION = "1.0.0"

class DocumentMetadata(BaseModel):
    doc_id: str
    content_hash: str
    source: str
    source_url: str | None
    classification: str  # publico, interno, confidencial, sensivel
    tenant: str
    ingested_at: datetime
    chunker_version: str
    embed_model: str
    embed_version: str
    schema_version: str

class ChunkMetadata(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_index: int
    content_hash: str
    # Herda metadados do documento
    classification: str
    tenant: str

def compute_hash(content: str) -> str:
    """Hash deterministico do conteudo"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def compute_chunk_id(doc_id: str, chunk_index: int, content_hash: str) -> str:
    """ID deterministico do chunk"""
    return hashlib.sha256(
        f"{doc_id}:{chunk_index}:{content_hash}".encode()
    ).hexdigest()[:16]

# PII Detection e Masking
PII_PATTERNS = {
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'cpf': r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}',
    'cnpj': r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}',
    'telefone': r'\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}'
}

def mask_pii(text: str, classification: str) -> str:
    """Remove/mascara PII conforme classificacao"""
    if classification in ['publico', 'interno']:
        for pii_type, pattern in PII_PATTERNS.items():
            text = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', text)
    return text

def should_scrub_pii(classification: str) -> bool:
    """Define se deve remover PII baseado na classificacao"""
    return classification in ['publico', 'interno']

async def ingest_document(
    content: str,
    source: str,
    source_url: str,
    classification: str,
    tenant: str,
    request_id: str
):
    log = logger.bind(request_id=request_id)

    # 1. Gerar metadados do documento
    content_hash = compute_hash(content)
    doc_id = f"doc_{content_hash[:16]}"

    metadata = DocumentMetadata(
        doc_id=doc_id,
        content_hash=content_hash,
        source=source,
        source_url=source_url,
        classification=classification,
        tenant=tenant,
        ingested_at=datetime.utcnow(),
        chunker_version=CHUNKER_VERSION,
        embed_model=EMBED_MODEL,
        embed_version=EMBED_VERSION,
        schema_version=SCHEMA_VERSION
    )

    log.info("Documento recebido", doc_id=doc_id, source=source)

    # 2. PII Handling
    if should_scrub_pii(classification):
        content = mask_pii(content, classification)
        log.info("PII mascarado", doc_id=doc_id)

    # 3. Chunking
    chunks = chunk_document(content, chunk_size=1000, overlap=200)

    # 4. Processar cada chunk
    chunk_records = []
    for i, chunk_text in enumerate(chunks):
        chunk_hash = compute_hash(chunk_text)
        chunk_id = compute_chunk_id(doc_id, i, chunk_hash)

        chunk_meta = ChunkMetadata(
            chunk_id=chunk_id,
            doc_id=doc_id,
            chunk_index=i,
            content_hash=chunk_hash,
            classification=classification,
            tenant=tenant
        )

        # 5. Gerar embedding
        embedding = await generate_embedding(chunk_text)

        chunk_records.append({
            "id": chunk_id,
            "content": chunk_text,
            "embedding": embedding,
            "metadata": chunk_meta.model_dump()
        })

    # 6. Persistir com metadados completos
    await vector_store.upsert(chunk_records)

    log.info("Documento indexado",
        doc_id=doc_id,
        chunks=len(chunk_records),
        classification=classification
        # NAO logar conteudo ou PII
    )

    return {
        "doc_id": doc_id,
        "chunks_created": len(chunk_records),
        "content_hash": content_hash
    }
```

## Checklist de Auditoria

- [ ] Documentos tem `doc_id` estavel e `content_hash`
- [ ] `source` e `ingested_at` registrados
- [ ] `chunker_version` documentado
- [ ] Parametros de chunking rastreavels
- [ ] `embed_model` e `embed_version` registrados
- [ ] PII detectado e mascarado conforme classificacao
- [ ] Metadados obrigatorios no vetor (classification, tenant, source, doc_hash)
- [ ] `schema_version` presente
- [ ] Logs sem PII e com trilha de auditoria

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
