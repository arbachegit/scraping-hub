"""
Dimensional Repository - Data access for fact and dimension tables
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from .client import get_supabase
from .dimensional_client import DimensionalClient, get_date_id, get_time_id

logger = structlog.get_logger()


class FactSearchRepository:
    """Repository for fact_search table"""

    TABLE_NAME = "fact_search"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_search(
        self,
        search_type: str,
        query_text: str,
        user_email: Optional[str] = None,
        query_params: Optional[dict] = None,
        results_count: int = 0,
        processing_time_ms: int = 0,
        credits_used: int = 1,
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """Record a search in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            # Get dimension keys
            user_sk = None
            if user_email:
                user_sk = await self.dim_client.ensure_user_dimension(user_email)

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "user_sk": user_sk,
                "search_type": search_type,
                "query_text": query_text,
                "query_params": json.dumps(query_params) if query_params else "{}",
                "results_count": results_count,
                "processing_time_ms": processing_time_ms,
                "credits_used": credits_used,
                "status": status,
                "error_message": error_message,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("fact_search_recorded", search_type=search_type)
                return result.data[0]["search_id"]

        except Exception as e:
            logger.error("fact_search_error", error=str(e))

        return None


class FactCompanyAnalysisRepository:
    """Repository for fact_company_analysis table"""

    TABLE_NAME = "fact_company_analysis"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_analysis(
        self,
        company_id: str,
        analysis_type: str,
        user_email: Optional[str] = None,
        sources_attempted: int = 0,
        sources_succeeded: int = 0,
        sources_failed: int = 0,
        completeness_score: float = 0,
        confidence_score: float = 0,
        processing_time_ms: int = 0,
        ai_tokens_used: int = 0,
        has_website_data: bool = False,
        has_linkedin_data: bool = False,
        has_news_data: bool = False,
        has_financial_data: bool = False,
        has_cnpj_data: bool = False,
        has_swot: bool = False,
        has_okrs: bool = False,
        has_competitors: bool = False
    ) -> Optional[str]:
        """Record a company analysis in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            # Get dimension keys
            user_sk = None
            if user_email:
                user_sk = await self.dim_client.ensure_user_dimension(user_email)

            company_sk = await self.dim_client.ensure_company_dimension(company_id)

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "user_sk": user_sk,
                "company_sk": company_sk,
                "analysis_type": analysis_type,
                "sources_attempted": sources_attempted,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed,
                "completeness_score": completeness_score,
                "confidence_score": confidence_score,
                "processing_time_ms": processing_time_ms,
                "ai_tokens_used": ai_tokens_used,
                "has_website_data": has_website_data,
                "has_linkedin_data": has_linkedin_data,
                "has_news_data": has_news_data,
                "has_financial_data": has_financial_data,
                "has_cnpj_data": has_cnpj_data,
                "has_swot": has_swot,
                "has_okrs": has_okrs,
                "has_competitors": has_competitors,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("fact_company_analysis_recorded", company_id=company_id)
                return result.data[0]["analysis_id"]

        except Exception as e:
            logger.error("fact_company_analysis_error", error=str(e))

        return None


class FactPersonAnalysisRepository:
    """Repository for fact_person_analysis table"""

    TABLE_NAME = "fact_person_analysis"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_analysis(
        self,
        person_id: str,
        person_type: str,
        analysis_type: str = "profile",
        user_email: Optional[str] = None,
        sources_attempted: int = 0,
        sources_succeeded: int = 0,
        sources_failed: int = 0,
        completeness_score: float = 0,
        confidence_score: float = 0,
        processing_time_ms: int = 0,
        ai_tokens_used: int = 0,
        has_linkedin_data: bool = False,
        has_social_data: bool = False,
        has_news_data: bool = False,
        has_photo: bool = False,
        has_voting_history: bool = False,
        has_controversies: bool = False
    ) -> Optional[str]:
        """Record a person analysis in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            user_sk = None
            if user_email:
                user_sk = await self.dim_client.ensure_user_dimension(user_email)

            person_sk = await self.dim_client.ensure_person_dimension(person_id)

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "user_sk": user_sk,
                "person_sk": person_sk,
                "person_type": person_type,
                "analysis_type": analysis_type,
                "sources_attempted": sources_attempted,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed,
                "completeness_score": completeness_score,
                "confidence_score": confidence_score,
                "processing_time_ms": processing_time_ms,
                "ai_tokens_used": ai_tokens_used,
                "has_linkedin_data": has_linkedin_data,
                "has_social_data": has_social_data,
                "has_news_data": has_news_data,
                "has_photo": has_photo,
                "has_voting_history": has_voting_history,
                "has_controversies": has_controversies,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("fact_person_analysis_recorded", person_id=person_id)
                return result.data[0]["analysis_id"]

        except Exception as e:
            logger.error("fact_person_analysis_error", error=str(e))

        return None


class FactNewsRepository:
    """Repository for fact_news table"""

    TABLE_NAME = "fact_news"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_news_query(
        self,
        query_text: str,
        source_code: str,
        user_email: Optional[str] = None,
        query_params: Optional[dict] = None,
        results_count: int = 0,
        relevant_count: int = 0,
        avg_sentiment_score: Optional[float] = None,
        positive_count: int = 0,
        negative_count: int = 0,
        neutral_count: int = 0,
        processing_time_ms: int = 0
    ) -> Optional[str]:
        """Record a news query in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            user_sk = None
            if user_email:
                user_sk = await self.dim_client.ensure_user_dimension(user_email)

            source_sk = await self.dim_client.get_source_sk(source_code)

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "user_sk": user_sk,
                "source_sk": source_sk,
                "query_text": query_text,
                "query_params": json.dumps(query_params) if query_params else "{}",
                "results_count": results_count,
                "relevant_count": relevant_count,
                "avg_sentiment_score": avg_sentiment_score,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "processing_time_ms": processing_time_ms,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("fact_news_recorded", query=query_text[:50])
                return result.data[0]["news_fact_id"]

        except Exception as e:
            logger.error("fact_news_error", error=str(e))

        return None


class FactIndicatorQueryRepository:
    """Repository for fact_indicator_query table"""

    TABLE_NAME = "fact_indicator_query"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_indicator_query(
        self,
        indicator_type: str,
        ibge_code: Optional[str] = None,
        indicator_subtype: Optional[str] = None,
        user_email: Optional[str] = None,
        data_found: bool = False,
        data_freshness_days: Optional[int] = None,
        data_year: Optional[int] = None,
        processing_time_ms: int = 0
    ) -> Optional[str]:
        """Record an indicator query in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            user_sk = None
            if user_email:
                user_sk = await self.dim_client.ensure_user_dimension(user_email)

            municipality_sk = None
            if ibge_code:
                municipality_sk = await self.dim_client.get_municipality_sk(ibge_code)

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "user_sk": user_sk,
                "municipality_sk": municipality_sk,
                "indicator_type": indicator_type,
                "indicator_subtype": indicator_subtype,
                "data_found": data_found,
                "data_freshness_days": data_freshness_days,
                "data_year": data_year,
                "processing_time_ms": processing_time_ms,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.info("fact_indicator_recorded", indicator_type=indicator_type)
                return result.data[0]["indicator_id"]

        except Exception as e:
            logger.error("fact_indicator_error", error=str(e))

        return None


class FactApiCallRepository:
    """Repository for fact_api_call table"""

    TABLE_NAME = "fact_api_call"

    def __init__(self):
        self.client = get_supabase()
        self.dim_client = DimensionalClient()

    def _is_available(self) -> bool:
        return self.client is not None

    async def record_api_call(
        self,
        source_code: str,
        endpoint: Optional[str] = None,
        http_method: str = "GET",
        http_status: Optional[int] = None,
        response_time_ms: int = 0,
        response_size_bytes: int = 0,
        is_cached: bool = False,
        cache_hit: bool = False,
        is_error: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        cost_incurred: float = 0
    ) -> Optional[str]:
        """Record an API call in the fact table"""
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow()

            source_sk = await self.dim_client.get_source_sk(source_code)

            if not source_sk:
                logger.warning("source_not_found_for_api_call", source_code=source_code)
                return None

            record = {
                "date_id": get_date_id(now),
                "time_id": get_time_id(now),
                "source_sk": source_sk,
                "endpoint": endpoint,
                "http_method": http_method,
                "http_status": http_status,
                "response_time_ms": response_time_ms,
                "response_size_bytes": response_size_bytes,
                "is_cached": is_cached,
                "cache_hit": cache_hit,
                "is_error": is_error,
                "error_type": error_type,
                "error_message": error_message,
                "cost_incurred": cost_incurred,
                "created_at": now.isoformat()
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                logger.debug("fact_api_call_recorded", source=source_code)
                return result.data[0]["call_id"]

        except Exception as e:
            logger.error("fact_api_call_error", error=str(e))

        return None


class AnalyticsQueryRepository:
    """Repository for querying analytics data from fact tables"""

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def get_searches_by_date(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search_type: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get search statistics by date"""
        if not self._is_available():
            return []

        try:
            # Use the view for daily aggregations
            query = self.client.table("v_searches_daily").select("*")

            if start_date:
                query = query.gte("full_date", start_date)
            if end_date:
                query = query.lte("full_date", end_date)
            if search_type:
                query = query.eq("search_type", search_type)

            result = query.order("full_date", desc=True).limit(limit).execute()
            return result.data or []

        except Exception as e:
            logger.error("get_searches_by_date_error", error=str(e))
            return []

    async def get_source_quality(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get data source quality metrics"""
        if not self._is_available():
            return []

        try:
            result = self.client.table("v_source_quality").select("*").limit(limit).execute()
            return result.data or []

        except Exception as e:
            logger.error("get_source_quality_error", error=str(e))
            return []

    async def get_company_analysis_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get company analysis summary"""
        if not self._is_available():
            return []

        try:
            query = self.client.table("v_company_analysis_summary").select("*")

            if start_date:
                query = query.gte("full_date", start_date)
            if end_date:
                query = query.lte("full_date", end_date)

            result = query.order("full_date", desc=True).limit(limit).execute()
            return result.data or []

        except Exception as e:
            logger.error("get_company_analysis_summary_error", error=str(e))
            return []

    async def get_user_usage(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user usage statistics"""
        if not self._is_available():
            return []

        try:
            result = self.client.table("v_user_usage").select("*").limit(limit).execute()
            return result.data or []

        except Exception as e:
            logger.error("get_user_usage_error", error=str(e))
            return []

    async def get_daily_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive daily metrics for dashboard"""
        if not self._is_available():
            return {}

        try:
            from datetime import timedelta

            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)

            start_date_id = int(start_date.strftime("%Y%m%d"))
            end_date_id = int(end_date.strftime("%Y%m%d"))

            # Get search counts
            searches = self.client.table("fact_search").select(
                "search_type", count="exact"
            ).gte("date_id", start_date_id).lte("date_id", end_date_id).execute()

            # Get API call stats
            api_calls = self.client.table("fact_api_call").select(
                "is_error", count="exact"
            ).gte("date_id", start_date_id).lte("date_id", end_date_id).execute()

            # Get company analyses
            company_analyses = self.client.table("fact_company_analysis").select(
                "analysis_type", count="exact"
            ).gte("date_id", start_date_id).lte("date_id", end_date_id).execute()

            # Get person analyses
            person_analyses = self.client.table("fact_person_analysis").select(
                "person_type", count="exact"
            ).gte("date_id", start_date_id).lte("date_id", end_date_id).execute()

            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_searches": searches.count if searches else 0,
                "total_api_calls": api_calls.count if api_calls else 0,
                "total_company_analyses": company_analyses.count if company_analyses else 0,
                "total_person_analyses": person_analyses.count if person_analyses else 0
            }

        except Exception as e:
            logger.error("get_daily_metrics_error", error=str(e))
            return {}

    async def get_search_type_distribution(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get distribution of search types"""
        if not self._is_available():
            return []

        try:
            from datetime import timedelta

            start_date_id = int((datetime.utcnow().date() - timedelta(days=days)).strftime("%Y%m%d"))

            result = self.client.rpc(
                "get_search_type_distribution",
                {"start_date_id": start_date_id}
            ).execute()

            return result.data or []

        except Exception:
            # Fallback: use raw query
            try:
                result = self.client.table("fact_search").select(
                    "search_type"
                ).execute()

                if not result.data:
                    return []

                # Aggregate in Python
                distribution = {}
                for row in result.data:
                    st = row["search_type"]
                    distribution[st] = distribution.get(st, 0) + 1

                return [{"search_type": k, "count": v} for k, v in distribution.items()]

            except Exception as e:
                logger.error("get_search_type_distribution_error", error=str(e))
                return []

    async def get_hourly_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get activity by hour of day"""
        if not self._is_available():
            return []

        try:
            from datetime import timedelta

            start_date_id = int((datetime.utcnow().date() - timedelta(days=days)).strftime("%Y%m%d"))

            result = self.client.table("fact_search").select(
                "time_id"
            ).gte("date_id", start_date_id).execute()

            if not result.data:
                return []

            # Aggregate by hour
            hourly = dict.fromkeys(range(24), 0)
            for row in result.data:
                hour = row["time_id"] // 100  # Extract hour from HHMM
                if 0 <= hour < 24:
                    hourly[hour] += 1

            return [{"hour": h, "count": c} for h, c in sorted(hourly.items())]

        except Exception as e:
            logger.error("get_hourly_activity_error", error=str(e))
            return []
