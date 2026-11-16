import ctypes
from ctypes import wintypes

gdiplus = ctypes.WinDLL("gdiplus.dll")

# GDI+ Constants
UnitPixel = 2
SmoothingModeAntiAlias = 4
TextRenderingHintClearTypeGridFit = 5
PixelFormat32bppPARGB = 0x000E200B  # 32-bit Premultiplied BGRA
ImageLockModeRead = 1

FontStyleRegular = 0
FontStyleBold = 1
FontStyleItalic = 2
FontStyleBoldItalic = 3

StringAlignmentNear = 0    # Left / Top
StringAlignmentCenter = 1  # Center
StringAlignmentFar = 2     # Right / Bottom


class _GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", wintypes.UINT),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


class _RectF(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.c_float),
        ("Y", ctypes.c_float),
        ("Width", ctypes.c_float),
        ("Height", ctypes.c_float),
    ]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.c_int),
        ("Y", ctypes.c_int),
        ("Width", ctypes.c_int),
        ("Height", ctypes.c_int),
    ]


class _BitmapData(ctypes.Structure):
    _fields_ = [
        ("Width", wintypes.UINT),
        ("Height", wintypes.UINT),
        ("Stride", ctypes.c_int),
        ("PixelFormat", ctypes.c_int),
        ("Scan0", ctypes.c_void_p),
        ("Reserved", ctypes.POINTER(wintypes.UINT)),
    ]


# Configure GDI+ function prototypes once on module load
gdiplus.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(_GdiplusStartupInput), ctypes.c_void_p]
gdiplus.GdiplusShutdown.argtypes = [ctypes.c_ulong]

gdiplus.GdipCreateBitmapFromScan0.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipGetImageGraphicsContext.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipSetSmoothingMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetTextRenderingHint.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipGraphicsClear.argtypes = [ctypes.c_void_p, wintypes.DWORD]

gdiplus.GdipCreateSolidFill.argtypes = [wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipFillRectangle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]

gdiplus.GdipCreatePen1.argtypes = [wintypes.DWORD, ctypes.c_float, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipDrawRectangle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]

gdiplus.GdipCreateFontFamilyFromName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateFont.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateStringFormat.argtypes = [ctypes.c_int, wintypes.LANGID, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipSetStringFormatAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetStringFormatLineAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipDrawString.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(_RectF), ctypes.c_void_p, ctypes.c_void_p]
gdiplus.GdipMeasureString.argtypes = [
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.POINTER(_RectF),
    ctypes.c_void_p,
    ctypes.POINTER(_RectF),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
]

gdiplus.GdipBitmapLockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Rect), wintypes.UINT, ctypes.c_int, ctypes.POINTER(_BitmapData)]
gdiplus.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(_BitmapData)]

gdiplus.GdipDeleteBrush.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeletePen.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteFont.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteFontFamily.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteStringFormat.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]

class GdiCanvas:
    """Zero-dependency GDI+ 2D drawing wrapper for Python. Written by Gemini."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._token = ctypes.c_ulong()
        self._bitmap = ctypes.c_void_p()
        self._graphics = ctypes.c_void_p()
        self._closed = False

        startup_input = _GdiplusStartupInput(GdiplusVersion=1)
        gdiplus.GdiplusStartup(ctypes.byref(self._token), ctypes.byref(startup_input), None)

        gdiplus.GdipCreateBitmapFromScan0(
            width, height, 0, PixelFormat32bppPARGB, None, ctypes.byref(self._bitmap)
        )
        gdiplus.GdipGetImageGraphicsContext(self._bitmap, ctypes.byref(self._graphics))
        gdiplus.GdipSetSmoothingMode(self._graphics, SmoothingModeAntiAlias)
        gdiplus.GdipSetTextRenderingHint(self._graphics, TextRenderingHintClearTypeGridFit)

    @staticmethod
    def _to_argb(color: tuple[int, ...]) -> int:
        if len(color) == 3:
            r, g, b = color
            a = 255
        elif len(color) == 4:
            r, g, b, a = color
        else:
            raise ValueError("Color must be an (R, G, B) or (R, G, B, A) tuple.")
        return ((a & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)

    @staticmethod
    def _get_font_style(bold: bool, italic: bool) -> int:
        if bold and italic:
            return FontStyleBoldItalic
        if bold:
            return FontStyleBold
        if italic:
            return FontStyleItalic
        return FontStyleRegular

    def clear(self, color: tuple[int, ...] = (0, 0, 0, 0)):
        """Fills the entire canvas with a solid or transparent color."""
        gdiplus.GdipGraphicsClear(self._graphics, self._to_argb(color))

    def draw_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill_color: tuple[int, ...] | None = None,
        border_color: tuple[int, ...] | None = None,
        border_width: float = 1.0,
    ):
        """Draws a filled and/or outlined rectangle."""
        if fill_color is not None:
            brush = ctypes.c_void_p()
            gdiplus.GdipCreateSolidFill(self._to_argb(fill_color), ctypes.byref(brush))
            try:
                gdiplus.GdipFillRectangle(
                    self._graphics, brush, float(x), float(y), float(width), float(height)
                )
            finally:
                if brush.value:
                    gdiplus.GdipDeleteBrush(brush)

        if border_color is not None and border_width > 0:
            pen = ctypes.c_void_p()
            gdiplus.GdipCreatePen1(
                self._to_argb(border_color), float(border_width), UnitPixel, ctypes.byref(pen)
            )
            try:
                gdiplus.GdipDrawRectangle(
                    self._graphics, pen, float(x), float(y), float(width), float(height)
                )
            finally:
                if pen.value:
                    gdiplus.GdipDeletePen(pen)

    def measure_text(
        self,
        text: str,
        font_name: str = "Segoe UI",
        font_size: float = 16.0,
        bold: bool = False,
        italic: bool = False,
        max_width: float = 0.0,
        max_height: float = 0.0,
    ) -> tuple[float, float]:
        """Returns the exact (width, height) in pixels needed to render the given text."""
        style = self._get_font_style(bold, italic)
        font_family = ctypes.c_void_p()
        font = ctypes.c_void_p()
        str_format = ctypes.c_void_p()

        try:
            gdiplus.GdipCreateFontFamilyFromName(font_name, None, ctypes.byref(font_family))
            gdiplus.GdipCreateFont(font_family, float(font_size), style, UnitPixel, ctypes.byref(font))
            gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(str_format))

            # 0.0 width/height tells GDI+ there is no bounding limit (single-line measurement)
            layout = _RectF(0.0, 0.0, float(max_width), float(max_height))
            bounding_box = _RectF()
            codepoints_fitted = ctypes.c_int(0)
            lines_filled = ctypes.c_int(0)

            gdiplus.GdipMeasureString(
                self._graphics,
                text,
                -1,
                font,
                ctypes.byref(layout),
                str_format,
                ctypes.byref(bounding_box),
                ctypes.byref(codepoints_fitted),
                ctypes.byref(lines_filled),
            )
            return (bounding_box.Width, bounding_box.Height)
        finally:
            if str_format.value:
                gdiplus.GdipDeleteStringFormat(str_format)
            if font.value:
                gdiplus.GdipDeleteFont(font)
            if font_family.value:
                gdiplus.GdipDeleteFontFamily(font_family)

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        width: float = 0.0,
        height: float = 0.0,
        color: tuple[int, ...] = (255, 255, 255),
        font_name: str = "Segoe UI",
        font_size: float = 16.0,
        bold: bool = False,
        italic: bool = False,
        align: str = "left",
        valign: str = "top",
    ) -> tuple[float, float]:
        """Draws anti-aliased text and returns the measured (width, height) it occupied."""
        style = self._get_font_style(bold, italic)
        align_map = {"left": StringAlignmentNear, "center": StringAlignmentCenter, "right": StringAlignmentFar}
        valign_map = {"top": StringAlignmentNear, "center": StringAlignmentCenter, "bottom": StringAlignmentFar}

        font_family = ctypes.c_void_p()
        font = ctypes.c_void_p()
        brush = ctypes.c_void_p()
        str_format = ctypes.c_void_p()

        try:
            gdiplus.GdipCreateFontFamilyFromName(font_name, None, ctypes.byref(font_family))
            gdiplus.GdipCreateFont(font_family, float(font_size), style, UnitPixel, ctypes.byref(font))
            gdiplus.GdipCreateSolidFill(self._to_argb(color), ctypes.byref(brush))
            gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(str_format))
            gdiplus.GdipSetStringFormatAlign(str_format, align_map.get(align.lower(), StringAlignmentNear))
            gdiplus.GdipSetStringFormatLineAlign(str_format, valign_map.get(valign.lower(), StringAlignmentNear))
            layout = _RectF(float(x), float(y), float(width), float(height))
            bounding_box = _RectF()
            gdiplus.GdipMeasureString(
            self._graphics, text, -1, font, ctypes.byref(layout), str_format, ctypes.byref(bounding_box), None, None
            )
            gdiplus.GdipDrawString(
            self._graphics, text, -1, font, ctypes.byref(layout), str_format, brush
            )
            return (bounding_box.Width, bounding_box.Height)
        finally:
            if str_format.value:
                gdiplus.GdipDeleteStringFormat(str_format)
            if brush.value:
                gdiplus.GdipDeleteBrush(brush)
            if font.value:
                gdiplus.GdipDeleteFont(font)
            if font_family.value:
                gdiplus.GdipDeleteFontFamily(font_family)

    def get_bytes(self) -> bytes:
        """Returns the raw 32-bit BGRA pixel buffer as Python bytes."""
        lock_rect = _Rect(0, 0, self.width, self.height)
        bmp_data = _BitmapData()
        gdiplus.GdipBitmapLockBits(
            self._bitmap,
            ctypes.byref(lock_rect),
            ImageLockModeRead,
            PixelFormat32bppPARGB,
            ctypes.byref(bmp_data),
        )
        try:
            byte_count = abs(bmp_data.Stride) * self.height
            return ctypes.string_at(bmp_data.Scan0, byte_count)
        finally:
            gdiplus.GdipBitmapUnlockBits(self._bitmap, ctypes.byref(bmp_data))
            
    def close(self):
        """Releases native GDI+ bitmap and graphics handles."""
        if not self._closed:
            if self._graphics.value:
                gdiplus.GdipDeleteGraphics(self._graphics)
            if self._bitmap.value:
                gdiplus.GdipDisposeImage(self._bitmap)
                gdiplus.GdiplusShutdown(self._token)
            self._closed = True

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()