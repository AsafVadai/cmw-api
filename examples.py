"""
Usage examples for the CMW API.
Run any example by calling its function directly.
"""

from cmw_api import CMW
from cmw_api.lte import LTECellConfig
from cmw_api.nr5g import NR5GCellConfig
from cmw_api.wcdma import WCDMACellConfig


# --------------------------------------------------------------------------- #
#  Example 1 — Identify and check options                                      #
# --------------------------------------------------------------------------- #

def example_identify(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        idn = cmw.initialize(reset=True)
        print("IDN:", idn)
        print("Options:", cmw.get_options())
        print("Date:", cmw.get_date())


# --------------------------------------------------------------------------- #
#  Example 2 — Non-signaling RF power measurement                              #
# --------------------------------------------------------------------------- #

def example_gprf_power(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        cmw.initialize()

        # Set RF connector and path
        cmw.gprf_set_rx_connector("RF1C")
        cmw.set_external_attenuation_rx(0.5)     # 0.5 dB cable loss

        # Configure measurement
        cmw.meas_set_frequency(1_800_000_000)    # 1800 MHz
        cmw.meas_set_filter_bandwidth(20_000_000)
        cmw.meas_set_count(10)

        result = cmw.meas_read_power(timeout=10)
        print(f"Power: {result.average:.2f} dBm  (min={result.minimum:.2f}, max={result.maximum:.2f})")


# --------------------------------------------------------------------------- #
#  Example 3 — LTE signaling: attach + throughput test                        #
# --------------------------------------------------------------------------- #

def example_lte_throughput(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        cmw.initialize()
        cmw.lte_set_rx_connector("RF1C")

        cfg = LTECellConfig(
            band=3,
            dl_channel=1300,
            bandwidth_mhz=20,
            dl_power_dbm=-65.0,
            mcc="234",
            mnc="30",
        )
        cmw.configure_cell(cfg)   # LTEModule
        cmw.cell_on()

        print("Waiting for UE to attach…")
        status = cmw.expect_attach(timeout=60)
        print("Status:", status)

        cmw.configure_throughput(direction="DLULink", duration_s=10.0)
        result = cmw.measure_throughput(timeout=30)
        print(f"DL: {result.dl_throughput_mbps:.1f} Mbps   UL: {result.ul_throughput_mbps:.1f} Mbps")
        print(f"DL BLER: {result.dl_bler_pct:.2f}%   UL BLER: {result.ul_bler_pct:.2f}%")

        rx = cmw.measure_rx_quality()
        print(f"RSRP={rx.rsrp_dbm:.1f} dBm  RSRQ={rx.rsrq_db:.1f} dB  SINR={rx.sinr_db:.1f} dB")

        cmw.disconnect()
        cmw.cell_off()


# --------------------------------------------------------------------------- #
#  Example 4 — 5G NR SA attach + throughput                                   #
# --------------------------------------------------------------------------- #

def example_nr5g_throughput(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        cmw.initialize()
        cmw.nr5g_set_rx_connector("RF1C")

        cfg = NR5GCellConfig(
            band=78,
            dl_arfcn=632628,
            scs_khz=30,
            bandwidth_mhz=100,
            dl_power_dbm=-65.0,
            mode="SA",
        )
        cmw.configure_cell(cfg)   # NR5GModule
        cmw.cell_on()

        print("Waiting for 5G NR attach…")
        cmw.expect_attach(timeout=90)

        cmw.configure_throughput(direction="DL", duration_s=10.0)
        result = cmw.measure_throughput(timeout=30)
        print(f"DL: {result.dl_throughput_mbps:.1f} Mbps  DL BLER: {result.dl_bler_pct:.2f}%")

        rx = cmw.measure_rx_quality()
        print(f"SS-RSRP={rx.ss_rsrp_dbm:.1f}  SS-SINR={rx.ss_sinr_db:.1f} dB")

        cmw.disconnect()
        cmw.cell_off()


# --------------------------------------------------------------------------- #
#  Example 5 — Bluetooth TX power + BER                                       #
# --------------------------------------------------------------------------- #

def example_bluetooth(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        cmw.initialize()
        cmw.gprf_set_rx_connector("RF2C")

        cmw.set_frequency(channel=0)          # BT channel 0 = 2402 MHz
        cmw.set_expected_power(dbm=4.0)
        cmw.set_packet_type("DH1")

        pwr = cmw.measure_tx_power(timeout=10)
        print(f"BT TX Power: {pwr.power_dbm:.2f} dBm  Freq error: {pwr.freq_error_khz:.1f} kHz")

        cmw.configure_ber(packet_count=1000)
        ber = cmw.measure_ber(timeout=30)
        print(f"BT BER: {ber.ber_pct:.4f}%  ({ber.error_count}/{ber.packet_count} packets)")


# --------------------------------------------------------------------------- #
#  Example 6 — WLAN EVM                                                       #
# --------------------------------------------------------------------------- #

def example_wlan_evm(host: str = "192.168.0.1") -> None:
    with CMW.via_tcp(host) as cmw:
        cmw.initialize()

        cmw.set_standard("AC")
        cmw.set_channel(36)
        cmw.set_bandwidth(80)
        cmw.set_mcs(9)
        cmw.set_expected_power(dbm=20.0)

        result = cmw.measure_evm(timeout=15)
        print(f"EVM RMS: {result.evm_rms_db:.2f} dB  Peak: {result.evm_peak_db:.2f} dB")
        print(f"Freq error: {result.freq_error_khz:.3f} kHz")


# --------------------------------------------------------------------------- #
#  Example 7 — VISA connection (NI-VISA or pyvisa-py)                         #
# --------------------------------------------------------------------------- #

def example_visa(resource: str = "TCPIP::192.168.0.1::hislip0::INSTR") -> None:
    with CMW.via_visa(resource, timeout_ms=15_000) as cmw:
        print(cmw.initialize(reset=True))


if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.1"
    example_identify(host)
