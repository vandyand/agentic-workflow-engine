"""Workflow executor wrapper for Streamlit integration."""
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


ROOT = Path(__file__).parent.parent


@dataclass
class LogEntry:
    """A single log entry from workflow execution."""
    timestamp: str
    level: str  # 'info', 'success', 'error', 'running'
    message: str
    node_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionResult:
    """Result of a workflow execution."""
    success: bool
    logs: List[LogEntry] = field(default_factory=list)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0


def substitute_query(workflow_path: str, query: str, output_path: str) -> None:
    """Load workflow, substitute {query} placeholder, write to output."""
    with open(workflow_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple string replacement for {query} placeholder
    content = content.replace('{query}', query)

    # For error_recovery, handle {url} placeholder
    if 'error_recovery' in workflow_path:
        if query == 'simulate failure':
            content = content.replace('{url}', 'https://httpstat.us/503')
        else:
            content = content.replace('{url}', 'https://httpstat.us/200')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def execute_workflow(
    workflow_name: str,
    query: str,
    timeout_seconds: int = 30
) -> ExecutionResult:
    """Execute a workflow and capture results.

    Args:
        workflow_name: Name of workflow (e.g., 'arxiv_search')
        query: Query string to substitute into workflow
        timeout_seconds: Max execution time

    Returns:
        ExecutionResult with logs and outputs
    """
    workflow_path = ROOT / 'workflows' / f'{workflow_name}.yaml'

    if not workflow_path.exists():
        return ExecutionResult(
            success=False,
            error=f"Workflow not found: {workflow_name}",
            logs=[LogEntry(
                timestamp=_timestamp(),
                level='error',
                message=f"Workflow file not found: {workflow_path}"
            )]
        )

    logs: List[LogEntry] = []
    start_time = time.time()

    # Create temp file with substituted query
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False
    ) as tmp:
        tmp_path = tmp.name
        substitute_query(str(workflow_path), query, tmp_path)

    try:
        logs.append(LogEntry(
            timestamp=_timestamp(),
            level='info',
            message=f"Starting workflow: {workflow_name}"
        ))
        logs.append(LogEntry(
            timestamp=_timestamp(),
            level='info',
            message=f"Query: {query}"
        ))

        # Run the workflow using runner.py
        runner_path = ROOT / 'runner.py'

        logs.append(LogEntry(
            timestamp=_timestamp(),
            level='info',
            message="Validating workflow schema..."
        ))

        # Execute with subprocess to capture output
        env = os.environ.copy()
        env['PYTHONPATH'] = str(ROOT)

        result = subprocess.run(
            [sys.executable, str(runner_path), tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(ROOT),
            env=env
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Parse output for node results
        node_outputs = {}
        for line in result.stdout.split('\n'):
            if line.strip():
                logs.append(LogEntry(
                    timestamp=_timestamp(),
                    level='info',
                    message=line.strip()
                ))

        if result.returncode == 0:
            logs.append(LogEntry(
                timestamp=_timestamp(),
                level='success',
                message=f"Workflow completed successfully in {elapsed_ms}ms"
            ))
            return ExecutionResult(
                success=True,
                logs=logs,
                node_outputs=node_outputs,
                execution_time_ms=elapsed_ms
            )
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            logs.append(LogEntry(
                timestamp=_timestamp(),
                level='error',
                message=f"Workflow failed: {error_msg}"
            ))
            return ExecutionResult(
                success=False,
                logs=logs,
                error=error_msg,
                execution_time_ms=elapsed_ms
            )

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logs.append(LogEntry(
            timestamp=_timestamp(),
            level='error',
            message=f"Workflow timed out after {timeout_seconds}s"
        ))
        return ExecutionResult(
            success=False,
            logs=logs,
            error="Timeout",
            execution_time_ms=elapsed_ms
        )
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logs.append(LogEntry(
            timestamp=_timestamp(),
            level='error',
            message=f"Execution error: {str(e)}"
        ))
        return ExecutionResult(
            success=False,
            logs=logs,
            error=str(e),
            execution_time_ms=elapsed_ms
        )
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass


def _timestamp() -> str:
    """Get current timestamp string."""
    return time.strftime("%H:%M:%S")
