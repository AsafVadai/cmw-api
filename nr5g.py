"""5G NR (New Radio) signaling application — SA and NSA modes."""

from dataclasses import dataclass
from .base import BaseMixin


@dataclass
class NR5GCellConfig:
    band: int = 78               # n78 = 3.5 GHz sub-6
    dl_arfcn: int = 632628       # NR-ARFCN
    scs_khz: int = 30            # Sub-carrier spacing: 15|30|60|120|240
    bandwidth_mhz: int = 100
    dl_power_dbm: float = -60.0
    cell_id: int = 1
    tac: int = 1
    mcc: str = "001"
    mnc: str = "01"
    mode: str = "SA"             # SA | NSA


@dataclass
class NR5GMeasResult:
    status: str
    ss_rsrp_dbm: float
    ss_rsrq_db: float
    ss_sinr_db: float
    csi_rsrp_dbm: float


@dataclass
class NR5GThroughputResult:
    status: str
    dl_throughput_mbps: float
    ul_throughput_mbps: float
    dl_bler_pct: float
    ul_bler_pct: float


class NR5GModule(BaseMixin):
    """5G NR signaling application on CMW."""

    _PREFIX = "CONFigure:NR5G:SIGN"
    _CALL = "CALL:NR5G:SIGN"

    # ------------------------------------------------------------------ #
    #  Cell Configuration                                                  #
    # ------------------------------------------------------------------ #

    def configure_cell(self, cfg: NR5GCellConfig) -> None:
        p = self._PREFIX
        self._write(f"{p}:CELL:BAND NR{cfg.band}")
        self._write(f"{p}:CELL:DL:NRARFcn {cfg.dl_arfcn}")
        self._write(f"{p}:CELL:SCS SCS{cfg.scs_khz}K")
        self._write(f"{p}:CELL:BAND:DL:BW BW{cfg.bandwidth_mhz}")
        self._write(f"{p}:CELL:DL:POWer {cfg.dl_power_dbm}")
        self._write(f"{p}:CELL:ID {cfg.cell_id}")
        self._write(f"{p}:CELL:TAC {cfg.tac}")
        self._write(f"{p}:CELL:MCC {cfg.mcc}")
        self._write(f"{p}:CELL:MNC {cfg.mnc}")
        self._write(f"{p}:MODE {cfg.mode}")

    def set_band(self, nr_band: int) -> None:
        self._write(f"{self._PREFIX}:CELL:BAND NR{nr_band}")

    def set_dl_arfcn(self, arfcn: int) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:NRARFcn {arfcn}")

    def set_scs(self, scs_khz: int) -> None:
        self._write(f"{self._PREFIX}:CELL:SCS SCS{scs_khz}K")

    def set_bandwidth(self, bw_mhz: int) -> None:
        self._write(f"{self._PREFIX}:CELL:BAND:DL:BW BW{bw_mhz}")

    def set_dl_power(self, dbm: float) -> None:
        self._write(f"{self._PREFIX}:CELL:DL:POWer {dbm}")

    def set_mode(self, mode: str) -> None:
        """SA (standalone) or NSA (non-standalone / EN-DC)."""
        self._write(f"{self._PREFIX}:MODE {mode}")

    def set_mcc_mnc(self, mcc: str, mnc: str) -> None:
        self._write(f"{self._PREFIX}:CELL:MCC {mcc}")
        self._write(f"{self._PREFIX}:CELL:MNC {mnc}")

    def set_imsi(self, imsi: str) -> None:
        self._write(f"{self._PREFIX}:MS:IMSI '{imsi}'")

    def set_authentication(self, algo: str, ki: str = "", op: str = "") -> None:
        self._write(f"{self._PREFIX}:MS:AUTH:ALG {algo}")
        if ki:
            self._write(f"{self._PREFIX}:MS:AUTH:KI '{ki}'")
        if op and algo == "MILENAGE":
            self._write(f"{self._PREFIX}:MS:AUTH:OP '{op}'")

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

    def expect_attach(self, timeout: float = 90.0) -> str:
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("ATTached", "CONNected"),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def get_call_status(self) -> str:
        return self._query(f"{self._CALL}:STATus?")

    def connect(self, timeout: float = 90.0) -> str:
        self._write(f"{self._CALL}:CONN")
        return self._poll_state(
            f"{self._CALL}:STATus?",
            target_states=("CONNected",),
            error_states=("DERegistered",),
            timeout=timeout,
        )

    def disconnect(self) -> None:
        self._write(f"{self._CALL}:DISC")

    # ------------------------------------------------------------------ #
    #  RX quality (SS-RSRP / SS-RSRQ / SS-SINR / CSI-RSRP)              #
    # ------------------------------------------------------------------ #

    def measure_rx_quality(self, timeout: float = 15.0) -> NR5GMeasResult:
        self._write("INITiate:NR5G:SIGN:RXQuality")
        self._poll_state(
            "FETCh:NR5G:SIGN:RXQuality:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:NR5G:SIGN:RXQuality:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return NR5GMeasResult(
            status=parts[0],
            ss_rsrp_dbm=self._safe_float(parts[1]),
            ss_rsrq_db=self._safe_float(parts[2]),
            ss_sinr_db=self._safe_float(parts[3]),
            csi_rsrp_dbm=self._safe_float(parts[4]),
        )

    # ------------------------------------------------------------------ #
    #  Throughput                                                          #
    # ------------------------------------------------------------------ #

    def configure_throughput(self, direction: str = "DL", duration_s: float = 10.0) -> None:
        self._write(f"CONFigure:NR5G:SIGN:ITP:DIR {direction}")
        self._write(f"CONFigure:NR5G:SIGN:ITP:DURation {duration_s}")

    def measure_throughput(self, timeout: float = 60.0) -> NR5GThroughputResult:
        self._write("INITiate:NR5G:SIGN:ITP")
        self._poll_state(
            "FETCh:NR5G:SIGN:ITP:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:NR5G:SIGN:ITP:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return NR5GThroughputResult(
            status=parts[0],
            dl_throughput_mbps=self._safe_float(parts[1]),
            ul_throughput_mbps=self._safe_float(parts[2]),
            dl_bler_pct=self._safe_float(parts[3]),
            ul_bler_pct=self._safe_float(parts[4]),
        )

    # ------------------------------------------------------------------ #
    #  Modulation quality (EVM)                                            #
    # ------------------------------------------------------------------ #

    def measure_evm(self, timeout: float = 15.0) -> dict:
        self._write("INITiate:NR5G:SIGN:MODulation")
        self._poll_state(
            "FETCh:NR5G:SIGN:MODulation:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:NR5G:SIGN:MODulation:EVM:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "evm_rms_pct": self._safe_float(parts[1]),
            "evm_peak_pct": self._safe_float(parts[2]),
            "freq_error_hz": self._safe_float(parts[3]),
        }

    # ------------------------------------------------------------------ #
    #  BLER                                                                #
    # ------------------------------------------------------------------ #

    def measure_bler(self, samples: int = 1000, timeout: float = 30.0) -> dict:
        self._write(f"CONFigure:NR5G:SIGN:BLER:SAMPles {samples}")
        self._write("INITiate:NR5G:SIGN:BLER")
        self._poll_state(
            "FETCh:NR5G:SIGN:BLER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query("FETCh:NR5G:SIGN:BLER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "dl_bler_pct": self._safe_float(parts[1]),
            "ul_bler_pct": self._safe_float(parts[2]),
        }

    # ------------------------------------------------------------------ #
    #  EN-DC (Non-Standalone) helpers                                      #
    # ------------------------------------------------------------------ #

    def endc_set_lte_anchor_band(self, band: int) -> None:
        """Configure the LTE anchor band for EN-DC (NSA) operation."""
        self._write(f"{self._PREFIX}:ENDC:LTE:BAND {band}")

    def endc_set_lte_earfcn(self, earfcn: int) -> None:
        self._write(f"{self._PREFIX}:ENDC:LTE:EARFCN {earfcn}")

    def endc_get_status(self) -> str:
        return self._query(f"{self._CALL}:ENDC:STATus?")
