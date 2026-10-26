# g435-battery

Windows tray icon that shows the battery level of the **Logitech G435 LIGHTSPEED** headset, which Logitech G HUB does not support.

> 🇧🇷 [Resumo em português](#português) no fim da página.

## Supported hardware

| Receiver | USB ID | Radio bridge | Status |
|---|---|---|---|
| G435 LIGHTSPEED (newer revision) | `046D:0ADF` | Holtek | ✅ tested (bridge firmware `V1.8.5.1`) |
| G435 LIGHTSPEED (original) | `046D:0ACB` | Realtek | ❌ different protocol, not supported |

To check which one you have: Device Manager → *Sound, video and game controllers* → *G435 Wireless Gaming Headset* → Properties → Details → Hardware IDs. Look for `PID_0ADF`.

If you have the `0ACB` receiver, or another firmware version, an issue with your IDs is welcome, but the app will not try to talk to it.

## What it does

- Asks the headset for its battery voltage every 5 minutes, and right after it reconnects.
- Shows the percentage in the tray icon (green / yellow / red, gray when the headset is off).
- Tooltip shows percentage, voltage and the time of the last reading.
- Notification when the battery reaches 20%.
- Right-click menu (in Portuguese): *Atualizar agora* (refresh now), *Iniciar com o Windows* (start with Windows), *Sair* (quit).

The **voltage is exact**. The **percentage is an estimate** from a generic 3.7 V lithium cell curve, not a Logitech table, so it can be off by a few points, especially mid-charge or while the USB cable is plugged in.

## Install

Requires Windows 10/11 and Python 3.10+.

```
git clone https://github.com/DsGrilo/g435-battery.git
cd g435-battery
pip install -r requirements.txt
pythonw g435_tray.py
```

`pythonw` runs it without a console window. To start it with Windows, right-click the tray icon and check *Iniciar com o Windows* (this adds an entry to `HKCU\...\Run`; uncheck to remove it).

Logs and the last reading are kept in `%LOCALAPPDATA%\g435-battery\`.

Tests for the protocol parser:

```
python -m pytest
```

## How it works

The receiver exposes a vendor HID interface (usage page `0xFF00`, 64-byte reports, no report ID). Commands are wrapped by the Holtek USB bridge:

```
00 | hid_cmd | len | crc16 lo | crc16 hi | data (60 bytes)      CRC-16/XMODEM, crc field zeroed
```

`hid_cmd 0x80` carries a command for the radio chip (`'P' 'A' …`). Replies and events come back as input reports containing `'P' 'I' …` frames. A battery reading is:

1. disable the bridge power saving (`0x85 01`), as the official tool does on every connection;
2. switch the receiver to remote mode (`E1 01`) so commands are forwarded to the headset;
3. send OTA command `0x31` (get battery) and read a little-endian `u16` in millivolts;
4. switch back to local mode (`E1 00`).

Details are in the docstring of [`protocol.py`](protocol.py).

The protocol was worked out by listening to the receiver and by studying how Logitech's official G435 firmware update tool talks to it. No Logitech code or binaries are included in this repository.

## ⚠️ Caveats

- Tested on a single receiver and headset. Use at your own risk.
- The app only sends the read commands listed above, and nothing it does is written to flash: unplugging the receiver resets it.
- The same bridge also accepts **dangerous commands** (enter DFU/firmware update mode, change the USB VID/PID). If you modify the code, do not send commands you have not identified first; a wrong one can leave the receiver unusable.
- Not tested: whether the mode switch every 5 minutes causes an audible glitch on every setup. If it does for you, increase `POLL_SECONDS` in `g435_tray.py`.

This project is not affiliated with or endorsed by Logitech. Logitech, G435 and LIGHTSPEED are trademarks of Logitech.

## Português

Ícone na bandeja do Windows com a bateria do **Logitech G435 LIGHTSPEED**, que o G HUB não suporta.

- Funciona com o receptor **`046D:0ADF`** (ponte Holtek). O receptor original `046D:0ACB` (Realtek) **não** é suportado.
- Pergunta a tensão da bateria ao fone a cada 5 minutos; a tensão é exata, a porcentagem é estimada.
- Instalação: `pip install -r requirements.txt` e `pythonw g435_tray.py`. Clique direito no ícone para iniciar com o Windows.
- O app só usa comandos de leitura e não grava nada na memória do dongle. A ponte também aceita comandos perigosos (modo DFU, troca de VID/PID): se for alterar o código, não mande comandos que você não identificou.
- Projeto não oficial, sem relação com a Logitech.

## License

[MIT](LICENSE)
