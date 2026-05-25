from __future__ import annotations

import json
import re
import shlex
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Iterable
from urllib.parse import unquote

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.domain.enums import RunStatus
from orchestrator.infrastructure.patches.pending_patch_service import PendingPatchService
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.interfaces.cli.main import build_post_apply_validation_use_case, build_use_case


RUNS_DIR = Path(".omx/runs")
JOBS_DB_PATH = Path(".omx/orchestrator.db")
WEB_TASKS_DIR = Path(".omx/web-tasks")
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


@dataclass
class TaskForm:
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
    check_command: str = "python -m pytest -q"
    agent_mode: str = "omx_team_patch"
    patch_coder: str = ""
    patch_fixer: str = ""
    reviewer: str = ""
    execution_backend: str = "local"
    sandbox_image: str = "python:3.12-slim"
    sandbox_network: str = "none"
    sandbox_worktree_mount: str = "readonly"
    sandbox_memory_limit: str = "1g"
    sandbox_cpu_limit: str = "1"
    real_checks: bool = True
    errors: list[str] = field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _render_index(request, form=_default_task_form())


@app.post("/tasks/run", response_class=HTMLResponse)
def run_task(
    request: Request,
    task_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    change_type: Annotated[str, Form()],
    allowed_paths: Annotated[str, Form()],
    worktree_path: Annotated[str, Form()] = "",
    check_command: Annotated[str, Form()] = "",
    agent_mode: Annotated[str, Form()] = "omx_team_patch",
    patch_coder: Annotated[str, Form()] = "",
    patch_fixer: Annotated[str, Form()] = "",
    reviewer: Annotated[str, Form()] = "",
    execution_backend: Annotated[str, Form()] = "local",
    sandbox_image: Annotated[str, Form()] = "python:3.12-slim",
    sandbox_network: Annotated[str, Form()] = "none",
    sandbox_worktree_mount: Annotated[str, Form()] = "readonly",
    sandbox_memory_limit: Annotated[str, Form()] = "1g",
    sandbox_cpu_limit: Annotated[str, Form()] = "1",
    real_checks: Annotated[bool, Form()] = False,
):
    form = TaskForm(
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
        execution_backend=execution_backend,
        sandbox_image=sandbox_image,
        sandbox_network=sandbox_network,
        sandbox_worktree_mount=sandbox_worktree_mount,
        sandbox_memory_limit=sandbox_memory_limit,
        sandbox_cpu_limit=sandbox_cpu_limit,
        real_checks=real_checks,
    )
    errors = _validate_task_form(form)
    if errors:
        form.errors = errors
        return _render_index(request, form=form, status_code=422)

    WEB_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    safe_worktree_path = _safe_local_path(worktree_path, DEFAULT_SMOKE_WORKTREE)
    _prepare_default_smoke_worktree(safe_worktree_path)
    task_path = WEB_TASKS_DIR / f"{_safe_id(task_id)}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    payload = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "change_type": change_type,
        "repo_path": str(safe_worktree_path),
        "worktree_path": str(safe_worktree_path),
        "allowed_paths": _lines(allowed_paths),
        "forbidden_paths": [".env", "secrets", "deploy/prod"],
        "allowed_command_prefixes": ["python", "python.exe", "python -m pytest", "pytest"],
        "execution_backend": execution_backend,
        "sandbox": {
            "image": sandbox_image,
            "network": sandbox_network,
            "worktree_mount": sandbox_worktree_mount,
            "memory_limit": sandbox_memory_limit,
            "cpu_limit": float(sandbox_cpu_limit),
        },
        "check_commands": {"test": check_command or None, "lint": None, "typecheck": None},
        "agent_mode": agent_mode,
        "agent_commands": {
            "patch_coder": patch_coder or None,
            "patch_fixer": patch_fixer or None,
            "reviewer": reviewer or None,
        },
        "max_attempts": 2,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 10,
        "command_timeout_seconds": 240,
        "risk_level": "medium",
    }
    task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    job_id = _start_background_run(task_path, agent_mode=agent_mode, real_checks=real_checks)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/examples/run")
def run_example(
    task_path: Annotated[str, Form()],
    agent_mode: Annotated[str, Form()] = "omx_team_patch",
    real_checks: Annotated[bool, Form()] = True,
):
    job_id = _start_background_run(Path(task_path), agent_mode=agent_mode, real_checks=real_checks)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_status(request: Request, job_id: str):
    job = _read_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    job = _reconcile_job(job)
    run_id = job.get("run_id") or ""
    if job.get("status") == "done" and run_id:
        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

    progress = _load_job_progress(run_id) if run_id else None
    return TEMPLATES.TemplateResponse(
        request,
        "job_status.html",
        {"job": job, "job_id": job_id, "run_id": run_id, "progress": progress},
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    repository = FileStateRepository()
    state = repository.load_state(run_id)
    run_dir = RUNS_DIR / run_id
    patches = PendingPatchService().list(run_id=run_id)
    return TEMPLATES.TemplateResponse(
        request,
        "run_detail.html",
        {
            "state": state,
            "run_id": run_id,
            "run_dir": run_dir,
            "summary": _build_run_summary(state, patches),
            "final_report": _read_optional(run_dir / "final_report.md"),
            "agent_log": _read_optional(run_dir / "logs" / "agent.log"),
            "phase_log": _read_optional(run_dir / "logs" / "phase.log"),
            "team_result": _read_first_optional(run_dir.glob("attempts/*/team_result.json")),
            "team_diagnostics": _read_first_optional(run_dir.glob("attempts/*/team_diagnostics.json")),
            "patches": patches,
        },
    )


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
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "runs": _load_runs(),
            "jobs": _load_recent_jobs(),
            "patches": PendingPatchService().list(),
            "examples": sorted(str(path).replace("\\", "/") for path in Path("examples").glob("task*.json")),
            "project_root": Path.cwd(),
            "form": form,
        },
        status_code=status_code,
    )


def _default_task_form() -> TaskForm:
    return TaskForm(
        worktree_path=str((Path.cwd() / DEFAULT_SMOKE_WORKTREE).resolve()),
        patch_coder=_team_patch_command(),
        patch_fixer="",
        reviewer="",
    )


def _validate_task_form(form: TaskForm) -> list[str]:
    errors: list[str] = []
    if not _safe_id(form.task_id) or _safe_id(form.task_id) != form.task_id:
        errors.append("Task ID 只能包含字母、数字、下划线和短横线。")
    if form.change_type not in ALLOWED_CHANGE_TYPES:
        errors.append("类型只能是 feature、bugfix、refactor 或 config。")
    if form.agent_mode not in ALLOWED_AGENT_MODES:
        errors.append("Agent 模式不合法。")

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
            state = build_use_case(agent_mode=agent_mode, real_checks=real_checks, git_diff=False).execute(
                RunTaskCommand(task_path=task_path)
            )
            if state.status != RunStatus.DONE:
                _update_job(
                    job_id,
                    status="failed",
                    message=f"任务未完成，停在 {state.current_phase} 阶段。请打开结果页查看报告。",
                    run_id=state.run_id,
                    finished_at=datetime.now().isoformat(),
                )
                return
            _update_job(
                job_id,
                status="done",
                message="任务已完成，正在打开结果页。",
                run_id=state.run_id,
                finished_at=datetime.now().isoformat(),
            )
        except Exception as exc:
            _update_job(
                job_id,
                status="failed",
                message=f"任务启动失败：{exc}",
                finished_at=datetime.now().isoformat(),
            )

    threading.Thread(target=worker, daemon=True).start()
    return job_id


def _job_repository() -> SQLiteJobRepository:
    return SQLiteJobRepository(JOBS_DB_PATH)


def _read_job(job_id: str) -> dict[str, Any] | None:
    return _job_repository().get(_safe_id(job_id))


def _write_job(job_id: str, payload: dict[str, Any]) -> None:
    normalized = dict(payload)
    normalized["job_id"] = _safe_id(job_id)
    _job_repository().create(normalized)


def _update_job(job_id: str, **updates: str) -> None:
    _job_repository().update(_safe_id(job_id), **updates)


def _load_recent_jobs() -> list[dict[str, Any]]:
    return [_reconcile_job(job) for job in _job_repository().list_recent(limit=20)]


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
        "phase": state.current_phase,
        "attempt": f"{state.attempt}/{state.max_attempts}",
        "updated_at": state.updated_at.isoformat(),
        "last_heartbeat_at": state.last_heartbeat_at.isoformat() if state.last_heartbeat_at else "",
        "heartbeat": heartbeat,
        "phase_log": phase,
    }


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
    calculator.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    test_file.write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
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
