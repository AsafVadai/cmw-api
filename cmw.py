"""
Rohde & Schwarz CMW Series — top-level API class.

Each technology is exposed as a namespaced sub-module on the CMW object, so
methods that share a name across technologies never collide:

    cmw.system   System / IEEE-488.2 / SYSTem / MMEMory
    cmw.route    RF connector routing and loss compensation
    cmw.gprf     General-purpose RF (non-signaling generator + power meter)
    cmw.lte      LTE signaling
    cmw.nr5g     5G NR signaling (SA / NSA)
    cmw.wcdma    WCDMA / UMTS signaling
    cmw.bt       Bluetooth Classic (BR/EDR) + LE
    cmw.wlan     WLAN 802.11 a/b/g/n/ac/ax/be

The most common IEEE-488.2 / lifecycle commands (identify, reset, initialize,
self_check, ...) are also delegated to the top level for convenience.

Supported transports
--------------------
  TCP/IP (raw socket, port 5025) — no VISA driver required:
      cmw = CMW.via_tcp("192.168.1.100")

  VISA (GPIB / USB-TMC / VXI-11 / HiSLIP) — needs the [visa] extra:
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


class CMW:
    """
    Unified API for the Rohde & Schwarz CMW wideband radio communication tester.

    Example — LTE throughput test
    -----------------------------
        from cmw_api import CMW
        from cmw_api.lte import LTECellConfig

        with CMW.via_tcp("192.168.0.1") as cmw:
            cmw.initialize()
            cmw.route.lte_set_rx_connector("RF1C")
            cmw.lte.configure_cell(LTECellConfig(band=3, dl_channel=1300, bandwidth_mhz=20))
            cmw.lte.cell_on()
            cmw.lte.expect_attach(timeout=60)
            cmw.lte.connect()
            print(cmw.lte.measure_throughput(timeout=30))

    Example — WLAN EVM (no collision with LTE/BT measure_* names)
    ------------------------------------------------------------
        with CMW.via_tcp("192.168.0.1") as cmw:
            cmw.initialize()
            cmw.wlan.set_standard("AX")
            cmw.wlan.set_channel(36)
            print(cmw.wlan.measure_evm())
    """

    def __init__(self, transport) -> None:
        self._transport = transport

        # Namespaced sub-modules — each owns the shared transport.
        self.system = SystemModule(transport)
        self.route = RoutingModule(transport)
        self.gprf = GPRFModule(transport)
        self.lte = LTEModule(transport)
        self.nr5g = NR5GModule(transport)
        self.wcdma = WCDMAModule(transport)
        self.bt = BluetoothModule(transport)
        self.wlan = WLANModule(transport)

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
    #  Top-level convenience delegates (common IEEE-488.2 / lifecycle)     #
    # ------------------------------------------------------------------ #

    def identify(self) -> str:
        """*IDN? — manufacturer, model, serial, firmware."""
        return self.system.identify()

    def reset(self) -> None:
        """*RST — reset to factory defaults."""
        self.system.reset()

    def clear_status(self) -> None:
        """*CLS — clear status registers and error queue."""
        self.system.clear_status()

    def wait_for_operation_complete(self, timeout: float = 60.0) -> None:
        """Block until all pending operations finish (*OPC?)."""
        self.system.wait_for_operation_complete(timeout)

    def get_options(self) -> str:
        """SYSTem:OPTions? — installed software options."""
        return self.system.get_options()

    def get_error(self) -> str:
        """SYSTem:ERRor:NEXT? — oldest error in the queue."""
        return self.system.get_error()

    def get_all_errors(self) -> list[str]:
        """Drain and return the whole SCPI error queue."""
        return self.system.get_all_errors()

    def preset(self) -> None:
        """SYSTem:PRESet."""
        self.system.preset()

    # ------------------------------------------------------------------ #
    #  Convenience helpers                                                 #
    # ------------------------------------------------------------------ #

    def initialize(self, reset: bool = True, check_errors: bool = True) -> str:
        """
        Standard initialization sequence. Returns the *IDN? string.
        """
        if reset:
            self.system.reset()
            self.system.clear_status()
            self.system.wait_for_operation_complete(timeout=30)
        idn = self.system.identify()
        if check_errors:
            errors = self.system.get_all_errors()
            if errors:
                raise CMWError(f"Errors after init: {errors}")
        return idn

    def safe_preset(self) -> None:
        """Reset, clear errors, and wait for idle — useful between test cases."""
        self.system.reset()
        self.system.clear_status()
        self.system.wait_for_operation_complete(timeout=30)
        self.system.get_all_errors()  # drain queue silently

    def self_check(self) -> dict:
        """
        Verify the instrument is reachable and responsive.

        Performs a lightweight round-trip without resetting the instrument:
          - reads *IDN? to confirm communication
          - runs *OPC? to confirm the command parser is alive
          - drains and reports the SCPI error queue

        Returns a dict you can log or assert on::

            {'idn': '...', 'opc': True, 'errors': [], 'ok': True}

        Raises CMWError if the instrument cannot be reached at all.
        """
        result = {"idn": None, "opc": False, "errors": [], "ok": False}
        try:
            result["idn"] = self.system.identify()
            result["opc"] = self._transport.query("*OPC?").strip() == "1"
            result["errors"] = self.system.get_all_errors()
        except CMWError:
            raise
        except Exception as exc:
            raise CMWError(f"Self-check failed: {exc}") from exc
        result["ok"] = bool(result["idn"]) and result["opc"] and not result["errors"]
        return result
