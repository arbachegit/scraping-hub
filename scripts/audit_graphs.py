#!/usr/bin/env python3
"""
Graph Auditor - Auditoria de Graficos Cumulativos
Valida integridade dos dados em stats_historico.

Regra: graficos cumulativos devem ser monotonicamente crescentes.
Se total[i] < total[i-1], temos uma anomalia.

Uso:
    python scripts/audit_graphs.py
    python scripts/audit_graphs.py --fix
    python scripts/audit_graphs.py --fix --category politicos
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

import structlog
from supabase import create_client

logger = structlog.get_logger()

CATEGORIES = ["empresas", "pessoas", "politicos", "mandatos", "emendas", "noticias"]


@dataclass
class AuditResult:
    """Resultado de auditoria de uma categoria."""

    category: str
    total_points: int = 0
    anomalies: int = 0
    fixed: int = 0
    status: str = "pending"
    details: list[dict] = field(default_factory=list)


class GraphAuditor:
    """Auditor de integridade de graficos cumulativos."""

    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
            "SUPABASE_KEY"
        )

        if not supabase_url or not supabase_key:
            logger.error(
                "audit_missing_credentials",
                hint="Set SUPABASE_URL and SUPABASE_SERVICE_KEY",
            )
            sys.exit(1)

        self._supabase = create_client(supabase_url, supabase_key)

    def audit_category(self, category: str, fix: bool = False) -> AuditResult:
        """
        Audita uma categoria verificando monotonicidade.

        Args:
            category: Nome da categoria (empresas, pessoas, etc.)
            fix: Se True, corrige anomalias com carry-forward

        Returns:
            AuditResult com detalhes
        """
        result = AuditResult(category=category)

        # Buscar dados ordenados por data
        response = (
            self._supabase.table("stats_historico")
            .select("*")
            .eq("categoria", category)
            .order("data", desc=False)
            .execute()
        )

        points = response.data or []
        result.total_points = len(points)

        if len(points) < 2:
            result.status = "pass"
            logger.info(
                "audit_category_skip",
                category=category,
                reason="insufficient_data",
                points=len(points),
            )
            return result

        # Verificar monotonicidade: total[i] >= total[i-1]
        last_valid_total = points[0]["total"]

        for i in range(1, len(points)):
            current = points[i]
            prev = points[i - 1]

            if current["total"] < prev["total"]:
                result.anomalies += 1
                anomaly = {
                    "date": current["data"],
                    "expected_min": prev["total"],
                    "actual": current["total"],
                    "drop": prev["total"] - current["total"],
                }
                result.details.append(anomaly)

                logger.warn(
                    "audit_anomaly_found",
                    category=category,
                    date=current["data"],
                    expected_min=prev["total"],
                    actual=current["total"],
                )

                if fix:
                    # Carry forward: usar ultimo valor valido
                    fix_total = last_valid_total
                    self._supabase.table("stats_historico").update(
                        {"total": fix_total}
                    ).eq("data", current["data"]).eq("categoria", category).execute()

                    result.fixed += 1
                    logger.info(
                        "audit_anomaly_fixed",
                        category=category,
                        date=current["data"],
                        old_total=current["total"],
                        new_total=fix_total,
                    )
            else:
                last_valid_total = current["total"]

        result.status = "pass" if result.anomalies == 0 else "fail"

        logger.info(
            "audit_category_complete",
            category=category,
            status=result.status,
            total_points=result.total_points,
            anomalies=result.anomalies,
            fixed=result.fixed,
        )

        return result

    def run_full_audit(self, fix: bool = False) -> list[AuditResult]:
        """
        Executa auditoria completa em todas as categorias.

        Args:
            fix: Se True, corrige anomalias

        Returns:
            Lista de AuditResult
        """
        logger.info("audit_full_start", fix=fix, categories=CATEGORIES)

        results = []
        for cat in CATEGORIES:
            result = self.audit_category(cat, fix=fix)
            results.append(result)

        # Resumo
        total_anomalies = sum(r.anomalies for r in results)
        total_fixed = sum(r.fixed for r in results)
        all_pass = all(r.status == "pass" for r in results)

        logger.info(
            "audit_full_complete",
            overall_status="pass" if all_pass else "fail",
            total_anomalies=total_anomalies,
            total_fixed=total_fixed,
            categories_audited=len(results),
        )

        return results


def main():
    """Entry point CLI."""
    parser = argparse.ArgumentParser(description="Auditoria de graficos cumulativos")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Corrigir anomalias (carry-forward ultimo valor valido)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=CATEGORIES,
        help="Auditar apenas uma categoria",
    )
    args = parser.parse_args()

    auditor = GraphAuditor()

    if args.category:
        result = auditor.audit_category(args.category, fix=args.fix)
        results = [result]
    else:
        results = auditor.run_full_audit(fix=args.fix)

    # Print summary
    print("\n" + "=" * 60)
    print("AUDIT REPORT")
    print("=" * 60)

    for r in results:
        icon = "PASS" if r.status == "pass" else "FAIL"
        fix_info = f" (fixed: {r.fixed})" if r.fixed > 0 else ""
        print(
            f"  [{icon}] {r.category:<12} "
            f"points={r.total_points:<6} "
            f"anomalies={r.anomalies}{fix_info}"
        )

    print("=" * 60)

    overall = "PASS" if all(r.status == "pass" for r in results) else "FAIL"
    print(f"Overall: {overall}")
    print()

    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
