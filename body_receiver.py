import time
from typing import Optional, TYPE_CHECKING

from protocol import BodyCommand, BodyResult

if TYPE_CHECKING:
    from action_controller import ActionController


class AuthoritativeBodyReceiver:
    """Owns body-side execution, validates command protocol and sequence, and returns completion telemetry."""

    def __init__(self, action_controller: "ActionController"):
        self.action_controller = action_controller
        self.expected_seq = 1
        self.last_result: Optional[BodyResult] = None

    def handle(self, payload: str) -> str:
        started_at = time.monotonic()
        errors = []

        try:
            command = BodyCommand.from_json(payload)
        except Exception as exc:
            result = BodyResult(
                seq=-1,
                goal_id="invalid",
                accepted=False,
                completed=False,
                status="rejected",
                started_at=started_at,
                finished_at=time.monotonic(),
                errors=[str(exc)],
            )
            self.last_result = result
            return result.to_json()

        if command.seq != self.expected_seq:
            result = BodyResult(
                seq=command.seq,
                goal_id=command.goal_id,
                accepted=False,
                completed=False,
                status=f"rejected: expected seq {self.expected_seq}",
                started_at=started_at,
                finished_at=time.monotonic(),
                errors=["out-of-order command"],
            )
            self.last_result = result
            return result.to_json()

        try:
            measurements = self.action_controller.execute_command(command)
            timed_out = bool(measurements.get("timed_out", False))
            completed = bool(measurements.get("completed", False)) and not timed_out
            if timed_out:
                status = "timed_out"
            elif completed:
                status = "completed"
            else:
                status = "failed"
        except Exception as exc:
            measurements = {}
            completed = False
            status = "failed"
            errors.append(str(exc))

        self.expected_seq += 1
        finished_at = time.monotonic()
        result = BodyResult(
            seq=command.seq,
            goal_id=command.goal_id,
            accepted=True,
            completed=completed,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            measurements=measurements,
            errors=errors,
        )
        self.last_result = result
        return result.to_json()
