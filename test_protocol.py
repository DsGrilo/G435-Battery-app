from protocol import (build_report, crc16_xmodem, lq_command, ota_command, parse_lq_reply,
                      parse_ota_reply, parse_report, parse_status, voltage_to_percent)


def hexreport(s):
    return list(bytes.fromhex(s).ljust(64, b'\0'))


def test_status_connected():
    r = hexreport('0e 50 49 11 ca c8 ab 6e 00 04 00 04 01 00 32')
    [f] = parse_report(r)
    assert parse_status(f).connected


def test_status_disconnected():
    r = hexreport('0e 50 49 11 c8 4c 82 6e 00 04 00 04 00 00 32')
    assert not parse_status(parse_report(r)[0]).connected


def test_two_frames_and_stale_tail_ignored():
    # tamanho 0x1a = dois frames de 13 bytes; o resto é lixo de buffer anterior
    r = hexreport('1a 50 49 01 c0 ab ac 6e 00 03 00 11 af 18 '
                  '50 49 01 c0 ac ac 6e 00 03 00 11 b0 17 32 49 11')
    frames = parse_report(r)
    assert [f.payload.hex() for f in frames] == ['11af18', '11b017']
    assert all(parse_status(f) is None for f in frames)


def test_media_key_is_not_status():
    r = hexreport('0d 50 49 11 cb 99 ac 6e 00 03 00 20 e9 00')
    assert parse_status(parse_report(r)[0]) is None


def test_crc_and_report_layout():
    pkt = build_report(0x84, [1])
    assert len(pkt) == 65 and pkt[:3] == [0, 0x84, 1] and pkt[5] == 1
    zeroed = pkt[:3] + [0, 0] + pkt[5:]
    assert crc16_xmodem(zeroed) == pkt[3] | pkt[4] << 8
    assert crc16_xmodem(b'123456789') == 0x31C3  # valor de referência do CRC-16/XMODEM


def test_commands():
    assert lq_command(0xE1, 1) == [0x50, 0x41, 0x0E, 0, 2, 0xE1, 1]
    assert ota_command(0x31) == [0x50, 0x41, 0x06, 0, 1, 0, 0x31]


def test_mode_reply_captured():
    r = hexreport('19 50 49 01 c0 86 17 26 01 03 00 0e 82 00 '
                  '50 49 0e d6 00 00 00 00 02 00 e0 01')
    frames = parse_report(r)
    assert [parse_lq_reply(f, 0xE0) for f in frames] == [None, 1]


def test_battery_reply_captured():
    r = hexreport('11 50 49 01 d7 98 fb 36 00 07 00 06 83 00 6b 10 00 00')
    [f] = parse_report(r)
    assert parse_ota_reply(f, 3) == 4203
    assert parse_ota_reply(f, 4) is None


def test_voltage_to_percent():
    assert voltage_to_percent(4250) == 100
    assert voltage_to_percent(4203) == 100
    assert voltage_to_percent(3800) == 50
    assert voltage_to_percent(3725) == 35
    assert voltage_to_percent(3200) == 0
