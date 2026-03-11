from __future__ import annotations

from pathlib import Path

import pytest

from many_panelz_explorer._operations.executors import (
    execute_operation_request,
    execute_robocopy,
)
from many_panelz_explorer._operations.types import (
    BACKEND_UNSTOPPABLE,
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationRequest,
    OperationResult,
)


def test_execute_robocopy_normalizes_success_exit_codes(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir(parents=True, exist_ok=True)
    robocopy_exe = tmp_path / "robocopy.exe"
    robocopy_exe.write_text("", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_write_script(
        artifacts: OperationArtifacts,
        script_lines: list[str],
    ) -> Path:
        captured["lines"] = list(script_lines)
        return artifacts.job_dir / "run.cmd"

    def _fake_run_script(
        script_path: Path,
        log_path: Path,
        *,
        cmd_path: str,
        wait: bool,
    ) -> OperationResult:
        _ = script_path, log_path, cmd_path, wait
        return OperationResult(status="succeeded", message="ok", processed_count=1)

    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.write_script",
        _fake_write_script,
    )
    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.run_script",
        _fake_run_script,
    )

    request = OperationRequest(
        kind="copy",
        sources=(source,),
        target_dir=target,
        backend_id="robocopy",
        dispatch_mode="run_now_wait",
        conflict_policy="rename",
    )
    preferences = OperationExecutionPreferences(
        resolved_robocopy_path=str(robocopy_exe),
        resolved_cmd_path=str(tmp_path / "cmd.exe"),
    )
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )

    result = execute_robocopy(
        request,
        artifacts,
        wait=True,
        preferences=preferences,
    )

    assert result.status == "succeeded"
    lines = captured["lines"]
    assert isinstance(lines, list)
    assert "if %ERRORLEVEL% GTR 7 exit /b %ERRORLEVEL%" in lines
    assert lines[-1] == "cmd /c exit /b 0"


@pytest.mark.parametrize(
    ("kind", "expected_token"),
    [
        ("copy", "+d"),
        ("move", "+dm"),
    ],
)
def test_execute_unstoppable_uses_supported_operation_switch_token(
    monkeypatch, tmp_path: Path, kind: str, expected_token: str
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir(parents=True, exist_ok=True)
    unstoppable_exe = tmp_path / "UnstoppableCopier.exe"
    unstoppable_exe.write_text("", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_write_script(
        artifacts: OperationArtifacts,
        script_lines: list[str],
    ) -> Path:
        captured["lines"] = list(script_lines)
        return artifacts.job_dir / "run.cmd"

    def _fake_run_script(
        script_path: Path,
        log_path: Path,
        *,
        cmd_path: str,
        wait: bool,
    ) -> OperationResult:
        _ = script_path, log_path, cmd_path, wait
        return OperationResult(status="succeeded", message="ok", processed_count=1)

    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.write_script",
        _fake_write_script,
    )
    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.run_script",
        _fake_run_script,
    )

    request = OperationRequest(
        kind=kind,  # type: ignore[arg-type]
        sources=(source,),
        target_dir=target,
        backend_id=BACKEND_UNSTOPPABLE,
        dispatch_mode="run_now_wait",
        conflict_policy="rename",
    )
    preferences = OperationExecutionPreferences(
        unstoppable_executable=str(unstoppable_exe),
        resolved_cmd_path=str(tmp_path / "cmd.exe"),
    )
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )

    result = execute_operation_request(
        request,
        wait=True,
        preferences=preferences,
        artifacts=artifacts,
    )

    assert result.status == "succeeded"
    lines = captured["lines"]
    assert isinstance(lines, list)
    assert lines
    command_line = str(lines[0])
    assert expected_token in command_line
    assert " copy " not in command_line
    assert " move " not in command_line


def test_execute_unstoppable_emits_one_command_per_source(
    monkeypatch, tmp_path: Path
) -> None:
    source_a = tmp_path / "source-a.txt"
    source_b = tmp_path / "source-b.txt"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir(parents=True, exist_ok=True)
    unstoppable_exe = tmp_path / "UnstoppableCopier.exe"
    unstoppable_exe.write_text("", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_write_script(
        artifacts: OperationArtifacts,
        script_lines: list[str],
    ) -> Path:
        captured["lines"] = list(script_lines)
        return artifacts.job_dir / "run.cmd"

    def _fake_run_script(
        script_path: Path,
        log_path: Path,
        *,
        cmd_path: str,
        wait: bool,
    ) -> OperationResult:
        _ = script_path, log_path, cmd_path, wait
        return OperationResult(status="succeeded", message="ok", processed_count=2)

    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.write_script",
        _fake_write_script,
    )
    monkeypatch.setattr(
        "many_panelz_explorer._operations.executors.run_script",
        _fake_run_script,
    )

    request = OperationRequest(
        kind="copy",
        sources=(source_a, source_b),
        target_dir=target,
        backend_id=BACKEND_UNSTOPPABLE,
        dispatch_mode="run_now_wait",
        conflict_policy="rename",
    )
    preferences = OperationExecutionPreferences(
        unstoppable_executable=str(unstoppable_exe),
        resolved_cmd_path=str(tmp_path / "cmd.exe"),
    )
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )

    result = execute_operation_request(
        request,
        wait=True,
        preferences=preferences,
        artifacts=artifacts,
    )

    assert result.status == "succeeded"
    lines = captured["lines"]
    assert isinstance(lines, list)
    command_lines = [str(line) for line in lines if "UnstoppableCopier.exe" in str(line)]
    assert len(command_lines) == 2
    assert str(source_a) in command_lines[0]
    assert str(source_b) in command_lines[1]
