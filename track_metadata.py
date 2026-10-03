"""Read-only audio metadata, off the UI thread. Never modifies music files."""
from pathlib import Path
import mutagen
from PySide6.QtCore import QObject,QRunnable,QThreadPool,Signal,Slot


def read_metadata(path):
    result={'title':Path(path).stem,'artist':'Без исполнителя','album':'','duration':0,'missing':False}
    try:
        result['missing']=not Path(path).is_file()
        audio=mutagen.File(path,easy=True)
        if audio is None:
            return result
        def tag(name):
            aliases={'title':('title','TIT2','Title'),'artist':('artist','TPE1','Author'),
                     'albumartist':('albumartist','TPE2','WM/AlbumArtist'),'album':('album','TALB','WM/AlbumTitle')}
            value=next((audio.get(k) for k in aliases[name] if audio.get(k)),[])
            value=getattr(value,'text',value)
            return ' / '.join(str(v) for v in value) if isinstance(value,(tuple,list)) else str(value or '')
        result.update(title=tag('title') or result['title'],artist=tag('artist') or tag('albumartist') or result['artist'],
                      album=tag('album'),duration=round(getattr(audio.info,'length',0)))
    except (OSError,ValueError,mutagen.MutagenError):
        pass
    return result


class ScanSignals(QObject):
    result=Signal(str,dict)


class Scan(QRunnable):
    def __init__(self,path,signals):
        super().__init__();self.path=path;self.signals=signals

    @Slot()
    def run(self):
        try:
            data=read_metadata(self.path)
        except Exception:
            data={'title':Path(self.path).stem,'artist':'Без исполнителя','album':'','duration':0,'missing':False}
        self.signals.result.emit(self.path,data)


class MetadataCache(QObject):
    ready=Signal(str,dict)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.cache={};self.pending=set()
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(3)
        self.signals=ScanSignals(self)
        self.signals.result.connect(self.received)

    def request(self,path):
        if path in self.cache:
            return self.cache[path]
        if path not in self.pending:
            self.pending.add(path)
            self.pool.start(Scan(path,self.signals))
        return {'title':Path(path).stem,'artist':'Чтение тегов…','album':'','duration':0,'missing':False}

    @Slot(str,dict)
    def received(self,path,data):
        self.pending.discard(path);self.cache[path]=data;self.ready.emit(path,data)
