from __future__ import annotations

import json
import re
import shlex
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Iterable
from urllib.parse import urlencode, unquote

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.application.use_cases.run_task import RunTaskUseCase
from orchestrator.application.task_template_registry import (
    DEFAULT_TEMPLATE_ID,
    get_command_preset,
    get_task_template_form,
    get_task_template_summary,
    list_command_presets,
    list_task_templates,
    normalize_template_id,
)
from orchestrator.domain.enums import RunStatus
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.config.task_loader import TaskLoader
from orchestrator.infrastructure.checks.fake_check_runner import FakeCheckRunner
from orchestrator.infrastructure.checks.shell_check_runner import ShellCheckRunner
from orchestrator.infrastructure.command.cancellation import CancellationRegistry, CommandCancelled
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.logging.file_heartbeat import FileHeartbeat
from orchestrator.infrastructure.patches.pending_patch_service import PendingPatchService
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.infrastructure.persistence.web_job_audit_log import WebJobAuditEvent, WebJobAuditLog
from orchestrator.interfaces.cli.main import build_agent, build_post_apply_validation_use_case
from orchestrator.report.final_report_writer import FinalReportWriter


RUNS_DIR = Path(".omx/runs")
JOBS_DB_PATH = Path(".omx/orchestrator.db")
WEB_TASKS_DIR = Path(".omx/web-tasks")
WEB_JOB_AUDIT_PATH = Path(".omx/web-job-audit.jsonl")
WEB_DIR = Path(__file__).parent
DEFAULT_SMOKE_WORKTREE = Path(".tmp/omx-unified-diff-smoke")
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))
ALLOWED_AGENT_MODES = {"omx_team_patch", "omx_patch", "omx", "codex", "shell", "mock"}
ALLOWED_CHANGE_TYPES = {"feature", "bugfix", "refactor", "config"}
ALLOWED_EXECUTION_BACKENDS = {"local", "docker"}
ALLOWED_DOCKER_NETWORKS = {"none", "bridge"}
ALLOWED_DOCKER_WORKTREE_MOUNTS = {"readonly", "rw"}
MEMORY_LIMIT_PATTERN = re.compile(r"^\d+(?:\.\d+)?[kKmMgG]?$")
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"(^|[\s\"'])([A-Za-z]:[\\/][^\s\"']*)")
ALLOWED_DOCKER_ABSOLUTE_PATH_PREFIXES = ("/worktree", "/run", "/cache")

app = FastAPI(title="Auto Evolution Orchestrator")
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
WEB_CANCELLATION_REGISTRY = CancellationRegistry()


@dataclass
class TaskForm:
    template_id: str = DEFAULT_TEMPLATE_ID
    task_id: str = "task-omx-team-web-001"
    title: str = "OMX Team Patch 示例任务"
    description: str = (
        "请让 OMX Team 产出 team_result JSON，其中包含 patch_plan。"
        "把 calculator.py 里的 add 函数从错误的 a - b 修复为 a + b。"
        "真实写文件、审批和测试都交给 Orchestrator。"
    )
    change_type: str = "bugfix"
    allowed_paths: str = "calculator.py"
    worktree_path: str = ""
    check_command: str = "python -m unittest -q"
    agent_mode: str = "omx_team_patch"
    patch_coder: str = ""
    patch_fixer: str = ""
    reviewer: str = ""
    command_preset: str = "custom"
    execution_backend: str = "local"
    sandbox_image: str = "python:3.12-slim"
    sandbox_network: str = "none"
    sandbox_worktree_mount: str = "readonly"
    sandbox_memory_limit: str = "1g"
    sandbox_cpu_limit: str = "1"
    real_checks: bool = True
    errors: list[str] = field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, template_id: str = DEFAULT_TEMPLATE_ID):
    return _render_index(request, form=_default_task_form(template_id))


@app.post("/tasks/run", response_class=HTMLResponse)
def run_task(
    request: Request,
    task_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    change_type: Annotated[str, Form()],
    allowed_paths: Annotated[str, Form()],
    template_id: Annotated[str, Form()] = DEFAULT_TEMPLATE_ID,
    worktree_path: Annotated[str, Form()] = "",
    check_command: Annotated[str, Form()] = "",
    agent_mode: Annotated[str, Form()] = "omx_team_patch",
    patch_coder: Annotated[str, Form()] = "",
    patch_fixer: Annotated[str, Form()] = "",
    reviewer: Annotated[str, Form()] = "",
    command_preset: Annotated[str, Form()] = "custom",
    execution_backend: Annotated[str, Form()] = "local",
    sandbox_image: Annotated[str, Form()] = "python:3.12-slim",
    sandbox_network: Annotated[str, Form()] = "none",
    sandbox_worktree_mount: Annotated[str, Form()] = "readonly",
    sandbox_memory_limit: Annotated[str, Form()] = "1g",
    sandbox_cpu_limit: Annotated[str, Form()] = "1",
    real_checks: Annotated[bool, Form()] = False,
):
    form = TaskForm(
        template_id=normalize_template_id(template_id),
        task_id=task_id,
        title=title,
        description=description,
        change_type=change_type,
        allowed_paths=allowed_paths,
        worktree_path=worktree_path,
        check_command=check_command,
        agent_mode=agent_mode,
        patch_coder=patch_coder,
        patch_fixer=patch_fixer,
        reviewer=reviewer,
        command_preset=command_preset,
        execution_backend=execution_backend,
        sandbox_image=sandbox_image,
        sandbox_network=sandbox_network,
        sandbox_worktree_mount=sandbox_worktree_mount,
        sandbox_memory_limit=sandbox_memory_limit,
        sandbox_cpu_limit=sandbox_cpu_limit,
        real_checks=real_checks,
    )
    _apply_command_preset(form)
    errors = _validate_task_form(form)
    if errors:
        form.errors = errors
        return _render_index(request, form=form, status_code=422)

    job_id = _create_web_task_and_start(form)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/templates/run", response_class=HTMLResponse)
def run_template(request: Request, template_id: Annotated[str, Form()] = DEFAULT_TEMPLATE_ID):
    form = _default_task_form(template_id)
    errors = _validate_task_form(form)
    if errors:
        form.errors = errors
        return _render_index(request, form=form, status_code=422)

    existing_job = _find_running_job_for_template(form.template_id)
    if existing_job:
        return RedirectResponse(url=f"/jobs/{existing_job['job_id']}?reused=1", status_code=303)

    job_id = _create_web_task_and_start(form)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


def _create_web_task_and_start(form: TaskForm) -> str:
    WEB_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    safe_worktree_path = _safe_local_path(form.worktree_path, DEFAULT_SMOKE_WORKTREE)
    _prepare_default_smoke_worktree(safe_worktree_path)
    task_path = WEB_TASKS_DIR / f"{_safe_id(form.task_id)}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    payload = {
        "task_id": form.task_id,
        "title": form.title,
        "description": form.description,
        "change_type": form.change_type,
        "repo_path": str(safe_worktree_path),
        "worktree_path": str(safe_worktree_path),
        "allowed_paths": _lines(form.allowed_paths),
        "forbidden_paths": [".env", "secrets", "deploy/prod"],
        "allowed_command_prefixes": ["python", "python.exe", "python -m pytest", "pytest"],
        "execution_backend": form.execution_backend,
        "sandbox": {
            "image": form.sandbox_image,
            "network": form.sandbox_network,
            "worktree_mount": form.sandbox_worktree_mount,
            "memory_limit": form.sandbox_memory_limit,
            "cpu_limit": float(form.sandbox_cpu_limit),
        },
        "check_commands": {"test": form.check_command or None, "lint": None, "typecheck": None},
        "agent_mode": form.agent_mode,
        "agent_commands": {
            "patch_coder": form.patch_coder or None,
            "patch_fixer": form.patch_fixer or None,
            "reviewer": form.reviewer or None,
        },
        "max_attempts": 2,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 10,
        "command_timeout_seconds": 240,
        "risk_level": "medium",
        "template_id": form.template_id,
    }
    task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _start_background_run(task_path, agent_mode=form.agent_mode, real_checks=form.real_checks)


def _rerun_task_path(source_task_path: Path) -> str:
    task = json.loads(source_task_path.read_text(encoding="utf-8"))
    task["task_id"] = f"{_safe_id(str(task.get('task_id') or 'task'))}-rerun-{datetime.now().strftime('%H%M%S')}"
    task["title"] = f"{str(task.get('title') or task['task_id'])}（重新运行）"
    WEB_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    target_task_path = WEB_TASKS_DIR / f"{task['task_id']}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    target_task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return _start_background_run(
        target_task_path,
        agent_mode=str(task.get("agent_mode") or "mock"),
        real_checks=True,
    )


@app.post("/examples/run")
def run_example(
    task_path: Annotated[str, Form()],
    agent_mode: Annotated[str, Form()] = "omx_team_patch",
    real_checks: Annotated[bool, Form()] = True,
):
    job_id = _start_background_run(Path(task_path), agent_mode=agent_mode, real_checks=real_checks)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_status(request: Request, job_id: str, reused: str = "", rerun_error: str = ""):
    job = _read_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    job = _reconcile_job(job)
    run_id = job.get("run_id") or ""
    if job.get("status") == "done" and run_id:
        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

    progress = _load_job_progress(run_id) if run_id else None
    task_context = _load_job_task_context(job, run_id)
    failure_hint = _build_job_failure_hint(job, progress)
    docker_evidence = _load_docker_evidence(RUNS_DIR / run_id) if run_id else _empty_docker_evidence()
    return TEMPLATES.TemplateResponse(
        request,
        "job_status.html",
        {
            "job": job,
            "job_id": job_id,
            "run_id": run_id,
            "progress": _label_job_progress(progress),
            "task_context": task_context,
            "task_meta": _build_job_task_meta(job, task_context),
            "failure_hint": failure_hint,
            "execution_chain": _build_execution_chain(
                task_context,
                status=str(job.get("status") or ""),
                phase=(progress or {}).get("phase") or str(job.get("status") or "创建中"),
                run_id=run_id,
                docker_evidence=docker_evidence,
                patches=[],
            ),
            "reused_existing_job": reused == "1",
            "rerun_error": _build_rerun_error(rerun_error),
            "auto_refresh": job.get("status") == "running",
        },
    )


@app.get("/tasks", response_class=HTMLResponse)
def task_manager(
    request: Request,
    status: str = "all",
    quality: str = "all",
    rerun: str = "all",
    page: int = 1,
    page_size: int = 10,
    q: str = "",
    batch: str = "",
):
    normalized_status = status if status in {"all", "running", "done", "failed", "stopped"} else "all"
    normalized_quality = quality if quality in {"all", "passed", "failed", "missing"} else "all"
    normalized_rerun = rerun if rerun in {"all", "available", "unavailable"} else "all"
    normalized_page_size = min(max(page_size, 5), 50)
    query = q.strip()
    status_jobs = _load_task_manager_jobs(normalized_status)
    quality_counts = _count_task_manager_quality(status_jobs)
    rerun_counts = _count_task_manager_rerun(status_jobs)
    filtered_jobs = _filter_task_manager_jobs(status_jobs, normalized_quality, normalized_rerun, query)
    total = len(filtered_jobs)
    total_pages = max(1, (total + normalized_page_size - 1) // normalized_page_size)
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * normalized_page_size
    enriched_jobs = filtered_jobs[start : start + normalized_page_size]
    return TEMPLATES.TemplateResponse(
        request,
        "tasks.html",
        {
            "jobs": enriched_jobs,
            "active_status": normalized_status,
            "active_quality": normalized_quality,
            "active_rerun": normalized_rerun,
            "query": query,
            "batch_notice": batch.strip(),
            "task_query": _tasks_query(
                status=normalized_status,
                quality=normalized_quality,
                rerun=normalized_rerun,
                page=current_page,
                page_size=normalized_page_size,
                q=query,
            ),
            "task_query_first_page": _tasks_query(
                status=normalized_status,
                quality=normalized_quality,
                rerun=normalized_rerun,
                page=1,
                page_size=normalized_page_size,
                q=query,
            ),
            "counts": _count_jobs_by_status(),
            "quality_counts": quality_counts,
            "rerun_counts": rerun_counts,
            "pagination": {
                "page": current_page,
                "page_size": normalized_page_size,
                "total": total,
                "total_pages": total_pages,
                "has_previous": current_page > 1,
                "has_next": current_page < total_pages,
                "previous_page": max(1, current_page - 1),
                "next_page": min(total_pages, current_page + 1),
                "previous_query": _tasks_query(
                    status=normalized_status,
                    quality=normalized_quality,
                    rerun=normalized_rerun,
                    page=max(1, current_page - 1),
                    page_size=normalized_page_size,
                    q=query,
                ),
                "next_query": _tasks_query(
                    status=normalized_status,
                    quality=normalized_quality,
                    rerun=normalized_rerun,
                    page=min(total_pages, current_page + 1),
                    page_size=normalized_page_size,
                    q=query,
                ),
            },
            "form": _default_task_form(),
            "docker_agent_command_presets": list_command_presets(),
            "task_templates": list_task_templates(),
            "auto_refresh": normalized_status in {"all", "running"},
        },
    )


@app.get("/tasks/audit.md")
def task_manager_audit_markdown():
    records = WebJobAuditLog(WEB_JOB_AUDIT_PATH).list_recent(limit=50)
    return PlainTextResponse(
        _build_task_manager_audit_markdown(records),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="task-manager-audit.md"'},
    )


@app.get("/tasks/audit", response_class=HTMLResponse)
def task_manager_audit_page(
    request: Request,
    event_type: str = "all",
    outcome: str = "all",
    q: str = "",
    limit: int = 50,
):
    active_limit = _normalize_task_manager_audit_limit(limit)
    records = WebJobAuditLog(WEB_JOB_AUDIT_PATH).list_recent(limit=active_limit)
    event_types = _task_manager_audit_event_types(records)
    active_event_type = event_type if event_type == "all" or event_type in event_types else "all"
    filtered_records = _filter_task_manager_audit_records(records, active_event_type)
    active_outcome = outcome if outcome in {"all", "skipped", "failed", "clean"} else "all"
    filtered_records = _filter_task_manager_audit_records_by_outcome(filtered_records, active_outcome)
    query = q.strip()
    filtered_records = _search_task_manager_audit_records(filtered_records, query)
    return TEMPLATES.TemplateResponse(
        request,
        "task_audit.html",
        {
            "records": [_build_task_manager_audit_view_record(record) for record in filtered_records],
            "total": len(records),
            "filtered_total": len(filtered_records),
            "event_types": event_types,
            "active_event_type": active_event_type,
            "active_outcome": active_outcome,
            "outcome_options": [
                {"value": "all", "label": "All"},
                {"value": "skipped", "label": "Has skipped"},
                {"value": "failed", "label": "Has failed"},
                {"value": "clean", "label": "No skipped or failed"},
            ],
            "query": query,
            "limit": active_limit,
            "limit_options": [25, 50, 100, 200],
        },
    )


@app.post("/tasks/batch")
def batch_tasks(
    action: Annotated[str, Form()],
    job_ids: Annotated[list[str] | None, Form()] = None,
    status: Annotated[str, Form()] = "all",
    quality: Annotated[str, Form()] = "all",
    rerun: Annotated[str, Form()] = "all",
    page: Annotated[int, Form()] = 1,
    page_size: Annotated[int, Form()] = 10,
    q: Annotated[str, Form()] = "",
):
    selected_job_ids = _unique_safe_ids(job_ids or [])
    if not selected_job_ids:
        return _redirect_to_tasks_with_batch_notice(
            "未选择任务，未执行批量操作。",
            status=status,
            quality=quality,
            rerun=rerun,
            page=page,
            page_size=page_size,
            q=q,
        )

    if action == "stop":
        summary = _batch_stop_jobs(selected_job_ids)
    elif action == "delete":
        summary = _batch_delete_jobs(selected_job_ids)
    elif action == "rerun":
        summary = _batch_rerun_jobs(selected_job_ids)
    else:
        summary = {"label": "未知批量操作", "processed": 0, "skipped": len(selected_job_ids), "failed": 0}

    _append_batch_web_job_audit(
        action=action,
        selected_job_ids=selected_job_ids,
        summary=summary,
        request_context=_task_request_context(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q),
    )

    notice = (
        f"{summary['label']}：成功 {summary['processed']} 个，"
        f"跳过 {summary['skipped']} 个，失败 {summary['failed']} 个。"
    )
    return _redirect_to_tasks_with_batch_notice(
        notice,
        status=status,
        quality=quality,
        rerun=rerun,
        page=page,
        page_size=page_size,
        q=q,
    )


@app.post("/tasks/{job_id}/stop")
def stop_task(
    job_id: str,
    status: str = "all",
    quality: str = "all",
    rerun: str = "all",
    page: int = 1,
    page_size: int = 10,
    q: str = "",
):
    safe_job_id = _safe_id(job_id)
    job = _read_job(safe_job_id)
    processed_job_ids: list[str] = []
    skipped_job_ids: list[str] = []
    if job and str(job.get("status") or "") == "running":
        cancelled_running_process = WEB_CANCELLATION_REGISTRY.cancel(safe_job_id)
        _update_job(
            safe_job_id,
            status="stopped",
            message=(
                "底层命令已收到终止信号。"
                if cancelled_running_process
                else "已收到停止请求。当前没有可终止的底层命令，Web Job 状态已冻结。"
            ),
            finished_at=datetime.now().isoformat(),
        )
        processed_job_ids.append(safe_job_id)
    else:
        skipped_job_ids.append(safe_job_id)
    _append_web_job_audit(
        WebJobAuditEvent(
            event_type="single_stop",
            request_context=_task_request_context(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q),
            selected_job_ids=[safe_job_id],
            processed_job_ids=processed_job_ids,
            skipped_job_ids=skipped_job_ids,
            run_ids=_job_run_ids([job]),
            message="停止任务",
            details={"job": _job_snapshot(job), "reason": "" if processed_job_ids else "job missing or not running"},
        )
    )
    return RedirectResponse(
        url=_tasks_url(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q),
        status_code=303,
    )


@app.post("/tasks/{job_id}/delete")
def delete_task(
    job_id: str,
    status: str = "all",
    quality: str = "all",
    rerun: str = "all",
    page: int = 1,
    page_size: int = 10,
    q: str = "",
):
    safe_job_id = _safe_id(job_id)
    job = _read_job(safe_job_id)
    _job_repository().delete(safe_job_id)
    _append_web_job_audit(
        WebJobAuditEvent(
            event_type="single_delete",
            request_context=_task_request_context(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q),
            selected_job_ids=[safe_job_id],
            processed_job_ids=[safe_job_id],
            run_ids=_job_run_ids([job]),
            message="删除任务记录",
            details={"deleted_job": _job_snapshot(job)},
        )
    )
    return RedirectResponse(
        url=_tasks_url(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q),
        status_code=303,
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str, rerun_error: str = ""):
    repository = FileStateRepository()
    state = repository.load_state(run_id)
    run_dir = RUNS_DIR / run_id
    patches = PendingPatchService().list(run_id=run_id)
    task_context = _load_task_context(run_dir)
    final_report = _read_optional(run_dir / "final_report.md")
    phase_log = _read_optional(run_dir / "logs" / "phase.log")
    docker_evidence = _load_docker_evidence(run_dir)
    phase_timeline = _parse_phase_timeline(phase_log)
    validation_evidence = _load_validation_evidence(run_dir, state.attempt)
    run_can_rerun = FileStateRepository().task_path_for_run(_safe_id(run_id)).exists()
    return TEMPLATES.TemplateResponse(
        request,
        "run_detail.html",
        {
            "state": state,
            "run_id": run_id,
            "run_dir": run_dir,
            "state_status_label": _status_label(str(state.status)),
            "summary": _build_run_summary(state, patches),
            "execution_summary": _build_execution_summary(state, patches, docker_evidence, phase_timeline),
            "execution_chain": _build_execution_chain(
                task_context,
                status=str(state.status),
                phase=str(state.current_phase),
                run_id=run_id,
                docker_evidence=docker_evidence,
                patches=patches,
            ),
            "run_artifacts": _build_run_artifacts(run_dir, task_context, patches),
            "task_context": task_context,
            "task_meta": _build_run_task_meta(state, task_context),
            "run_can_rerun": run_can_rerun,
            "failure_hint": _build_run_failure_hint(state, final_report, phase_log, validation_evidence),
            "rerun_error": _build_rerun_error(rerun_error),
            "final_report": final_report,
            "agent_log": _read_optional(run_dir / "logs" / "agent.log"),
            "phase_log": phase_log,
            "phase_timeline": phase_timeline,
            "validation_evidence": validation_evidence,
            "docker_evidence": docker_evidence,
            "team_result": _read_first_optional(run_dir.glob("attempts/*/team_result.json")),
            "team_diagnostics": _read_first_optional(run_dir.glob("attempts/*/team_diagnostics.json")),
            "patches": patches,
        },
    )


@app.get("/runs/{run_id}/audit.md", response_class=PlainTextResponse)
def run_audit_markdown(run_id: str):
    repository = FileStateRepository()
    state = repository.load_state(run_id)
    run_dir = RUNS_DIR / run_id
    patches = PendingPatchService().list(run_id=run_id)
    task_context = _load_task_context(run_dir)
    final_report = _read_optional(run_dir / "final_report.md")
    phase_log = _read_optional(run_dir / "logs" / "phase.log")
    docker_evidence = _load_docker_evidence(run_dir)
    phase_timeline = _parse_phase_timeline(phase_log)
    validation_evidence = _load_validation_evidence(run_dir, state.attempt)
    content = _build_run_audit_markdown(
        state=state,
        run_dir=run_dir,
        patches=patches,
        task_context=task_context,
        final_report=final_report,
        phase_log=phase_log,
        docker_evidence=docker_evidence,
        phase_timeline=phase_timeline,
        validation_evidence=validation_evidence,
    )
    return PlainTextResponse(
        content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{_safe_id(run_id)}-audit.md"'},
    )


@app.post("/jobs/{job_id}/rerun")
def rerun_job(job_id: str):
    job = _read_job(job_id)
    if not job:
        _append_web_job_audit(
            WebJobAuditEvent(
                event_type="single_rerun",
                selected_job_ids=[_safe_id(job_id)],
                skipped_job_ids=[_safe_id(job_id)],
                message="重新运行任务",
                details={"reason": "job missing"},
            )
        )
        return RedirectResponse(url="/tasks", status_code=303)
    run_id = str(job.get("run_id") or "")
    task_path = _task_path_for_job(job, run_id)
    if not task_path:
        _append_web_job_audit(
            WebJobAuditEvent(
                event_type="single_rerun",
                selected_job_ids=[_safe_id(job_id)],
                skipped_job_ids=[_safe_id(job_id)],
                run_ids=_job_run_ids([job]),
                message="重新运行任务",
                details={"job": _job_snapshot(job), "reason": "missing task.json"},
            )
        )
        return RedirectResponse(url=f"/jobs/{_safe_id(job_id)}?rerun_error=missing_task", status_code=303)
    new_job_id = _rerun_task_path(task_path)
    _append_web_job_audit(
        WebJobAuditEvent(
            event_type="single_rerun",
            selected_job_ids=[_safe_id(job_id)],
            processed_job_ids=[_safe_id(job_id), new_job_id],
            run_ids=_job_run_ids([job]),
            message="重新运行任务",
            details={"source_job": _job_snapshot(job), "new_job_id": new_job_id},
        )
    )
    return RedirectResponse(url=f"/jobs/{new_job_id}", status_code=303)


@app.post("/runs/{run_id}/rerun")
def rerun_run(run_id: str):
    safe_run_id = _safe_id(run_id)
    task_path = FileStateRepository().task_path_for_run(safe_run_id)
    if not task_path.exists():
        return RedirectResponse(url=f"/runs/{safe_run_id}?rerun_error=missing_task", status_code=303)
    new_job_id = _rerun_task_path(task_path)
    return RedirectResponse(url=f"/jobs/{new_job_id}", status_code=303)


@app.post("/patches/apply")
def apply_patch(
    run_id: Annotated[str, Form()],
    patch: Annotated[str, Form()],
    reviewer: Annotated[str, Form()] = "web",
    note: Annotated[str, Form()] = "",
    rerun_task: Annotated[bool, Form()] = False,
    rerun_checks: Annotated[bool, Form()] = False,
):
    service = PendingPatchService()
    summary = service.apply(run_id, patch, reviewer=reviewer, note=note, rerun_checks=rerun_checks)
    if rerun_task:
        task_path = FileStateRepository().task_path_for_run(run_id)
        agent_mode = json.loads(task_path.read_text(encoding="utf-8")).get("agent_mode", "mock")
        rerun_state = build_post_apply_validation_use_case(agent_mode=agent_mode).execute(
            RunTaskCommand(task_path=task_path)
        )
        summary = service.record_rerun_task(run_id, patch, rerun_state)
    return RedirectResponse(url=f"/runs/{summary['run_id']}", status_code=303)


@app.post("/patches/reject")
def reject_patch(
    run_id: Annotated[str, Form()],
    patch: Annotated[str, Form()],
    reviewer: Annotated[str, Form()] = "web",
    note: Annotated[str, Form()] = "",
):
    summary = PendingPatchService().reject(run_id, patch, reviewer=reviewer, note=note)
    return RedirectResponse(url=f"/runs/{summary['run_id']}", status_code=303)


def _render_index(request: Request, form: TaskForm, status_code: int = 200) -> HTMLResponse:
    jobs = _load_recent_jobs()
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "runs": _load_runs(),
            "jobs": jobs,
            "patches": PendingPatchService().list(),
            "examples": sorted(str(path).replace("\\", "/") for path in Path("examples").glob("task*.json")),
            "docker_agent_command_presets": list_command_presets(),
            "task_templates": _list_task_templates_with_recent_jobs(jobs),
            "project_root": Path.cwd(),
            "form": form,
        },
        status_code=status_code,
    )


def _default_task_form(template_id: str = DEFAULT_TEMPLATE_ID) -> TaskForm:
    selected_template_id = normalize_template_id(template_id)
    values = get_task_template_form(selected_template_id)
    form = TaskForm(
        template_id=selected_template_id,
        worktree_path=str((Path.cwd() / DEFAULT_SMOKE_WORKTREE).resolve()),
        patch_coder=_team_patch_command(),
        patch_fixer="",
        reviewer="",
    )
    for key, value in values.items():
        setattr(form, key, value)
    _apply_command_preset(form)
    return form


def _validate_task_form(form: TaskForm) -> list[str]:
    errors: list[str] = []
    if not _safe_id(form.task_id) or _safe_id(form.task_id) != form.task_id:
        errors.append("Task ID 只能包含字母、数字、下划线和短横线。")
    if form.change_type not in ALLOWED_CHANGE_TYPES:
        errors.append("类型只能是 feature、bugfix、refactor 或 config。")
    if form.agent_mode not in ALLOWED_AGENT_MODES:
        errors.append("Agent 模式不合法。")
    preset = get_command_preset(form.command_preset)
    if not preset:
        errors.append("Docker agent command preset is not supported.")
    elif form.command_preset != "custom":
        if form.execution_backend != "docker":
            errors.append("Docker agent command presets require execution backend docker.")
        if form.agent_mode not in preset["agent_modes"]:
            allowed = ", ".join(preset["agent_modes"])
            errors.append(f"Docker agent command preset {form.command_preset} only supports: {allowed}.")

    if form.execution_backend not in ALLOWED_EXECUTION_BACKENDS:
        errors.append("Execution backend 只能是 local 或 docker。")
    if form.execution_backend == "docker":
        _validate_docker_sandbox(form, errors)
        _validate_docker_commands(form, errors)

    worktree = _safe_local_path(form.worktree_path, DEFAULT_SMOKE_WORKTREE)
    default_worktree = (Path.cwd() / DEFAULT_SMOKE_WORKTREE).resolve()
    if worktree != default_worktree and not worktree.exists():
        errors.append(f"Worktree 不存在：{worktree}")
    elif worktree.exists() and not worktree.is_dir():
        errors.append(f"Worktree 必须是目录：{worktree}")

    allowed_paths = _lines(form.allowed_paths)
    if not allowed_paths:
        errors.append("Allowed paths 至少填写一个相对路径。")
    for item in allowed_paths:
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"Allowed paths 只能填写 worktree 内的相对路径：{item}")
        if item.strip().startswith(("/", "\\")):
            errors.append(f"Allowed paths 不能以路径分隔符开头：{item}")

    if form.real_checks and not form.check_command.strip():
        errors.append("启用真实检查时必须填写 Test command。")
    if form.check_command.strip():
        _validate_web_command(form.check_command, "Test command", errors)
    if form.patch_coder.strip():
        _validate_web_command(form.patch_coder, "Patch coder", errors)
    if form.patch_fixer.strip():
        _validate_web_command(form.patch_fixer, "Patch fixer", errors)
    if form.reviewer.strip():
        _validate_web_command(form.reviewer, "Reviewer", errors)
    return errors


def _apply_command_preset(form: TaskForm) -> None:
    preset = get_command_preset(form.command_preset)
    if not preset or form.command_preset == "custom":
        return
    commands = preset.get("commands") or {}
    form.patch_coder = str(commands.get("patch_coder") or "")
    form.patch_fixer = str(commands.get("patch_fixer") or "")
    form.reviewer = str(commands.get("reviewer") or "")

def _validate_docker_sandbox(form: TaskForm, errors: list[str]) -> None:
    if not form.sandbox_image.strip():
        errors.append("Docker image 不能为空。")
    if form.sandbox_network not in ALLOWED_DOCKER_NETWORKS:
        errors.append("Docker network 只能是 none 或 bridge。")
    if form.sandbox_worktree_mount not in ALLOWED_DOCKER_WORKTREE_MOUNTS:
        errors.append("Docker worktree mount 只能是 readonly 或 rw。")
    if form.sandbox_worktree_mount != "readonly":
        errors.append("Web UI 当前只允许 Docker worktree readonly 挂载。")
    if not MEMORY_LIMIT_PATTERN.match(form.sandbox_memory_limit.strip()):
        errors.append("Docker memory limit 需使用数字加可选单位，例如 512m 或 1g。")
    try:
        cpu_limit = float(form.sandbox_cpu_limit)
    except ValueError:
        errors.append("Docker CPU limit 必须是大于 0 的数字。")
        return
    if cpu_limit <= 0:
        errors.append("Docker CPU limit 必须大于 0。")


def _validate_docker_commands(form: TaskForm, errors: list[str]) -> None:
    for label, command in [
        ("Test command", form.check_command),
        ("Patch coder", form.patch_coder),
        ("Patch fixer", form.patch_fixer),
        ("Reviewer", form.reviewer),
    ]:
        if command.strip():
            _validate_docker_command_paths(command, label, errors)


def _validate_docker_command_paths(command: str, label: str, errors: list[str]) -> None:
    if WINDOWS_ABSOLUTE_PATH_PATTERN.search(command):
        errors.append(
            f"{label} uses a Windows host path. Docker commands must use /worktree, /run, /cache, or placeholders."
        )
        return
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        return
    for part in parts:
        normalized = part.strip("\"'")
        if not normalized.startswith("/"):
            continue
        if normalized.startswith(ALLOWED_DOCKER_ABSOLUTE_PATH_PREFIXES):
            continue
        errors.append(
            f"{label} uses unsupported Docker absolute path: {normalized}. Use /worktree, /run, or /cache."
        )
        return


def _validate_web_command(command: str, label: str, errors: list[str]) -> None:
    lowered = command.lower()
    forbidden_markers = ["rm -rf", "remove-item", "format ", "mkfs", "drop table", "truncate", "delete from"]
    if any(marker in lowered for marker in forbidden_markers):
        errors.append(f"{label} 包含高风险命令。")
        return
    try:
        shlex.split(command, posix=False)
    except ValueError as exc:
        errors.append(f"{label} 不是合法命令：{exc}")


def _start_background_run(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
    job_id = datetime.now().strftime("job-%Y%m%d-%H%M%S-%f")
    workspace_root = Path.cwd()
    db_path = workspace_root / JOBS_DB_PATH
    runs_dir = workspace_root / RUNS_DIR
    _write_job(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "message": "任务已提交，OMX/Codex 正在生成补丁。这个过程可能需要几十秒。",
            "task_path": str(task_path),
            "run_id": "",
            "started_at": datetime.now().isoformat(),
            "finished_at": "",
        },
    )

    def worker() -> None:
        try:
            state = _build_web_use_case(
                job_id,
                agent_mode=agent_mode,
                real_checks=real_checks,
                runs_dir=runs_dir,
            ).execute(
                RunTaskCommand(task_path=task_path)
            )
            if _job_was_stopped(job_id):
                return
            if state.status != RunStatus.DONE:
                _update_job(
                    job_id,
                    db_path=db_path,
                    status="failed",
                    message=f"任务未完成，停在 {state.current_phase} 阶段。请打开结果页查看报告。",
                    run_id=state.run_id,
                    finished_at=datetime.now().isoformat(),
                )
                return
            _update_job(
                job_id,
                db_path=db_path,
                status="done",
                message="任务已完成，正在打开结果页。",
                run_id=state.run_id,
                finished_at=datetime.now().isoformat(),
            )
        except Exception as exc:
            if _job_was_stopped(job_id):
                return
            if isinstance(exc, CommandCancelled):
                _update_job(
                    job_id,
                    db_path=db_path,
                    status="stopped",
                    message="底层命令已被停止。",
                    finished_at=datetime.now().isoformat(),
                )
                return
            _update_job(
                job_id,
                db_path=db_path,
                status="failed",
                message=f"任务启动失败：{exc}",
                finished_at=datetime.now().isoformat(),
            )

    threading.Thread(target=worker, daemon=True).start()
    return job_id


def _build_web_use_case(job_id: str, *, agent_mode: str, real_checks: bool, runs_dir: Path | None = None) -> RunTaskUseCase:
    heartbeat = FileHeartbeat()
    command_runner = SafeCommandRunner(
        heartbeat=heartbeat,
        cancellation_registry=WEB_CANCELLATION_REGISTRY,
        cancellation_key=_safe_id(job_id),
    )
    return RunTaskUseCase(
        task_loader=TaskLoader(),
        safety_policy=SafetyPolicy(),
        state_repository=FileStateRepository(runs_dir or RUNS_DIR),
        agent=build_agent(agent_mode, command_runner),
        check_runner=ShellCheckRunner(command_runner=command_runner) if real_checks else FakeCheckRunner(pass_all=True),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def _job_repository() -> SQLiteJobRepository:
    return SQLiteJobRepository(JOBS_DB_PATH)


def _read_job(job_id: str) -> dict[str, Any] | None:
    return _job_repository().get(_safe_id(job_id))


def _write_job(job_id: str, payload: dict[str, Any]) -> None:
    normalized = dict(payload)
    normalized["job_id"] = _safe_id(job_id)
    _job_repository().create(normalized)


def _update_job(job_id: str, db_path: Path | None = None, **updates: str) -> None:
    repository = SQLiteJobRepository(db_path) if db_path else _job_repository()
    repository.update(_safe_id(job_id), **updates)


def _job_was_stopped(job_id: str) -> bool:
    job = _read_job(job_id)
    return bool(job and str(job.get("status") or "") == "stopped")


def _load_recent_jobs() -> list[dict[str, Any]]:
    return [_build_recent_job(job) for job in _job_repository().list_recent(limit=20)]


def _build_recent_job(job: dict[str, Any]) -> dict[str, Any]:
    reconciled = _reconcile_job(job)
    status = str(reconciled.get("status") or "")
    reconciled["status_label"] = _status_label(status)
    reconciled["status_class"] = _status_css_class(status)
    return reconciled


def _load_jobs_page(*, status: str, limit: int, offset: int) -> list[dict[str, Any]]:
    status_filter = None if status == "all" else status
    return [_reconcile_job(job) for job in _job_repository().list_page(limit=limit, offset=offset, status=status_filter)]


def _load_task_manager_jobs(status: str) -> list[dict[str, str]]:
    status_filter = None if status == "all" else status
    raw_jobs = [_reconcile_job(job) for job in _job_repository().list_page(limit=500, offset=0, status=status_filter)]
    return [_build_task_manager_job(job) for job in raw_jobs]


def _count_task_manager_quality(jobs: list[dict[str, str]]) -> dict[str, int]:
    counts = {"all": len(jobs), "passed": 0, "failed": 0, "missing": 0}
    for job in jobs:
        quality_class = job.get("quality_class", "")
        if quality_class == "done":
            counts["passed"] += 1
        elif quality_class == "failed":
            counts["failed"] += 1
        else:
            counts["missing"] += 1
    return counts


def _count_task_manager_rerun(jobs: list[dict[str, str]]) -> dict[str, int]:
    counts = {"all": len(jobs), "available": 0, "unavailable": 0}
    for job in jobs:
        if job.get("can_rerun"):
            counts["available"] += 1
        elif job.get("rerun_unavailable_reason"):
            counts["unavailable"] += 1
    return counts


def _filter_task_manager_jobs(jobs: list[dict[str, str]], quality: str, rerun: str, query: str) -> list[dict[str, str]]:
    jobs = [job for job in jobs if _task_manager_quality_matches(job, quality)]
    jobs = [job for job in jobs if _task_manager_rerun_matches(job, rerun)]
    if not query:
        return jobs
    needle = query.lower()
    return [job for job in jobs if _task_manager_job_matches(job, needle)]


def _task_manager_quality_matches(job: dict[str, str], quality: str) -> bool:
    if quality == "all":
        return True
    quality_class = job.get("quality_class", "")
    if quality == "missing":
        return quality_class == "unknown"
    if quality == "passed":
        return quality_class == "done"
    if quality == "failed":
        return quality_class == "failed"
    return True


def _task_manager_rerun_matches(job: dict[str, str], rerun: str) -> bool:
    if rerun == "all":
        return True
    if rerun == "available":
        return bool(job.get("can_rerun"))
    if rerun == "unavailable":
        return bool(job.get("rerun_unavailable_reason"))
    return True


def _unique_safe_ids(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    safe_values: list[str] = []
    for value in values:
        safe_value = _safe_id(str(value))
        if safe_value and safe_value not in seen:
            seen.add(safe_value)
            safe_values.append(safe_value)
    return safe_values


def _batch_stop_jobs(job_ids: list[str]) -> dict[str, int | str]:
    processed = 0
    skipped = 0
    failed = 0
    for job_id in job_ids:
        job = _read_job(job_id)
        if not job or str(job.get("status") or "") != "running":
            skipped += 1
            continue
        try:
            cancelled_running_process = WEB_CANCELLATION_REGISTRY.cancel(job_id)
            _update_job(
                job_id,
                status="stopped",
                message=(
                    "底层命令已收到终止信号。"
                    if cancelled_running_process
                    else "已收到批量停止请求。当前没有可终止的底层命令，Web Job 状态已冻结。"
                ),
                finished_at=datetime.now().isoformat(),
            )
            processed += 1
        except Exception:
            failed += 1
    return {"label": "批量停止", "processed": processed, "skipped": skipped, "failed": failed}


def _batch_delete_jobs(job_ids: list[str]) -> dict[str, int | str]:
    processed = 0
    failed = 0
    repository = _job_repository()
    for job_id in job_ids:
        try:
            repository.delete(job_id)
            processed += 1
        except Exception:
            failed += 1
    return {"label": "批量删除", "processed": processed, "skipped": 0, "failed": failed}


def _batch_rerun_jobs(job_ids: list[str]) -> dict[str, int | str]:
    processed = 0
    skipped = 0
    failed = 0
    for job_id in job_ids:
        job = _read_job(job_id)
        if not job or str(job.get("status") or "") == "running":
            skipped += 1
            continue
        run_id = str(job.get("run_id") or "")
        task_path = _task_path_for_job(job, run_id)
        if not task_path:
            skipped += 1
            continue
        try:
            _rerun_task_path(task_path)
            processed += 1
        except Exception:
            failed += 1
    return {"label": "批量重新运行", "processed": processed, "skipped": skipped, "failed": failed}


def _empty_batch_summary(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "processed_job_ids": [],
        "skipped_job_ids": [],
        "failed_job_ids": [],
        "run_ids": [],
        "reasons": {},
    }


def _record_batch_processed(summary: dict[str, Any], job_id: str, job: dict[str, Any] | None) -> None:
    summary["processed"] += 1
    summary["processed_job_ids"].append(job_id)
    for run_id in _job_run_ids([job]):
        if run_id not in summary["run_ids"]:
            summary["run_ids"].append(run_id)


def _record_batch_skipped(summary: dict[str, Any], job_id: str, reason: str) -> None:
    summary["skipped"] += 1
    summary["skipped_job_ids"].append(job_id)
    summary["reasons"][job_id] = reason


def _record_batch_failed(summary: dict[str, Any], job_id: str, reason: str) -> None:
    summary["failed"] += 1
    summary["failed_job_ids"].append(job_id)
    summary["reasons"][job_id] = reason


def _batch_stop_jobs(job_ids: list[str]) -> dict[str, Any]:
    summary = _empty_batch_summary("批量停止")
    for job_id in job_ids:
        job = _read_job(job_id)
        if not job or str(job.get("status") or "") != "running":
            _record_batch_skipped(summary, job_id, "job missing or not running")
            continue
        try:
            cancelled_running_process = WEB_CANCELLATION_REGISTRY.cancel(job_id)
            _update_job(
                job_id,
                status="stopped",
                message=(
                    "底层命令已收到终止信号。"
                    if cancelled_running_process
                    else "已收到批量停止请求。当前没有可终止的底层命令，Web Job 状态已冻结。"
                ),
                finished_at=datetime.now().isoformat(),
            )
            _record_batch_processed(summary, job_id, job)
        except Exception:
            _record_batch_failed(summary, job_id, "exception")
    return summary


def _batch_delete_jobs(job_ids: list[str]) -> dict[str, Any]:
    summary = _empty_batch_summary("批量删除")
    repository = _job_repository()
    for job_id in job_ids:
        job = _read_job(job_id)
        try:
            repository.delete(job_id)
            _record_batch_processed(summary, job_id, job)
        except Exception:
            _record_batch_failed(summary, job_id, "exception")
    return summary


def _batch_rerun_jobs(job_ids: list[str]) -> dict[str, Any]:
    summary = _empty_batch_summary("批量重新运行")
    for job_id in job_ids:
        job = _read_job(job_id)
        if not job or str(job.get("status") or "") == "running":
            _record_batch_skipped(summary, job_id, "job missing or running")
            continue
        run_id = str(job.get("run_id") or "")
        task_path = _task_path_for_job(job, run_id)
        if not task_path:
            _record_batch_skipped(summary, job_id, "missing task.json")
            continue
        try:
            new_job_id = _rerun_task_path(task_path)
            _record_batch_processed(summary, job_id, job)
            summary["processed_job_ids"].append(new_job_id)
        except Exception:
            _record_batch_failed(summary, job_id, "exception")
    return summary


def _task_manager_job_matches(job: dict[str, str], needle: str) -> bool:
    haystack = " ".join(
        [
            job.get("task_name", ""),
            job.get("task_id", ""),
            job.get("job_id", ""),
            job.get("run_id", ""),
            job.get("template_label", ""),
            job.get("template_id", ""),
            job.get("execution_backend", ""),
            job.get("agent_mode", ""),
            job.get("quality_label", ""),
            job.get("quality_reason", ""),
            job.get("review_issue_label", ""),
            job.get("review_issue_summary", ""),
            job.get("rerun_unavailable_reason", ""),
            job.get("status", ""),
        ]
    ).lower()
    return needle in haystack


def _count_jobs(status: str) -> int:
    status_filter = None if status == "all" else status
    return _job_repository().count(status_filter)


def _find_running_job_for_template(template_id: str) -> dict[str, Any] | None:
    selected_template_id = normalize_template_id(template_id)
    for job in _load_recent_jobs():
        if str(job.get("status") or "") != "running":
            continue
        if _template_id_from_job(job) == selected_template_id:
            return job
    return None


def _build_task_manager_job(job: dict[str, Any]) -> dict[str, str]:
    job_id = str(job.get("job_id") or "")
    run_id = str(job.get("run_id") or "")
    status = str(job.get("status") or "unknown")
    task_context = _load_job_task_context(job, run_id)
    quality_summary = _load_task_manager_quality_summary(run_id)
    review_issue_label = f"Review issues: {_count_review_issues(run_id)}" if run_id else "Review issues: 0"
    review_issue_summary = _first_review_issue_summary(run_id)
    can_rerun = status != "running" and bool(_task_path_for_job(job, run_id))
    return {
        "job_id": job_id,
        "task_name": task_context.get("title") or task_context.get("task_id") or job_id,
        "task_id": task_context.get("task_id") or "",
        "status": status,
        "status_label": _status_label(status),
        "status_class": _status_css_class(status),
        "run_id": run_id,
        "message": str(job.get("message") or ""),
        "started_at": str(job.get("started_at") or ""),
        "updated_at": str(job.get("updated_at") or ""),
        "template_label": task_context.get("template_label") or task_context.get("template_id") or "历史任务",
        "template_id": task_context.get("template_id") or "",
        "execution_backend": task_context.get("execution_backend") or "旧任务未记录",
        "agent_mode": task_context.get("agent_mode") or "",
        "quality_label": quality_summary["label"],
        "quality_reason": quality_summary["reason"],
        "quality_class": quality_summary["css_class"],
        "review_issue_label": review_issue_label,
        "review_issue_summary": review_issue_summary,
        "detail_url": f"/runs/{run_id}" if status == "done" and run_id else f"/jobs/{job_id}",
        "run_detail_url": f"/runs/{run_id}" if run_id else "",
        "evidence_url": f"/runs/{run_id}#validation-evidence" if run_id else "",
        "can_stop": "1" if status == "running" else "",
        "can_rerun": "1" if can_rerun else "",
        "rerun_unavailable_reason": "" if can_rerun or status == "running" else "缺少原始 task.json",
    }


def _count_review_issues(run_id: str) -> int:
    if not run_id:
        return 0
    review = _read_first_json_optional((RUNS_DIR / run_id).glob("attempts/*/review.json"))
    issues = review.get("issues") if review else None
    return len(issues) if isinstance(issues, list) else 0


def _first_review_issue_summary(run_id: str) -> str:
    if not run_id:
        return ""
    review = _read_first_json_optional((RUNS_DIR / run_id).glob("attempts/*/review.json"))
    issues = review.get("issues") if review else None
    if not isinstance(issues, list):
        return ""
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "unknown")
        message = str(issue.get("message") or "").strip()
        location = _review_issue_location(issue)
        if not message and location == "-":
            continue
        issue_label = f"{severity}: {message}" if message else severity
        return f"First issue: {location} / {issue_label}"
    return ""


def _review_issue_location(issue: dict[str, object]) -> str:
    location_parts = [str(issue.get("file") or "")]
    if issue.get("line") not in (None, ""):
        location_parts.append(str(issue.get("line")))
    return ":".join(part for part in location_parts if part) or "-"


def _load_task_manager_quality_summary(run_id: str) -> dict[str, str]:
    if not run_id:
        return {"label": "未记录", "reason": "等待 run_id", "css_class": "unknown"}
    report = _read_first_json_optional((RUNS_DIR / run_id).glob("attempts/*/quality_report.json"))
    if not report:
        return {"label": "未记录", "reason": "未找到 quality_report.json", "css_class": "unknown"}
    score = report.get("quality_score", "unknown")
    decision = str(report.get("decision") or "unknown")
    passed = bool(report.get("passed"))
    reason = str(report.get("reason") or "未记录")
    return {
        "label": f"{score} / {decision}",
        "reason": reason,
        "css_class": "done" if passed or decision == "done" else "failed",
    }


def _build_job_task_meta(job: dict[str, Any], task_context: dict[str, str]) -> dict[str, str]:
    return {
        "task_name": task_context.get("title") or task_context.get("task_id") or str(job.get("job_id") or ""),
        "task_id": task_context.get("task_id") or "未记录",
        "template": task_context.get("template_label") or task_context.get("template_id") or "历史任务",
        "backend": task_context.get("execution_backend") or "旧任务未记录",
        "agent": task_context.get("agent_mode") or "agent 未记录",
        "started_at": str(job.get("started_at") or "未记录"),
        "updated_at": str(job.get("updated_at") or "未记录"),
    }


def _build_run_task_meta(state: RunState, task_context: dict[str, str]) -> dict[str, str]:
    return {
        "task_name": task_context.get("title") or task_context.get("task_id") or state.task_id,
        "task_id": task_context.get("task_id") or state.task_id,
        "template": task_context.get("template_label") or task_context.get("template_id") or "历史任务",
        "backend": task_context.get("execution_backend") or "旧任务未记录",
        "agent": task_context.get("agent_mode") or "agent 未记录",
        "started_at": state.started_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    }


def _build_job_failure_hint(job: dict[str, Any], progress: dict[str, str] | None) -> dict[str, str]:
    status = str(job.get("status") or "")
    if status not in {"failed", "stopped"}:
        return {"enabled": ""}
    phase = (progress or {}).get("phase") or "未记录"
    message = str(job.get("message") or "任务未完成。")
    return {
        "enabled": "1",
        "title": "失败原因",
        "phase": phase,
        "reason": message,
        "next_action": _suggest_next_action(phase, message),
    }


def _build_rerun_error(code: str) -> dict[str, str]:
    if code == "missing_task":
        return {
            "enabled": "1",
            "title": "无法重新运行",
            "message": "没有找到该任务的原始 task.json，通常是早期历史任务或任务文件已被移动。",
            "next_action": "返回任务管理重新创建任务，或打开保留的 run 详情复制启动配置。",
        }
    return {"enabled": ""}


def _build_run_failure_hint(
    state: RunState,
    final_report: str,
    phase_log: str,
    validation_evidence: dict[str, object] | None = None,
) -> dict[str, str]:
    status = str(state.status)
    if status not in {"halted", "retrying"}:
        return {"enabled": ""}
    phase = str(state.current_phase or "未记录")
    reason = _extract_failure_reason(final_report) or _last_nonempty_line(phase_log) or f"任务停在 {phase} 阶段。"
    return {
        "enabled": "1",
        "title": "失败原因",
        "phase": phase,
        "reason": reason,
        "quality_reason": _validation_quality_reason(validation_evidence),
        "review_issue": _validation_first_review_issue(validation_evidence),
        "next_action": _suggest_next_action(phase, reason),
    }


def _validation_quality_reason(validation_evidence: dict[str, object] | None) -> str:
    if not validation_evidence:
        return ""
    quality_report = str(validation_evidence.get("quality_report") or "")
    if not quality_report or quality_report == "not recorded":
        return ""
    parts = [part.strip() for part in quality_report.split(" / ") if part.strip()]
    return parts[-1] if parts else quality_report


def _validation_first_review_issue(validation_evidence: dict[str, object] | None) -> str:
    if not validation_evidence:
        return ""
    review_issue_rows = validation_evidence.get("review_issue_rows")
    if not isinstance(review_issue_rows, list):
        return ""
    for issue in review_issue_rows:
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "unknown")
        location = str(issue.get("location") or "-")
        message = str(issue.get("message") or "").strip()
        if not message and location == "-":
            continue
        issue_label = f"{severity}: {message}" if message else severity
        return f"{location} / {issue_label}"
    return ""


def _build_execution_chain(
    task_context: dict[str, str],
    *,
    status: str,
    phase: str,
    run_id: str,
    docker_evidence: dict[str, object],
    patches: list[dict[str, object]],
) -> dict[str, object]:
    backend = task_context.get("execution_backend") or "未记录"
    agent_mode = task_context.get("agent_mode") or "未记录"
    preset = task_context.get("command_preset") or "custom/未记录"
    patch_coder = task_context.get("patch_coder") or "未记录"
    has_patches = bool(patches)
    pending_patches = sum(1 for patch in patches if patch.get("status") == "pending")
    applied_patches = sum(1 for patch in patches if patch.get("status") == "applied")
    docker_enabled = bool(docker_evidence.get("enabled")) or backend == "docker"
    agent_label = _agent_chain_label(agent_mode)
    return {
        "headline": f"{backend} / {agent_mode}",
        "agent_label": agent_label,
        "backend_label": "Docker sandbox" if docker_enabled else "本地执行",
        "command_preset": preset,
        "patch_coder": patch_coder,
        "run_label": run_id or "创建中",
        "phase": phase or "未记录",
        "quality_label": _quality_gate_label(status, phase),
        "patch_label": _patch_chain_label(has_patches, pending_patches, applied_patches),
        "docker_label": _docker_chain_label(docker_evidence, backend),
        "nodes": [
            {
                "title": "Web UI",
                "status": "已提交",
                "detail": task_context.get("task_id") or "任务 ID 未记录",
                "tone": "success",
            },
            {
                "title": "Orchestrator",
                "status": phase or status or "等待 run",
                "detail": f"Run：{run_id or '创建中'}",
                "tone": _chain_tone(status, phase),
            },
            {
                "title": "Agent",
                "status": agent_label,
                "detail": f"Preset：{preset}",
                "tone": "info" if agent_mode != "未记录" else "warning",
            },
            {
                "title": "执行环境",
                "status": "Docker sandbox" if docker_enabled else "Local",
                "detail": _docker_chain_label(docker_evidence, backend),
                "tone": "success" if docker_evidence.get("enabled") else "info",
            },
            {
                "title": "Patch",
                "status": _patch_chain_label(has_patches, pending_patches, applied_patches),
                "detail": "补丁审批区记录实际变更" if has_patches else "暂无补丁记录",
                "tone": "warning" if pending_patches else ("success" if has_patches else "info"),
            },
            {
                "title": "Quality Gate",
                "status": _quality_gate_label(status, phase),
                "detail": "Hard check / review / gate",
                "tone": _chain_tone(status, phase),
            },
        ],
    }


def _agent_chain_label(agent_mode: str) -> str:
    if agent_mode == "codex":
        return "Codex 直接执行"
    if agent_mode == "omx":
        return "OMX 入口"
    if agent_mode == "omx_patch":
        return "OMX Patch Agent"
    if agent_mode == "omx_team_patch":
        return "OMX Team 编排"
    if agent_mode == "shell":
        return "Shell Agent"
    if agent_mode == "mock":
        return "Mock Agent"
    return "Agent 未记录"


def _docker_chain_label(docker_evidence: dict[str, object], backend: str) -> str:
    if docker_evidence.get("enabled"):
        count = docker_evidence.get("count") or 0
        image = docker_evidence.get("image") or "镜像未记录"
        return f"已记录 {count} 次 Docker 执行 / {image}"
    if backend == "docker":
        return "计划使用 Docker，等待执行证据"
    return "未使用 Docker sandbox"


def _patch_chain_label(has_patches: bool, pending_count: int, applied_count: int) -> str:
    if pending_count:
        return f"待审批 {pending_count} 个"
    if applied_count:
        return f"已批准 {applied_count} 个"
    if has_patches:
        return "已有补丁记录"
    return "暂无补丁"


def _quality_gate_label(status: str, phase: str) -> str:
    if status == "done":
        return "已通过"
    if status in {"failed", "halted"}:
        return "未通过"
    if status == "stopped":
        return "已停止"
    return phase or "运行中"


def _chain_tone(status: str, phase: str) -> str:
    text = f"{status} {phase}".lower()
    if any(keyword in text for keyword in ("done", "passed", "success")):
        return "success"
    if any(keyword in text for keyword in ("failed", "halted", "error")):
        return "danger"
    if "stopped" in text or "pending" in text or "approval" in text:
        return "warning"
    return "info"


def _build_execution_summary(
    state: RunState,
    patches: list[dict[str, object]],
    docker_evidence: dict[str, object],
    phase_timeline: list[dict[str, str]],
) -> dict[str, str]:
    pending_count = sum(1 for patch in patches if patch.get("status") == "pending")
    applied_count = sum(1 for patch in patches if patch.get("status") == "applied")
    rejected_count = sum(1 for patch in patches if patch.get("status") == "rejected")
    last_event = phase_timeline[-1] if phase_timeline else {}
    docker_label = "有记录" if docker_evidence.get("enabled") else "无记录"
    if docker_evidence.get("enabled"):
        docker_label = f"{docker_evidence.get('count', 0)} 次 / {docker_evidence.get('image') or '镜像未记录'}"
    return {
        "status": str(state.status),
        "status_label": _status_label(str(state.status)),
        "phase": str(state.current_phase or "未记录"),
        "attempt": f"{state.attempt}/{state.max_attempts}",
        "patch_stats": f"待审批 {pending_count} / 已批准 {applied_count} / 已拒绝 {rejected_count}",
        "docker": docker_label,
        "last_event": str(last_event.get("summary") or "暂无阶段事件"),
        "updated_at": state.updated_at.isoformat(),
    }


def _build_run_artifacts(run_dir: Path, task_context: dict[str, str], patches: list[dict[str, object]]) -> dict[str, object]:
    files = {
        "task": run_dir / "task.json",
        "state": run_dir / "run_state.json",
        "final_report": run_dir / "final_report.md",
        "phase_log": run_dir / "logs" / "phase.log",
        "heartbeat_log": run_dir / "logs" / "heartbeat.log",
        "agent_log": run_dir / "logs" / "agent.log",
        "docker_log": run_dir / "logs" / "docker_sandbox.jsonl",
    }
    artifact_rows = [
        _artifact_row("任务文件", files["task"]),
        _artifact_row("运行状态", files["state"]),
        _artifact_row("最终报告", files["final_report"]),
        _artifact_row("阶段日志", files["phase_log"]),
        _artifact_row("心跳日志", files["heartbeat_log"]),
        _artifact_row("Agent 日志", files["agent_log"]),
        _artifact_row("Docker 日志", files["docker_log"]),
    ]
    changed_files = _changed_files_from_patches(patches)
    return {
        "run_dir": run_dir.as_posix(),
        "worktree": task_context.get("worktree_path") or "未记录",
        "rows": artifact_rows,
        "patch_count": str(len(patches)),
        "patch_rows": [_patch_artifact_row(patch) for patch in patches],
        "changed_files": changed_files,
        "changed_files_label": ", ".join(changed_files) if changed_files else "暂无变更文件记录",
    }


def _load_validation_evidence(run_dir: Path, attempt: int) -> dict[str, object]:
    attempt_dir = run_dir / "attempts" / f"{attempt:03d}"
    hard_checks = _read_json_optional(attempt_dir / "hard_checks.json")
    review = _read_json_optional(attempt_dir / "review.json")
    quality_report = _read_json_optional(attempt_dir / "quality_report.json")
    hard_check_label, hard_check_rows = _format_hard_check_evidence(hard_checks)
    review_label, review_issue_rows = _format_review_evidence(review)
    return {
        "hard_checks": hard_check_label,
        "hard_check_rows": hard_check_rows,
        "review": review_label,
        "review_issue_rows": review_issue_rows,
        "quality_report": _format_quality_report_evidence(quality_report),
    }


def _format_hard_check_evidence(payload: dict[str, object] | None) -> tuple[str, list[dict[str, str]]]:
    if not payload:
        return "not recorded", []
    commands = payload.get("commands")
    if not isinstance(commands, list) or not commands:
        return "not recorded", []
    passed = all(bool(command.get("passed")) for command in commands if isinstance(command, dict))
    command_labels = []
    rows: list[dict[str, str]] = []
    for command in commands:
        if not isinstance(command, dict):
            continue
        name = str(command.get("name") or "check")
        status = "passed" if command.get("passed") else "failed"
        exit_code = command.get("exit_code", "")
        command_labels.append(f"{name}:{status}:exit={exit_code}")
        rows.append(
            {
                "name": name,
                "status": status,
                "command": str(command.get("command") or ""),
                "exit_code": str(exit_code),
                "duration": str(command.get("duration_seconds") or "0"),
                "score": str(command.get("score") or "0"),
            }
        )
    return f"{'passed' if passed else 'failed'} / " + ", ".join(command_labels), rows


def _format_review_evidence(payload: dict[str, object] | None) -> tuple[str, list[dict[str, str]]]:
    if not payload:
        return "not recorded", []
    passed = payload.get("pass", payload.get("pass_"))
    confidence = payload.get("confidence", "unknown")
    summary = str(payload.get("summary") or "").strip() or "no summary"
    blocking = payload.get("blocking", "unknown")
    issue_rows: list[dict[str, str]] = []
    issues = payload.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            location_parts = [str(issue.get("file") or "")]
            if issue.get("line") not in (None, ""):
                location_parts.append(str(issue.get("line")))
            issue_rows.append(
                {
                    "severity": str(issue.get("severity") or ""),
                    "severity_class": _review_issue_severity_class(issue.get("severity")),
                    "category": str(issue.get("category") or ""),
                    "location": ":".join(part for part in location_parts if part) or "-",
                    "message": str(issue.get("message") or ""),
                    "suggestion": str(issue.get("suggestion") or ""),
                }
            )
    return f"pass={passed} / confidence={confidence} / blocking={blocking} / {summary}", issue_rows


def _review_issue_severity_class(severity: object) -> str:
    normalized = str(severity or "").strip().lower()
    if normalized in {"blocker", "critical"}:
        return "severity-blocker"
    if normalized in {"major", "high"}:
        return "severity-major"
    if normalized in {"minor", "medium", "low"}:
        return "severity-minor"
    return "severity-unknown"


def _format_quality_report_evidence(payload: dict[str, object] | None) -> str:
    if not payload:
        return "not recorded"
    decision = payload.get("decision", "unknown")
    score = payload.get("quality_score", "unknown")
    passed = payload.get("passed", "unknown")
    reason = str(payload.get("reason") or "").strip() or "no reason"
    return f"decision={decision} / score={score} / passed={passed} / {reason}"


def _build_run_audit_markdown(
    *,
    state: RunState,
    run_dir: Path,
    patches: list[dict[str, object]],
    task_context: dict[str, str],
    final_report: str,
    phase_log: str,
    docker_evidence: dict[str, object],
    phase_timeline: list[dict[str, str]],
    validation_evidence: dict[str, object],
) -> str:
    execution_summary = _build_execution_summary(state, patches, docker_evidence, phase_timeline)
    run_artifacts = _build_run_artifacts(run_dir, task_context, patches)
    task_meta = _build_run_task_meta(state, task_context)
    failure_hint = _build_run_failure_hint(state, final_report, phase_log, validation_evidence)
    quality_reason = _validation_quality_reason(validation_evidence)
    first_review_issue = _validation_first_review_issue(validation_evidence)
    lines = [
        f"# Run Audit: {state.run_id}",
        "",
        "## Summary",
        f"- Task: {task_meta['task_name']}",
        f"- Task ID: {task_meta['task_id']}",
        f"- Status: {execution_summary['status_label']} / {execution_summary['status']}",
        f"- Phase: {execution_summary['phase']}",
        f"- Attempt: {execution_summary['attempt']}",
        f"- Updated At: {execution_summary['updated_at']}",
        "",
        "## Execution",
        f"- Template: {task_meta['template']}",
        f"- Backend: {task_meta['backend']}",
        f"- Agent: {task_meta['agent']}",
        f"- Command Preset: {task_context.get('command_preset') or 'custom/unknown'}",
        f"- Test Command: {task_context.get('test_command') or 'unknown'}",
        f"- Worktree: {run_artifacts['worktree']}",
        f"- Allowed Paths: {task_context.get('allowed_paths') or 'unknown'}",
        "",
        "## Quality Gate",
        f"- Decision: {_quality_gate_label(str(state.status), str(state.current_phase))}",
        f"- Patch Stats: {execution_summary['patch_stats']}",
        f"- Last Event: {execution_summary['last_event']}",
        f"- Hard Checks: {validation_evidence['hard_checks']}",
        f"- Review: {validation_evidence['review']}",
        f"- Quality Report: {validation_evidence['quality_report']}",
        *( [f"- Quality Reason: {quality_reason}"] if quality_reason else [] ),
        *( [f"- First Review Issue: {first_review_issue}"] if first_review_issue else [] ),
        "",
        "## Docker Evidence",
    ]
    if failure_hint.get("enabled"):
        lines.extend(
            [
                "## Failure Summary",
                f"- Phase: {failure_hint.get('phase') or 'unknown'}",
                f"- Reason: {failure_hint.get('reason') or 'unknown'}",
                *( [f"- Quality Gate: {failure_hint['quality_reason']}"] if failure_hint.get("quality_reason") else [] ),
                *( [f"- First Review Issue: {failure_hint['review_issue']}"] if failure_hint.get("review_issue") else [] ),
                f"- Next Action: {failure_hint.get('next_action') or 'unknown'}",
                "",
            ]
        )
    review_issue_rows = validation_evidence.get("review_issue_rows")
    if isinstance(review_issue_rows, list) and review_issue_rows:
        lines.extend(["## Review Issues"])
        for issue in review_issue_rows:
            if not isinstance(issue, dict):
                continue
            lines.append(
                "- "
                f"{issue.get('severity') or 'unknown'} / "
                f"{issue.get('category') or 'unknown'} / "
                f"{issue.get('location') or '-'} / "
                f"{issue.get('message') or ''}"
                + (f" / suggestion={issue.get('suggestion')}" if issue.get("suggestion") else "")
            )
        lines.append("")

    if docker_evidence.get("enabled"):
        lines.extend(
            [
                f"- Enabled: yes",
                f"- Image: {docker_evidence.get('image') or 'unknown'}",
                f"- Count: {docker_evidence.get('count') or 0}",
                f"- Network: {docker_evidence.get('network') or 'unknown'}",
                f"- Worktree Mount: {docker_evidence.get('worktree_mount') or 'unknown'}",
                f"- Last Phase: {docker_evidence.get('phase') or 'unknown'}",
                f"- Last Exit Code: {docker_evidence.get('exit_code') or 'unknown'}",
            ]
        )
    else:
        lines.append("- Enabled: no")

    lines.extend(
        [
            "",
            "## Artifacts",
            f"- Run Dir: {run_artifacts['run_dir']}",
            f"- Changed Files: {run_artifacts['changed_files_label']}",
        ]
    )
    for row in run_artifacts["rows"]:
        lines.append(f"- {row['label']}: {row['status']} ({row['path']})")

    lines.extend(["", "## Patches"])
    if run_artifacts["patch_rows"]:
        for patch in run_artifacts["patch_rows"]:
            lines.append(
                f"- {patch['name']}: {patch['status']} / risk={patch['risk_score']} / files={patch['files']}"
            )
    else:
        lines.append("- none")

    if phase_timeline:
        lines.extend(["", "## Phase Timeline"])
        for event in phase_timeline[-10:]:
            lines.append(f"- {event.get('summary') or event.get('message') or 'event'}")

    lines.extend(["", "## Final Report"])
    lines.append(final_report.strip() if final_report.strip() else "No final report recorded.")
    lines.append("")
    return "\n".join(lines)


def _artifact_row(label: str, path: Path) -> dict[str, str]:
    exists = path.exists()
    return {
        "label": label,
        "path": path.as_posix(),
        "status": "已生成" if exists else "暂无记录",
        "size": _format_file_size(path.stat().st_size) if exists and path.is_file() else "",
    }


def _patch_artifact_row(patch: dict[str, object]) -> dict[str, str]:
    return {
        "name": str(patch.get("patch") or "未记录"),
        "status": str(patch.get("status") or "未记录"),
        "risk_score": str(patch.get("risk_score") or "未记录"),
        "files": str(patch.get("files") or "暂无变更文件记录"),
    }


def _changed_files_from_patches(patches: list[dict[str, object]]) -> list[str]:
    changed: list[str] = []
    seen: set[str] = set()
    for patch in patches:
        files = str(patch.get("files") or "")
        for file in (item.strip() for item in files.split(",") if item.strip()):
            if file not in seen:
                seen.add(file)
                changed.append(file)
    return changed


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def _parse_phase_timeline(phase_log: str) -> list[dict[str, str]]:
    timeline: list[dict[str, str]] = []
    for line in phase_log.splitlines():
        raw = line.strip()
        if not raw:
            continue
        fields = _parse_log_fields(raw)
        timestamp = _extract_log_timestamp(raw)
        phase = fields.get("phase") or _fallback_phase_label(raw)
        event = fields.get("event") or "log"
        attempt = fields.get("attempt") or ""
        reason = fields.get("reason") or fields.get("message") or ""
        summary = _format_timeline_summary(phase, event, attempt, reason)
        timeline.append(
            {
                "time": timestamp,
                "phase": phase,
                "event": event,
                "attempt": attempt,
                "message": reason or raw,
                "summary": summary,
                "tone": _timeline_tone(event, raw),
            }
        )
    return timeline[-20:]


def _parse_log_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r"(?P<key>[A-Za-z_][\w.-]*)=(?P<value>\"[^\"]*\"|'[^']*'|\S+)", line):
        value = match.group("value").strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        fields[match.group("key")] = value
    return fields


def _extract_log_timestamp(line: str) -> str:
    first = line.split(maxsplit=1)[0] if line else ""
    return first if re.match(r"^\d{4}-\d{2}-\d{2}", first) else ""


def _fallback_phase_label(line: str) -> str:
    first = line.split(maxsplit=1)[0] if line else ""
    return first if first else "未记录"


def _format_timeline_summary(phase: str, event: str, attempt: str, reason: str) -> str:
    attempt_text = f" / 第 {attempt} 次" if attempt else ""
    reason_text = f" / {reason}" if reason else ""
    return f"{phase}：{event}{attempt_text}{reason_text}"


def _timeline_tone(event: str, line: str) -> str:
    text = f"{event} {line}".lower()
    if any(keyword in text for keyword in ("halt", "failed", "error", "exception", "timeout")):
        return "danger"
    if any(keyword in text for keyword in ("passed", "success", "done", "end", "complete")):
        return "success"
    if any(keyword in text for keyword in ("retry", "warning", "pending")):
        return "warning"
    return "info"


def _extract_failure_reason(final_report: str) -> str:
    for line in final_report.splitlines():
        stripped = line.strip().strip("- ")
        if not stripped:
            continue
        lowered = stripped.lower()
        if "reason" in lowered or "failed" in lowered or "halt" in lowered or "失败" in stripped or "停止" in stripped:
            return stripped
    return _last_nonempty_line(final_report)


def _last_nonempty_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _suggest_next_action(phase: str, reason: str) -> str:
    text = f"{phase} {reason}".lower()
    if "patch requires approval" in text or "pending" in text or "审批" in reason:
        return "查看补丁审批区，确认风险后批准并验证或拒绝。"
    if "hard_checks" in text or "check:" in text or "test" in text or "测试" in reason:
        return "先查看最终结论和阶段日志，确认测试失败原因后重新运行或调整任务。"
    if "review" in text or "json" in text:
        return "查看 Agent 输出和 review JSON，确认模型输出格式后重新运行。"
    if "safety" in text or "安全" in reason:
        return "检查允许路径、命令白名单和权限配置。"
    if "code" in text or "agent" in text:
        return "查看 Agent 日志，确认模型命令或 patch 输出是否有效。"
    return "先查看最终结论，再展开诊断日志定位原因。"


def _count_jobs_by_status() -> dict[str, int]:
    return _job_repository().counts_by_status()


def _tasks_query(
    *,
    status: str,
    page: int,
    page_size: int,
    q: str = "",
    quality: str = "all",
    rerun: str = "all",
) -> str:
    normalized_status = status if status in {"all", "running", "done", "failed", "stopped"} else "all"
    normalized_quality = quality if quality in {"all", "passed", "failed", "missing"} else "all"
    normalized_rerun = rerun if rerun in {"all", "available", "unavailable"} else "all"
    normalized_page = max(page, 1)
    normalized_page_size = min(max(page_size, 5), 50)
    return urlencode(
        {
            "status": normalized_status,
            "quality": normalized_quality,
            "rerun": normalized_rerun,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "q": q.strip(),
        }
    )


def _tasks_url(
    *,
    status: str,
    page: int,
    page_size: int,
    q: str = "",
    quality: str = "all",
    rerun: str = "all",
) -> str:
    return f"/tasks?{_tasks_query(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q)}"


def _redirect_to_tasks_with_batch_notice(
    notice: str,
    *,
    status: str,
    quality: str,
    rerun: str,
    page: int,
    page_size: int,
    q: str,
) -> RedirectResponse:
    url = _tasks_url(status=status, quality=quality, rerun=rerun, page=page, page_size=page_size, q=q)
    return RedirectResponse(url=f"{url}&{urlencode({'batch': notice})}", status_code=303)


def _task_request_context(
    *,
    status: str = "all",
    quality: str = "all",
    rerun: str = "all",
    page: int = 1,
    page_size: int = 10,
    q: str = "",
) -> dict[str, str | int]:
    return {"status": status, "quality": quality, "rerun": rerun, "page": page, "page_size": page_size, "q": q}


def _append_batch_web_job_audit(
    *,
    action: str,
    selected_job_ids: list[str],
    summary: dict[str, Any],
    request_context: dict[str, Any],
) -> None:
    _append_web_job_audit(
        WebJobAuditEvent(
            event_type=f"batch_{action}" if action in {"stop", "delete", "rerun"} else "batch_unknown",
            request_context=request_context,
            selected_job_ids=selected_job_ids,
            processed_job_ids=list(summary.get("processed_job_ids") or []),
            skipped_job_ids=list(summary.get("skipped_job_ids") or []),
            failed_job_ids=list(summary.get("failed_job_ids") or []),
            run_ids=list(summary.get("run_ids") or []),
            message=str(summary.get("label") or ""),
            details={"reasons": summary.get("reasons") or {}},
        )
    )


def _append_web_job_audit(event: WebJobAuditEvent) -> None:
    try:
        WebJobAuditLog(WEB_JOB_AUDIT_PATH).append(event)
    except Exception:
        # Task operations should remain available even if the audit file is temporarily unwritable.
        return


def _job_snapshot(job: dict[str, Any] | None) -> dict[str, str]:
    if not job:
        return {}
    return {
        "job_id": str(job.get("job_id") or ""),
        "status": str(job.get("status") or ""),
        "message": str(job.get("message") or ""),
        "task_path": str(job.get("task_path") or ""),
        "run_id": str(job.get("run_id") or ""),
        "started_at": str(job.get("started_at") or ""),
        "finished_at": str(job.get("finished_at") or ""),
        "updated_at": str(job.get("updated_at") or ""),
    }


def _job_run_ids(jobs: Iterable[dict[str, Any] | None]) -> list[str]:
    run_ids: list[str] = []
    for job in jobs:
        if not job:
            continue
        run_id = str(job.get("run_id") or "")
        if run_id and run_id not in run_ids:
            run_ids.append(run_id)
    return run_ids


def _build_task_manager_audit_markdown(records: list[dict[str, Any]]) -> str:
    lines = ["# Task Manager Audit", ""]
    if not records:
        lines.append("No task manager audit events recorded.")
        return "\n".join(lines) + "\n"
    for record in records:
        event_type = str(record.get("event_type") or "")
        created_at = str(record.get("created_at") or "")
        selected = list(record.get("selected_job_ids") or [])
        processed = list(record.get("processed_job_ids") or [])
        skipped = list(record.get("skipped_job_ids") or [])
        failed = list(record.get("failed_job_ids") or [])
        run_ids = list(record.get("run_ids") or [])
        message = str(record.get("message") or "")
        lines.extend(
            [
                f"## {created_at} {event_type}",
                "",
                f"- Message: {message}",
                f"- Selected: {len(selected)} ({', '.join(selected) if selected else '-'})",
                f"- Processed: {len(processed)} ({', '.join(processed) if processed else '-'})",
                f"- Skipped: {len(skipped)} ({', '.join(skipped) if skipped else '-'})",
                f"- Failed: {len(failed)} ({', '.join(failed) if failed else '-'})",
                f"- Runs: {', '.join(run_ids) if run_ids else '-'}",
                "",
            ]
        )
    return "\n".join(lines)


def _task_manager_audit_event_types(records: list[dict[str, Any]]) -> list[str]:
    return sorted({str(record.get("event_type") or "") for record in records if record.get("event_type")})


def _normalize_task_manager_audit_limit(limit: int) -> int:
    if limit in {25, 50, 100, 200}:
        return limit
    return 50


def _filter_task_manager_audit_records(records: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    if event_type == "all":
        return records
    return [record for record in records if str(record.get("event_type") or "") == event_type]


def _filter_task_manager_audit_records_by_outcome(records: list[dict[str, Any]], outcome: str) -> list[dict[str, Any]]:
    if outcome == "all":
        return records
    if outcome == "skipped":
        return [record for record in records if record.get("skipped_job_ids")]
    if outcome == "failed":
        return [record for record in records if record.get("failed_job_ids")]
    if outcome == "clean":
        return [
            record
            for record in records
            if not record.get("skipped_job_ids") and not record.get("failed_job_ids")
        ]
    return records


def _search_task_manager_audit_records(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    if not query:
        return records
    needle = query.lower()
    return [record for record in records if needle in _task_manager_audit_search_text(record)]


def _task_manager_audit_search_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in [
        "event_type",
        "created_at",
        "actor",
        "message",
        "selected_job_ids",
        "processed_job_ids",
        "skipped_job_ids",
        "failed_job_ids",
        "run_ids",
    ]:
        parts.append(str(record.get(key) or ""))
    for nested_key in ["request_context", "details"]:
        value = record.get(nested_key)
        if isinstance(value, dict):
            parts.extend(f"{key} {nested_value}" for key, nested_value in value.items())
    return " ".join(parts).lower()


def _build_task_manager_audit_view_record(record: dict[str, Any]) -> dict[str, str]:
    selected = list(record.get("selected_job_ids") or [])
    processed = list(record.get("processed_job_ids") or [])
    skipped = list(record.get("skipped_job_ids") or [])
    failed = list(record.get("failed_job_ids") or [])
    run_ids = list(record.get("run_ids") or [])
    details = record.get("details") if isinstance(record.get("details"), dict) else {}
    reasons = details.get("reasons") if isinstance(details.get("reasons"), dict) else {}
    return {
        "event_type": str(record.get("event_type") or ""),
        "created_at": str(record.get("created_at") or ""),
        "actor": str(record.get("actor") or ""),
        "message": str(record.get("message") or ""),
        "selected_count": str(len(selected)),
        "processed_count": str(len(processed)),
        "skipped_count": str(len(skipped)),
        "failed_count": str(len(failed)),
        "selected_jobs": ", ".join(str(value) for value in selected) or "-",
        "processed_jobs": ", ".join(str(value) for value in processed) or "-",
        "skipped_jobs": ", ".join(str(value) for value in skipped) or "-",
        "failed_jobs": ", ".join(str(value) for value in failed) or "-",
        "run_ids": ", ".join(str(value) for value in run_ids) or "-",
        "reasons": "; ".join(f"{key}: {value}" for key, value in reasons.items()) or "-",
    }


def _list_task_templates_with_recent_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recent_by_template: dict[str, dict[str, str]] = {}
    for job in jobs:
        template_id = _template_id_from_job(job)
        if not template_id or template_id in recent_by_template:
            continue
        recent_by_template[template_id] = {
            "job_id": str(job.get("job_id") or ""),
            "status": str(job.get("status") or ""),
            "status_label": _status_label(str(job.get("status") or "")),
            "status_class": _status_css_class(str(job.get("status") or "")),
            "run_id": str(job.get("run_id") or ""),
            "updated_at": str(job.get("updated_at") or ""),
        }

    templates: list[dict[str, Any]] = []
    for template in list_task_templates():
        item = dict(template)
        item["recent_job"] = recent_by_template.get(str(template["id"]), {})
        templates.append(item)
    return templates


def _template_id_from_job(job: dict[str, Any]) -> str:
    task_path = Path(str(job.get("task_path") or ""))
    if not task_path.exists():
        return ""
    try:
        task = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return normalize_template_id(str(task.get("template_id") or "")) if task.get("template_id") else ""


def _status_css_class(status: str) -> str:
    normalized = status.lower().strip()
    if normalized in {"done", "failed", "running", "stopped"}:
        return normalized
    return "unknown"


def _status_label(status: str) -> str:
    normalized = status.lower().strip()
    return {
        "done": "已完成",
        "failed": "失败",
        "halted": "已暂停",
        "running": "运行中",
        "retrying": "重试中",
        "stopped": "已停止",
    }.get(normalized, status or "未知")


def _load_runs() -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    if not RUNS_DIR.exists():
        return runs
    repository = FileStateRepository()
    for path in sorted(RUNS_DIR.glob("run-*"), reverse=True):
        if not (path / "run_state.json").exists():
            continue
        try:
            state = repository.load_state(path.name)
        except Exception:
            continue
        runs.append(
            {
                "run_id": state.run_id,
                "task_id": state.task_id,
                "status": state.status,
                "status_label": _status_label(str(state.status)),
                "phase": state.current_phase,
            }
        )
    return runs[:30]


def _infer_run_id_for_job(job: dict[str, Any]) -> str:
    task_path = Path(str(job.get("task_path") or ""))
    if not task_path.exists() or not RUNS_DIR.exists():
        return ""
    candidates: list[Path] = []
    for run_state_path in RUNS_DIR.glob("run-*/run_state.json"):
        run_dir = run_state_path.parent
        copied_task = run_dir / "task.json"
        if not copied_task.exists():
            continue
        if copied_task.stat().st_mtime + 1 < task_path.stat().st_mtime:
            continue
        try:
            copied = json.loads(copied_task.read_text(encoding="utf-8"))
            original = json.loads(task_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if copied.get("task_id") == original.get("task_id"):
            candidates.append(run_dir)
    if not candidates:
        return ""
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0].name


def _reconcile_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("status") in {"done", "failed"}:
        return job

    job_id = str(job.get("job_id") or "")
    if not job_id:
        return job

    run_id = str(job.get("run_id") or "") or _infer_run_id_for_job(job)
    if not run_id:
        return job

    updates: dict[str, str] = {}
    if not job.get("run_id"):
        updates["run_id"] = run_id

    try:
        state = FileStateRepository().load_state(run_id)
    except Exception:
        if updates:
            _update_job(job_id, **updates)
            return _read_job(job_id) or {**job, **updates}
        return job

    if state.status == RunStatus.DONE:
        updates.update(
            {
                "status": "done",
                "message": "任务已完成，正在打开结果页。",
                "finished_at": str(job.get("finished_at") or datetime.now().isoformat()),
            }
        )
    elif state.status == RunStatus.HALTED:
        updates.update(
            {
                "status": "failed",
                "message": f"任务未完成，停在 {state.current_phase} 阶段。请打开结果页查看报告。",
                "finished_at": str(job.get("finished_at") or datetime.now().isoformat()),
            }
        )

    if updates:
        _update_job(job_id, **updates)
        return _read_job(job_id) or {**job, **updates}
    return job


def _load_job_progress(run_id: str | None) -> dict[str, str] | None:
    if not run_id:
        return None
    run_dir = RUNS_DIR / run_id
    state_path = run_dir / "run_state.json"
    if not state_path.exists():
        return None
    try:
        state = FileStateRepository().load_state(run_id)
    except Exception:
        return None
    heartbeat = _tail_last_line(run_dir / "logs" / "heartbeat.log")
    phase = _tail_last_line(run_dir / "logs" / "phase.log")
    return {
        "run_id": state.run_id,
        "status": str(state.status),
        "status_label": _status_label(str(state.status)),
        "phase": state.current_phase,
        "attempt": f"{state.attempt}/{state.max_attempts}",
        "updated_at": state.updated_at.isoformat(),
        "last_heartbeat_at": state.last_heartbeat_at.isoformat() if state.last_heartbeat_at else "",
        "heartbeat": heartbeat,
        "phase_log": phase,
    }


def _load_docker_evidence(run_dir: Path) -> dict[str, object]:
    log_path = run_dir / "logs" / "docker_sandbox.jsonl"
    evidence = _empty_docker_evidence(log_path)
    if not log_path.exists():
        return evidence

    lines = [line for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if not lines:
        return evidence

    parsed_payloads: list[dict[str, object]] = []
    for line in lines:
        try:
            parsed_payloads.append(json.loads(line))
        except json.JSONDecodeError:
            parsed_payloads.append({"raw": line})
    last_payload = parsed_payloads[-1]
    phases = [str(payload.get("phase", "")) for payload in parsed_payloads if payload.get("phase")]
    recent_logs = [json.dumps(payload, ensure_ascii=False) for payload in parsed_payloads[-5:]]

    evidence.update(
        {
            "enabled": True,
            "count": len(lines),
            "image": str(last_payload.get("image", "")),
            "network": str(last_payload.get("network", "")),
            "worktree_mount": str(last_payload.get("worktree_mount", "")),
            "worktree_container_path": str(last_payload.get("worktree_container_path", "")),
            "phase": str(last_payload.get("phase", "")),
            "command": str(last_payload.get("command", "")),
            "exit_code": str(last_payload.get("exit_code", "")),
            "duration_seconds": str(last_payload.get("duration_seconds", "")),
            "timed_out": str(last_payload.get("timed_out", "")),
            "last_log": json.dumps(last_payload, ensure_ascii=False),
            "phases": ", ".join(phases),
            "recent_logs": recent_logs,
        }
    )
    return evidence


def _empty_docker_evidence(log_path: Path | None = None) -> dict[str, object]:
    return {
        "enabled": False,
        "count": 0,
        "image": "",
        "network": "",
        "worktree_mount": "",
        "worktree_container_path": "",
        "phase": "",
        "command": "",
        "exit_code": "",
        "duration_seconds": "",
        "timed_out": "",
        "last_log": "",
        "phases": "",
        "recent_logs": [],
        "log_path": log_path.as_posix() if log_path else "",
    }


def _label_job_progress(progress: dict[str, str] | None) -> dict[str, str] | None:
    if progress is None:
        return None
    labeled = dict(progress)
    labeled.setdefault("status_label", _status_label(str(progress.get("status") or "")))
    return labeled


def _load_task_context(run_dir: Path) -> dict[str, str]:
    task_path = run_dir / "task.json"
    return _load_task_context_from_path(task_path)


def _load_job_task_context(job: dict[str, Any], run_id: str | None) -> dict[str, str]:
    if run_id:
        run_task_path = RUNS_DIR / run_id / "task.json"
        if run_task_path.exists():
            return _load_task_context_from_path(run_task_path)
    task_path_value = str(job.get("task_path") or "").strip()
    if not task_path_value:
        return _load_task_context_from_path(Path(""))
    task_path = Path(task_path_value)
    return _load_task_context_from_path(task_path)


def _task_path_for_job(job: dict[str, Any], run_id: str | None) -> Path | None:
    if run_id:
        run_task_path = RUNS_DIR / run_id / "task.json"
        if run_task_path.exists():
            return run_task_path
    task_path_value = str(job.get("task_path") or "").strip()
    if not task_path_value:
        return None
    task_path = Path(task_path_value)
    return task_path if task_path.exists() and task_path.is_file() else None


def _load_task_context_from_path(task_path: Path) -> dict[str, str]:
    if not str(task_path) or not task_path.exists() or not task_path.is_file():
        return {
            "task_id": "",
            "title": "",
            "template_id": "",
            "template_label": "",
            "template_description": "",
            "execution_backend": "",
            "agent_mode": "",
            "command_preset": "",
            "worktree_path": "",
            "allowed_paths": "",
            "test_command": "",
        }
    try:
        task = json.loads(task_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        task = {}
    template_id = str(task.get("template_id") or "")
    template = get_task_template_summary(template_id) if template_id else {"id": "", "label": "", "description": ""}
    agent_commands = task.get("agent_commands") or {}
    check_commands = task.get("check_commands") or {}
    allowed_paths = task.get("allowed_paths") or []
    if not isinstance(allowed_paths, list):
        allowed_paths = [str(allowed_paths)]
    return {
        "task_id": str(task.get("task_id") or ""),
        "title": str(task.get("title") or ""),
        "template_id": str(template.get("id") or template_id),
        "template_label": str(template.get("label") or ""),
        "template_description": str(template.get("description") or ""),
        "execution_backend": str(task.get("execution_backend") or ""),
        "agent_mode": str(task.get("agent_mode") or ""),
        "command_preset": _infer_command_preset(task),
        "worktree_path": str(task.get("worktree_path") or task.get("repo_path") or ""),
        "allowed_paths": ", ".join(str(path) for path in allowed_paths),
        "test_command": str(check_commands.get("test") or ""),
        "patch_coder": str(agent_commands.get("patch_coder") or ""),
    }


def _infer_command_preset(task: dict[str, Any]) -> str:
    task_preset = task.get("command_preset")
    if task_preset:
        return str(task_preset)
    patch_coder = str((task.get("agent_commands") or {}).get("patch_coder") or "")
    for preset in list_command_presets():
        preset_id = str(preset["id"])
        command_preset = get_command_preset(preset_id)
        commands = (command_preset or {}).get("commands") or {}
        if patch_coder and patch_coder == str(commands.get("patch_coder") or ""):
            return preset_id
    return ""


def _tail_last_line(path: Path) -> str:
    if not path.exists():
        return ""
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.replace(",", "\n").splitlines() if line.strip()]


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value).strip("-") or "task"


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json_optional(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _read_first_json_optional(paths: Iterable[Path]) -> dict[str, object] | None:
    for path in sorted(paths, reverse=True):
        payload = _read_json_optional(path)
        if payload:
            return payload
    return None


def _read_first_optional(paths: Iterable[Path]) -> str:
    for path in sorted(paths, reverse=True):
        content = _read_optional(path)
        if content:
            return content
    return ""


def _team_patch_command() -> str:
    backend = Path.cwd() / "scripts" / "run_omx_team_patch.py"
    return f'python "{backend}" {{task_id}} {{prompt_file}} {{run_dir}}'


def _safe_local_path(value: str, fallback: Path) -> Path:
    decoded = unquote(value or "").strip()
    if not decoded:
        return (Path.cwd() / fallback).resolve()
    path = Path(decoded)
    if not path.is_absolute():
        path = Path.cwd() / path
    text = str(path)
    if "\ufffd" in text:
        return (Path.cwd() / fallback).resolve()
    return path.resolve()


def _prepare_default_smoke_worktree(path: Path) -> None:
    default_path = (Path.cwd() / DEFAULT_SMOKE_WORKTREE).resolve()
    if path != default_path:
        return
    path.mkdir(parents=True, exist_ok=True)
    calculator = path / "calculator.py"
    test_file = path / "test_calculator.py"
    team_backend = path / "docker_team_backend.py"
    patch_backend = path / "patch_backend.py"
    calculator.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    test_file.write_text(
        "import unittest\n\n"
        "from calculator import add\n\n\n"
        "class CalculatorTest(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(1, 2), 3)\n\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
        encoding="utf-8",
    )
    team_backend.write_text(_default_docker_team_backend_source(), encoding="utf-8")
    patch_backend.write_text(_default_docker_patch_backend_source(), encoding="utf-8")


def _default_docker_team_backend_source() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import json",
            "import pathlib",
            "import sys",
            "",
            "task_id = sys.argv[1]",
            "prompt = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')",
            "assert 'Allowed file snapshot' in prompt",
            "payload = {",
            "    'schema_version': '1.0',",
            "    'task_id': task_id,",
            "    'status': 'completed',",
            "    'roles': {},",
            "    'artifacts': {",
            "        'patch_plan': {",
            "            'schema_version': '1.0',",
            "            'task_id': task_id,",
            "            'summary': 'Fix calculator.add from Docker team backend.',",
            "            'operations': [",
            "                {'op': 'replace_text', 'path': 'calculator.py', 'old': 'return a - b', 'new': 'return a + b'}",
            "            ],",
            "        },",
            "        'review': {",
            "            'schema_version': '1.0',",
            "            'task_id': task_id,",
            "            'pass': True,",
            "            'confidence': 91,",
            "            'summary': 'Docker team backend review passed.',",
            "            'issues': [],",
            "            'blocking': False,",
            "            'recommended_next_action': 'pass',",
            "        },",
            "    },",
            "    'diagnostics': [],",
            "}",
            "print(json.dumps(payload, ensure_ascii=False))",
            "",
        ]
    )


def _default_docker_patch_backend_source() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import json",
            "import sys",
            "",
            "task_id = sys.argv[1]",
            "payload = {",
            "    'schema_version': '1.0',",
            "    'task_id': task_id,",
            "    'summary': 'Fix calculator.add from Docker patch backend.',",
            "    'operations': [",
            "        {'op': 'replace_text', 'path': 'calculator.py', 'old': 'return a - b', 'new': 'return a + b'}",
            "    ],",
            "}",
            "print(json.dumps(payload, ensure_ascii=False))",
            "",
        ]
    )


def _build_run_summary(state, patches: list[dict[str, object]]) -> dict[str, str]:
    pending_count = sum(1 for patch in patches if patch.get("status") == "pending")
    applied_count = sum(1 for patch in patches if patch.get("status") == "applied")
    rejected_count = sum(1 for patch in patches if patch.get("status") == "rejected")
    status = str(state.status)
    phase = str(state.current_phase)

    if pending_count:
        title = "需要审批补丁"
        tone = "warning"
        message = f"系统生成了 {pending_count} 个待审批补丁，还没有直接写入完成。请在下方选择批准或拒绝。"
        action = "检查补丁预览后，点击批准并验证或拒绝补丁。"
    elif status == "done":
        title = "运行成功"
        tone = "success"
        message = "任务已经跑完，检查、评审和质量门禁都通过了。"
        action = "查看最终报告，或返回首页继续运行其他任务。"
    elif status == "halted":
        title = "运行停止"
        tone = "danger"
        message = f"任务停在 {phase} 阶段，通常表示测试失败、模型输出不合法或安全策略拦截。"
        action = "先看最终结论，再展开诊断日志定位原因。"
    else:
        title = "运行中或等待下一步"
        tone = "info"
        message = f"当前阶段是 {phase}。如果页面长时间不变，可以刷新页面查看最新状态。"
        action = "等待完成，或刷新页面。"

    return {
        "title": title,
        "tone": tone,
        "message": message,
        "action": action,
        "patch_stats": f"待审批 {pending_count} / 已批准 {applied_count} / 已拒绝 {rejected_count}",
    }


def main() -> None:
    uvicorn.run("orchestrator.interfaces.web.main:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
