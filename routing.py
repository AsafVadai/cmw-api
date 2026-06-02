"""RF connector routing and frontend configuration."""

from .base import BaseMixin


class RoutingModule(BaseMixin):
    """
    CMW RF connectors (typical CMW500 layout):
      RF1 COM  — TX/RX combo port
      RF2 COM  — second combo port
      RF3 OUT  — output only
      RF4 IN   — input only
    """

    # ------------------------------------------------------------------ #
    #  ROUTe:GPRx / common routing                                        #
    # ------------------------------------------------------------------ #

    def connect_rf_output(self, connector: str = "RF1C") -> None:
        """ROUTe:... enable RF output on the given connector."""
        self._write(f"ROUTe:GPRF:MEAS:ROUT {connector}")

    def set_scenario_signaling(self, tech: str = "LTE") -> None:
        """
        Select the test scenario (signaling application).
        tech: LTE | NR5G | WCDMA | GSM | CDMA2K | BT | WLAN
        """
        self._write(f"ROUTe:{tech}:SIGN:SCENario:SCELl")

    # ------------------------------------------------------------------ #
    #  General-purpose RF path (non-signaling)                            #
    # ------------------------------------------------------------------ #

    def gprf_set_rx_connector(self, connector: str) -> None:
        """ROUTe:GPRF:MEAS:RFConnector — set RX input connector."""
        self._write(f"ROUTe:GPRF:MEAS:RFConnector {connector}")

    def gprf_set_tx_connector(self, connector: str) -> None:
        """ROUTe:GPRF:GEN:RFConnector — set TX output connector."""
        self._write(f"ROUTe:GPRF:GEN:RFConnector {connector}")

    def gprf_set_rx_path(self, path: str = "RX1") -> None:
        self._write(f"ROUTe:GPRF:MEAS:RXPath {path}")

    def gprf_set_tx_path(self, path: str = "TX1") -> None:
        self._write(f"ROUTe:GPRF:GEN:TXPath {path}")

    # ------------------------------------------------------------------ #
    #  LTE routing helpers                                                 #
    # ------------------------------------------------------------------ #

    def lte_set_rx_connector(self, connector: str) -> None:
        self._write(f"ROUTe:LTE:SIGN:RFConnector {connector}")

    def lte_set_scenario(self, scenario: str = "SCELl") -> None:
        """SCELl=single cell, SCC=secondary component carrier, etc."""
        self._write(f"ROUTe:LTE:SIGN:SCENario:{scenario}")

    # ------------------------------------------------------------------ #
    #  5G NR routing helpers                                               #
    # ------------------------------------------------------------------ #

    def nr5g_set_rx_connector(self, connector: str) -> None:
        self._write(f"ROUTe:NR5G:SIGN:RFConnector {connector}")

    def nr5g_set_scenario(self, scenario: str = "SCELl") -> None:
        self._write(f"ROUTe:NR5G:SIGN:SCENario:{scenario}")

    # ------------------------------------------------------------------ #
    #  Attenuation / external loss compensation                           #
    # ------------------------------------------------------------------ #

    def set_external_attenuation_rx(self, db: float, connector: str = "RF1C") -> None:
        """Compensate for cable/attenuator loss on RX path."""
        self._write(f"SENSe:CORRection:LOSS:INPut:{connector} {db}")

    def set_external_attenuation_tx(self, db: float, connector: str = "RF1C") -> None:
        """Compensate for cable/attenuator loss on TX path."""
        self._write(f"SENSe:CORRection:LOSS:OUTPut:{connector} {db}")
