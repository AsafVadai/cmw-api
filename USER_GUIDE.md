# CMW API — User Guide

Complete reference for the `cmw_api` Python library, covering connection setup, every functional module, error handling, and common test patterns.

---

## Table of Contents

1. [Installation](#1-installation)
2. [Connecting to the Instrument](#2-connecting-to-the-instrument)
3. [Initialization Sequence](#3-initialization-sequence)
4. [System Module](#4-system-module)
5. [RF Routing Module](#5-rf-routing-module)
6. [General-Purpose RF (GPRF)](#6-general-purpose-rf-gprf)
7. [LTE Signaling](#7-lte-signaling)
8. [5G NR Signaling](#8-5g-nr-signaling)
9. [WCDMA / UMTS Signaling](#9-wcdma--umts-signaling)
10. [Bluetooth](#10-bluetooth)
11. [WLAN](#11-wlan)
12. [Error Handling](#12-error-handling)
13. [Patterns and Best Practices](#13-patterns-and-best-practices)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Installation

### Prerequisites

- Python 3.10 or later
- CMW instrument reachable on the network (LAN port), or connected via GPIB / USB

### Install dependencies

```bash
pip install pyvisa pyvisa-py
```

`pyvisa` is only required for VISA connections (GPIB, USB-TMC, VXI-11, HiSLIP).
The raw TCP transport (`CMW.via_tcp`) has no external dependencies beyond the Python standard library.

### Verify VISA backend (optional)

```python
import pyvisa
rm = pyvisa.ResourceManager()
print(rm.list_resources())   # should show your instrument
```

---

## 2. Connecting to the Instrument

All connections are made through the `CMW` factory class methods. The recommended pattern is to use it as a context manager so the connection is always closed on exit.

### TCP/IP — raw socket (port 5025)

No VISA driver installation is required. This is the simplest option for LAN-connected instruments.

```python
from cmw_api import CMW

with CMW.via_tcp("192.168.0.1") as cmw:
    ...

# Custom port or timeout
with CMW.via_tcp("192.168.0.1", port=5025, timeout=15.0) as cmw:
    ...
```

### VISA — VXI-11 (legacy LAN)

```python
with CMW.via_visa("TCPIP::192.168.0.1::INSTR") as cmw:
    ...
```

### VISA — HiSLIP (recommended LAN-VISA)

HiSLIP offers better performance and error recovery over LAN compared to VXI-11.

```python
with CMW.via_visa("TCPIP::192.168.0.1::hislip0::INSTR") as cmw:
    ...
```

### VISA — USB-TMC

```python
# VID 0x0AAD = Rohde & Schwarz, PID 0x0197 = CMW500
with CMW.via_visa("USB0::0x0AAD::0x0197::100001::INSTR") as cmw:
    ...
```

### VISA — GPIB

```python
with CMW.via_visa("GPIB0::20::INSTR") as cmw:
    ...
```

### Manual (no context manager)

```python
cmw = CMW.via_tcp("192.168.0.1")
try:
    ...
finally:
    cmw.close()
```

---

## 3. Initialization Sequence

Always call `initialize()` immediately after connecting. It performs a full reset, clears the status/error registers, waits for the instrument to become idle, and returns the `*IDN?` string.

```python
with CMW.via_tcp("192.168.0.1") as cmw:
    idn = cmw.initialize()
    print(idn)
    # Rohde&Schwarz,CMW500,1234567,3.7.10
```

| Parameter | Default | Description |
|---|---|---|
| `reset` | `True` | Send `*RST` + `*CLS` before querying IDN |
| `check_errors` | `True` | Drain error queue and raise `CMWError` if any errors found |

To skip the reset (e.g., continuing a previous test session):

```python
idn = cmw.initialize(reset=False)
```

### Between test cases

`safe_preset()` resets and silently drains the error queue — useful to guarantee a clean state between sequential test cases without raising on stale errors:

```python
cmw.safe_preset()
```

---

## 4. System Module

Provides IEEE-488.2 common commands and the SCPI `SYSTem` subsystem.

### Identification and reset

```python
cmw.identify()          # *IDN?  → "Rohde&Schwarz,CMW500,..."
cmw.reset()             # *RST
cmw.clear_status()      # *CLS
cmw.self_test()         # *TST?  → "0" on pass
cmw.get_options()       # SYSTem:OPTions?
```

### Synchronisation

`wait_for_operation_complete()` blocks until the instrument finishes all pending operations (`*OPC?` returns `1`). Use this after any command that triggers a long background action.

```python
cmw.reset()
cmw.wait_for_operation_complete(timeout=30.0)
```

### Error queue

```python
# Read one error at a time
err = cmw.get_error()            # '+0,"No error"' when empty

# Drain all errors into a list
errors = cmw.get_all_errors()    # [] when empty

# Check count first (fast)
count = cmw.get_error_count()
```

### Status registers

```python
cmw.get_status_byte()                    # *STB?
cmw.get_event_status()                   # *ESR?  (reads and clears)
cmw.set_service_request_enable(0x20)     # *SRE — enable SRQ on MAV
cmw.set_event_status_enable(0xFF)        # *ESE
```

### Date / time

```python
cmw.set_date(2025, 6, 1)
cmw.get_date()                  # "2025,6,1"
cmw.set_time(9, 30, 0)
cmw.get_time()                  # "9,30,0"
```

### Display

```python
cmw.set_display_update(False)   # disable for faster remote operation
cmw.set_display_update(True)    # re-enable
```

### File system (MMEMory)

```python
cmw.mem_catalog()                      # list root directory
cmw.mem_catalog("/var/user/tests")     # list specific path
cmw.mem_store("/var/user/tests/state1.savrcl")   # save instrument state
cmw.mem_load("/var/user/tests/state1.savrcl")    # restore state
cmw.mem_delete("/var/user/tests/old.savrcl")
cmw.mem_mkdir("/var/user/results")
```

---

## 5. RF Routing Module

Configures which physical RF connector is used for each application and compensates for external cable or attenuator losses.

### CMW500 connector layout (typical)

| Connector | Type | Use |
|---|---|---|
| `RF1C` | TX/RX combo | Primary signaling port |
| `RF2C` | TX/RX combo | Secondary / diversity |
| `RF3` | Output only | DL signal generation |
| `RF4` | Input only | UL power measurement |

### GPRF routing

```python
cmw.gprf_set_rx_connector("RF1C")   # receive path for power measurements
cmw.gprf_set_tx_connector("RF1C")   # transmit path for generator
cmw.gprf_set_rx_path("RX1")
cmw.gprf_set_tx_path("TX1")
```

### LTE routing

```python
cmw.lte_set_rx_connector("RF1C")
cmw.lte_set_scenario("SCELl")   # SCELl = single cell (default)
```

### 5G NR routing

```python
cmw.nr5g_set_rx_connector("RF1C")
cmw.nr5g_set_scenario("SCELl")
```

### External loss compensation

Entering the cable or attenuator loss (in dB) corrects all power readings and generator levels automatically.

```python
cmw.set_external_attenuation_rx(0.5, connector="RF1C")   # 0.5 dB cable loss on RX
cmw.set_external_attenuation_tx(0.5, connector="RF1C")   # 0.5 dB cable loss on TX
```

---

## 6. General-Purpose RF (GPRF)

The GPRF application provides a technology-independent CW/modulated signal generator and a wideband power meter. Use it for non-signaling calibration, quick power checks, or spectrum surveys.

### Signal Generator

```python
cmw.gen_set_frequency(2_450_000_000)   # 2450 MHz
cmw.gen_set_level(-10.0)               # -10 dBm
cmw.gen_set_modulation("CW")           # CW | WLAN | BT | LTE ...
cmw.gen_set_output(True)               # RF output ON
print(cmw.gen_get_level())             # read back level
cmw.gen_set_output(False)              # RF output OFF
```

### Power Measurement

```python
cmw.meas_set_frequency(1_800_000_000)      # tune to 1800 MHz
cmw.meas_set_filter_bandwidth(20_000_000)  # 20 MHz filter
cmw.meas_set_trigger_source("IMMediate")   # free-run
cmw.meas_set_count(10)                     # average 10 samples

result = cmw.meas_read_power(timeout=10.0)
# GPRFPowerResult(status='RDY', current=-45.3, average=-45.1, minimum=-45.5, maximum=-44.9)
print(f"Average: {result.average:.2f} dBm")
```

**Trigger sources:** `IMMediate` (free-run) | `EXTernal` | `IF` | `Power`

To fetch the last result without re-triggering:

```python
result = cmw.meas_fetch_power()
```

To abort an ongoing measurement:

```python
cmw.meas_abort_power()
```

### Spectrum Measurement

```python
cmw.spec_set_center_frequency(2_400_000_000)   # 2.4 GHz centre
cmw.spec_set_span(100_000_000)                  # 100 MHz span
cmw.spec_set_rbw(1_000_000)                     # 1 MHz RBW

result = cmw.spec_read(timeout=15.0)
# GPRFSpectrumResult(start_freq=2350e6, stop_freq=2450e6, peak_power=-12.3, peak_freq=2402e6, ...)
print(f"Peak: {result.peak_power:.1f} dBm at {result.peak_freq/1e6:.1f} MHz")
```

---

## 7. LTE Signaling

Simulates an LTE base station (eNB). The DUT (UE) attaches to the virtual cell, allowing call control and layer-1/layer-2/IP measurements.

### Cell configuration

Use `LTECellConfig` to describe the cell in one object, then pass it to `configure_cell()`.

```python
from cmw_api.lte import LTECellConfig

cfg = LTECellConfig(
    band=3,                # LTE Band 3 (1800 MHz)
    dl_channel=1300,       # EARFCN
    bandwidth_mhz=20,      # 20 MHz
    dl_power_dbm=-65.0,    # DL RS power
    ul_power_max_dbm=23.0, # Max UE TX power
    cell_id=1,
    tac=1,
    mcc="234",
    mnc="30",
    imsi="234300000000001",
    auth_algo="MILENAGE",
)
cmw.configure_cell(cfg)
```

`LTECellConfig` fields and defaults:

| Field | Default | Description |
|---|---|---|
| `band` | `1` | LTE band number (1–71) |
| `dl_channel` | `300` | DL EARFCN |
| `bandwidth_mhz` | `10.0` | `1.4 \| 3 \| 5 \| 10 \| 15 \| 20` |
| `dl_power_dbm` | `-60.0` | DL reference signal power (dBm) |
| `ul_power_max_dbm` | `23.0` | Maximum UE UL power (dBm) |
| `cell_id` | `1` | Physical Cell Identity (PCI) |
| `tac` | `1` | Tracking Area Code |
| `mcc` | `"001"` | Mobile Country Code |
| `mnc` | `"01"` | Mobile Network Code |
| `imsi` | `""` | UE IMSI (leave empty to accept any) |
| `auth_algo` | `"MILENAGE"` | `MILENAGE \| XOR \| NONE` |

Individual parameters can also be set directly:

```python
cmw.set_band(7)
cmw.set_dl_earfcn(2850)
cmw.set_bandwidth(15)
cmw.set_dl_power(-70.0)
cmw.set_cell_id(42)
cmw.set_mcc_mnc("310", "260")
cmw.set_imsi("310260000000001")
cmw.set_authentication("MILENAGE", ki="000102030405060708090A0B0C0D0E0F",
                                    op="63BFA50EE6523365FF14C1F45F88737D")
cmw.set_category(6)                # UE category
```

### Link adaptation (DL/UL)

```python
cmw.set_dl_modulation("QAM64")    # QPSK | QAM16 | QAM64 | QAM256 | AUTO
cmw.set_ul_modulation("AUTO")
cmw.set_dl_rb_count(100)          # allocate all RBs for 20 MHz
cmw.set_ul_rb_count(50)
cmw.set_mimo(2)                   # 2×2 MIMO
```

### Cell on/off and call control

```python
cmw.cell_on()

# Wait for UE to register (network-initiated)
status = cmw.expect_attach(timeout=60)
print(status)   # "ATTached" or "CONNected"

# Establish a data bearer
cmw.connect(timeout=60)
print(cmw.get_call_status())    # "CONNected"

# Later...
cmw.disconnect()
cmw.cell_off()
```

Call status values: `DERegistered` → `REGistered` → `ATTached` → `CONNected`

### Handover

```python
cmw.initiate_handover(target_band=7, earfcn=2850)
```

### RX quality measurement (RSRP / RSRQ / RSSI / SINR)

```python
rx = cmw.measure_rx_quality(timeout=15.0)
print(f"RSRP={rx.rsrp_dbm:.1f} dBm  RSRQ={rx.rsrq_db:.1f} dB  SINR={rx.sinr_db:.1f} dB")
```

`LTEMeasResult` fields:

| Field | Unit | Description |
|---|---|---|
| `status` | — | `RDY` on success |
| `rsrp_dbm` | dBm | Reference Signal Received Power |
| `rsrq_db` | dB | Reference Signal Received Quality |
| `rssi_dbm` | dBm | Received Signal Strength Indicator |
| `sinr_db` | dB | Signal-to-Interference-plus-Noise Ratio |

To get the last result without re-triggering:

```python
rx = cmw.fetch_rx_quality()
```

### Throughput (IP data)

```python
cmw.configure_throughput(
    direction="DLULink",   # DL | UL | DLULink
    duration_s=10.0,
    payload_kb=0,          # 0 = time-based (unlimited payload)
)
result = cmw.measure_throughput(timeout=30.0)
print(f"DL: {result.dl_throughput_mbps:.1f} Mbps  ({result.dl_bler_pct:.2f}% BLER)")
print(f"UL: {result.ul_throughput_mbps:.1f} Mbps  ({result.ul_bler_pct:.2f}% BLER)")
```

### UL power

```python
pwr = cmw.measure_ul_power(timeout=15.0)
print(f"PUSCH={pwr.pusch_power_dbm:.1f} dBm  PUCCH={pwr.pucch_power_dbm:.1f} dBm")
```

### BLER

```python
result = cmw.measure_bler(samples=1000, timeout=30.0)
# {'status': 'RDY', 'dl_bler_pct': 0.1, 'ul_bler_pct': 0.0,
#  'dl_ack_count': 998, 'dl_nack_count': 2}
```

### Modulation quality (EVM)

```python
result = cmw.measure_evm(timeout=15.0)
# {'status': 'RDY', 'evm_rms_pct': 1.2, 'evm_peak_pct': 3.1,
#  'freq_error_hz': 15.0, 'timing_error_us': 0.03}
```

---

## 8. 5G NR Signaling

Simulates a 5G NR gNB in either Standalone (SA) or Non-Standalone / EN-DC (NSA) mode.

### Cell configuration

```python
from cmw_api.nr5g import NR5GCellConfig

cfg = NR5GCellConfig(
    band=78,              # n78 = 3.5 GHz sub-6 GHz
    dl_arfcn=632628,      # NR-ARFCN
    scs_khz=30,           # sub-carrier spacing: 15|30|60|120|240 kHz
    bandwidth_mhz=100,    # 100 MHz
    dl_power_dbm=-65.0,
    cell_id=1,
    tac=1,
    mcc="001",
    mnc="01",
    mode="SA",            # SA | NSA
)
cmw.configure_cell(cfg)
```

`NR5GCellConfig` fields:

| Field | Default | Description |
|---|---|---|
| `band` | `78` | NR band number |
| `dl_arfcn` | `632628` | NR-ARFCN for DL |
| `scs_khz` | `30` | Sub-carrier spacing (kHz) |
| `bandwidth_mhz` | `100` | Channel bandwidth (MHz) |
| `dl_power_dbm` | `-60.0` | DL SS/PBCH power |
| `cell_id` | `1` | Physical Cell Identity |
| `tac` | `1` | Tracking Area Code |
| `mcc` | `"001"` | Mobile Country Code |
| `mnc` | `"01"` | Mobile Network Code |
| `mode` | `"SA"` | `SA` (standalone) or `NSA` (EN-DC) |

### Cell on/off and call control

Same pattern as LTE:

```python
cmw.cell_on()
cmw.expect_attach(timeout=90)
cmw.connect(timeout=90)
# ... run measurements ...
cmw.disconnect()
cmw.cell_off()
```

### EN-DC (NSA mode)

Configure the LTE anchor before enabling the NR cell:

```python
cmw.set_mode("NSA")
cmw.endc_set_lte_anchor_band(3)
cmw.endc_set_lte_earfcn(1300)
cmw.cell_on()
cmw.expect_attach(timeout=90)
print(cmw.endc_get_status())    # "CONNected" when NR leg is up
```

### RX quality (SS-RSRP / SS-RSRQ / SS-SINR / CSI-RSRP)

```python
rx = cmw.measure_rx_quality(timeout=15.0)
print(f"SS-RSRP={rx.ss_rsrp_dbm:.1f} dBm  SS-SINR={rx.ss_sinr_db:.1f} dB")
```

`NR5GMeasResult` fields:

| Field | Unit | Description |
|---|---|---|
| `ss_rsrp_dbm` | dBm | SS Reference Signal Received Power |
| `ss_rsrq_db` | dB | SS Reference Signal Received Quality |
| `ss_sinr_db` | dB | SS Signal-to-Interference-plus-Noise Ratio |
| `csi_rsrp_dbm` | dBm | CSI Reference Signal Received Power |

### Throughput, BLER, EVM

Same method signatures as LTE — see [Section 7](#7-lte-signaling).

```python
cmw.configure_throughput(direction="DL", duration_s=10.0)
result = cmw.measure_throughput()

bler = cmw.measure_bler(samples=1000)
evm  = cmw.measure_evm()
```

---

## 9. WCDMA / UMTS Signaling

### Cell configuration

```python
from cmw_api.wcdma import WCDMACellConfig

cfg = WCDMACellConfig(
    band=1,
    dl_uarfcn=10700,
    dl_power_dbm=-60.0,
    cell_id=1,
    mcc="234",
    mnc="30",
)
cmw.configure_cell(cfg)
```

| Field | Default | Description |
|---|---|---|
| `band` | `1` | UMTS band |
| `dl_uarfcn` | `10700` | DL UARFCN |
| `dl_power_dbm` | `-60.0` | DL cell power |
| `cell_id` | `1` | Primary Scrambling Code |
| `mcc` / `mnc` | `"001"/"01"` | Network identity |
| `imsi` | `""` | UE IMSI (empty = any) |

### Call control

```python
cmw.cell_on()
cmw.expect_attach(timeout=60)
cmw.connect(timeout=60)
cmw.disconnect()
cmw.cell_off()
```

### Measurements

```python
# RSCP / Ec/No / RSSI
rx = cmw.measure_rx_quality()
print(f"RSCP={rx.rscp_dbm:.1f}  Ec/No={rx.ec_no_db:.1f}")

# UL power (DPCCH / DPDCH)
pwr = cmw.measure_ul_power()
print(f"DPCCH={pwr['dpcch_power_dbm']:.1f} dBm")
```

---

## 10. Bluetooth

### Bluetooth Classic (BR/EDR)

#### Configuration

> **Important:** `set_frequency()`, `set_expected_power()`, `set_packet_type()`, `set_trigger_source()`, and `set_burst_count()` are **Classic-only**. For BLE use the `le_*` equivalents.

```python
cmw.set_frequency(channel=0)          # BT Classic channel 0 = 2402 MHz; range 0–78
cmw.set_expected_power(dbm=4.0)       # approximate DUT TX power (Classic only)
cmw.set_packet_type("DH1")            # DH1 | DH3 | DH5 | 2DH1 | 2DH3 | 3DH1 | 3DH3 | 3DH5
cmw.set_trigger_source("POWer")       # IMMediate | POWer | EXTernal
cmw.set_burst_count(100)              # statistics averaging count
cmw.set_payload_pattern("PRBS9")      # PRBS9 | PRBS15 | 11110000 | 10101010 | ALLOnes | ALLZeros
cmw.set_whitening(True, tech="BT")    # data whitening ON (standard) / OFF (debug)
```

#### TX power

```python
result = cmw.measure_tx_power(timeout=15.0)
print(f"Power={result.power_dbm:.2f} dBm  Freq error={result.freq_error_khz:.1f} kHz")
```

`BTRFResult` fields: `status`, `power_dbm`, `freq_error_khz`, `modulation_index`

To fetch without re-triggering:

```python
result = cmw.fetch_tx_power()
```

#### Frequency deviation / modulation

```python
mod = cmw.measure_modulation()
# {'status': 'RDY', 'max_freq_dev_khz': 158.3, 'avg_freq_dev_khz': 155.1, 'modulation_index': 0.31}
```

#### ICFT — Initial Carrier Frequency Tolerance

Mandatory for BR/EDR conformance (typical limit: ±75 kHz / ±75 ppm).

```python
result = cmw.measure_icft(timeout=15.0)
# {'status': 'RDY', 'icft_ppm': 12.3, 'pass_fail': 'PASS'}
print(f"ICFT={result['icft_ppm']:.1f} ppm  →  {result['pass_fail']}")
```

#### DEVM — Differential EVM for EDR

Mandatory for EDR (2DH / 3DH) conformance. Select an EDR packet type first.

```python
cmw.set_packet_type("2DH1")   # or 3DH1, 3DH5, etc.
result = cmw.measure_devm(timeout=15.0)
# {'status': 'RDY', 'devm_db': -28.5, 'evm_rms_db': -30.1, 'evm_peak_db': -24.3}
print(f"DEVM={result['devm_db']:.1f} dB  EVM RMS={result['evm_rms_db']:.1f} dB")
```

#### Carrier frequency drift

```python
result = cmw.measure_frequency_drift(duration_s=1.0, timeout=30.0)
# {'status': 'RDY', 'drift_ppm': 3.2}
print(f"Drift={result['drift_ppm']:.1f} ppm")
```

#### BER

```python
cmw.configure_ber(packet_count=1000)
result = cmw.measure_ber(timeout=30.0)
print(f"BER={result.ber_pct:.4f}%  Errors={result.error_count}/{result.packet_count}")
```

---

### Bluetooth LE

#### Configuration

```python
cmw.le_set_phy("LE1M")               # LE1M | LE2M | LECoded_S2 | LECoded_S8
cmw.le_set_channel(37)               # LE channel index 0–39 (37/38/39 = advertising)
cmw.le_set_expected_power(dbm=0.0)   # expected DUT TX power (LE-specific)
cmw.set_whitening(True, tech="BLE")  # data whitening ON (standard) / OFF (debug)
```

**LE PHY reference:**

| Value | PHY | Data rate | Range |
|---|---|---|---|
| `LE1M` | LE 1M | 1 Mbps | Standard |
| `LE2M` | LE 2M | 2 Mbps | Short range, higher throughput |
| `LECoded_S2` | LE Coded S=2 | 500 kbps | ~2× range vs LE 1M |
| `LECoded_S8` | LE Coded S=8 | 125 kbps | ~4× range vs LE 1M |

#### TX power

```python
pwr = cmw.le_measure_tx_power(timeout=15.0)
print(f"Power={pwr.power_dbm:.2f} dBm  Freq error={pwr.freq_error_khz:.1f} kHz")
# Note: modulation_index is 0.0 for LE Coded PHY (not reported by CMW)
```

#### RSSI

```python
rssi = cmw.le_measure_rssi(timeout=15.0)
print(f"RSSI={rssi['rssi_dbm']:.1f} dBm")
```

#### Frequency offset

BLE 5.0+ requires frequency accuracy within ±20 ppm.

```python
result = cmw.le_measure_frequency_offset(timeout=15.0)
print(f"Freq offset={result['freq_offset_ppm']:.1f} ppm  ({result['freq_offset_khz']:.2f} kHz)")
```

#### BER

```python
ber = cmw.le_measure_ber(packet_count=1000, timeout=30.0)
print(f"BER={ber.ber_pct:.4f}%  Errors={ber.error_count}/{ber.packet_count}")
```

#### PER — Packet Error Rate (conformance metric)

PER is the primary RX sensitivity metric in BLE conformance testing. The Bluetooth Core Spec defines a pass threshold of < 30.8% PER at the reference sensitivity level.

```python
result = cmw.le_measure_per(packet_count=1500, timeout=30.0)
# BTLEPERResult(status='RDY', per_pct=0.2, packet_count=1500, error_count=3)
print(f"PER={result.per_pct:.3f}%  →  {'PASS' if result.per_pct < 30.8 else 'FAIL'}")
```

#### Direction Finding — CTE / AoA / AoD (BLE 5.1+)

Constant Tone Extension (CTE) enables Angle of Arrival and Angle of Departure measurements for indoor positioning.

```python
cmw.le_configure_cte(cte_type="AOA", length_us=16)   # AOA | AOD | CONnectionless
# Then trigger the standard TX power or BER measurement; CMW captures the CTE automatically
```

---

## 11. WLAN

Requires the CMW WLAN software option:

| Standard | Required option |
|---|---|
| 802.11 a/b/g/n/ac/ax | CMW-KM052x |
| 802.11be (Wi-Fi 7) | CMW-KM053x (in addition to CMW-KM052x) |

### Configuration

**Supported standards:**

| Value | Standard | Common name | Max BW | Rate/MCS config |
|---|---|---|---|---|
| `A` | 802.11a | Wi-Fi 1 | 20 MHz | `set_data_rate()` — 6/9/12/18/24/36/48/54 Mbps |
| `B` | 802.11b | Wi-Fi 1 | 22 MHz | `set_data_rate()` — 1/2/5.5/11 Mbps |
| `G` | 802.11g | Wi-Fi 3 | 20 MHz | `set_data_rate()` — 6/9/12/18/24/36/48/54 Mbps |
| `N` | 802.11n | Wi-Fi 4 | 40 MHz | `set_mcs()` — MCS 0–31 |
| `AC` | 802.11ac | Wi-Fi 5 | 160 MHz | `set_mcs()` — MCS 0–9 |
| `AX` | 802.11ax | Wi-Fi 6/6E | 160 MHz | `set_mcs()` — MCS 0–11 |
| `BE` | 802.11be | Wi-Fi 7 | 320 MHz | `set_eht_mcs()` — MCS 0–15 |

> **Note:** BE requires CMW firmware with 802.11be support and the **CMW-KM053x** option.

```python
cmw.set_standard("AX")              # A | B | G | N | AC | AX | BE
cmw.set_channel(36)                 # 802.11 channel number
cmw.set_bandwidth(80)               # 20 | 40 | 80 | 160 | 320 MHz
cmw.set_mcs(11)                     # MCS index — range depends on standard (see table above)
cmw.set_guard_interval("VSHORT")    # see guard interval table below
cmw.set_spatial_streams(2)          # 1–4 for N/AC/AX; 1–16 for BE
cmw.set_expected_power(dbm=20.0)
cmw.set_trigger_source("POWer")     # IMMediate | POWer | EXTernal
cmw.set_burst_count(100)
```

**Guard interval values:**

| Value | Duration | Valid for |
|---|---|---|
| `NORM` | 800 ns | All standards |
| `SHORT` | 400 ns | 802.11n, 802.11ac |
| `VSHORT` | 200 ns | 802.11ax (HE), 802.11be (EHT) |
| `DBL` | 1600 ns | 802.11be (EHT) — extended range |
| `QUAD` | 3200 ns | 802.11be (EHT) — maximum range |

**Legacy standards (A/B/G) — use data rate instead of MCS:**

```python
cmw.set_standard("G")
cmw.set_data_rate(54.0)   # 54 Mbps (802.11g max)

cmw.set_standard("B")
cmw.set_data_rate(11.0)   # 11 Mbps (802.11b max)
```

### TX power

```python
result = cmw.measure_tx_power(timeout=15.0)
print(f"Avg power={result.avg_power_dbm:.2f} dBm  Peak={result.peak_power_dbm:.2f} dBm")
```

`WLANPowerResult` fields: `status`, `power_dbm`, `avg_power_dbm`, `peak_power_dbm`

### EVM

```python
result = cmw.measure_evm(timeout=15.0)
print(f"EVM RMS={result.evm_rms_db:.2f} dB  Freq error={result.freq_error_khz:.3f} kHz")
```

`WLANEVMResult` fields: `status`, `evm_rms_db`, `evm_peak_db`, `freq_error_khz`, `symbol_clock_error_ppm`

### Spectral mask

```python
result = cmw.measure_spectral_mask(timeout=15.0)
print(f"Mask: {result['mask_result']}  Margin={result['margin_db']:.1f} dB")
```

### Adjacent Channel Power (ACP / ACLR)

Used for regulatory spectral compliance (FCC part 15, ETSI EN 300 328).

```python
cmw.configure_acp(offset_mhz=20.0)      # offset = channel spacing
result = cmw.measure_acp(timeout=15.0)
print(f"Primary={result.primary_power_dbm:.1f} dBm")
print(f"Lower ACP={result.lower_acp_dbm:.1f} dBm  ACLR={result.lower_aclr_db:.1f} dB")
print(f"Upper ACP={result.upper_acp_dbm:.1f} dBm  ACLR={result.upper_aclr_db:.1f} dB")
```

`WLANACPResult` fields: `status`, `primary_power_dbm`, `lower_acp_dbm`, `upper_acp_dbm`, `lower_aclr_db`, `upper_aclr_db`

### Occupied Bandwidth (OBW)

```python
cmw.configure_obw(percent=99.0)      # bandwidth containing 99% of power
result = cmw.measure_obw(timeout=15.0)
print(f"OBW={result['obw_mhz']:.1f} MHz")
```

### RSSI (RX sensitivity)

```python
result = cmw.measure_rssi(timeout=15.0)
print(f"RSSI={result['rssi_dbm']:.1f} dBm")
```

### Packet Error Rate (PER)

```python
cmw.configure_per(packet_count=1000)
result = cmw.measure_per(timeout=30.0)
print(f"PER={result['per_pct']:.3f}%  ({result['error_count']}/{result['packet_count']})")
```

### 802.11ax (HE / Wi-Fi 6/6E) specific

#### HE PPDU format

```python
cmw.set_he_ppdu_format("SU")    # SU (single-user) | MU (multi-user DL) | TRIG (triggered UL) | ER (extended range)
```

#### BSS colour (spatial reuse)

```python
cmw.set_bss_colour(42)   # 0–63; valid for both AX and BE
```

#### OFDMA resource unit allocation

```python
# Four 26-tone RUs in a 20 MHz channel (uplink OFDMA)
cmw.set_ofdma_ru_allocation("26,26,26,26")
# Single full-channel RU (242 tones = full 20 MHz)
cmw.set_ofdma_ru_allocation("242")
```

#### Target Wake Time (TWT)

```python
cmw.set_twt(enabled=True, wake_interval_ms=512.0, sleep_duration_ms=100.0)
```

### 802.11be (Wi-Fi 7) — EHT specific

Wi-Fi 7 introduces **4096-QAM**, **320 MHz channels**, **preamble puncturing**, and **Multi-Link Operation (MLO)**.

#### EHT MCS (0–15)

```python
cmw.set_standard("BE")
cmw.set_bandwidth(320)      # up to 320 MHz on 6 GHz
cmw.set_eht_mcs(13)         # MCS 13 = 4096-QAM 5/6
```

| MCS | Modulation | Notes |
|---|---|---|
| 0–9 | up to 1024-QAM 5/6 | Shared with 802.11ax |
| 10–11 | 1024-QAM | New in 802.11be |
| 12–13 | 4096-QAM | New in 802.11be — requires very high SNR |
| 14 | BPSK + DCM + DUP | Robust duplicate mode — **puncturing only** |
| 15 | BPSK + DUP | Robust duplicate mode — **puncturing only** |

> **MCS 14 & 15** are extra-robust BPSK modes (not higher-order modulations). They are defined exclusively for **preamble-punctured** transmissions and trade throughput for robustness. They are only valid when a puncturing pattern is active.

```python
# MCS 14/15 require an active puncturing pattern
cmw.set_standard("BE")
cmw.set_bandwidth(160)
cmw.set_eht_puncturing_pattern("P80")   # puncture an 80 MHz sub-channel first
cmw.set_eht_mcs(14)                      # BPSK + DCM + DUP robust mode
```

#### Preamble puncturing

```python
cmw.set_eht_puncturing_pattern("NONE")   # no puncturing (default)
cmw.set_eht_puncturing_pattern("P80")    # puncture one 80 MHz sub-channel
cmw.set_eht_puncturing_pattern("P160")   # puncture one 160 MHz sub-channel
```

#### Multi-Link Operation (MLO)

MLO allows simultaneous TX/RX across multiple bands. Configure each link then set the active count.

```python
# 3-link MLO: 2.4 GHz + 5 GHz + 6 GHz
cmw.set_mlo_link(0, freq_hz=2_437_000_000, bw_mhz=40)    # link 0 — 2.4 GHz ch 6
cmw.set_mlo_link(1, freq_hz=5_180_000_000, bw_mhz=80)    # link 1 — 5 GHz ch 36
cmw.set_mlo_link(2, freq_hz=6_135_000_000, bw_mhz=320)   # link 2 — 6 GHz ch 1
cmw.set_mlo_link_count(3)

# Per-link power results
per_link = cmw.measure_tx_power_mlo(link_count=3)
for i in range(3):
    print(f"Link {i}: {per_link[f'link_{i}_power_dbm']:.1f} dBm")
```

#### Full Wi-Fi 7 EVM example

```python
cmw.set_standard("BE")
cmw.set_bandwidth(320)
cmw.set_eht_mcs(11)                   # 1024-QAM
cmw.set_guard_interval("VSHORT")      # 200 ns
cmw.set_spatial_streams(4)
cmw.set_expected_power(dbm=20.0)

result = cmw.measure_evm(timeout=15.0)
print(f"EVM RMS={result.evm_rms_db:.2f} dB  Freq error={result.freq_error_khz:.3f} kHz")
```

---

## 12. Error Handling

### Exception hierarchy

```
CMWError                   — base class; catch this to handle all CMW errors
├── CMWTimeoutError        — poll loop or *OPC? exceeded the timeout
└── CMWMeasurementError    — measurement returned an ERR state, or SCPI error queue contained entries
```

```python
from cmw_api import CMW
from cmw_api.exceptions import CMWError, CMWTimeoutError, CMWMeasurementError
```

### Handling connection failures

```python
from cmw_api.exceptions import CMWError

try:
    cmw = CMW.via_tcp("192.168.0.1")
except CMWError as e:
    print(f"Could not connect: {e}")
```

### Handling measurement timeouts

```python
from cmw_api.exceptions import CMWTimeoutError

try:
    result = cmw.expect_attach(timeout=30)
except CMWTimeoutError:
    print("UE did not attach within 30 seconds")
    cmw.cell_off()
```

### Handling measurement errors

```python
from cmw_api.exceptions import CMWMeasurementError

try:
    result = cmw.measure_throughput(timeout=20)
except CMWMeasurementError as e:
    print(f"Measurement failed: {e}")
    cmw.get_all_errors()   # drain SCPI queue before next test
```

### Checking SCPI errors after commands

Call `get_all_errors()` after a block of configuration commands to surface any bad parameters early:

```python
cmw.set_band(999)          # invalid band
errors = cmw.get_all_errors()
if errors:
    raise RuntimeError(f"Configuration errors: {errors}")
```

---

## 13. Patterns and Best Practices

### Always use the context manager

The `with` statement guarantees the transport is closed even if an exception occurs mid-test.

```python
with CMW.via_tcp("192.168.0.1") as cmw:
    cmw.initialize()
    # ... test steps ...
```

### Parameterise config objects for readability

```python
BAND_3_20MHZ = LTECellConfig(
    band=3, dl_channel=1300, bandwidth_mhz=20,
    mcc="234", mnc="30",
)

with CMW.via_tcp(CMW_IP) as cmw:
    cmw.initialize()
    cmw.lte_set_rx_connector("RF1C")
    cmw.configure_cell(BAND_3_20MHZ)
    cmw.cell_on()
    cmw.expect_attach()
    cmw.connect()
    ...
```

### Reset between test cases

```python
def run_test(cmw, cfg):
    cmw.safe_preset()              # reset, clear errors, wait idle
    cmw.lte_set_rx_connector("RF1C")
    cmw.configure_cell(cfg)
    cmw.cell_on()
    cmw.expect_attach()
    cmw.connect()
    return cmw.measure_throughput()

with CMW.via_tcp(CMW_IP) as cmw:
    cmw.initialize()
    for cfg in [BAND_1_10MHZ, BAND_3_20MHZ, BAND_7_20MHZ]:
        result = run_test(cmw, cfg)
        print(cfg.band, result)
```

### Disable display update for faster throughput

```python
cmw.set_display_update(False)
# ... run many measurements ...
cmw.set_display_update(True)
```

### Save and restore instrument state

```python
# Save state at the start of a test session
cmw.mem_store("/var/user/session_start.savrcl")

# Restore if something goes wrong
cmw.mem_load("/var/user/session_start.savrcl")
```

### Mix initiate + fetch for back-to-back measurements

`measure_*()` methods both initiate and fetch in one blocking call. When you need to overlap measurement time with other work, use the low-level pattern:

```python
cmw.meas_initiate_power()          # fire and move on
# ... do other work here ...
result = cmw.meas_fetch_power()    # collect when needed
```

---

## 14. Troubleshooting

### Cannot connect via TCP

- Verify the CMW's IP address in **Setup → Instrument → Network**.
- Confirm TCP port 5025 is not blocked by a firewall.
- Try pinging the instrument: `ping 192.168.0.1`
- Check the CMW front-panel LAN LED is lit.

### `pyvisa` import error

```
CMWError: pyvisa is not installed. Run: pip install pyvisa pyvisa-py
```

Install the packages: `pip install pyvisa pyvisa-py`

### VISA resource not found

```python
import pyvisa
rm = pyvisa.ResourceManager()
print(rm.list_resources())
```

If your instrument is not listed, ensure:
- NI-VISA or the pyvisa-py backend is correctly installed.
- The HiSLIP or VXI-11 service is enabled on the CMW (Setup → Network).
- The resource string matches — HiSLIP format: `TCPIP::ip::hislip0::INSTR`.

### Measurement always returns `ERR`

1. Drain the error queue: `print(cmw.get_all_errors())`
2. Verify the application option is installed: `cmw.get_options()`
3. Ensure the correct RF connector and routing are set before initiating.
4. Confirm the DUT is transmitting on the expected frequency and channel.

### UE never attaches (LTE/NR/WCDMA)

- Verify the DL power is not too low (`dl_power_dbm` typically `-65` to `-70` dBm at the DUT).
- Confirm MCC/MNC match what the DUT expects (or disable PLMN locking on the DUT).
- Check `get_cell_state()` returns `ON` before calling `expect_attach()`.
- For 5G SA, confirm the DUT supports the configured NR band and bandwidth.

### `CMWTimeoutError` on `expect_attach`

Increase the timeout or add diagnostic logging:

```python
import time

deadline = time.time() + 90
while time.time() < deadline:
    status = cmw.get_call_status()
    print(f"[{time.strftime('%H:%M:%S')}] status = {status}")
    if status in ("ATTached", "CONNected"):
        break
    time.sleep(2)
```

### BLE conformance test failures (PER too high / RSSI unexpected)

- Ensure `le_set_phy()` is called **before** `le_measure_per()` or `le_measure_rssi()`.
- Use `le_set_expected_power()` (not `set_expected_power()`) for BLE — the Classic and LE paths are separate on the CMW.
- For LE Coded PHY (S2/S8) BER/PER measurements, allow a longer timeout — S8 packets are 8× longer than LE 1M.
- If `BTRFResult.modulation_index` is `0.0` for LE Coded, this is expected — the CMW does not return that field for this PHY.
- Verify `LECoded_S2` / `LECoded_S8` string format with your CMW firmware version; some versions use `LECODED_S2` (no underscore).

### EDR DEVM measurement returns `ERR`

- DEVM requires an **EDR packet type** — call `set_packet_type("2DH1")` or `"3DH1"` etc. before triggering.
- Verify the DUT is transmitting EDR frames, not basic-rate BR frames.
- DEVM is only valid with `set_packet_type()` values starting with `2` (π/4-DQPSK) or `3` (8DPSK).
- Check `cmw.get_all_errors()` — a common error is attempting DEVM with a BR (DH) packet type selected.

### 802.11be (Wi-Fi 7) measurement returns `ERR` or is not available

- Confirm the **CMW-KM053x** option is installed: `cmw.get_options()` — the option key must appear in the returned string.
- Verify the CMW firmware version supports 802.11be (check the R&S release notes for your firmware).
- `set_standard("BE")` and `set_bandwidth(320)` must be called **before** any measurement is initiated.
- 320 MHz operation requires the 6 GHz band — confirm the DUT is transmitting on a valid 6 GHz channel (e.g. channel 1 at 5955 MHz).
- For MLO, each configured link (`set_mlo_link`) must have a distinct frequency band. Configuring two links on the same band will cause an error.
- EHT MCS 12/13 (4096-QAM) require a very high SNR — if EVM measurement fails, try a lower MCS index first to isolate whether the issue is the modulation order or the measurement setup.

### Slow measurement loop

- Call `set_display_update(False)` before the loop.
- Use `fetch_*()` variants instead of `measure_*()` when re-reading a continuously running measurement.
- Use `*OPC?` synchronisation only when truly needed — it adds at least one round-trip latency per measurement.
