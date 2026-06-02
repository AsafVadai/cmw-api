"""CMW system & common IEEE-488.2 commands."""

from .base import BaseMixin


class SystemModule(BaseMixin):

    # ------------------------------------------------------------------ #
    #  IEEE-488.2 / Common Commands                                        #
    # ------------------------------------------------------------------ #

    def identify(self) -> str:
        """*IDN? — returns manufacturer, model, serial, firmware string."""
        return self._query("*IDN?")

    def reset(self) -> None:
        """*RST — reset instrument to factory defaults."""
        self._write("*RST")

    def clear_status(self) -> None:
        """*CLS — clear status registers and error queue."""
        self._write("*CLS")

    def wait_for_operation_complete(self, timeout: float = 60.0) -> None:
        """Block until all pending operations finish."""
        self._opc_wait(timeout)

    def get_event_status(self) -> int:
        """*ESR? — read and clear Standard Event Status Register."""
        return self._query_int("*ESR?")

    def get_status_byte(self) -> int:
        """*STB? — read Status Byte Register."""
        return self._query_int("*STB?")

    def set_service_request_enable(self, mask: int) -> None:
        """*SRE <mask> — enable SRQ conditions."""
        self._write(f"*SRE {mask}")

    def set_event_status_enable(self, mask: int) -> None:
        """*ESE <mask> — enable standard event status bits."""
        self._write(f"*ESE {mask}")

    def self_test(self) -> str:
        """*TST? — run internal self-test; returns result code."""
        return self._query("*TST?")

    # ------------------------------------------------------------------ #
    #  SYSTem subsystem                                                    #
    # ------------------------------------------------------------------ #

    def get_error(self) -> str:
        """SYSTem:ERRor[:NEXT]? — read oldest error from queue."""
        return self._query("SYSTem:ERRor:NEXT?")

    def get_all_errors(self) -> list[str]:
        """Drain the error queue and return all messages."""
        errors = []
        while True:
            err = self._query("SYSTem:ERRor:NEXT?")
            if err.startswith("0,") or err == '+0,"No error"':
                break
            errors.append(err)
        return errors

    def get_error_count(self) -> int:
        """SYSTem:ERRor:COUNt? — number of errors in queue."""
        return self._query_int("SYSTem:ERRor:COUNt?")

    def get_version(self) -> str:
        """SYSTem:VERSion? — SCPI version."""
        return self._query("SYSTem:VERSion?")

    def set_date(self, year: int, month: int, day: int) -> None:
        self._write(f"SYSTem:DATE {year},{month},{day}")

    def get_date(self) -> str:
        return self._query("SYSTem:DATE?")

    def set_time(self, hour: int, minute: int, second: int) -> None:
        self._write(f"SYSTem:TIME {hour},{minute},{second}")

    def get_time(self) -> str:
        return self._query("SYSTem:TIME?")

    def preset(self) -> None:
        """SYSTem:PRESet — identical to *RST for CMW."""
        self._write("SYSTem:PRESet")

    def get_options(self) -> str:
        """SYSTem:OPTions? — list installed software options."""
        return self._query("SYSTem:OPTions?")

    def set_display_update(self, enabled: bool) -> None:
        """SYSTem:DISPlay:UPDate — enable/disable front-panel update."""
        self._write(f"SYSTem:DISPlay:UPDate {'ON' if enabled else 'OFF'}")

    def get_display_update(self) -> bool:
        return self._query("SYSTem:DISPlay:UPDate?") == "1"

    # ------------------------------------------------------------------ #
    #  MMEMory (file system)                                               #
    # ------------------------------------------------------------------ #

    def mem_catalog(self, path: str = "") -> str:
        """MMEMory:CATalog? — list files in directory."""
        cmd = f'MMEMory:CATalog? "{path}"' if path else "MMEMory:CATalog?"
        return self._query(cmd)

    def mem_store(self, filename: str) -> None:
        """MMEMory:STORe:STATe — save instrument state to file."""
        self._write(f'MMEMory:STORe:STATe "{filename}"')

    def mem_load(self, filename: str) -> None:
        """MMEMory:LOAD:STATe — load instrument state from file."""
        self._write(f'MMEMory:LOAD:STATe "{filename}"')

    def mem_delete(self, filename: str) -> None:
        self._write(f'MMEMory:DELete "{filename}"')

    def mem_mkdir(self, path: str) -> None:
        self._write(f'MMEMory:MDIRectory "{path}"')
