"""Ícone na bandeja com a bateria do G435. Rode com pythonw para não abrir console."""
import datetime
import json
import os
import sys
import threading
import time
import winreg

import pystray
from PIL import Image, ImageDraw, ImageFont

from dongle import Dongle, DongleError, find_path
from protocol import parse_status, voltage_to_percent

APP = 'g435-battery'
DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], APP)
STATE_FILE = os.path.join(DATA_DIR, 'state.json')
EVENTS_LOG = os.path.join(DATA_DIR, 'events.log')
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
LOW = 20
POLL_SECONDS = 300
# o headset leva alguns segundos para aceitar comandos depois de conectar
RECONNECT_DELAY = 5

os.makedirs(DATA_DIR, exist_ok=True)


def load_state():
    empty = {'battery': None, 'mv': None, 'updated': None}
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            state = json.load(f)
    except (OSError, ValueError):
        return empty
    # versões antigas gravavam um byte de status que não era a bateria
    return state if state.get('mv') else empty


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f)


def log_event(line):
    stamp = datetime.datetime.now().isoformat(timespec='seconds')
    with open(EVENTS_LOG, 'a', encoding='utf-8') as f:
        f.write(f'{stamp} {line}\n')


def make_icon(text, color):
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 8, 63, 56), radius=10, fill=color)
    size = 40 if len(text) <= 2 else 30
    try:
        font = ImageFont.truetype('arialbd.ttf', size)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 32), text, font=font, fill='white', anchor='mm')
    return img


class App:
    def __init__(self):
        self.state = load_state()
        self.connected = False
        self.dongle = False
        self.warned = False
        self.next_poll = 0.0
        self.icon = pystray.Icon(APP, make_icon('?', 'gray'), 'G435', menu=pystray.Menu(
            pystray.MenuItem(lambda _: self.describe(), None, enabled=False),
            pystray.MenuItem('Atualizar agora', self.poll_now),
            pystray.MenuItem('Iniciar com o Windows', self.toggle_autostart,
                             checked=lambda _: autostart_enabled()),
            pystray.MenuItem('Sair', lambda: self.icon.stop()),
        ))

    def describe(self):
        b, upd = self.state['battery'], self.state['updated']
        if not self.dongle:
            head = 'Dongle não encontrado'
        elif self.connected:
            head = 'Conectado'
        else:
            head = 'Headset desligado'
        if b is None:
            return f'{head} · bateria ainda não lida'
        return f'{head} · {b}% · {self.state["mv"] / 1000:.2f} V (lido {upd})'

    def refresh(self):
        b = self.state['battery']
        if b is None:
            text, color = '?', 'gray'
        else:
            text = str(b)
            color = '#2e7d32' if b > 50 else '#f9a825' if b > LOW else '#c62828'
            if not self.connected:
                color = 'gray'
        self.icon.icon = make_icon(text, color)
        self.icon.title = 'G435: ' + self.describe()
        self.icon.update_menu()

    def on_frame(self, frame):
        st = parse_status(frame)
        if st is None or st.connected == self.connected:
            return
        log_event(f'connected={int(st.connected)}')
        self.connected = st.connected
        if st.connected:
            self.next_poll = time.time() + RECONNECT_DELAY
        self.refresh()

    def on_battery(self, mv):
        pct = voltage_to_percent(mv)
        log_event(f'battery_mv={mv} battery={pct}')
        self.state = {'battery': pct, 'mv': mv,
                      'updated': datetime.datetime.now().strftime('%d/%m %H:%M')}
        save_state(self.state)
        if pct <= LOW and not self.warned:
            self.icon.notify(f'Bateria em {pct}%', 'G435')
            self.warned = True
        elif pct > LOW:
            self.warned = False
        self.refresh()

    def poll_now(self):
        self.next_poll = 0.0

    def poll_battery(self, dongle):
        self.next_poll = time.time() + POLL_SECONDS
        try:
            self.connected = dongle.headset_linked()
            if self.connected:
                self.on_battery(dongle.read_battery_mv())
            else:
                self.refresh()
        except DongleError as e:
            log_event(f'erro: {e}')

    def reader(self):
        while True:
            path = find_path()
            if not path:
                if self.dongle:
                    self.dongle = self.connected = False
                    self.refresh()
                time.sleep(5)
                continue
            dongle = None
            try:
                dongle = Dongle(path, on_frame=self.on_frame)
                self.dongle = True
                self.refresh()
                while True:
                    if time.time() >= self.next_poll:
                        self.poll_battery(dongle)
                    dongle.poll(1000)
            except OSError as e:
                log_event(f'dongle: {e}')
                time.sleep(2)
            finally:
                if dongle:
                    dongle.close()

    def toggle_autostart(self):
        set_autostart(not autostart_enabled())

    def run(self):
        threading.Thread(target=self.reader, daemon=True).start()
        self.icon.run(setup=lambda icon: (setattr(icon, 'visible', True), self.refresh()))


def autostart_command():
    pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP)
            return True
    except OSError:
        return False


def set_autostart(enable):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enable:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, autostart_command())
        else:
            winreg.DeleteValue(k, APP)


if __name__ == '__main__':
    App().run()
