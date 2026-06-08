# CMW API — Python SCPI Control Library

A Python library for remote control of the **Rohde & Schwarz CMW** wideband radio communication tester family (CMW100, CMW270, CMW290, CMW500) via SCPI commands over TCP/IP or VISA.

---

## Features

| Domain | Module | Key capabilities |
|---|---|---|
| System / IEEE-488.2 | `SystemModule` | Reset, identify, error queue, file system |
| RF Routing | `RoutingModule` | Connector selection, path, cable loss compensation |
| General-Purpose RF | `GPRFModule` | CW generator, wideband power meter, spectrum |
| LTE Signaling | `LTEModule` | Cell config, attach, data connection, RSRP/RSRQ/SINR, throughput, BLER, EVM |
| 5G NR Signaling | `NR5GModule` | SA & NSA/EN-DC, NR-ARFCN, SS-RSRP/SINR, throughput, BLER, EVM |
| WCDMA / UMTS | `WCDMAModule` | Cell config, attach, RSCP/Ec/No, UL power |
| Bluetooth | `BluetoothModule` | Classic BR/EDR: TX power, ICFT, DEVM, frequency drift, BER, modulation; BLE: TX power, RSSI, PER, BER, frequency offset, CTE/AoA/AoD |
| WLAN | `WLANModule` | 802.11 a/b/g/n/ac/ax/be (Wi-Fi 7) — EVM, TX power, ACP/ACLR, OBW, RSSI, spectral mask, PER, MLO per-link power, EHT MCS 0–15, preamble puncturing, TWT, OFDMA, HE PPDU |

---

## Requirements

- Python 3.10 or later
- CMW instrument accessible over a LAN (TCP port 5025) or via a VISA interface

```
pip install pyvisa pyvisa-py
```

`pyvisa` and `pyvisa-py` are only required when connecting via VISA (GPIB, USB‑TMC, VXI‑11, HiSLIP). The raw TCP transport has no external dependencies.

---

## Quick Start

### 1 — Connect and identify

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    print(cmw.initialize())
# Rohde&Schwarz,CMW500,1234567,3.7.10
```

### 2 — Non-signaling RF power measurement

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.gprf_set_rx_connector("RF1C")
    cmw.meas_set_frequency(1_800_000_000)   # 1800 MHz
    cmw.meas_set_filter_bandwidth(20_000_000)
    result = cmw.meas_read_power()
    print(f"{result.average:.2f} dBm")
```

### 3 — LTE attach and throughput

```python
from cmw_api import CMW
from cmw_api.lte import LTECellConfig

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.lte_set_rx_connector("RF1C")
    cmw.configure_cell(LTECellConfig(band=3, dl_channel=1300, bandwidth_mhz=20))
    cmw.cell_on()
    cmw.expect_attach(timeout=60)
    cmw.connect()
    result = cmw.measure_throughput(timeout=30)
    print(f"DL {result.dl_throughput_mbps:.1f} Mbps / UL {result.ul_throughput_mbps:.1f} Mbps")
```

### 4 — 5G NR SA attach and throughput

```python
from cmw_api import CMW
from cmw_api.nr5g import NR5GCellConfig

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.nr5g_set_rx_connector("RF1C")
    cmw.configure_cell(NR5GCellConfig(band=78, dl_arfcn=632628, bandwidth_mhz=100))
    cmw.cell_on()
    cmw.expect_attach(timeout=90)
    cmw.connect()
    print(cmw.measure_throughput())
```

---

## Connection Options

| Method | When to use | Example resource string |
|---|---|---|
| `CMW.via_tcp(host)` | LAN, no VISA driver needed | `"192.168.0.1"` |
| `CMW.via_visa(resource)` | GPIB, USB-TMC, VXI-11, HiSLIP | `"TCPIP::192.168.0.1::hislip0::INSTR"` |

---

## File Layout

```
cmw_api/
├── cmw.py          # CMW — top-level class
├── transport.py    # TcpTransport / VisaTransport
├── base.py         # BaseMixin (shared helpers)
├── exceptions.py   # CMWError, CMWTimeoutError, CMWMeasurementError
├── system.py       # SystemModule
├── routing.py      # RoutingModule
├── gprf.py         # GPRFModule
├── lte.py          # LTEModule
├── nr5g.py         # NR5GModule
├── wcdma.py        # WCDMAModule
├── bluetooth.py    # BluetoothModule
├── wlan.py         # WLANModule
├── examples.py     # Runnable usage examples
└── requirements.txt
```

---

## Further Reading

See [USER_GUIDE.md](USER_GUIDE.md) for:
- Detailed walkthrough of every module
- Complete API reference with parameter tables
- Error handling patterns
- Troubleshooting tips
