"""Audio-reactive visualizers inspired by the reference screenshots."""
from __future__ import annotations
import math
from types import SimpleNamespace
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout, QWidget, QScrollArea

PRESETS = [
    ('gold','Золотая волна','wave',('#dba51a','#ffda47','#ffeab4')),
    ('aurora','Северное сияние','ribbon',('#7000ed','#d600df','#f6de32','#00c6ac')),
    ('violet','Фиолетовая лента','ribbon',('#6b10ae','#e300db','#410474')),
    ('ocean','Океан','ribbon',('#087b87','#13bbae','#b8d8d2')),
    ('green_bars','Зелёный эквалайзер','bars',('#054322','#4cad00','#d9ff17')),
    ('purple','Пурпурная волна','wave',('#6700d8','#e61dff','#8e00ff')),
    ('rainbow_bars','Радужный спектр','segments',('#ff271b','#ffe800','#38f940','#00cefb','#720cff')),
    ('sunset','Закат','wave',('#e000c7','#c214ac','#baaf12','#fff01f')),
    ('fire_bars','Огненный эквалайзер','bars',('#510000','#cf250b','#ff8e19')),
    ('petals','Цветные лепестки','petals',('#bc00ff','#fa1477','#ffce32')),
    ('orbit','Пульсирующая орбита','orbit',('#cf27ff','#13b991','#d0ff33')),
    ('stereo_ice','Стерео · мята и лёд','stereo',('#6affe0','#94bdff')),
    ('stereo_sunset','Стерео · лимон и роза','stereo',('#faff54','#ff69b8')),
    ('cyan','Бирюзовый осциллограф','scope',('#06a4c6','#7bffeb','#f6fff4')),
    ('off','Без визуализации','off',('#153844','#153844')),
]
PRESET_IDS = {p[0] for p in PRESETS}


def preset_info(key):
    return next((p for p in PRESETS if p[0]==key),PRESETS[0])


def gradient(rect,colors,vertical=False):
    g=QLinearGradient(rect.left(),rect.bottom() if vertical else rect.top(),
                      rect.left() if vertical else rect.right(),rect.top())
    for i,color in enumerate(colors):
        g.setColorAt(i/max(1,len(colors)-1),QColor(color))
    return g


def sample(values,count):
    if len(values)==0:
        return np.zeros(count)
    return np.interp(np.linspace(0,len(values)-1,count),np.arange(len(values)),values)


def draw_visualizer(p,rect,key,signal,phase=0,theme_colors=None):
    _,_,kind,colors=preset_info(key)
    if key=='gold' and theme_colors:
        fill=QColor(theme_colors['wave'])
        colors=(fill.darker(140).name(),fill.name(),fill.lighter(140).name())
    p.save()
    p.setClipRect(rect)
    p.fillRect(rect,QColor('#060c0f'))
    r=rect.adjusted(1,1,-1,-1)
    if kind=='off':
        p.restore()
        return
    n=140
    wave=sample(signal.wave,n).clip(0,1)
    spec=sample(signal.spectrum,n).clip(0,1)
    energy=min(1,max(signal.levels))
    mid=r.center().y()
    if kind in ('wave','ribbon'):
        x=np.linspace(0,1,n)
        if kind=='ribbon':
            amplitude=(.22+.62*wave+.18*spec)*min(1,energy*3.5)
            envelope=np.sin(x*math.tau*.85+phase*.8)*amplitude
        else:
            envelope=wave*.86
        path=QPainterPath(QPointF(r.left(),mid-envelope[0]*r.height()*.47))
        for i,v in enumerate(envelope):
            path.lineTo(r.left()+i*r.width()/(n-1),mid-v*r.height()*.47)
        for i in range(n-1,-1,-1):
            path.lineTo(r.left()+i*r.width()/(n-1),mid+envelope[i]*r.height()*.47)
        path.closeSubpath()
        p.setBrush(gradient(r,colors))
        edge=QColor('#f2ddff' if key=='violet' else '#c7fffa' if key=='ocean' else '#fff4c3' if key=='gold' else '#ffffff')
        if key=='gold' and theme_colors:
            edge=QColor(theme_colors['wave_edge'])
        p.setPen(QPen(edge,1.15))
        p.drawPath(path)
        if kind=='wave':
            signed=sample(getattr(signal,'signal_wave',wave),n)
            line=QPainterPath()
            for i,v in enumerate(signed):
                point=QPointF(r.left()+i*r.width()/(n-1),mid-v*r.height()*.22)
                line.moveTo(point) if i==0 else line.lineTo(point)
            p.setPen(QPen(QColor('#fff6cc'),.75))
            p.setBrush(Qt.NoBrush)
            p.drawPath(line)
    elif kind in ('bars','segments'):
        bars=36
        levels=sample(spec,bars)
        peaks=sample(getattr(signal,'peaks',spec),bars)
        width=r.width()/bars
        for i,value in enumerate(levels):
            h=max(.5,value*r.height()*.93)
            bar=QRectF(r.left()+i*width+1,r.bottom()-h,max(1,width-2),h)
            p.setPen(Qt.NoPen)
            if kind=='segments':
                color=QColor.fromHsvF((i/bars*.78)%1,1,.95)
                p.setBrush(color)
                for y in np.arange(r.bottom()-2,bar.top(),-3):
                    p.drawRect(QRectF(bar.x(),float(y),bar.width(),1.5))
            else:
                p.setBrush(gradient(QRectF(r.x(),r.y(),r.width(),r.height()),colors,True))
                p.drawRoundedRect(bar,1.8 if key=='fire_bars' else .3,1.8 if key=='fire_bars' else .3)
            if peaks[i]>.02:
                p.fillRect(QRectF(bar.x(),r.bottom()-peaks[i]*r.height()*.93-2,bar.width(),1.4),
                           QColor('#d7dfff') if kind=='bars' else QColor.fromHsvF(i/bars*.78,.5,1))
    elif kind in ('petals','orbit'):
        center=r.center()
        maximum=min(r.height()*.46,r.width()*.25)
        path=QPainterPath()
        points=180
        values=sample(wave,points)
        rotation=phase*.4
        for i in range(points+1):
            theta=i/points*math.tau
            if kind=='petals':
                radius=maximum*(.08+(.2+.7*energy)*abs(math.sin(theta*1.5)))*(.7+.3*values[i%points])
            else:
                radius=maximum*(.48+.38*energy+.14*values[i%points])*(.9+.1*math.sin(theta*6+phase))
            point=QPointF(center.x()+radius*math.cos(theta+rotation),center.y()+radius*math.sin(theta+rotation))
            path.moveTo(point) if i==0 else path.lineTo(point)
        path.closeSubpath()
        shifted=[QColor.fromHsvF((phase*.035+i*.24)%1,.8,.95) for i in range(3)]
        if kind=='orbit':
            g=QRadialGradient(center,maximum)
            g.setColorAt(0,QColor('#cd18ff'));g.setColorAt(.32,QColor('#497fb1'))
            g.setColorAt(.85,shifted[1]);g.setColorAt(1,shifted[2])
            p.setPen(QPen(shifted[2],2.2))
        else:
            g=QLinearGradient(center.x()-maximum,center.y()-maximum,center.x()+maximum,center.y()+maximum)
            g.setColorAt(0,shifted[0]);g.setColorAt(.5,shifted[1]);g.setColorAt(1,shifted[2])
            p.setPen(Qt.NoPen)
        p.setBrush(g);p.drawPath(path)
        if kind=='orbit':
            p.setPen(QPen(QColor('#dc32ff'),1.7));p.setBrush(Qt.NoBrush)
            p.drawEllipse(center,4,4)
    elif kind in ('stereo','scope'):
        p.setPen(QPen(QColor('#1c2330'),.5))
        for i in range(12):
            x=r.left()+r.width()*i/12;p.drawLine(QPointF(x,r.top()),QPointF(x,r.bottom()))
        channels=getattr(signal,'stereo_wave',[wave,wave]) if kind=='stereo' else [getattr(signal,'signal_wave',wave)]
        for channel,values in enumerate(channels):
            values=sample(values,n)
            center=r.top()+r.height()*(.28 if channel==0 else .76) if kind=='stereo' else mid
            amplitude=r.height()*(.21 if kind=='stereo' else .44)
            path=QPainterPath()
            for i,v in enumerate(values):
                point=QPointF(r.left()+i*r.width()/(n-1),center-float(v)*amplitude)
                path.moveTo(point) if i==0 else path.lineTo(point)
            p.setBrush(Qt.NoBrush)
            for width,alpha in ((6,25),(3.5,70),(1.2,255)):
                color=QColor(colors[channel%len(colors)]);color.setAlpha(alpha)
                p.setPen(QPen(color,width));p.drawPath(path)
    p.restore()


class VisualCard(QPushButton):
    def __init__(self,key,controller,parent=None):
        super().__init__(parent)
        self.key=key
        self.controller=controller
        self.setCheckable(True)
        self.setMinimumSize(195,103)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(preset_info(key)[1])

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#32d8cb' if self.isChecked() else '#28414f'),2 if self.isChecked() else 1))
        p.setBrush(QColor('#112d38' if self.isChecked() else '#10212b'))
        p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),7,7)
        # Explicit effect thumbnails use illustrative signals when audio is stopped.
        c=self.controller
        if max(c.levels)<.001:
            x=np.linspace(0,math.tau,140)
            c=SimpleNamespace(wave=np.abs(np.sin(x*2)*(.45+.3*np.sin(x*13))),
                spectrum=(.16+.55*np.abs(np.sin(x*2.2)))*np.linspace(1,.4,140),
                signal_wave=np.sin(x*7)*.6,stereo_wave=[np.sin(x*9)*.6,np.sin(x*11+.5)*.6],levels=[.55,.5])
        draw_visualizer(p,QRectF(10,10,self.width()-20,self.height()-39),self.key,c,2,self.controller.theme['colors'])
        p.setPen(QColor('#e3f3f7'))
        p.drawText(QRectF(9,self.height()-26,self.width()-18,20),Qt.AlignCenter,preset_info(self.key)[1])


class VisualizerDialog(QDialog):
    def __init__(self,controller):
        super().__init__(controller)
        from dialogs import DIALOG_STYLE
        self.controller=controller
        self.setWindowTitle('Визуализация · WAVEN Custom')
        self.setStyleSheet(DIALOG_STYLE)
        self.resize(880,620)
        root=QVBoxLayout(self)
        title=QLabel('Визуализация')
        title.setStyleSheet('font-size:23px;font-weight:600;color:#f1f9fa')
        root.addWidget(title)
        root.addWidget(QLabel('Выберите эффект. Он сразу появится в плеере и сохранится для следующего запуска.'))
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        panel=QWidget();panel.setObjectName('panel');grid=QGridLayout(panel)
        self.cards=[]
        for i,(key,*_) in enumerate(PRESETS):
            card=VisualCard(key,controller)
            card.setChecked(key==controller.visual_preset)
            card.clicked.connect(lambda checked=False,k=key:self.select(k))
            grid.addWidget(card,i//4,i%4)
            self.cards.append(card)
        scroll.setWidget(panel);root.addWidget(scroll,1)
        self.description=QLabel();root.addWidget(self.description)
        close=QPushButton('Готово');close.clicked.connect(self.accept);root.addWidget(close,alignment=Qt.AlignRight)
        self.update_description()

    def select(self,key):
        self.controller.set_visualizer(key)
        for card in self.cards:
            card.setChecked(card.key==key)
        self.update_description()

    def update_description(self):
        self.description.setText('Выбран: '+preset_info(self.controller.visual_preset)[1]+' · Миниатюры показывают пример эффекта')
