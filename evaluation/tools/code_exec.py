from __future__ import annotations

import html
import threading
from typing import Any, ClassVar


class CodeExecTool:
    name = "code_exec"
    description = (
        "Execute a shell command in an isolated E2B environment. "
        "Returns exit code, stdout, and stderr as XML."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "cmd": {
                "type": "string",
                "description": (
                    "Shell command using relative working-directory paths. "
                    "Do not reference host paths."
                ),
            }
        },
        "required": ["cmd"],
    }

    def __init__(
        self,
        api_key: str,
        *,
        template_id: str = "",
        sandbox_timeout: int = 600,
        command_timeout: int = 120,
    ) -> None:
        if not api_key:
            raise RuntimeError("E2B_API_KEY is required")
        self._api_key = api_key
        self._template_id = template_id
        self._sandbox_timeout = sandbox_timeout
        self._command_timeout = command_timeout
        self._sandbox: Any | None = None
        self._lock = threading.Lock()

    def _sandbox_instance(self) -> Any:
        if self._sandbox is None:
            try:
                from e2b_code_interpreter import Sandbox
            except ImportError as exc:
                raise RuntimeError("Install e2b-code-interpreter to use code_exec") from exc
            kwargs: dict[str, Any] = {
                "api_key": self._api_key,
                "timeout": self._sandbox_timeout,
            }
            if self._template_id:
                kwargs["template"] = self._template_id
            create = getattr(Sandbox, "create", None)
            self._sandbox = create(**kwargs) if callable(create) else Sandbox(**kwargs)
        return self._sandbox

    def call(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("cmd")
        if not isinstance(command, str) or not command.strip():
            return "[code_exec] Invalid request: 'cmd' must be a non-empty string."
        with self._lock:
            sandbox = self._sandbox_instance()
            result = sandbox.commands.run(command, timeout=self._command_timeout)
        return (
            "<shell_results>\n"
            f"<exit_code>{html.escape(str(getattr(result, 'exit_code', 0)))}</exit_code>\n"
            f"<stdout>{html.escape(str(getattr(result, 'stdout', '') or '')[:20000])}</stdout>\n"
            f"<stderr>{html.escape(str(getattr(result, 'stderr', '') or '')[:4000])}</stderr>\n"
            "</shell_results>"
        )

    def close(self) -> None:
        with self._lock:
            sandbox = self._sandbox
            self._sandbox = None
        if sandbox is None:
            return
        kill = getattr(sandbox, "kill", None)
        close = getattr(sandbox, "close", None)
        if callable(kill):
            kill()
        elif callable(close):
            close()
