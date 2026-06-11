#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║  WorkCountdown v1.2 — Виджет рабочего дня               ║
║  Windows 10/11 | Python 3.8+                            ║
║  Новое: RGB-пикер, resize, все мониторы,                ║
║          минималистичный прозрачный режим               ║
╚══════════════════════════════════════════════════════════╝
Зависимости: только стандартная библиотека Python
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json, os, sys, datetime, random, math, time, colorsys, ctypes

try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

# ══════════════════════════════════════════════════════════════ КОНСТАНТЫ ══════

APP_NAME = "WorkCountdown"
APP_VER  = "1.2.0"
CFG_FILE = os.path.join(os.path.expanduser("~"), ".workcountdown.json")
TKEY     = "#010101"   # цвет → прозрачность (minimalist mode)

DAYS_RU  = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
DAY_MOOD = ["😤","😐","😑","🙂","🎉","😎","😎"]

DEF_CFG = {
    "work_start":   "09:00",
    "work_end_wd":  "18:00",
    "work_end_fr":  "17:00",
    "custom_start": None, "custom_end": None, "custom_date": None,
    "pos_x": 60,  "pos_y": 60,
    "win_w": 286,
    "opacity":      0.92,
    "theme":        "dark",
    "always_on_top":False,
    "color_bg":     None,     # кастомный цвет фона (hex или None → тема)
    "color_timer":  None,     # кастомный цвет таймера (hex или None → тема)
    "minimalist":   False,    # прозрачный режим только с таймером
}

THEMES = {
    "dark": dict(
        bg="#0d0d1a", hdr="#13132a", dim="#606090",
        accent="#7c6aff", warn="#ff6b6b", ok="#4ecdc4",
        bar_bg="#1e1e38", border="#2a2a4a",
    ),
    "light": dict(
        bg="#f0f2ff", hdr="#e0e4ff", dim="#8080b0",
        accent="#5040d0", warn="#cc4422", ok="#007a6e",
        bar_bg="#d0d4f0", border="#c0c4e8",
    ),
}

FW_COLORS = [
    "#ff6b6b","#ffd93d","#6bcb77","#4d96ff",
    "#ff6bd6","#c7f464","#ff9a3c","#a29bfe",
    "#f72585","#7209b7","#3a86ff","#80ffdb",
]

def get_theme(cfg):
    """Тема + кастомные цвета из конфига."""
    t = dict(THEMES[cfg.get("theme", "dark")])
    t["bar_fg"] = t["accent"]
    if cfg.get("color_bg"):
        t["bg"]  = cfg["color_bg"]
        t["hdr"] = cfg["color_bg"]
    if cfg.get("color_timer"):
        t["accent"] = cfg["color_timer"]
        t["bar_fg"] = cfg["color_timer"]
    return t

# ══════════════════════════════════════════════════════════════ КОНФИГ ══════════

def load_cfg():
    try:
        if os.path.exists(CFG_FILE):
            data = json.loads(open(CFG_FILE, encoding="utf-8").read())
            for k, v in DEF_CFG.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        print(f"[cfg] load: {e}")
    return dict(DEF_CFG)

def save_cfg(cfg):
    try:
        open(CFG_FILE, "w", encoding="utf-8").write(
            json.dumps(cfg, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfg] save: {e}")

# ══════════════════════════════════════════════════════════════ АВТОЗАПУСК ══════

def _run_cmd():
    if getattr(sys, "frozen", False): return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def autostart_get():
    if not WINDOWS: return False
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        try: winreg.QueryValueEx(k, APP_NAME); return True
        except FileNotFoundError: return False
        finally: winreg.CloseKey(k)
    except: return False

def autostart_set(on):
    if not WINDOWS: return
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if on: winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _run_cmd())
        else:
            try: winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError: pass
        winreg.CloseKey(k)
    except Exception as e: print(f"[autostart] {e}")

# ══════════════════════════════════════════════════════════════ МОНИТОРЫ ════════

def get_all_monitors():
    """Возвращает список (x, y, w, h) для КАЖДОГО подключённого монитора."""
    if not WINDOWS:
        try:
            r = tk.Tk(); r.withdraw()
            w, h = r.winfo_screenwidth(), r.winfo_screenheight()
            r.destroy()
        except: w, h = 1920, 1080
        return [(0, 0, w, h)]

    monitors = []

    class RECT(ctypes.Structure):
        _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                    ("right",ctypes.c_long),("bottom",ctypes.c_long)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize",ctypes.c_ulong),("rcMonitor",RECT),
                    ("rcWork",RECT),("dwFlags",ctypes.c_ulong)]

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(RECT), ctypes.c_long)

    def _cb(hMon, hDC, lpRC, data):
        info = MONITORINFO(); info.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hMon, ctypes.byref(info))
        r = info.rcMonitor
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
    except Exception as e:
        print(f"[monitors] {e}")

    return monitors or [(0, 0, 1920, 1080)]

# ══════════════════════════════════════════════════════════════ ВРЕМЯ ═══════════

def parse_t(s): h, m = map(int, s.strip().split(":")); return h, m

def valid_t(s):
    try: h, m = parse_t(s); return 0 <= h <= 23 and 0 <= m <= 59
    except: return False

def schedule(cfg):
    now = datetime.datetime.now(); today = now.strftime("%Y-%m-%d")
    if (cfg.get("custom_date") == today
            and cfg.get("custom_start") and cfg.get("custom_end")):
        sh, sm = parse_t(cfg["custom_start"]); eh, em = parse_t(cfg["custom_end"])
    else:
        sh, sm = parse_t(cfg["work_start"])
        key = "work_end_fr" if now.weekday() == 4 else "work_end_wd"
        eh, em = parse_t(cfg[key])
    s = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    e = now.replace(hour=eh, minute=em, second=0, microsecond=0)
    return s, e

def tick_state(cfg):
    now = datetime.datetime.now(); s, e = schedule(cfg)
    total = max(1, (e - s).total_seconds())
    if now < s: return "before", int((e - now).total_seconds()), 0.0, e
    if now >= e: return "done",  0,                              1.0, e
    rem  = (e - now).total_seconds()
    prog = (now - s).total_seconds() / total
    return "working", int(rem), prog, e

def fmt(secs):
    h = secs // 3600; m = (secs % 3600) // 60; s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ══════════════════════════════════════════════════════════════ ФЕЙЕРВЕРКИ ══════

class Ptcl:
    __slots__ = ("x","y","vx","vy","col","life","dec","sz")
    def __init__(self, x, y, col):
        a = random.uniform(0, 2 * math.pi); sp = random.uniform(3, 9)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
        self.col = col; self.life = 1.0
        self.dec = random.uniform(0.010, 0.028)
        self.sz  = random.uniform(2, 5)

class FWWindow(tk.Toplevel):
    """Полноэкранная анимация на указанном мониторе."""
    DURATION = 9.0; FPS = 30

    def __init__(self, parent, mx=0, my=0, mw=None, mh=None):
        super().__init__(parent)
        sw = mw or self.winfo_screenwidth()
        sh = mh or self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+{mx}+{my}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.93)
        self.sw, self.sh = sw, sh

        cv = tk.Canvas(self, width=sw, height=sh, bg="black", highlightthickness=0)
        cv.pack(); self.cv = cv

        cx, cy = sw // 2, sh // 2
        # Текст с тенью
        cv.create_text(cx+3, cy-52, text="🎉  СВОБОДА!  🎉",
                       font=("Segoe UI", 60, "bold"), fill="#2a1a00")
        cv.create_text(cx,   cy-55, text="🎉  СВОБОДА!  🎉",
                       font=("Segoe UI", 60, "bold"), fill="#ffd93d")
        cv.create_text(cx+2, cy+12, text="Рабочий день окончен!",
                       font=("Segoe UI", 28), fill="#001a1a")
        cv.create_text(cx,   cy+10, text="Рабочий день окончен!",
                       font=("Segoe UI", 28), fill="#ffffff")
        cv.create_text(cx,   cy+58, text="[ клик / Esc — закрыть ]",
                       font=("Segoe UI", 12), fill="#444444")

        self.pts = []; self.alive = True; self.t0 = time.time()
        cv.bind("<Button-1>", lambda _: self._bye())
        cv.bind("<Button-3>", lambda _: self._bye())
        self.bind("<Escape>", lambda _: self._bye())
        self._frame()

    def _spawn(self):
        x = random.randint(80, self.sw - 80)
        y = random.randint(50, self.sh // 2 - 40)
        c = random.choice(FW_COLORS); n = random.randint(55, 85)
        self.pts += [Ptcl(x, y, c) for _ in range(n)]

    def _frame(self):
        if not self.alive or time.time() - self.t0 > self.DURATION:
            self._bye(); return
        if random.random() < 0.20: self._spawn()
        cv = self.cv; cv.delete("p"); live = []
        for p in self.pts:
            p.x += p.vx; p.y += p.vy; p.vy += 0.18; p.life -= p.dec
            if p.life <= 0: continue
            live.append(p)
            r = min(255, int(int(p.col[1:3], 16) * p.life))
            g = min(255, int(int(p.col[3:5], 16) * p.life))
            b = min(255, int(int(p.col[5:7], 16) * p.life))
            col = f"#{r:02x}{g:02x}{b:02x}"; sz = p.sz * p.life
            cv.create_oval(p.x-sz, p.y-sz, p.x+sz, p.y+sz,
                           fill=col, outline="", tags="p")
        self.pts = live; self.after(1000 // self.FPS, self._frame)

    def _bye(self): self.alive = False; self.destroy()

def show_fireworks_all(parent):
    """Запускает фейерверки на каждом подключённом мониторе."""
    for (mx, my, mw, mh) in get_all_monitors():
        try: FWWindow(parent, mx, my, mw, mh)
        except Exception as e: print(f"[fw] {mx},{my}: {e}")

# ══════════════════════════════════════════════════════════════ RGB ПИКЕР ═══════

class ColorPickerDialog(tk.Toplevel):
    """
    HSV colour picker:
      • Кольцо оттенков (Hue wheel, 360 секторов)
      • Квадрат насыщенности / яркости (SV grid, 22×22 ячейки)
      • HEX-ввод + RGB-readout + превью
    """
    WHL_CS  = 210   # размер canvas кольца (px)
    WHL_OUT = 95    # внешний радиус кольца
    WHL_IN  = 65    # внутренний радиус (ширина полосы)
    SV_N    = 22    # ячеек SV-сетки (N×N)
    SV_CS   = 132   # размер canvas сетки (каждая ячейка = SV_CS // SV_N)

    def __init__(self, parent, initial="#7c6aff", label="", callback=None):
        super().__init__(parent)
        self.callback = callback
        # Начальный цвет → HSV
        r,g,b = int(initial[1:3],16)/255, int(initial[3:5],16)/255, int(initial[5:7],16)/255
        self._h, self._s, self._v = colorsys.rgb_to_hsv(r, g, b)
        self._hex = initial

        self.title(f"🎨  Цвет: {label}")
        self.resizable(False, False)
        self.configure(bg="#111120")
        self.attributes("-topmost", True)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = self.winfo_reqwidth(),    self.winfo_reqheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        bg = "#111120"
        out = tk.Frame(self, bg=bg); out.pack(padx=14, pady=14)

        # ── Верхний ряд: кольцо (лево) + SV-квадрат (право) ──
        top = tk.Frame(out, bg=bg); top.pack()

        lf = tk.Frame(top, bg=bg); lf.pack(side=tk.LEFT, padx=(0,12))
        self._cv_whl = tk.Canvas(lf, width=self.WHL_CS, height=self.WHL_CS,
                                  bg=bg, highlightthickness=0)
        self._cv_whl.pack()
        tk.Label(lf, text="← Тон (Hue) →", bg=bg, fg="#404060",
                 font=("Segoe UI", 8)).pack(pady=(4,0))

        rf = tk.Frame(top, bg=bg); rf.pack(side=tk.LEFT)
        self._cv_sv = tk.Canvas(rf, width=self.SV_CS, height=self.SV_CS,
                                 bg=bg, highlightthickness=1,
                                 highlightbackground="#2a2a50")
        self._cv_sv.pack()
        tk.Label(rf, text="↔ Насыщенность  ↕ Яркость",
                 bg=bg, fg="#404060", font=("Segoe UI", 8)).pack(pady=(4,0))

        # ── Превью + HEX ──
        pv = tk.Frame(out, bg=bg); pv.pack(fill=tk.X, pady=(12,0))
        self._prev = tk.Label(pv, bg=self._hex, width=5, height=2, relief=tk.FLAT)
        self._prev.pack(side=tk.LEFT, padx=(0,10))
        tk.Label(pv, text="HEX:", bg=bg, fg="#606090",
                 font=("Segoe UI",9)).pack(side=tk.LEFT)
        self._hex_var = tk.StringVar(value=self._hex.upper())
        e = ttk.Entry(pv, textvariable=self._hex_var, width=9, font=("Consolas",10))
        e.pack(side=tk.LEFT, padx=4)
        e.bind("<Return>",   self._hex_entered)
        e.bind("<FocusOut>", self._hex_entered)
        self._rgb_lbl = tk.Label(pv, text="", bg=bg, fg="#606090", font=("Segoe UI",8))
        self._rgb_lbl.pack(side=tk.LEFT, padx=8)

        # ── Кнопки ──
        bf = tk.Frame(out, bg=bg); bf.pack(fill=tk.X, pady=(12,0))
        ttk.Button(bf, text="✖  Отмена",    command=self.destroy).pack(side=tk.RIGHT, padx=(4,0))
        ttk.Button(bf, text="✔  Применить", command=self._apply).pack(side=tk.RIGHT)

        # ── Биндинги ──
        self._cv_whl.bind("<Button-1>",  self._whl_event)
        self._cv_whl.bind("<B1-Motion>", self._whl_event)
        self._cv_sv.bind("<Button-1>",   self._sv_event)
        self._cv_sv.bind("<B1-Motion>",  self._sv_event)

        self._draw_wheel(); self._draw_sv(); self._update_preview()

    # ── Hue Wheel ──────────────────────────────────────────────────────────────

    def _draw_wheel(self):
        cv = self._cv_whl; cv.delete("all")
        cs = self.WHL_CS; cx = cy = cs // 2
        ro = self.WHL_OUT; ri = self.WHL_IN; bg = "#111120"

        # 360 pie-секторов → кольцо оттенков
        # Красный (hue=0) сверху (90°), идём по часовой стрелке
        for i in range(360):
            r, g, b = colorsys.hsv_to_rgb(i / 360.0, 1.0, 1.0)
            col = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            cv.create_arc(cx-ro, cy-ro, cx+ro, cy+ro,
                          start=90-i, extent=-1.5,
                          fill=col, outline=col, style=tk.PIESLICE)

        # Перекрываем центр → создаём кольцо
        cv.create_oval(cx-ri, cy-ri, cx+ri, cy+ri, fill=bg, outline=bg)

        # Индикатор текущего тона
        ang = math.radians(90 - self._h * 360)
        mid = (ri + ro) / 2
        mx = cx + mid * math.cos(ang)
        my = cy - mid * math.sin(ang)
        cv.create_oval(mx-7, my-7, mx+7, my+7, outline="white", width=2)
        cv.create_oval(mx-5, my-5, mx+5, my+5, outline="black",  width=1)

    def _whl_event(self, e):
        cs = self.WHL_CS; cx = cy = cs // 2
        dx, dy = e.x - cx, e.y - cy
        dist = math.hypot(dx, dy)
        # Зона реакции чуть шире кольца для удобства
        if self.WHL_IN - 8 <= dist <= self.WHL_OUT + 10:
            angle = math.degrees(math.atan2(dy, dx))
            # atan2: верх = -90°, правый = 0°. Конвертируем: верх = hue 0, CW
            self._h = ((90 - angle) % 360) / 360
            self._draw_wheel(); self._draw_sv(); self._update_preview()

    # ── SV Grid ────────────────────────────────────────────────────────────────

    def _draw_sv(self):
        cv = self._cv_sv; cv.delete("all")
        N = self.SV_N; cs = self.SV_CS
        cw = cs / N; ch = cs / N

        for si in range(N):
            for vi in range(N):
                s = si / N; v = 1.0 - vi / N
                r, g, b = colorsys.hsv_to_rgb(self._h, s, v)
                col = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                x1, y1 = si * cw, vi * ch
                cv.create_rectangle(x1, y1, x1+cw+1, y1+ch+1, fill=col, outline="")

        # Индикатор текущего S/V
        px = max(5, min(cs-5, int(self._s * cs)))
        py = max(5, min(cs-5, int((1.0 - self._v) * cs)))
        cv.create_oval(px-7, py-7, px+7, py+7, outline="white", width=2)
        cv.create_oval(px-5, py-5, px+5, py+5, outline="black",  width=1)

    def _sv_event(self, e):
        cs = self.SV_CS
        self._s = max(0.0, min(1.0, e.x / cs))
        self._v = max(0.0, min(1.0, 1.0 - e.y / cs))
        self._draw_sv(); self._update_preview()

    # ── Preview / HEX ──────────────────────────────────────────────────────────

    def _update_preview(self):
        r, g, b = colorsys.hsv_to_rgb(self._h, self._s, self._v)
        ri, gi, bi = int(r*255), int(g*255), int(b*255)
        self._hex = f"#{ri:02x}{gi:02x}{bi:02x}"
        self._hex_var.set(self._hex.upper())
        self._prev.config(bg=self._hex)
        self._rgb_lbl.config(text=f"R {ri}  G {gi}  B {bi}")

    def _hex_entered(self, e=None):
        val = self._hex_var.get().strip().lstrip("#")
        if len(val) == 6:
            try:
                r,g,b = int(val[:2],16)/255, int(val[2:4],16)/255, int(val[4:],16)/255
                self._h, self._s, self._v = colorsys.rgb_to_hsv(r, g, b)
                self._draw_wheel(); self._draw_sv(); self._update_preview()
            except ValueError: pass

    def _apply(self):
        if self.callback: self.callback(self._hex)
        self.destroy()

# ══════════════════════════════════════════════════════════════ НАСТРОЙКИ ════════

class SettingsWin(tk.Toplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.cfg = dict(cfg); self.on_save = on_save
        t = get_theme(cfg); self.t = t
        self.title("⚙️  Настройки WorkCountdown")
        self.resizable(False, False)
        self.configure(bg=t["bg"])
        self.attributes("-topmost", True)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = 400; h = self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _lf(self, p, txt):
        return tk.LabelFrame(p, text=f"  {txt}  ",
                             bg=self.t["bg"], fg=self.t["dim"],
                             font=("Segoe UI",9,"bold"), bd=1, relief=tk.GROOVE)

    def _row(self, p, lbl, var, width=9):
        f = tk.Frame(p, bg=self.t["bg"]); f.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f, text=lbl, bg=self.t["bg"], fg=self.t["dim"],
                 font=("Segoe UI",9), anchor="w").pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=var, width=width).pack(side=tk.RIGHT)

    def _color_row(self, parent, label, cfg_key):
        """Строка выбора цвета: метка + свотч + кнопка сброса."""
        t = self.t
        theme_name = self.cfg.get("theme", "dark")
        # Дефолтный цвет из темы
        def_col = THEMES[theme_name]["bg"] if cfg_key == "color_bg" \
                  else THEMES[theme_name]["accent"]
        cur = self.cfg.get(cfg_key) or def_col

        f = tk.Frame(parent, bg=t["bg"]); f.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f, text=label, bg=t["bg"], fg=t["dim"],
                 font=("Segoe UI",9), anchor="w").pack(side=tk.LEFT)

        reset_lbl = tk.Label(f, text=" ↩ сброс", bg=t["bg"], fg=t["dim"],
                              font=("Segoe UI",8), cursor="hand2")
        reset_lbl.pack(side=tk.RIGHT)
        swatch = tk.Label(f, bg=cur, width=7, height=1, cursor="hand2")
        swatch.pack(side=tk.RIGHT, padx=(6, 0))

        def open_picker():
            c = self.cfg.get(cfg_key) or def_col
            ColorPickerDialog(self, initial=c, label=label,
                              callback=lambda h: _on_pick(h))

        def _on_pick(h):
            self.cfg[cfg_key] = h
            swatch.config(bg=h)

        def _reset():
            self.cfg[cfg_key] = None
            swatch.config(bg=def_col)

        swatch.bind("<Button-1>", lambda e: open_picker())
        reset_lbl.bind("<Button-1>", lambda e: _reset())
        reset_lbl.bind("<Enter>", lambda e: reset_lbl.config(fg="#ff6b6b"))
        reset_lbl.bind("<Leave>", lambda e: reset_lbl.config(fg=t["dim"]))

    def _build(self):
        t = self.t
        out = tk.Frame(self, bg=t["bg"]); out.pack(padx=14, pady=14, fill=tk.BOTH, expand=True)

        # ── Расписание ──────────────────────────────────────────────────────
        lf1 = self._lf(out, "🕐 Стандартное расписание"); lf1.pack(fill=tk.X, pady=(0,8))
        self.v_start = tk.StringVar(value=self.cfg["work_start"])
        self.v_wd    = tk.StringVar(value=self.cfg["work_end_wd"])
        self.v_fr    = tk.StringVar(value=self.cfg["work_end_fr"])
        self._row(lf1, "Начало (пн–вс):",  self.v_start)
        self._row(lf1, "Конец (пн–чт):",   self.v_wd)
        self._row(lf1, "Конец (пятница):", self.v_fr)
        tk.Label(lf1, bg=t["bg"], fg=t["dim"], font=("Segoe UI",8),
                 text="  Время московское. Формат: ЧЧ:ММ").pack(anchor="w",padx=6,pady=(0,5))

        # ── Кастомный день ──────────────────────────────────────────────────
        lf2 = self._lf(out, "📅 Сегодня опоздал?"); lf2.pack(fill=tk.X, pady=(0,8))
        tk.Label(lf2, bg=t["bg"], fg=t["dim"], font=("Segoe UI",8),
                 text="  Применяется только на сегодня. Пусто = стандартное.").pack(
                 anchor="w",padx=6,pady=(4,0))
        today    = datetime.datetime.now().strftime("%Y-%m-%d")
        is_today = self.cfg.get("custom_date") == today
        cs = (self.cfg.get("custom_start") or "") if is_today else ""
        ce = (self.cfg.get("custom_end")   or "") if is_today else ""
        self.v_cs = tk.StringVar(value=cs); self.v_ce = tk.StringVar(value=ce)
        self._row(lf2, "Начало сегодня:", self.v_cs)
        self._row(lf2, "Конец сегодня:",  self.v_ce)
        tk.Label(lf2, bg=t["bg"], fg=t["dim"], font=("Segoe UI",8),
                 text="  Например: 09:35  →  18:30").pack(anchor="w",padx=6,pady=(0,5))

        # ── Цвета ───────────────────────────────────────────────────────────
        lf3 = self._lf(out, "🎨 Цвета и внешний вид"); lf3.pack(fill=tk.X, pady=(0,8))

        fr_th = tk.Frame(lf3, bg=t["bg"]); fr_th.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(fr_th, text="Тема:", bg=t["bg"], fg=t["dim"],
                 font=("Segoe UI",9)).pack(side=tk.LEFT)
        self.v_theme = tk.StringVar(value=self.cfg["theme"])
        ttk.Combobox(fr_th, textvariable=self.v_theme, values=["dark","light"],
                     width=8, state="readonly").pack(side=tk.RIGHT)

        self._color_row(lf3, "Цвет фона:", "color_bg")
        self._color_row(lf3, "Цвет таймера:", "color_timer")

        fr_o = tk.Frame(lf3, bg=t["bg"]); fr_o.pack(fill=tk.X, padx=10, pady=(0,6))
        tk.Label(fr_o, text="Прозрачность:", bg=t["bg"], fg=t["dim"],
                 font=("Segoe UI",9)).pack(side=tk.LEFT)
        self.v_opac = tk.DoubleVar(value=self.cfg["opacity"])
        ttk.Scale(fr_o, from_=0.3, to=1.0, variable=self.v_opac,
                  orient=tk.HORIZONTAL, length=110).pack(side=tk.RIGHT)

        # ── Система ─────────────────────────────────────────────────────────
        lf4 = self._lf(out, "⚡ Система"); lf4.pack(fill=tk.X, pady=(0,10))
        self.v_top  = tk.BooleanVar(value=self.cfg.get("always_on_top", False))
        self.v_mini = tk.BooleanVar(value=self.cfg.get("minimalist", False))
        self.v_auto = tk.BooleanVar(value=autostart_get())

        ttk.Checkbutton(lf4, text="Поверх всех окон",
                        variable=self.v_top).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(lf4,
                        text="Минималистичный режим  (прозрачный фон, только таймер)",
                        variable=self.v_mini).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(lf4, text="Автозапуск при старте Windows",
                        variable=self.v_auto).pack(anchor="w", padx=10, pady=(0,6))

        if not WINDOWS:
            tk.Label(lf4, bg=t["bg"], fg=t["dim"], font=("Segoe UI",8),
                     text="  (автозапуск и прозрачность — только Windows)").pack(
                     anchor="w", padx=10, pady=(0,4))

        # ── Кнопки ──────────────────────────────────────────────────────────
        bf = tk.Frame(out, bg=t["bg"]); bf.pack(fill=tk.X)
        ttk.Button(bf, text="✖  Отмена",    command=self.destroy).pack(side=tk.RIGHT, padx=(4,0))
        ttk.Button(bf, text="💾  Сохранить", command=self._save).pack(side=tk.RIGHT)

    def _save(self):
        for var, name in [(self.v_start,"Начало"),(self.v_wd,"Конец Пн–Чт"),(self.v_fr,"Конец Пт")]:
            if not valid_t(var.get()):
                messagebox.showerror("Ошибка",f"Неверный формат «{name}»: {var.get()!r}",parent=self)
                return
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cs, ce = self.v_cs.get().strip(), self.v_ce.get().strip()
        if cs or ce:
            if not (valid_t(cs) and valid_t(ce)):
                messagebox.showerror("Ошибка","Неверный формат кастомного времени",parent=self)
                return
            self.cfg.update(custom_start=cs, custom_end=ce, custom_date=today)
        else:
            self.cfg.update(custom_start=None, custom_end=None, custom_date=None)
        self.cfg.update(
            work_start    = self.v_start.get().strip(),
            work_end_wd   = self.v_wd.get().strip(),
            work_end_fr   = self.v_fr.get().strip(),
            theme         = self.v_theme.get(),
            opacity       = round(float(self.v_opac.get()), 2),
            always_on_top = self.v_top.get(),
            minimalist    = self.v_mini.get(),
        )
        autostart_set(self.v_auto.get()); save_cfg(self.cfg)
        self.on_save(self.cfg); self.destroy()

# ══════════════════════════════════════════════════════════════ ГЛАВНЫЙ ВИДЖЕТ ══

class Widget(tk.Tk):
    MIN_W = 200; MAX_W = 900

    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self._sopen    = False
        self._fw_shown = False
        self._dx = self._dy = 0
        self._rx = self._ry = self._rw = self._rh = 0
        self._last_prog = 0.0

        self.overrideredirect(True)
        self.attributes("-topmost", self.cfg.get("always_on_top", False))
        self.attributes("-alpha",   self.cfg.get("opacity", 0.92))

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, min(self.cfg.get("pos_x", 60), sw - 300))
        y = max(0, min(self.cfg.get("pos_y", 60), sh - 200))
        self._W = max(self.MIN_W, min(self.MAX_W, self.cfg.get("win_w", 286)))
        self.geometry(f"+{x}+{y}")

        self._ui()
        self._tick()

    # ── ОБЫЧНЫЙ UI ────────────────────────────────────────────────────────────

    def _ui(self):
        for w in self.winfo_children(): w.destroy()

        # Снимаем прозрачный ключ (если выходим из мини-режима)
        if WINDOWS:
            try: self.attributes("-transparentcolor", "")
            except: pass

        if self.cfg.get("minimalist", False):
            self._ui_minimalist()
            return

        t = get_theme(self.cfg); self._t = t; W = self._W

        self.configure(bg=t["border"])
        wrap = tk.Frame(self, bg=t["bg"]); wrap.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)

        # Хедер
        hdr = tk.Frame(wrap, bg=t["hdr"], height=33); hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        hl  = tk.Label(hdr, text=f"⏱  {APP_NAME}", bg=t["hdr"], fg=t["dim"],
                        font=("Segoe UI",8,"bold"), anchor="w"); hl.pack(side=tk.LEFT, padx=10)
        for sym, hover, cmd in [("✕","#ff5555",self._close), ("⚙",t["accent"],self._open_sett)]:
            b = tk.Label(hdr, text=sym, bg=t["hdr"], fg=t["dim"],
                          font=("Segoe UI",10,"bold"), cursor="hand2", width=2)
            b.pack(side=tk.RIGHT, padx=1)
            b.bind("<Button-1>", lambda e,c=cmd: c())
            b.bind("<Enter>",    lambda e,b=b,c=hover: b.config(fg=c))
            b.bind("<Leave>",    lambda e,b=b: b.config(fg=t["dim"]))
        for w in [hdr, hl]:
            w.bind("<ButtonPress-1>",   self._ds)
            w.bind("<B1-Motion>",       self._dm)
            w.bind("<ButtonRelease-1>", self._dr)

        # Тело
        body  = tk.Frame(wrap, bg=t["bg"]); body.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(body, bg=t["bg"]); inner.pack(padx=16, pady=(10,0), fill=tk.BOTH, expand=True)

        self._ld = tk.Label(inner, text="", bg=t["bg"], fg=t["dim"],
                             font=("Segoe UI",9,"bold"), anchor="w"); self._ld.pack(fill=tk.X)

        self._bar = tk.Canvas(inner, height=6, bg=t["bar_bg"], highlightthickness=0, bd=0)
        self._bar.pack(fill=tk.X, pady=(7,2))
        self._bar.bind("<Configure>", lambda e: self._draw_bar(self._last_prog))

        self._lp = tk.Label(inner, text="—", bg=t["bg"], fg=t["dim"],
                             font=("Segoe UI",8), anchor="e"); self._lp.pack(fill=tk.X)

        # Шрифт масштабируется с шириной виджета
        font_sz = max(22, min(84, W // 6))
        self._lt = tk.Label(inner, text="00:00:00", bg=t["bg"], fg=t["accent"],
                             font=("Segoe UI", font_sz, "bold"), anchor="center")
        self._lt.pack(fill=tk.X, pady=(4,0))

        self._ls = tk.Label(inner, text="до конца рабочего дня", bg=t["bg"],
                             fg=t["dim"], font=("Segoe UI",9), anchor="center")
        self._ls.pack(fill=tk.X, pady=(0,8))

        # Resize grip
        bot = tk.Frame(wrap, bg=t["bg"], height=14); bot.pack(fill=tk.X); bot.pack_propagate(False)
        self._grip = tk.Label(bot, text="◢", bg=t["bg"], fg=t["border"],
                               font=("Segoe UI",9), cursor="size_nw_se")
        self._grip.pack(side=tk.RIGHT, padx=2)
        self._grip.bind("<ButtonPress-1>",   self._rs_start)
        self._grip.bind("<B1-Motion>",       self._rs_motion)
        self._grip.bind("<ButtonRelease-1>", self._rs_stop)
        self._grip.bind("<Enter>", lambda e: self._grip.config(fg=t["dim"]))
        self._grip.bind("<Leave>", lambda e: self._grip.config(fg=t["border"]))

        # Drag + контекстное меню
        for w in [body, inner, self._ld, self._ls, self._lp, self._lt]:
            w.bind("<ButtonPress-1>",   self._ds)
            w.bind("<B1-Motion>",       self._dm)
            w.bind("<ButtonRelease-1>", self._dr)
            w.bind("<Button-3>",        self._ctx)
        self._bar.bind("<Button-3>", self._ctx)
        self.update_idletasks()

    # ── МИНИМАЛИСТИЧНЫЙ UI ────────────────────────────────────────────────────

    def _ui_minimalist(self):
        """
        Прозрачный фон, только плавающий таймер с тенью.
        Перетаскивается за текст, ПКМ → контекстное меню.
        """
        W  = self._W
        fz = max(28, min(96, W // 5))   # шрифт масштабируется с шириной
        H  = fz * 2 + 16

        # Весь фон → прозрачный ключ
        self.configure(bg=TKEY)
        if WINDOWS:
            self.attributes("-transparentcolor", TKEY)

        cv = tk.Canvas(self, width=W, height=H, bg=TKEY, highlightthickness=0)
        cv.pack(); self._mini_cv = cv
        self._mini_W = W; self._mini_H = H; self._mini_fz = fz
        self.geometry(f"{W}x{H}")
        self._t = get_theme(self.cfg)   # нужен для _tick

        cv.bind("<ButtonPress-1>",   self._ds)
        cv.bind("<B1-Motion>",       self._dm)
        cv.bind("<ButtonRelease-1>", self._dr)
        cv.bind("<Button-3>",        self._ctx)

        self._draw_mini("00:00:00", "#888888")

    def _draw_mini(self, text, color):
        """Обновляем плавающий таймер в минималистичном режиме."""
        cv = self._mini_cv
        cx = self._mini_W // 2; cy = self._mini_H // 2
        fnt = ("Segoe UI", self._mini_fz, "bold")
        cv.delete("shadow"); cv.delete("timer_text")
        # Тень (несколько смещённых копий текста)
        for ox, oy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,-3),(0,3),(-3,0),(3,0)]:
            cv.create_text(cx+ox, cy+oy, text=text, font=fnt,
                           fill="#000030", tags="shadow")
        # Основной текст
        cv.create_text(cx, cy, text=text, font=fnt, fill=color, tags="timer_text")

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _ds(self, e): self._dx, self._dy = e.x_root-self.winfo_x(), e.y_root-self.winfo_y()
    def _dm(self, e): self.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")
    def _dr(self, e):
        self.cfg["pos_x"] = self.winfo_x(); self.cfg["pos_y"] = self.winfo_y()
        save_cfg(self.cfg)

    # ── Resize ────────────────────────────────────────────────────────────────

    def _rs_start(self, e):
        self._rx, self._ry = e.x_root, e.y_root
        self._rw, self._rh = self.winfo_width(), self.winfo_height()

    def _rs_motion(self, e):
        nw = max(self.MIN_W, min(self.MAX_W, self._rw + (e.x_root - self._rx)))
        nh = max(120,                         self._rh + (e.y_root - self._ry))
        self.geometry(f"{nw}x{nh}")

    def _rs_stop(self, e):
        self.cfg["win_w"] = self.winfo_width()
        self._W = self.cfg["win_w"]
        save_cfg(self.cfg); self._ui()   # пересчитываем шрифт под новую ширину

    # ── Контекстное меню ──────────────────────────────────────────────────────

    def _ctx(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="⚙️   Настройки", command=self._open_sett)
        m.add_separator()
        aot  = self.cfg.get("always_on_top", False)
        mini = self.cfg.get("minimalist",    False)
        m.add_command(label=f"{'✅' if aot  else '  '} Поверх всех окон",   command=self._toggle_top)
        m.add_command(label=f"{'✅' if mini else '  '} Минималистичный режим", command=self._toggle_mini)
        m.add_separator()
        m.add_command(label="🎇   Тест фейерверков (все мониторы)",
                       command=lambda: show_fireworks_all(self))
        m.add_separator()
        m.add_command(label="❌   Выход", command=self._close)
        m.tk_popup(e.x_root, e.y_root)

    def _toggle_top(self):
        self.cfg["always_on_top"] = not self.cfg.get("always_on_top", False)
        self.attributes("-topmost", self.cfg["always_on_top"]); save_cfg(self.cfg)

    def _toggle_mini(self):
        self.cfg["minimalist"] = not self.cfg.get("minimalist", False)
        save_cfg(self.cfg); self._ui()

    # ── Настройки ─────────────────────────────────────────────────────────────

    def _open_sett(self):
        if self._sopen: return
        self._sopen = True
        def on_destroy(ev):
            if str(ev.widget) == str(win): self._sopen = False
        win = SettingsWin(self, self.cfg, self._apply)
        win.bind("<Destroy>", on_destroy)

    def _apply(self, cfg):
        self.cfg = cfg; self._sopen = False; self._fw_shown = False
        self.attributes("-alpha",   cfg["opacity"])
        self.attributes("-topmost", cfg.get("always_on_top", False))
        self._W = max(self.MIN_W, min(self.MAX_W, cfg.get("win_w", 286)))
        self._ui()

    # ── Прогресс-бар ──────────────────────────────────────────────────────────

    def _draw_bar(self, progress):
        self._last_prog = progress
        if self.cfg.get("minimalist"): return
        try:
            t  = self._t; bw = self._bar.winfo_width()
            if bw < 5: return
            self._bar.delete("b")
            if progress > 0:
                fw = max(4, int(bw * progress))
                self._bar.create_rectangle(0, 0, fw, 6, fill=t["bar_fg"],
                                           outline="", tags="b")
        except tk.TclError: pass

    # ── Главный тик ───────────────────────────────────────────────────────────

    def _tick(self):
        status, rem, prog, end = tick_state(self.cfg)
        t   = self._t
        now = datetime.datetime.now()
        wd  = now.weekday()
        day = f"{DAY_MOOD[wd]} {DAYS_RU[wd]}"
        end_str   = end.strftime("%H:%M")
        is_custom = (self.cfg.get("custom_date") == now.strftime("%Y-%m-%d")
                     and bool(self.cfg.get("custom_start")))
        is_mini   = self.cfg.get("minimalist", False)

        # ── Цвет таймера ──────────────────────────────────────────────────
        if status == "before":
            t_color = t["dim"]
        elif status == "working":
            # < 30 мин — пульсация между warn и ok
            t_color = (t["warn"] if now.second % 2 == 0 else t["ok"]) if rem < 1800 else t["accent"]
        else:
            t_color = t["ok"]

        timer_text = fmt(rem) if status != "done" else "00:00:00"

        if is_mini:
            # ── Минималистичный режим ──────────────────────────────────────
            try: self._draw_mini(timer_text, t_color)
            except tk.TclError: pass
        else:
            # ── Обычный режим ─────────────────────────────────────────────
            try:
                if status == "before":
                    self._ld.config(text=f"{day}  •  с {self.cfg['work_start']}", fg=t["dim"])
                    self._lt.config(text=timer_text, fg=t["dim"])
                    self._ls.config(text="до начала рабочего дня")
                    self._lp.config(text="—")
                elif status == "working":
                    tag = "  🔧" if is_custom else ""
                    self._ld.config(text=f"{day}  •  до {end_str}{tag}", fg=t["dim"])
                    self._lp.config(text=f"{int(prog*100)}%")
                    self._ls.config(text="осталось")
                    self._lt.config(text=timer_text, fg=t_color)
                elif status == "done":
                    self._ld.config(text=f"{day}  •  СВОБОДЕН! 🍻", fg=t["ok"])
                    self._lt.config(text="00:00:00", fg=t["ok"])
                    self._ls.config(text="Рабочий день окончен!  🎉")
                    self._lp.config(text="100%")
                self._draw_bar(prog)
            except tk.TclError: pass

        # ── Фейерверки на ВСЕХ мониторах ──────────────────────────────────
        if status == "done" and not self._fw_shown:
            self._fw_shown = True
            self.after(400, lambda: show_fireworks_all(self))

        self.after(1000, self._tick)

    # ── Закрытие ──────────────────────────────────────────────────────────────

    def _close(self):
        self.cfg["pos_x"] = self.winfo_x(); self.cfg["pos_y"] = self.winfo_y()
        self.cfg["win_w"] = self.winfo_width()
        save_cfg(self.cfg); self.destroy()

# ══════════════════════════════════════════════════════════════ ENTRY POINT ═════

if __name__ == "__main__":
    app = Widget()
    app.mainloop()
