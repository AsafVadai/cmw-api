"""Base mixin shared by all functional modules."""

import math
import time
from .exceptions import CMWTimeoutError, CMWMeasurementError

# Non-numeric tokens that R&S instruments return in place of a value.
# They are mapped to NaN so that parsing never crashes on a valid reply.
#   INV  = invalid        NCAP = not captured       NAV  = not available
#   OFL  = overflow       UFL  = underflow          DC   = don't care / no result
_NON_NUMERIC_TOKENS = {"INV", "NCAP", "NAV", "OFL", "UFL", "DC", "NONE", ""}


class BaseMixin:
    """Base class for all functional modules; owns the shared transport."""

    def __init__(self, transport) -> None:
        self._transport = transport

    def _write(self, cmd: str) -> None:
        self._transport.write(cmd)

    def _query(self, cmd: str) -> str:
        return self._transport.query(cmd)

    @staticmethod
    def _safe_float(token: str) -> float:
        """
        Convert a SCPI response token to float, tolerating the special
        non-numeric tokens R&S instruments return (INV, NCAP, NAV, OFL, ...).

        Returns NaN for any token that is not a finite number, so callers
        never crash on a structurally valid reply.
        """
        t = token.strip().upper()
        if t in _NON_NUMERIC_TOKENS:
            return float("nan")
        try:
            return float(token)
        except (ValueError, TypeError):
            return float("nan")

    def _query_float(self, cmd: str) -> float:
        """Query a single value and return it as a float (NaN-safe)."""
        return self._safe_float(self._query(cmd))

    @staticmethod
    def _safe_int(token: str) -> int:
        """
        Convert a SCPI token to int, tolerating the special non-numeric tokens
        (INV, NCAP, NAV, ...). Returns 0 for any token that is not an integer,
        so count/sample fields never crash a parser on an unusual reply.
        """
        t = token.strip().upper()
        if t in _NON_NUMERIC_TOKENS:
            return 0
        try:
            return int(float(token))   # tolerate "1000.0" style replies too
        except (ValueError, TypeError):
            return 0

    def _query_int(self, cmd: str) -> int:
        try:
            return int(self._query(cmd))
        except (ValueError, TypeError) as exc:
            raise CMWMeasurementError(
                f"Expected an integer reply to '{cmd}' but got something else"
            ) from exc

    def _fetch_csv(self, cmd: str, min_fields: int) -> list[str]:
        """
        Query a comma-separated response and return its fields.

        Raises CMWMeasurementError (with the raw text) if fewer than
        min_fields are returned, so a malformed/short reply produces a clear
        diagnostic instead of an IndexError deep inside a parser.
        """
        raw = self._query(cmd)
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < min_fields:
            raise CMWMeasurementError(
                f"'{cmd}' returned {len(parts)} field(s), expected at least "
                f"{min_fields}. Raw reply: {raw!r}. "
                "Check the application option is installed and a measurement has run."
            )
        return parts

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
