"""Bluetooth (Classic + LE) application on CMW."""

from dataclasses import dataclass
from .base import BaseMixin


@dataclass
class BTRFResult:
    status: str
    power_dbm: float
    freq_error_khz: float
    modulation_index: float


@dataclass
class BTBERResult:
    status: str
    ber_pct: float
    packet_count: int
    error_count: int


class BluetoothModule(BaseMixin):
    """Bluetooth Classic (BR/EDR) and Bluetooth LE measurements."""

    _BT = "BT"
    _BTLE = "BLE"

    # ------------------------------------------------------------------ #
    #  Common / connection setup                                           #
    # ------------------------------------------------------------------ #

    def set_frequency(self, channel: int) -> None:
        """Bluetooth channel number (0–78 for Classic, 0–39 for LE)."""
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:CHANnel {channel}")

    def set_expected_power(self, dbm: float) -> None:
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:EXPower {dbm}")

    def set_packet_type(self, ptype: str = "DH1") -> None:
        """DH1 | DH3 | DH5 | 2DH1 | 2DH3 | 3DH1 | 3DH3 | 3DH5 | LE1M | LE2M | LECODED"""
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:PACKet {ptype}")

    def set_trigger_source(self, source: str = "POWer") -> None:
        """IMMediate | POWer | EXTernal"""
        self._write(f"CONFigure:{self._BT}:MEAS:TRIGger:SOURce {source}")

    def set_burst_count(self, count: int) -> None:
        self._write(f"CONFigure:{self._BT}:MEAS:COUNt:STATistics {count}")

    # ------------------------------------------------------------------ #
    #  TX power measurement                                                #
    # ------------------------------------------------------------------ #

    def measure_tx_power(self, timeout: float = 15.0) -> BTRFResult:
        self._write(f"INITiate:{self._BT}:MEAS:POWer")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:POWer:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTRFResult(
            status=parts[0],
            power_dbm=float(parts[1]),
            freq_error_khz=float(parts[2]),
            modulation_index=float(parts[3]),
        )

    def fetch_tx_power(self) -> BTRFResult:
        raw = self._query(f"FETCh:{self._BT}:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTRFResult(
            status=parts[0],
            power_dbm=float(parts[1]),
            freq_error_khz=float(parts[2]),
            modulation_index=float(parts[3]),
        )

    # ------------------------------------------------------------------ #
    #  Frequency deviation / modulation                                   #
    # ------------------------------------------------------------------ #

    def measure_modulation(self, timeout: float = 15.0) -> dict:
        self._write(f"INITiate:{self._BT}:MEAS:MODulation")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:MODulation:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:MODulation:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "max_freq_dev_khz": float(parts[1]),
            "avg_freq_dev_khz": float(parts[2]),
            "modulation_index": float(parts[3]),
        }

    # ------------------------------------------------------------------ #
    #  BER (Bit Error Rate)                                                #
    # ------------------------------------------------------------------ #

    def configure_ber(self, packet_count: int = 1000) -> None:
        self._write(f"CONFigure:{self._BT}:MEAS:BER:PACKets {packet_count}")

    def measure_ber(self, timeout: float = 30.0) -> BTBERResult:
        self._write(f"INITiate:{self._BT}:MEAS:BER")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:BER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:BER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTBERResult(
            status=parts[0],
            ber_pct=float(parts[1]),
            packet_count=int(parts[2]),
            error_count=int(parts[3]),
        )

    # ------------------------------------------------------------------ #
    #  Bluetooth LE specific                                               #
    # ------------------------------------------------------------------ #

    def le_set_phy(self, phy: str = "LE1M") -> None:
        """LE1M | LE2M | LECoded_S2 | LECoded_S8"""
        self._write(f"CONFigure:{self._BTLE}:MEAS:PHY {phy}")

    def le_set_channel(self, channel: int) -> None:
        """LE channel index 0–39."""
        self._write(f"CONFigure:{self._BTLE}:MEAS:CHANnel {channel}")

    def le_measure_tx_power(self, timeout: float = 15.0) -> BTRFResult:
        self._write(f"INITiate:{self._BTLE}:MEAS:POWer")
        self._poll_state(
            f"FETCh:{self._BTLE}:MEAS:POWer:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BTLE}:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTRFResult(
            status=parts[0],
            power_dbm=float(parts[1]),
            freq_error_khz=float(parts[2]),
            modulation_index=float(parts[3]),
        )

    def le_measure_ber(self, packet_count: int = 1000, timeout: float = 30.0) -> BTBERResult:
        self._write(f"CONFigure:{self._BTLE}:MEAS:BER:PACKets {packet_count}")
        self._write(f"INITiate:{self._BTLE}:MEAS:BER")
        self._poll_state(
            f"FETCh:{self._BTLE}:MEAS:BER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BTLE}:MEAS:BER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTBERResult(
            status=parts[0],
            ber_pct=float(parts[1]),
            packet_count=int(parts[2]),
            error_count=int(parts[3]),
        )
