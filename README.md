# g435-battery

Windows tray icon that shows the battery level of the **Logitech G435 LIGHTSPEED** headset, which Logitech G HUB does not support.

> 🇧🇷 [Resumo em português](#português) no fim da página.

## Supported hardware

| Receiver | USB ID | Radio bridge | Status |
|---|---|---|---|
| G435 LIGHTSPEED (newer revision) | `046D:0ADF` | Holtek | ✅ tested (bridge firmware `V1.8.5.1`) |
| G435 LIGHTSPEED (original) | `046D:0ACB` | Realtek | ❌ different protocol, not supported |

### Is my receiver compatible?

Plug in the receiver and use one of these.

**Without installing anything (PowerShell):**

```powershell
Get-PnpDevice -PresentOnly | Where-Object InstanceId -match 'VID_046D&PID_0A(DF|CB)' | Select-Object -First 1 InstanceId
```

- `PID_0ADF` in the result → **compatible**.
- `PID_0ACB` → original receiver, **not supported**.
- Nothing → the receiver was not found (is it plugged in?).

The same ID is in Device Manager → *Sound, video and game controllers* → *G435 Wireless Gaming Headset* → Properties → Details → Hardware IDs.

**With the check script** (after steps 1–4 of the [step by step](#step-by-step)):

```
python check.py
```

```
COMPATIBLE: receiver 046D:0ADF (Holtek bridge), firmware V1.8.5.1.
```

It only lists USB devices and, on a compatible receiver, reads the bridge firmware version. It never switches modes or sends anything else. If your firmware differs from `V1.8.5.1` it should still work; if it doesn't, please open an issue with the script output.

## What it does

- Asks the headset for its battery voltage every 5 minutes, and right after it reconnects.
- Shows the percentage in the tray icon (green / yellow / red, gray when the headset is off).
- Tooltip shows percentage, voltage and the time of the last reading.
- Notification when the battery reaches 20%.
- Right-click menu (in Portuguese): *Atualizar agora* (refresh now), *Iniciar com o Windows* (start with Windows), *Sair* (quit).

The **voltage is exact**. The **percentage is an estimate** from a generic 3.7 V lithium cell curve, not a Logitech table, so it can be off by a few points, especially mid-charge or while the USB cable is plugged in.

## Install

Requires Windows 10/11 and Python 3.10+. G HUB is not needed.

### Step by step

**1. Install Python** (skip if `python --version` already works in a terminal)

- Download it from [python.org/downloads](https://www.python.org/downloads/) and run the installer.
- On the first screen, **check "Add python.exe to PATH"** before clicking *Install Now*.
- Or, from a terminal: `winget install Python.Python.3.12`

**2. Download this project**

- On this page, click the green **Code** button → **Download ZIP**.
- Extract it somewhere it will stay, for example `Documents\g435-battery`. Don't run it from inside the ZIP or from the Downloads folder if you plan to delete it later: the *start with Windows* option points to this folder.
- Or, with git: `git clone https://github.com/DsGrilo/g435-battery.git`

**3. Open a terminal in that folder**

- Open the folder in Explorer, click the address bar, type `cmd` and press Enter.

**4. Install the dependencies**

```
pip install -r requirements.txt
```

If `pip` is not found, use `py -m pip install -r requirements.txt`.

**5. Check that your receiver is compatible**

Plug in the receiver, turn on the headset and run:

```
python check.py
```

Continue only if it prints `COMPATIBLE`. See [Is my receiver compatible?](#is-my-receiver-compatible) for the other results.

**6. Start the app**

```
pythonw g435_tray.py
```

`pythonw` runs it without a console window, so you can close the terminal. A gray `?` icon appears in the tray (next to the clock) and turns into the battery percentage within a few seconds. If you don't see it, click the `^` arrow: Windows hides new tray icons there; you can drag it onto the taskbar.

**7. Start with Windows (optional)**

Right-click the icon → check **Iniciar com o Windows**. This adds an entry under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. If you move the folder later, uncheck and check it again.

### Updating

Download the ZIP again and extract it over the old folder (or `git pull`), then right-click the icon → **Sair** and start it again (step 6).

### Uninstalling

1. Right-click the icon → uncheck **Iniciar com o Windows** → **Sair**.
2. Delete the project folder.
3. Delete `%LOCALAPPDATA%\g435-battery\` (last reading and log).
4. Optional: `pip uninstall hidapi pystray pillow`.

### Troubleshooting

- **Icon stays gray with `?`** — the headset is off or not linked to the receiver. Turn it on and use *Atualizar agora* (refresh now).
- **The tooltip says *Dongle não encontrado*** (receiver not found) — run `python check.py`.
- **Something else** — the log is in `%LOCALAPPDATA%\g435-battery\events.log`. Please include it in an issue.

### Tests

```
pip install pytest
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
- The app only sends the commands listed above, and nothing it does is written to flash: unplugging the receiver resets it.
- The same bridge also accepts **dangerous commands** (enter DFU/firmware update mode, change the USB VID/PID). If you modify the code, do not send commands you have not identified first; a wrong one can leave the receiver unusable.
- Not tested: whether the mode switch every 5 minutes causes an audible glitch on every setup. If it does for you, increase `POLL_SECONDS` in `g435_tray.py`.

This project is not affiliated with or endorsed by Logitech. Logitech, G435 and LIGHTSPEED are trademarks of Logitech.

## Português

Ícone na bandeja do Windows com a bateria do **Logitech G435 LIGHTSPEED**, que o G HUB não suporta.

- Funciona com o receptor **`046D:0ADF`** (ponte Holtek). O receptor original `046D:0ACB` (Realtek) **não** é suportado.
- Para saber qual é o seu: rode o comando de PowerShell da seção [Is my receiver compatible?](#is-my-receiver-compatible) (`PID_0ADF` = compatível) ou `python check.py`.
- Pergunta a tensão da bateria ao fone a cada 5 minutos; a tensão é exata, a porcentagem é estimada.
- O app não grava nada na memória do dongle: só lê a bateria e troca de modo temporariamente. A ponte também aceita comandos perigosos (modo DFU, troca de VID/PID): se for alterar o código, não mande comandos que você não identificou.
- Projeto não oficial, sem relação com a Logitech.

### Passo a passo

1. **Instale o Python** em [python.org/downloads](https://www.python.org/downloads/). Na primeira tela do instalador, **marque "Add python.exe to PATH"**. Pule se `python --version` já funciona no terminal.
2. **Baixe o projeto**: botão verde **Code** → **Download ZIP**, e extraia num lugar fixo, por exemplo `Documentos\g435-battery`. A opção de iniciar com o Windows aponta para essa pasta.
3. **Abra um terminal na pasta**: no Explorer, clique na barra de endereço, digite `cmd` e aperte Enter.
4. **Instale as dependências**: `pip install -r requirements.txt` (se `pip` não for encontrado, use `py -m pip install -r requirements.txt`).
5. **Confira o receptor**: com o receptor no USB e o fone ligado, rode `python check.py`. Só continue se aparecer `COMPATIBLE`.
6. **Abra o app**: `pythonw g435_tray.py`. Pode fechar o terminal. Um ícone cinza com `?` aparece perto do relógio e vira a porcentagem em alguns segundos. Se não aparecer, clique na setinha `^`; dá para arrastar o ícone para a barra.
7. **Iniciar com o Windows (opcional)**: clique direito no ícone → marque **Iniciar com o Windows**. Se mudar a pasta de lugar, desmarque e marque de novo.

**Atualizar:** baixe o ZIP de novo e extraia por cima, depois clique direito no ícone → **Sair** e abra de novo (passo 6).

**Desinstalar:** clique direito → desmarque **Iniciar com o Windows** → **Sair**; apague a pasta do projeto e `%LOCALAPPDATA%\g435-battery\`.

**Problemas:** ícone cinza com `?` = fone desligado ou fora de alcance (use **Atualizar agora**). Para qualquer outra coisa, o log fica em `%LOCALAPPDATA%\g435-battery\events.log`; mande junto numa issue.

## License

[MIT](LICENSE)
