"""LTE signaling application — cell setup, call control, and measurements."""

from dataclasses import dataclass, field
from typing import Optional
from .base import BaseMixin


@dataclass
class LTECellConfig:
    band: int = 1
    dl_channel: int = 300       # EARFCN
    bandwidth_mhz: float = 10.0
    dl_power_dbm: float = -60.0
    ul_power_max_dbm: float = 23.0
    cell_id: int = 1
    tac: int = 1
    mcc: str = "001"
    mnc: str = "01"
    imsi: str = ""
    auth_algo: str = "MILENAGE"  # MILENAGE | XOR | NONE


@dataclass
class LTEMeasResult:
    status: str
    rsrp_dbm: float
    rsrq_db: float
    rssi_dbm: float
    sinr_db: float


@dataclass
class LTEThroughputResult:
    status: str
    dl_throughput_mbps: float
    ul_throughput_mbps: float
    dl_bler_pct: float
    ul_bler_pct: float


@dataclass
class LTERFPowerResult:
    status: str
    pusch_power_dbm: float
    pucch_power_dbm: float
    prach_power_dbm: float


class LTEModule(BaseMixin):
    """LTE FDD/TDD signaling application on CMW."""

    _PREFIX = "CONFigure:LTE:SIGN"
    _MEAS = "MEASure:LTE:SIGN"
    _FETCH = "FETCh:LTE:SIGN"
    _CALL = "CALL:LTE:SIGN"

    # ------------------------------------------------------------------ #
    #  Cell Configuration                                                  #
    # ------------------------------------------------------------------ #

    def configure_cell(self, cfg: LTECellConfig) -> None:
        """Apply a full cell configuration from an LTECellConfig object."""
        p = self._PREFIX
        self._write(f"{p}:CELL:BAND {cfg.band}")
        self._write(f"{p}:CELL:DL:EARFCN {cfg.dl_channel}")
        self._write(f"{p}:CELL:BAND:DL:BW BW{int(cfg.bandwidth_mhz)}")
        self._write(f"{p}:CELL:DL:POWer {cfg.dl_power_dbm}")
        self._write(f"{p}:CELL:UL:POWer:MAX {cfg.ul_power_max_dbm}")
        self._write(f"{p}:CELL:ID {cfg.cell_id}")
        self._write(f"{p}:CELL:TAC {cfg.tac}")
        self._write(f"{p}:CELL:MCC {cfg.mcc}")
        self._write(f"{p}:CELL:MNC {cfg.mnc}")
        if cfg.imsi:
            self._write(f"{p}:MS:IMSI '{cfg.imsi}'")
        self._write(f"{p}:MS:AUTH:ALG {cfg.auth_algo}")

    def set_band(self, band: int) -> None:
        self._write(f"{self._PREFIX}:CELL:BAND {band}")

    def set_dl_earfcn(self, earfcn: int) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:EARFCN {earfcn}")

    def set_bandwidth(self, bw_mhz: float) -> None:
        """bw_mhz: 1.4 | 3 | 5 | 10 | 15 | 20"""
        bw_map = {1.4: "BW1_4", 3: "BW3", 5: "BW5", 10: "BW10", 15: "BW15", 20: "BW20"}
        token = bw_map.get(bw_mhz, f"BW{int(bw_mhz)}")
        self._write(f"{self._PREFIX}:CELL:BAND:DL:BW {token}")

    def set_dl_power(self, dbm: float) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:POWer {dbm}")

    def get_dl_power(self) -> float:
        return self._query_float(f"{self._PREFIX}:CELL:DL:POWer?")

    def set_cell_id(self, cell_id: int) -> None:
        self._write(f"{self._PREFIX}:CELL:ID {cell_id}")

    def set_mcc_mnc(self, mcc: str, mnc: str) -> None:
        self._write(f"{self._PREFIX}:CELL:MCC {mcc}")
        self._write(f"{self._PREFIX}:CELL:MNC {mnc}")

    def set_imsi(self, imsi: str) -> None:
        self._write(f"{self._PREFIX}:MS:IMSI '{imsi}'")

    def set_authentication(self, algo: str, ki: str = "", op: str = "") -> None:
        """
        algo: MILENAGE | XOR | NONE
        ki:   subscriber key (hex string)
        op:   operator variant (hex string, MILENAGE only)
        """
        self._write(f"{self._PREFIX}:MS:AUTH:ALG {algo}")
        if ki:
            self._write(f"{self._PREFIX}:MS:AUTH:KI '{ki}'")
        if op and algo == "MILENAGE":
            self._write(f"{self._PREFIX}:MS:AUTH:OP '{op}'")

    def set_category(self, category: int) -> None:
        """UE category (1–15+)."""
        self._write(f"{self._PREFIX}:MS:CAT {category}")

    # ------------------------------------------------------------------ #
    #  DL/UL throughput configuration                                     #
    # ------------------------------------------------------------------ #

    def set_dl_modulation(self, mod: str = "AUTO") -> None:
        """QPSK | QAM16 | QAM64 | QAM256 | AUTO"""
        self._write(f"{self._PREFIX}:DL:MOD {mod}")

    def set_ul_modulation(self, mod: str = "AUTO") -> None:
        self._write(f"{self._PREFIX}:UL:MOD {mod}")

    def set_dl_rb_count(self, rb: int) -> None:
        self._write(f"{self._PREFIX}:DL:RB:COUNt {rb}")

    def set_ul_rb_count(self, rb: int) -> None:
        self._write(f"{self._PREFIX}:UL:RB:COUNt {rb}")

    def set_mimo(self, layers: int = 2) -> None:
        """Number of MIMO layers: 1 | 2 | 4"""
        self._write(f"{self._PREFIX}:DL:MIMO:LAYers {layers}")

    # ------------------------------------------------------------------ #
    #  Cell on/off                                                         #
    # ------------------------------------------------------------------ #

    def cell_on(self) -> None:
        self._write(f"{self._PREFIX}:CELL:STATe ON")

    def cell_off(self) -> None:
        self._write(f"{self._PREFIX}:CELL:STATe OFF")

    def get_cell_state(self) -> str:
        return self._query(f"{self._PREFIX}:CELL:STATe?")

    # ------------------------------------------------------------------ #
    #  Call control                                                        #
    # ------------------------------------------------------------------ #

    def expect_attach(self, timeout: float = 60.0) -> str:
        """Wait for UE to register/attach on the cell."""
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("ATTached", "CONNected"),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def get_call_status(self) -> str:
        return self._query(f"{self._CALL}:STATus?")

    def connect(self, timeout: float = 60.0) -> str:
        """Trigger data connection establishment and wait for CONNECTED."""
        self._write(f"{self._CALL}:CONN")
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("CONNected",),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def disconnect(self) -> None:
        self._write(f"{self._CALL}:DISC")

    def initiate_handover(self, target_band: int, earfcn: int) -> None:
        self._write(f"{self._PREFIX}:HO:BAND {target_band}")
        self._write(f"{self._PREFIX}:HO:EARFCN {earfcn}")
        self._write(f"{self._CALL}:HO:EXECute")

    # ------------------------------------------------------------------ #
    #  RX quality measurements (RSRP/RSRQ/RSSI/SINR)                     #
    # ------------------------------------------------------------------ #

    def measure_rx_quality(self, timeout: float = 15.0) -> LTEMeasResult:
        self._write(f"INITiate:LTE:SIGN:RXQuality")
        self._poll_state(
            f"FETCh:LTE:SIGN:RXQuality:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:LTE:SIGN:RXQuality:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return LTEMeasResult(
            status=parts[0],
            rsrp_dbm=self._safe_float(parts[1]),
            rsrq_db=self._safe_float(parts[2]),
            rssi_dbm=self._safe_float(parts[3]),
            sinr_db=self._safe_float(parts[4]),
        )

    def fetch_rx_quality(self) -> LTEMeasResult:
        raw = self._query("FETCh:LTE:SIGN:RXQuality:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return LTEMeasResult(
            status=parts[0],
            rsrp_dbm=self._safe_float(parts[1]),
            rsrq_db=self._safe_float(parts[2]),
            rssi_dbm=self._safe_float(parts[3]),
            sinr_db=self._safe_float(parts[4]),
        )

    # ------------------------------------------------------------------ #
    #  Throughput measurement (IP data)                                    #
    # ------------------------------------------------------------------ #

    def configure_throughput(
        self,
        direction: str = "DL",
        duration_s: float = 10.0,
        payload_kb: int = 0,
    ) -> None:
        """
        direction: DL | UL | DLULink (both)
        payload_kb: 0 = unlimited / time-based
        """
        self._write(f"CONFigure:LTE:SIGN:ITP:DIR {direction}")
        self._write(f"CONFigure:LTE:SIGN:ITP:DURation {duration_s}")
        if payload_kb:
            self._write(f"CONFigure:LTE:SIGN:ITP:PAYLoad {payload_kb}")

    def measure_throughput(self, timeout: float = 60.0) -> LTEThroughputResult:
        self._write("INITiate:LTE:SIGN:ITP")
        self._poll_state(
            "FETCh:LTE:SIGN:ITP:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:LTE:SIGN:ITP:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return LTEThroughputResult(
            status=parts[0],
            dl_throughput_mbps=self._safe_float(parts[1]),
            ul_throughput_mbps=self._safe_float(parts[2]),
            dl_bler_pct=self._safe_float(parts[3]),
            ul_bler_pct=self._safe_float(parts[4]),
        )

    # ------------------------------------------------------------------ #
    #  UL power measurements                                               #
    # ------------------------------------------------------------------ #

    def measure_ul_power(self, timeout: float = 15.0) -> LTERFPowerResult:
        self._write("INITiate:LTE:SIGN:ULPower")
        self._poll_state(
            "FETCh:LTE:SIGN:ULPower:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:LTE:SIGN:ULPower:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return LTERFPowerResult(
            status=parts[0],
            pusch_power_dbm=self._safe_float(parts[1]),
            pucch_power_dbm=self._safe_float(parts[2]),
            prach_power_dbm=self._safe_float(parts[3]),
        )

    # ------------------------------------------------------------------ #
    #  BLER / channel quality                                              #
    # ------------------------------------------------------------------ #

    def measure_bler(
        self,
        samples: int = 1000,
        timeout: float = 30.0,
    ) -> dict:
        self._write(f"CONFigure:LTE:SIGN:BLER:SAMPles {samples}")
        self._write("INITiate:LTE:SIGN:BLER")
        self._poll_state(
            "FETCh:LTE:SIGN:BLER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:LTE:SIGN:BLER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "dl_bler_pct": self._safe_float(parts[1]),
            "ul_bler_pct": self._safe_float(parts[2]),
            "dl_ack_count": self._safe_int(parts[3]),
            "dl_nack_count": self._safe_int(parts[4]),
        }

    # ------------------------------------------------------------------ #
    #  Modulation quality (EVM)                                            #
    # ------------------------------------------------------------------ #

    def measure_evm(self, timeout: float = 15.0) -> dict:
        self._write("INITiate:LTE:SIGN:MODulation")
        self._poll_state(
            "FETCh:LTE:SIGN:MODulation:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:LTE:SIGN:MODulation:EVM:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "evm_rms_pct": self._safe_float(parts[1]),
            "evm_peak_pct": self._safe_float(parts[2]),
            "freq_error_hz": self._safe_float(parts[3]),
            "timing_error_us": self._safe_float(parts[4]),
        }
