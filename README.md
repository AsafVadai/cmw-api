# CMW API — Python SCPI Control Library

A Python library for remote control of the **Rohde & Schwarz CMW** wideband radio communication tester family (CMW100, CMW270, CMW290, CMW500) via SCPI commands over TCP/IP or VISA.

---

## Features

Primary focus: **WLAN (802.11 a/b/g/n/ac/ax/be)** and **Bluetooth LE / Classic**.

| Domain | Module | Key capabilities |
|---|---|---|
| **WLAN** | `WLANModule` | 802.11 a/b/g/n/ac/ax/**be (Wi-Fi 7)** — EVM, TX power, ACP/ACLR, OBW, RSSI, spectral mask & flatness, PER, MLO per-link power, EHT MCS 0–15, preamble puncturing, TWT, OFDMA, HE PPDU |
| **Bluetooth** | `BluetoothModule` | **BLE**: TX power, RSSI, PER, BER, frequency offset, modulation (Δf1/Δf2), CTE/AoA/AoD; **Classic BR/EDR**: TX power, ICFT, DEVM, frequency drift, BER, modulation |
| General-Purpose RF | `GPRFModule` | CW generator, wideband power meter, spectrum |
| RF Routing | `RoutingModule` | Connector selection, path, cable loss compensation |
| System / IEEE-488.2 | `SystemModule` | Reset, identify, error queue, file system |
| LTE Signaling | `LTEModule` | Cell config, attach, data connection, RSRP/RSRQ/SINR, throughput, BLER, EVM |
| 5G NR Signaling | `NR5GModule` | SA & NSA/EN-DC, NR-ARFCN, SS-RSRP/SINR, throughput, BLER, EVM |
| WCDMA / UMTS | `WCDMAModule` | Cell config, attach, RSCP/Ec/No, UL power |

---

## Requirements

- Python 3.10 or later
- CMW instrument accessible over a LAN (TCP port 5025) or via a VISA interface

## Installation

```bash
# Clone and install
git clone https://github.com/AsafVadai/cmw-api.git
cd cmw-api
pip install .

# With VISA support (GPIB / USB-TMC / VXI-11 / HiSLIP)
pip install '.[visa]'
```

The raw TCP transport has **no external dependencies**. `pyvisa`/`pyvisa-py` are only needed for the VISA transport and are pulled in by the `[visa]` extra.

## API namespaces

Each technology is exposed as a sub-module on the `CMW` object, so identically named
methods never collide:

| Namespace | Module | Example |
|---|---|---|
| `cmw.system` | System / IEEE-488.2 / files | `cmw.system.get_options()` |
| `cmw.route` | RF connector routing | `cmw.route.lte_set_rx_connector("RF1C")` |
| `cmw.gprf` | General-purpose RF | `cmw.gprf.meas_read_power()` |
| `cmw.lte` | LTE signaling | `cmw.lte.measure_throughput()` |
| `cmw.nr5g` | 5G NR signaling | `cmw.nr5g.measure_evm()` |
| `cmw.wcdma` | WCDMA / UMTS | `cmw.wcdma.measure_rx_quality()` |
| `cmw.bt` | Bluetooth Classic + LE | `cmw.bt.le_measure_per()` |
| `cmw.wlan` | WLAN 802.11 | `cmw.wlan.measure_evm()` |

Common lifecycle commands are delegated to the top level for convenience:
`cmw.initialize()`, `cmw.reset()`, `cmw.identify()`, `cmw.get_all_errors()`, `cmw.self_check()`.

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
    cmw.route.gprf_set_rx_connector("RF1C")
    cmw.gprf.meas_set_frequency(1_800_000_000)   # 1800 MHz
    cmw.gprf.meas_set_filter_bandwidth(20_000_000)
    result = cmw.gprf.meas_read_power()
    print(f"{result.average:.2f} dBm")
```

### 3 — WLAN: configure and measure EVM / TX power (Wi-Fi 6)

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    # Configure the 802.11 receiver
    cmw.wlan.set_standard("AX")          # A | B | G | N | AC | AX | BE
    cmw.wlan.set_channel(36)             # 5 GHz channel 36
    cmw.wlan.set_bandwidth(80)           # 80 MHz
    cmw.wlan.set_mcs(9)                  # MCS index
    cmw.wlan.set_expected_power(20.0)    # dBm

    # Monitor
    pwr = cmw.wlan.measure_tx_power()
    evm = cmw.wlan.measure_evm()
    print(f"TX power: {pwr.avg_power_dbm:.2f} dBm   EVM RMS: {evm.evm_rms_db:.2f} dB")
```

### 4 — WLAN: Wi-Fi 7 (802.11be) with 320 MHz + MLO

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.wlan.set_standard("BE")
    cmw.wlan.set_bandwidth(320)          # 320 MHz (Wi-Fi 7)
    cmw.wlan.set_eht_mcs(13)             # EHT MCS 0–15

    # Multi-Link Operation: 5 GHz + 6 GHz links
    cmw.wlan.set_mlo_link(0, freq_hz=5_180_000_000, bw_mhz=160)
    cmw.wlan.set_mlo_link(1, freq_hz=6_135_000_000, bw_mhz=320)
    cmw.wlan.set_mlo_link_count(2)

    print(cmw.wlan.measure_tx_power_mlo(link_count=2))   # per-link power
```

### 5 — Bluetooth LE: TX power, modulation, and PER

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.bt.le_set_phy("LE1M")            # LE1M | LE2M | LECoded_S2 | LECoded_S8
    cmw.bt.le_set_channel(0)
    cmw.bt.le_set_expected_power(0.0)    # dBm

    pwr = cmw.bt.le_measure_tx_power()
    mod = cmw.bt.le_measure_modulation()           # Δf1avg / Δf2avg / ratio
    per = cmw.bt.le_measure_per(packet_count=1500) # RX conformance metric
    print(f"LE power: {pwr.power_dbm:.2f} dBm")
    print(f"Δf2/Δf1 ratio: {mod['delta_f2_f1_ratio']:.3f}  (pass ≥ 0.80)")
    print(f"PER: {per.per_pct:.3f}%  ({per.error_count}/{per.packet_count})")
```

### 6 — Bluetooth Classic (BR/EDR): TX power, ICFT, DEVM

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    cmw.bt.set_frequency(channel=0)      # channel 0 = 2402 MHz
    cmw.bt.set_expected_power(4.0)       # dBm

    cmw.bt.set_packet_type("DH1")
    pwr  = cmw.bt.measure_tx_power()
    icft = cmw.bt.measure_icft()         # Initial Carrier Frequency Tolerance

    cmw.bt.set_packet_type("2DH1")       # EDR packet required for DEVM
    devm = cmw.bt.measure_devm()
    print(f"TX power: {pwr.power_dbm:.2f} dBm   ICFT: {icft['icft_ppm']:.1f} ppm")
    print(f"DEVM: {devm['devm_db']:.1f} dB")
```

> Cellular examples (LTE, 5G NR, WCDMA) are in [USER_GUIDE.md](USER_GUIDE.md) and [examples.py](examples.py).

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
