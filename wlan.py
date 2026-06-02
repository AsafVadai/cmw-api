"""WLAN (Wi-Fi) application on CMW (requires CMW-KM052x / CMW-KM053x options)."""

from dataclasses import dataclass
from .base import BaseMixin


@dataclass
class WLANPowerResult:
    status: str
    power_dbm: float
    avg_power_dbm: float
    peak_power_dbm: float


@dataclass
class WLANEVMResult:
    status: str
    evm_rms_db: float
    evm_peak_db: float
    freq_error_khz: float
    symbol_clock_error_ppm: float


class WLANModule(BaseMixin):
    """WLAN 802.11 a/b/g/n/ac/ax/be measurements."""

    _WLAN = "WLAN"

    # ------------------------------------------------------------------ #
    #  Configuration                                                       #
    # ------------------------------------------------------------------ #

    def set_standard(self, std: str = "N") -> None:
        """
        Select the 802.11 standard variant.

        Supported values:
          A   — 802.11a   (5 GHz OFDM, up to 54 Mbps)
          B   — 802.11b   (2.4 GHz DSSS, up to 11 Mbps)
          G   — 802.11g   (2.4 GHz OFDM, up to 54 Mbps)
          N   — 802.11n   (HT, 2.4/5 GHz, up to 600 Mbps)
          AC  — 802.11ac  (VHT, 5 GHz, up to ~7 Gbps)
          AX  — 802.11ax  (HE / Wi-Fi 6/6E, 2.4/5/6 GHz)
          BE  — 802.11be  (EHT / Wi-Fi 7, 2.4/5/6 GHz, MLO, up to 46 Gbps)

        Note: BE requires firmware support and the CMW-KM053x option.
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:STANdard IEEE802{std}")

    def set_channel(self, channel: int) -> None:
        """802.11 channel number."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:CHANnel {channel}")

    def set_frequency(self, freq_hz: float) -> None:
        self._write(f"CONFigure:{self._WLAN}:MEAS:FREQuency {freq_hz:.0f}")

    def set_bandwidth(self, bw_mhz: int) -> None:
        """20 | 40 | 80 | 160 | 320 MHz  (320 MHz requires 802.11be / Wi-Fi 7)"""
        self._write(f"CONFigure:{self._WLAN}:MEAS:BANDwidth {bw_mhz}")

    # ------------------------------------------------------------------ #
    #  802.11be (Wi-Fi 7) — EHT specific configuration                   #
    # ------------------------------------------------------------------ #

    def set_eht_mcs(self, mcs: int) -> None:
        """
        Set the EHT MCS index for 802.11be (Wi-Fi 7).

        Valid range: 0–13
          MCS 0–9  : shared with 802.11ax
          MCS 10–11: 1024-QAM (new in 802.11be)
          MCS 12–13: 4096-QAM (new in 802.11be)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:MCS {mcs}")

    def set_eht_puncturing_pattern(self, pattern: str) -> None:
        """
        Configure the preamble puncturing pattern (802.11be).

        Puncturing removes specific sub-channels to avoid interference,
        primarily in 80/160/320 MHz operation.

        pattern: NONE | P80 | P160 | P320 | custom bitmask string
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:PUNCturing {pattern}")

    def set_mlo_link(self, link_id: int, freq_hz: float, bw_mhz: int) -> None:
        """
        Configure one link of a Multi-Link Operation (MLO) setup (802.11be).

        Wi-Fi 7 allows simultaneous transmission across multiple bands/channels
        (e.g. 2.4 GHz + 5 GHz + 6 GHz). Each logical link is identified by
        link_id (0-based).

        link_id  : 0, 1, or 2
        freq_hz  : centre frequency of the link in Hz
        bw_mhz   : channel bandwidth of the link (20 | 40 | 80 | 160 | 320)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINK{link_id}:FREQuency {freq_hz:.0f}")
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINK{link_id}:BANDwidth {bw_mhz}")

    def set_mlo_link_count(self, count: int) -> None:
        """Set the number of active MLO links (1–3)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINKcount {count}")

    def set_eht_spatial_reuse(self, enabled: bool) -> None:
        """Enable or disable EHT spatial reuse (BSS colouring extension in 802.11be)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:SPATialreuse {'ON' if enabled else 'OFF'}")

    def set_expected_power(self, dbm: float) -> None:
        self._write(f"CONFigure:{self._WLAN}:MEAS:EXPower {dbm}")

    def set_trigger_source(self, source: str = "POWer") -> None:
        """IMMediate | POWer | EXTernal"""
        self._write(f"CONFigure:{self._WLAN}:MEAS:TRIGger:SOURce {source}")

    def set_mcs(self, mcs: int) -> None:
        """MCS index 0–9 (802.11n/ac/ax)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:MCS {mcs}")

    def set_guard_interval(self, gi: str = "NORM") -> None:
        """NORM (800ns) | SHORT (400ns) | VSHORT (HE 200ns)"""
        self._write(f"CONFigure:{self._WLAN}:MEAS:GUARdinterval {gi}")

    def set_spatial_streams(self, streams: int = 1) -> None:
        self._write(f"CONFigure:{self._WLAN}:MEAS:SPATialstreams {streams}")

    def set_burst_count(self, count: int) -> None:
        self._write(f"CONFigure:{self._WLAN}:MEAS:COUNt:STATistics {count}")

    # ------------------------------------------------------------------ #
    #  TX power measurement                                                #
    # ------------------------------------------------------------------ #

    def measure_tx_power(self, timeout: float = 15.0) -> WLANPowerResult:
        self._write(f"INITiate:{self._WLAN}:MEAS:POWer")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:POWer:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._WLAN}:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return WLANPowerResult(
            status=parts[0],
            power_dbm=float(parts[1]),
            avg_power_dbm=float(parts[2]),
            peak_power_dbm=float(parts[3]),
        )

    # ------------------------------------------------------------------ #
    #  Modulation / EVM                                                    #
    # ------------------------------------------------------------------ #

    def measure_evm(self, timeout: float = 15.0) -> WLANEVMResult:
        self._write(f"INITiate:{self._WLAN}:MEAS:EVMeasurement")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:EVMeasurement:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._WLAN}:MEAS:EVMeasurement:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return WLANEVMResult(
            status=parts[0],
            evm_rms_db=float(parts[1]),
            evm_peak_db=float(parts[2]),
            freq_error_khz=float(parts[3]),
            symbol_clock_error_ppm=float(parts[4]),
        )

    # ------------------------------------------------------------------ #
    #  Spectral mask                                                        #
    # ------------------------------------------------------------------ #

    def measure_spectral_mask(self, timeout: float = 15.0) -> dict:
        self._write(f"INITiate:{self._WLAN}:MEAS:SPECtrum")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:SPECtrum:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._WLAN}:MEAS:SPECtrum:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "mask_result": parts[1],     # PASS | FAIL
            "peak_power_dbm": float(parts[2]),
            "margin_db": float(parts[3]),
        }

    # ------------------------------------------------------------------ #
    #  RX sensitivity / PER                                               #
    # ------------------------------------------------------------------ #

    def configure_per(self, packet_count: int = 1000) -> None:
        """Configure packet error rate test."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:PER:PACKets {packet_count}")

    def measure_per(self, timeout: float = 30.0) -> dict:
        self._write(f"INITiate:{self._WLAN}:MEAS:PER")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:PER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._WLAN}:MEAS:PER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "per_pct": float(parts[1]),
            "packet_count": int(parts[2]),
            "error_count": int(parts[3]),
        }
