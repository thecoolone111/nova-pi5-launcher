#!/usr/bin/env python3
"""
Nova OS v6 — Raspberry Pi 5
Native PyQt6 application — full redesign
"""

import sys, os, math, time, subprocess, json, random, glob, shutil, datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient, QPainterPath,
    QKeyEvent, QCursor, QPalette
)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

VERSION   = "6.0.0"
APP_DIR   = Path("/opt/novaos")
USB_ROOT  = Path("/media")
USAGE_FILE = APP_DIR / "app_usage.json"

# ──────────────────────────────────────────────────────────────────
#  THEMES
# ──────────────────────────────────────────────────────────────────
THEMES = {
    "NOVA BLUE":    {"bg":"#000a1a","accent":"#00c8ff","accent2":"#00ffcc"},
    "MILITARY":     {"bg":"#030d02","accent":"#39ff14","accent2":"#aaff00"},
    "ALIEN":        {"bg":"#020c06","accent":"#00ff88","accent2":"#ccff00"},
    "CYBERPUNK":    {"bg":"#0d0010","accent":"#ff00ff","accent2":"#ff6ec7"},
    "DEEP SPACE":   {"bg":"#00000f","accent":"#7b68ee","accent2":"#c8a0ff"},
    "BIOHAZARD":    {"bg":"#0a0800","accent":"#ff6600","accent2":"#ffcc00"},
    "STEALTH":      {"bg":"#080808","accent":"#cc0000","accent2":"#ff4444"},
    "ARCTIC":       {"bg":"#020810","accent":"#88ddff","accent2":"#ffffff"},
}
CURRENT_THEME = "NOVA BLUE"

def T():       return THEMES[CURRENT_THEME]
def AC():      return QColor(T()["accent"])
def AC2():     return QColor(T()["accent2"])
def BG():      return QColor(T()["bg"])
def ACA(a):    c=QColor(T()["accent"]); c.setAlpha(int(a)); return c
def AC2A(a):   c=QColor(T()["accent2"]); c.setAlpha(int(a)); return c

# ──────────────────────────────────────────────────────────────────
#  USAGE TRACKING
# ──────────────────────────────────────────────────────────────────
def load_usage():
    try:
        with open(USAGE_FILE) as f: return json.load(f)
    except: return {}

def save_usage(d):
    try: APP_DIR.mkdir(parents=True,exist_ok=True); open(USAGE_FILE,"w").write(json.dumps(d))
    except: pass

def record_launch(key):
    d=load_usage(); d[key]=d.get(key,0)+1; save_usage(d)

def top_apps(n=8):
    d=load_usage()
    keys=[k for k,_ in sorted(d.items(),key=lambda x:-x[1])][:n]
    for fb in ["ap:terminal","ap:firefox","ap:retroarch","ap:files"]:
        if fb not in keys and len(keys)<n: keys.append(fb)
    return keys[:n]

# ──────────────────────────────────────────────────────────────────
#  ALL APPS REGISTRY
# ──────────────────────────────────────────────────────────────────
ALL_APPS = {
    "ap:moonlight": ("🌙","MOONLIGHT","PC Stream"),
    "ap:firefox":   ("🦊","FIREFOX","Browser"),
    "ap:raspotify": ("🎵","RASPOTIFY","Music"),
    "ap:vesktop":   ("💬","VESKTOP","Discord"),
    "ap:godot":     ("🎮","GODOT","Engine"),
    "ap:retroarch": ("🕹","RETROARCH","Emulator"),
    "ap:terminal":  ("💻","TERMINAL","CLI"),
    "ap:files":     ("📁","FILES","Manager"),
    "ap:network":   ("📡","NETWORK","WiFi"),
    "ap:bluetooth": ("🔵","BLUET.","Pair"),
    "ap:vlc":       ("🎬","VLC","Media"),
    "ap:youtube":   ("▶","YOUTUBE","Video"),
    "sc:roms":      ("💾","ROMS","Library"),
    "sc:settings":  ("⚙","SETTINGS","Config"),
}

# ──────────────────────────────────────────────────────────────────
#  HELPER — panel background style
# ──────────────────────────────────────────────────────────────────
def PS(): return "background:rgba(0,10,25,0.88);border:1px solid rgba(0,200,255,0.32);"

# ──────────────────────────────────────────────────────────────────
#  BACKGROUND LAYERS
# ──────────────────────────────────────────────────────────────────
class GridBG(QWidget):
    def __init__(self,p=None):
        super().__init__(p); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._o=0.0; t=QTimer(self); t.timeout.connect(self._tick); t.start(40)
    def _tick(self): self._o=(self._o+0.7)%44; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); c=QColor(T()["accent"]); c.setAlpha(11); painter.setPen(QPen(c,1))
        o=self._o; x=-44+(o%44)
        while x<self.width(): painter.drawLine(int(x),0,int(x),self.height()); x+=44
        y=-44+(o%44)
        while y<self.height(): painter.drawLine(0,int(y),self.width(),int(y)); y+=44
        painter.end()

class Particles(QWidget):
    def __init__(self,p=None):
        super().__init__(p); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._pts=[]; self._on=True; t=QTimer(self); t.timeout.connect(self._tick); t.start(40)
    def _new(self,y=None):
        w=self.width() or 1280; h=self.height() or 800
        return {"x":random.uniform(0,w),"y":y if y is not None else random.uniform(0,h),
                "sz":random.uniform(0.6,2.2),"vx":random.uniform(-0.12,0.12),
                "vy":-random.uniform(0.12,0.45),"l":random.uniform(0,1),"ml":random.uniform(0.5,1.0)}
    def _tick(self):
        if not self._pts: self._pts=[self._new() for _ in range(28)]
        if not self._on: return
        for p in self._pts:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["l"]+=0.004
            if p["y"]<-4 or p["l"]>p["ml"]: p.update(self._new(y=self.height()+4))
        self.update()
    def paintEvent(self,_):
        if not self._on: return
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ac=QColor(T()["accent"])
        for p in self._pts:
            a=int(math.sin((p["l"]/p["ml"])*math.pi)*70)
            if a<=0: continue
            c=QColor(ac); c.setAlpha(a); painter.setBrush(QBrush(c)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p["x"],p["y"]),p["sz"],p["sz"])
        painter.end()

class Scanlines(QWidget):
    def __init__(self,p=None):
        super().__init__(p); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    def paintEvent(self,_):
        painter=QPainter(self); painter.setBrush(QBrush(QColor(0,0,0,13))); painter.setPen(Qt.PenStyle.NoPen)
        y=0
        while y<self.height(): painter.drawRect(0,y+2,self.width(),2); y+=4
        painter.end()

class Corners(QWidget):
    def __init__(self,p=None):
        super().__init__(p); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(AC(),2)); m,l=14,52
        painter.drawLine(m,m+l,m,m); painter.drawLine(m,m,m+l,m)
        painter.drawLine(self.width()-m,m+l,self.width()-m,m); painter.drawLine(self.width()-m,m,self.width()-m-l,m)
        painter.drawLine(m,self.height()-m-l,m,self.height()-m); painter.drawLine(m,self.height()-m,m+l,self.height()-m)
        painter.drawLine(self.width()-m,self.height()-m-l,self.width()-m,self.height()-m); painter.drawLine(self.width()-m,self.height()-m,self.width()-m-l,self.height()-m)
        painter.end()

# ──────────────────────────────────────────────────────────────────
#  BOOT SCREEN
# ──────────────────────────────────────────────────────────────────
class BootScreen(QWidget):
    finished = pyqtSignal()
    def __init__(self,p=None):
        super().__init__(p); self.setStyleSheet("background:#000008;")
        self._step=0; self._prog=0.0; self._alphas=[0,0,0,0]; self._tag_a=0; self._phase=0; self._fade=0
        self._ring_a=0.0; self._ring2_a=0.0
        self._build(); t=QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def _build(self):
        lay=QVBoxLayout(self); lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.setSpacing(20)
        self._logo=_LogoWidget(); self._logo.setFixedSize(560,100); lay.addWidget(self._logo,0,Qt.AlignmentFlag.AlignCenter)
        self._tag=QLabel("RASPBERRY PI 5  //  GAMING OS  //  ARM64"); self._tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tag.setStyleSheet("color:rgba(0,200,255,0);font-size:10px;letter-spacing:5px;font-family:monospace;background:transparent;")
        lay.addWidget(self._tag)
        self._ver=QLabel(f"v{VERSION}  ·  BCM2712  ·  CORTEX-A76  ·  2.4GHz"); self._ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ver.setStyleSheet("color:rgba(0,200,255,0);font-size:7px;letter-spacing:2px;font-family:monospace;background:transparent;")
        lay.addWidget(self._ver)
        self._bar=_BootBar(); self._bar.setFixedSize(300,6); self._bar.setVisible(False); lay.addWidget(self._bar,0,Qt.AlignmentFlag.AlignCenter)
        self._ring=_BootRing(); self._ring.setFixedSize(90,90); self._ring.setVisible(False); lay.addWidget(self._ring,0,Qt.AlignmentFlag.AlignCenter)

    def _tick(self):
        self._step+=1
        if self._step<35:
            idx=self._step//8
            for i in range(4): self._logo.set_alpha(i, min(255,(self._step-i*8)*16) if i<=idx else 0)
        elif self._step==35:
            self._phase=1; self._bar.setVisible(True)
        elif self._phase==1:
            self._prog=min(1.0,self._prog+0.013)
            self._bar.set_prog(self._prog)
            self._tag_a=min(200,self._tag_a+7)
            self._tag.setStyleSheet(f"color:rgba(0,200,255,{self._tag_a});font-size:10px;letter-spacing:5px;font-family:monospace;background:transparent;")
            self._ver.setStyleSheet(f"color:rgba(0,200,255,{int(self._tag_a*0.7)});font-size:7px;letter-spacing:2px;font-family:monospace;background:transparent;")
            if self._prog>=1.0: self._phase=2; self._bar.setVisible(False); self._ring.setVisible(True)
        elif self._phase==2:
            self._ring.tick()
            if self._step>130: self._phase=3
        elif self._phase==3:
            self._fade=min(255,self._fade+10); self.update()
            if self._fade>=255: self.finished.emit()

    def paintEvent(self,e):
        super().paintEvent(e)
        if self._phase==3 and self._fade>0:
            p=QPainter(self); p.fillRect(self.rect(),QColor(0,0,8,self._fade)); p.end()

class _LogoWidget(QWidget):
    def __init__(self): super().__init__(); self._a=[0,0,0,0]; self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    def set_alpha(self,i,a): self._a[i]=a; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        f=QFont("monospace",64); f.setBold(True); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,12); painter.setFont(f)
        letters="NOVA"; fm=painter.fontMetrics()
        total=fm.horizontalAdvance(letters)+12*3; x=(self.width()-total)//2; y=self.height()-8
        for i,ch in enumerate(letters):
            a=self._a[i]; c=QColor(0,200,255,a); painter.setPen(QPen(c))
            if a>80:
                g=QColor(0,200,255,a//4)
                for dx,dy in [(-2,0),(2,0),(0,-2),(0,2)]: painter.setPen(QPen(g)); painter.drawText(x+dx,y+dy,ch)
                painter.setPen(QPen(c))
            painter.drawText(x,y,ch); x+=fm.horizontalAdvance(ch)+12
        painter.end()

class _BootBar(QWidget):
    def __init__(self): super().__init__(); self._p=0.0
    def set_prog(self,p): self._p=p; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        painter.setBrush(QBrush(QColor(255,255,255,15))); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(0,0,w,h,2,2)
        if self._p>0:
            g=QLinearGradient(0,0,w,0); g.setColorAt(0,QColor("#00c8ff")); g.setColorAt(1,QColor("#00ffcc"))
            painter.setBrush(QBrush(g)); painter.drawRoundedRect(0,0,int(w*self._p),h,2,2)
        painter.end()

class _BootRing(QWidget):
    def __init__(self): super().__init__(); self._a=0.0
    def tick(self): self._a=(self._a+3)%360; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx,cy=self.width()//2,self.height()//2
        painter.save(); painter.translate(cx,cy); painter.rotate(self._a)
        painter.setPen(QPen(QColor(0,200,255,80),2)); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawEllipse(QPointF(0,0),40,40)
        painter.restore()
        painter.save(); painter.translate(cx,cy); painter.rotate(-self._a*1.5)
        painter.setPen(QPen(QColor(0,255,204,35),1,Qt.PenStyle.DashLine)); painter.drawEllipse(QPointF(0,0),30,30)
        painter.restore()
        painter.translate(cx,cy); f=QFont("monospace",5); painter.setFont(f); painter.setPen(QPen(QColor("#00ffcc")))
        for i,t in enumerate(["SYS","INIT","✦"]): painter.drawText(-18,-10+i*9,36,9,Qt.AlignmentFlag.AlignCenter,t)
        painter.end()

# ──────────────────────────────────────────────────────────────────
#  SHARED WIDGETS
# ──────────────────────────────────────────────────────────────────
class SectionHdr(QWidget):
    def __init__(self,text,p=None):
        super().__init__(p); self._text=text; self.setFixedHeight(26)
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(AC2(),1)); painter.setFont(QFont("monospace",7))
        painter.drawText(0,0,14,self.height(),Qt.AlignmentFlag.AlignVCenter,"▶")
        ac=ACA(105); f=QFont("monospace",6); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,2); painter.setFont(f); painter.setPen(QPen(ac))
        painter.drawText(14,0,400,self.height(),Qt.AlignmentFlag.AlignVCenter,self._text)
        lx=14+painter.fontMetrics().horizontalAdvance(self._text)+8; ac.setAlpha(32); painter.setPen(QPen(ac,1))
        painter.drawLine(lx,self.height()//2,self.width(),self.height()//2); painter.end()

class GlowBtn(QPushButton):
    def __init__(self,text="",small=False,p=None):
        super().__init__(text,p); self._small=small; self._hov=False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); self.setFixedHeight(28 if small else 34)
    def enterEvent(self,e): self._hov=True; self.update()
    def leaveEvent(self,e): self._hov=False; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); path=QPainterPath()
        path.moveTo(5,0); path.lineTo(w,0); path.lineTo(w-5,h); path.lineTo(0,h); path.closeSubpath()
        painter.setBrush(QBrush(ACA(38 if self._hov else 16))); painter.setPen(QPen(ACA(190 if self._hov else 110),1)); painter.drawPath(path)
        f=QFont("monospace",6 if self._small else 7); f.setBold(True); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,1)
        painter.setFont(f); painter.setPen(QPen(AC())); painter.drawText(0,0,w,h,Qt.AlignmentFlag.AlignCenter,self.text()); painter.end()

class Toast(QWidget):
    def __init__(self,p=None):
        super().__init__(p); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setFixedHeight(32)
        self._text=""; self._a=0; self._fade=QTimer(self); self._fade.timeout.connect(self._do_fade)
        self._hide=QTimer(self); self._hide.setSingleShot(True); self._hide.timeout.connect(lambda:self._fade.start(28)); self.hide()
    def show_msg(self,text):
        self._text=text; self._a=255; self._fade.stop(); self._hide.stop()
        self.show(); self.raise_(); self._repos(); self.update(); self._hide.start(2800)
    def _repos(self):
        if self.parent():
            pw,ph=self.parent().width(),self.parent().height(); w=min(460,pw-40)
            self.setFixedWidth(w); self.move((pw-w)//2,ph-56)
    def _do_fade(self):
        self._a-=14
        if self._a<=0: self._a=0; self._fade.stop(); self.hide()
        self.update()
    def paintEvent(self,_):
        if not self._text: return
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); path=QPainterPath()
        path.moveTo(6,0); path.lineTo(w,0); path.lineTo(w-6,h); path.lineTo(0,h); path.closeSubpath()
        bg=QColor(0,5,18,int(self._a*0.96)); painter.setBrush(QBrush(bg)); border=ACA(int(self._a*0.5)); painter.setPen(QPen(border,1)); painter.drawPath(path)
        f=QFont("monospace",7); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,1); painter.setFont(f)
        tc=AC(); tc.setAlpha(self._a); painter.setPen(QPen(tc)); painter.drawText(0,0,w,h,Qt.AlignmentFlag.AlignCenter,self._text); painter.end()

def make_scroll(widget,h=None):
    s=QScrollArea(); s.setWidget(widget); s.setWidgetResizable(True); s.setFrameShape(QFrame.Shape.NoFrame)
    s.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    s.setStyleSheet("QScrollArea{background:transparent;border:none;}QScrollBar:vertical{background:rgba(0,200,255,0.04);width:3px;border:none;}QScrollBar::handle:vertical{background:rgba(0,200,255,0.22);border-radius:1px;}QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
    if h: s.setFixedHeight(h)
    return s

class AppTile(QWidget):
    clicked=pyqtSignal(str)
    def __init__(self,icon,label,sub,action,size=76,p=None):
        super().__init__(p); self._icon=icon; self._label=label; self._sub=sub; self._action=action; self._hov=False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); self.setFixedSize(size,size-4)
    def enterEvent(self,e): self._hov=True; self.update()
    def leaveEvent(self,e): self._hov=False; self.update()
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self.clicked.emit(self._action)
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); path=QPainterPath()
        path.moveTo(0,0); path.lineTo(w-7,0); path.lineTo(w,7); path.lineTo(w,h); path.lineTo(7,h); path.lineTo(0,h-7); path.closeSubpath()
        painter.setClipPath(path); painter.setBrush(QBrush(ACA(42 if self._hov else 12))); painter.setPen(QPen(ACA(160 if self._hov else 48),1)); painter.drawPath(path)
        g=QLinearGradient(0,0,w,0); g.setColorAt(0,QColor(0,0,0,0)); g.setColorAt(0.5,ACA(75)); g.setColorAt(1,QColor(0,0,0,0))
        painter.setPen(QPen(QBrush(g),1)); painter.drawLine(0,0,w,0); painter.setClipping(False)
        painter.setFont(QFont("Segoe UI Emoji",16)); painter.setPen(QPen(QColor("white")))
        painter.drawText(0,0,w,int(h*0.52),Qt.AlignmentFlag.AlignCenter,self._icon)
        f=QFont("monospace",5); f.setBold(True); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,0.5)
        painter.setFont(f); painter.setPen(QPen(AC()))
        painter.drawText(0,int(h*0.52),w,14,Qt.AlignmentFlag.AlignCenter,self._label)
        painter.setFont(QFont("monospace",4)); painter.setPen(QPen(ACA(75)))
        painter.drawText(0,int(h*0.52)+13,w,12,Qt.AlignmentFlag.AlignCenter,self._sub); painter.end()

# ──────────────────────────────────────────────────────────────────
#  WORKERS
# ──────────────────────────────────────────────────────────────────
class StatsWorker(QThread):
    updated=pyqtSignal(dict)
    def run(self):
        while True: self.updated.emit(self._read()); self.sleep(3)
    def _read(self):
        d={}
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f: d["cpu_temp"]=round(int(f.read().strip())/1000,1)
        except: d["cpu_temp"]=None
        if HAS_PSUTIL:
            try:
                vm=psutil.virtual_memory(); disk=psutil.disk_usage("/")
                d.update({"ram_pct":round(vm.percent,1),"ram_used_gb":round(vm.used/1024**3,2),"ram_total_gb":round(vm.total/1024**3,2),
                           "disk_pct":round(disk.percent,1),"disk_used_gb":round(disk.used/1024**3,1),"disk_total_gb":round(disk.total/1024**3,1),
                           "cpu_pct":psutil.cpu_percent(interval=0)})
            except: pass
        elif HAS_REQUESTS:
            try:
                r=requests.get("http://localhost:7777/stats",timeout=0.7)
                if r.ok: d.update(r.json())
            except: pass
        return d

class MusicEngine(QThread):
    track_changed=pyqtSignal(str,str,int,int)  # title,artist,idx,total
    play_state=pyqtSignal(bool)
    BUILTIN=[("Whatever It Takes","Imagine Dragons"),("Radioactive","Imagine Dragons"),("Enemy","Imagine Dragons"),("Thunder","Imagine Dragons")]
    def __init__(self):
        super().__init__(); self._playlist=list(self.BUILTIN); self._idx=0; self._playing=False; self._proc=None; self._mode="none"
        self._detect()
    def _detect(self):
        if shutil.which("mpg123"):
            mp3s=list((Path.home()/"Music").glob("**/*.mp3"))
            if mp3s:
                self._playlist=[(p.stem,"Local") for p in mp3s[:40]]+[(p,str(p)) for p in mp3s[:40]]
                self._playlist=[(p.stem,"Local") for p in mp3s[:40]]; self._mode="mpg123"; return
        try:
            r=subprocess.run(["systemctl","is-active","raspotify"],capture_output=True,text=True)
            if r.stdout.strip()=="active": self._mode="raspotify"; return
        except: pass
        self._mode="none"
    def play_pause(self):
        if self._playing: self._stop(); self._playing=False
        else: self._playing=True; self._play_cur()
        self.play_state.emit(self._playing)
    def next(self): self._idx=(self._idx+1)%len(self._playlist); self._emit(); (self._stop() or self._play_cur()) if self._playing else None
    def prev(self): self._idx=(self._idx-1)%len(self._playlist); self._emit(); (self._stop() or self._play_cur()) if self._playing else None
    def _emit(self): t,a=self._playlist[self._idx]; self.track_changed.emit(t,a,self._idx,len(self._playlist))
    def _play_cur(self):
        if self._mode!="mpg123": return
        t,path=self._playlist[self._idx]
        # For builtin list no real path; skip
        if not Path(path).exists(): return
        try: self._proc=subprocess.Popen(["mpg123","-q",path],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass
    def _stop(self):
        if self._proc:
            try: self._proc.terminate()
            except: pass
            self._proc=None
    def current(self): return self._playlist[self._idx][0], self._playlist[self._idx][1]
    def run(self):
        while True: self.sleep(5)

class DiscordReader(QThread):
    notifications=pyqtSignal(list)
    def run(self):
        while True: self.notifications.emit(self._read()); self.sleep(20)
    def _read(self):
        bases=[Path.home()/".config"/"vesktop",Path.home()/".config"/"discord",
               Path.home()/".var"/"app"/"dev.vencord.Vesktop"/"config"/"vesktop"]
        for b in bases:
            if b.exists(): return [{"server":"Vesktop","ch":"status","msg":"Vesktop is running","t":"now"}]
        return [{"server":"Discord","ch":"info","msg":"Open Vesktop to connect","t":"--"}]

# ──────────────────────────────────────────────────────────────────
#  TOP BAR
# ──────────────────────────────────────────────────────────────────
class TopBar(QWidget):
    prev_clicked=pyqtSignal(); next_clicked=pyqtSignal(); track_clicked=pyqtSignal()
    def __init__(self,p=None):
        super().__init__(p); self.setFixedHeight(66); self._bar_h=[8]*5; self._bar_ph=[random.uniform(0,math.pi*2) for _ in range(5)]; self._playing=False
        self._build(); t=QTimer(self); t.timeout.connect(self._tick_vis); t.start(80)
    def _build(self):
        lay=QHBoxLayout(self); lay.setContentsMargins(16,0,16,0); lay.setSpacing(0)
        # LEFT
        left=QWidget(); left.setFixedWidth(280); left.setStyleSheet("background:transparent;")
        ll=QVBoxLayout(left); ll.setContentsMargins(8,8,8,8); ll.setSpacing(2)
        self._welcome=QLabel("WELCOME, COMMANDER")
        self._welcome.setStyleSheet(f"color:{T()['accent']};font-size:14px;font-weight:bold;font-family:monospace;background:transparent;letter-spacing:2px;")
        self._sub_lbl=QLabel("SYSTEM READY  //  NOVA OS v6")
        self._sub_lbl.setStyleSheet("color:rgba(0,200,255,0.42);font-size:7px;font-family:monospace;background:transparent;letter-spacing:1px;")
        ll.addWidget(self._welcome); ll.addWidget(self._sub_lbl); lay.addWidget(left)
        lay.addStretch(1)
        # CENTRE — music
        centre=QWidget(); centre.setStyleSheet("background:transparent;")
        cl=QHBoxLayout(centre); cl.setContentsMargins(0,0,0,0); cl.setSpacing(8); cl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._vis=QWidget(); self._vis.setFixedSize(32,18); self._vis.paintEvent=self._paint_vis; cl.addWidget(self._vis)
        self._btn_prev=QPushButton("◀"); self._btn_prev.setFixedSize(26,26); self._btn_prev.setStyleSheet(self._bs()); self._btn_prev.clicked.connect(self.prev_clicked); cl.addWidget(self._btn_prev)
        # Track widget — click to pause
        self._track_w=QWidget(); self._track_w.setFixedWidth(210); self._track_w.setStyleSheet("background:transparent;"); self._track_w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        tl=QVBoxLayout(self._track_w); tl.setContentsMargins(0,0,0,0); tl.setSpacing(1)
        self._track_title=QLabel("Whatever It Takes"); self._track_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_title.setStyleSheet(f"color:{T()['accent2']};font-size:10px;font-weight:bold;font-family:monospace;background:transparent;")
        self._track_artist=QLabel("Imagine Dragons  •  1/4"); self._track_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_artist.setStyleSheet("color:rgba(0,200,255,0.48);font-size:7px;font-family:monospace;background:transparent;")
        tl.addWidget(self._track_title); tl.addWidget(self._track_artist)
        self._track_w.mousePressEvent=lambda e: self.track_clicked.emit()
        cl.addWidget(self._track_w)
        self._btn_next=QPushButton("▶"); self._btn_next.setFixedSize(26,26); self._btn_next.setStyleSheet(self._bs()); self._btn_next.clicked.connect(self.next_clicked); cl.addWidget(self._btn_next)
        lay.addWidget(centre); lay.addStretch(1)
        # RIGHT
        right=QWidget(); right.setFixedWidth(280); right.setStyleSheet("background:transparent;")
        rl=QVBoxLayout(right); rl.setContentsMargins(8,8,8,8); rl.setSpacing(2); rl.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self._clock=QLabel("--:--:--"); self._clock.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._clock.setStyleSheet(f"color:{T()['accent2']};font-size:14px;font-weight:bold;font-family:monospace;background:transparent;")
        self._sysinfo=QLabel("CPU --°C  RAM --%"); self._sysinfo.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._sysinfo.setStyleSheet("color:rgba(0,200,255,0.42);font-size:7px;font-family:monospace;background:transparent;")
        rl.addWidget(self._clock); rl.addWidget(self._sysinfo); lay.addWidget(right)
    def _bs(self):
        return f"QPushButton{{background:rgba(0,200,255,0.08);border:1px solid rgba(0,200,255,0.28);color:{T()['accent']};font-size:10px;border-radius:13px;}}QPushButton:hover{{background:rgba(0,200,255,0.22);}}"
    def _tick_vis(self):
        t2=time.time()
        if self._playing:
            for i in range(5): self._bar_h[i]=int(4+math.sin(t2*4+self._bar_ph[i])*6+random.uniform(0,2))
        else:
            for i in range(5): self._bar_h[i]=max(2,self._bar_h[i]-1)
        self._vis.update()
    def _paint_vis(self,_):
        painter=QPainter(self._vis); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.fillRect(self._vis.rect(),QColor(0,0,0,0)); ac=AC()
        for i,h in enumerate(self._bar_h): painter.setBrush(QBrush(ac)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(i*6,18-h,4,h,1,1)
        painter.end()
    def set_track(self,title,artist,idx,total):
        self._track_title.setText(title); self._track_artist.setText(f"{artist}  •  {idx+1}/{total}")
    def set_playing(self,v): self._playing=v
    def update_clock(self,t): self._clock.setText(t)
    def update_sysinfo(self,cpu,ram): self._sysinfo.setText(f"CPU {cpu}  RAM {ram}")
    def refresh_theme(self):
        ac=T()["accent"]; ac2=T()["accent2"]
        self._welcome.setStyleSheet(f"color:{ac};font-size:14px;font-weight:bold;font-family:monospace;background:transparent;letter-spacing:2px;")
        self._clock.setStyleSheet(f"color:{ac2};font-size:14px;font-weight:bold;font-family:monospace;background:transparent;")
        self._track_title.setStyleSheet(f"color:{ac2};font-size:10px;font-weight:bold;font-family:monospace;background:transparent;")
        for b in [self._btn_prev,self._btn_next]: b.setStyleSheet(self._bs())
    def paintEvent(self,_):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(0,4,14,252))
        painter.setPen(QPen(ACA(88),1)); painter.drawLine(0,self.height()-1,self.width(),self.height()-1); painter.end()

# ──────────────────────────────────────────────────────────────────
#  NAV BAR (inside centre panel)
# ──────────────────────────────────────────────────────────────────
class NavBar(QWidget):
    tab_clicked=pyqtSignal(str)
    TABS=[("home","⬡ HOME","1"),("apps","◈ APPS","2"),("roms","🎮 ROMS","3"),("stream","🌙 STREAM","4"),("settings","⚙ SETTINGS","5")]
    def __init__(self,p=None):
        super().__init__(p); self.setFixedHeight(38); self._btns={}
        lay=QHBoxLayout(self); lay.setContentsMargins(0,2,0,2); lay.setSpacing(3)
        for key,label,hint in self.TABS:
            b=_NavBtn(f"{label} [{hint}]",key); b.clicked.connect(lambda _,k=key:self.tab_clicked.emit(k)); self._btns[key]=b; lay.addWidget(b)
        lay.addStretch()
    def set_active(self,key):
        for k,b in self._btns.items(): b.set_active(k==key)
    def paintEvent(self,_):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(0,4,14,220)); painter.setPen(QPen(ACA(55),1)); painter.drawLine(0,self.height()-1,self.width(),self.height()-1); painter.end()

class _NavBtn(QPushButton):
    def __init__(self,text,key,p=None):
        super().__init__(text,p); self._key=key; self._active=False; self._hov=False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); self.setFixedHeight(32); self.setMinimumWidth(95)
    def set_active(self,v): self._active=v; self.update()
    def enterEvent(self,e): self._hov=True; self.update()
    def leaveEvent(self,e): self._hov=False; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); path=QPainterPath()
        path.moveTo(7,0); path.lineTo(w,0); path.lineTo(w-7,h); path.lineTo(0,h); path.closeSubpath()
        act=self._active or self._hov; painter.setBrush(QBrush(ACA(30 if act else 0))); painter.setPen(QPen(ACA(175 if act else 50),1)); painter.drawPath(path)
        f=QFont("monospace",6); f.setBold(act); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,0.8); painter.setFont(f); painter.setPen(QPen(AC() if act else ACA(85)))
        painter.drawText(0,0,w,h,Qt.AlignmentFlag.AlignCenter,self.text())
        if act: painter.setPen(QPen(AC2(),2)); painter.drawLine(4,h-2,w-4,h-2)
        painter.end()

# ──────────────────────────────────────────────────────────────────
#  LEFT PANEL — quick launch (most-used)
# ──────────────────────────────────────────────────────────────────
class LeftPanel(QWidget):
    action=pyqtSignal(str)
    def __init__(self,p=None):
        super().__init__(p); self.setFixedWidth(185); self._build()
    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(6,8,6,8); lay.setSpacing(6)
        lay.addWidget(SectionHdr("QUICK LAUNCH"))
        self._grid_w=QWidget(); self._grid=QGridLayout(self._grid_w); self._grid.setSpacing(5); self._grid.setContentsMargins(0,0,0,0)
        lay.addWidget(self._grid_w); lay.addStretch(); self.refresh()
    def refresh(self):
        while self._grid.count():
            item=self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for i,key in enumerate(top_apps(8)):
            icon,label,sub=ALL_APPS.get(key,("🔷",key.split(":")[-1].upper(),""))
            tile=AppTile(icon,label,sub,key,size=82); tile.clicked.connect(self._on_tile); self._grid.addWidget(tile,i//2,i%2)
    def _on_tile(self,action): record_launch(action); self.refresh(); self.action.emit(action)
    def paintEvent(self,_):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(0,5,15,175)); painter.setPen(QPen(ACA(45),1)); painter.drawLine(self.width()-1,0,self.width()-1,self.height()); painter.end()

# ──────────────────────────────────────────────────────────────────
#  STAT MINI
# ──────────────────────────────────────────────────────────────────
class StatMini(QWidget):
    def __init__(self,label,p=None):
        super().__init__(p); self._label=label; self._val="--"; self._bar=0.0; self._warn=False
        self.setFixedHeight(58); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
    def set_val(self,val,bar=0.0,warn=False): self._val=str(val); self._bar=bar; self._warn=warn; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); painter.setBrush(QBrush(QColor(0,10,25,185))); painter.setPen(QPen(ACA(52),1)); painter.drawRect(0,0,w-1,h-1)
        g=QLinearGradient(0,0,w,0); g.setColorAt(0,QColor(0,0,0,0)); g.setColorAt(0.5,ACA(65)); g.setColorAt(1,QColor(0,0,0,0))
        painter.setPen(QPen(QBrush(g),1)); painter.drawLine(0,0,w,0)
        f=QFont("monospace",5); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,1.5); painter.setFont(f); painter.setPen(QPen(ACA(95)))
        painter.drawText(0,4,w,12,Qt.AlignmentFlag.AlignCenter,self._label)
        vc=QColor("#ff4444") if self._warn else AC2(); f2=QFont("monospace",11); f2.setBold(True); painter.setFont(f2); painter.setPen(QPen(vc))
        painter.drawText(0,13,w,22,Qt.AlignmentFlag.AlignCenter,self._val)
        bx,by,bw,bh=5,h-8,w-10,3; painter.setBrush(QBrush(ACA(20))); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(bx,by,bw,bh,1,1)
        if self._bar>0:
            g2=QLinearGradient(bx,0,bx+bw,0); g2.setColorAt(0,AC()); g2.setColorAt(1,AC2()); painter.setBrush(QBrush(g2)); painter.drawRoundedRect(bx,by,int(bw*self._bar),bh,1,1)
        painter.end()

# ──────────────────────────────────────────────────────────────────
#  NOTIFICATION ROW
# ──────────────────────────────────────────────────────────────────
class NotifRow(QWidget):
    def __init__(self,icon,title,body,ts,p=None):
        super().__init__(p); self.setFixedHeight(46)
        self.setStyleSheet("background:rgba(0,8,20,0.75);border:1px solid rgba(0,200,255,0.18);")
        lay=QHBoxLayout(self); lay.setContentsMargins(8,4,8,4); lay.setSpacing(7)
        ic=QLabel(icon); ic.setStyleSheet("font-size:14px;background:transparent;"); ic.setFixedSize(22,22); lay.addWidget(ic)
        tc=QVBoxLayout(); tc.setSpacing(1)
        t=QLabel(title); t.setStyleSheet(f"color:{T()['accent']};font-size:7px;font-weight:bold;font-family:monospace;background:transparent;")
        b=QLabel(body); b.setStyleSheet("color:rgba(0,200,255,0.5);font-size:6px;font-family:monospace;background:transparent;"); b.setWordWrap(True)
        tc.addWidget(t); tc.addWidget(b); lay.addLayout(tc,1)
        tsl=QLabel(ts); tsl.setStyleSheet("color:rgba(0,200,255,0.28);font-size:6px;font-family:monospace;background:transparent;"); lay.addWidget(tsl)

# ──────────────────────────────────────────────────────────────────
#  TAB PAGES
# ──────────────────────────────────────────────────────────────────
class HomePage(QWidget):
    action=pyqtSignal(str)
    def __init__(self,p=None):
        super().__init__(p); self._build()
    def _build(self):
        root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(0,0,6,0); lay.setSpacing(7)
        lay.addWidget(SectionHdr("SYSTEM STATUS"))
        sb=QWidget(); sb.setStyleSheet(PS()); sl=QVBoxLayout(sb); sl.setContentsMargins(12,8,12,8); sl.setSpacing(3)
        for txt in ["✓  Nova OS v6 running natively (PyQt6)","✓  Stats server active on :7777","✓  All services nominal"]:
            l=QLabel(txt); l.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-family:monospace;background:transparent;"); sl.addWidget(l)
        lay.addWidget(sb)
        lay.addWidget(SectionHdr("RECENT ACTIVITY"))
        self._act_w=QWidget(); self._act_l=QVBoxLayout(self._act_w); self._act_l.setContentsMargins(0,0,0,0); self._act_l.setSpacing(3)
        ph=QLabel("No recent activity"); ph.setStyleSheet("color:rgba(0,200,255,0.32);font-size:7px;font-family:monospace;background:transparent;"); self._act_l.addWidget(ph)
        lay.addWidget(self._act_w); lay.addStretch()
        scroll=make_scroll(root); ml=QVBoxLayout(self); ml.setContentsMargins(0,0,0,0); ml.addWidget(scroll)
    def log(self,msg):
        while self._act_l.count()>6:
            item=self._act_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        now=datetime.datetime.now().strftime("%H:%M:%S")
        l=QLabel(f"[{now}]  {msg}"); l.setStyleSheet(f"color:{T()['accent']};font-size:7px;font-family:monospace;background:transparent;"); self._act_l.addWidget(l)

class AppsPage(QWidget):
    action=pyqtSignal(str)
    GAMING=[("🌙","MOONLIGHT","PC Stream","ap:moonlight"),("🕹","RETROARCH","Multi-System","ap:retroarch"),("🎮","GODOT","Pi-Apps","ap:godot"),("🕹","BATOCERA","Emu Distro","ap:batocera"),("💾","ROM LIB","Library","sc:roms")]
    MEDIA=[("🎵","RASPOTIFY","Spotify Connect","ap:raspotify"),("💬","VESKTOP","Discord ARM64","ap:vesktop"),("🦊","FIREFOX","Browser","ap:firefox"),("🎬","VLC","Media Player","ap:vlc"),("▶","YOUTUBE","Via Firefox","ap:youtube")]
    SYSTEM=[("💻","TERMINAL","CLI","ap:terminal"),("📁","FILES","Manager","ap:files"),("📡","NETWORK","WiFi","ap:network"),("🔵","BLUETOOTH","Pair","ap:bluetooth"),("⚙","SETTINGS","Config","sc:settings")]
    def __init__(self,p=None):
        super().__init__(p); root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(0,0,6,0); lay.setSpacing(7)
        warn=QWidget(); warn.setStyleSheet("background:rgba(255,140,0,0.09);border:1px solid rgba(255,140,0,0.4);")
        wl=QVBoxLayout(warn); wl.setContentsMargins(10,6,10,6)
        wt=QLabel("⚠  Spotify desktop and Discord desktop are NOT available for ARM64. Use Raspotify + Vesktop instead.")
        wt.setStyleSheet("color:#ffaa33;font-size:7px;background:transparent;"); wt.setWordWrap(True); wl.addWidget(wt); lay.addWidget(warn)
        for title,apps in [("STREAMING & GAMING",self.GAMING),("MEDIA & COMMS",self.MEDIA),("SYSTEM TOOLS",self.SYSTEM)]:
            lay.addWidget(SectionHdr(title)); grid=QGridLayout(); grid.setSpacing(6)
            for i,(icon,lbl,sub,act) in enumerate(apps):
                tile=AppTile(icon,lbl,sub,act,size=88); tile.clicked.connect(self.action); grid.addWidget(tile,i//5,i%5)
            lay.addLayout(grid)
        lay.addStretch(); scroll=make_scroll(root); ml=QVBoxLayout(self); ml.setContentsMargins(0,0,0,0); ml.addWidget(scroll)

class RomsPage(QWidget):
    action=pyqtSignal(str)
    SYSTEMS=[("🎮","PS1","Needs BIOS","rom:ps1"),("🕹","PS2","Experimental","rom:ps2"),("📱","PSP","PPSSPP","rom:psp"),("🕹","NES","1983","rom:nes"),("🎮","SNES","1990","rom:snes"),("🎮","N64","1996","rom:n64"),("📟","GBA","2001","rom:gba"),("📟","NDS","Batocera","rom:nds"),("🎮","GENESIS","1988","rom:genesis"),("🪐","SATURN","Unreliable","rom:saturn"),("💫","DREAMCAST","1998","rom:dreamcast"),("🕹","ARCADE","MAME","rom:arcade"),("🟩","GB","1989","rom:gameboy"),("🟦","GBC","1998","rom:gbc"),("🎯","WII","Batocera","rom:wii"),("🎮","WII U","x86 only","rom:wiiu"),("🎮","SWITCH","Too weak","rom:switch"),("📟","3DS","2011","rom:3ds"),("📺","ATARI","1977","rom:atari"),("💿","SEGA CD","BIOS","rom:segacd")]
    def __init__(self,p=None):
        super().__init__(p); root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(0,0,6,0); lay.setSpacing(7)
        legend=QHBoxLayout()
        for txt,col in [("■ WORKS","#00ff80"),("■ PARTIAL","#ffaa33"),("■ N/A","#ff5555")]:
            l=QLabel(txt); l.setStyleSheet(f"color:{col};font-size:7px;background:transparent;"); legend.addWidget(l)
        legend.addStretch(); lay.addLayout(legend); lay.addWidget(SectionHdr("ROM LIBRARY"))
        grid=QGridLayout(); grid.setSpacing(5)
        for i,(icon,lbl,sub,act) in enumerate(self.SYSTEMS):
            tile=AppTile(icon,lbl,sub,act,size=76); tile.clicked.connect(self.action); grid.addWidget(tile,i//5,i%5)
        lay.addLayout(grid); lay.addStretch(); scroll=make_scroll(root); ml=QVBoxLayout(self); ml.setContentsMargins(0,0,0,0); ml.addWidget(scroll)

class StreamPage(QWidget):
    action=pyqtSignal(str)
    def __init__(self,p=None):
        super().__init__(p); root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(0,0,6,0); lay.setSpacing(8)
        hero=QWidget(); hero.setStyleSheet(PS()); hl=QHBoxLayout(hero); hl.setContentsMargins(14,12,14,12); hl.setSpacing(10)
        ml=QLabel("🌙"); ml.setStyleSheet("font-size:34px;background:transparent;"); ml.setFixedSize(52,52); hl.addWidget(ml)
        tc=QVBoxLayout()
        t=QLabel("MOONLIGHT STREAMING"); t.setStyleSheet(f"color:{T()['accent2']};font-size:13px;font-weight:bold;font-family:monospace;background:transparent;")
        d=QLabel("Stream PC games to Pi 5 over LAN. Works with Sunshine (free, any GPU).\n⚠  Console-only boot: eglfs.json fix applied by installer automatically."); d.setStyleSheet("color:rgba(0,200,255,0.58);font-size:7px;background:transparent;"); d.setWordWrap(True)
        tc.addWidget(t); tc.addWidget(d); hl.addLayout(tc,1); btn=GlowBtn("LAUNCH ▶"); btn.clicked.connect(lambda:self.action.emit("ap:moonlight")); hl.addWidget(btn); lay.addWidget(hero)
        lay.addWidget(SectionHdr("SETUP STEPS")); steps=QHBoxLayout(); steps.setSpacing(7)
        for num,title,body in [("01","HOST PC","Install Sunshine on Windows/Linux/Mac. Same LAN as Pi. Ethernet recommended."),("02","INSTALL","Run Nova OS installer — Moonlight + eglfs.json set up automatically. Use moonlight-nova."),("03","PAIR","Moonlight → Add Host → PC IP → enter PIN in Sunshine web UI (port 47990).")]:
            w=QWidget(); w.setStyleSheet(PS()); wl=QVBoxLayout(w); wl.setContentsMargins(10,10,10,10); wl.setSpacing(3)
            nl=QLabel(num); nl.setStyleSheet("color:rgba(0,200,255,0.25);font-size:22px;font-weight:bold;font-family:monospace;background:transparent;")
            tl=QLabel(title); tl.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-weight:bold;font-family:monospace;background:transparent;")
            bl=QLabel(body); bl.setStyleSheet("color:rgba(0,200,255,0.48);font-size:7px;background:transparent;"); bl.setWordWrap(True)
            wl.addWidget(nl); wl.addWidget(tl); wl.addWidget(bl); steps.addWidget(w)
        lay.addLayout(steps); lay.addStretch(); scroll=make_scroll(root); ml2=QVBoxLayout(self); ml2.setContentsMargins(0,0,0,0); ml2.addWidget(scroll)

class ToggleSwitch(QWidget):
    toggled=pyqtSignal(bool)
    def __init__(self,on=True,p=None): super().__init__(p); self._on=on; self.setFixedSize(42,20); self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._on=not self._on; self.toggled.emit(self._on); self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); painter.setBrush(QBrush(ACA(48 if self._on else 15))); painter.setPen(QPen(AC() if self._on else ACA(50),1)); painter.drawRoundedRect(0,0,w-1,h-1,10,10)
        kx=w-18 if self._on else 2; painter.setBrush(QBrush(AC() if self._on else ACA(55))); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(kx,2,16,16); painter.end()

class ScaleSliderRow(QWidget):
    """A labelled slider row used in the scaling settings panel."""
    value_changed = pyqtSignal(int)

    def __init__(self, label, sub, lo, hi, default, unit="", p=None):
        super().__init__(p)
        self._unit = unit
        self.setStyleSheet(PS())
        lay = QVBoxLayout(self); lay.setContentsMargins(10,8,10,8); lay.setSpacing(5)
        # Header row: label + current value
        hdr = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-weight:bold;font-family:monospace;background:transparent;letter-spacing:1px;")
        self._val_lbl = QLabel(f"{default}{unit}")
        self._val_lbl.setStyleSheet(f"color:{T()['accent2']};font-size:11px;font-weight:bold;font-family:monospace;background:transparent;")
        hdr.addWidget(lbl); hdr.addStretch(); hdr.addWidget(self._val_lbl)
        lay.addLayout(hdr)
        # Slider
        self._slider = _GlowSlider(Qt.Orientation.Horizontal, lo, hi, default)
        self._slider.valueChanged.connect(self._on_change)
        lay.addWidget(self._slider)
        # Sub label
        s = QLabel(sub)
        s.setStyleSheet("color:rgba(0,200,255,0.38);font-size:6px;font-family:monospace;background:transparent;")
        lay.addWidget(s)

    def _on_change(self, v):
        self._val_lbl.setText(f"{v}{self._unit}")
        self.value_changed.emit(v)

    def set_value(self, v):
        self._slider.blockSignals(True)
        self._slider.setValue(v)
        self._slider.blockSignals(False)
        self._val_lbl.setText(f"{v}{self._unit}")


class _GlowSlider(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, orientation, lo, hi, val, p=None):
        super().__init__(p)
        self._lo=lo; self._hi=hi; self._val=val
        self.setFixedHeight(22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._drag=False

    def value(self): return self._val
    def setValue(self, v): self._val=max(self._lo,min(self._hi,v)); self.update()

    def _pos_to_val(self, x):
        frac = max(0.0, min(1.0, (x - 10) / max(1, self.width() - 20)))
        return int(self._lo + frac * (self._hi - self._lo))

    def mousePressEvent(self, e):
        if e.button()==Qt.MouseButton.LeftButton:
            self._drag=True; self._val=self._pos_to_val(e.position().x())
            self.valueChanged.emit(self._val); self.update()

    def mouseMoveEvent(self, e):
        if self._drag:
            self._val=self._pos_to_val(e.position().x())
            self.valueChanged.emit(self._val); self.update()

    def mouseReleaseEvent(self, e): self._drag=False

    def paintEvent(self, _):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        # Track
        painter.setBrush(QBrush(ACA(18))); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, h//2-3, w-20, 6, 3, 3)
        # Fill
        frac=(self._val-self._lo)/max(1,self._hi-self._lo)
        fw=int((w-20)*frac)
        if fw>0:
            g=QLinearGradient(10,0,w-10,0); g.setColorAt(0,AC()); g.setColorAt(1,AC2())
            painter.setBrush(QBrush(g)); painter.drawRoundedRect(10,h//2-3,fw,6,3,3)
        # Knob
        kx=10+fw
        painter.setBrush(QBrush(AC2())); painter.setPen(QPen(ACA(180),1))
        painter.drawEllipse(kx-8, h//2-8, 16, 16)
        painter.end()


class ScalePresetRow(QWidget):
    """Row of preset buttons."""
    preset_clicked = pyqtSignal(str, int)   # label, value

    def __init__(self, presets, p=None):
        # presets = list of (label, sublabel, value)
        super().__init__(p)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)
        self._btns = []
        for label, sub, val in presets:
            btn = _PresetBtn(label, sub, val)
            btn.clicked.connect(lambda _,l=label,v=val: self.preset_clicked.emit(l,v))
            self._btns.append((val, btn)); lay.addWidget(btn)

    def set_active_val(self, val):
        for v,b in self._btns: b.set_active(v==val)


class _PresetBtn(QPushButton):
    def __init__(self, label, sub, val, p=None):
        super().__init__(p); self._label=label; self._sub=sub; self._val=val; self._active=False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); self.setFixedHeight(40)
        self._hov=False
    def set_active(self,v): self._active=v; self.update()
    def enterEvent(self,e): self._hov=True; self.update()
    def leaveEvent(self,e): self._hov=False; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        hi=self._active or self._hov
        painter.setBrush(QBrush(ACA(45 if self._active else 22 if self._hov else 10)))
        painter.setPen(QPen(ACA(210 if self._active else 140 if self._hov else 60),1))
        painter.drawRect(0,0,w-1,h-1)
        f=QFont("monospace",7); f.setBold(True); painter.setFont(f)
        painter.setPen(QPen(AC2() if self._active else AC() if self._hov else ACA(160)))
        painter.drawText(0,2,w,h//2,Qt.AlignmentFlag.AlignCenter, self._label)
        f2=QFont("monospace",5); painter.setFont(f2); painter.setPen(QPen(ACA(110)))
        painter.drawText(0,h//2,w,h//2,Qt.AlignmentFlag.AlignCenter, self._sub)
        painter.end()


class SettingsPage(QWidget):
    toggle_changed  = pyqtSignal(str, bool)
    scale_changed   = pyqtSignal(int)        # 60-150 (percent)
    font_changed    = pyqtSignal(int)        # px
    tile_changed    = pyqtSignal(int)        # px
    layout_changed  = pyqtSignal(str)        # "focus"|"compact"|"full"

    def __init__(self, p=None):
        super().__init__(p)
        root = QWidget()
        lay = QVBoxLayout(root); lay.setContentsMargins(0,0,6,0); lay.setSpacing(7)

        # ── SCALING ──────────────────────────────────────
        lay.addWidget(SectionHdr("SCALING  //  7\" TOUCHSCREEN & SMALL DISPLAYS"))

        # UI Scale
        self._scale_row = ScaleSliderRow("UI SCALE","Scales all panels, text and tiles  —  use 70–80% for 7\" screens",60,150,100,"%")
        self._scale_presets = ScalePresetRow([("70%","7\" TOUCH",70),("85%","COMPACT",85),("100%","DEFAULT",100),("120%","LARGE",120),("150%","HUGE",150)])
        self._scale_presets.set_active_val(100)
        self._scale_row.value_changed.connect(self._on_scale)
        self._scale_presets.preset_clicked.connect(lambda _,v: self._apply_scale(v))
        lay.addWidget(self._scale_row); lay.addWidget(self._scale_presets)

        # Font Size
        self._font_row = ScaleSliderRow("FONT SIZE","Base font size — independent of UI scale",7,16,10,"px")
        self._font_row.value_changed.connect(lambda v: self.font_changed.emit(v))
        lay.addWidget(self._font_row)

        # Tile Size
        self._tile_row = ScaleSliderRow("TILE SIZE","App / ROM tile size — larger = easier to tap on touchscreens",48,120,76,"px")
        self._tile_row.value_changed.connect(lambda v: self.tile_changed.emit(v))
        lay.addWidget(self._tile_row)

        # Panel Layout
        lay.addWidget(SectionHdr("PANEL LAYOUT"))
        layout_box = QWidget(); layout_box.setStyleSheet(PS())
        lb = QVBoxLayout(layout_box); lb.setContentsMargins(10,8,10,8); lb.setSpacing(6)
        ll = QLabel("PANEL LAYOUT")
        ll.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-weight:bold;font-family:monospace;background:transparent;letter-spacing:1px;")
        lb.addWidget(ll)
        self._layout_presets = ScalePresetRow([
            ("FOCUS","Centre only",0),
            ("COMPACT","Left+Centre",1),
            ("FULL","3 columns",2),
        ])
        self._layout_presets.set_active_val(2)
        self._layout_presets.preset_clicked.connect(self._on_layout)
        lb.addWidget(self._layout_presets)
        ls = QLabel("Hide side panels to maximise content on small screens")
        ls.setStyleSheet("color:rgba(0,200,255,0.38);font-size:6px;font-family:monospace;background:transparent;")
        lb.addWidget(ls); lay.addWidget(layout_box)

        # ── DISPLAY & PERFORMANCE ─────────────────────────
        lay.addWidget(SectionHdr("DISPLAY & PERFORMANCE"))
        for key,label,sub,default in [
            ("scanlines","SCANLINES","CRT overlay effect",True),
            ("particles","PARTICLES","Ambient particle field",True),
            ("flicker","FLICKER","Screen flicker",True),
            ("reduceani","REDUCE ANIMATIONS","Better Pi 5 performance",False),
        ]:
            row=QWidget(); row.setStyleSheet(PS()); row.setFixedHeight(44)
            rl=QHBoxLayout(row); rl.setContentsMargins(12,0,12,0)
            tc=QVBoxLayout(); tc.setSpacing(1)
            l=QLabel(label); l.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-weight:bold;font-family:monospace;background:transparent;")
            s=QLabel(sub);   s.setStyleSheet("color:rgba(0,200,255,0.38);font-size:6px;font-family:monospace;background:transparent;")
            tc.addWidget(l); tc.addWidget(s); rl.addLayout(tc); rl.addStretch()
            tog=ToggleSwitch(default); tog.toggled.connect(lambda on,k=key: self.toggle_changed.emit(k,on))
            rl.addWidget(tog); lay.addWidget(row)

        # ── ABOUT ─────────────────────────────────────────
        lay.addWidget(SectionHdr("ABOUT"))
        about=QWidget(); about.setStyleSheet(PS()); al=QVBoxLayout(about); al.setContentsMargins(12,8,12,8)
        at=QLabel(f"Nova OS v{VERSION}  |  Raspberry Pi OS Bookworm 64-bit ARM64\n"
                  "Hardware: Pi 5 BCM2712 Cortex-A76 @ 2.4GHz · 4/8GB LPDDR4X\n"
                  "Apps: Firefox ✓  Moonlight ✓  RetroArch ✓  Godot ✓  Raspotify ✓  Vesktop ✓\n"
                  "Not on ARM64: Spotify desktop ✗  Discord desktop ✗  Wii U ✗  Switch ✗")
        at.setStyleSheet("color:rgba(0,200,255,0.48);font-size:7px;font-family:monospace;background:transparent;")
        at.setWordWrap(True); al.addWidget(at); lay.addWidget(about)

        lay.addStretch()
        scroll=make_scroll(root); ml=QVBoxLayout(self); ml.setContentsMargins(0,0,0,0); ml.addWidget(scroll)

    def _on_scale(self, v):
        self._scale_presets.set_active_val(v)
        self.scale_changed.emit(v)

    def _apply_scale(self, v):
        self._scale_row.set_value(v)
        self._scale_presets.set_active_val(v)
        self.scale_changed.emit(v)

    def _on_layout(self, label, _val):
        modes = {"FOCUS":"focus","COMPACT":"compact","FULL":"full"}
        self.layout_changed.emit(modes.get(label, "full"))

# ──────────────────────────────────────────────────────────────────
#  RIGHT PANEL
# ──────────────────────────────────────────────────────────────────
class BrightnessSlider(QWidget):
    changed=pyqtSignal(float)
    def __init__(self,p=None): super().__init__(p); self._v=1.0; self.setFixedHeight(26); self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); self._drag=False
    def mousePressEvent(self,e): self._drag=True; self._set(e.position().x())
    def mouseMoveEvent(self,e):
        if self._drag: self._set(e.position().x())
    def mouseReleaseEvent(self,e): self._drag=False
    def _set(self,x): self._v=max(0.1,min(1.0,x/self.width())); self.changed.emit(self._v); self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); painter.setBrush(QBrush(ACA(20))); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(0,h//2-3,w,6,3,3)
        fw=int(w*self._v); g=QLinearGradient(0,0,w,0); g.setColorAt(0,AC()); g.setColorAt(1,AC2()); painter.setBrush(QBrush(g)); painter.drawRoundedRect(0,h//2-3,fw,6,3,3)
        painter.setBrush(QBrush(AC())); painter.drawEllipse(fw-8,h//2-8,16,16); painter.end()

class ThemeChip(QPushButton):
    def __init__(self,name,ac,ac2,p=None):
        super().__init__(p); self._name=name; self._ac=ac; self._ac2=ac2; self._sel=False; self.setFixedSize(56,24); self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    def set_sel(self,v): self._sel=v; self.update()
    def paintEvent(self,_):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); g=QLinearGradient(0,0,w,0); g.setColorAt(0,QColor(self._ac)); g.setColorAt(1,QColor(self._ac2))
        painter.setBrush(QBrush(g)); bc=QColor(self._ac); bc.setAlpha(200 if self._sel else 75); painter.setPen(QPen(bc,2 if self._sel else 1)); painter.drawRoundedRect(0,0,w-1,h-1,3,3)
        f=QFont("monospace",4); f.setBold(True); painter.setFont(f); painter.setPen(QPen(QColor(0,0,0,210))); painter.drawText(0,0,w,h,Qt.AlignmentFlag.AlignCenter,self._name[:7]); painter.end()

class RightPanel(QWidget):
    theme_changed=pyqtSignal(str); brightness_changed=pyqtSignal(float); action=pyqtSignal(str)
    def __init__(self,p=None):
        super().__init__(p); self.setFixedWidth(215); self._pending_update=None; self._build()
    def _build(self):
        root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(6,8,6,8); lay.setSpacing(9)
        # Discord
        lay.addWidget(SectionHdr("DISCORD"))
        self._disc_w=QWidget(); self._disc_l=QVBoxLayout(self._disc_w); self._disc_l.setContentsMargins(0,0,0,0); self._disc_l.setSpacing(3)
        ph=QLabel("Checking…"); ph.setStyleSheet("color:rgba(0,200,255,0.38);font-size:7px;font-family:monospace;background:transparent;"); self._disc_l.addWidget(ph)
        lay.addWidget(make_scroll(self._disc_w,80))
        # Quick settings
        lay.addWidget(SectionHdr("QUICK SETTINGS"))
        bright_box=QWidget(); bright_box.setStyleSheet(PS()); bl=QVBoxLayout(bright_box); bl.setContentsMargins(8,6,8,6); bl.setSpacing(4)
        bl_lbl=QLabel("☀  BRIGHTNESS"); bl_lbl.setStyleSheet(f"color:{T()['accent']};font-size:7px;font-weight:bold;font-family:monospace;background:transparent;"); bl.addWidget(bl_lbl)
        self._bright=BrightnessSlider(); self._bright.changed.connect(self.brightness_changed); bl.addWidget(self._bright); lay.addWidget(bright_box)
        theme_box=QWidget(); theme_box.setStyleSheet(PS()); tbl=QVBoxLayout(theme_box); tbl.setContentsMargins(8,6,8,6); tbl.setSpacing(5)
        tl=QLabel("🎨  THEME"); tl.setStyleSheet(f"color:{T()['accent']};font-size:7px;font-weight:bold;font-family:monospace;background:transparent;"); tbl.addWidget(tl)
        chip_grid=QGridLayout(); chip_grid.setSpacing(4); self._chips={}
        for i,(name,t) in enumerate(THEMES.items()):
            chip=ThemeChip(name,t["accent"],t["accent2"]); chip.set_sel(name==CURRENT_THEME)
            chip.clicked.connect(lambda _,n=name:self.theme_changed.emit(n)); self._chips[name]=chip; chip_grid.addWidget(chip,i//2,i%2)
        tbl.addLayout(chip_grid); lay.addWidget(theme_box)
        # Updates
        lay.addWidget(SectionHdr("UPDATES"))
        upd_box=QWidget(); upd_box.setStyleSheet(PS()); ul=QVBoxLayout(upd_box); ul.setContentsMargins(8,6,8,6); ul.setSpacing(5)
        self._upd_lbl=QLabel("Insert USB with novaos.py to update"); self._upd_lbl.setStyleSheet("color:rgba(0,200,255,0.45);font-size:7px;font-family:monospace;background:transparent;"); self._upd_lbl.setWordWrap(True); ul.addWidget(self._upd_lbl)
        self._check_btn=GlowBtn("🔍  CHECK USB",small=True); self._check_btn.clicked.connect(self._check_usb); ul.addWidget(self._check_btn)
        self._apply_btn=GlowBtn("⬆  APPLY UPDATE",small=True); self._apply_btn.clicked.connect(self._apply_update); self._apply_btn.setVisible(False); ul.addWidget(self._apply_btn)
        lay.addWidget(upd_box)
        # Last Discord project
        lay.addWidget(SectionHdr("LAST PROJECT"))
        proj_box=QWidget(); proj_box.setStyleSheet(PS()); pl=QVBoxLayout(proj_box); pl.setContentsMargins(8,6,8,6); pl.setSpacing(4)
        self._proj_lbl=QLabel("No recent project"); self._proj_lbl.setStyleSheet(f"color:{T()['accent']};font-size:8px;font-weight:bold;font-family:monospace;background:transparent;"); self._proj_lbl.setWordWrap(True); pl.addWidget(self._proj_lbl)
        open_btn=GlowBtn("▶  OPEN IN VESKTOP",small=True); open_btn.clicked.connect(lambda:self.action.emit("ap:vesktop")); pl.addWidget(open_btn); lay.addWidget(proj_box)
        lay.addStretch(); scroll=make_scroll(root); ml=QVBoxLayout(self); ml.setContentsMargins(0,0,0,0); ml.addWidget(scroll)

    def _check_usb(self):
        found=None
        try:
            for mount in USB_ROOT.iterdir():
                if mount.is_dir():
                    for f in mount.rglob("novaos.py"): found=f; break
                if found: break
        except: pass
        if found:
            self._pending_update=found; self._upd_lbl.setText(f"Found: {found.name}\nTap Apply to install."); self._apply_btn.setVisible(True)
        else:
            self._upd_lbl.setText("No update found.\nInsert USB with novaos.py and try again."); self._apply_btn.setVisible(False)

    def _apply_update(self):
        if self._pending_update:
            try:
                shutil.copy2(self._pending_update, APP_DIR/"novaos.py")
                self._upd_lbl.setText("✓ Updated!\nRestart Nova OS to apply."); self._apply_btn.setVisible(False)
            except Exception as e: self._upd_lbl.setText(f"✗ Failed:\n{e}")

    def set_discord(self,msgs):
        while self._disc_l.count():
            item=self._disc_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for m in (msgs or [])[:4]:
            w=QWidget(); w.setStyleSheet("background:rgba(0,5,15,0.8);border:1px solid rgba(0,200,255,0.18);border-radius:2px;")
            wl=QVBoxLayout(w); wl.setContentsMargins(6,3,6,3); wl.setSpacing(1)
            srv=QLabel(f"💬 {m.get('server','?')} #{m.get('ch','?')}"); srv.setStyleSheet(f"color:{T()['accent']};font-size:6px;font-weight:bold;font-family:monospace;background:transparent;")
            msg=QLabel(m.get("msg","")); msg.setStyleSheet("color:rgba(0,200,255,0.5);font-size:6px;font-family:monospace;background:transparent;"); msg.setWordWrap(True)
            wl.addWidget(srv); wl.addWidget(msg); self._disc_l.addWidget(w)

    def set_chips_active(self,name):
        for n,c in self._chips.items(): c.set_sel(n==name)

    def paintEvent(self,_):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(0,5,15,175)); painter.setPen(QPen(ACA(42),1)); painter.drawLine(0,0,0,self.height()); painter.end()

# ──────────────────────────────────────────────────────────────────
#  FOOTER
# ──────────────────────────────────────────────────────────────────
class Footer(QWidget):
    def __init__(self,p=None): super().__init__(p); self.setFixedHeight(21); self._ph=0.0; self._build(); t=QTimer(self); t.timeout.connect(self._tick); t.start(50)
    def _build(self):
        lay=QHBoxLayout(self); lay.setContentsMargins(14,0,14,0)
        self._left=QLabel("NOVA OS v6 // PI 5 ARM64 // ALL SYSTEMS NOMINAL"); self._left.setStyleSheet("color:rgba(0,200,255,0.28);font-size:6px;font-family:monospace;background:transparent;")
        self._date=QLabel("--/--/----"); self._date.setStyleSheet("color:rgba(0,200,255,0.28);font-size:6px;font-family:monospace;background:transparent;")
        self._theme_lbl=QLabel("● NOVA BLUE"); self._theme_lbl.setStyleSheet("color:rgba(0,200,255,0.28);font-size:6px;font-family:monospace;background:transparent;")
        lay.addWidget(self._left); lay.addStretch(); lay.addWidget(self._date); lay.addWidget(self._theme_lbl)
    def _tick(self): self._ph=(self._ph+0.06)%(math.pi*2); self.update()
    def update_date(self,t): self._date.setText(t)
    def update_theme(self,n): self._theme_lbl.setText(f"● {n}")
    def paintEvent(self,_):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(0,2,10,252)); painter.setPen(QPen(ACA(75),1)); painter.drawLine(0,0,self.width(),0)
        a=int((math.sin(self._ph)*0.5+0.5)*200+55); dc=AC2(); dc.setAlpha(a); painter.setBrush(QBrush(dc)); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(5,7,7,7); painter.end()

# ──────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ──────────────────────────────────────────────────────────────────
class NovaOS(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Nova OS v6"); self.setMinimumSize(1024,600); self._boot_start=time.time(); self._show_boot()

    def _show_boot(self):
        self._boot=BootScreen(); self._boot.finished.connect(self._boot_done); self.setCentralWidget(self._boot); self.showFullScreen()

    def _boot_done(self):
        self._build_ui(); self._start_workers()

    def _build_ui(self):
        central=QWidget(); self.setCentralWidget(central); central.setStyleSheet(f"background:{T()['bg']};")
        # Background
        self._grid=GridBG(central); self._pts=Particles(central); self._scan=Scanlines(central); self._corn=Corners(central)
        # Main layout
        main=QVBoxLayout(central); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        # Top bar
        self._topbar=TopBar()
        self._topbar.prev_clicked.connect(lambda:self._music.prev())
        self._topbar.next_clicked.connect(lambda:self._music.next())
        self._topbar.track_clicked.connect(self._music_toggle)
        main.addWidget(self._topbar)
        # Body
        body=QHBoxLayout(); body.setContentsMargins(8,6,8,4); body.setSpacing(6)
        self._left=LeftPanel(); self._left.action.connect(self._dispatch); body.addWidget(self._left)
        # Centre column
        centre_col=QWidget(); centre_col.setStyleSheet("background:transparent;")
        cc=QVBoxLayout(centre_col); cc.setContentsMargins(0,0,0,0); cc.setSpacing(5)
        # Stats row
        stats_row=QHBoxLayout(); stats_row.setSpacing(5)
        self._s_cpu=StatMini("CPU TEMP"); self._s_ram=StatMini("RAM"); self._s_disk=StatMini("DISK"); self._s_up=StatMini("UPTIME")
        for s in [self._s_cpu,self._s_ram,self._s_disk,self._s_up]: stats_row.addWidget(s)
        cc.addLayout(stats_row)
        # Nav bar
        self._nav=NavBar(); self._nav.tab_clicked.connect(self._show_tab); cc.addWidget(self._nav)
        # Stack
        self._stack=QStackedWidget(); self._stack.setStyleSheet("background:transparent;")
        self._pg_home=HomePage(); self._pg_apps=AppsPage(); self._pg_roms=RomsPage(); self._pg_stream=StreamPage(); self._pg_settings=SettingsPage()
        for pg in [self._pg_home,self._pg_apps,self._pg_roms,self._pg_stream,self._pg_settings]: self._stack.addWidget(pg)
        for pg in [self._pg_home,self._pg_apps,self._pg_roms,self._pg_stream]: pg.action.connect(self._dispatch)
        self._pg_settings.toggle_changed.connect(self._on_toggle)
        self._pg_settings.scale_changed.connect(self._on_scale)
        self._pg_settings.font_changed.connect(self._on_font)
        self._pg_settings.tile_changed.connect(self._on_tile_size)
        self._pg_settings.layout_changed.connect(self._on_layout)
        cc.addWidget(self._stack,1)
        # Pi notifications
        notif_lbl=SectionHdr("PI NOTIFICATIONS"); cc.addWidget(notif_lbl)
        self._notif_w=QWidget(); self._notif_l=QVBoxLayout(self._notif_w); self._notif_l.setContentsMargins(0,0,0,0); self._notif_l.setSpacing(3)
        for icon,title,body2 in [("📡","Network","WiFi connected — DHCP assigned"),("🌡","Thermal","CPU temperature nominal"),("💾","Storage","Boot drive healthy")]:
            self._notif_l.addWidget(NotifRow(icon,title,body2,"boot"))
        notif_scroll=make_scroll(self._notif_w,106); cc.addWidget(notif_scroll)
        body.addWidget(centre_col,1)
        # Right panel
        self._right=RightPanel(); self._right.theme_changed.connect(self._apply_theme); self._right.brightness_changed.connect(self._set_brightness); self._right.action.connect(self._dispatch); body.addWidget(self._right)
        body_w=QWidget(); body_w.setLayout(body); main.addWidget(body_w,1)
        # Footer
        self._footer=Footer(); main.addWidget(self._footer)
        # Toast
        self._toast=Toast(central)
        # Music engine (init early so it exists)
        self._music=MusicEngine(); self._music.track_changed.connect(self._on_track); self._music.play_state.connect(self._topbar.set_playing); self._music.start()
        t,a=self._music.current(); self._topbar.set_track(t,a,0,len(self._music._playlist))
        self._show_tab("home")

    def resizeEvent(self,e):
        super().resizeEvent(e)
        if hasattr(self,"_grid"):
            for w in [self._grid,self._pts,self._scan,self._corn]: w.setGeometry(0,0,self.width(),self.height())
        if hasattr(self,"_toast"): self._toast._reposition()

    def _show_tab(self,key):
        idx={"home":0,"apps":1,"roms":2,"stream":3,"settings":4}
        if key not in idx: return
        self._stack.setCurrentIndex(idx[key]); self._nav.set_active(key)

    def _dispatch(self,action):
        if not action: return
        record_launch(action); self._left.refresh()
        t,v=action.split(":",1)
        if t=="sc": self._show_tab(v)
        elif t=="ap": self._launch(v)
        elif t=="rom": self._launch_rom(v)

    NOT_SUP={"wiiu":"✗ Cemu is x86-only — not on Pi5","switch":"✗ Pi5 underpowered for Switch emulation","saturn":"⚠ Saturn has known boot failures on Pi5"}
    APP_WARN={"moonlight":"⚠ Use moonlight-nova — handles eglfs.json automatically","batocera":"⚠ Batocera needs its own SD card or USB","raspotify":"⚠ Control from Spotify on phone → Devices → Nova OS Pi5","vesktop":"⚠ Run the Nova OS installer to install Vesktop","godot":"⚠ Install via Pi-Apps → Games → Godot"}
    APP_CMD={"moonlight":["moonlight-nova"],"firefox":["firefox"],"vesktop":["vesktop"],"retroarch":["retroarch"],"vlc":["vlc"],"terminal":["lxterminal"],"files":["pcmanfm"],"network":["nm-connection-editor"],"bluetooth":["blueman-manager"],"youtube":["firefox","https://youtube.com"],"batocera":["firefox","https://batocera.org"]}

    def _launch(self,app):
        if app in self.APP_WARN: self._toast.show_msg(self.APP_WARN[app])
        name=app.upper().replace("-"," ")
        self._pg_home.log(f"Launched {name}")
        cmd=self.APP_CMD.get(app)
        if cmd:
            try: subprocess.Popen(cmd,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); (self._toast.show_msg(f"▶ LAUNCHING {name}…") if app not in self.APP_WARN else None)
            except FileNotFoundError: self._toast.show_msg(f"✗ {name} not found — run installer")
        else: self._toast.show_msg(f"▶ {name}…")

    def _launch_rom(self,system):
        if system in self.NOT_SUP: self._toast.show_msg(self.NOT_SUP[system]); return
        p=os.path.expanduser(f"~/RetroPie/roms/{system}/"); os.makedirs(p,exist_ok=True)
        try: subprocess.Popen(["pcmanfm",p],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass
        self._toast.show_msg(f"▶ ~/RetroPie/roms/{system}/")

    def _apply_theme(self,name):
        global CURRENT_THEME; CURRENT_THEME=name
        self._right.set_chips_active(name); self._footer.update_theme(name); self._topbar.refresh_theme()
        self.centralWidget().setStyleSheet(f"background:{T()['bg']};"); self._toast.show_msg(f"▶ THEME: {name}"); self.update()

    def _set_brightness(self,val):
        try:
            for d in Path("/sys/class/backlight").iterdir():
                mf=d/"max_brightness"
                if mf.exists():
                    with open(mf) as f: mx=int(f.read())
                    with open(d/"brightness","w") as f: f.write(str(int(mx*val)))
        except: pass

    def _on_toggle(self,key,on):
        if key=="scanlines": self._scan.setVisible(on)
        elif key=="particles": self._pts._on=on
        elif key=="reduceani": self._pts._timer if hasattr(self._pts,"_timer") else None
        self._toast.show_msg(f"{'▶ ON' if on else '▶ OFF'}: {key.upper()}")

    def _on_scale(self, pct):
        """Apply UI scale to the whole window via a zoom transform on the central body."""
        factor = pct / 100.0
        # Scale the body area (between topbar and footer) by adjusting font sizes
        # Qt doesn't have CSS zoom, so we scale via QGraphicsEffect-free approach:
        # set the font scale on the app and resize left/right panels
        left_w  = max(100, int(185 * factor))
        right_w = max(120, int(215 * factor))
        self._left.setFixedWidth(left_w)
        self._right.setFixedWidth(right_w)
        # Scale topbar and footer heights
        self._topbar.setFixedHeight(max(40, int(66 * factor)))
        self._footer.setFixedHeight(max(16, int(21 * factor)))
        self._toast.show_msg(f"▶ UI SCALE: {pct}%")

    def _on_font(self, px):
        """Bump the base font size used across labels."""
        # Re-style a few key labels
        ac = T()["accent"]; ac2 = T()["accent2"]
        self._topbar._welcome.setStyleSheet(
            f"color:{ac};font-size:{px+4}px;font-weight:bold;font-family:monospace;background:transparent;letter-spacing:2px;")
        self._topbar._clock.setStyleSheet(
            f"color:{ac2};font-size:{px+4}px;font-weight:bold;font-family:monospace;background:transparent;")
        self._toast.show_msg(f"▶ FONT SIZE: {px}px")

    def _on_tile_size(self, px):
        """Resize all app tiles in quick launch and tab pages."""
        # Rebuild quick launch with new tile size baked in via AppTile's fixed size
        # The AppTile size is set at construction — easiest to just rebuild the grid
        for tile in self._left._grid_w.findChildren(AppTile):
            tile.setFixedSize(px, max(40, px - 4))
        for tile in self._pg_apps.findChildren(AppTile):
            tile.setFixedSize(int(px * 1.15), max(48, int(px * 1.1)))
        for tile in self._pg_roms.findChildren(AppTile):
            tile.setFixedSize(px, max(40, px - 4))
        self._toast.show_msg(f"▶ TILE SIZE: {px}px")

    def _on_layout(self, mode):
        if mode == "focus":
            self._left.setVisible(False); self._right.setVisible(False)
            self._toast.show_msg("▶ LAYOUT: FOCUS — centre only")
        elif mode == "compact":
            self._left.setVisible(True); self._right.setVisible(False)
            self._toast.show_msg("▶ LAYOUT: COMPACT — left + centre")
        else:
            self._left.setVisible(True); self._right.setVisible(True)
            self._toast.show_msg("▶ LAYOUT: FULL — all 3 columns")

    def _on_track(self,title,artist,idx,total): self._topbar.set_track(title,artist,idx,total)
    def _music_toggle(self): self._music.play_pause()

    def _start_workers(self):
        # Clock
        self._clk=QTimer(self); self._clk.timeout.connect(self._tick_clock); self._clk.start(1000); self._tick_clock()
        # Stats
        self._stats=StatsWorker(); self._stats.updated.connect(self._on_stats); self._stats.start()
        # Discord
        self._disc=DiscordReader(); self._disc.notifications.connect(self._right.set_discord); self._disc.start()
        # USB check
        self._usb_t=QTimer(self); self._usb_t.timeout.connect(self._poll_usb); self._usb_t.start(8000)

    def _tick_clock(self):
        now=datetime.datetime.now()
        self._topbar.update_clock(now.strftime("%H:%M:%S")); self._footer.update_date(now.strftime("%d.%m.%Y"))
        uptime=int(time.time()-self._boot_start); h=uptime//3600; m=(uptime%3600)//60; s=uptime%60
        self._s_up.set_val(f"{h:02d}:{m:02d}:{s:02d}")

    def _on_stats(self,d):
        ct=d.get("cpu_temp"); rp=d.get("ram_pct"); dp=d.get("disk_pct")
        if ct is not None: self._s_cpu.set_val(f"{ct}°C",max(0,(ct-30)/50),ct>74)
        if rp is not None: self._s_ram.set_val(f"{rp:.0f}%",rp/100)
        if dp is not None: self._s_disk.set_val(f"{dp:.0f}%",dp/100)
        cpu=f"{ct}°C" if ct else "--°C"; ram=f"{rp:.0f}%" if rp else "--%"
        self._topbar.update_sysinfo(cpu,ram)
        if ct and ct>78:
            self._add_notif("🌡","THERMAL WARNING",f"CPU at {ct}°C — check cooling")

    def _add_notif(self,icon,title,body):
        while self._notif_l.count()>5:
            item=self._notif_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        now=datetime.datetime.now().strftime("%H:%M"); self._notif_l.addWidget(NotifRow(icon,title,body,now))

    def _poll_usb(self):
        try:
            for mount in USB_ROOT.iterdir():
                if mount.is_dir():
                    for f in mount.rglob("novaos.py"):
                        self._add_notif("💾","USB UPDATE","New novaos.py on USB — check Updates panel"); return
        except: pass

    def keyPressEvent(self,e):
        k=e.key()
        if k==Qt.Key.Key_1: self._show_tab("home")
        elif k==Qt.Key.Key_2: self._show_tab("apps")
        elif k==Qt.Key.Key_3: self._show_tab("roms")
        elif k==Qt.Key.Key_4: self._show_tab("stream")
        elif k==Qt.Key.Key_5: self._show_tab("settings")
        elif k==Qt.Key.Key_Escape and self._stack.currentIndex()!=0: self._show_tab("home")
        elif k==Qt.Key.Key_F11: self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif k==Qt.Key.Key_Q and (e.modifiers()&Qt.KeyboardModifier.ControlModifier): self.close()
        else: super().keyPressEvent(e)

def main():
    app=QApplication(sys.argv); app.setApplicationName("Nova OS")
    p=QPalette(); p.setColor(QPalette.ColorRole.Window,QColor("#000a1a")); p.setColor(QPalette.ColorRole.WindowText,QColor("#00c8ff")); app.setPalette(p)
    win=NovaOS(); sys.exit(app.exec())

if __name__=="__main__":
    main()
