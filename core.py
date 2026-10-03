"""Local queue, playlist and settings storage. No dependency on the original WAVEN."""
from __future__ import annotations

import copy
import json
import os
import random
import re
import tempfile
import uuid
from pathlib import Path

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.aiff', '.aif', '.mp4'}
PLAYLIST_EXTENSIONS = {'.m3u', '.m3u8', '.pls'}


def normalized(path):
    return os.path.normcase(os.path.abspath(os.path.expanduser(str(path))))


def natural_key(path):
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r'(\d+)', Path(path).name)]


def unique_paths(paths):
    seen, result = set(), []
    for path in paths:
        path = os.path.abspath(os.path.expanduser(str(path)))
        key = normalized(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def folder_tracks(folder):
    return [str(p.resolve()) for p in sorted(Path(folder).iterdir(), key=natural_key)
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS]


def read_playlist(path):
    path = Path(path)
    data = path.read_bytes()
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = data.decode('cp1251')
    lines = text.splitlines()
    if path.suffix.lower() == '.pls':
        pairs = []
        for line in lines:
            match = re.match(r'File(\d+)=(.*)', line, re.I)
            if match:
                pairs.append((int(match[1]), match[2]))
        lines = [value for _, value in sorted(pairs)]
    result = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '://' in line:
            continue
        p = Path(line)
        if not p.is_absolute():
            p = path.parent / p
        if p.suffix.lower() in AUDIO_EXTENSIONS:
            result.append(str(p.resolve()))
    return unique_paths(result)


def write_playlist(path, tracks):
    path = Path(path)
    lines = ['#EXTM3U']
    for track in tracks:
        try:
            line = os.path.relpath(track, path.parent)
        except ValueError:
            line = str(track)
        lines.append(line)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')


def open_selection(paths):
    """Opening one song builds its sibling queue and keeps that song selected."""
    paths = [Path(p).expanduser().resolve() for p in paths]
    if len(paths) == 1 and paths[0].is_file() and paths[0].suffix.lower() in AUDIO_EXTENSIONS:
        tracks = folder_tracks(paths[0].parent)
        key = normalized(paths[0])
        index = next((i for i, t in enumerate(tracks) if normalized(t) == key), 0)
        return tracks, index, str(paths[0].parent)
    tracks = []
    for path in paths:
        if path.is_dir():
            tracks.extend(folder_tracks(path))
        elif path.is_file() and path.suffix.lower() in PLAYLIST_EXTENSIONS:
            tracks.extend(read_playlist(path))
        elif path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            tracks.append(str(path))
    tracks = unique_paths(tracks)
    return tracks, 0 if tracks else -1, str(paths[0]) if len(paths) == 1 else 'Выбранные файлы'


class Queue:
    def __init__(self, tracks=None, index=-1):
        self.tracks = list(tracks or [])
        self.index = min(max(index, 0), len(self.tracks) - 1) if self.tracks else -1
        self.history = []

    @property
    def current(self):
        return self.tracks[self.index] if 0 <= self.index < len(self.tracks) else None

    def replace(self, tracks, index=0):
        self.tracks = list(tracks)
        self.index = min(max(index, 0), len(self.tracks) - 1) if self.tracks else -1
        self.history.clear()

    def advance(self, direction=1, repeat=False, shuffle=False, automatic=False):
        if not self.tracks:
            return None
        if shuffle and direction > 0:
            candidates = [i for i, path in enumerate(self.tracks)
                          if i != self.index and Path(path).is_file()]
            if not candidates:
                if repeat and self.current and Path(self.current).is_file():
                    return self.current
                return None
            self.history.append(self.index)
            self.index = random.choice(candidates)
            return self.current
        if shuffle and direction < 0:
            while self.history:
                index = self.history.pop()
                if 0 <= index < len(self.tracks) and Path(self.tracks[index]).is_file():
                    self.index = index
                    return self.current
        start = self.index
        for step in range(1, len(self.tracks) + 1):
            index = start + step * direction
            if not 0 <= index < len(self.tracks):
                if not repeat:
                    return None
                index %= len(self.tracks)
            if Path(self.tracks[index]).is_file():
                self.index = index
                return self.current
        return None


def default_state():
    return {'version': 1, 'playlists': [], 'queue': [], 'index': -1, 'position': 0,
            'volume': 50, 'repeat': 'off', 'shuffle': False, 'source': '',
            'theme': None, 'window_position': None, 'window_scale': 1}


class Store:
    def __init__(self, directory=None):
        from app_paths import profile_directory
        self.directory = Path(directory) if directory is not None else profile_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'library.json'
        self.error = ''
        self.state = default_state()
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict) or not isinstance(data.get('queue', []), list):
                    raise ValueError('Неверный формат библиотеки')
                self.state.update(data)
            except (OSError, ValueError) as exc:
                self.error = f'Библиотека не прочитана: {exc}. Исходный файл сохранён как library.damaged.json.'
                # Preserve unreadable state before a later autosave.
                backup = self.directory / ('library.damaged.' + uuid.uuid4().hex[:8] + '.json')
                import shutil
                shutil.copy2(self.path, backup)
                self.error = f'Библиотека не прочитана: {exc}. Копия: {backup.name}'
        self.state['queue'] = [p for p in self.state.get('queue', []) if isinstance(p, str)]
        playlists = self.state.get('playlists', [])
        self.state['playlists'] = [p for p in playlists if isinstance(p, dict)
                                   and isinstance(p.get('name'), str)
                                   and isinstance(p.get('tracks'), list)] if isinstance(playlists, list) else []
        for playlist in self.state['playlists']:
            playlist.setdefault('id', uuid.uuid4().hex)
            playlist['tracks'] = [p for p in playlist['tracks'] if isinstance(p, str)]

    def save(self):
        fd, tmp = tempfile.mkstemp(prefix='library-', suffix='.tmp', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.state, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def create_playlist(self, name, tracks):
        record = {'id': uuid.uuid4().hex, 'name': name.strip() or 'Новый плейлист',
                  'tracks': unique_paths(tracks)}
        self.state['playlists'].append(record)
        self.save()
        return record

    def playlist(self, identity):
        return next((p for p in self.state['playlists'] if p['id'] == identity), None)

    def snapshot(self):
        return copy.deepcopy(self.state)
