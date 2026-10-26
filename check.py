"""Diz se o receptor do G435 ligado neste PC é compatível com o app.

Só lê: lista os dispositivos USB e, no receptor compatível, pede a versão do firmware da ponte.
"""
import sys
import time

import hid

from protocol import PID, USAGE_PAGE, VID, build_report

HID_CMD_READ_FW_VERSION = 0x84
PID_REALTEK = 0x0ACB


def read_fw_version(path):
    dev = hid.device()
    dev.open_path(path)
    try:
        dev.write(build_report(HID_CMD_READ_FW_VERSION, [1]))
        time.sleep(0.01)
        reply = bytes(dev.get_input_report(0, 65))
    finally:
        dev.close()
    if len(reply) < 2 or reply[1] != ord('O'):
        return None
    return reply[2:].split(b'\0')[0].decode(errors='replace')


def main():
    found = {d['product_id'] for d in hid.enumerate(VID)}

    if PID in found:
        paths = [d['path'] for d in hid.enumerate(VID, PID) if d['usage_page'] == USAGE_PAGE]
        if not paths:
            print(f'Receiver {VID:04X}:{PID:04X} found, but without the 0x{USAGE_PAGE:04X} interface.')
            print('This is unexpected. Please open an issue with this message.')
            return 1
        try:
            fw = read_fw_version(paths[0])
        except OSError as e:
            fw = None
            print(f'(could not read the firmware version: {e})')
        print(f'COMPATIBLE: receiver {VID:04X}:{PID:04X} (Holtek bridge), firmware {fw or "unknown"}.')
        if fw and fw != 'V1.8.5.1':
            print('Firmware differs from the tested one (V1.8.5.1). It should work; if not, please open an issue.')
        return 0

    if PID_REALTEK in found:
        print(f'NOT COMPATIBLE: receiver {VID:04X}:{PID_REALTEK:04X} (original G435, Realtek bridge).')
        print('This receiver uses a different protocol and is not supported.')
        return 2

    print('No G435 receiver found. Is it plugged in?')
    return 3


if __name__ == '__main__':
    sys.exit(main())
