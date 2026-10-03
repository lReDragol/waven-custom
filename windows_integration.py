"""Windows association registration and verified, user-guided default selection."""
import os
import sys
from pathlib import Path
from urllib.parse import quote
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QMessageBox
from app_paths import application_directory,is_portable
from ui_style import DIALOG_STYLE

AUDIO_TYPES=('.mp3','.wav','.flac','.m4a','.aac','.ogg','.opus','.wma','.aiff')

def app_identity(executable=None,portable=None):
    portable=is_portable() if portable is None else portable
    return {'name':'WAVEN Custom Portable' if portable else 'WAVEN Custom',
            'progid':'WavenCustom.Portable.Audio' if portable else 'WavenCustom.Audio',
            'product':'WavenCustomPortable' if portable else 'WavenCustom',
            'executable':str(Path(executable or application_directory()/'Waven Custom.exe').resolve()),
            'portable':portable}

def registration_entries(identity):
    """Declarative HKCU entries; no default replacement or UserChoice writes."""
    name=identity['name'];progid=identity['progid'];exe=identity['executable']
    base='Software\\Classes\\'+progid
    capabilities='Software\\'+identity['product']+'\\Capabilities'
    icon='"'+exe+'",0';command='"'+exe+'" "%1"'
    entries=[(base,'','Аудиофайл WAVEN Custom'),(base,'FriendlyTypeName','Аудиофайл WAVEN Custom'),
             (base+'\\DefaultIcon','',icon),(base+'\\shell\\open\\command','',command),
             (base+'\\Application','ApplicationName',name),
             (base+'\\Application','ApplicationDescription','Музыка, плейлисты и визуализации'),
             (base+'\\Application','ApplicationIcon',icon),
             (capabilities,'ApplicationName',name),
             (capabilities,'ApplicationDescription','Музыка, плейлисты и визуализации'),
             (capabilities,'ApplicationIcon',icon),
             ('Software\\RegisteredApplications',name,capabilities)]
    for extension in AUDIO_TYPES:
        entries.extend([(capabilities+'\\FileAssociations',extension,progid),
                        ('Software\\Classes\\'+extension+'\\OpenWithProgids',progid,'')])
    # Portable registration must not overwrite the installed copy's executable registration.
    if not identity['portable']:
        application='Software\\Classes\\Applications\\Waven Custom.exe'
        entries.extend([(application,'FriendlyAppName',name),(application+'\\DefaultIcon','',icon),
                        (application+'\\shell\\open\\command','',command),
                        ('Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\Waven Custom.exe','',exe)])
        entries.extend((application+'\\SupportedTypes',ext,'') for ext in AUDIO_TYPES)
    return entries

def register_application(identity=None):
    import winreg
    import ctypes
    if identity is None and not getattr(sys,'frozen',False):
        raise OSError('Для регистрации используйте собранный EXE или установщик.')
    identity=identity or app_identity()
    if not Path(identity['executable']).is_file():raise OSError('Файл плеера не найден: '+identity['executable'])
    for path,value,data in registration_entries(identity):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,path) as key:
            winreg.SetValueEx(key,value,0,winreg.REG_SZ,data)
    ctypes.windll.shell32.SHChangeNotify(0x08000000,0,None,None)
    return identity['name']

def association_string(kind,extension='.mp3'):
    """Query the effective Shell handler, not merely the registered ProgID."""
    import ctypes
    from ctypes import wintypes
    query=ctypes.WinDLL('Shlwapi').AssocQueryStringW
    query.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,
                    wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    query.restype=ctypes.c_long
    length=wintypes.DWORD(0)
    query(0,kind,extension,'open',None,ctypes.byref(length))
    if not 0<length.value<65536:return ''
    buffer=ctypes.create_unicode_buffer(length.value)
    return buffer.value if query(0,kind,extension,'open',buffer,ctypes.byref(length))==0 else ''

def default_status(identity):
    try:
        executable=association_string(2)  # ASSOCSTR_EXECUTABLE
        name=association_string(4)  # ASSOCSTR_FRIENDLYAPPNAME
        expected=os.path.normcase(os.path.abspath(identity['executable']))
        matches=bool(executable) and os.path.normcase(os.path.abspath(executable))==expected
        return {'is_default':matches,'application':name or (Path(executable).name if executable else 'Не определено Windows'),
                'executable':executable,'error':''}
    except (OSError,AttributeError) as exc:
        return {'is_default':False,'application':'Не удалось проверить','executable':'','error':str(exc)}

def default_apps_url(name,build=None):
    build=sys.getwindowsversion().build if build is None else build
    if build>=22000:return 'ms-settings:defaultapps?registeredAppUser='+quote(name)
    return 'ms-settings:defaultapps'

class DefaultAppDialog(QDialog):
    def __init__(self,identity,parent=None,status_reader=default_status,url_opener=QDesktopServices.openUrl):
        super().__init__(parent)
        self.identity=identity;self.status_reader=status_reader;self.url_opener=url_opener
        self.setWindowTitle('MP3 по умолчанию — WAVEN Custom');self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(530);self.resize(590,445)
        root=QVBoxLayout(self);root.setContentsMargins(26,24,26,22);root.setSpacing(16)
        title=QLabel('Открывать MP3 в WAVEN Custom');title.setStyleSheet('font-size:21px;font-weight:600;color:#edf5fa');root.addWidget(title)
        self.status=QLabel();self.status.setWordWrap(True);root.addWidget(self.status)
        self.current=QLabel();self.current.setWordWrap(True);self.current.setStyleSheet('color:#a4b6ca');root.addWidget(self.current)
        name=identity['name']
        if sys.getwindowsversion().build>=22000:
            steps=f'1. Нажмите «Открыть настройки Windows».\n2. Найдите .mp3 на странице {name}.\n3. Выберите {name} и подтвердите выбор.'
        else:
            steps=f'1. Нажмите «Открыть настройки Windows».\n2. В разделе «Музыкальный проигрыватель» нажмите текущий плеер.\n3. Выберите {name} с бирюзовой иконкой.'
        self.instructions=QLabel(steps);self.instructions.setWordWrap(True)
        self.instructions.setStyleSheet('background:#1b2735;padding:16px;border-radius:7px;color:#dce8f4;');root.addWidget(self.instructions)
        note=QLabel('Регистрация в списке приложений уже выполнена. Галочка установщика сама по себе не меняет выбранный плеер. Это окно автоматически проверит результат.')
        note.setWordWrap(True);note.setStyleSheet('color:#8fa4bb');root.addWidget(note)
        self.path_label=QLabel('Ваш плеер: '+identity['executable']);self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet('color:#71869e;font-size:10px');root.addWidget(self.path_label)
        root.addStretch()
        actions=QHBoxLayout()
        self.open_button=QPushButton('Открыть настройки Windows');self.open_button.setObjectName('primary')
        self.open_button.clicked.connect(self.open_settings);actions.addWidget(self.open_button)
        self.check_button=QPushButton('Проверить');self.check_button.clicked.connect(self.refresh_status);actions.addWidget(self.check_button)
        self.close_button=QPushButton('Позже');self.close_button.clicked.connect(self.accept);actions.addWidget(self.close_button);root.addLayout(actions)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh_status);self.timer.start(1200)
        self.finished.connect(self.timer.stop);self.refresh_status()

    def refresh_status(self):
        result=self.status_reader(self.identity)
        if result['is_default']:
            self.status.setText('✓ Готово: MP3 открываются в этой версии WAVEN Custom')
            self.status.setStyleSheet('color:#6ae0bc;font-weight:600;font-size:14px;')
            self.close_button.setText('Готово');self.open_button.setEnabled(False)
        else:
            self.status.setText('Нужно выбрать плеер в Windows' if not result['error'] else 'Статус MP3 пока не подтверждён')
            self.status.setStyleSheet('color:#f0c887;font-weight:600;font-size:14px;')
            self.close_button.setText('Позже');self.open_button.setEnabled(True)
        self.current.setText('Сейчас для MP3: '+result['application'])
        self.current.setToolTip(result['error'] or result['executable'])

    def open_settings(self):
        if not self.url_opener(QUrl(default_apps_url(self.identity['name']))):
            QMessageBox.warning(self,'Не удалось открыть параметры','Откройте Параметры → Приложения → Приложения по умолчанию.')

def choose_default(parent=None,confirm=True):
    if sys.platform!='win32':return
    if confirm and QMessageBox.question(parent,'Плеер по умолчанию',
            'Добавить WAVEN Custom в список аудиоплееров Windows и настроить открытие MP3?')!=QMessageBox.Yes:return
    try:
        identity=app_identity();register_application()
        DefaultAppDialog(identity,parent).exec()
    except OSError as exc:QMessageBox.warning(parent,'Приложение по умолчанию',str(exc))
