from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QListWidget,QListWidgetItem,QTreeWidget,QTreeWidgetItem,QHeaderView,QAbstractItemView,
    QSplitter,QLineEdit,QMenu,QInputDialog,QFileDialog,QMessageBox)
from core import AUDIO_EXTENSIONS,unique_paths,normalized,folder_tracks,read_playlist,write_playlist
from track_metadata import MetadataCache


def duration_text(seconds):
    if not seconds:
        return '—'
    if seconds>=3600:
        return f'{seconds//3600}:{seconds//60%60:02}:{seconds%60:02}'
    return f'{seconds//60}:{seconds%60:02}'


class TrackTable(QTreeWidget):
    reordered=Signal()

    def __init__(self):
        super().__init__()
        self.setRootIsDecorated(False)
        self.setColumnCount(5)
        self.setHeaderLabels(['#','Название','Исполнитель','Альбом','Время'])
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0,QHeaderView.Fixed)
        self.header().setSectionResizeMode(1,QHeaderView.Stretch)
        self.header().setSectionResizeMode(4,QHeaderView.Fixed)
        self.setColumnWidth(0,35);self.setColumnWidth(2,160)
        self.setColumnWidth(3,130);self.setColumnWidth(4,62)

    def count(self):
        return self.topLevelItemCount()

    def item(self,index):
        return self.topLevelItem(index)

    def row(self,item):
        return self.indexOfTopLevelItem(item)

    def currentRow(self):
        return self.row(self.currentItem()) if self.currentItem() else -1

    def setCurrentRow(self,index):
        self.setCurrentItem(self.item(index))

    def dropEvent(self,event):
        super().dropEvent(event)
        self.reordered.emit()


class PlaylistDialog(QDialog):
    def __init__(self,player):
        super().__init__(player)
        from dialogs import DIALOG_STYLE
        self.player=player;self.store=player.store
        self.metadata=MetadataCache(self);self.metadata.ready.connect(self.metadata_ready)
        self.setWindowTitle('Музыка и плейлисты · WAVEN Custom')
        self.setStyleSheet(DIALOG_STYLE+'''
QTreeWidget {background:#0d202a;alternate-background-color:#102630;color:#e9f3f5;
 border:1px solid #294753;outline:0;selection-background-color:#215869;}
QTreeWidget::item {height:34px;border-bottom:1px solid #183440;}
QTreeWidget::item:selected {background:#215869;color:white;}
QHeaderView::section {background:#142e3b;color:#9db9c6;padding:8px;border:0;border-bottom:1px solid #36515d;}
QPushButton#primary {background:#56e2c6;color:#052531;font-weight:600;border-radius:5px;}
QPushButton#primary:disabled {background:#214038;color:#76948b;}
QPushButton#subtle {background:transparent;border:1px solid #2c4a56;border-radius:5px;}
QLabel#muted {color:#94b0bf;}
QListWidget {border:0;background:#0c1922;}
QListWidget::item {padding:11px 9px;border-radius:5px;}
''')
        self.resize(1080,630);self.setMinimumSize(880,500)
        root=QVBoxLayout(self);root.setContentsMargins(20,18,20,16);root.setSpacing(14)
        title=QLabel('Ваша музыка');title.setStyleSheet('font-size:24px;font-weight:600;color:#f0f9fc')
        root.addWidget(title)
        self.now_playing=QLabel();self.now_playing.setObjectName('muted');root.addWidget(self.now_playing)
        split=QSplitter();root.addWidget(split,1)
        left=QWidget();left.setObjectName('panel');sidebar=QVBoxLayout(left)
        sidebar.setContentsMargins(0,0,16,0)
        self.lists=QListWidget();self.lists.setMinimumWidth(205)
        sidebar.addWidget(self.lists,1)
        self.new_button=self.make_button('＋ Создать плейлист',self.create,sidebar)
        self.new_button.setObjectName('primary')
        self.import_button=self.make_button('Импортировать список…',self.import_list,sidebar)
        self.import_button.setObjectName('subtle')
        split.addWidget(left)
        right=QWidget();right.setObjectName('panel');content=QVBoxLayout(right);content.setContentsMargins(12,0,0,0)
        heading=QHBoxLayout();self.collection_name=QLabel();self.collection_name.setStyleSheet('font-size:20px;font-weight:600;color:#ebf8fb')
        heading.addWidget(self.collection_name,1)
        self.more_button=self.make_button('•••',self.more_menu,heading)
        self.more_button.setToolTip('Переименовать, экспортировать или удалить плейлист')
        content.addLayout(heading)
        self.explanation=QLabel();self.explanation.setObjectName('muted');self.explanation.setWordWrap(True)
        content.addWidget(self.explanation)
        toolbar=QHBoxLayout()
        self.play_button=self.make_button('▶ Воспроизвести',lambda:self.play(),toolbar);self.play_button.setObjectName('primary')
        self.add_button=self.make_button('＋ Добавить музыку',self.add_menu,toolbar)
        self.save_button=self.make_button('Сохранить как плейлист…',self.save_queue_as,toolbar)
        toolbar.addStretch();content.addLayout(toolbar)
        self.search=QLineEdit();self.search.setPlaceholderText('Найти песню, исполнителя или альбом…');self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_tracks);content.addWidget(self.search)
        self.empty=QLabel('Здесь пока нет песен.\nНажмите «Добавить музыку» и выберите файлы или папку.')
        self.empty.setAlignment(Qt.AlignCenter);self.empty.setStyleSheet('color:#8caebb;padding:30px;font-size:14px;')
        content.addWidget(self.empty)
        self.tracks=TrackTable();content.addWidget(self.tracks,1)
        self.tracks.reordered.connect(self.reorder)
        self.tracks.itemDoubleClicked.connect(lambda item,column:self.play(self.tracks.row(item)))
        self.tracks.itemSelectionChanged.connect(self.selection_changed)
        self.tracks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tracks.customContextMenuRequested.connect(self.track_menu)
        footer=QHBoxLayout()
        self.count_label=QLabel();self.count_label.setObjectName('muted');footer.addWidget(self.count_label,1)
        self.add_to_button=self.make_button('В другой плейлист…',self.add_to_playlist,footer)
        self.remove_button=self.make_button('Убрать из списка',self.remove_tracks,footer)
        self.remove_button.setToolTip('Убрать выбранные строки. Музыкальные файлы не удаляются.')
        content.addLayout(footer);split.addWidget(right);split.setStretchFactor(1,1);split.setSizes([225,815])
        bottom=QHBoxLayout()
        tip=QLabel('Двойной щелчок — играть с этой песни. Перетаскивание строк — изменить порядок.')
        tip.setObjectName('muted');bottom.addWidget(tip,1);self.make_button('Готово',self.hide,bottom);root.addLayout(bottom)
        self.lists.currentItemChanged.connect(self.show_tracks)
        self.lists.itemDoubleClicked.connect(lambda item:self.play(0) if item.data(Qt.UserRole) else None)
        player.queueChanged.connect(self.queue_changed)
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_now_playing);self.timer.start(500)
        self.refresh()

    def make_button(self,text,callback,layout):
        btn=QPushButton(text);btn.clicked.connect(callback);layout.addWidget(btn);return btn

    def identity(self):
        item=self.lists.currentItem();return (item.data(Qt.UserRole) if item else None) or 'queue'

    def selected_tracks(self):
        record=self.store.playlist(self.identity())
        return record['tracks'] if record else self.player.queue.tracks

    def refresh(self,identity=None):
        identity=identity or self.identity();self.lists.blockSignals(True);self.lists.clear()
        current=QListWidgetItem('♫  Сейчас в очереди');current.setData(Qt.UserRole,'queue');self.lists.addItem(current)
        heading=QListWidgetItem('МОИ ПЛЕЙЛИСТЫ');heading.setFlags(Qt.NoItemFlags);heading.setForeground(QColor('#6f939f'))
        self.lists.addItem(heading);chosen=current
        for record in self.store.state['playlists']:
            item=QListWidgetItem(f'{record["name"]}  ·  {len(record["tracks"])}')
            item.setData(Qt.UserRole,record['id']);self.lists.addItem(item)
            if record['id']==identity:chosen=item
        if not self.store.state['playlists']:
            item=QListWidgetItem('Создайте свой первый список');item.setFlags(Qt.NoItemFlags)
            item.setForeground(QColor('#7c98a3'));self.lists.addItem(item)
        self.lists.setCurrentItem(chosen);self.lists.blockSignals(False);self.show_tracks()

    def show_tracks(self,*args):
        record=self.store.playlist(self.identity())
        self.collection_name.setText(record['name'] if record else 'Сейчас в очереди')
        self.explanation.setText('Сохранённый плейлист. Изменения записываются автоматически.' if record else
                                 'Песни, которые плеер проигрывает по порядку. Сохраните их как плейлист, чтобы вернуться к подборке.')
        self.save_button.setVisible(record is None)
        self.more_button.setToolTip('Действия с плейлистом' if record else 'Экспорт текущей очереди')
        self.tracks.blockSignals(True);self.tracks.clear()
        for i,path in enumerate(self.selected_tracks()):
            item=QTreeWidgetItem([str(i+1),'','','',''])
            item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsDragEnabled)
            item.setData(0,Qt.UserRole,path);self.tracks.addTopLevelItem(item)
            self.fill_item(item,self.metadata.request(path))
        self.tracks.blockSignals(False)
        self.empty.setVisible(self.tracks.count()==0);self.tracks.setVisible(self.tracks.count()>0)
        self.play_button.setEnabled(self.tracks.count()>0)
        self.filter_tracks(self.search.text());self.selection_changed();self.update_now_playing()

    def fill_item(self,item,data):
        item.setData(0,Qt.UserRole+1,data)
        item.setText(1,data['title']);item.setText(2,data['artist']);item.setText(3,data['album'])
        item.setText(4,duration_text(data['duration']));item.setTextAlignment(4,Qt.AlignRight|Qt.AlignVCenter)
        path=item.data(0,Qt.UserRole)
        tip=f'{data["title"]}\n{data["artist"]}\n{path}'
        if data.get('missing'):tip+='\nФайл не найден'
        for column in range(5):item.setToolTip(column,tip)
        if data.get('missing'):item.setForeground(1,QColor('#ffac73'))
        playing=self.player.queue.current and normalized(path)==normalized(self.player.queue.current)
        if playing:item.setText(0,'▶');item.setForeground(1,QColor('#56e2c6'))

    def metadata_ready(self,path,data):
        for i in range(self.tracks.count()):
            item=self.tracks.item(i)
            if item.data(0,Qt.UserRole)==path:self.fill_item(item,data)
        self.filter_tracks(self.search.text())

    def filter_tracks(self,text):
        visible=0;total=0
        for index in range(self.tracks.count()):
            item=self.tracks.item(index)
            haystack=' '.join(item.text(c) for c in (1,2,3))+' '+item.data(0,Qt.UserRole)
            hidden=text.casefold() not in haystack.casefold()
            item.setHidden(hidden);visible+=int(not hidden)
            total+=(item.data(0,Qt.UserRole+1) or {}).get('duration',0)
        self.tracks.setDragEnabled(not bool(text))
        self.count_label.setText((f'Найдено: {visible} из {self.tracks.count()}' if text else f'{self.tracks.count()} треков')+
                                (f' · {duration_text(total)}' if total else ''))
        self.play_button.setEnabled(visible>0)
        self.selection_changed()

    def selection_changed(self):
        items=[i for i in self.tracks.selectedItems() if not i.isHidden()]
        self.add_to_button.setEnabled(bool(items));self.remove_button.setEnabled(bool(items))
        self.play_button.setText('▶ Играть с выбранной' if items else '▶ Воспроизвести список')

    def update_now_playing(self):
        if self.isVisible():
            self.now_playing.setText('В плеере: '+self.player.title+(' · '+self.player.artist if self.player.artist else ''))

    def queue_changed(self):
        displayed=[self.tracks.item(i).data(0,Qt.UserRole) for i in range(self.tracks.count())]
        if self.identity()=='queue' and displayed!=self.player.queue.tracks:
            self.show_tracks()
        else:
            for i in range(self.tracks.count()):
                item=self.tracks.item(i);item.setText(0,str(i+1));item.setForeground(1,QColor('#e9f3f5'))
                self.fill_item(item,item.data(0,Qt.UserRole+1))
        self.update_now_playing()

    def commit_tracks(self,paths):
        record=self.store.playlist(self.identity())
        if record:
            record['tracks']=list(paths);self.store.save()
        else:
            current=self.player.queue.current
            index=next((i for i,p in enumerate(paths) if current and normalized(p)==normalized(current)),0)
            still_present=current and any(normalized(p)==normalized(current) for p in paths)
            self.player.queue.replace(paths,index)
            if current and not still_present:
                self.player.player.stop()
                if paths:self.player.load_current(False)
                else:
                    from PySide6.QtCore import QUrl
                    self.player.player.setSource(QUrl());self.player.title='Очередь пуста'
                    self.player.artist='Добавьте музыку';self.player.album='';self.player.cover=type(self.player.cover)()
            self.player.persist()
        self.refresh()

    def reorder(self):
        self.commit_tracks([self.tracks.item(i).data(0,Qt.UserRole) for i in range(self.tracks.count())])

    def create(self):
        name,ok=QInputDialog.getText(self,'Создать плейлист','Как назвать подборку?')
        if ok and name.strip():self.refresh(self.store.create_playlist(name,[])['id'])

    def save_queue_as(self):
        name,ok=QInputDialog.getText(self,'Сохранить очередь','Название плейлиста:')
        if ok and name.strip():self.refresh(self.store.create_playlist(name,self.player.queue.tracks)['id'])

    def rename(self):
        record=self.store.playlist(self.identity())
        if record:
            name,ok=QInputDialog.getText(self,'Переименовать','Название:',text=record['name'])
            if ok and name.strip():record['name']=name.strip();self.store.save();self.refresh()

    def delete(self):
        record=self.store.playlist(self.identity())
        if record and QMessageBox.question(self,'Удалить плейлист',f'Удалить «{record["name"]}»?\nМузыкальные файлы сохранятся.')==QMessageBox.Yes:
            self.store.state['playlists'].remove(record);self.store.save();self.refresh('queue')

    def play(self,index=None):
        paths=list(self.selected_tracks())
        if not paths:return
        if index is None:
            visible=[i for i in range(self.tracks.count()) if not self.tracks.item(i).isHidden()]
            if not visible:return
            selected=[self.tracks.row(i) for i in self.tracks.selectedItems() if not i.isHidden()]
            index=min(selected) if selected else visible[0]
        self.player.queue.replace(paths,index)
        record=self.store.playlist(self.identity())
        if record:self.store.state['source']='Плейлист: '+record['name']
        self.player.load_current(True)

    def add_menu(self):
        menu=QMenu(self);menu.addAction('Выбрать файлы…',self.add_files);menu.addAction('Добавить папку…',self.add_folder)
        menu.exec(self.add_button.mapToGlobal(self.add_button.rect().bottomLeft()))

    def add_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Добавить музыку','','Музыка (*.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus *.wma *.aiff *.mp4);;Все файлы (*)')
        if paths:self.commit_tracks(unique_paths(self.selected_tracks()+[p for p in paths if Path(p).suffix.lower() in AUDIO_EXTENSIONS]))

    def add_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Добавить папку')
        if folder:
            try:self.commit_tracks(unique_paths(self.selected_tracks()+folder_tracks(folder)))
            except OSError as exc:QMessageBox.warning(self,'Папка',str(exc))

    def remove_tracks(self):
        removed={self.tracks.row(item) for item in self.tracks.selectedItems() if not item.isHidden()}
        self.commit_tracks([p for i,p in enumerate(self.selected_tracks()) if i not in removed])

    def add_to_playlist(self):
        paths=[i.data(0,Qt.UserRole) for i in self.tracks.selectedItems() if not i.isHidden()]
        if not paths:return
        menu=QMenu(self)
        def add(record):
            record['tracks']=unique_paths(record['tracks']+paths);self.store.save();self.refresh()
        for record in self.store.state['playlists']:
            menu.addAction(record['name'],lambda checked=False,r=record:add(r))
        if self.store.state['playlists']:menu.addSeparator()
        def create():
            name,ok=QInputDialog.getText(self,'Новый плейлист','Название:')
            if ok and name.strip():self.refresh(self.store.create_playlist(name,paths)['id'])
        menu.addAction('＋ Новый плейлист из выбранного…',create)
        menu.exec(self.add_to_button.mapToGlobal(self.add_to_button.rect().topLeft()))

    def more_menu(self):
        menu=QMenu(self)
        if self.store.playlist(self.identity()):
            menu.addAction('Переименовать…',self.rename)
        menu.addAction('Экспортировать M3U8…',self.export_list)
        if self.store.playlist(self.identity()):menu.addSeparator();menu.addAction('Удалить плейлист…',self.delete)
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def track_menu(self,point):
        menu=QMenu(self);menu.addAction('▶ Играть с выбранной',lambda:self.play())
        menu.addAction('Добавить в плейлист…',self.add_to_playlist);menu.addAction('Убрать из списка',self.remove_tracks)
        menu.exec(self.tracks.viewport().mapToGlobal(point))

    def import_list(self):
        path,_=QFileDialog.getOpenFileName(self,'Импорт плейлиста','','Плейлисты (*.m3u *.m3u8 *.pls)')
        if path:
            try:self.refresh(self.store.create_playlist(Path(path).stem,read_playlist(path))['id'])
            except (OSError,ValueError) as exc:QMessageBox.warning(self,'Импорт',str(exc))

    def export_list(self):
        path,_=QFileDialog.getSaveFileName(self,'Экспорт плейлиста','playlist.m3u8','M3U8 (*.m3u8)')
        if path:
            try:write_playlist(path,self.selected_tracks())
            except OSError as exc:QMessageBox.warning(self,'Экспорт',str(exc))
