"""Opt-in Windows registration. Never writes the protected UserChoice key."""
import sys
from urllib.parse import quote
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox
from app_paths import application_directory,is_portable

def register_application():
    import winreg
    import ctypes
    if not getattr(sys,'frozen',False):
        raise OSError('Для регистрации используйте собранный EXE или установщик.')
    portable=is_portable()
    name='WAVEN Custom Portable' if portable else 'WAVEN Custom'
    progid='WavenCustom.Portable.Audio' if portable else 'WavenCustom.Audio'
    product='WavenCustomPortable' if portable else 'WavenCustom'
    exe=str(application_directory()/'Waven Custom.exe')
    def write(path,value,data):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,path) as key:winreg.SetValueEx(key,value,0,winreg.REG_SZ,data)
    base='Software\\Classes\\'+progid
    write(base,'','Аудиофайл WAVEN Custom');write(base,'FriendlyTypeName','Аудиофайл WAVEN Custom')
    write(base+'\\DefaultIcon','','"'+exe+'",0')
    write(base+'\\shell\\open\\command','','"'+exe+'" "%1"')
    capabilities='Software\\'+product+'\\Capabilities'
    write(capabilities,'ApplicationName',name)
    write(capabilities,'ApplicationDescription','Музыка, плейлисты и визуализации')
    write(capabilities,'ApplicationIcon','"'+exe+'",0')
    for extension in ('.mp3','.wav','.flac','.m4a','.aac','.ogg','.opus','.wma','.aiff'):
        write(capabilities+'\\FileAssociations',extension,progid)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,'Software\\Classes\\'+extension+'\\OpenWithProgids') as key:
            winreg.SetValueEx(key,progid,0,winreg.REG_NONE,b'')
    write('Software\\RegisteredApplications',name,capabilities)
    ctypes.windll.shell32.SHChangeNotify(0x08000000,0,None,None)
    return name

def default_apps_url(name):
    if sys.getwindowsversion().build>=22000:
        return 'ms-settings:defaultapps?registeredAppUser='+quote(name)
    return 'ms-settings:defaultapps'

def choose_default(parent=None,confirm=True):
    if sys.platform!='win32':return
    if confirm and QMessageBox.question(parent,'Плеер по умолчанию',
            'Добавить WAVEN Custom в список аудиоплееров Windows?\n\n'
            'Затем в системных параметрах выберите WAVEN Custom для .mp3. '
            'Windows требует вашего подтверждения. Текущая ассоциация не меняется автоматически.')!=QMessageBox.Yes:return
    try:
        name=register_application()
        if not QDesktopServices.openUrl(QUrl(default_apps_url(name))):
            raise OSError('Откройте Параметры → Приложения → Приложения по умолчанию и выберите WAVEN Custom для .mp3.')
    except OSError as exc:QMessageBox.warning(parent,'Приложение по умолчанию',str(exc))
