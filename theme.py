"""Editable layout derived from the user's reference, not decompiled application code."""
from __future__ import annotations
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_THEME = {
    'name': 'WAVEN · оригинальная компоновка', 'width': 800, 'height': 250,
    'colors': {'background_top': '#0a0c0f', 'background_bottom': '#051e2d',
               'border': '#174655', 'text': '#ffffff', 'artist': '#b4dce6',
               'album': '#6496a0', 'accent': '#00ffd5', 'button': '#6496a0',
               'stop': '#505a64', 'small_button': '#324650', 'wave': '#ffda47',
               'wave_edge': '#ffeb87', 'meter': '#cbff47', 'track': '#0f1923',
               'play_background': '#56e2c6', 'play_text': '#052531'},
    'font_size': 10,
    'elements': {
        'cover': [20,20,210,210], 'logo': [365,9,70,22],
        'title': [252,29,240,20], 'artist': [252,54,240,17], 'album': [252,78,240,17],
        'visualizer': [500,25,280,60], 'format': [650,30,124,15],
        'meter_left': [250,115,260,4], 'meter_right': [520,115,260,4],
        'progress': [250,135,530,8], 'time': [252,146,300,12],
        'previous': [250,170,60,40], 'play': [330,160,70,50],
        'next': [420,170,60,40], 'stop': [500,170,60,40],
        'volume': [630,185,150,8], 'playlist': [250,220,40,20],
        'info': [300,220,40,20], 'visual': [350,220,40,20],
        'skin': [400,220,40,20], 'options': [450,220,40,20],
        'exit': [780,0,20,20]
    }
}

LABELS = {'cover':'Обложка', 'logo':'Логотип', 'title':'Название трека', 'artist':'Исполнитель',
          'album':'Альбом', 'visualizer':'Визуализация', 'format':'Формат аудио',
          'meter_left':'Левый канал', 'meter_right':'Правый канал', 'progress':'Прогресс',
          'time':'Время', 'previous':'Предыдущая', 'play':'Воспроизведение', 'next':'Следующая',
          'stop':'Стоп', 'volume':'Громкость', 'playlist':'Плейлисты', 'info':'Информация',
          'visual':'Режим визуализации', 'skin':'Редактор темы', 'options':'Настройки', 'exit':'Закрыть'}
COLOR_LABELS = {'background_top':'Фон сверху', 'background_bottom':'Фон снизу', 'border':'Рамка',
                'text':'Основной текст', 'artist':'Исполнитель', 'album':'Альбом', 'accent':'Акцент / прогресс',
                'button':'Кнопки перехода', 'stop':'Кнопка STOP', 'small_button':'Малые кнопки',
                'wave':'Переливы: начальный цвет', 'wave_edge':'Переливы: контур', 'meter':'Индикаторы: край градиента',
                'track':'Дорожки ползунков','play_background':'Кнопка PLAY','play_text':'Надпись PLAY'}


def readable_text_color(background,foreground):
    def luminance(color):
        values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
    def contrast(color):
        light,dark=sorted([luminance(background),luminance(color)],reverse=True)
        return (light+.05)/(dark+.05)
    return foreground if contrast(foreground)>=4.5 else max(('#051b22','#ffffff','#000000'),key=contrast)


def validated_theme(value):
    theme = copy.deepcopy(DEFAULT_THEME)
    if not isinstance(value, dict):
        return theme
    theme['name'] = str(value.get('name', theme['name']))[:120]
    theme['width'] = max(400, min(2400, int(value.get('width', 800))))
    theme['height'] = max(180, min(1600, int(value.get('height', 250))))
    theme['font_size'] = max(7, min(28, int(value.get('font_size', 10))))
    import re
    for key, color in value.get('colors', {}).items():
        if key in theme['colors'] and isinstance(color, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            theme['colors'][key] = color
    for key, rect in value.get('elements', {}).items():
        if key in theme['elements'] and isinstance(rect, list) and len(rect) == 4:
            x,y,w,h = [int(v) for v in rect]
            w = min(max(4,w), theme['width'])
            h = min(max(4,h), theme['height'])
            theme['elements'][key] = [max(0,min(x,theme['width']-w)),max(0,min(y,theme['height']-h)),w,h]
    return theme


def import_theme(path):
    path = Path(path)
    if path.suffix.lower() != '.xml':
        return validated_theme(json.loads(path.read_text(encoding='utf-8-sig')))
    # ElementTree does not resolve external entities.
    root = ET.fromstring(path.read_text(encoding='utf-8-sig'))
    if root.tag != 'WavenUIConfig':
        raise ValueError('Поддерживается XML WavenUIConfig. Графические WavenSkin — другой формат.')
    theme = copy.deepcopy(DEFAULT_THEME)
    theme['name'] = path.stem
    def color(el, keys, fallback):
        try:
            values = [max(0,min(255,int(el.get(k)))) for k in keys]
            return '#' + ''.join(f'{v:02x}' for v in values)
        except (TypeError, ValueError):
            return fallback
    mapping = {'Logo':'logo', 'AlbumArt':'cover', 'TextTitle':'title', 'TextArtist':'artist',
               'TextAlbum':'album', 'TextFormat':'format', 'Visualizer':'visualizer',
               'VUMeterLeft':'meter_left', 'VUMeterRight':'meter_right', 'ProgressBar':'progress',
               'VolumeSlider':'volume', 'TimeText':'time'}
    buttons = {'Prev':'previous','Next':'next','Play':'play','Stop':'stop','Playlist':'playlist',
               'Lyric':'info','Visual':'visual','Skin':'skin','DSP':'options','Exit':'exit'}
    for el in root:
        if el.tag == 'Design':
            theme['width'],theme['height'] = int(el.get('W',800)),int(el.get('H',250))
            theme['colors']['background_top'] = color(el,('R1','G1','B1'),'#0a0c0f')
            theme['colors']['background_bottom'] = color(el,('R2','G2','B2'),'#051e2d')
        key = buttons.get(el.get('Name')) if el.tag == 'Button' else mapping.get(el.tag)
        if key:
            old = theme['elements'][key]
            theme['elements'][key] = [int(el.get('X',old[0])),int(el.get('Y',old[1])),
                                      int(el.get('W',el.get('Size',old[2]))),int(el.get('H',el.get('Size',old[3])))]
            color_key = {'title':'text','artist':'artist','album':'album','play':'play_background',
                         'stop':'stop','previous':'button','playlist':'small_button'}.get(key)
            if color_key:
                theme['colors'][color_key] = color(el,('R','G','B'),theme['colors'][color_key])
    # The reference WAVEN XML calls its left button Next and its right one Prev.
    # Preserve the visual order expected of previous / next when importing that layout.
    if theme['elements']['previous'][0] > theme['elements']['next'][0]:
        theme['elements']['previous'],theme['elements']['next'] = theme['elements']['next'],theme['elements']['previous']
    return validated_theme(theme)
