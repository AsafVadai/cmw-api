"""
Rohde & Schwarz CMW Series — top-level API class.

Supported transports
--------------------
  TCP/IP (raw socket, port 5025):
      cmw = CMW.via_tcp("192.168.1.100")

  VISA (GPIB / USB-TMC / VXI-11 / HiSLIP):
      cmw = CMW.via_visa("TCPIP::192.168.1.100::INSTR")
      cmw = CMW.via_visa("TCPIP::192.168.1.100::hislip0::INSTR")
      cmw = CMW.via_visa("USB0::0x0AAD::0x0197::100001::INSTR")
      cmw = CMW.via_visa("GPIB0::20::INSTR")
"""

from __future__ import annotations

from .transport import TcpTransport, VisaTransport
from .system import SystemModule
from .routing import RoutingModule
from .gprf import GPRFModule
from .lte import LTEModule
from .nr5g import NR5GModule
from .wcdma import WCDMAModule
from .bluetooth import BluetoothModule
from .wlan import WLANModule
from .exceptions import CMWError


class CMW(
    SystemModule,
    RoutingModule,
    GPRFModule,
    LTEModule,
    NR5GModule,
    WCDMAModule,
    BluetoothModule,
    WLANModule,
):
    """
    Unified API for the Rohde & Schwarz CMW wideband radio communication tester.

    All functional domains are exposed as methods on a single object:
      - System / IEEE-488.2 commands  (SystemModule)
      - RF routing                    (RoutingModule)
      - General-purpose RF            (GPRFModule)
      - LTE signaling                 (LTEModule)
      - 5G NR signaling               (NR5GModule)
      - WCDMA / UMTS signaling        (WCDMAModule)
      - Bluetooth Classic + LE        (BluetoothModule)
      - WLAN 802.11                   (WLANModule)

    Example — LTE throughput test
    -----------------------------
        from cmw_api import CMW
        from cmw_api.lte import LTECellConfig

        with CMW.via_tcp("192.168.0.1") as cmw:
            cmw.reset()
            cmw.lte_set_rx_connector("RF1C")
            cfg = LTECellConfig(band=3, dl_channel=1300, bandwidth_mhz=20)
            cmw.configure_cell(cfg)       # LTEModule.configure_cell
            cmw.cell_on()
            cmw.expect_attach(timeout=60)
            cmw.connect()
            result = cmw.measure_throughput(timeout=30)
            print(result)
    """

    def __init__(self, transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ #
    #  Factory constructors                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def via_tcp(
        cls,
        host: str,
        port: int = TcpTransport.PORT,
        timeout: float = 10.0,
    ) -> "CMW":
        """Connect via raw TCP socket (no VISA required)."""
        return cls(TcpTransport(host, port, timeout))

    @classmethod
    def via_visa(
        cls,
        resource_string: str,
        timeout_ms: int = 10_000,
    ) -> "CMW":
        """Connect via PyVISA (GPIB, USB-TMC, VXI-11, HiSLIP)."""
        return cls(VisaTransport(resource_string, timeout_ms))

    # ------------------------------------------------------------------ #
    #  Context manager                                                     #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "CMW":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        """Release the transport connection."""
        try:
            self._transport.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Convenience helpers                                                 #
    # ------------------------------------------------------------------ #

    def initialize(self, reset: bool = True, check_errors: bool = True) -> str:
        """
        Standard initialization sequence.
        Returns the *IDN? string.
        """
        if reset:
            self.reset()
            self.clear_status()
            self.wait_for_operation_complete(timeout=30)
        idn = self.identify()
        if check_errors:
            errors = self.get_all_errors()
            if errors:
                raise CMWError(f"Errors after init: {errors}")
        return idn

    def safe_preset(self) -> None:
        """Reset, clear errors, and wait for idle — useful between test cases."""
        self.reset()
        self.clear_status()
        self.wait_for_operation_complete(timeout=30)
        self.get_all_errors()  # drain queue silently
