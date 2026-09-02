"""Liveness, readiness, and administrator-only bounded metrics."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, status

from services.api.app.dependencies import AdminAccountDependency
from src.digital_twin.student import AccountRole, AccountStatus


router = APIRouter(tags=["operations"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(request: Request):
    checks = {
        "student_database": _dependency_ready(
            request.app.state.student_repository.healthcheck
        ),
        "identity_database": _dependency_ready(
            request.app.state.identity_repository.healthcheck
        ),
        "ingestion_database": _dependency_ready(
            request.app.state.ingestion_job_repository.healthcheck
        ),
        "onboarding_store": _dependency_ready(
            request.app.state.session_repository.healthcheck
        ),
        "object_store": _object_store_ready(request.app.state.object_store.root),
    }
    if not all(checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "not_ready",
                "message": "A required durable dependency is unavailable.",
                "checks": checks,
            },
        )
    return {"status": "ready", "checks": checks}


@router.get("/operations/metrics")
def metrics(request: Request, account_id: AdminAccountDependency):
    account = request.app.state.student_repository.get_account(account_id)
    if (
        account is None
        or account.status != AccountStatus.ACTIVE
        or account.role != AccountRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "admin_required", "message": "Administrator required."},
        )
    snapshot = request.app.state.operational_metrics.snapshot()
    budget = request.app.state.provider_budget
    snapshot["provider_budget"] = (
        budget.snapshot()
        if budget is not None
        else {
            "mode": "deterministic",
            "calls": 0,
            "reported_cost_usd": 0.0,
        }
    )
    planner_budget = getattr(request.app.state, "autonomy_planner_budget", None)
    snapshot["autonomy_planner_budget"] = (
        planner_budget.snapshot()
        if planner_budget is not None
        else {
            "mode": "deterministic",
            "calls": 0,
            "reported_cost_usd": 0.0,
        }
    )
    return snapshot


def _object_store_ready(root) -> bool:
    try:
        return root.is_dir() and os.access(root, os.R_OK | os.W_OK | os.X_OK)
    except OSError:
        return False


def _dependency_ready(check) -> bool:
    try:
        return bool(check())
    except Exception:
        return False
