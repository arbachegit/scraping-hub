"""
LinkedIn Service
Servico especializado para dados de LinkedIn
"""

import structlog
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.scrapers import CoresignalClient, ProxycurlClient


logger = structlog.get_logger()


@dataclass
class PerfilLinkedIn:
    """Perfil enriquecido de pessoa no LinkedIn"""
    # Identificacao
    linkedin_url: Optional[str] = None
    nome_completo: Optional[str] = None
    primeiro_nome: Optional[str] = None
    sobrenome: Optional[str] = None

    # Profissional
    cargo_atual: Optional[str] = None
    empresa_atual: Optional[str] = None
    headline: Optional[str] = None

    # Contato
    email: Optional[str] = None
    telefone: Optional[str] = None

    # Localizacao
    cidade: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None

    # Educacao
    educacao: List[Dict] = field(default_factory=list)

    # Experiencia
    experiencias: List[Dict] = field(default_factory=list)

    # Skills
    skills: List[str] = field(default_factory=list)

    # Extras
    conexoes: Optional[int] = None
    foto_url: Optional[str] = None
    resumo: Optional[str] = None


class LinkedInService:
    """
    Servico para inteligencia de LinkedIn

    Funcionalidades:
    - Enriquecimento de perfis
    - Mapeamento de organograma
    - Busca de profissionais
    - Analise de network
    """

    def __init__(self):
        self.coresignal = CoresignalClient()
        self.proxycurl = ProxycurlClient()

    async def get_profile(
        self,
        linkedin_url: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_domain: Optional[str] = None,
        include_skills: bool = True,
        include_email: bool = False
    ) -> PerfilLinkedIn:
        """
        Obtem perfil completo de uma pessoa

        Args:
            linkedin_url: URL do perfil
            first_name: Primeiro nome (para busca)
            last_name: Sobrenome (para busca)
            company_domain: Dominio da empresa (para busca)
            include_skills: Incluir habilidades
            include_email: Incluir email pessoal (custo extra)

        Returns:
            Perfil enriquecido
        """
        logger.info(
            "linkedin_get_profile",
            url=linkedin_url,
            name=f"{first_name} {last_name}"
        )

        perfil = PerfilLinkedIn(linkedin_url=linkedin_url)

        # Buscar dados via Proxycurl
        data = await self.proxycurl.enrich_person(
            linkedin_url=linkedin_url,
            first_name=first_name,
            last_name=last_name,
            company_domain=company_domain
        )

        if data:
            self._parse_proxycurl_profile(perfil, data)

        return perfil

    def _parse_proxycurl_profile(
        self,
        perfil: PerfilLinkedIn,
        data: Dict[str, Any]
    ) -> None:
        """Parseia dados do Proxycurl para o modelo"""
        perfil.linkedin_url = perfil.linkedin_url or data.get("public_identifier")
        perfil.nome_completo = data.get("full_name")
        perfil.primeiro_nome = data.get("first_name")
        perfil.sobrenome = data.get("last_name")
        perfil.headline = data.get("headline")
        perfil.resumo = data.get("summary")
        perfil.conexoes = data.get("connections")
        perfil.foto_url = data.get("profile_pic_url")

        # Localizacao
        perfil.cidade = data.get("city")
        perfil.estado = data.get("state")
        perfil.pais = data.get("country_full_name")

        # Experiencia atual
        experiences = data.get("experiences", [])
        if experiences:
            current = experiences[0]
            perfil.cargo_atual = current.get("title")
            perfil.empresa_atual = current.get("company")
            perfil.experiencias = experiences

        # Educacao
        perfil.educacao = data.get("education", [])

        # Skills
        perfil.skills = data.get("skills", [])

        # Contato
        perfil.email = data.get("personal_email")
        perfil.telefone = data.get("personal_numbers", [None])[0]

    async def search_professionals(
        self,
        title: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca profissionais por criterios

        Args:
            title: Cargo
            company: Empresa
            location: Localizacao
            skills: Lista de habilidades
            limit: Numero maximo de resultados

        Returns:
            Lista de profissionais encontrados
        """
        logger.info(
            "linkedin_search_professionals",
            title=title,
            company=company,
            limit=limit
        )

        results = await self.coresignal.search_members(
            title=title,
            company=company,
            location=location,
            skills=skills,
            limit=limit
        )

        return results

    async def map_company_org(
        self,
        company_linkedin: str,
        max_employees: int = 100
    ) -> Dict[str, Any]:
        """
        Mapeia organograma de uma empresa

        Args:
            company_linkedin: URL do LinkedIn da empresa
            max_employees: Numero maximo de funcionarios a analisar

        Returns:
            Estrutura organizacional
        """
        logger.info("linkedin_map_org", company=company_linkedin)

        # Buscar funcionarios
        result = await self.proxycurl.get_company_employees(
            linkedin_url=company_linkedin,
            page_size=max_employees
        )

        employees = result.get("employees", [])

        # Organizar por nivel hierarquico
        org = {
            "c_level": [],
            "vp_directors": [],
            "managers": [],
            "senior": [],
            "others": []
        }

        c_level_keywords = ["ceo", "cfo", "cto", "coo", "cmo", "chief", "founder"]
        vp_keywords = ["vp", "vice president", "director"]
        manager_keywords = ["manager", "head of", "lead"]
        senior_keywords = ["senior", "sr.", "principal"]

        for emp in employees:
            title = (emp.get("title") or "").lower()

            if any(k in title for k in c_level_keywords):
                org["c_level"].append(emp)
            elif any(k in title for k in vp_keywords):
                org["vp_directors"].append(emp)
            elif any(k in title for k in manager_keywords):
                org["managers"].append(emp)
            elif any(k in title for k in senior_keywords):
                org["senior"].append(emp)
            else:
                org["others"].append(emp)

        return {
            "company": company_linkedin,
            "total_employees": len(employees),
            "organization": org,
            "summary": {
                "c_level_count": len(org["c_level"]),
                "vp_directors_count": len(org["vp_directors"]),
                "managers_count": len(org["managers"]),
                "senior_count": len(org["senior"]),
                "others_count": len(org["others"])
            }
        }

    async def analyze_profile(
        self,
        linkedin_url: str
    ) -> Dict[str, Any]:
        """
        Analisa um perfil de LinkedIn

        Args:
            linkedin_url: URL do perfil

        Returns:
            Insights sobre o perfil
        """
        logger.info("linkedin_analyze_profile", url=linkedin_url)

        profile = await self.get_profile(linkedin_url=linkedin_url)

        # Calcular anos de experiencia
        total_exp_months = 0
        companies_worked = set()

        for exp in profile.experiencias:
            duration = exp.get("duration_months", 0) or 0
            total_exp_months += duration
            if exp.get("company"):
                companies_worked.add(exp.get("company"))

        years_experience = total_exp_months / 12

        # Nivel de senioridade estimado
        if years_experience > 15:
            seniority = "Executive"
        elif years_experience > 10:
            seniority = "Senior"
        elif years_experience > 5:
            seniority = "Mid-Level"
        elif years_experience > 2:
            seniority = "Junior"
        else:
            seniority = "Entry-Level"

        # Skills mais relevantes
        top_skills = profile.skills[:10] if profile.skills else []

        return {
            "profile": {
                "name": profile.nome_completo,
                "headline": profile.headline,
                "current_company": profile.empresa_atual,
                "current_title": profile.cargo_atual,
                "location": f"{profile.cidade}, {profile.estado}, {profile.pais}"
            },
            "insights": {
                "years_experience": round(years_experience, 1),
                "estimated_seniority": seniority,
                "companies_count": len(companies_worked),
                "education_count": len(profile.educacao),
                "skills_count": len(profile.skills),
                "top_skills": top_skills,
                "connections": profile.conexoes
            }
        }

    async def find_decision_makers(
        self,
        company_linkedin: str,
        roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Encontra tomadores de decisao em uma empresa

        Args:
            company_linkedin: URL do LinkedIn da empresa
            roles: Roles especificos a buscar

        Returns:
            Lista de decision makers
        """
        roles = roles or ["CEO", "CTO", "CFO", "VP", "Director", "Head"]

        logger.info(
            "linkedin_find_decision_makers",
            company=company_linkedin,
            roles=roles
        )

        decision_makers = []

        for role in roles:
            result = await self.proxycurl.search_employees(
                linkedin_url=company_linkedin,
                keyword_regex=role,
                page_size=5
            )
            decision_makers.extend(result.get("employees", []))

        return decision_makers

    async def close(self):
        """Fecha os clientes"""
        await self.coresignal.close()
        await self.proxycurl.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
