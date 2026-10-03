"""Graceful installer shutdown, scoped to the exact executable being updated."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import time


class ProcessEntry(ctypes.Structure):
    _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
              ('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),
              ('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
              ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),
              ('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]


def prepare_update(executable,timeout=15):
    """Ask visible windows to close, then wait for both app and onefile launcher.

    Never terminates processes or closes other installations with the same name.
    A denied request, unresponsive app, or canceled close blocks the update.
    """
    target=Path(executable).resolve()
    if not Path(executable).is_absolute() or target.name.casefold()!='waven custom.exe':
        raise ValueError('Expected the absolute path to Waven Custom.exe')
    expected=os.path.normcase(str(target))
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user=ctypes.WinDLL('user32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    for name in ('Process32FirstW','Process32NextW'):
        function=getattr(kernel,name)
        function.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)]
        function.restype=wintypes.BOOL
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.WaitForSingleObject.restype=wintypes.DWORD
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM];user.EnumWindows.restype=wintypes.BOOL
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype=wintypes.DWORD
    user.IsWindowVisible.argtypes=[wintypes.HWND];user.IsWindowVisible.restype=wintypes.BOOL
    user.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.GetClassNameW.restype=ctypes.c_int
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.PostMessageW.restype=wintypes.BOOL

    handles={};requested=set();failures=[]

    def discover_processes():
        snapshot=kernel.CreateToolhelp32Snapshot(2,0)  # TH32CS_SNAPPROCESS
        if snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        try:
            entry=ProcessEntry();entry.dwSize=ctypes.sizeof(entry)
            more=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
            if not more:raise ctypes.WinError(ctypes.get_last_error())
            while more:
                pid=entry.th32ProcessID
                if entry.szExeFile.casefold()==target.name.casefold() and pid!=os.getpid() and pid not in handles:
                    handle=kernel.OpenProcess(0x1000|0x100000,False,pid)  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
                    if not handle:
                        error=ctypes.get_last_error()
                        if error!=87:raise ctypes.WinError(error)  # 87: process already exited
                    else:
                        path=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(path))
                        if not kernel.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(length)):
                            error=ctypes.get_last_error();kernel.CloseHandle(handle)
                            raise ctypes.WinError(error)
                        if os.path.normcase(str(Path(path.value).resolve()))==expected:
                            handles[pid]=handle
                        else:kernel.CloseHandle(handle)
                more=kernel.Process32NextW(snapshot,ctypes.byref(entry))
        finally:kernel.CloseHandle(snapshot)

    try:
        @callback_type
        def close_window(hwnd,unused):
            pid=wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value not in handles or (pid.value,int(hwnd)) in requested:return True
            class_name=ctypes.create_unicode_buffer(256)
            user.GetClassNameW(hwnd,class_name,len(class_name))
            qt_window=class_name.value.startswith('Qt') and 'QWindow' in class_name.value
            if user.IsWindowVisible(hwnd) or qt_window:
                if not user.PostMessageW(hwnd,0x0010,0,0):  # WM_CLOSE, not TerminateProcess
                    failures.append(ctypes.get_last_error())
                else:requested.add((pid.value,int(hwnd)))
            return True

        deadline=time.monotonic()+timeout
        while True:
            # A onefile launcher may not have created its Qt child/window yet.
            discover_processes()
            pending=[pid for pid,handle in handles.items() if kernel.WaitForSingleObject(handle,0)!=0]
            if not pending:return {'closed':list(handles),'remaining':[]}
            if not user.EnumWindows(close_window,0):raise ctypes.WinError(ctypes.get_last_error())
            if failures:raise ctypes.WinError(failures[0])
            if time.monotonic()>=deadline:return {'closed':[pid for pid in handles if pid not in pending],'remaining':pending}
            time.sleep(.1)
    finally:
        for handle in handles.values():kernel.CloseHandle(handle)


def updater_main(arguments):
    if len(arguments)!=2 or arguments[0]!='--prepare-update':return 2
    try:
        result=prepare_update(arguments[1])
        return 10 if result['remaining'] else 0
    except (OSError,ValueError):
        return 11


if __name__=='__main__':
    raise SystemExit(updater_main(sys.argv[1:]))
