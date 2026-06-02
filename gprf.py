"""General-Purpose RF (GPRF) — non-signaling power/frequency measurements."""

from dataclasses import dataclass
from typing import Optional
from .base import BaseMixin


@dataclass
class GPRFPowerResult:
    current: float    # dBm
    average: float    # dBm
    minimum: float    # dBm
    maximum: float    # dBm
    status: str


@dataclass
class GPRFSpectrumResult:
    start_freq: float   # Hz
    stop_freq: float    # Hz
    peak_power: float   # dBm
    peak_freq: float    # Hz
    status: str


class GPRFModule(BaseMixin):
    """Non-signaling RF generator and power measurement (GPRF application)."""

    # ------------------------------------------------------------------ #
    #  Generator (signal source)                                          #
    # ------------------------------------------------------------------ #

    def gen_set_frequency(self, freq_hz: float) -> None:
        self._write(f"SOURce:GPRF:GEN:RFFrequency {freq_hz:.0f}")

    def gen_get_frequency(self) -> float:
        return self._query_float("SOURce:GPRF:GEN:RFFrequency?")

    def gen_set_level(self, dbm: float) -> None:
        self._write(f"SOURce:GPRF:GEN:RFLevel:POWer {dbm}")

    def gen_get_level(self) -> float:
        return self._query_float("SOURce:GPRF:GEN:RFLevel:POWer?")

    def gen_set_output(self, enabled: bool) -> None:
        self._write(f"SOURce:GPRF:GEN:STAT {'ON' if enabled else 'OFF'}")

    def gen_get_output(self) -> bool:
        return self._query("SOURce:GPRF:GEN:STAT?") in ("1", "ON")

    def gen_set_modulation(self, mod: str = "CW") -> None:
        """CW | WLAN | BT | LTE etc. (depends on installed options)."""
        self._write(f"SOURce:GPRF:GEN:MODulation {mod}")

    # ------------------------------------------------------------------ #
    #  Power Measurement                                                   #
    # ------------------------------------------------------------------ #

    def meas_set_frequency(self, freq_hz: float) -> None:
        self._write(f"CONFigure:GPRF:MEAS:POWer:FREQuency {freq_hz:.0f}")

    def meas_set_filter_bandwidth(self, bw_hz: float) -> None:
        self._write(f"CONFigure:GPRF:MEAS:POWer:FILTer:BANDwidth {bw_hz:.0f}")

    def meas_set_trigger_source(self, source: str = "IMMediate") -> None:
        """IMMediate | EXTernal | IF | Power."""
        self._write(f"CONFigure:GPRF:MEAS:POWer:TRIGger:SOURce {source}")

    def meas_set_count(self, count: int) -> None:
        """Number of averages."""
        self._write(f"CONFigure:GPRF:MEAS:POWer:COUNt {count}")

    def meas_initiate_power(self) -> None:
        """INITiate a single-shot power measurement."""
        self._write("INITiate:GPRF:MEAS:POWer")

    def meas_read_power(self, timeout: float = 10.0) -> GPRFPowerResult:
        """Start measurement and return result (blocks until complete)."""
        self._write("INITiate:GPRF:MEAS:POWer")
        self._poll_state(
            "FETCh:GPRF:MEAS:POWer:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:GPRF:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return GPRFPowerResult(
            status=parts[0],
            current=float(parts[1]),
            average=float(parts[2]),
            minimum=float(parts[3]),
            maximum=float(parts[4]),
        )

    def meas_fetch_power(self) -> GPRFPowerResult:
        """Return the last power measurement without re-triggering."""
        raw = self._query("FETCh:GPRF:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return GPRFPowerResult(
            status=parts[0],
            current=float(parts[1]),
            average=float(parts[2]),
            minimum=float(parts[3]),
            maximum=float(parts[4]),
        )

    def meas_abort_power(self) -> None:
        self._write("STOP:GPRF:MEAS:POWer")

    # ------------------------------------------------------------------ #
    #  Spectrum measurement                                                #
    # ------------------------------------------------------------------ #

    def spec_set_center_frequency(self, freq_hz: float) -> None:
        self._write(f"CONFigure:GPRF:MEAS:SPECtrum:FREQuency:CENTer {freq_hz:.0f}")

    def spec_set_span(self, span_hz: float) -> None:
        self._write(f"CONFigure:GPRF:MEAS:SPECtrum:FREQuency:SPAN {span_hz:.0f}")

    def spec_set_rbw(self, rbw_hz: float) -> None:
        self._write(f"CONFigure:GPRF:MEAS:SPECtrum:BANDwidth:RESolution {rbw_hz:.0f}")

    def spec_read(self, timeout: float = 15.0) -> GPRFSpectrumResult:
        self._write("INITiate:GPRF:MEAS:SPECtrum")
        self._poll_state(
            "FETCh:GPRF:MEAS:SPECtrum:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:GPRF:MEAS:SPECtrum:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return GPRFSpectrumResult(
            status=parts[0],
            start_freq=float(parts[1]),
            stop_freq=float(parts[2]),
            peak_power=float(parts[3]),
            peak_freq=float(parts[4]),
        )
