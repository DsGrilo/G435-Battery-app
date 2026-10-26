"""Conversa com o dongle: leitura de eventos e pedido de bateria ao headset."""
import time

import hid

from protocol import (HID_CMD_AW_WRITE, HID_CMD_POWER_SAVING, LQ_GET_CONNECT_STATUS,
                      LQ_GET_MODE, LQ_SET_MODE, OTA_GET_BATTERY, PID, USAGE_PAGE, VID,
                      Frame, build_report, lq_command, ota_command, parse_lq_reply,
                      parse_ota_reply, parse_report)


class DongleError(Exception):
    pass


def find_path():
    paths = [d['path'] for d in hid.enumerate(VID, PID) if d['usage_page'] == USAGE_PAGE]
    return paths[0] if paths else None


class Dongle:
    def __init__(self, path, on_frame=None):
        self.dev = hid.device()
        self.dev.open_path(path)
        self.on_frame = on_frame or (lambda frame: None)
        self.transmission = 0
        # a ferramenta oficial desliga a economia de energia da ponte ao conectar
        self._hid_command(HID_CMD_POWER_SAVING, [1], check=False)

    def close(self):
        self.dev.close()

    def poll(self, timeout_ms=1000) -> list[Frame]:
        frames = parse_report(self.dev.read(64, timeout_ms))
        for frame in frames:
            self.on_frame(frame)
        return frames

    def _hid_command(self, hid_cmd, data, check=True):
        self.dev.write(build_report(hid_cmd, data))
        time.sleep(0.01)
        reply = self.dev.get_input_report(0, 65)
        if check and (len(reply) < 2 or reply[1] != ord('O')):
            raise DongleError(f'comando {hid_cmd:#04x} recusado')
        return reply

    def _aw_command(self, cmd):
        if cmd[3] == 0:
            self.transmission = self.transmission % 127 + 1
            cmd[3] = self.transmission
        self._hid_command(HID_CMD_AW_WRITE, cmd)
        return cmd[3]

    def _wait(self, match, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            for frame in self.poll(100):
                value = match(frame)
                if value is not None:
                    return value
        raise DongleError('sem resposta')

    def _lq_get(self, cmd_id):
        self._aw_command(lq_command(cmd_id))
        return self._wait(lambda f: parse_lq_reply(f, cmd_id))

    def _set_remote(self, remote):
        self._aw_command(lq_command(LQ_SET_MODE, 1 if remote else 0))
        if self._lq_get(LQ_GET_MODE) != int(remote):
            raise DongleError('não trocou de modo')

    def headset_linked(self) -> bool:
        # bit 0x08 é o que a ferramenta oficial exige para entrar em modo remoto
        return bool(self._lq_get(LQ_GET_CONNECT_STATUS) & 0x08)

    def read_battery_mv(self) -> int:
        """Tensão da bateria do headset em mV. Deixa o dongle de volta em modo local."""
        was_remote = self._lq_get(LQ_GET_MODE) == 1
        if not was_remote:
            self._set_remote(True)
        try:
            trans = self._aw_command(ota_command(OTA_GET_BATTERY))
            return self._wait(lambda f: parse_ota_reply(f, trans))
        finally:
            if not was_remote:
                self._set_remote(False)
