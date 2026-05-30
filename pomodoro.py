"""
番茄钟桌面应用
Pomodoro Desktop Timer
纯 Python 实现，仅依赖标准库（tkinter + winsound + threading）
"""

import tkinter as tk
from tkinter import ttk
import math
import os
import ctypes
import json
import struct
import tempfile
from pathlib import Path

# ============================================================
# Windows API 辅助
# ============================================================
def flash_window(hwnd, count=5):
    try:
        FLASHW_ALL = 0x3
        FLASHW_TIMERNOFG = 0xC

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hwnd", ctypes.c_void_p),
                ("dwFlags", ctypes.c_uint),
                ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint),
            ]

        info = FLASHWINFO()
        info.cbSize = ctypes.sizeof(FLASHWINFO)
        info.hwnd = ctypes.c_void_p(hwnd)
        info.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
        info.uCount = count
        info.dwTimeout = 0
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass


def bring_to_front(hwnd):
    try:
        SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def get_hwnd(root):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if hwnd == 0:
            hwnd = root.winfo_id()
        return hwnd
    except Exception:
        return 0


# ============================================================
# 系统托盘图标
# ============================================================
def create_tray_icon(hwnd, callback, tip="Pomodoro"):
    try:
        ico_path = _create_tomato_ico()
        if not ico_path:
            return None, None

        NIF_ICON = 0x2
        NIF_MESSAGE = 0x1
        NIF_TIP = 0x4
        NIM_ADD = 0x0
        WM_TRAY = 0x8000 + 1

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", ctypes.c_void_p),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", ctypes.c_void_p),
                ("szTip", ctypes.c_char * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_char * 256),
                ("uVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_char * 64),
                ("dwInfoFlags", ctypes.c_uint),
                ("guidItem", ctypes.c_ubyte * 16),
                ("hBalloonIcon", ctypes.c_void_p),
            ]

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x10
        LoadImage = ctypes.windll.user32.LoadImageW
        LoadImage.restype = ctypes.c_void_p

        hicon = LoadImage(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if not hicon:
            hicon = LoadImage(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if not hicon:
            return None, ico_path

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = ctypes.c_void_p(hwnd)
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = hicon
        nid.szTip = tip.encode('utf-8')[:127]

        ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        return nid, ico_path
    except Exception as e:
        print(f"Tray icon creation failed: {e}")
        return None, None


def remove_tray_icon(nid):
    if nid is None:
        return
    try:
        NIM_DELETE = 0x2
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
    except Exception:
        pass


def show_tray_balloon(nid, title, msg, icon_type=1):
    if nid is None:
        return
    try:
        NIF_INFO = 0x10
        NIM_MODIFY = 0x1
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = title.encode('utf-8')[:63]
        nid.szInfo = msg.encode('utf-8')[:255]
        nid.dwInfoFlags = icon_type
        nid.uVersion = 0
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
    except Exception:
        pass


def _create_tomato_ico():
    """生成珊瑚红色圆形 ICO"""
    try:
        tmpdir = tempfile.gettempdir()
        ico_path = os.path.join(tmpdir, "pomodoro_tray.ico")
        if os.path.exists(ico_path):
            return ico_path

        size = 32
        bmp_data = bytearray()
        # BITMAPINFOHEADER
        bmp_data += struct.pack('<I', 40)
        bmp_data += struct.pack('<i', size)
        bmp_data += struct.pack('<i', size * 2)
        bmp_data += struct.pack('<H', 1)
        bmp_data += struct.pack('<H', 32)
        bmp_data += struct.pack('<I', 0)
        bmp_data += struct.pack('<I', size * size * 4)
        bmp_data += struct.pack('<i', 0) * 4

        cx, cy = size // 2, size // 2
        r = size // 2 - 2
        # Coral color #c75b48
        base_r, base_g, base_b = 199, 91, 72
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= r:
                    shade = 1.0 - (dist / r) * 0.25
                    R = int(base_r * shade)
                    G = int(base_g * shade)
                    B = int(base_b * shade)
                    A = 255
                elif dist <= r + 1.5:
                    R, G, B, A = 160, 65, 50, 220
                else:
                    R, G, B, A = 0, 0, 0, 0
                bmp_data += struct.pack('BBBB', B, G, R, A)

        and_mask = bytearray()
        for y in range(size):
            row = 0
            for x in range(size):
                dx, dy = x - cx, y - cy
                if math.sqrt(dx * dx + dy * dy) <= r + 1.5:
                    row |= (1 << (7 - (x % 8)))
                if (x % 8) == 7:
                    and_mask.append(row)
                    row = 0
            if size % 8 != 0:
                and_mask.append(row)
        while len(and_mask) % 4 != 0:
            and_mask.append(0)

        full_bmp = bytes(bmp_data) + bytes(and_mask)
        ico = bytearray()
        ico += struct.pack('<HHH', 0, 1, 1)
        ico += struct.pack('<BBBBHHII',
            32, 32, 0, 0, 1, 32, len(full_bmp), 22)
        ico += full_bmp

        with open(ico_path, 'wb') as f:
            f.write(bytes(ico))
        return ico_path
    except Exception as e:
        print(f"ICO creation failed: {e}")
        return None


# ============================================================
# 配色方案 — 暖米色主题
# ============================================================
#  背景:    #f6f0ec  暖米色
#  主色:    #c75b48  珊瑚红
#  深色字:  #3c3836  暖深灰
#  副字:    #756a64  暖灰褐
#  边框:    #d8cfc9  浅灰褐
#  环底色:  #e5ddd7  中浅灰褐
# ============================================================

C_WORK       = '#c75b48'  # 珊瑚红 — 专注
C_WORK_DIM   = '#a8483a'
C_SHORT      = '#5d9e8a'  # 暖鼠尾绿 — 短休
C_SHORT_DIM  = '#4a7d6e'
C_LONG       = '#5d8eb8'  # 暖蓝 — 长休
C_LONG_DIM   = '#4a7296'

C_BG         = '#f6f0ec'  # 主背景
C_CANVAS_BG  = '#f6f0ec'
C_RING_BG    = '#e5ddd7'  # 进度环底色
C_TEXT       = '#3c3836'  # 主文字
C_TEXT_SUB   = '#756a64'  # 副文字
C_SURFACE    = '#ede6e0'  # 面板/卡片表面
C_BORDER     = '#d8cfc9'  # 边框/分割线

C_BTN_RESET_BG  = '#ede6e0'
C_BTN_RESET_FG  = '#756a64'
C_BTN_RESET_HV  = '#e0d8d1'

C_SETTINGS_BG   = '#efe8e2'
C_ENTRY_BG      = '#faf7f4'
C_ENTRY_FG      = '#3c3836'
C_SAVE_BG       = '#5d9e8a'
C_SAVE_HV       = '#4a7d6e'


class PomodoroApp:
    COLORS = {
        'work':       {'main': C_WORK,  'dim': C_WORK_DIM,  'label': '专注中…'},
        'shortBreak': {'main': C_SHORT, 'dim': C_SHORT_DIM, 'label': '休息一下'},
        'longBreak':  {'main': C_LONG,  'dim': C_LONG_DIM,  'label': '深度放松'},
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pomodoro")
        self.root.geometry("400x580")
        self.root.minsize(340, 500)
        self.root.configure(bg=C_BG)

        ico_path = _create_tomato_ico()
        if ico_path:
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.mode = 'work'
        self.time_left = 25 * 60
        self.total_time = 25 * 60
        self.running = False
        self.pomo_count = 0
        self.total_focus_min = 0
        self.always_on_top = tk.BooleanVar(value=False)
        self.auto_start = tk.BooleanVar(value=True)
        self.minimize_to_tray = tk.BooleanVar(value=True)

        self.settings = {'work': 25, 'shortBreak': 5, 'longBreak': 15, 'longInterval': 4}
        self._load_settings()

        self.tray_nid = None
        self.tray_ico_path = None

        self._build_ui()
        self._setup_bindings()
        self.root.after(200, self._setup_tray)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center_window()

    # ─── 设置持久化 ─────────────────────────────────
    def _load_settings(self):
        cfg_path = Path.home() / ".pomodoro_config.json"
        try:
            if cfg_path.exists():
                with open(cfg_path, 'r') as f:
                    data = json.load(f)
                    for k in self.settings:
                        if k in data:
                            self.settings[k] = data[k]
        except Exception:
            pass

    def _save_settings(self):
        cfg_path = Path.home() / ".pomodoro_config.json"
        try:
            with open(cfg_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    # ─── 托盘 ───────────────────────────────────────
    def _setup_tray(self):
        self.root.update_idletasks()
        hwnd = get_hwnd(self.root)
        if hwnd:
            self.tray_nid, self.tray_ico_path = create_tray_icon(hwnd, None)

    def _on_close(self):
        if self.minimize_to_tray.get() and self.tray_nid:
            self.root.withdraw()
        else:
            self._quit()

    def _quit(self):
        self.running = False
        self._save_settings()
        remove_tray_icon(self.tray_nid)
        if self.tray_ico_path and os.path.exists(self.tray_ico_path):
            try:
                os.remove(self.tray_ico_path)
            except Exception:
                pass
        self.root.destroy()

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 400, 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ============================================================
    # UI 构建
    # ============================================================
    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=C_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))
        self._build_canvas_ring()
        self._build_controls()
        self._build_stats()
        self._build_settings_panel()
        self._update_ui()

    def _build_canvas_ring(self):
        self.canvas_size = 280
        self.ring_radius = 120
        self.ring_width = 9
        cx = cy = self.canvas_size // 2

        self.canvas = tk.Canvas(
            self.main_frame,
            width=self.canvas_size, height=self.canvas_size,
            bg=C_CANVAS_BG, highlightthickness=0
        )
        self.canvas.pack(pady=(0, 10))

        # 背景环
        self.ring_bg_id = self.canvas.create_oval(
            cx - self.ring_radius, cy - self.ring_radius,
            cx + self.ring_radius, cy + self.ring_radius,
            outline=C_RING_BG, width=self.ring_width, fill=''
        )

        self.progress_arc = None

        # 中心时间
        self.time_text = self.canvas.create_text(
            cx, cy - 12,
            text="25:00",
            font=('Segoe UI', 42, 'bold'),
            fill=C_TEXT, anchor='center'
        )

        # 模式标签
        self.mode_text = self.canvas.create_text(
            cx, cy + 32,
            text='专注中…',
            font=('Segoe UI', 11),
            fill=C_TEXT_SUB, anchor='center'
        )

    def _draw_progress(self, fraction):
        cx = cy = self.canvas_size // 2
        r = self.ring_radius

        if self.progress_arc is not None:
            self.canvas.delete(self.progress_arc)

        if fraction >= 1.0 or fraction <= 0.0:
            return

        angle = fraction * 360
        color = self.COLORS[self.mode]['main']
        self.progress_arc = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-angle,
            outline=color, width=self.ring_width,
            style='arc'
        )

    def _build_controls(self):
        # 模式切换按钮
        mode_frame = tk.Frame(self.main_frame, bg=C_BG)
        mode_frame.pack(pady=(0, 8))

        style = ttk.Style()
        style.theme_use('clam')

        # ttk 按钮在暖色背景下的样式
        style.configure('Mode.TButton',
                        font=('Segoe UI', 10, 'bold'),
                        padding=(16, 7),
                        background=C_SURFACE,
                        foreground=C_TEXT,
                        borderwidth=0,
                        relief='flat')
        style.map('Mode.TButton',
                  background=[('pressed', C_WORK), ('active', C_BORDER)],
                  foreground=[('pressed', '#ffffff')])

        self.btn_work = ttk.Button(mode_frame, text="专注", style='Mode.TButton',
                                   command=lambda: self._switch_mode('work'))
        self.btn_work.pack(side=tk.LEFT, padx=3)

        self.btn_short = ttk.Button(mode_frame, text="短休", style='Mode.TButton',
                                    command=lambda: self._switch_mode('shortBreak'))
        self.btn_short.pack(side=tk.LEFT, padx=3)

        self.btn_long = ttk.Button(mode_frame, text="长休", style='Mode.TButton',
                                   command=lambda: self._switch_mode('longBreak'))
        self.btn_long.pack(side=tk.LEFT, padx=3)

        # 主控制按钮
        btn_frame = tk.Frame(self.main_frame, bg=C_BG)
        btn_frame.pack(pady=(5, 0))

        self.btn_reset = tk.Button(btn_frame, text="↺", font=('Segoe UI', 14),
                                    width=3,
                                    bg=C_BTN_RESET_BG, fg=C_BTN_RESET_FG,
                                    activebackground=C_BTN_RESET_HV, activeforeground=C_TEXT,
                                    relief=tk.FLAT, bd=0, cursor='hand2',
                                    command=self._reset)
        self.btn_reset.pack(side=tk.LEFT, padx=8)

        self.btn_main = tk.Button(btn_frame, text="开始", font=('Segoe UI', 14, 'bold'),
                                   width=10, height=2,
                                   bg=C_WORK, fg='white',
                                   activebackground=C_WORK_DIM, activeforeground='white',
                                   relief=tk.FLAT, bd=0, cursor='hand2',
                                   command=self._toggle_timer)
        self.btn_main.pack(side=tk.LEFT, padx=8)

        self.btn_skip = tk.Button(btn_frame, text="跳过", font=('Segoe UI', 11),
                                   width=4,
                                   bg=C_BTN_RESET_BG, fg=C_BTN_RESET_FG,
                                   activebackground=C_BTN_RESET_HV, activeforeground=C_TEXT,
                                   relief=tk.FLAT, bd=0, cursor='hand2',
                                   command=self._skip)
        self.btn_skip.pack(side=tk.LEFT, padx=8)

    def _build_stats(self):
        stat_frame = tk.Frame(self.main_frame, bg=C_BG)
        stat_frame.pack(pady=(12, 8))

        for key, label in [('pomo', '完成番茄'), ('focus', '专注时长')]:
            f = tk.Frame(stat_frame, bg=C_BG)
            f.pack(side=tk.LEFT, padx=30)

            val = tk.Label(f, text="0", font=('Segoe UI', 26, 'bold'),
                          fg=C_TEXT, bg=C_BG)
            val.pack()

            lbl = tk.Label(f, text=label, font=('Segoe UI', 9),
                          fg=C_TEXT_SUB, bg=C_BG)
            lbl.pack()

            if key == 'pomo':
                self.pomo_label = val
            else:
                self.focus_label = val

    def _build_settings_panel(self):
        self.settings_visible = False

        tool_frame = tk.Frame(self.main_frame, bg=C_BG)
        tool_frame.pack(pady=(12, 5))

        self.btn_settings = tk.Button(tool_frame, text="设置", font=('Segoe UI', 9),
                                       bg=C_BG, fg=C_TEXT_SUB,
                                       activebackground=C_BG, activeforeground=C_TEXT,
                                       relief=tk.FLAT, bd=0, cursor='hand2',
                                       command=self._toggle_settings)
        self.btn_settings.pack(side=tk.LEFT, padx=5)

        self.cb_top = tk.Checkbutton(tool_frame, text="置顶", variable=self.always_on_top,
                                      command=self._toggle_always_on_top,
                                      font=('Segoe UI', 9),
                                      bg=C_BG, fg=C_TEXT_SUB,
                                      selectcolor=C_BG,
                                      activebackground=C_BG, activeforeground=C_TEXT)
        self.cb_top.pack(side=tk.LEFT, padx=10)

        self.cb_auto = tk.Checkbutton(tool_frame, text="自动继续", variable=self.auto_start,
                                       font=('Segoe UI', 9),
                                       bg=C_BG, fg=C_TEXT_SUB,
                                       selectcolor=C_BG,
                                       activebackground=C_BG, activeforeground=C_TEXT)
        self.cb_auto.pack(side=tk.LEFT, padx=5)

        self.settings_frame = tk.Frame(self.main_frame, bg=C_SETTINGS_BG,
                                        highlightbackground=C_BORDER,
                                        highlightthickness=1)
        self._build_settings_content()

    def _build_settings_content(self):
        header = tk.Label(self.settings_frame, text="时长设置 (分钟)",
                         font=('Segoe UI', 10, 'bold'),
                         fg=C_TEXT, bg=C_SETTINGS_BG)
        header.pack(pady=(12, 8), padx=15, anchor='w')

        self.setting_vars = {}
        settings_info = [
            ('work',         '专注时长',          1, 120),
            ('shortBreak',   '短休息时长',         1, 30),
            ('longBreak',    '长休息时长',         1, 60),
            ('longInterval', '长休息间隔 (个番茄)', 2, 10),
        ]

        for key, label, vmin, vmax in settings_info:
            row = tk.Frame(self.settings_frame, bg=C_SETTINGS_BG)
            row.pack(fill=tk.X, padx=15, pady=4)

            tk.Label(row, text=label, font=('Segoe UI', 10),
                    fg=C_TEXT, bg=C_SETTINGS_BG).pack(side=tk.LEFT)

            var = tk.IntVar(value=self.settings[key])
            self.setting_vars[key] = var

            vcmd = (self.root.register(self._validate_int), '%P')
            sp = tk.Spinbox(row, textvariable=var, font=('Segoe UI', 10),
                           width=5, justify='center', from_=vmin, to=vmax,
                           bg=C_ENTRY_BG, fg=C_ENTRY_FG,
                           buttonbackground=C_SURFACE,
                           relief=tk.FLAT, bd=0,
                           validate='key', validatecommand=vcmd)
            sp.pack(side=tk.RIGHT, padx=(8, 0))

            unit = '分钟' if key != 'longInterval' else '个'
            tk.Label(row, text=unit, font=('Segoe UI', 9),
                    fg=C_TEXT_SUB, bg=C_SETTINGS_BG).pack(side=tk.RIGHT)

        btn_save = tk.Button(self.settings_frame, text="保存设置", font=('Segoe UI', 10),
                             bg=C_SAVE_BG, fg='white',
                             activebackground=C_SAVE_HV,
                             relief=tk.FLAT, bd=0, cursor='hand2',
                             padx=20, pady=5,
                             command=self._apply_settings)
        btn_save.pack(pady=(10, 14))

    def _validate_int(self, v):
        if v == '':
            return True
        try:
            int(v)
            return True
        except ValueError:
            return False

    def _toggle_settings(self):
        if self.settings_visible:
            self.settings_frame.pack_forget()
            self.settings_visible = False
        else:
            self.settings_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
            self.settings_visible = True

    def _toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    # =====
