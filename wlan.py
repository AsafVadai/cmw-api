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


@dataclass
class WLANACPResult:
    """Adjacent Channel Power / ACLR result."""
    status: str
    primary_power_dbm: float
    lower_acp_dbm: float
    upper_acp_dbm: float
    lower_aclr_db: float
    upper_aclr_db: float


class WLANModule(BaseMixin):
    """WLAN 802.11 a/b/g/n/ac/ax/be (Wi-Fi 7) measurements.

    Required software options
    -------------------------
      802.11 a/b/g/n/ac/ax : CMW-KM052x
      802.11be  (Wi-Fi 7)  : CMW-KM053x  (in addition to CMW-KM052x)
    """

    _WLAN = "WLAN"

    # ------------------------------------------------------------------ #
    #  Standard / mode configuration                                       #
    # ------------------------------------------------------------------ #

    def set_standard(self, std: str = "N") -> None:
        """
        Select the 802.11 standard variant.

        Supported values
        ----------------
          A   — 802.11a   (5 GHz OFDM, up to 54 Mbps)
          B   — 802.11b   (2.4 GHz DSSS, up to 11 Mbps)
          G   — 802.11g   (2.4 GHz OFDM, up to 54 Mbps)
          N   — 802.11n   (HT, 2.4/5 GHz, MCS 0–31)
          AC  — 802.11ac  (VHT, 5 GHz, MCS 0–9)
          AX  — 802.11ax  (HE / Wi-Fi 6/6E, 2.4/5/6 GHz, MCS 0–11)
          BE  — 802.11be  (EHT / Wi-Fi 7, 2.4/5/6 GHz, MCS 0–13, MLO)

        Note
        ----
          - For A/B/G use set_data_rate() to select the modulation rate.
            set_mcs() is not applicable for these standards.
          - BE requires CMW firmware support and the CMW-KM053x option.
        """
        valid = {"A", "B", "G", "N", "AC", "AX", "BE"}
        if std.upper() not in valid:
            raise ValueError(f"Unknown standard '{std}'. Must be one of: {sorted(valid)}")
        self._write(f"CONFigure:{self._WLAN}:MEAS:STANdard IEEE802{std.upper()}")

    def set_channel(self, channel: int) -> None:
        """802.11 channel number (e.g. 1–14 for 2.4 GHz, 36–177 for 5 GHz, 1–233 for 6 GHz)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:CHANnel {channel}")

    def set_frequency(self, freq_hz: float) -> None:
        """Set centre frequency in Hz (alternative to set_channel)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:FREQuency {freq_hz:.0f}")

    def set_bandwidth(self, bw_mhz: int) -> None:
        """
        Set channel bandwidth in MHz.

        Valid values: 20 | 40 | 80 | 160 | 320
        320 MHz is only available with 802.11be (Wi-Fi 7).
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:BANDwidth {bw_mhz}")

    def set_expected_power(self, dbm: float) -> None:
        """Expected DUT TX power in dBm (used to set CMW input attenuator)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:EXPower {dbm}")

    def set_trigger_source(self, source: str = "POWer") -> None:
        """IMMediate | POWer | EXTernal"""
        self._write(f"CONFigure:{self._WLAN}:MEAS:TRIGger:SOURce {source}")

    def set_data_rate(self, rate_mbps: float) -> None:
        """
        Set the expected data rate for 802.11a/b/g (legacy OFDM/DSSS).

        Use this instead of set_mcs() when the active standard is A, B, or G.

        Valid rates
        -----------
          802.11a / g : 6, 9, 12, 18, 24, 36, 48, 54  Mbps
          802.11b     : 1, 2, 5.5, 11                  Mbps
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:DATArate {rate_mbps}")

    def set_mcs(self, mcs: int) -> None:
        """
        Set the MCS index for 802.11n/ac/ax.

        Valid ranges per standard
        -------------------------
          802.11n  (HT)  : MCS 0–31  (8 modulations × up to 4 spatial streams)
          802.11ac (VHT) : MCS 0–9
          802.11ax (HE)  : MCS 0–11
          802.11be (EHT) : use set_eht_mcs() instead (MCS 0–13)

        For 802.11a/b/g use set_data_rate() — MCS does not apply.
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:MCS {mcs}")

    def set_guard_interval(self, gi: str = "NORM") -> None:
        """
        Set the guard interval (cyclic prefix) duration.

        Values
        ------
          NORM   : 800 ns  — 802.11a/b/g/n/ac/ax/be
          SHORT  : 400 ns  — 802.11n/ac
          VSHORT : 200 ns  — 802.11ax (HE) and 802.11be (EHT)
          DBL    : 1600 ns — 802.11be (EHT) only, extended range
          QUAD   : 3200 ns — 802.11be (EHT) only, maximum range
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:GUARdinterval {gi}")

    def set_spatial_streams(self, streams: int = 1) -> None:
        """
        Set the number of spatial streams.

        Range: 1–4 for N/AC/AX, 1–16 for BE (802.11be supports up to 16 streams).
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:SPATialstreams {streams}")

    def set_burst_count(self, count: int) -> None:
        """Number of bursts to capture for statistical averaging."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:COUNt:STATistics {count}")

    # ------------------------------------------------------------------ #
    #  TX power measurement                                                #
    # ------------------------------------------------------------------ #

    def measure_tx_power(self, timeout: float = 15.0) -> WLANPowerResult:
        """Trigger and return TX burst power (current / average / peak)."""
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
        """Trigger and return EVM (RMS and peak), frequency error, and symbol clock error."""
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
    #  Spectral mask                                                       #
    # ------------------------------------------------------------------ #

    def measure_spectral_mask(self, timeout: float = 15.0) -> dict:
        """Trigger spectral mask test. Returns pass/fail, peak power, and margin."""
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
            "mask_result": parts[1],       # PASS | FAIL
            "peak_power_dbm": float(parts[2]),
            "margin_db": float(parts[3]),
        }

    # ------------------------------------------------------------------ #
    #  Adjacent Channel Power (ACP / ACLR)                                #
    # ------------------------------------------------------------------ #

    def configure_acp(self, offset_mhz: float = 20.0) -> None:
        """
        Configure the ACP measurement offset frequency.

        offset_mhz: distance from the channel centre to the adjacent channel centre.
        Typical values match the channel spacing: 20 MHz for 20 MHz channels,
        40 MHz for 40 MHz channels, etc.
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:ACP:OFFSet {offset_mhz}")

    def measure_acp(self, timeout: float = 15.0) -> WLANACPResult:
        """
        Trigger and return Adjacent Channel Power / ACLR measurement.

        Used for regulatory spectral compliance testing (FCC, ETSI, etc.).

        Returns
        -------
        WLANACPResult
          primary_power_dbm : in-channel TX power
          lower_acp_dbm     : power in lower adjacent channel (dBm)
          upper_acp_dbm     : power in upper adjacent channel (dBm)
          lower_aclr_db     : lower adjacent channel leakage ratio (dB, positive = better)
          upper_aclr_db     : upper adjacent channel leakage ratio (dB, positive = better)
        """
        self._write(f"INITiate:{self._WLAN}:MEAS:ACP")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:ACP:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._WLAN}:MEAS:ACP:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return WLANACPResult(
            status=parts[0],
            primary_power_dbm=float(parts[1]),
            lower_acp_dbm=float(parts[2]),
            upper_acp_dbm=float(parts[3]),
            lower_aclr_db=float(parts[4]),
            upper_aclr_db=float(parts[5]),
        )

    # ------------------------------------------------------------------ #
    #  Occupied Bandwidth (OBW)                                           #
    # ------------------------------------------------------------------ #

    def configure_obw(self, percent: float = 99.0) -> None:
        """
        Set the power percentage used for OBW calculation (typically 99 %).

        The OBW is the bandwidth containing the specified percentage of the total
        transmitted power.
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:OBW:PERCent {percent}")

    def measure_obw(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return Occupied Bandwidth measurement.

        Returns
        -------
        dict
          status  : 'RDY' on success
          obw_mhz : measured occupied bandwidth in MHz
        """
        self._write(f"INITiate:{self._WLAN}:MEAS:OBW")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:OBW:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        status = self._query(f"FETCh:{self._WLAN}:MEAS:OBW:STATus?")
        obw = self._query_float(f"FETCh:{self._WLAN}:MEAS:OBW:VALue?")
        return {"status": status, "obw_mhz": obw / 1e6}

    # ------------------------------------------------------------------ #
    #  RX sensitivity / RSSI                                              #
    # ------------------------------------------------------------------ #

    def measure_rssi(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return RSSI (Received Signal Strength Indicator).

        The CMW generates a calibrated downlink signal; the DUT reports RSSI
        which the CMW captures and returns.

        Returns
        -------
        dict
          status   : 'RDY' on success
          rssi_dbm : measured RSSI in dBm
        """
        self._write(f"INITiate:{self._WLAN}:MEAS:RXQuality")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:RXQuality:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        status = self._query(f"FETCh:{self._WLAN}:MEAS:RXQuality:STATus?")
        rssi = self._query_float(f"FETCh:{self._WLAN}:MEAS:RXQuality:RSSI?")
        return {"status": status, "rssi_dbm": rssi}

    # ------------------------------------------------------------------ #
    #  RX sensitivity / PER                                               #
    # ------------------------------------------------------------------ #

    def configure_per(self, packet_count: int = 1000) -> None:
        """Configure packet error rate test (number of packets to transmit)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:PER:PACKets {packet_count}")

    def measure_per(self, timeout: float = 30.0) -> dict:
        """
        Trigger and return Packet Error Rate measurement.

        Returns
        -------
        dict
          status        : 'RDY' on success
          per_pct       : packet error rate in percent
          packet_count  : total packets sent
          error_count   : packets with errors
        """
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

    # ------------------------------------------------------------------ #
    #  802.11ax (HE / Wi-Fi 6/6E) specific configuration                 #
    # ------------------------------------------------------------------ #

    def set_he_ppdu_format(self, fmt: str = "SU") -> None:
        """
        Set the HE PPDU format for 802.11ax transmissions.

        Values
        ------
          SU   : Single-User PPDU (default)
          MU   : Multi-User PPDU (DL MU-MIMO or DL OFDMA)
          TRIG : Trigger-Based PPDU (UL OFDMA / UL MU-MIMO)
          ER   : Extended Range SU PPDU (outdoor / long range)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:HE:PPDUFormat {fmt}")

    def set_bss_colour(self, colour: int) -> None:
        """
        Set the BSS Colour value (0–63) for 802.11ax/be spatial reuse.

        BSS Colour is a 6-bit field in the HE/EHT PPDU that allows overlapping
        BSSs to distinguish their frames and apply spatial reuse policies.
        Valid for both 802.11ax (HE) and 802.11be (EHT).
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:HE:BSS:COLour {colour}")

    def set_ofdma_ru_allocation(self, ru_string: str) -> None:
        """
        Configure OFDMA Resource Unit (RU) allocation for 802.11ax UL/DL.

        ru_string: comma-separated RU sizes in tones, e.g. "26,26,26,26" for
        four 26-tone RUs in a 20 MHz channel, or "242" for a single 242-tone
        RU (full 20 MHz).

        Common RU sizes (tones): 26, 52, 106, 242, 484, 996, 2×996
        """
        self._write(f'CONFigure:{self._WLAN}:MEAS:HE:OFDMA:TXRUAlloc "{ru_string}"')

    def set_twt(
        self,
        enabled: bool = True,
        wake_interval_ms: float = 512.0,
        sleep_duration_ms: float = 100.0,
    ) -> None:
        """
        Configure Target Wake Time (TWT) for 802.11ax power-save testing.

        Parameters
        ----------
        enabled           : enable or disable TWT negotiation
        wake_interval_ms  : interval between TWT service periods (ms)
        sleep_duration_ms : duration of the TWT sleep period (ms)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:HE:TWT:ENABle {'ON' if enabled else 'OFF'}")
        if enabled:
            self._write(f"CONFigure:{self._WLAN}:MEAS:HE:TWT:WAKEInterval {wake_interval_ms}")
            self._write(f"CONFigure:{self._WLAN}:MEAS:HE:TWT:SLEEPDuration {sleep_duration_ms}")

    # ------------------------------------------------------------------ #
    #  802.11be (EHT / Wi-Fi 7) specific configuration                   #
    # ------------------------------------------------------------------ #

    def set_eht_mcs(self, mcs: int) -> None:
        """
        Set the EHT MCS index for 802.11be (Wi-Fi 7).

        Valid range: 0–13
          MCS 0–9  : shared with 802.11ax (up to 1024-QAM 5/6)
          MCS 10–11: 1024-QAM (new in 802.11be)
          MCS 12–13: 4096-QAM (new in 802.11be, requires very high SNR)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:MCS {mcs}")

    def set_eht_puncturing_pattern(self, pattern: str) -> None:
        """
        Configure preamble puncturing for 802.11be.

        Puncturing removes specific 20 MHz sub-channels from a wider channel
        to avoid interference (e.g. from a legacy BSS).

        Values: NONE | P80 | P160 | P320 | <custom bitmask string>
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:PUNCturing {pattern}")

    def set_mlo_link(self, link_id: int, freq_hz: float, bw_mhz: int) -> None:
        """
        Configure one link of a Multi-Link Operation (MLO) setup (802.11be).

        Wi-Fi 7 allows simultaneous TX/RX across multiple bands (e.g. 2.4 + 5 + 6 GHz).
        Each logical link is identified by link_id (0-based, max 2).

        Parameters
        ----------
        link_id : 0, 1, or 2
        freq_hz : centre frequency in Hz
        bw_mhz  : channel bandwidth (20 | 40 | 80 | 160 | 320)
        """
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINK{link_id}:FREQuency {freq_hz:.0f}")
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINK{link_id}:BANDwidth {bw_mhz}")

    def set_mlo_link_count(self, count: int) -> None:
        """Set the number of active MLO links (1–3)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:MLO:LINKcount {count}")

    def measure_tx_power_mlo(self, link_count: int = 3, timeout: float = 15.0) -> dict:
        """
        Trigger TX power measurement for each active MLO link (802.11be).

        Returns per-link average power after calling INITiate:WLAN:MEAS:POWer.
        The aggregate (all-links) result is also available via measure_tx_power().

        Parameters
        ----------
        link_count : number of active MLO links (must match set_mlo_link_count())

        Returns
        -------
        dict with keys link_0_power_dbm, link_1_power_dbm, link_2_power_dbm
        (only keys for active links are populated).
        """
        self._write(f"INITiate:{self._WLAN}:MEAS:POWer")
        self._poll_state(
            f"FETCh:{self._WLAN}:MEAS:POWer:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        result = {}
        for i in range(min(link_count, 3)):
            val = self._query_float(f"FETCh:{self._WLAN}:MEAS:MLO:LINK{i}:POWer:AVG?")
            result[f"link_{i}_power_dbm"] = val
        return result

    def set_eht_spatial_reuse(self, enabled: bool) -> None:
        """Enable or disable EHT spatial reuse (BSS colouring extension in 802.11be)."""
        self._write(f"CONFigure:{self._WLAN}:MEAS:EHT:SPATialreuse {'ON' if enabled else 'OFF'}")
