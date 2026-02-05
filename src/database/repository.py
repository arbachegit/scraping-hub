"""
Repository layer - Data persistence
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog

from .client import get_supabase

logger = structlog.get_logger()


class CompanyRepository:
    """
    Repository for company data persistence
    Stores and retrieves company analyses
    """

    TABLE_NAME = "companies"
    ANALYSIS_TABLE = "company_analyses"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        """Check if database is available"""
        return self.client is not None

    async def save_company(self, company_data: Dict[str, Any]) -> Optional[str]:
        """
        Save or update company data
        Returns company ID
        """
        if not self._is_available():
            logger.warning("db_not_available_save")
            return None

        try:
            # Prepare data
            record = {
                "name": company_data.get("name") or company_data.get("nome_fantasia"),
                "nome_fantasia": company_data.get("nome_fantasia"),
                "razao_social": company_data.get("razao_social"),
                "cnpj": company_data.get("cnpj"),
                "website": company_data.get("website"),
                "industry": company_data.get("industry"),
                "description": company_data.get("description"),
                "linkedin_url": company_data.get("linkedin_url"),
                "raw_data": json.dumps(company_data, default=str, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Upsert by name or CNPJ
            if company_data.get("cnpj"):
                result = self.client.table(self.TABLE_NAME).upsert(
                    record,
                    on_conflict="cnpj"
                ).execute()
            else:
                # Try to find existing by name
                existing = self.client.table(self.TABLE_NAME).select("id").eq(
                    "name", record["name"]
                ).execute()

                if existing.data:
                    record["id"] = existing.data[0]["id"]

                result = self.client.table(self.TABLE_NAME).upsert(record).execute()

            if result.data:
                logger.info("company_saved", name=record["name"])
                return result.data[0].get("id")

        except Exception as e:
            logger.error("company_save_error", error=str(e))

        return None

    async def get_company(
        self,
        name: Optional[str] = None,
        cnpj: Optional[str] = None,
        max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get company from database
        Returns None if not found or too old
        """
        if not self._is_available():
            return None

        try:
            query = self.client.table(self.TABLE_NAME).select("*")

            if cnpj:
                query = query.eq("cnpj", cnpj)
            elif name:
                query = query.ilike("name", f"%{name}%")
            else:
                return None

            result = query.limit(1).execute()

            if not result.data:
                return None

            record = result.data[0]

            # Check age
            updated_at = datetime.fromisoformat(record["updated_at"].replace("Z", ""))
            if datetime.utcnow() - updated_at > timedelta(hours=max_age_hours):
                logger.info("company_data_stale", name=name)
                return None

            # Parse raw_data
            if record.get("raw_data"):
                record["cached_data"] = json.loads(record["raw_data"])

            logger.info("company_cache_hit", name=name)
            return record

        except Exception as e:
            logger.error("company_get_error", error=str(e))

        return None

    async def save_analysis(
        self,
        company_id: str,
        analysis_type: str,
        analysis_data: Dict[str, Any]
    ) -> bool:
        """Save company analysis (SWOT, OKRs, etc)"""
        if not self._is_available():
            return False

        try:
            record = {
                "company_id": company_id,
                "analysis_type": analysis_type,
                "swot": json.dumps(analysis_data.get("swot_analysis"), default=str) if analysis_data.get("swot_analysis") else None,
                "okrs": json.dumps(analysis_data.get("suggested_okrs"), default=str) if analysis_data.get("suggested_okrs") else None,
                "competitors": json.dumps(analysis_data.get("competitors"), default=str) if analysis_data.get("competitors") else None,
                "key_people": json.dumps(analysis_data.get("key_people"), default=str) if analysis_data.get("key_people") else None,
                "raw_analysis": json.dumps(analysis_data, default=str, ensure_ascii=False),
                "created_at": datetime.utcnow().isoformat()
            }

            self.client.table(self.ANALYSIS_TABLE).insert(record).execute()
            logger.info("analysis_saved", company_id=company_id, type=analysis_type)
            return True

        except Exception as e:
            logger.error("analysis_save_error", error=str(e))
            return False

    async def get_latest_analysis(
        self,
        company_id: str,
        analysis_type: str = "client",
        max_age_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """Get latest analysis for company"""
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.ANALYSIS_TABLE).select("*").eq(
                "company_id", company_id
            ).eq(
                "analysis_type", analysis_type
            ).order(
                "created_at", desc=True
            ).limit(1).execute()

            if not result.data:
                return None

            record = result.data[0]

            # Check age
            created_at = datetime.fromisoformat(record["created_at"].replace("Z", ""))
            if datetime.utcnow() - created_at > timedelta(hours=max_age_hours):
                return None

            # Parse JSON fields
            if record.get("raw_analysis"):
                return json.loads(record["raw_analysis"])

        except Exception as e:
            logger.error("analysis_get_error", error=str(e))

        return None


class SearchRepository:
    """
    Repository for search history and caching
    """

    TABLE_NAME = "search_cache"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def cache_search(
        self,
        search_type: str,
        query: str,
        result: Dict[str, Any],
        ttl_hours: int = 24
    ) -> bool:
        """Cache a search result"""
        if not self._is_available():
            return False

        try:
            record = {
                "search_type": search_type,
                "query": query.lower().strip(),
                "result": json.dumps(result, default=str, ensure_ascii=False),
                "expires_at": (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }

            self.client.table(self.TABLE_NAME).upsert(
                record,
                on_conflict="search_type,query"
            ).execute()

            return True

        except Exception as e:
            logger.error("cache_save_error", error=str(e))
            return False

    async def get_cached_search(
        self,
        search_type: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached search result if not expired"""
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "search_type", search_type
            ).eq(
                "query", query.lower().strip()
            ).limit(1).execute()

            if not result.data:
                return None

            record = result.data[0]

            # Check expiration
            expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", ""))
            if datetime.utcnow() > expires_at:
                return None

            return json.loads(record["result"])

        except Exception as e:
            logger.error("cache_get_error", error=str(e))

        return None
