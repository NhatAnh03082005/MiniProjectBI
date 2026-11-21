"""Optional, user-scoped Gemini key storage in Windows Credential Manager.

Only this application's fixed generic credential is accessed. No file or
environment-variable fallback is used; callers must never log the returned key.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import re

_TARGET = "MiniProjectBI/GeminiAPI"
_GENERIC = 1
_LOCAL_MACHINE = 2  # Same Windows user and computer, across logon sessions.
_NOT_FOUND = 1168
_KEY = re.compile(r"[A-Za-z0-9._-]{20,512}\Z")


class CredentialStoreError(RuntimeError):
    """Safe user-facing failure, without native exception text or credentials."""


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def is_supported() -> bool:
    return os.name == "nt" and hasattr(ctypes, "WinDLL")


def _api():
    if not is_supported():
        raise CredentialStoreError("Ghi nhớ key trên máy chỉ hỗ trợ Windows Credential Manager.")
    try:
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(_Credential))]
        api.CredReadW.restype = wintypes.BOOL
        api.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        api.CredDeleteW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        return api
    except (OSError, AttributeError):
        raise CredentialStoreError("Không mở được Windows Credential Manager; vẫn có thể nhập key cho phiên này.") from None


def _valid_key(value) -> bool:
    return isinstance(value, str) and _KEY.fullmatch(value) is not None


def load_key() -> str | None:
    if not is_supported():
        return None
    api = _api()
    pointer = ctypes.POINTER(_Credential)()
    if not api.CredReadW(_TARGET, _GENERIC, 0, ctypes.byref(pointer)):
        if ctypes.get_last_error() == _NOT_FOUND:
            return None
        raise CredentialStoreError("Không đọc được key đã lưu; hãy nhập key cho phiên này.")
    try:
        item = pointer.contents
        if item.Type != _GENERIC or item.TargetName != _TARGET \
                or not 20 <= item.CredentialBlobSize <= 512 or not item.CredentialBlob:
            raise CredentialStoreError("Key đã lưu không hợp lệ; hãy nhập và lưu lại key mới.")
        value = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize).decode("ascii")
        if not _valid_key(value):
            raise CredentialStoreError("Key đã lưu không hợp lệ; hãy nhập và lưu lại key mới.")
        return value
    except (ValueError, UnicodeError):
        raise CredentialStoreError("Key đã lưu không đọc được; hãy nhập và lưu lại key mới.") from None
    finally:
        api.CredFree(pointer)


def save_key(key: str) -> None:
    if not _valid_key(key):
        raise CredentialStoreError("Key chưa đúng định dạng để lưu; hãy kiểm tra ô Gemini API key.")
    api = _api()
    blob = ctypes.create_string_buffer(key.encode("ascii"))
    item = _Credential()
    item.Type, item.Persist = _GENERIC, _LOCAL_MACHINE
    item.TargetName, item.UserName = _TARGET, "Gemini API"
    item.Comment = "MiniProjectBI: Gemini key for the current Windows user"
    item.CredentialBlobSize = len(key)
    item.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(wintypes.BYTE))
    try:
        if not api.CredWriteW(ctypes.byref(item), 0):
            raise CredentialStoreError("Không lưu được key vào Windows Credential Manager; key vẫn dùng được trong phiên này.")
    finally:
        ctypes.memset(blob, 0, ctypes.sizeof(blob))


def delete_key() -> None:
    api = _api()
    if not api.CredDeleteW(_TARGET, _GENERIC, 0) and ctypes.get_last_error() != _NOT_FOUND:
        raise CredentialStoreError("Không xóa được key đã lưu trong Windows Credential Manager.")
