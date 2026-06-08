"""Bluetooth Classic (BR/EDR) and Bluetooth LE application on CMW."""

from dataclasses import dataclass
from .base import BaseMixin
from .exceptions import CMWError


@dataclass
class BTRFResult:
    status: str
    power_dbm: float
    freq_error_khz: float
    modulation_index: float   # 0.0 for PHYs that do not report this field


@dataclass
class BTBERResult:
    status: str
    ber_pct: float
    packet_count: int
    error_count: int


@dataclass
class BTLEPERResult:
    """BLE Packet Error Rate result (conformance metric)."""
    status: str
    per_pct: float
    packet_count: int
    error_count: int


# LE PHY names that are NOT valid Classic packet types
_LE_PHY_NAMES = {"LE1M", "LE2M", "LECODED", "LECODED_S2", "LECODED_S8"}


class BluetoothModule(BaseMixin):
    """Bluetooth Classic (BR/EDR) and Bluetooth LE measurements.

    Transport prefix mapping (CMW firmware R3.7+)
    ----------------------------------------------
      Classic BR/EDR : BT   (legacy firmware used BTooth)
      Bluetooth LE   : BLE  (legacy firmware used BTLE)
    """

    _BT = "BT"
    _BTLE = "BLE"

    # ================================================================== #
    #  Bluetooth Classic (BR/EDR)                                         #
    # ================================================================== #

    # ------------------------------------------------------------------ #
    #  Classic — configuration                                            #
    # ------------------------------------------------------------------ #

    def set_frequency(self, channel: int) -> None:
        """
        Set the Bluetooth Classic channel (0–78, where channel N = 2402 + N MHz).

        Classic only. For BLE use le_set_channel().
        """
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:CHANnel {channel}")

    def set_expected_power(self, dbm: float) -> None:
        """
        Set the expected DUT TX power for Bluetooth Classic (dBm).

        Classic only. For BLE use le_set_expected_power().
        """
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:EXPower {dbm}")

    def set_packet_type(self, ptype: str = "DH1") -> None:
        """
        Set the Bluetooth Classic packet type.

        Valid values (BR): DH1, DH3, DH5
        Valid values (EDR 2 Mbps): 2DH1, 2DH3, 2DH5
        Valid values (EDR 3 Mbps): 3DH1, 3DH3, 3DH5

        Note: LE PHY names (LE1M, LE2M, LECoded_S2, etc.) are NOT valid here.
              Use le_set_phy() for BLE PHY selection.
        """
        if ptype.upper().replace("_", "") in {p.replace("_", "") for p in _LE_PHY_NAMES}:
            raise CMWError(
                f"'{ptype}' is a BLE PHY — use le_set_phy() for BLE. "
                "set_packet_type() accepts Classic BR/EDR packet types only."
            )
        self._write(f"CONFigure:{self._BT}:MEAS:RFSettings:PACKet {ptype}")

    def set_trigger_source(self, source: str = "POWer") -> None:
        """IMMediate | POWer | EXTernal"""
        self._write(f"CONFigure:{self._BT}:MEAS:TRIGger:SOURce {source}")

    def set_burst_count(self, count: int) -> None:
        """Number of bursts to capture for statistical averaging."""
        self._write(f"CONFigure:{self._BT}:MEAS:COUNt:STATistics {count}")

    def set_payload_pattern(self, pattern: str = "PRBS9") -> None:
        """
        Set the payload data pattern for Bluetooth Classic BER / loopback tests.

        Values
        ------
          PRBS9     : Pseudo-random (9-bit) — standard conformance pattern
          PRBS15    : Pseudo-random (15-bit)
          11110000  : Alternating nibbles
          10101010  : Alternating bits
          ALLOnes   : All 1s
          ALLZeros  : All 0s
        """
        self._write(f"CONFigure:{self._BT}:MEAS:PATTern {pattern}")

    def set_whitening(self, enabled: bool, tech: str = "BT") -> None:
        """
        Enable or disable data whitening.

        Parameters
        ----------
        enabled : True = whitening ON (standard), False = OFF (debug/test only)
        tech    : 'BT' for Classic, 'BLE' for Bluetooth LE
        """
        prefix = self._BT if tech.upper() == "BT" else self._BTLE
        self._write(f"CONFigure:{prefix}:MEAS:WHITening {'ON' if enabled else 'OFF'}")

    # ------------------------------------------------------------------ #
    #  Classic — TX power measurement                                     #
    # ------------------------------------------------------------------ #

    def measure_tx_power(self, timeout: float = 15.0) -> BTRFResult:
        """Trigger and return TX power, frequency error, and modulation index."""
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
            modulation_index=float(parts[3]) if len(parts) > 3 else 0.0,
        )

    def fetch_tx_power(self) -> BTRFResult:
        """Return the last Classic TX power result without re-triggering."""
        raw = self._query(f"FETCh:{self._BT}:MEAS:POWer:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTRFResult(
            status=parts[0],
            power_dbm=float(parts[1]),
            freq_error_khz=float(parts[2]),
            modulation_index=float(parts[3]) if len(parts) > 3 else 0.0,
        )

    # ------------------------------------------------------------------ #
    #  Classic — frequency deviation / modulation                        #
    # ------------------------------------------------------------------ #

    def measure_modulation(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return frequency deviation and modulation index for Classic BR.

        Returns
        -------
        dict
          status              : 'RDY' on success
          max_freq_dev_khz    : peak frequency deviation (kHz)
          avg_freq_dev_khz    : average frequency deviation (kHz)
          modulation_index    : modulation index (dimensionless)
        """
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
    #  Classic — ICFT (Initial Carrier Frequency Tolerance)              #
    # ------------------------------------------------------------------ #

    def measure_icft(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return Initial Carrier Frequency Tolerance (ICFT).

        ICFT measures the carrier frequency offset at TX burst start-up.
        Mandatory for BR/EDR conformance testing (typically ±75 kHz / ±75 ppm).

        Returns
        -------
        dict
          status    : 'RDY' on success
          icft_ppm  : carrier frequency tolerance in ppm
          pass_fail : 'PASS' or 'FAIL'
        """
        self._write(f"INITiate:{self._BT}:MEAS:ICFT")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:ICFT:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:ICFT:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "icft_ppm": float(parts[1]),
            "pass_fail": parts[2],
        }

    # ------------------------------------------------------------------ #
    #  Classic — DEVM (Differential EVM for EDR)                        #
    # ------------------------------------------------------------------ #

    def measure_devm(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return Differential EVM (DEVM) for EDR packets.

        DEVM is mandatory for 2 Mbps (π/4-DQPSK) and 3 Mbps (8-DPSK) EDR
        conformance testing. Requires an EDR packet type (2DH1, 3DH1, etc.)
        to be selected via set_packet_type() first.

        Typical limit: ≤ 0.3 for DQPSK, ≤ 0.2 for 8DPSK (normalised).

        Returns
        -------
        dict
          status      : 'RDY' on success
          devm_db     : differential EVM in dB
          evm_rms_db  : RMS EVM in dB
          evm_peak_db : peak EVM in dB
        """
        self._write(f"INITiate:{self._BT}:MEAS:DEVM")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:DEVM:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:DEVM:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "devm_db": float(parts[1]),
            "evm_rms_db": float(parts[2]),
            "evm_peak_db": float(parts[3]),
        }

    # ------------------------------------------------------------------ #
    #  Classic — carrier frequency drift                                  #
    # ------------------------------------------------------------------ #

    def measure_frequency_drift(
        self,
        duration_s: float = 1.0,
        timeout: float = 30.0,
    ) -> dict:
        """
        Trigger and return long-term carrier frequency drift for Classic BT.

        Measures frequency stability over a sustained TX burst of duration_s seconds.
        Used for Class 1/2/3 PA stability testing.

        Returns
        -------
        dict
          status    : 'RDY' on success
          drift_ppm : peak frequency drift over the measurement window (ppm)
        """
        self._write(f"CONFigure:{self._BT}:MEAS:FREQuency:DRIFt:TIME {duration_s}")
        self._write(f"INITiate:{self._BT}:MEAS:FREQuency:DRIFt")
        self._poll_state(
            f"FETCh:{self._BT}:MEAS:FREQuency:DRIFt:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BT}:MEAS:FREQuency:DRIFt:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "drift_ppm": float(parts[1]),
        }

    # ------------------------------------------------------------------ #
    #  Classic — BER                                                      #
    # ------------------------------------------------------------------ #

    def configure_ber(self, packet_count: int = 1000) -> None:
        """Configure Classic BT BER test (number of packets)."""
        self._write(f"CONFigure:{self._BT}:MEAS:BER:PACKets {packet_count}")

    def measure_ber(self, timeout: float = 30.0) -> BTBERResult:
        """Trigger and return Bit Error Rate for Bluetooth Classic."""
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

    # ================================================================== #
    #  Bluetooth LE                                                        #
    # ================================================================== #

    # ------------------------------------------------------------------ #
    #  LE — configuration                                                 #
    # ------------------------------------------------------------------ #

    def le_set_phy(self, phy: str = "LE1M") -> None:
        """
        Set the Bluetooth LE PHY.

        Values
        ------
          LE1M        : 1 Mbps (BLE 4.0+)
          LE2M        : 2 Mbps (BLE 5.0+)
          LECoded_S2  : Coded PHY, coding scheme S=2 (500 kbps, BLE 5.0+)
          LECoded_S8  : Coded PHY, coding scheme S=8 (125 kbps, BLE 5.0+)

        Note: LECoded_S8 provides the longest range at the cost of throughput.
        Verify exact string format with your CMW firmware version if SCPI errors occur.
        """
        self._write(f"CONFigure:{self._BTLE}:MEAS:PHY {phy}")

    def le_set_channel(self, channel: int) -> None:
        """
        Set the BLE channel index (0–39).

        Data channels: 0–36
        Advertising channels: 37 (2402 MHz), 38 (2426 MHz), 39 (2480 MHz)
        """
        self._write(f"CONFigure:{self._BTLE}:MEAS:CHANnel {channel}")

    def le_set_expected_power(self, dbm: float) -> None:
        """
        Set the expected DUT TX power for Bluetooth LE (dBm).

        Use this for LE instead of set_expected_power() which is Classic-only.
        """
        self._write(f"CONFigure:{self._BTLE}:MEAS:EXPower {dbm}")

    def le_configure_cte(self, cte_type: str = "AOA", length_us: int = 16) -> None:
        """
        Configure Constant Tone Extension (CTE) for direction finding (BLE 5.1+).

        CTE is used for Angle of Arrival (AoA) and Angle of Departure (AoD)
        indoor positioning measurements.

        Parameters
        ----------
        cte_type  : AOA | AOD | CONnectionless
        length_us : CTE length in microseconds — 8, 16, 20, or 32
        """
        self._write(f"CONFigure:{self._BTLE}:MEAS:CTE:TYPE {cte_type}")
        self._write(f"CONFigure:{self._BTLE}:MEAS:CTE:LENgth {length_us}")

    # ------------------------------------------------------------------ #
    #  LE — TX power measurement                                          #
    # ------------------------------------------------------------------ #

    def le_measure_tx_power(self, timeout: float = 15.0) -> BTRFResult:
        """
        Trigger and return BLE TX power, frequency error, and modulation index.

        Note: modulation_index is not meaningful for LE 2M or LE Coded PHYs
        and will be 0.0 if the CMW does not return that field.
        """
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
            modulation_index=float(parts[3]) if len(parts) > 3 else 0.0,
        )

    # ------------------------------------------------------------------ #
    #  LE — RSSI                                                          #
    # ------------------------------------------------------------------ #

    def le_measure_rssi(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return BLE RSSI (Received Signal Strength Indicator).

        Essential for link budget analysis and range estimation.

        Returns
        -------
        dict
          status   : 'RDY' on success
          rssi_dbm : measured RSSI in dBm
        """
        self._write(f"INITiate:{self._BTLE}:MEAS:RSSI")
        self._poll_state(
            f"FETCh:{self._BTLE}:MEAS:RSSI:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BTLE}:MEAS:RSSI:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "rssi_dbm": float(parts[1]),
        }

    # ------------------------------------------------------------------ #
    #  LE — frequency offset                                              #
    # ------------------------------------------------------------------ #

    def le_measure_frequency_offset(self, timeout: float = 15.0) -> dict:
        """
        Trigger and return BLE carrier frequency offset.

        BLE 5.0+ requires frequency accuracy within ±20 ppm.
        This measurement verifies the DUT's crystal / PLL accuracy.

        Returns
        -------
        dict
          status           : 'RDY' on success
          freq_offset_khz  : frequency offset in kHz
          freq_offset_ppm  : frequency offset in ppm
        """
        self._write(f"INITiate:{self._BTLE}:MEAS:FREQuency:OFFset")
        self._poll_state(
            f"FETCh:{self._BTLE}:MEAS:FREQuency:OFFset:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BTLE}:MEAS:FREQuency:OFFset:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return {
            "status": parts[0],
            "freq_offset_khz": float(parts[1]),
            "freq_offset_ppm": float(parts[2]),
        }

    # ------------------------------------------------------------------ #
    #  LE — BER                                                           #
    # ------------------------------------------------------------------ #

    def le_measure_ber(self, packet_count: int = 1000, timeout: float = 30.0) -> BTBERResult:
        """Trigger and return BLE Bit Error Rate."""
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

    # ------------------------------------------------------------------ #
    #  LE — PER (Packet Error Rate — conformance metric)                 #
    # ------------------------------------------------------------------ #

    def le_measure_per(self, packet_count: int = 1000, timeout: float = 30.0) -> BTLEPERResult:
        """
        Trigger and return BLE Packet Error Rate (PER).

        PER is the primary RX sensitivity metric in BLE conformance testing
        (Bluetooth Core Spec Vol 6, Part B, Section 4.7 — typically pass < 30.8%).

        Returns
        -------
        BTLEPERResult
          per_pct       : packet error rate in percent
          packet_count  : total packets transmitted
          error_count   : packets received with errors or lost
        """
        self._write(f"CONFigure:{self._BTLE}:MEAS:PER:PACKets {packet_count}")
        self._write(f"INITiate:{self._BTLE}:MEAS:PER")
        self._poll_state(
            f"FETCh:{self._BTLE}:MEAS:PER:STATus?",
            target_states=("RDY",),
            error_states=("ERR",),
            timeout=timeout,
        )
        raw = self._query(f"FETCh:{self._BTLE}:MEAS:PER:ALL?")
        parts = [p.strip() for p in raw.split(",")]
        return BTLEPERResult(
            status=parts[0],
            per_pct=float(parts[1]),
            packet_count=int(parts[2]),
            error_count=int(parts[3]),
        )
