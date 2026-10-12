import json
import socket
import threading
import time
from typing import Optional, TYPE_CHECKING

from protocol import BodyCommand, BodyResult

if TYPE_CHECKING:
    from body_receiver import AuthoritativeBodyReceiver


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class BodyTransportClient:
    """Laptop cognition client communicating across a transport boundary to the body."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout_s: float = 15.0):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    def send_command(self, command: BodyCommand) -> BodyResult:
        """Sends a BodyCommand JSON message over TCP and waits for the BodyResult."""
        payload = command.to_json() + "\n"
        sock = None
        started_at = time.monotonic()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(max(self.timeout_s, command.timeout_s + 5.0))
            sock.connect((self.host, self.port))
            sock.sendall(payload.encode("utf-8"))

            buffer = ""
            while "\n" not in buffer:
                chunk = sock.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk

            if not buffer.strip():
                raise ConnectionError("Empty response from body receiver server")

            result_line = buffer.strip().split("\n")[0]
            data = json.loads(result_line)
            return BodyResult(
                seq=data.get("seq", command.seq),
                goal_id=data.get("goal_id", command.goal_id),
                accepted=data.get("accepted", False),
                completed=data.get("completed", False),
                status=data.get("status", "unknown"),
                started_at=data.get("started_at", started_at),
                finished_at=data.get("finished_at", time.monotonic()),
                measurements=data.get("measurements", {}),
                errors=data.get("errors", []),
            )
        except Exception as exc:
            return BodyResult(
                seq=command.seq,
                goal_id=command.goal_id,
                accepted=False,
                completed=False,
                status=f"transport_error: {exc}",
                started_at=started_at,
                finished_at=time.monotonic(),
                measurements={},
                errors=[str(exc)],
            )
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass


class BodyTransportServer:
    """Authoritative body-side server listening over TCP and dispatching to AuthoritativeBodyReceiver."""

    def __init__(
        self,
        receiver: "AuthoritativeBodyReceiver",
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ):
        self.receiver = receiver
        self.host = host
        self.port = port
        self._server_sock: Optional[socket.socket] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._bound_port = port

    @property
    def bound_port(self) -> int:
        return self._bound_port

    def start(self) -> None:
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._bound_port = self._server_sock.getsockname()[1]
        self._server_sock.listen(5)
        self._server_sock.settimeout(0.5)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serve_loop, name="BodyTransportServer", daemon=True)
        self._thread.start()

    def _serve_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                client_sock, _ = self._server_sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                client_sock.settimeout(35.0)
                buffer = ""
                while "\n" not in buffer and not self._stop_event.is_set():
                    chunk = client_sock.recv(4096).decode("utf-8")
                    if not chunk:
                        break
                    buffer += chunk

                if buffer.strip():
                    command_line = buffer.strip().split("\n")[0]
                    response_json = self.receiver.handle(command_line)
                    client_sock.sendall((response_json + "\n").encode("utf-8"))
            except Exception as exc:
                try:
                    err_result = BodyResult(
                        seq=-1,
                        goal_id="server_error",
                        accepted=False,
                        completed=False,
                        status="server_error",
                        started_at=time.monotonic(),
                        finished_at=time.monotonic(),
                        errors=[str(exc)],
                    )
                    client_sock.sendall((err_result.to_json() + "\n").encode("utf-8"))
                except Exception:
                    pass
            finally:
                try:
                    client_sock.close()
                except Exception:
                    pass

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
