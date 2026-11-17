import ctypes
from ctypes import wintypes
import time
import uuid

combase = ctypes.WinDLL("combase.dll")

HRESULT = ctypes.c_long
HSTRING = ctypes.c_void_p
RO_INIT_MULTITHREADED = 1
RPC_E_CHANGED_MODE = -2147417850  # 0x80010106
_TICKS_PER_SECOND = 10_000_000


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    @classmethod
    def from_uuid(cls, u: uuid.UUID) -> "_GUID":
        g = cls()
        g.Data1, g.Data2, g.Data3 = u.fields[:3]
        for i in range(8):
            g.Data4[i] = u.bytes[8 + i]
        return g


class _TimeSpan(ctypes.Structure):
    _fields_ = [("Duration", ctypes.c_int64)]


_IID_IAsyncInfo = _GUID.from_uuid(uuid.UUID("00000036-0000-0000-C000-000000000046"))
_IID_SessionManagerStatics = _GUID.from_uuid(uuid.UUID("2050C4EE-11A0-57DE-AED7-C97C70338245"))

# Use c_void_p for all out-pointer parameters passed via ctypes.byref()
combase.RoInitialize.argtypes = [ctypes.c_int]
combase.RoInitialize.restype = HRESULT

combase.RoUninitialize.argtypes = []
combase.RoUninitialize.restype = None

combase.WindowsCreateString.argtypes = [wintypes.LPCWSTR, wintypes.UINT, ctypes.c_void_p]
combase.WindowsCreateString.restype = HRESULT

combase.WindowsDeleteString.argtypes = [HSTRING]
combase.WindowsDeleteString.restype = HRESULT

combase.WindowsGetStringRawBuffer.argtypes = [HSTRING, ctypes.c_void_p]
combase.WindowsGetStringRawBuffer.restype = wintypes.LPCWSTR

combase.RoGetActivationFactory.argtypes = [HSTRING, ctypes.c_void_p, ctypes.c_void_p]
combase.RoGetActivationFactory.restype = HRESULT


class MediaWatcher:
    """Zero-dependency WinRT wrapper for reading Windows 10/11 active media metadata and timeline. Written by Gemini, checked by me"""

    _STATUS_MAP = {
        0: "Closed",
        1: "Opened",
        2: "Changing",
        3: "Stopped",
        4: "Playing",
        5: "Paused",
    }

    def __init__(self):
        self._owns_com = False
        self._closed = False
        self._manager_ptr = ctypes.c_void_p()

        hr = combase.RoInitialize(RO_INIT_MULTITHREADED)
        if hr >= 0:
            self._owns_com = True
        elif hr != RPC_E_CHANGED_MODE:
            raise OSError(f"RoInitialize failed with HRESULT 0x{hr & 0xFFFFFFFF:08X}")

        self._manager_ptr = self._request_session_manager()

    @staticmethod
    def _check_hr(hr: int, context: str = ""):
        if hr < 0:
            raise OSError(f"HRESULT 0x{hr & 0xFFFFFFFF:08X} failed: {context}")

    @staticmethod
    def _get_vtable_func(ptr: ctypes.c_void_p, index: int, restype, *argtypes):
        if not ptr or not ptr.value:
            raise ValueError(f"Attempted to invoke vtable slot {index} on a NULL COM pointer.")
        vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        func_type = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        return func_type(vtable[index])

    @classmethod
    def _release_com(cls, ptr: ctypes.c_void_p):
        if ptr and ptr.value:
            release = cls._get_vtable_func(ptr, 2, wintypes.ULONG)
            release(ptr)
            ptr.value = None

    @staticmethod
    def _hstring_to_str(hstr: HSTRING) -> str:
        if not hstr or not hstr.value:
            return ""
        length = wintypes.UINT(0)
        buf = combase.WindowsGetStringRawBuffer(hstr, ctypes.byref(length))
        text = buf[: length.value] if buf else ""
        combase.WindowsDeleteString(hstr)
        return text

    @classmethod
    def _await_async_op(cls, async_op_ptr: ctypes.c_void_p) -> ctypes.c_void_p:
        if not async_op_ptr or not async_op_ptr.value:
            raise ValueError("IAsyncOperation pointer is NULL.")

        query_interface = cls._get_vtable_func(async_op_ptr, 0, HRESULT, ctypes.c_void_p, ctypes.c_void_p)
        async_info_ptr = ctypes.c_void_p()
        cls._check_hr(
            query_interface(async_op_ptr, ctypes.byref(_IID_IAsyncInfo), ctypes.byref(async_info_ptr)),
            "QI IAsyncInfo",
        )

        try:
            get_status = cls._get_vtable_func(async_info_ptr, 7, HRESULT, ctypes.c_void_p)
            status = ctypes.c_int(0)

            while True:
                cls._check_hr(get_status(async_info_ptr, ctypes.byref(status)), "IAsyncInfo.get_Status")
                if status.value != 0:
                    break
                time.sleep(0.005)

            if status.value != 1:
                raise RuntimeError(f"WinRT async operation failed with status {status.value}")

            get_results = cls._get_vtable_func(async_op_ptr, 8, HRESULT, ctypes.c_void_p)
            result_ptr = ctypes.c_void_p()
            cls._check_hr(get_results(async_op_ptr, ctypes.byref(result_ptr)), "IAsyncOperation.GetResults")
            return result_ptr
        finally:
            cls._release_com(async_info_ptr)

    def _request_session_manager(self) -> ctypes.c_void_p:
        class_name = "Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager"
        hstr_class = HSTRING()
        self._check_hr(
            combase.WindowsCreateString(class_name, len(class_name), ctypes.byref(hstr_class)),
            "WindowsCreateString",
        )

        factory_ptr = ctypes.c_void_p()
        op_manager_ptr = ctypes.c_void_p()

        try:
            self._check_hr(
                combase.RoGetActivationFactory(
                    hstr_class, ctypes.byref(_IID_SessionManagerStatics), ctypes.byref(factory_ptr)
                ),
                "RoGetActivationFactory",
            )
            request_async = self._get_vtable_func(factory_ptr, 6, HRESULT, ctypes.c_void_p)
            self._check_hr(request_async(factory_ptr, ctypes.byref(op_manager_ptr)), "RequestAsync")
            return self._await_async_op(op_manager_ptr)
        finally:
            self._release_com(op_manager_ptr)
            self._release_com(factory_ptr)
            if hstr_class.value:
                combase.WindowsDeleteString(hstr_class)

    def _get_current_session(self) -> ctypes.c_void_p:
        session_ptr = ctypes.c_void_p()
        get_current = self._get_vtable_func(self._manager_ptr, 6, HRESULT, ctypes.c_void_p)
        self._check_hr(get_current(self._manager_ptr, ctypes.byref(session_ptr)), "GetCurrentSession")
        return session_ptr

    def _read_timeline_from_session(self, session_ptr: ctypes.c_void_p) -> dict[str, float]:
        """Reads StartTime, EndTime, and Position (in seconds) safely."""
        timeline_ptr = ctypes.c_void_p()
        try:
            get_timeline = self._get_vtable_func(session_ptr, 8, HRESULT, ctypes.c_void_p)
            self._check_hr(get_timeline(session_ptr, ctypes.byref(timeline_ptr)), "GetTimelineProperties")

            if not timeline_ptr.value:
                return {"position": 0.0, "duration": 0.0, "start_time": 0.0, "end_time": 0.0}

            get_start = self._get_vtable_func(timeline_ptr, 6, HRESULT, ctypes.c_void_p)
            get_end = self._get_vtable_func(timeline_ptr, 7, HRESULT, ctypes.c_void_p)
            get_pos = self._get_vtable_func(timeline_ptr, 10, HRESULT, ctypes.c_void_p)

            start_ts = _TimeSpan()
            end_ts = _TimeSpan()
            pos_ts = _TimeSpan()

            self._check_hr(get_start(timeline_ptr, ctypes.byref(start_ts)), "get_StartTime")
            self._check_hr(get_end(timeline_ptr, ctypes.byref(end_ts)), "get_EndTime")
            self._check_hr(get_pos(timeline_ptr, ctypes.byref(pos_ts)), "get_Position")

            start_sec = start_ts.Duration / _TICKS_PER_SECOND
            end_sec = end_ts.Duration / _TICKS_PER_SECOND
            pos_sec = pos_ts.Duration / _TICKS_PER_SECOND
            duration_sec = max(0.0, end_sec - start_sec)

            return {
                "position": pos_sec,
                "duration": duration_sec,
                "start_time": start_sec,
                "end_time": end_sec,
            }
        finally:
            self._release_com(timeline_ptr)

    def get_media_info(self) -> dict | None:
        """Returns title, artist, album, status, position (sec), and duration (sec), or None."""
        session_ptr = self._get_current_session()
        if not session_ptr.value:
            return None

        op_props_ptr = ctypes.c_void_p()
        props_ptr = ctypes.c_void_p()
        playback_info_ptr = ctypes.c_void_p()

        try:
            timeline = self._read_timeline_from_session(session_ptr)
            status_str = "Unknown"
            get_playback_info = self._get_vtable_func(session_ptr, 9, HRESULT, ctypes.c_void_p)
            self._check_hr(get_playback_info(session_ptr, ctypes.byref(playback_info_ptr)), "GetPlaybackInfo")

            if playback_info_ptr.value:
                get_status = self._get_vtable_func(playback_info_ptr, 7, HRESULT, ctypes.c_void_p)
                status_code = ctypes.c_int(0)
                self._check_hr(get_status(playback_info_ptr, ctypes.byref(status_code)), "get_PlaybackStatus")
                status_str = self._STATUS_MAP.get(status_code.value, "Unknown")

            try_get_props = self._get_vtable_func(session_ptr, 7, HRESULT, ctypes.c_void_p)
            self._check_hr(try_get_props(session_ptr, ctypes.byref(op_props_ptr)), "TryGetMediaPropertiesAsync")
            props_ptr = self._await_async_op(op_props_ptr)

            if not props_ptr.value:
                return None

            get_title = self._get_vtable_func(props_ptr, 6, HRESULT, ctypes.c_void_p)
            get_artist = self._get_vtable_func(props_ptr, 9, HRESULT, ctypes.c_void_p)
            get_album = self._get_vtable_func(props_ptr, 10, HRESULT, ctypes.c_void_p)

            h_title, h_artist, h_album = HSTRING(), HSTRING(), HSTRING()
            
            self._check_hr(get_title(props_ptr, ctypes.byref(h_title)), "get_Title")
            self._check_hr(get_artist(props_ptr, ctypes.byref(h_artist)), "get_Artist")
            self._check_hr(get_album(props_ptr, ctypes.byref(h_album)), "get_AlbumTitle")
            return {
            "title": self._hstring_to_str(h_title),
            "artist": self._hstring_to_str(h_artist),
            "album": self._hstring_to_str(h_album),
            "status": status_str,
            "position": timeline["position"],
            "duration": timeline["duration"],
            }
        finally:
            self._release_com(props_ptr)
            self._release_com(op_props_ptr)
            self._release_com(playback_info_ptr)
            self._release_com(session_ptr)
            
    def close(self):
        """Releases the cached WinRT session manager and uninitializes COM if owned."""
        if not self._closed:
            self._release_com(self._manager_ptr)
        if self._owns_com:
            combase.RoUninitialize()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()