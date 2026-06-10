#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════╗
║   WorkCountdown v1.0 — Виджет рабочего дня       ║
║   Windows 10/11 | Python 3.8+                    ║
║   Запуск: python countdown_widget.py             ║
╚══════════════════════════════════════════════════╝
Зависимости: только стандартная библиотека Python
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json, os, sys, datetime, random, math, time

try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False  # macOS / Linux — автозапуск недоступен

# ═══════════════════════════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME  = "WorkCountdown"
APP_VER   = "1.0.0"
CFG_FILE  = os.path.join(os.path.expanduser("~"), ".workcountdown.json")
WIDGET_W  = 286

DAYS_RU  = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
DAY_MOOD = ["😤","😐","😑","🙂","🎉","😎","😎"]

DEF_CFG = {
    "work_start":    "09:00",
    "work_end_wd":   "18:00",   # Пн–Чт
    "work_end_fr":   "17:00",   # Пятница
    "custom_start":  None,
    "custom_end":    None,
    "custom_date":   None,
    "pos_x":         60,
    "pos_y":         60,
    "opacity":       0.92,
    "theme":         "dark",
    "always_on_top": False,
}

THEMES = {
    "dark": dict(
        bg="#0d0d1a", hdr="#13132a", text="#dde0ff",
        dim="#606090", accent="#7c6aff", warn="#ff6b6b",
        ok="#4ecdc4", bar_bg="#1e1e38", bar_fg="#7c6aff",
        border="#2a2a4a",
    ),
    "light": dict(
        bg="#f0f2ff", hdr="#e0e4ff", text="#1a1a40",
        dim="#8080b0", accent="#5040d0", warn="#cc4422",
        ok="#007a6e", bar_bg="#d0d4f0", bar_fg="#5040d0",
        border="#c0c4e8",
    ),
}

FW_COLORS = [
    "#ff6b6b","#ffd93d","#6bcb77","#4d96ff",
    "#ff6bd6","#c7f464","#ff9a3c","#a29bfe",
    "#f72585","#7209b7","#3a86ff","#80ffdb",
]

# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГ: ЗАГРУЗКА / СОХРАНЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

def load_cfg():
    try:
        if os.path.exists(CFG_FILE):
            data = json.loads(open(CFG_FILE, encoding="utf-8").read())
            for k, v in DEF_CFG.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        print(f"[cfg] load error: {e}")
    return dict(DEF_CFG)

def save_cfg(cfg):
    try:
        open(CFG_FILE, "w", encoding="utf-8").write(
            json.dumps(cfg, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfg] save error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# АВТОЗАПУСК (Windows Registry)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_cmd():
    """Команда для автозапуска — поддерживает и .py и скомпилированный .exe"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def autostart_get():
    if not WINDOWS:
        return False
    try:
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(k, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(k)
    except:
        return False

def autostart_set(on):
    if not WINDOWS:
        return
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE
        )
        if on:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _run_cmd())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(k)
    except Exception as e:
        print(f"[autostart] {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# ЛОГИКА ВРЕМЕНИ
# ═══════════════════════════════════════════════════════════════════════════════

def parse_t(s):
    h, m = map(int, s.strip().split(":"))
    return h, m

def valid_t(s):
    try:
        h, m = parse_t(s)
        return 0 <= h <= 23 and 0 <= m <= 59
    except:
        return False

def schedule(cfg):
    now   = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    if (cfg.get("custom_date") == today
            and cfg.get("custom_start") and cfg.get("custom_end")):
        sh, sm = parse_t(cfg["custom_start"])
        eh, em = parse_t(cfg["custom_end"])
    else:
        sh, sm = parse_t(cfg["work_start"])
        key    = "work_end_fr" if now.weekday() == 4 else "work_end_wd"
        eh, em = parse_t(cfg[key])
    s = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    e = now.replace(hour=eh, minute=em, second=0, microsecond=0)
    return s, e

def tick_state(cfg):
    """Возвращает (status, remaining_secs, progress 0..1, end_dt)"""
    now = datetime.datetime.now()
    s, e = schedule(cfg)
    total = max(1, (e - s).total_seconds())
    if now < s:
        return "before",  int((e - now).total_seconds()), 0.0,                      e
    if now >= e:
        return "done",    0,                              1.0,                       e
    rem  = (e - now).total_seconds()
    prog = (now - s).total_seconds() / total
    return "working", int(rem), prog, e

def fmt(secs):
    h = secs // 3600; m = (secs % 3600) // 60; s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ═══════════════════════════════════════════════════════════════════════════════
# ФЕЙЕРВЕРКИ
# ═══════════════════════════════════════════════════════════════════════════════

class Ptcl:
    __slots__ = ("x","y","vx","vy","col","life","dec","sz")
    def __init__(self, x, y, col):
        a      = random.uniform(0, 2 * math.pi)
        sp     = random.uniform(3, 9)
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
        self.col  = col
        self.life = 1.0
        self.dec  = random.uniform(0.010, 0.028)
        self.sz   = random.uniform(2, 5)

class FWWindow(tk.Toplevel):
    """Полноэкранная анимация фейерверков с текстом."""
    DURATION = 9.0   # секунд
    FPS      = 30

    def __init__(self, parent):
        super().__init__(parent)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.93)
        self.sw, self.sh = sw, sh

        cv = tk.Canvas(self, width=sw, height=sh, bg="black", highlightthickness=0)
        cv.pack()
        self.cv = cv

        cx, cy = sw // 2, sh // 2
        # Тень-эффект для текста
        cv.create_text(cx+3, cy-52, text="🎉  СВОБОДА!  🎉",
                       font=("Segoe UI", 60, "bold"), fill="#2a1a00")
        cv.create_text(cx, cy-55, text="🎉  СВОБОДА!  🎉",
                       font=("Segoe UI", 60, "bold"), fill="#ffd93d")
        cv.create_text(cx+2, cy+12, text="Рабочий день окончен!",
                       font=("Segoe UI", 28), fill="#001a1a")
        cv.create_text(cx, cy+10, text="Рабочий день окончен!",
                       font=("Segoe UI", 28), fill="#ffffff")
        cv.create_text(cx, cy+58, text="[ клик мышью или Esc — закрыть ]",
                       font=("Segoe UI", 12), fill="#444444")

        self.pts   = []
        self.alive = True
        self.t0    = time.time()

        cv.bind("<Button-1>", lambda _: self._bye())
        cv.bind("<Button-3>", lambda _: self._bye())
        self.bind("<Escape>", lambda _: self._bye())
        self._frame()

    def _spawn(self):
        x = random.randint(80, self.sw - 80)
        y = random.randint(50, self.sh // 2 - 40)
        c = random.choice(FW_COLORS)
        n = random.randint(55, 85)
        self.pts += [Ptcl(x, y, c) for _ in range(n)]

    def _frame(self):
        if not self.alive or time.time() - self.t0 > self.DURATION:
            self._bye()
            return
        if random.random() < 0.20:
            self._spawn()
        cv = self.cv
        cv.delete("p")
        live = []
        for p in self.pts:
            p.x  += p.vx
            p.y  += p.vy
            p.vy += 0.18       # гравитация
            p.life -= p.dec
            if p.life <= 0:
                continue
            live.append(p)
            r = min(255, int(int(p.col[1:3], 16) * p.life))
            g = min(255, int(int(p.col[3:5], 16) * p.life))
            b = min(255, int(int(p.col[5:7], 16) * p.life))
            col = f"#{r:02x}{g:02x}{b:02x}"
            sz  = p.sz * p.life
            cv.create_oval(p.x-sz, p.y-sz, p.x+sz, p.y+sz,
                           fill=col, outline="", tags="p")
        self.pts = live
        self.after(1000 // self.FPS, self._frame)

    def _bye(self):
        self.alive = False
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════════════
# ОКНО НАСТРОЕК
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsWin(tk.Toplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.cfg     = dict(cfg)
        self.on_save = on_save
        t = THEMES[cfg.get("theme", "dark")]
        self.t = t

        self.title("⚙️  Настройки WorkCountdown")
        self.resizable(False, False)
        self.configure(bg=t["bg"])
        self.attributes("-topmost", True)
        self.grab_set()

        self._build()
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = 370
        h  = self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Вспомогательные строители ─────────────────────────────────────────────

    def _lf(self, parent, title):
        return tk.LabelFrame(parent, text=f"  {title}  ",
                             bg=self.t["bg"], fg=self.t["dim"],
                             font=("Segoe UI", 9, "bold"),
                             bd=1, relief=tk.GROOVE)

    def _row(self, parent, label, var, width=9):
        f = tk.Frame(parent, bg=self.t["bg"])
        f.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f, text=label, bg=self.t["bg"], fg=self.t["dim"],
                 font=("Segoe UI", 9), anchor="w").pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=var, width=width).pack(side=tk.RIGHT)

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build(self):
        t   = self.t
        out = tk.Frame(self, bg=t["bg"])
        out.pack(padx=14, pady=14, fill=tk.BOTH, expand=True)

        # ── Стандартное расписание ──────────────────────────────────────────
        lf1 = self._lf(out, "🕐 Стандартное расписание")
        lf1.pack(fill=tk.X, pady=(0, 8))

        self.v_start = tk.StringVar(value=self.cfg["work_start"])
        self.v_wd    = tk.StringVar(value=self.cfg["work_end_wd"])
        self.v_fr    = tk.StringVar(value=self.cfg["work_end_fr"])
        self._row(lf1, "Начало рабочего дня (пн–вс):", self.v_start)
        self._row(lf1, "Конец рабочего дня (пн–чт):",  self.v_wd)
        self._row(lf1, "Конец рабочего дня (пятница):", self.v_fr)
        tk.Label(lf1, bg=t["bg"], fg=t["dim"], font=("Segoe UI", 8),
                 text="  Время московское. Формат: ЧЧ:ММ").pack(
                 anchor="w", padx=6, pady=(0, 5))

        # ── Кастомный день ──────────────────────────────────────────────────
        lf2 = self._lf(out, "📅 Опоздал? Другой график на сегодня")
        lf2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lf2, bg=t["bg"], fg=t["dim"], font=("Segoe UI", 8),
                 text="  Применяется только на сегодня. Оставь пустым чтобы сбросить.").pack(
                 anchor="w", padx=6, pady=(4, 0))
        today    = datetime.datetime.now().strftime("%Y-%m-%d")
        is_today = self.cfg.get("custom_date") == today
        cs = (self.cfg.get("custom_start") or "") if is_today else ""
        ce = (self.cfg.get("custom_end")   or "") if is_today else ""
        self.v_cs = tk.StringVar(value=cs)
        self.v_ce = tk.StringVar(value=ce)
        self._row(lf2, "Начало сегодня:", self.v_cs)
        self._row(lf2, "Конец сегодня:",  self.v_ce)
        tk.Label(lf2, bg=t["bg"], fg=t["dim"], font=("Segoe UI", 8),
                 text="  Например: 09:35 — 18:00").pack(
                 anchor="w", padx=6, pady=(0, 5))

        # ── Внешний вид ─────────────────────────────────────────────────────
        lf3 = self._lf(out, "🎨 Внешний вид")
        lf3.pack(fill=tk.X, pady=(0, 8))

        fr_t = tk.Frame(lf3, bg=t["bg"])
        fr_t.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(fr_t, text="Тема:", bg=t["bg"], fg=t["dim"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.v_theme = tk.StringVar(value=self.cfg["theme"])
        ttk.Combobox(fr_t, textvariable=self.v_theme,
                     values=["dark", "light"], width=8,
                     state="readonly").pack(side=tk.RIGHT)

        fr_o = tk.Frame(lf3, bg=t["bg"])
        fr_o.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(fr_o, text="Прозрачность:", bg=t["bg"], fg=t["dim"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.v_opac = tk.DoubleVar(value=self.cfg["opacity"])
        ttk.Scale(fr_o, from_=0.3, to=1.0, variable=self.v_opac,
                  orient=tk.HORIZONTAL, length=110).pack(side=tk.RIGHT)

        # ── Система ─────────────────────────────────────────────────────────
        lf4 = self._lf(out, "⚡ Система")
        lf4.pack(fill=tk.X, pady=(0, 10))
        self.v_top  = tk.BooleanVar(value=self.cfg.get("always_on_top", False))
        self.v_auto = tk.BooleanVar(value=autostart_get())
        ttk.Checkbutton(lf4, text="Поверх всех окон",
                        variable=self.v_top).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(lf4, text="Автозапуск при старте Windows",
                        variable=self.v_auto).pack(anchor="w", padx=10, pady=(0, 6))
        if not WINDOWS:
            tk.Label(lf4, bg=t["bg"], fg=t["dim"], font=("Segoe UI", 8),
                     text="  (автозапуск доступен только на Windows)").pack(
                     anchor="w", padx=10, pady=(0, 4))

        # ── Кнопки ──────────────────────────────────────────────────────────
        bf = tk.Frame(out, bg=t["bg"])
        bf.pack(fill=tk.X)
        ttk.Button(bf, text="✖  Отмена",
                   command=self.destroy).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(bf, text="💾  Сохранить",
                   command=self._save).pack(side=tk.RIGHT)

    def _save(self):
        # Валидация стандартного расписания
        for var, name in [
            (self.v_start, "Начало"),
            (self.v_wd,    "Конец (Пн–Чт)"),
            (self.v_fr,    "Конец (Пятница)"),
        ]:
            if not valid_t(var.get()):
                messagebox.showerror(
                    "Ошибка", f"Неверный формат «{name}»: {var.get()!r}\n"
                              f"Используй ЧЧ:ММ, например 09:00",
                    parent=self,
                )
                return

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cs = self.v_cs.get().strip()
        ce = self.v_ce.get().strip()

        if cs or ce:
            if not (valid_t(cs) and valid_t(ce)):
                messagebox.showerror(
                    "Ошибка",
                    "Неверный формат кастомного времени.\nИспользуй ЧЧ:ММ",
                    parent=self,
                )
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
        )
        autostart_set(self.v_auto.get())
        save_cfg(self.cfg)
        self.on_save(self.cfg)
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ВИДЖЕТ
# ═══════════════════════════════════════════════════════════════════════════════

class Widget(tk.Tk):
    W = WIDGET_W

    def __init__(self):
        super().__init__()
        self.cfg       = load_cfg()
        self._sopen    = False   # настройки открыты?
        self._fw_shown = False   # фейерверки уже показывали?
        self._dx       = 0
        self._dy       = 0

        # Убираем системные декорации — полностью кастомный вид
        self.overrideredirect(True)
        self.attributes("-topmost",  self.cfg.get("always_on_top", False))
        self.attributes("-alpha",    self.cfg.get("opacity", 0.92))

        # Восстанавливаем позицию, не выходя за край экрана
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = max(0, min(self.cfg.get("pos_x", 60), sw - self.W - 10))
        y  = max(0, min(self.cfg.get("pos_y", 60), sh - 180))
        self.geometry(f"+{x}+{y}")

        self._ui()
        self._tick()

    # ── Построение UI ────────────────────────────────────────────────────────

    def _ui(self):
        for w in self.winfo_children():
            w.destroy()

        t = THEMES[self.cfg.get("theme", "dark")]
        self._t = t
        W = self.W

        # Внешняя рамка (граница 1px)
        self.configure(bg=t["border"])
        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)

        # ── Хедер (drag zone) ──────────────────────────────────────────────
        hdr = tk.Frame(wrap, bg=t["hdr"], height=33)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        hl = tk.Label(hdr, text=f"⏱  {APP_NAME}",
                      bg=t["hdr"], fg=t["dim"],
                      font=("Segoe UI", 8, "bold"), anchor="w")
        hl.pack(side=tk.LEFT, padx=10)

        # Кнопки хедера: правой стороной идёт ✕ затем ⚙
        for sym, hover, cmd in [
            ("✕", "#ff5555", self._close),
            ("⚙", t["accent"], self._open_sett),
        ]:
            b = tk.Label(hdr, text=sym, bg=t["hdr"], fg=t["dim"],
                         font=("Segoe UI", 10, "bold"), cursor="hand2", width=2)
            b.pack(side=tk.RIGHT, padx=1)
            b.bind("<Button-1>", lambda e, c=cmd: c())
            b.bind("<Enter>",    lambda e, b=b, c=hover: b.config(fg=c))
            b.bind("<Leave>",    lambda e, b=b: b.config(fg=t["dim"]))

        # Drag на хедер
        for w in [hdr, hl]:
            w.bind("<ButtonPress-1>",   self._ds)
            w.bind("<B1-Motion>",       self._dm)
            w.bind("<ButtonRelease-1>", self._dr)

        # ── Тело ───────────────────────────────────────────────────────────
        body  = tk.Frame(wrap, bg=t["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(body, bg=t["bg"])
        inner.pack(padx=16, pady=(10, 14))

        # День + подпись расписания
        self._ld = tk.Label(inner, text="", bg=t["bg"], fg=t["dim"],
                            font=("Segoe UI", 9, "bold"),
                            anchor="w", width=27)
        self._ld.pack(anchor="w")

        # Прогресс-бар (фиксированная ширина = W-36 ≈ 250px)
        BAR_W = W - 36
        self._bar = tk.Canvas(inner, height=6, width=BAR_W,
                              bg=t["bar_bg"], highlightthickness=0, bd=0)
        self._bar.pack(pady=(7, 2), anchor="w")

        # Процент выполнения
        self._lp = tk.Label(inner, text="—", bg=t["bg"], fg=t["dim"],
                            font=("Segoe UI", 8), anchor="e", width=27)
        self._lp.pack(anchor="e")

        # Главный таймер — большие цифры
        self._lt = tk.Label(inner, text="00:00:00", bg=t["bg"], fg=t["accent"],
                            font=("Segoe UI", 44, "bold"), anchor="center", width=9)
        self._lt.pack(pady=(4, 0))

        # Статус
        self._ls = tk.Label(inner, text="до конца рабочего дня",
                            bg=t["bg"], fg=t["dim"],
                            font=("Segoe UI", 9), anchor="center", width=27)
        self._ls.pack()

        # Drag и контекстное меню на body
        for w in [body, inner, self._ld, self._ls, self._lp, self._lt]:
            w.bind("<ButtonPress-1>",   self._ds)
            w.bind("<B1-Motion>",       self._dm)
            w.bind("<ButtonRelease-1>", self._dr)
            w.bind("<Button-3>",        self._ctx)
        self._bar.bind("<Button-3>", self._ctx)

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _ds(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _dm(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _dr(self, e):
        self.cfg["pos_x"] = self.winfo_x()
        self.cfg["pos_y"] = self.winfo_y()
        save_cfg(self.cfg)

    # ── Контекстное меню ─────────────────────────────────────────────────────

    def _ctx(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="⚙️   Настройки",          command=self._open_sett)
        m.add_separator()
        aot = self.cfg.get("always_on_top", False)
        m.add_command(
            label=f"{'✅' if aot else '  '} Поверх всех окон",
            command=self._toggle_top,
        )
        m.add_separator()
        m.add_command(label="🎇   Тест фейерверков",  command=lambda: FWWindow(self))
        m.add_separator()
        m.add_command(label="❌   Выход",               command=self._close)
        m.tk_popup(e.x_root, e.y_root)

    def _toggle_top(self):
        self.cfg["always_on_top"] = not self.cfg.get("always_on_top", False)
        self.attributes("-topmost", self.cfg["always_on_top"])
        save_cfg(self.cfg)

    # ── Настройки ────────────────────────────────────────────────────────────

    def _open_sett(self):
        if self._sopen:
            return
        self._sopen = True

        def on_destroy(e):
            # Срабатывает и на дочерних виджетах — проверяем виджет
            if str(e.widget) == str(win):
                self._sopen = False

        win = SettingsWin(self, self.cfg, self._apply)
        win.bind("<Destroy>", on_destroy)

    def _apply(self, cfg):
        self.cfg     = cfg
        self._sopen  = False
        self._fw_shown = False
        self.attributes("-alpha",   cfg["opacity"])
        self.attributes("-topmost", cfg.get("always_on_top", False))
        self._ui()

    # ── Прогресс-бар ─────────────────────────────────────────────────────────

    def _draw_bar(self, progress):
        t  = self._t
        bw = self.W - 36
        self._bar.delete("b")
        if progress > 0:
            fw = max(5, int(bw * progress))
            self._bar.create_rectangle(0, 0, fw, 6,
                                       fill=t["bar_fg"], outline="", tags="b")

    # ── Главный тик (каждую секунду) ─────────────────────────────────────────

    def _tick(self):
        status, rem, prog, end = tick_state(self.cfg)
        t   = self._t
        now = datetime.datetime.now()
        wd  = now.weekday()
        day = f"{DAY_MOOD[wd]} {DAYS_RU[wd]}"
        end_str  = end.strftime("%H:%M")
        is_custom = (
            self.cfg.get("custom_date") == now.strftime("%Y-%m-%d")
            and bool(self.cfg.get("custom_start"))
        )

        if status == "before":
            self._ld.config(
                text=f"{day}  •  с {self.cfg['work_start']}",
                fg=t["dim"],
            )
            self._lt.config(text=fmt(rem), fg=t["dim"])
            self._ls.config(text="до начала рабочего дня")
            self._lp.config(text="—")

        elif status == "working":
            tag = "  🔧" if is_custom else ""
            self._ld.config(text=f"{day}  •  до {end_str}{tag}", fg=t["dim"])
            self._lp.config(text=f"{int(prog * 100)}%")
            self._ls.config(text="осталось")
            # < 30 мин: цвет пульсирует между warn и ok
            if rem < 1800:
                color = t["warn"] if (now.second % 2 == 0) else t["ok"]
                self._lt.config(text=fmt(rem), fg=color)
            else:
                self._lt.config(text=fmt(rem), fg=t["accent"])

        elif status == "done":
            self._ld.config(text=f"{day}  •  СВОБОДЕН! 🍻", fg=t["ok"])
            self._lt.config(text="00:00:00", fg=t["ok"])
            self._ls.config(text="Рабочий день окончен!  🎉")
            self._lp.config(text="100%")
            if not self._fw_shown:
                self._fw_shown = True
                self.after(400, lambda: FWWindow(self))

        self._draw_bar(prog)
        self.after(1000, self._tick)

    # ── Закрытие ─────────────────────────────────────────────────────────────

    def _close(self):
        self.cfg["pos_x"] = self.winfo_x()
        self.cfg["pos_y"] = self.winfo_y()
        save_cfg(self.cfg)
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = Widget()
    app.mainloop()
