"""Installed and portable profile locations."""
import os
import sys
from pathlib import Path

def application_directory():
    return Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

def is_portable():
    return (application_directory()/'portable.flag').is_file()

def profile_directory():
    override=os.environ.get('WAVEN_CUSTOM_DATA')
    if override:return Path(override)
    if is_portable():return application_directory()/'Data'
    return Path(os.environ.get('APPDATA',str(Path.home())))/'WavenCustom'
