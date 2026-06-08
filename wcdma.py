"""WCDMA / UMTS signaling application on CMW."""

from dataclasses import dataclass
from .base import BaseMixin


@dataclass
class WCDMACellConfig:
    band: int = 1
    dl_uarfcn: int = 10700
    dl_power_dbm: float = -60.0
    cell_id: int = 1
    mcc: str = "001"
    mnc: str = "01"
    imsi: str = ""


@dataclass
class WCDMAMeasResult:
    status: str
    rscp_dbm: float
    ec_no_db: float
    rssi_dbm: float


class WCDMAModule(BaseMixin):
    """WCDMA (UMTS) signaling application."""

    _PREFIX = "CONFigure:WCDMA:SIGN"
    _CALL = "CALL:WCDMA:SIGN"

    def configure_cell(self, cfg: WCDMACellConfig) -> None:
        p = self._PREFIX
        self._write(f"{p}:CELL:BAND {cfg.band}")
        self._write(f"{p}:CELL:DL:UARFcn {cfg.dl_uarfcn}")
        self._write(f"{p}:CELL:DL:POWer {cfg.dl_power_dbm}")
        self._write(f"{p}:CELL:ID {cfg.cell_id}")
        self._write(f"{p}:CELL:MCC {cfg.mcc}")
        self._write(f"{p}:CELL:MNC {cfg.mnc}")
        if cfg.imsi:
            self._write(f"{p}:MS:IMSI '{cfg.imsi}'")

    def set_band(self, band: int) -> None:
        self._write(f"{self._PREFIX}:CELL:BAND {band}")

    def set_dl_uarfcn(self, uarfcn: int) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:UARFcn {uarfcn}")

    def set_dl_power(self, dbm: float) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:POWer {dbm}")

    def cell_on(self) -> None:
        self._write(f"{self._PREFIX}:CELL:STATe ON")

    def cell_off(self) -> None:
        self._write(f"{self._PREFIX}:CELL:STATe OFF")

    def get_call_status(self) -> str:
        return self._query(f"{self._CALL}:STATus?")

    def expect_attach(self, timeout: float = 60.0) -> str:
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("ATTached", "CONNected"),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def connect(self, timeout: float = 60.0) -> str:
        self._write(f"{self._CALL}:CONN")
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("CONNected",),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def disconnect(self) -> None:
        self._write(f"{self._CALL}:DISC")

    def measure_rx_quality(self, timeout: float = 15.0) -> WCDMAMeasResult:
        self._write("INITiate:WCDMA:SIGN:RXQuality")
        self._poll_state(
            "FETCh:WCDMA:SIGN:RXQuality:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:WCDMA:SIGN:RXQuality:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return WCDMAMeasResult(
            status=parts[0],
            rscp_dbm=self._safe_float(parts[1]),
            ec_no_db=self._safe_float(parts[2]),
            rssi_dbm=self._safe_float(parts[3]),
        )

    def measure_ul_power(self, timeout: float = 15.0) -> dict:
        self._write("INITiate:WCDMA:SIGN:ULPower")
        self._poll_state(
            "FETCh:WCDMA:SIGN:ULPower:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:WCDMA:SIGN:ULPower:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "dpcch_power_dbm": self._safe_float(parts[1]),
            "dpdch_power_dbm": self._safe_float(parts[2]),
        }
