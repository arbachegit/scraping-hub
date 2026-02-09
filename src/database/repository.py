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
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Upsert by name or CNPJ
            if company_data.get("cnpj"):
                result = (
                    self.client.table(self.TABLE_NAME).upsert(record, on_conflict="cnpj").execute()
                )
            else:
                # Try to find existing by name
                existing = (
                    self.client.table(self.TABLE_NAME)
                    .select("id")
                    .eq("name", record["name"])
                    .execute()
                )

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
        self, name: Optional[str] = None, cnpj: Optional[str] = None, max_age_hours: int = 24
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
        self, company_id: str, analysis_type: str, analysis_data: Dict[str, Any]
    ) -> bool:
        """Save company analysis (SWOT, OKRs, etc)"""
        if not self._is_available():
            return False

        try:
            record = {
                "company_id": company_id,
                "analysis_type": analysis_type,
                "swot": json.dumps(analysis_data.get("swot_analysis"), default=str)
                if analysis_data.get("swot_analysis")
                else None,
                "okrs": json.dumps(analysis_data.get("suggested_okrs"), default=str)
                if analysis_data.get("suggested_okrs")
                else None,
                "competitors": json.dumps(analysis_data.get("competitors"), default=str)
                if analysis_data.get("competitors")
                else None,
                "key_people": json.dumps(analysis_data.get("key_people"), default=str)
                if analysis_data.get("key_people")
                else None,
                "raw_analysis": json.dumps(analysis_data, default=str, ensure_ascii=False),
                "created_at": datetime.utcnow().isoformat(),
            }

            self.client.table(self.ANALYSIS_TABLE).insert(record).execute()
            logger.info("analysis_saved", company_id=company_id, type=analysis_type)
            return True

        except Exception as e:
            logger.error("analysis_save_error", error=str(e))
            return False

    async def get_latest_analysis(
        self, company_id: str, analysis_type: str = "client", max_age_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """Get latest analysis for company"""
        if not self._is_available():
            return None

        try:
            result = (
                self.client.table(self.ANALYSIS_TABLE)
                .select("*")
                .eq("company_id", company_id)
                .eq("analysis_type", analysis_type)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

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


class PeopleRepository:
    """
    Repository for people data persistence
    Stores and retrieves people profiles and analyses
    """

    TABLE_NAME = "people"
    ANALYSIS_TABLE = "people_analyses"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save_person(self, person_data: Dict[str, Any]) -> Optional[str]:
        """Save or update person data. Returns person ID."""
        if not self._is_available():
            logger.warning("db_not_available_save_person")
            return None

        try:
            record = {
                "full_name": person_data.get("name") or person_data.get("full_name"),
                "person_type": person_data.get("person_type", "professional"),
                "current_title": person_data.get("title") or person_data.get("current_title"),
                "current_company": person_data.get("company") or person_data.get("current_company"),
                "linkedin_url": person_data.get("linkedin_url"),
                "twitter_url": person_data.get("twitter_url"),
                "instagram_url": person_data.get("instagram_url"),
                "email": person_data.get("email"),
                "phone": person_data.get("phone"),
                "city": person_data.get("city"),
                "state": person_data.get("state"),
                "country": person_data.get("country", "Brasil"),
                "seniority": person_data.get("seniority"),
                "photo_url": person_data.get("photo_url"),
                "bio": person_data.get("professional_summary") or person_data.get("bio"),
                "raw_data": json.dumps(person_data, default=str, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            # Try to find existing by name
            existing = (
                self.client.table(self.TABLE_NAME)
                .select("id")
                .eq("full_name", record["full_name"])
                .eq("person_type", record.get("person_type", "professional"))
                .execute()
            )

            if existing.data:
                record["id"] = existing.data[0]["id"]

            result = self.client.table(self.TABLE_NAME).upsert(record).execute()

            if result.data:
                logger.info("person_saved", name=record["full_name"])
                return result.data[0].get("id")

        except Exception as e:
            logger.error("person_save_error", error=str(e))

        return None

    async def get_person(
        self, name: str, person_type: str = "professional", max_age_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """Get person from database"""
        if not self._is_available():
            return None

        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .ilike("full_name", f"%{name}%")
                .eq("person_type", person_type)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            record = result.data[0]

            # Check age
            updated_at = datetime.fromisoformat(record["updated_at"].replace("Z", ""))
            if datetime.utcnow() - updated_at > timedelta(hours=max_age_hours):
                logger.info("person_data_stale", name=name)
                return None

            if record.get("raw_data"):
                record["cached_data"] = json.loads(record["raw_data"])

            logger.info("person_cache_hit", name=name)
            return record

        except Exception as e:
            logger.error("person_get_error", error=str(e))

        return None

    async def save_analysis(
        self, person_id: str, analysis_data: Dict[str, Any], company_id: Optional[str] = None
    ) -> bool:
        """Save person analysis"""
        if not self._is_available():
            return False

        try:
            record = {
                "person_id": person_id,
                "company_id": company_id,
                "analysis_type": "profile",
                "strengths": json.dumps(analysis_data.get("strengths"), default=str)
                if analysis_data.get("strengths")
                else None,
                "skills": json.dumps(analysis_data.get("skills_assessment"), default=str)
                if analysis_data.get("skills_assessment")
                else None,
                "career_history": json.dumps(analysis_data.get("career_analysis"), default=str)
                if analysis_data.get("career_analysis")
                else None,
                "fit_analysis": analysis_data.get("professional_summary"),
                "confidence_score": analysis_data.get("confidence_score"),
                "sources": json.dumps(analysis_data.get("sources_used"), default=str)
                if analysis_data.get("sources_used")
                else None,
                "raw_data": json.dumps(analysis_data, default=str, ensure_ascii=False),
                "created_at": datetime.utcnow().isoformat(),
            }

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            self.client.table(self.ANALYSIS_TABLE).insert(record).execute()
            logger.info("person_analysis_saved", person_id=person_id)
            return True

        except Exception as e:
            logger.error("person_analysis_save_error", error=str(e))
            return False

    async def get_latest_analysis(
        self, person_id: str, max_age_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """Get latest analysis for person"""
        if not self._is_available():
            return None

        try:
            result = (
                self.client.table(self.ANALYSIS_TABLE)
                .select("*")
                .eq("person_id", person_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            record = result.data[0]

            created_at = datetime.fromisoformat(record["created_at"].replace("Z", ""))
            if datetime.utcnow() - created_at > timedelta(hours=max_age_hours):
                return None

            if record.get("raw_data"):
                return json.loads(record["raw_data"])

        except Exception as e:
            logger.error("person_analysis_get_error", error=str(e))

        return None


class PoliticianRepository:
    """
    Repository for politician data persistence
    """

    TABLE_NAME = "people"  # Same table, different person_type
    ANALYSIS_TABLE = "people_analyses"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save_politician(self, politician_data: Dict[str, Any]) -> Optional[str]:
        """Save or update politician data. Returns ID."""
        if not self._is_available():
            logger.warning("db_not_available_save_politician")
            return None

        try:
            record = {
                "full_name": politician_data.get("name") or politician_data.get("full_name"),
                "person_type": "politician",
                "political_role": politician_data.get("role")
                or politician_data.get("political_role"),
                "political_party": politician_data.get("party")
                or politician_data.get("political_party"),
                "state": politician_data.get("state"),
                "city": politician_data.get("city"),
                "linkedin_url": politician_data.get("linkedin_url"),
                "twitter_url": politician_data.get("twitter_url"),
                "instagram_url": politician_data.get("instagram_url"),
                "facebook_url": politician_data.get("facebook_url"),
                "email": politician_data.get("email"),
                "phone": politician_data.get("phone"),
                "photo_url": politician_data.get("image") or politician_data.get("photo_url"),
                "bio": politician_data.get("personal_summary")
                or politician_data.get("description"),
                "raw_data": json.dumps(politician_data, default=str, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            # Try to find existing
            existing = (
                self.client.table(self.TABLE_NAME)
                .select("id")
                .eq("full_name", record["full_name"])
                .eq("person_type", "politician")
                .execute()
            )

            if existing.data:
                record["id"] = existing.data[0]["id"]

            result = self.client.table(self.TABLE_NAME).upsert(record).execute()

            if result.data:
                logger.info("politician_saved", name=record["full_name"])
                return result.data[0].get("id")

        except Exception as e:
            logger.error("politician_save_error", error=str(e))

        return None

    async def get_politician(self, name: str, max_age_hours: int = 48) -> Optional[Dict[str, Any]]:
        """Get politician from database"""
        if not self._is_available():
            return None

        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .ilike("full_name", f"%{name}%")
                .eq("person_type", "politician")
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            record = result.data[0]

            updated_at = datetime.fromisoformat(record["updated_at"].replace("Z", ""))
            if datetime.utcnow() - updated_at > timedelta(hours=max_age_hours):
                logger.info("politician_data_stale", name=name)
                return None

            if record.get("raw_data"):
                record["cached_data"] = json.loads(record["raw_data"])

            logger.info("politician_cache_hit", name=name)
            return record

        except Exception as e:
            logger.error("politician_get_error", error=str(e))

        return None

    async def save_analysis(self, politician_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Save politician analysis"""
        if not self._is_available():
            return False

        try:
            record = {
                "person_id": politician_id,
                "analysis_type": "politician_profile",
                "public_perception": json.dumps(analysis_data.get("public_perception"), default=str)
                if analysis_data.get("public_perception")
                else None,
                "controversies": json.dumps(analysis_data.get("controversies"), default=str)
                if analysis_data.get("controversies")
                else None,
                "strengths": json.dumps(analysis_data.get("key_characteristics"), default=str)
                if analysis_data.get("key_characteristics")
                else None,
                "fit_analysis": analysis_data.get("personal_summary"),
                "confidence_score": analysis_data.get("confidence_score"),
                "sources": json.dumps(analysis_data.get("sources_used"), default=str)
                if analysis_data.get("sources_used")
                else None,
                "raw_data": json.dumps(analysis_data, default=str, ensure_ascii=False),
                "created_at": datetime.utcnow().isoformat(),
            }

            record = {k: v for k, v in record.items() if v is not None}

            self.client.table(self.ANALYSIS_TABLE).insert(record).execute()
            logger.info("politician_analysis_saved", politician_id=politician_id)
            return True

        except Exception as e:
            logger.error("politician_analysis_save_error", error=str(e))
            return False


class SearchHistoryRepository:
    """
    Repository for search history - tracks ALL searches
    """

    TABLE_NAME = "search_history"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save_search(
        self,
        search_type: str,
        query: Dict[str, Any],
        user_email: Optional[str] = None,
        results_count: int = 0,
        result_ids: Optional[list] = None,
    ) -> Optional[str]:
        """Save a search to history"""
        if not self._is_available():
            return None

        try:
            record = {
                "search_type": search_type,
                "query": json.dumps(query, default=str, ensure_ascii=False),
                "user_email": user_email,
                "results_count": results_count,
                "result_ids": json.dumps(result_ids) if result_ids else None,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat(),
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("search_saved", type=search_type)
                return result.data[0].get("id")

        except Exception as e:
            logger.error("search_save_error", error=str(e))

        return None

    async def get_user_searches(
        self, user_email: str, search_type: Optional[str] = None, limit: int = 50
    ) -> list:
        """Get user's search history"""
        if not self._is_available():
            return []

        try:
            query = self.client.table(self.TABLE_NAME).select("*").eq("user_email", user_email)

            if search_type:
                query = query.eq("search_type", search_type)

            result = query.order("created_at", desc=True).limit(limit).execute()

            return result.data or []

        except Exception as e:
            logger.error("search_history_get_error", error=str(e))
            return []


class SearchRepository:
    """
    Repository for search result caching
    """

    TABLE_NAME = "search_cache"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def cache_search(
        self, search_type: str, query: str, result: Dict[str, Any], ttl_hours: int = 24
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
                "created_at": datetime.utcnow().isoformat(),
            }

            self.client.table(self.TABLE_NAME).upsert(
                record, on_conflict="search_type,query"
            ).execute()

            return True

        except Exception as e:
            logger.error("cache_save_error", error=str(e))
            return False

    async def get_cached_search(self, search_type: str, query: str) -> Optional[Dict[str, Any]]:
        """Get cached search result if not expired"""
        if not self._is_available():
            return None

        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .eq("search_type", search_type)
                .eq("query", query.lower().strip())
                .limit(1)
                .execute()
            )

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
