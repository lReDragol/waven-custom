"""Qt appearance workbench: elements, canvas, inspector and undo history."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from xml.etree.ElementTree import ParseError
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QShortcut, QKeySequence
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem, QSplitter, QScrollArea,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QGridLayout, QFileDialog,
    QColorDialog, QMessageBox)
from theme import DEFAULT_THEME, LABELS, COLOR_LABELS, validated_theme, import_theme
from ui_style import DIALOG_STYLE

GROUPS = {
    'МЕДИА': ('cover','title','artist','album'),
    'ИНДИКАТОРЫ': ('visualizer','format','meter_left','meter_right','progress','time','volume'),
    'УПРАВЛЕНИЕ': ('previous','play','next','stop','playlist','info','visual','skin','options','mode'),
    'ОКНО': ('logo','exit'),
}
PALETTES = {
    'Графит': {'background_top':'#161c27','background_bottom':'#202d3d','border':'#44546a',
              'text':'#f1f4fa','artist':'#c0d0e2','album':'#8fa5bd','button':'#435570',
              'small_button':'#33465d','stop':'#394558','accent':'#73c9fa',
              'play_background':'#84d2ed','play_text':'#102839','track':'#101923'},
    'Светлая': {'background_top':'#f5f7fa','background_bottom':'#e2eaf2','border':'#a2b4c7',
               'text':'#14253a','artist':'#344e69','album':'#577089','button':'#d0dce8',
               'small_button':'#c8d7e5','stop':'#c4d0df','accent':'#118b85',
               'play_background':'#146d6c','play_text':'#ffffff','track':'#b6c6d6'},
    'Оригинал': DEFAULT_THEME['colors'],
}


class CanvasStage(QWidget):
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#0b1018'))
        p.setPen(QPen(QColor('#202c3b'),1))
        for x in range(16,self.width(),20):
            for y in range(16,self.height(),20):p.drawPoint(x,y)


class ThemeDialog(QDialog):
    def __init__(self,player):
        super().__init__(player)
        from app import PlayerCanvas
        self.player=player;self.draft=copy.deepcopy(player.theme);self.original=copy.deepcopy(player.theme)
        self.history=[copy.deepcopy(self.draft)];self.history_index=0;self.syncing=False
        self.selected_key='play'
        self.setWindowTitle('Оформление — WAVEN Custom');self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumSize(960,600);self.resize(1200,730)
        screen=self.screen().availableGeometry()
        self.resize(min(self.width(),screen.width()-40),min(self.height(),screen.height()-60))
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(0)
        header=QHBoxLayout();header.setContentsMargins(24,18,24,16)
        headings=QVBoxLayout();headings.setSpacing(3)
        title=QLabel('Оформление');title.setStyleSheet('font-size:23px;font-weight:600;color:#f2f5fa')
        headings.addWidget(title);sub=QLabel('Настройте плеер под себя');sub.setStyleSheet('color:#8fa1b7')
        headings.addWidget(sub);header.addLayout(headings,1)
        self.state_label=QLabel('Все изменения сохранены');self.state_label.setStyleSheet('color:#8fa1b7')
        header.addWidget(self.state_label);root.addLayout(header)
        toolbar=QHBoxLayout();toolbar.setContentsMargins(20,0,20,16);toolbar.setSpacing(8)
        self.name=QLineEdit(self.draft['name']);self.name.setPlaceholderText('Название темы');self.name.setMaximumWidth(280)
        self.name.editingFinished.connect(self.change_name);toolbar.addWidget(self.name)
        self.palette=QComboBox();self.palette.addItems(['Готовые палитры…',*PALETTES]);self.palette.setFixedWidth(165)
        self.palette.activated.connect(self.choose_palette);toolbar.addWidget(self.palette);toolbar.addStretch()
        self.undo_button=self.button('↶',self.undo,toolbar,'Отменить · Ctrl+Z');self.undo_button.setFixedWidth(38)
        self.redo_button=self.button('↷',self.redo,toolbar,'Повторить · Ctrl+Y');self.redo_button.setFixedWidth(38)
        self.button('Сбросить оформление',self.reset_theme,toolbar)
        self.button('Импорт',self.import_file,toolbar);self.button('Экспорт',self.export_file,toolbar);root.addLayout(toolbar)
        splitter=QSplitter(Qt.Horizontal);root.addWidget(splitter,1)
        layers_panel=QWidget();layers_panel.setObjectName('panel');layers_layout=QVBoxLayout(layers_panel)
        layers_layout.setContentsMargins(14,16,10,12);layers_layout.setSpacing(12)
        self.section_label('ЭЛЕМЕНТЫ',layers_layout)
        self.layers=QTreeWidget();self.layers.setHeaderHidden(True);self.layers.setRootIsDecorated(False)
        self.layers.setIndentation(0);self.layers.setStyleSheet('QTreeWidget {border:0;background:transparent;padding:0;} QTreeWidget::item {height:21px;padding:4px 8px;}')
        self.layer_items={}
        for group,keys in GROUPS.items():
            parent=QTreeWidgetItem([group]);parent.setFlags(Qt.ItemIsEnabled);parent.setForeground(0,QColor('#72869f'))
            self.layers.addTopLevelItem(parent);parent.setExpanded(True)
            for key in keys:
                item=QTreeWidgetItem([LABELS[key]]);item.setData(0,Qt.UserRole,key);parent.addChild(item);self.layer_items[key]=item
        self.layers.currentItemChanged.connect(self.layer_changed);layers_layout.addWidget(self.layers)
        layers_panel.setMinimumWidth(170);layers_panel.setMaximumWidth(245);splitter.addWidget(layers_panel)
        center=QWidget();center.setObjectName('panel');center_layout=QVBoxLayout(center);center_layout.setContentsMargins(0,0,0,0);center_layout.setSpacing(0)
        canvas_tools=QHBoxLayout();canvas_tools.setContentsMargins(16,12,16,12)
        self.canvas_size=QLabel();self.canvas_size.setStyleSheet('color:#8fa1b7');canvas_tools.addWidget(self.canvas_size,1)
        self.outlines=QCheckBox('Контуры');self.outlines.toggled.connect(self.change_outlines);canvas_tools.addWidget(self.outlines)
        self.zoom_combo=QComboBox();self.zoom_combo.addItems(['Вписать','50%','75%','100%','125%','150%'])
        self.zoom_combo.setFixedWidth(92);self.zoom_combo.currentIndexChanged.connect(self.update_zoom);canvas_tools.addWidget(self.zoom_combo)
        center_layout.addLayout(canvas_tools)
        self.stage=CanvasStage();stage_layout=QVBoxLayout(self.stage);stage_layout.setContentsMargins(20,20,20,20)
        self.preview=PlayerCanvas(player,self.draft,preview=True);self.preview.edit_mode=True
        self.preview.selected=self.selected_key;self.preview.show_all_outlines=False
        stage_layout.addWidget(self.preview,0,Qt.AlignCenter)
        self.canvas_scroll=QScrollArea();self.canvas_scroll.setWidgetResizable(True);self.canvas_scroll.setWidget(self.stage)
        center_layout.addWidget(self.canvas_scroll,1)
        canvas_hint=QLabel('Перетащите элемент • Потяните за угол, чтобы изменить размер')
        canvas_hint.setWordWrap(True);canvas_hint.setStyleSheet('color:#71869f;padding:12px 16px;font-size:11px')
        center_layout.addWidget(canvas_hint);splitter.addWidget(center)
        inspector=QWidget();inspector.setObjectName('panel');inspector.setMinimumWidth(270);inspector.setMaximumWidth(340)
        inspector_layout=QVBoxLayout(inspector);inspector_layout.setContentsMargins(0,0,0,0)
        self.tabs=QTabWidget();inspector_layout.addWidget(self.tabs)
        props,props_layout=self.inspector_page();self.tabs.addTab(props,'Элемент')
        self.element_title=QLabel();self.element_title.setStyleSheet('font-size:18px;font-weight:600;color:#f0f5fb');props_layout.addWidget(self.element_title)
        self.section_label('ПОЛОЖЕНИЕ И РАЗМЕР',props_layout)
        geo=QGridLayout();geo.setSpacing(10);self.coords=[]
        for i,label in enumerate(('X','Y','Ширина','Высота')):
            cell=QVBoxLayout();cell.setSpacing(5);cell.addWidget(QLabel(label))
            spin=QSpinBox();spin.setRange(0,2400);spin.setSuffix(' px');spin.setKeyboardTracking(False)
            spin.valueChanged.connect(self.change_geometry);cell.addWidget(spin);self.coords.append(spin);geo.addLayout(cell,i//2,i%2)
        props_layout.addLayout(geo);self.section_label('ВЫРАВНИВАНИЕ ПО ХОЛСТУ',props_layout)
        alignment=QHBoxLayout();alignment.setSpacing(5)
        for title,mode in [('Слева','left'),('Центр','center'),('Справа','right')]:
            self.button(title,lambda checked=False,m=mode:self.align_element(m),alignment)
        props_layout.addLayout(alignment);self.section_label('ЦВЕТ ЭЛЕМЕНТА',props_layout)
        self.element_color_layout=QVBoxLayout();props_layout.addLayout(self.element_color_layout)
        self.element_color_note=QLabel();self.element_color_note.setWordWrap(True);self.element_color_note.setStyleSheet('color:#8fa1b7');props_layout.addWidget(self.element_color_note)
        props_layout.addStretch();self.button('Восстановить этот элемент',self.reset_element,props_layout)
        palette_page,palette_layout=self.inspector_page();self.tabs.addTab(palette_page,'Палитра')
        self.color_buttons={}
        for heading,keys in [('ПОВЕРХНОСТИ',('background_top','background_bottom','border','track')),
                             ('ТЕКСТ',('text','artist','album')),
                             ('УПРАВЛЕНИЕ',('play_background','play_text','button','stop','small_button','accent')),
                             ('ИНДИКАТОРЫ КАНАЛОВ',('meter',))]:
            self.section_label(heading,palette_layout)
            for key in keys:self.color_buttons[key]=self.color_row(key,palette_layout)
        palette_layout.addStretch()
        canvas_page,canvas_layout=self.inspector_page();self.tabs.addTab(canvas_page,'Окно');self.section_label('РАЗМЕР ОКНА ПРИ 100%',canvas_layout)
        self.width=self.number_row('Ширина',300,2400,' px',canvas_layout)
        self.height=self.number_row('Высота',94,2400,' px',canvas_layout)
        hint=QLabel('Базовый размер в логических пикселях. Масштаб Windows учитывается автоматически.');hint.setWordWrap(True);canvas_layout.addWidget(hint)
        self.section_label('ТИПОГРАФИКА',canvas_layout);self.font=self.number_row('Базовый текст',7,28,' px',canvas_layout)
        hint=QLabel('Размер задаётся в пикселях макета. Масштаб предпросмотра не меняет размер плеера.')
        hint.setWordWrap(True);hint.setStyleSheet('color:#8fa1b7');canvas_layout.addWidget(hint)
        canvas_layout.addStretch();self.button('Сбросить всю тему',self.reset_theme,canvas_layout)
        splitter.addWidget(inspector);splitter.setSizes([190,670,300]);splitter.setStretchFactor(1,1)
        splitter.splitterMoved.connect(self.update_zoom)
        footer=QHBoxLayout();footer.setContentsMargins(20,14,20,14);footer.setSpacing(10)
        note=QLabel('Предпросмотр не изменяет плеер до применения');note.setStyleSheet('color:#8fa1b7');footer.addWidget(note,1)
        self.button('Отмена',self.reject,footer);self.apply_button=self.button('Применить',self.apply,footer)
        self.save_button=self.button('Сохранить',self.accept,footer);self.save_button.setObjectName('primary');root.addLayout(footer)
        self.preview.elementSelected.connect(self.preview_selected);self.preview.geometryEdited.connect(self.preview_moved)
        self.preview.editFinished.connect(self.record)
        self.shortcuts=[]
        for keys,action in [('Ctrl+Z',self.undo),('Ctrl+Y',self.redo),('Ctrl+Shift+Z',self.redo),('Ctrl+S',self.apply)]:
            shortcut=QShortcut(QKeySequence(keys),self);shortcut.activated.connect(action);self.shortcuts.append(shortcut)
        self.timer=QTimer(self);self.timer.timeout.connect(self.preview.update);self.timer.start(40)
        self.refresh();QTimer.singleShot(0,self.update_zoom)

    def button(self,text,callback,layout,tip=None):
        button=QPushButton(text);button.clicked.connect(callback)
        if tip:button.setToolTip(tip)
        layout.addWidget(button);return button

    def inspector_page(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True);widget=QWidget();widget.setObjectName('panel')
        layout=QVBoxLayout(widget);layout.setContentsMargins(16,18,16,18);layout.setSpacing(12);scroll.setWidget(widget)
        return scroll,layout

    def section_label(self,text,layout):
        label=QLabel(text);label.setStyleSheet('color:#778da6;font-size:10px;font-weight:600;padding-top:12px');layout.addWidget(label)

    def number_row(self,label,minimum,maximum,suffix,layout):
        row=QHBoxLayout();row.addWidget(QLabel(label),1)
        value=QSpinBox();value.setRange(minimum,maximum);value.setSuffix(suffix);value.setMaximumWidth(120)
        value.setKeyboardTracking(False);value.valueChanged.connect(self.change_dimensions);row.addWidget(value);layout.addLayout(row);return value

    def color_row(self,key,layout):
        row=QHBoxLayout();label=QLabel(COLOR_LABELS[key]);label.setWordWrap(True);row.addWidget(label,1)
        button=QPushButton();button.setFixedWidth(87);button.setToolTip(COLOR_LABELS[key])
        button.clicked.connect(lambda checked=False,k=key:self.choose_color(k));row.addWidget(button);layout.addLayout(row)
        self.paint_swatch(button,self.draft['colors'][key]);return button

    def paint_swatch(self,button,color):
        button.setText(color.upper());text='#101820' if QColor(color).lightness()>145 else '#ffffff'
        button.setStyleSheet(f'background:{color};color:{text};border:1px solid #58687e;padding:6px 4px;font-size:10px;')

    def refresh(self):
        self.syncing=True;self.name.setText(self.draft['name'])
        for widget,key in ((self.width,'window_width'),(self.height,'window_height'),(self.font,'font_size')):widget.setValue(self.draft[key])
        for key,button in self.color_buttons.items():self.paint_swatch(button,self.draft['colors'][key])
        self.preview.set_theme(self.draft);self.preview.selected=self.selected_key
        self.layers.setCurrentItem(self.layer_items[self.selected_key]);self.update_properties()
        self.syncing=False;self.update_status();self.update_zoom()

    def update_properties(self):
        self.element_title.setText(LABELS[self.selected_key])
        for widget,value in zip(self.coords,self.draft['elements'][self.selected_key]):
            widget.blockSignals(True);widget.setValue(value);widget.blockSignals(False)
        while self.element_color_layout.count():
            child=self.element_color_layout.takeAt(0)
            if child.layout():
                while child.layout().count():
                    item=child.layout().takeAt(0)
                    if item.widget():item.widget().deleteLater()
        keys={'play':('play_background','play_text'),'previous':('button',),'next':('button',),'stop':('stop',),
              'title':('text',),'artist':('artist',),'album':('album',),'progress':('accent','track'),
              'volume':('accent','track'),'meter_left':('meter',),'meter_right':('meter',),
              'visualizer':()}.get(self.selected_key,())
        if self.selected_key in ('playlist','info','visual','skin','options','mode'):keys=('small_button','text')
        for key in keys:self.color_row(key,self.element_color_layout)
        self.element_color_note.setText('Цвета и параметры каждого эффекта настраиваются в окне VIS.' if self.selected_key=='visualizer'
                                        else '' if keys else 'Цвет задаётся содержимым элемента.')

    def update_status(self):
        dirty=self.draft!=self.original
        self.state_label.setText('Есть несохранённые изменения' if dirty else 'Все изменения сохранены')
        self.apply_button.setEnabled(dirty);self.undo_button.setEnabled(self.history_index>0)
        self.redo_button.setEnabled(self.history_index<len(self.history)-1)

    def record(self):
        if self.draft!=self.history[self.history_index]:
            self.history=self.history[:self.history_index+1]+[copy.deepcopy(self.draft)]
            self.history=self.history[-80:];self.history_index=len(self.history)-1
        self.update_status()

    def undo(self):
        if self.history_index>0:self.history_index-=1;self.draft=copy.deepcopy(self.history[self.history_index]);self.refresh()

    def redo(self):
        if self.history_index<len(self.history)-1:self.history_index+=1;self.draft=copy.deepcopy(self.history[self.history_index]);self.refresh()

    def layer_changed(self,item,*args):
        if self.syncing or not item:return
        key=item.data(0,Qt.UserRole)
        if key:self.preview_selected(key)

    def preview_selected(self,key):
        self.selected_key=key;self.preview.selected=key
        self.layers.blockSignals(True);self.layers.setCurrentItem(self.layer_items[key]);self.layers.blockSignals(False)
        self.update_properties();self.preview.update()

    def change_geometry(self):
        if self.syncing:return
        self.draft['elements'][self.selected_key]=[w.value() for w in self.coords]
        self.draft=validated_theme(self.draft);self.preview.set_theme(self.draft);self.update_properties();self.record()

    def preview_moved(self,key,rect):
        self.draft['elements'][key]=rect[:]
        for widget,value in zip(self.coords,rect):widget.blockSignals(True);widget.setValue(value);widget.blockSignals(False)
        self.update_status()

    def align_element(self,mode):
        rect=self.draft['elements'][self.selected_key]
        rect[0]=0 if mode=='left' else (self.draft['width']-rect[2])//2 if mode=='center' else self.draft['width']-rect[2]
        self.record();self.refresh()

    def change_dimensions(self):
        if self.syncing:return
        self.draft.update(window_width=self.width.value(),window_height=self.height.value(),font_size=self.font.value())
        self.draft=validated_theme(self.draft);self.record();self.refresh()

    def change_name(self):
        if self.syncing:return
        self.draft['name']=self.name.text().strip() or 'Моя тема';self.record()

    def choose_color(self,key):
        color=QColorDialog.getColor(QColor(self.draft['colors'][key]),self,COLOR_LABELS[key])
        if color.isValid():self.draft['colors'][key]=color.name();self.record();self.refresh()

    def choose_palette(self,index):
        name=self.palette.itemText(index)
        if name in PALETTES:self.draft['colors'].update(PALETTES[name]);self.record();self.refresh()
        self.palette.setCurrentIndex(0)

    def change_outlines(self,enabled):
        self.preview.show_all_outlines=enabled;self.preview.update()

    def update_zoom(self,*args):
        if not hasattr(self,'canvas_scroll'):return
        index=self.zoom_combo.currentIndex();area=self.canvas_scroll.viewport().size()
        factor=min((area.width()-48)/self.draft['window_width'],(area.height()-48)/self.draft['window_height'],1.25) if index==0 else (.5,.75,1,1.25,1.5)[index-1]
        factor=max(.15,factor)
        self.preview.setFixedSize(round(self.draft['window_width']*factor),round(self.draft['window_height']*factor))
        self.canvas_size.setText(f'{self.draft["window_width"]} × {self.draft["window_height"]}  ·  {round(factor*100)}%')

    def resizeEvent(self,event):
        super().resizeEvent(event);QTimer.singleShot(0,self.update_zoom)

    def reset_element(self):
        self.draft['elements'][self.selected_key]=DEFAULT_THEME['elements'][self.selected_key][:]
        self.draft=validated_theme(self.draft);self.record();self.refresh()

    def reset_theme(self):
        if QMessageBox.question(self,'Сбросить оформление?','Вернуть исходные цвета, расположение и размер 600 × 188 при 100%? Плейлисты не изменятся. Действие можно отменить через Ctrl+Z.')==QMessageBox.Yes:
            self.draft=copy.deepcopy(DEFAULT_THEME);self.record();self.refresh()

    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Импорт темы','','Темы (*.json *.xml)')
        if path:
            try:self.draft=import_theme(path);self.record();self.refresh()
            except (OSError,ValueError,TypeError,AttributeError,ParseError) as exc:QMessageBox.warning(self,'Тема не прочитана',str(exc))

    def export_file(self):
        self.change_name();path,_=QFileDialog.getSaveFileName(self,'Экспорт темы','waven-theme.json','Тема (*.json)')
        if path:
            try:Path(path).write_text(json.dumps(self.draft,ensure_ascii=False,indent=2),encoding='utf-8')
            except OSError as exc:QMessageBox.warning(self,'Не удалось сохранить',str(exc))

    def apply(self):
        self.change_name();self.player.set_theme(self.draft);self.original=copy.deepcopy(self.player.theme);self.update_status()

    def accept(self):
        self.apply();self.timer.stop();super().accept()

    def reject(self):
        self.timer.stop();super().reject()
