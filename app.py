from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QUrl, QTimer, QRectF, QPointF, Signal, QLockFile
from PySide6.QtGui import (QColor, QPainter, QPen, QLinearGradient, QPainterPath,
                           QFont, QImage, QIcon, QPixmap, QAction, QKeySequence, QShortcut)
from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QFileDialog, QMenu,
                               QMessageBox, QToolTip)
from PySide6.QtMultimedia import (QMediaPlayer, QAudioOutput, QMediaMetaData,
                                  QAudioBufferOutput, QAudioFormat)
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from core import Store, Queue, open_selection
from theme import DEFAULT_THEME, validated_theme, readable_text_color
from visualizers import draw_visualizer,PRESET_IDS,preset_info,sample

BUTTONS = {'previous': '<', 'play': '▶ PLAY', 'next': '>', 'stop': 'STOP',
           'playlist': 'LIST', 'info': '!', 'visual': 'VIS', 'skin': 'SKIN',
           'options': '(W)', 'exit': '×'}
TIPS = {'previous':'Предыдущая · Ctrl+←', 'play':'Воспроизведение / пауза · Пробел',
        'next':'Следующая · Ctrl+→', 'stop':'Стоп', 'playlist':'Плейлисты и очередь · Ctrl+L',
        'info':'Сведения о треке', 'visual':'Выбрать визуализацию',
        'skin':'Редактор оформления · Ctrl+T', 'options':'Меню', 'exit':'Закрыть'}


def clock_text(ms):
    seconds = max(0, int(ms) // 1000)
    hours, minutes, seconds = seconds // 3600, (seconds // 60) % 60, seconds % 60
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'


def app_icon():
    pix = QPixmap(64,64)
    pix.fill(QColor('#071b27'))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#00dbed'),4))
    p.drawPolyline([QPointF(8,33),QPointF(16,33),QPointF(22,14),QPointF(29,49),
                    QPointF(36,20),QPointF(43,39),QPointF(49,33),QPointF(56,33)])
    p.end()
    return QIcon(pix)


class PlayerCanvas(QWidget):
    elementSelected = Signal(str)
    geometryEdited = Signal(str, list)
    editFinished = Signal()

    def __init__(self, controller, theme=None, preview=False, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.theme = validated_theme(theme)
        self.preview = preview
        self.edit_mode = False
        self.show_all_outlines = False
        self.resize_item = False
        self.selected = 'cover'
        self.drag_item = None
        self.drag_origin = None
        self.window_origin = None
        self.seeking = False
        self.volume_drag = False
        self.buttons = {}
        self.setMouseTracking(True)
        if not preview:
            self.setAcceptDrops(True)
        for key, label in BUTTONS.items():
            button = QPushButton(label, self)
            button.setObjectName(key)
            button.setAccessibleName(TIPS[key].split(' · ')[0])
            button.setToolTip(TIPS[key])
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(lambda checked=False, k=key: self.controller.action(k))
            if preview:
                button.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.buttons[key] = button
        self.set_theme(self.theme)

    @property
    def sx(self):
        return self.width() / self.theme['width']

    @property
    def sy(self):
        return self.height() / self.theme['height']

    def set_theme(self, theme):
        self.theme = validated_theme(theme)
        colors = self.theme['colors']
        for key, btn in self.buttons.items():
            fill = (colors['play_background'] if key == 'play' else colors['stop'] if key == 'stop'
                    else '#ff3232' if key == 'exit' else colors['button'] if key in ('next','previous')
                    else colors['small_button'])
            text_color=colors['play_text'] if key=='play' else colors['text']
            if key=='play':
                text_color=readable_text_color(fill,text_color)
            btn.setStyleSheet(f'QPushButton {{background:{fill}; color:{text_color};'
                              f'border:1px solid #286170; border-radius:0px; padding:0px; min-height:0px; min-width:0px;}}'
                              'QPushButton:hover {border:1px solid #b4ffff;}'
                              'QPushButton:pressed {background:#15818b;color:white;}')
        self.layout_buttons()
        self.update()

    def layout_buttons(self):
        if not self.theme:
            return
        for key, btn in self.buttons.items():
            x,y,w,h = self.theme['elements'][key]
            btn.setGeometry(round(x*self.sx),round(y*self.sy),round(w*self.sx),round(h*self.sy))
            font = QFont('Arial')
            font.setPixelSize(max(8,round((self.theme['font_size']+2 if key=='play' else self.theme['font_size'])*self.sy)))
            font.setBold(key=='play')
            btn.setFont(font)

    def resizeEvent(self, event):
        self.layout_buttons()

    def rect_for(self, key):
        return QRectF(*self.theme['elements'][key])

    def paintEvent(self, event):
        c = self.controller
        if self.preview:
            self.buttons['play'].setText('Ⅱ PAUSE' if c.player.playbackState()==QMediaPlayer.PlayingState else '▶ PLAY')
        t = self.theme
        colors = t['colors']
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.sx,self.sy)
        gradient = QLinearGradient(0,0,0,t['height'])
        gradient.setColorAt(0,QColor(colors['background_top']))
        gradient.setColorAt(1,QColor(colors['background_bottom']))
        p.setPen(QPen(QColor(colors['border']),1))
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(.5,.5,t['width']-1,t['height']-1),5,5)
        r = self.rect_for('cover')
        p.setBrush(QColor('#030506'))
        p.setPen(QColor('#484238'))
        p.drawRect(r)
        if not c.cover.isNull():
            image = c.cover
            side = min(image.width(),image.height())
            src = QRectF((image.width()-side)/2,(image.height()-side)/2,side,side)
            p.drawImage(r.adjusted(1,1,-1,-1),image,src)
        else:
            p.setPen(QColor('#1c5363'))
            font=QFont('Segoe UI',30)
            p.setFont(font)
            p.drawText(r,Qt.AlignCenter,'♫')
        self.draw_text(p,'logo','WAVEN',14,'#21c9ff',True,Qt.AlignCenter)
        self.draw_text(p,'title',c.title,13,colors['text'],True)
        self.draw_text(p,'artist',c.artist,10,colors['artist'])
        self.draw_text(p,'album',c.album,9,colors['album'])
        r=self.rect_for('visualizer')
        p.setBrush(QColor(0,0,0,80))
        p.setPen(QColor('#47452d'))
        p.drawRect(r)
        draw_visualizer(p,r.adjusted(1,1,-1,-1),c.visual_preset,c,c.visual_phase,colors)
        p.fillRect(self.rect_for('format'),QColor(6,12,15,175))
        self.draw_text(p,'format',c.audio_format,8,colors['accent'])
        for key,value in [('meter_left',c.levels[0]),('meter_right',c.levels[1])]:
            r=self.rect_for(key)
            meter_gradient=QLinearGradient(r.left(),r.top(),r.right(),r.top())
            meter_gradient.setColorAt(0,QColor('#26bfe6'));meter_gradient.setColorAt(.5,QColor('#17ef9d'))
            meter_gradient.setColorAt(1,QColor(colors['meter']))
            p.fillRect(QRectF(r.x(),r.y(),r.width()*min(1,max(0,value)),r.height()),meter_gradient)
        r=self.rect_for('progress')
        p.setPen(QPen(QColor('#383a39'),.8))
        p.setBrush(QColor(colors['track']))
        p.drawRoundedRect(r,4,4)
        progress= c.position / c.duration if c.duration else 0
        if progress>0:
            fill=QLinearGradient(0,r.top(),0,r.bottom())
            fill.setColorAt(0,QColor('#00bfed'))
            fill.setColorAt(.35,QColor(colors['accent']))
            fill.setColorAt(1,QColor('#0067c8'))
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(r.x(),r.y(),r.width()*min(1,progress),r.height()),4,4)
        self.draw_text(p,'time',f'{clock_text(c.position)} / {clock_text(c.duration)}',10,colors['text'])
        r=self.rect_for('volume')
        p.setPen(QColor('#32424c'))
        p.setBrush(QColor(colors['track']))
        p.drawRoundedRect(r,4,4)
        v=max(0,min(1,c.audio.volume()))
        p.setBrush(QColor(colors['accent']))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(r.x(),r.y(),r.width()*v,r.height()),4,4)
        p.setBrush(QColor('#ffffff'))
        p.drawEllipse(QPointF(r.x()+r.width()*v,r.center().y()),5,5)
        if self.edit_mode:
            p.setBrush(Qt.NoBrush)
            for key in t['elements']:
                if key!=self.selected and not self.show_all_outlines:continue
                p.setPen(QPen(QColor('#78efcf' if key==self.selected else '#426b78'),
                              1.4/self.sx if key==self.selected else .6,Qt.SolidLine if key==self.selected else Qt.DashLine))
                p.drawRect(self.rect_for(key).adjusted(-2,-2,2,2))
            r=self.rect_for(self.selected)
            p.fillRect(QRectF(r.right()-3,r.bottom()-3,7,7),QColor('#78efcf'))
        p.end()

    def draw_text(self,p,key,text,size,color,bold=False,alignment=Qt.AlignLeft|Qt.AlignVCenter):
        r=self.rect_for(key)
        font=QFont('Arial')
        font.setPixelSize(max(7,size+self.theme['font_size']-10))
        font.setBold(bold)
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(r,alignment,p.fontMetrics().elidedText(str(text),Qt.ElideRight,int(r.width())))

    def local_point(self,event):
        return QPointF(event.position().x()/self.sx,event.position().y()/self.sy)

    def mousePressEvent(self,event):
        pt=self.local_point(event)
        if event.button()==Qt.RightButton:
            if not self.preview:
                self.controller.show_menu(event.globalPosition().toPoint())
            return
        if event.button()!=Qt.LeftButton:
            return
        if self.edit_mode:
            selected_rect=self.rect_for(self.selected)
            if QRectF(selected_rect.right()-7,selected_rect.bottom()-7,14,14).contains(pt):
                self.drag_item=self.selected;self.resize_item=True;self.drag_origin=pt
                self.rect_origin=self.theme['elements'][self.selected][:]
                return
            for key in reversed(list(self.theme['elements'])):
                if self.rect_for(key).contains(pt):
                    self.selected=key
                    self.drag_item=key
                    self.resize_item=False
                    self.drag_origin=pt
                    self.rect_origin=self.theme['elements'][key][:]
                    self.elementSelected.emit(key)
                    self.update()
                    return
        if self.preview:
            return
        if self.rect_for('progress').adjusted(0,-5,0,5).contains(pt):
            self.seeking=True
            self.seek_to(pt)
        elif self.rect_for('volume').adjusted(-5,-6,5,6).contains(pt):
            self.volume_drag=True
            self.volume_to(pt)
        else:
            self.drag_origin=event.globalPosition().toPoint()
            self.window_origin=self.window().pos()

    def mouseMoveEvent(self,event):
        pt=self.local_point(event)
        if self.edit_mode and self.drag_item:
            delta=pt-self.drag_origin
            x,y,w,h=self.rect_origin
            if self.resize_item:
                rect=[x,y,round(max(4,min(self.theme['width']-x,w+delta.x()))),
                      round(max(4,min(self.theme['height']-y,h+delta.y())))]
            else:
                rect=[round(max(0,min(self.theme['width']-w,x+delta.x()))),
                      round(max(0,min(self.theme['height']-h,y+delta.y()))),w,h]
            self.theme['elements'][self.drag_item]=rect
            self.layout_buttons()
            self.geometryEdited.emit(self.drag_item,rect)
            self.update()
        elif self.seeking:
            self.seek_to(pt)
        elif self.volume_drag:
            self.volume_to(pt)
        elif self.drag_origin is not None and self.window_origin is not None and event.buttons() & Qt.LeftButton:
            self.window().move(self.window_origin+event.globalPosition().toPoint()-self.drag_origin)

    def mouseReleaseEvent(self,event):
        if self.edit_mode and self.drag_item:self.editFinished.emit()
        self.drag_item=None
        self.resize_item=False
        self.drag_origin=None
        self.window_origin=None
        self.seeking=False
        self.volume_drag=False

    def mouseDoubleClickEvent(self,event):
        if not self.preview and self.rect_for('cover').contains(self.local_point(event)):
            self.controller.choose_files()

    def wheelEvent(self,event):
        if not self.preview:
            self.controller.set_volume(round(self.controller.audio.volume()*100)+(5 if event.angleDelta().y()>0 else -5))

    def seek_to(self,point):
        r=self.rect_for('progress')
        if self.controller.duration:
            self.controller.player.setPosition(round(max(0,min(1,(point.x()-r.x())/r.width()))*self.controller.duration))

    def volume_to(self,point):
        r=self.rect_for('volume')
        self.controller.set_volume(round(100*max(0,min(1,(point.x()-r.x())/r.width()))))

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self,event):
        self.controller.open_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()


class PlayerWindow(QWidget):
    queueChanged=Signal()

    def __init__(self,store):
        super().__init__()
        self.store=store
        self.setWindowTitle('WAVEN Custom')
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint)
        self.queue=Queue(store.state['queue'],store.state.get('index',-1))
        self.title='Откройте музыку'
        self.artist='Перетащите файл или папку в плеер'
        self.album='Двойной щелчок по обложке — открыть файлы'
        self.cover=QImage()
        self.position=0
        self.duration=0
        self.audio_format=''
        self.wave=np.zeros(140)
        self.spectrum=np.zeros(140)
        self.peaks=np.zeros(140)
        self.signal_wave=np.zeros(140)
        self.stereo_wave=[np.zeros(140),np.zeros(140)]
        self.levels=[0.,0.]
        legacy={0:'gold',1:'rainbow_bars',2:'off'}.get(store.state.get('visual_mode'),'aurora')
        self.visual_preset=store.state.get('visual_preset',legacy)
        if self.visual_preset not in PRESET_IDS:
            self.visual_preset='aurora'
        self.visual_phase=0.
        self.visual_dialog=None
        self.theme=validated_theme(store.state.get('theme'))
        self.player=QMediaPlayer(self)
        self.audio=QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(max(0,min(100,store.state.get('volume',50)))/100)
        self.buffer=QAudioBufferOutput(self)
        self.player.setAudioBufferOutput(self.buffer)
        self.buffer.audioBufferReceived.connect(self.audio_buffer)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.metaDataChanged.connect(self.metadata_changed)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(self.media_error)
        self.canvas=PlayerCanvas(self,self.theme,parent=self)
        self.pending_position=0
        self.playlists_dialog=None
        self.theme_dialog=None
        self.last_error=''
        self.resize_reference()
        saved=store.state.get('window_position')
        if isinstance(saved,list) and len(saved)==2:
            point=QPointF(*saved).toPoint()
            if any(screen.availableGeometry().contains(point) for screen in QApplication.screens()):
                self.move(point)
        self.shortcuts=[]
        for key,callback in [('Space',self.toggle),('Ctrl+Right',self.next_track),
                             ('Ctrl+Left',self.previous_track),('Ctrl+O',self.choose_files),
                             ('Ctrl+L',self.show_playlists),('Ctrl+T',self.show_theme),
                             ('Ctrl+Shift+O',self.choose_folder)]:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.save_timer=QTimer(self)
        self.save_timer.timeout.connect(self.persist)
        self.save_timer.start(5000)
        if self.queue.current and Path(self.queue.current).is_file():
            self.load_current(False,store.state.get('position',0))
        if store.error:
            QTimer.singleShot(500,lambda: QMessageBox.warning(self,'Библиотека',store.error))

    def resizeEvent(self,event):
        self.canvas.setGeometry(self.rect())

    def tick(self):
        if self.player.playbackState()!=QMediaPlayer.PlayingState:
            self.wave*=.82
            self.spectrum*=.82
            self.signal_wave*=.82
            self.stereo_wave=[wave*.82 for wave in self.stereo_wave]
            self.levels=[v*.85 for v in self.levels]
        else:
            self.visual_phase+=.033
        self.peaks=np.maximum(self.spectrum,self.peaks-.009)
        self.canvas.update()

    def audio_buffer(self,buffer):
        if not buffer.isValid() or buffer.sampleCount()==0:
            return
        fmt=buffer.format()
        kinds={QAudioFormat.Float:(np.float32,1.),QAudioFormat.Int16:(np.int16,32768.),
               QAudioFormat.Int32:(np.int32,2147483648.),QAudioFormat.UInt8:(np.uint8,128.)}
        if fmt.sampleFormat() not in kinds:
            return
        kind,scale=kinds[fmt.sampleFormat()]
        samples=np.frombuffer(buffer.data(),dtype=kind,count=buffer.sampleCount()).astype(np.float32)
        if fmt.sampleFormat()==QAudioFormat.UInt8:
            samples-=128
        samples/=scale
        channels=max(1,fmt.channelCount())
        frames=samples.reshape(-1,channels)
        levels=np.sqrt(np.mean(frames*frames,axis=0))*2.5
        self.levels=[float(min(1,levels[0])),float(min(1,levels[min(1,len(levels)-1)]))]
        mono=np.mean(frames,axis=1)
        self.signal_wave=sample(np.convolve(mono,np.ones(5)/5,mode='same'),140).clip(-1,1)*1.8
        self.stereo_wave=[sample(np.convolve(frames[:,i],np.ones(5)/5,mode='same'),140).clip(-1,1)*1.8
                          for i in (0,min(1,channels-1))]
        # Wave envelopes and FFT bins come from decoded audio, not random values.
        chunks=np.array_split(np.abs(mono),140)
        fresh=np.array([np.max(chunk) if len(chunk) else 0 for chunk in chunks])
        self.wave=np.maximum(fresh*1.4,self.wave*.65).clip(0,1)
        fft=np.abs(np.fft.rfft(mono*np.hanning(len(mono))))
        if len(fft)>2:
            bins=np.geomspace(1,len(fft)-1,141).astype(int)
            spec=np.array([np.max(fft[a:max(a+1,b)]) for a,b in zip(bins[:-1],bins[1:])])
            self.spectrum=np.maximum(np.log1p(spec)*.20,self.spectrum*.8).clip(0,1)
        suffix=Path(self.queue.current or '').suffix[1:].upper()
        self.audio_format=f'{fmt.sampleRate()} Hz · {channels} ch · {suffix}'

    def position_changed(self,value):
        self.position=value

    def duration_changed(self,value):
        self.duration=value

    def metadata_changed(self):
        meta=self.player.metaData()
        self.title=meta.stringValue(QMediaMetaData.Title) or Path(self.queue.current or '').stem or 'Откройте музыку'
        self.artist=meta.stringValue(QMediaMetaData.ContributingArtist) or meta.stringValue(QMediaMetaData.AlbumArtist) or 'Неизвестный исполнитель'
        self.album=meta.stringValue(QMediaMetaData.AlbumTitle) or Path(self.queue.current or '').parent.name
        cover=meta.value(QMediaMetaData.CoverArtImage)
        if not isinstance(cover,QImage) or cover.isNull():
            cover=meta.value(QMediaMetaData.ThumbnailImage)
        if isinstance(cover,QImage) and not cover.isNull():
            self.cover=cover
        self.canvas.setToolTip(f'{self.title}\n{self.artist}\n{self.queue.current or ""}')

    def playback_changed(self,state):
        self.canvas.buttons['play'].setText('Ⅱ PAUSE' if state==QMediaPlayer.PlayingState else '▶ PLAY')

    def media_status(self,status):
        if status in (QMediaPlayer.LoadedMedia,QMediaPlayer.BufferedMedia) and self.pending_position:
            position=self.pending_position
            self.pending_position=0
            self.player.setPosition(min(position,max(0,self.duration-250)))
        if status==QMediaPlayer.EndOfMedia:
            if self.store.state.get('repeat')=='one':
                self.player.setPosition(0)
                self.player.play()
            else:
                source=self.player.source()
                index=self.queue.index
                QTimer.singleShot(0,lambda:self.next_track(automatic=True)
                                  if self.player.source()==source and self.queue.index==index
                                  and self.player.mediaStatus()==QMediaPlayer.EndOfMedia else None)

    def media_error(self,error,text):
        self.last_error=text
        logging.error('Playback: %s: %s',self.queue.current,text)
        self.artist='Ошибка воспроизведения'
        self.album=text
        self.canvas.setToolTip(text)

    def load_current(self,play=True,position=0):
        path=self.queue.current
        if not path:
            return
        if not Path(path).is_file():
            self.notify('Файл не найден: '+path)
            return
        self.player.stop()
        self.last_error=''
        self.pending_position=max(0,int(position))
        self.position=0
        self.duration=0
        self.title=Path(path).stem
        self.artist=''
        self.album=Path(path).parent.name
        self.cover=QImage()
        for name in ('cover.jpg','folder.jpg','cover.png','folder.png'):
            image=QImage(str(Path(path).parent/name))
            if not image.isNull():
                self.cover=image
                break
        self.audio_format=Path(path).suffix[1:].upper()
        self.player.setSource(QUrl.fromLocalFile(path))
        if play:
            self.player.play()
        self.queueChanged.emit()
        self.persist()

    def open_paths(self,paths,play=True):
        try:
            tracks,index,source=open_selection(paths)
        except (OSError,ValueError) as exc:
            self.notify(str(exc))
            return
        if not tracks:
            self.notify('В выбранных файлах или папке нет поддерживаемой музыки.')
            return
        self.queue.replace(tracks,index)
        self.store.state['source']=source
        self.load_current(play)

    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Открыть музыку',str(Path(self.queue.current).parent) if self.queue.current else '',
                    'Музыка и плейлисты (*.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus *.wma *.aiff *.m3u *.m3u8 *.pls);;Все файлы (*)')
        if paths:
            self.open_paths(paths)

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Папка с музыкой')
        if folder:
            self.open_paths([folder])

    def toggle(self):
        if not self.queue.current:
            self.choose_files()
        elif self.player.playbackState()==QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.player.source().isEmpty():
            self.load_current()
        else:
            self.player.play()

    def next_track(self,automatic=False):
        if self.queue.advance(1,self.store.state.get('repeat')=='all',self.store.state.get('shuffle',False),automatic):
            self.load_current(True)
        elif not automatic:
            self.notify('Конец списка. Повтор всей очереди включается в меню (W).')

    def previous_track(self):
        if self.queue.advance(-1,self.store.state.get('repeat')=='all',self.store.state.get('shuffle',False)):
            self.load_current(True)

    def set_volume(self,value):
        self.audio.setVolume(max(0,min(100,value))/100)
        self.canvas.update()

    def notify(self,text):
        self.canvas.setToolTip(text)
        QToolTip.showText(self.mapToGlobal(self.rect().center()),text,self)

    def action(self,key):
        actions={'previous':self.previous_track,'next':self.next_track,'play':self.toggle,
                 'stop':self.player.stop,'playlist':self.show_playlists,'skin':self.show_theme,
                 'exit':self.close,'info':self.show_info,'visual':self.switch_visual,
                 'options':lambda:self.show_menu(self.mapToGlobal(self.rect().bottomRight()))}
        actions[key]()

    def show_info(self):
        QMessageBox.information(self,'Текущий трек',f'{self.title}\n{self.artist}\n{self.album}\n\n'
                                f'{self.audio_format}\n{clock_text(self.duration)}\n\n{self.queue.current or "Файл не выбран"}')

    def switch_visual(self):
        from visualizers import VisualizerDialog
        if self.visual_dialog is None:
            self.visual_dialog=VisualizerDialog(self)
            self.visual_dialog.finished.connect(lambda *_:setattr(self,'visual_dialog',None))
        self.visual_dialog.show()
        self.visual_dialog.raise_()

    def set_visualizer(self,key):
        if key in PRESET_IDS:
            self.visual_preset=key
            self.canvas.buttons['visual'].setToolTip('Визуализация: '+preset_info(key)[1])
            self.canvas.update()
            self.persist()

    def show_playlists(self):
        from dialogs import PlaylistDialog
        if self.playlists_dialog is None:
            self.playlists_dialog=PlaylistDialog(self)
        self.playlists_dialog.refresh()
        self.playlists_dialog.show()
        self.playlists_dialog.raise_()
        self.playlists_dialog.activateWindow()

    def show_theme(self):
        from dialogs import ThemeDialog
        if self.theme_dialog is not None:
            self.theme_dialog.raise_()
            return
        dialog=ThemeDialog(self)
        self.theme_dialog=dialog
        dialog.finished.connect(lambda *_:setattr(self,'theme_dialog',None))
        dialog.show()

    def set_theme(self,theme):
        self.theme=validated_theme(theme)
        self.canvas.set_theme(self.theme)
        self.resize_reference()
        self.persist()

    def resize_reference(self,factor=1):
        # Original WAVEN uses an 800 x 250 physical-pixel surface on this PC.
        ratio=self.devicePixelRatioF()
        self.resize(round(self.theme['width']*factor/ratio),round(self.theme['height']*factor/ratio))

    def show_menu(self,point):
        menu=QMenu(self)
        menu.addAction('Открыть файлы…',self.choose_files)
        menu.addAction('Открыть папку…',self.choose_folder)
        menu.addAction('Плейлисты…',self.show_playlists)
        menu.addAction('Оформление…',self.show_theme)
        if sys.platform=='win32':
            from windows_integration import choose_default
            menu.addAction('Сделать плеером по умолчанию…',lambda:choose_default(self))
        menu.addSeparator()
        shuffle=menu.addAction('Перемешивать')
        shuffle.setCheckable(True)
        shuffle.setChecked(bool(self.store.state.get('shuffle')))
        shuffle.toggled.connect(lambda flag:self.setting('shuffle',flag))
        repeat=menu.addMenu('Повтор')
        for name,value in [('Выключен','off'),('Вся очередь','all'),('Один трек','one')]:
            action=repeat.addAction(name)
            action.setCheckable(True)
            action.setChecked(self.store.state.get('repeat','off')==value)
            action.triggered.connect(lambda checked=False,v=value:self.setting('repeat',v))
        scale=menu.addMenu('Размер окна')
        for factor in (1,1.25,1.5,2):
            scale.addAction(f'{round(factor*100)}%',lambda f=factor:self.resize_reference(f))
        top=menu.addAction('Поверх всех окон')
        top.setCheckable(True)
        top.setChecked(bool(self.windowFlags() & Qt.WindowStaysOnTopHint))
        top.toggled.connect(self.always_on_top)
        menu.addAction('Свернуть',self.showMinimized)
        menu.addSeparator()
        menu.addAction('О программе',lambda:QMessageBox.information(self,'WAVEN Custom',
                      'Локальная версия по вашему визуальному образцу WAVEN.\n'
                      'Редактируемый исходный проект на Python / PySide6.\n\n'
                      'Ctrl+O — файлы; Ctrl+Shift+O — папка\nCtrl+L — плейлисты; Ctrl+T — оформление\n'
                      'Пробел — пауза; Ctrl+←/→ — предыдущая/следующая\n'
                      'Громкость — ползунок или колесо мыши.\n\nБиблиотека: '+str(self.store.path)))
        menu.addAction('Выход',self.close)
        menu.exec(point)

    def always_on_top(self,enabled):
        self.setWindowFlag(Qt.WindowStaysOnTopHint,enabled)
        self.show()

    def setting(self,key,value):
        self.store.state[key]=value
        self.persist()

    def persist(self):
        self.store.state.update(queue=self.queue.tracks[:],index=self.queue.index,
                                position=self.pending_position or self.position,volume=round(self.audio.volume()*100),
                                theme=copy.deepcopy(self.theme),visual_preset=self.visual_preset,
                                window_position=[self.x(),self.y()])
        try:
            self.store.save()
        except OSError as exc:
            logging.error('Save: %s',exc)
            self.notify('Не удалось сохранить библиотеку: '+str(exc))

    def closeEvent(self,event):
        if self.theme_dialog is not None:
            self.theme_dialog.reject()
        self.persist()
        self.player.stop()
        QApplication.instance().quit()
        event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('Waven Custom')
    app.setApplicationVersion('2.0.0')
    app.setOrganizationName('Drago')
    app.setStyle('Fusion')
    app.setWindowIcon(app_icon())
    if '--make-default' in sys.argv:
        from windows_integration import choose_default
        choose_default(confirm=False)
        return 0
    store=Store()
    logging.basicConfig(filename=str(store.directory/'player.log'),level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
    def exception_hook(kind,value,tb):
        logging.error('Unhandled error',exc_info=(kind,value,tb))
        QMessageBox.critical(None,'Ошибка Waven Custom',str(value)+'\n\nПодробности: '+str(store.directory/'player.log'))
    sys.excepthook=exception_hook
    paths=[os.path.abspath(p) for p in sys.argv[1:] if not p.startswith('--')]
    server_name='WavenCustom_'+hashlib.sha256(str(store.directory.resolve()).encode()).hexdigest()[:16]
    socket=QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(500):
        socket.write(json.dumps(paths,ensure_ascii=False).encode('utf-8')+b'\n')
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return 0
    lock=QLockFile(str(store.directory/'player.lock'))
    lock.setStaleLockTime(10000)
    if not lock.tryLock(1000):
        QMessageBox.warning(None,'Waven Custom','Плеер уже запускается. Повторите открытие файла через несколько секунд.')
        return 1
    QLocalServer.removeServer(server_name)
    server=QLocalServer(app)
    if not server.listen(server_name):
        raise RuntimeError(server.errorString())
    window=PlayerWindow(store)
    clients={}
    def accept_client():
        client=server.nextPendingConnection()
        clients[client]=bytearray()
        def read():
            clients[client].extend(bytes(client.readAll()))
            if len(clients[client])>1_000_000:
                client.disconnectFromServer()
                return
            if b'\n' in clients[client]:
                try:
                    payload=json.loads(bytes(clients[client]).split(b'\n')[0])
                    if isinstance(payload,list) and all(isinstance(p,str) for p in payload) and payload:
                        window.open_paths(payload)
                    window.showNormal()
                    window.raise_()
                    window.activateWindow()
                except (ValueError,OSError) as exc:
                    window.notify(str(exc))
                client.disconnectFromServer()
        client.readyRead.connect(read)
        client.disconnected.connect(lambda:(clients.pop(client,None),client.deleteLater()))
        if client.bytesAvailable():
            read()
    server.newConnection.connect(accept_client)
    window.show()
    if paths:
        QTimer.singleShot(0,lambda:window.open_paths(paths))
    result=app.exec()
    server.close()
    lock.unlock()
    return result


if __name__=='__main__':
    sys.exit(main())
