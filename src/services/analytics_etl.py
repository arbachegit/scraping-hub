"""
Analytics ETL Service
Handles data transformation and loading for the dimensional model
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.database.dimensional_client import DimensionalClient
from src.database.dimensional_repository import (
    FactApiCallRepository,
    FactCompanyAnalysisRepository,
    FactIndicatorQueryRepository,
    FactNewsRepository,
    FactPersonAnalysisRepository,
    FactSearchRepository,
)

logger = structlog.get_logger()


class AnalyticsETL:
    """
    ETL service for analytics data.
    Transforms operational data into dimensional model facts.
    """

    def __init__(self):
        self.dim_client = DimensionalClient()
        self.fact_search_repo = FactSearchRepository()
        self.fact_company_repo = FactCompanyAnalysisRepository()
        self.fact_person_repo = FactPersonAnalysisRepository()
        self.fact_news_repo = FactNewsRepository()
        self.fact_indicator_repo = FactIndicatorQueryRepository()
        self.fact_api_repo = FactApiCallRepository()

    async def record_search(
        self,
        search_type: str,
        query: str,
        user_email: Optional[str] = None,
        results_count: int = 0,
        processing_time_ms: int = 0,
        credits_used: int = 1,
        status: str = "completed",
        error_message: Optional[str] = None,
        query_params: Optional[dict] = None
    ) -> Optional[str]:
        """
        Record a search event in the analytics fact table.
        Call this from search services after completing a search.
        """
        return await self.fact_search_repo.record_search(
            search_type=search_type,
            query_text=query,
            user_email=user_email,
            query_params=query_params,
            results_count=results_count,
            processing_time_ms=processing_time_ms,
            credits_used=credits_used,
            status=status,
            error_message=error_message
        )

    async def record_company_analysis(
        self,
        company_id: str,
        analysis_type: str = "client",
        user_email: Optional[str] = None,
        sources_result: Optional[Dict[str, bool]] = None,
        completeness_score: float = 0,
        confidence_score: float = 0,
        processing_time_ms: int = 0,
        ai_tokens_used: int = 0,
        analysis_result: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record a company analysis event.
        Call this from CompanyIntelService after completing an analysis.
        """
        # Calculate source metrics
        sources_attempted = 0
        sources_succeeded = 0
        sources_failed = 0

        has_website_data = False
        has_linkedin_data = False
        has_news_data = False
        has_financial_data = False
        has_cnpj_data = False

        if sources_result:
            sources_attempted = len(sources_result)
            sources_succeeded = sum(1 for v in sources_result.values() if v)
            sources_failed = sources_attempted - sources_succeeded

            has_website_data = sources_result.get("website", False)
            has_linkedin_data = sources_result.get("linkedin", False) or sources_result.get("apollo", False)
            has_news_data = sources_result.get("news", False) or sources_result.get("serper", False)
            has_financial_data = sources_result.get("financial", False)
            has_cnpj_data = sources_result.get("cnpj", False) or sources_result.get("brasilapi", False)

        # Determine what outputs were generated
        has_swot = False
        has_okrs = False
        has_competitors = False

        if analysis_result:
            has_swot = bool(analysis_result.get("swot_analysis"))
            has_okrs = bool(analysis_result.get("suggested_okrs"))
            has_competitors = bool(analysis_result.get("competitors"))

        return await self.fact_company_repo.record_analysis(
            company_id=company_id,
            analysis_type=analysis_type,
            user_email=user_email,
            sources_attempted=sources_attempted,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            ai_tokens_used=ai_tokens_used,
            has_website_data=has_website_data,
            has_linkedin_data=has_linkedin_data,
            has_news_data=has_news_data,
            has_financial_data=has_financial_data,
            has_cnpj_data=has_cnpj_data,
            has_swot=has_swot,
            has_okrs=has_okrs,
            has_competitors=has_competitors
        )

    async def record_person_analysis(
        self,
        person_id: str,
        person_type: str = "professional",
        analysis_type: str = "profile",
        user_email: Optional[str] = None,
        sources_result: Optional[Dict[str, bool]] = None,
        completeness_score: float = 0,
        confidence_score: float = 0,
        processing_time_ms: int = 0,
        ai_tokens_used: int = 0,
        analysis_result: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record a person/politician analysis event.
        Call this from PeopleIntelService or PoliticianIntelService.
        """
        sources_attempted = 0
        sources_succeeded = 0
        sources_failed = 0

        has_linkedin_data = False
        has_social_data = False
        has_news_data = False
        has_photo = False

        if sources_result:
            sources_attempted = len(sources_result)
            sources_succeeded = sum(1 for v in sources_result.values() if v)
            sources_failed = sources_attempted - sources_succeeded

            has_linkedin_data = sources_result.get("linkedin", False) or sources_result.get("apollo", False)
            has_social_data = sources_result.get("twitter", False) or sources_result.get("instagram", False)
            has_news_data = sources_result.get("news", False) or sources_result.get("serper", False)
            has_photo = sources_result.get("photo", False)

        has_voting_history = False
        has_controversies = False

        if analysis_result and person_type == "politician":
            has_voting_history = bool(analysis_result.get("voting_history"))
            has_controversies = bool(analysis_result.get("controversies"))

        return await self.fact_person_repo.record_analysis(
            person_id=person_id,
            person_type=person_type,
            analysis_type=analysis_type,
            user_email=user_email,
            sources_attempted=sources_attempted,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            ai_tokens_used=ai_tokens_used,
            has_linkedin_data=has_linkedin_data,
            has_social_data=has_social_data,
            has_news_data=has_news_data,
            has_photo=has_photo,
            has_voting_history=has_voting_history,
            has_controversies=has_controversies
        )

    async def record_news_query(
        self,
        query: str,
        source_code: str = "serper",
        user_email: Optional[str] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        processing_time_ms: int = 0
    ) -> Optional[str]:
        """
        Record a news query event.
        Call this from NewsMonitorService.
        """
        results_count = 0
        relevant_count = 0
        avg_sentiment = None
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        if results:
            results_count = len(results)
            relevant_count = sum(1 for r in results if r.get("relevance_score", 0) > 0.5)

            sentiments = [r.get("sentiment_score") for r in results if r.get("sentiment_score") is not None]
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)

            for r in results:
                sentiment = r.get("sentiment")
                if sentiment == "positive":
                    positive_count += 1
                elif sentiment == "negative":
                    negative_count += 1
                else:
                    neutral_count += 1

        return await self.fact_news_repo.record_news_query(
            query_text=query,
            source_code=source_code,
            user_email=user_email,
            results_count=results_count,
            relevant_count=relevant_count,
            avg_sentiment_score=avg_sentiment,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            processing_time_ms=processing_time_ms
        )

    async def record_indicator_query(
        self,
        indicator_type: str,
        ibge_code: Optional[str] = None,
        indicator_subtype: Optional[str] = None,
        user_email: Optional[str] = None,
        data_found: bool = False,
        data_year: Optional[int] = None,
        processing_time_ms: int = 0
    ) -> Optional[str]:
        """
        Record an indicator query event.
        Call this from RegionalIntelService.
        """
        data_freshness_days = None
        if data_year:
            current_year = datetime.utcnow().year
            data_freshness_days = (current_year - data_year) * 365

        return await self.fact_indicator_repo.record_indicator_query(
            indicator_type=indicator_type,
            ibge_code=ibge_code,
            indicator_subtype=indicator_subtype,
            user_email=user_email,
            data_found=data_found,
            data_freshness_days=data_freshness_days,
            data_year=data_year,
            processing_time_ms=processing_time_ms
        )

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
        error: Optional[Exception] = None,
        cost: float = 0
    ) -> Optional[str]:
        """
        Record an external API call.
        Call this from scrapers after each API call.
        """
        is_error = error is not None or (http_status and http_status >= 400)
        error_type = None
        error_message = None

        if error:
            error_type = type(error).__name__
            error_message = str(error)[:500]

        return await self.fact_api_repo.record_api_call(
            source_code=source_code,
            endpoint=endpoint,
            http_method=http_method,
            http_status=http_status,
            response_time_ms=response_time_ms,
            response_size_bytes=response_size_bytes,
            is_cached=is_cached,
            cache_hit=cache_hit,
            is_error=is_error,
            error_type=error_type,
            error_message=error_message,
            cost_incurred=cost
        )


class AnalyticsTracker:
    """
    Context manager for tracking analytics of operations.
    Use this to automatically track timing and record facts.
    """

    def __init__(self, etl: Optional[AnalyticsETL] = None):
        self.etl = etl or AnalyticsETL()
        self._start_time: Optional[float] = None
        self._operation_type: Optional[str] = None
        self._metadata: Dict[str, Any] = {}

    def start_operation(self, operation_type: str, **metadata):
        """Start tracking an operation"""
        self._start_time = time.time()
        self._operation_type = operation_type
        self._metadata = metadata
        return self

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds"""
        if self._start_time is None:
            return 0
        return int((time.time() - self._start_time) * 1000)

    async def end_search(
        self,
        query: str,
        results_count: int = 0,
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """End tracking and record as search fact"""
        return await self.etl.record_search(
            search_type=self._metadata.get("search_type", "unknown"),
            query=query,
            user_email=self._metadata.get("user_email"),
            results_count=results_count,
            processing_time_ms=self.get_elapsed_ms(),
            credits_used=self._metadata.get("credits_used", 1),
            status=status,
            error_message=error_message,
            query_params=self._metadata.get("query_params")
        )

    async def end_company_analysis(
        self,
        company_id: str,
        sources_result: Optional[Dict[str, bool]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        completeness_score: float = 0,
        confidence_score: float = 0,
        ai_tokens_used: int = 0
    ) -> Optional[str]:
        """End tracking and record as company analysis fact"""
        return await self.etl.record_company_analysis(
            company_id=company_id,
            analysis_type=self._metadata.get("analysis_type", "client"),
            user_email=self._metadata.get("user_email"),
            sources_result=sources_result,
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            processing_time_ms=self.get_elapsed_ms(),
            ai_tokens_used=ai_tokens_used,
            analysis_result=analysis_result
        )

    async def end_person_analysis(
        self,
        person_id: str,
        person_type: str = "professional",
        sources_result: Optional[Dict[str, bool]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        completeness_score: float = 0,
        confidence_score: float = 0,
        ai_tokens_used: int = 0
    ) -> Optional[str]:
        """End tracking and record as person analysis fact"""
        return await self.etl.record_person_analysis(
            person_id=person_id,
            person_type=person_type,
            analysis_type=self._metadata.get("analysis_type", "profile"),
            user_email=self._metadata.get("user_email"),
            sources_result=sources_result,
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            processing_time_ms=self.get_elapsed_ms(),
            ai_tokens_used=ai_tokens_used,
            analysis_result=analysis_result
        )

    async def end_api_call(
        self,
        source_code: str,
        http_status: Optional[int] = None,
        response_size_bytes: int = 0,
        is_cached: bool = False,
        cache_hit: bool = False,
        error: Optional[Exception] = None
    ) -> Optional[str]:
        """End tracking and record as API call fact"""
        return await self.etl.record_api_call(
            source_code=source_code,
            endpoint=self._metadata.get("endpoint"),
            http_method=self._metadata.get("http_method", "GET"),
            http_status=http_status,
            response_time_ms=self.get_elapsed_ms(),
            response_size_bytes=response_size_bytes,
            is_cached=is_cached,
            cache_hit=cache_hit,
            error=error,
            cost=self._metadata.get("cost", 0)
        )


# Singleton instance for easy access
_analytics_etl: Optional[AnalyticsETL] = None


def get_analytics_etl() -> AnalyticsETL:
    """Get singleton AnalyticsETL instance"""
    global _analytics_etl
    if _analytics_etl is None:
        _analytics_etl = AnalyticsETL()
    return _analytics_etl


def get_tracker(**metadata) -> AnalyticsTracker:
    """Get a new AnalyticsTracker with shared ETL instance"""
    return AnalyticsTracker(get_analytics_etl())
