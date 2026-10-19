"""
Windows DPAPI helpers so the portal password is never stored in plain text.

The encrypted blob can only be decrypted by the same Windows user account on the
same machine, which is exactly the scope the scheduled tasks run under.
"""
import base64
import ctypes
import ctypes.wintypes as wt


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob_bytes(blob: _DATA_BLOB) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


def _call(func_name: str, data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    func = getattr(crypt32, func_name)
    ok = func(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_bytes(blob_out)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def encrypt_secret(plain: str) -> str:
    """Encrypts text with DPAPI and returns a base64 string safe for a config file."""
    if not plain:
        return ""
    return base64.b64encode(_call("CryptProtectData", plain.encode("utf-8"))).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Reverses encrypt_secret. Raises if the blob belongs to another user or machine."""
    if not token:
        return ""
    return _call("CryptUnprotectData", base64.b64decode(token)).decode("utf-8")
