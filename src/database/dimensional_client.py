"""
Dimensional Client - Helper functions for data warehouse operations
"""

from datetime import datetime
from typing import Optional

import structlog

from .client import get_supabase

logger = structlog.get_logger()


def get_date_id(dt: Optional[datetime] = None) -> int:
    """
    Convert datetime to date_id (YYYYMMDD format)
    Returns today's date_id if no datetime provided
    """
    if dt is None:
        dt = datetime.utcnow()
    return int(dt.strftime("%Y%m%d"))


def get_time_id(dt: Optional[datetime] = None) -> int:
    """
    Convert datetime to time_id (HHMM format)
    Returns current time_id if no datetime provided
    """
    if dt is None:
        dt = datetime.utcnow()
    return int(dt.strftime("%H%M"))


def get_period(hour: int) -> str:
    """Get period of day from hour (Portuguese)"""
    if 0 <= hour < 6:
        return "madrugada"
    elif 6 <= hour < 12:
        return "manha"
    elif 12 <= hour < 18:
        return "tarde"
    else:
        return "noite"


class DimensionalClient:
    """
    Client for dimensional data warehouse operations.
    Provides helper methods for working with fact and dimension tables.
    """

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        """Check if database is available"""
        return self.client is not None

    async def ensure_user_dimension(
        self,
        user_email: str,
        plan_type: str = "free"
    ) -> Optional[str]:
        """
        Ensure user exists in dim_user and return user_sk.
        Creates new dimension record if user doesn't exist.
        """
        if not self._is_available():
            return None

        try:
            # Check if user already exists
            result = self.client.table("dim_user").select("user_sk").eq(
                "user_email", user_email
            ).eq(
                "is_current", True
            ).limit(1).execute()

            if result.data:
                return result.data[0]["user_sk"]

            # Create new user dimension
            new_user = {
                "user_email": user_email,
                "plan_type": plan_type,
                "first_access_date": datetime.utcnow().date().isoformat(),
                "is_current": True,
                "valid_from": datetime.utcnow().isoformat()
            }

            result = self.client.table("dim_user").insert(new_user).execute()

            if result.data:
                logger.info("dim_user_created", email=user_email)
                return result.data[0]["user_sk"]

        except Exception as e:
            logger.error("ensure_user_dimension_error", error=str(e))

        return None

    async def ensure_company_dimension(
        self,
        company_id: str,
        company_data: Optional[dict] = None
    ) -> Optional[str]:
        """
        Ensure company exists in dim_company and return company_sk.
        Fetches from companies table if not in dimension.
        """
        if not self._is_available():
            return None

        try:
            # Check if company already exists in dimension
            result = self.client.table("dim_company").select("company_sk").eq(
                "company_id", company_id
            ).eq(
                "is_current", True
            ).limit(1).execute()

            if result.data:
                return result.data[0]["company_sk"]

            # Fetch from companies table if no data provided
            if company_data is None:
                company_result = self.client.table("companies").select("*").eq(
                    "id", company_id
                ).limit(1).execute()

                if not company_result.data:
                    logger.warning("company_not_found", company_id=company_id)
                    return None

                company_data = company_result.data[0]

            # Create dimension record
            dim_record = {
                "company_id": company_id,
                "cnpj": company_data.get("cnpj"),
                "razao_social": company_data.get("razao_social"),
                "nome_fantasia": company_data.get("nome_fantasia"),
                "industry": company_data.get("industry"),
                "size": company_data.get("size"),
                "state": company_data.get("state"),
                "city": company_data.get("city"),
                "revenue_range": company_data.get("revenue_range"),
                "website": company_data.get("website"),
                "is_current": True,
                "valid_from": datetime.utcnow().isoformat()
            }

            result = self.client.table("dim_company").insert(dim_record).execute()

            if result.data:
                logger.info("dim_company_created", company_id=company_id)
                return result.data[0]["company_sk"]

        except Exception as e:
            logger.error("ensure_company_dimension_error", error=str(e))

        return None

    async def ensure_person_dimension(
        self,
        person_id: str,
        person_data: Optional[dict] = None
    ) -> Optional[str]:
        """
        Ensure person exists in dim_person and return person_sk.
        Fetches from people table if not in dimension.
        """
        if not self._is_available():
            return None

        try:
            # Check if person already exists in dimension
            result = self.client.table("dim_person").select("person_sk").eq(
                "person_id", person_id
            ).eq(
                "is_current", True
            ).limit(1).execute()

            if result.data:
                return result.data[0]["person_sk"]

            # Fetch from people table if no data provided
            if person_data is None:
                person_result = self.client.table("people").select("*").eq(
                    "id", person_id
                ).limit(1).execute()

                if not person_result.data:
                    logger.warning("person_not_found", person_id=person_id)
                    return None

                person_data = person_result.data[0]

            # Create dimension record
            dim_record = {
                "person_id": person_id,
                "full_name": person_data.get("full_name"),
                "person_type": person_data.get("person_type", "professional"),
                "current_title": person_data.get("current_title"),
                "current_company": person_data.get("current_company"),
                "seniority": person_data.get("seniority"),
                "state": person_data.get("state"),
                "city": person_data.get("city"),
                "political_party": person_data.get("political_party"),
                "political_role": person_data.get("political_role"),
                "is_current": True,
                "valid_from": datetime.utcnow().isoformat()
            }

            result = self.client.table("dim_person").insert(dim_record).execute()

            if result.data:
                logger.info("dim_person_created", person_id=person_id)
                return result.data[0]["person_sk"]

        except Exception as e:
            logger.error("ensure_person_dimension_error", error=str(e))

        return None

    async def get_source_sk(self, source_code: str) -> Optional[str]:
        """Get source_sk for a data source by its code"""
        if not self._is_available():
            return None

        try:
            result = self.client.table("dim_data_source").select("source_sk").eq(
                "source_code", source_code
            ).limit(1).execute()

            if result.data:
                return result.data[0]["source_sk"]

            logger.warning("source_not_found", source_code=source_code)

        except Exception as e:
            logger.error("get_source_sk_error", error=str(e))

        return None

    async def get_municipality_sk(self, ibge_code: str) -> Optional[str]:
        """Get municipality_sk by IBGE code"""
        if not self._is_available():
            return None

        try:
            result = self.client.table("dim_municipality").select("municipality_sk").eq(
                "ibge_code", ibge_code
            ).limit(1).execute()

            if result.data:
                return result.data[0]["municipality_sk"]

        except Exception as e:
            logger.error("get_municipality_sk_error", error=str(e))

        return None

    async def update_company_dimension_scd2(
        self,
        company_id: str,
        new_data: dict
    ) -> Optional[str]:
        """
        Update company dimension using SCD Type 2.
        Closes current record and creates new one with updated data.
        """
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow().isoformat()

            # Close current record
            self.client.table("dim_company").update({
                "is_current": False,
                "valid_to": now
            }).eq(
                "company_id", company_id
            ).eq(
                "is_current", True
            ).execute()

            # Create new current record
            dim_record = {
                "company_id": company_id,
                "cnpj": new_data.get("cnpj"),
                "razao_social": new_data.get("razao_social"),
                "nome_fantasia": new_data.get("nome_fantasia"),
                "industry": new_data.get("industry"),
                "size": new_data.get("size"),
                "state": new_data.get("state"),
                "city": new_data.get("city"),
                "revenue_range": new_data.get("revenue_range"),
                "website": new_data.get("website"),
                "is_current": True,
                "valid_from": now
            }

            result = self.client.table("dim_company").insert(dim_record).execute()

            if result.data:
                logger.info("dim_company_scd2_updated", company_id=company_id)
                return result.data[0]["company_sk"]

        except Exception as e:
            logger.error("update_company_dimension_scd2_error", error=str(e))

        return None

    async def update_person_dimension_scd2(
        self,
        person_id: str,
        new_data: dict
    ) -> Optional[str]:
        """
        Update person dimension using SCD Type 2.
        """
        if not self._is_available():
            return None

        try:
            now = datetime.utcnow().isoformat()

            # Close current record
            self.client.table("dim_person").update({
                "is_current": False,
                "valid_to": now
            }).eq(
                "person_id", person_id
            ).eq(
                "is_current", True
            ).execute()

            # Create new current record
            dim_record = {
                "person_id": person_id,
                "full_name": new_data.get("full_name"),
                "person_type": new_data.get("person_type", "professional"),
                "current_title": new_data.get("current_title"),
                "current_company": new_data.get("current_company"),
                "seniority": new_data.get("seniority"),
                "state": new_data.get("state"),
                "city": new_data.get("city"),
                "political_party": new_data.get("political_party"),
                "political_role": new_data.get("political_role"),
                "is_current": True,
                "valid_from": now
            }

            result = self.client.table("dim_person").insert(dim_record).execute()

            if result.data:
                logger.info("dim_person_scd2_updated", person_id=person_id)
                return result.data[0]["person_sk"]

        except Exception as e:
            logger.error("update_person_dimension_scd2_error", error=str(e))

        return None
