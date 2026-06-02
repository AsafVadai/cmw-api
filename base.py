"""Base mixin shared by all functional modules."""

import time
from .exceptions import CMWTimeoutError, CMWMeasurementError


class BaseMixin:
    """Provides write/query helpers to sub-modules that share a transport."""

    # Sub-classes must expose _transport (set by CMW.__init__)

    def _write(self, cmd: str) -> None:
        self._transport.write(cmd)

    def _query(self, cmd: str) -> str:
        return self._transport.query(cmd)

    def _query_float(self, cmd: str) -> float:
        return float(self._query(cmd))

    def _query_int(self, cmd: str) -> int:
        return int(self._query(cmd))

    def _check_errors(self) -> None:
        """Read and raise the SCPI error queue (SYST:ERR?)."""
        while True:
            resp = self._query("SYSTem:ERRor:ALL?")
            if resp.startswith("0,") or resp == '+0,"No error"':
                break
            raise CMWMeasurementError(f"CMW error: {resp}")

    def _opc_wait(self, timeout: float = 30.0, poll_interval: float = 0.2) -> None:
        """Block until *OPC? returns 1 or timeout expires."""
        self._write("*OPC")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._query("*OPC?") == "1":
                return
            time.sleep(poll_interval)
        raise CMWTimeoutError("*OPC? did not return 1 within timeout")

    def _poll_state(
        self,
        query_cmd: str,
        target_states: tuple,
        error_states: tuple = (),
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> str:
        """Poll a state query until it reaches a target or error state."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self._query(query_cmd).strip().strip('"')
            if state in target_states:
                return state
            if state in error_states:
                raise CMWMeasurementError(f"Unexpected state: {state}")
            time.sleep(poll_interval)
        raise CMWTimeoutError(
            f"Timed out waiting for {target_states}; last state: {state}"
        )
