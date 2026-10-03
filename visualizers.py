"""Audio-reactive visualizers inspired by the reference screenshots."""
from __future__ import annotations
import math
from types import SimpleNamespace
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QSize, QElapsedTimer, QEvent
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QAbstractButton, QLabel,
                               QGridLayout, QWidget, QScrollArea, QSizePolicy, QHBoxLayout,
                               QFormLayout, QDoubleSpinBox, QSpinBox, QCheckBox, QColorDialog)

PRESETS = [
    # Keep the old key so existing profiles retain their selected effect.
    ('gold','Переливающаяся волна','wave',('#dba51a','#ffda47','#ffeab4')),
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
LEGACY_PRESETS = {p[0]:p for p in PRESETS}
ALIASES={'violet':'aurora','ocean':'aurora','purple':'gold','sunset':'gold',
         'fire_bars':'green_bars','stereo_sunset':'stereo_ice'}
NAMES={'gold':'Волна','aurora':'Лента','green_bars':'Эквалайзер','rainbow_bars':'Спектр',
       'petals':'Лепестки','orbit':'Орбита','stereo_ice':'Стерео','cyan':'Осциллограф'}
PRESETS=[(key,NAMES.get(key,name),kind,colors) for key,name,kind,colors in PRESETS if key not in ALIASES]
PRESETS[-1:-1]=[('tunnel','Частотный тоннель','tunnel',('#29e5d5','#5396ff','#eb67f7')),
               ('vectorscope','Стереополе','vectorscope',('#6affe0','#94bdff','#ef72de'))]
PRESET_IDS = {p[0] for p in PRESETS}


def visual_config(key,value=None):
    import re
    value=value if isinstance(value,dict) else {}
    palette=list(preset_info(key)[3])
    palette=[palette[0],palette[len(palette)//2],palette[-1]]
    if key=='gold':palette=['#a92bff','#ffe553','#19e4cb']
    colors=value.get('colors',palette)
    if not isinstance(colors,list) or len(colors)!=3 or not all(isinstance(c,str) and re.fullmatch('#[0-9a-fA-F]{6}',c) for c in colors):colors=palette
    def number(name,default,low,high):
        try:return max(low,min(high,float(value.get(name,default))))
        except (TypeError,ValueError):return default
    return dict(colors=colors[:],sensitivity=number('sensitivity',1,.25,4),
                speed=number('speed',1,0,3),detail=int(number('detail',36,12,96)),
                glow=bool(value.get('glow',True)),color_motion=bool(value.get('color_motion',key in ('gold','petals','orbit'))))


def migrate_visuals(key,settings):
    settings=settings if isinstance(settings,dict) else {}
    result={k:visual_config(k,v) for k,v in settings.items() if k in PRESET_IDS}
    canonical=ALIASES.get(key,key)
    if key in ALIASES and canonical not in result:
        palette=LEGACY_PRESETS[key][3]
        result[canonical]=visual_config(canonical,dict(colors=[palette[0],palette[len(palette)//2],palette[-1]],color_motion=False))
    return canonical if canonical in PRESET_IDS else 'aurora',result


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


def demo_signal(phase):
    """Moving illustrative audio, independent of playback volume or pause."""
    x=np.linspace(0,math.tau,140)
    beat=.66+.22*math.sin(phase*2.7)
    wave=(.25+.45*np.abs(np.sin(x*1.7-phase*1.3))+.22*np.sin(x*13+phase*4)**2)*beat
    spectrum=(.1+.72*np.abs(np.sin(x*1.5-phase*.9))**2)*np.linspace(1,.45,140)*beat
    signed=np.sin(x*7+phase*3)*(.35+.35*np.sin(x*1.5-phase)**2)
    return SimpleNamespace(wave=wave,spectrum=spectrum,peaks=np.minimum(1,spectrum+.11),
        signal_wave=signed,stereo_wave=[signed,np.sin(x*9-phase*2)*.65],levels=[beat,beat*.9])


def shimmer_colors(phase,base):
    hue,saturation,value,_=QColor(base).getHsvF()
    return tuple(QColor.fromHsvF((max(0,hue)+phase*.045+i*.19)%1,
                                max(.65,saturation),max(.85,value)).name() for i in range(5))


def draw_visualizer(p,rect,key,signal,phase=0,theme_colors=None,settings=None):
    _,_,kind,colors=preset_info(key)
    config=visual_config(key,(settings if settings is not None else getattr(signal,'visual_settings',{})).get(key,{}))
    colors=config['colors'];phase*=config['speed']
    if config['color_motion']:
        colors=[QColor.fromHsvF((max(0,QColor(c).hsvHueF())+phase*.045)%1,
                              QColor(c).hsvSaturationF(),QColor(c).valueF()).name() for c in colors]
    p.save()
    p.setClipRect(rect)
    p.fillRect(rect,QColor('#060c0f'))
    r=rect.adjusted(1,1,-1,-1)
    if kind=='off':
        p.restore()
        return
    n=140
    wave=(sample(signal.wave,n)*config['sensitivity']).clip(0,1)
    spec=(sample(signal.spectrum,n)*config['sensitivity']).clip(0,1)
    energy=float(np.sqrt(np.mean(wave*wave)))
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
        if key=='gold':edge=QColor(colors[1]).lighter(150)
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
        bars=config['detail']
        levels=sample(spec,bars)
        peaks=sample(getattr(signal,'peaks',spec),bars)
        width=r.width()/bars
        for i,value in enumerate(levels):
            h=max(.5,value*r.height()*.93)
            bar=QRectF(r.left()+i*width+1,r.bottom()-h,max(1,width-2),h)
            p.setPen(Qt.NoPen)
            if kind=='segments':
                color=QColor(colors[min(2,int(i/bars*3))])
                p.setBrush(color)
                for y in np.arange(r.bottom()-2,bar.top(),-3):
                    p.drawRect(QRectF(bar.x(),float(y),bar.width(),1.5))
            else:
                p.setBrush(gradient(QRectF(r.x(),r.y(),r.width(),r.height()),colors,True))
                p.drawRoundedRect(bar,1.8 if key=='fire_bars' else .3,1.8 if key=='fire_bars' else .3)
            if peaks[i]>.02:
                p.fillRect(QRectF(bar.x(),r.bottom()-peaks[i]*r.height()*.93-2,bar.width(),1.4),
                           QColor('#d7dfff') if kind=='bars' else color.lighter(150))
    elif kind in ('petals','orbit','tunnel'):
        center=r.center()
        maximum=min(r.height()*.46,r.width()*.46)
        path=QPainterPath()
        points=180
        values=sample(spec,points)
        rotation=phase*.4
        for i in range(points+1):
            theta=i/points*math.tau
            if kind=='petals':
                lobes=max(3,config['detail']//6)
                radius=maximum*(.1+abs(math.sin(theta*lobes/2))*(.25+.6*math.sqrt(values[i%points])+.05*energy))
            else:
                radius=maximum*(.25+.12*energy+.58*values[i%points])
            point=QPointF(center.x()+radius*math.cos(theta+rotation),center.y()+radius*math.sin(theta+rotation))
            path.moveTo(point) if i==0 else path.lineTo(point)
        path.closeSubpath()
        shifted=[QColor(c) for c in colors]
        if kind=='orbit':
            g=QRadialGradient(center,maximum)
            g.setColorAt(0,shifted[0]);g.setColorAt(.32,shifted[1])
            g.setColorAt(.85,shifted[1]);g.setColorAt(1,shifted[2])
            p.setPen(QPen(shifted[2],2.2))
        else:
            g=QLinearGradient(center.x()-maximum,center.y()-maximum,center.x()+maximum,center.y()+maximum)
            g.setColorAt(0,shifted[0]);g.setColorAt(.5,shifted[1]);g.setColorAt(1,shifted[2])
            p.setPen(Qt.NoPen)
        p.setBrush(g);p.drawPath(path)
        if kind in ('orbit','tunnel'):
            p.setBrush(Qt.NoBrush)
            bands=sample(spec,config['detail'])
            for i,v in enumerate(bands):
                theta=math.tau*i/len(bands)+rotation
                inner=maximum*.3;outer=inner+maximum*.68*v
                p.setPen(QPen(shifted[i%3],max(1,maximum/25)))
                p.drawLine(QPointF(center.x()+inner*math.cos(theta),center.y()+inner*math.sin(theta)),
                           QPointF(center.x()+outer*math.cos(theta),center.y()+outer*math.sin(theta)))
            if kind=='tunnel':
                for j in range(1,6):
                    factor=(j/6+phase*.12)%1
                    p.save();p.translate(center);p.scale(factor*2.2,factor*2.2);p.translate(-center)
                    color=QColor(colors[j%3]);color.setAlpha(int(190*(1-factor)))
                    p.setPen(QPen(color,1.2));p.drawPath(path);p.restore()
        else:
            p.setPen(QPen(shifted[2],.8));p.setBrush(Qt.NoBrush)
            for i,v in enumerate(sample(spec,max(3,config['detail']//6))):
                theta=math.tau*i/max(3,config['detail']//6)+rotation
                p.drawLine(center,QPointF(center.x()+maximum*v*math.cos(theta),center.y()+maximum*v*math.sin(theta)))
    elif kind=='vectorscope':
        center=r.center();size=min(r.width(),r.height())*.45
        p.setPen(QPen(QColor('#28414f'),.6));p.setBrush(Qt.NoBrush)
        p.drawEllipse(center,size,size)
        channels=getattr(signal,'stereo_wave',[wave,wave]);count=config['detail']*4
        left=sample(channels[0],count)*config['sensitivity'];right=sample(channels[1],count)*config['sensitivity']
        path=QPainterPath()
        for i,(l,rr) in enumerate(zip(left,right)):
            point=QPointF(center.x()+np.clip((l-rr)*.707,-1,1)*size,center.y()-np.clip((l+rr)*.707,-1,1)*size)
            path.moveTo(point) if not i else path.lineTo(point)
        p.setPen(QPen(QBrush(gradient(r,colors)),1.2));p.drawPath(path)
    elif kind in ('stereo','scope'):
        p.setPen(QPen(QColor('#1c2330'),.5))
        for i in range(12):
            x=r.left()+r.width()*i/12;p.drawLine(QPointF(x,r.top()),QPointF(x,r.bottom()))
        channels=getattr(signal,'stereo_wave',[wave,wave]) if kind=='stereo' else [getattr(signal,'signal_wave',wave)]
        for channel,values in enumerate(channels):
            values=(sample(values,n)*config['sensitivity']).clip(-1,1)
            center=r.top()+r.height()*(.28 if channel==0 else .76) if kind=='stereo' else mid
            amplitude=r.height()*(.21 if kind=='stereo' else .44)
            path=QPainterPath()
            for i,v in enumerate(values):
                point=QPointF(r.left()+i*r.width()/(n-1),center-float(v)*amplitude)
                path.moveTo(point) if i==0 else path.lineTo(point)
            p.setBrush(Qt.NoBrush)
            for width,alpha in (((6,25),(3.5,70),(1.2,255)) if config['glow'] else ((1.2,255),)):
                color=QColor(colors[channel%len(colors)]);color.setAlpha(alpha)
                if kind=='scope':
                    shades=[QColor(c) for c in colors]
                    for shade in shades:shade.setAlpha(alpha)
                    p.setPen(QPen(QBrush(gradient(r,shades)),width))
                else:p.setPen(QPen(color,width))
                p.drawPath(path)
    p.restore()


class VisualCard(QAbstractButton):
    def __init__(self,key,controller,parent=None):
        super().__init__(parent)
        self.key=key
        self.controller=controller
        self.phase=0.
        self.demo=demo_signal(0)
        self.setCheckable(True)
        # QAbstractButton avoids the common QPushButton stylesheet's min-height.
        self.setMinimumSize(190,132)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(preset_info(key)[1])
        self.setToolTip(preset_info(key)[1])

    def sizeHint(self):
        return QSize(218,132)

    def minimumSizeHint(self):
        return QSize(190,132)

    def set_demo(self,signal,phase):
        self.demo=signal;self.phase=phase;self.update()

    def enterEvent(self,event):
        super().enterEvent(event);self.update()

    def leaveEvent(self,event):
        super().leaveEvent(event);self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        active=self.isChecked()
        p.setPen(QPen(QColor('#32d8cb' if active else '#52717e' if self.underMouse() else '#28414f'),2 if active else 1))
        p.setBrush(QColor('#112d38' if self.isChecked() else '#162c37' if self.underMouse() else '#10212b'))
        p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),7,7)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('#98b1be'),1,Qt.DotLine))
            p.drawRoundedRect(self.rect().adjusted(4,4,-4,-4),5,5)
        preview=QRectF(10,10,self.width()-20,self.height()-42)
        draw_visualizer(p,preview,self.key,self.demo,self.phase,self.controller.theme['colors'],self.controller.visual_settings)
        if self.key=='off':
            p.setPen(QColor('#64818e'));p.drawText(preview,Qt.AlignCenter,'—')
        p.setPen(QColor('#e3f3f7'))
        label=p.fontMetrics().elidedText(preset_info(self.key)[1],Qt.ElideRight,self.width()-18)
        p.drawText(QRectF(9,self.height()-27,self.width()-18,20),Qt.AlignCenter,label)


class VisualizerDialog(QDialog):
    def __init__(self,controller):
        super().__init__(controller)
        from ui_style import DIALOG_STYLE
        self.controller=controller
        self.setWindowTitle('Визуализация · WAVEN Custom')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumSize(450,430)
        area=self.screen().availableGeometry()
        self.resize(min(960,area.width()-40),min(760,area.height()-60))
        root=QVBoxLayout(self)
        root.setContentsMargins(20,18,20,18);root.setSpacing(12)
        title=QLabel('Визуализация')
        title.setStyleSheet('font-size:23px;font-weight:600;color:#f1f9fa')
        root.addWidget(title)
        subtitle=QLabel('Живые примеры работают даже без музыки. Нажмите на эффект, чтобы выбрать его для плеера.')
        subtitle.setWordWrap(True);root.addWidget(subtitle)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        panel=QWidget();panel.setObjectName('panel');self.grid=QGridLayout(panel)
        self.grid.setContentsMargins(0,0,8,0);self.grid.setSpacing(12);self.grid.setAlignment(Qt.AlignTop)
        self.columns=4
        self.cards=[]
        for i,(key,*_) in enumerate(PRESETS):
            card=VisualCard(key,controller)
            card.setChecked(key==controller.visual_preset)
            card.clicked.connect(lambda checked=False,k=key:self.select(k))
            self.grid.addWidget(card,i//4,i%4)
            self.cards.append(card)
        self.scroll.setWidget(panel);root.addWidget(self.scroll,1)
        self.scroll.viewport().installEventFilter(self)
        self.description=QLabel();self.description.setWordWrap(True);root.addWidget(self.description)
        controls=QWidget();form=QGridLayout(controls);form.setContentsMargins(0,0,0,0)
        self.color_buttons=[]
        for index in range(3):
            button=QPushButton('Цвет '+str(index+1));button.setFixedWidth(80)
            button.clicked.connect(lambda checked=False,i=index:self.choose_color(i))
            self.color_buttons.append(button);form.addWidget(button,0,index)
        self.sensitivity=QDoubleSpinBox();self.sensitivity.setRange(.25,4);self.sensitivity.setSingleStep(.25)
        self.sensitivity.setPrefix('Чувств. ×');self.sensitivity.valueChanged.connect(self.save_config);form.addWidget(self.sensitivity,1,0)
        self.detail=QSpinBox();self.detail.setRange(12,96);self.detail.setSingleStep(6)
        self.detail.setPrefix('Детали: ');self.detail.valueChanged.connect(self.save_config);form.addWidget(self.detail,1,1)
        root.addWidget(controls)
        second=QGridLayout()
        self.motion=QCheckBox('Переливы цвета');self.motion.toggled.connect(self.save_config);second.addWidget(self.motion,0,0)
        self.glow=QCheckBox('Свечение');self.glow.toggled.connect(self.save_config);second.addWidget(self.glow,0,1)
        self.speed=QDoubleSpinBox();self.speed.setRange(0,3);self.speed.setSingleStep(.25)
        self.speed.setPrefix('Скорость ×');self.speed.valueChanged.connect(self.save_config);form.addWidget(self.speed,1,2)
        reset=QPushButton('Сбросить эффект');reset.clicked.connect(self.reset_config);second.addWidget(reset,0,2)
        root.addLayout(second)
        close=QPushButton('Готово');close.clicked.connect(self.accept);root.addWidget(close,alignment=Qt.AlignRight)
        self.clock=QElapsedTimer()
        self.animation_timer=QTimer(self);self.animation_timer.setInterval(40)
        self.animation_timer.timeout.connect(self.animate)
        self.update_description()
        self.load_config()

    def load_config(self):
        self.syncing=True
        config=visual_config(self.controller.visual_preset,self.controller.visual_settings.get(self.controller.visual_preset))
        for button,color in zip(self.color_buttons,config['colors']):
            button.setStyleSheet('background:'+color+';color:'+('#111111' if QColor(color).lightness()>140 else '#ffffff'))
        self.sensitivity.setValue(config['sensitivity']);self.detail.setValue(config['detail'])
        self.speed.setValue(config['speed']);self.motion.setChecked(config['color_motion']);self.glow.setChecked(config['glow'])
        kind=preset_info(self.controller.visual_preset)[2]
        for i,button in enumerate(self.color_buttons):button.setEnabled(kind!='off' and not (kind=='stereo' and i==2))
        self.sensitivity.setEnabled(kind!='off');self.motion.setEnabled(kind!='off')
        self.speed.setEnabled(kind!='off')
        self.detail.setEnabled(kind in ('bars','segments','petals','orbit','tunnel','vectorscope'))
        self.glow.setEnabled(kind in ('stereo','scope'))
        self.syncing=False

    def save_config(self,*args):
        if getattr(self,'syncing',True):return
        key=self.controller.visual_preset
        config=visual_config(key,self.controller.visual_settings.get(key))
        config.update(sensitivity=self.sensitivity.value(),detail=self.detail.value(),speed=self.speed.value(),
                      color_motion=self.motion.isChecked(),glow=self.glow.isChecked())
        self.controller.visual_settings[key]=config;self.controller.persist();self.controller.canvas.update()

    def choose_color(self,index):
        key=self.controller.visual_preset;config=visual_config(key,self.controller.visual_settings.get(key))
        color=QColorDialog.getColor(QColor(config['colors'][index]),self,'Цвет эффекта')
        if color.isValid():
            config['colors'][index]=color.name();self.controller.visual_settings[key]=config
            self.controller.persist();self.load_config();self.controller.canvas.update()

    def reset_config(self):
        self.controller.visual_settings.pop(self.controller.visual_preset,None)
        self.controller.persist();self.load_config();self.controller.canvas.update()

    def eventFilter(self,watched,event):
        if watched is self.scroll.viewport() and event.type()==QEvent.Resize:
            self.reflow_cards()
        return super().eventFilter(watched,event)

    def reflow_cards(self):
        columns=max(1,min(4,(self.scroll.viewport().width()-8+12)//(190+12)))
        if columns==self.columns:return
        for card in self.cards:self.grid.removeWidget(card)
        for column in range(4):self.grid.setColumnStretch(column,0)
        for i,card in enumerate(self.cards):self.grid.addWidget(card,i//columns,i%columns)
        for column in range(columns):self.grid.setColumnStretch(column,1)
        self.columns=columns

    def showEvent(self,event):
        super().showEvent(event)
        self.reflow_cards();self.clock.start();self.animation_timer.start();self.animate()

    def hideEvent(self,event):
        self.animation_timer.stop()
        super().hideEvent(event)

    def animate(self):
        phase=self.clock.elapsed()/1000
        signal=demo_signal(phase)
        viewport=self.scroll.viewport()
        for card in self.cards:
            if viewport.rect().intersects(card.rect().translated(card.mapTo(viewport,QPointF(0,0).toPoint()))):
                card.set_demo(signal,phase)

    def select(self,key):
        self.controller.set_visualizer(key)
        for card in self.cards:
            card.setChecked(card.key==key)
        self.update_description()
        self.load_config()

    def update_description(self):
        self.description.setText('Выбран: '+preset_info(self.controller.visual_preset)[1]+' · В плеере эффект реагирует на вашу музыку')
