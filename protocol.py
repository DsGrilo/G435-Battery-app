"""Protocolo do dongle LIGHTSPEED do G435 com chip Holtek (046D:0ADF).

Formato tirado da ferramenta oficial G435Update 3.1.1.14 (dfu_utility + AWToolLIB2.dll).

Envio (output report de 65 bytes, report ID 0):
    00 | hid_cmd | len | crc16 lo | crc16 hi | dados (60 bytes)
    crc16 = CRC-16/XMODEM sobre o pacote inteiro com o campo de crc zerado.
    Depois de cada envio, um GetInputReport devolve 'O' (ok) ou 'F' (falha) no byte 1.

hid_cmd 0x80 encapsula um comando "PA" para o chip de rádio:
    'P' 'A' | categoria | transmissão | len | ...

Eventos (input reports de 64 bytes): [tam] + frames
    'P' 'I' | tipo | seq | timestamp u32 LE | len u16 LE | payload[len]

Payloads observados:
    04 cc ?? ??   status do headset: cc=1 conectado
    0e ..         resposta de comando de link (e0 = modo, e6 = status da conexão)
    06 tt ss vv vv  resposta OTA (tt = transmissão, ss = 0 ok, vv = valor u16 LE)
    20 kk 00      tecla de mídia (e9 vol+, ea vol-, 00 soltou)
"""
import struct
from dataclasses import dataclass

VID, PID = 0x046D, 0x0ADF
USAGE_PAGE = 0xFF00

CMD_STATUS = 0x04

HID_CMD_AW_WRITE = 0x80
HID_CMD_POWER_SAVING = 0x85

LQ_GET_MODE = 0xE0
LQ_SET_MODE = 0xE1
LQ_GET_CONNECT_STATUS = 0xE6
OTA_GET_BATTERY = 0x31

# tensão (mV) -> %, curva típica de célula de lítio 3,7 V
VOLTAGE_CURVE = [
    (4200, 100), (4100, 90), (4000, 80), (3900, 65), (3800, 50),
    (3750, 40), (3700, 30), (3650, 20), (3600, 10), (3500, 5), (3300, 0),
]


@dataclass
class Frame:
    typ: int
    seq: int
    payload: bytes


@dataclass
class Status:
    connected: bool


def crc16_xmodem(data) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def build_report(hid_cmd: int, data) -> list[int]:
    pkt = [0, hid_cmd, len(data), 0, 0] + list(data) + [0] * (60 - len(data))
    crc = crc16_xmodem(pkt)
    pkt[3], pkt[4] = crc & 0xFF, crc >> 8
    return pkt


def lq_command(cmd_id: int, *params: int) -> list[int]:
    return [0x50, 0x41, 0x0E, 0, 1 + len(params), cmd_id, *params]


def ota_command(cmd_id: int) -> list[int]:
    return [0x50, 0x41, 0x06, 0, 1, 0, cmd_id]


def parse_report(report) -> list[Frame]:
    if not report:
        return []
    size = report[0]
    data = bytes(report[1:1 + size])
    frames, i = [], 0
    while i + 10 <= len(data) and data[i:i + 2] == b'PI':
        length = struct.unpack_from('<H', data, i + 8)[0]
        frames.append(Frame(data[i + 2], data[i + 3], data[i + 10:i + 10 + length]))
        i += 10 + length
    return frames


def parse_status(frame: Frame) -> Status | None:
    p = frame.payload
    if len(p) < 2 or p[0] != CMD_STATUS:
        return None
    return Status(connected=p[1] == 1)


def parse_lq_reply(frame: Frame, cmd_id: int) -> int | None:
    p = frame.payload
    if len(p) >= 2 and p[0] == cmd_id:
        return p[1]
    return None


def parse_ota_reply(frame: Frame, transmission: int) -> int | None:
    p = frame.payload
    # a resposta ecoa a transmissão com o bit 7 ligado
    if len(p) >= 5 and p[0] == 0x06 and p[1] & 0x7F == transmission and p[2] == 0:
        return struct.unpack_from('<H', p, 3)[0]
    return None


def voltage_to_percent(mv: int) -> int:
    if mv >= VOLTAGE_CURVE[0][0]:
        return 100
    for (v_hi, p_hi), (v_lo, p_lo) in zip(VOLTAGE_CURVE, VOLTAGE_CURVE[1:]):
        if mv >= v_lo:
            return round(p_lo + (p_hi - p_lo) * (mv - v_lo) / (v_hi - v_lo))
    return 0
