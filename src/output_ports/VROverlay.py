import config;
import openvr;
import ctypes;
import time
from output_ports.gdi_canvas import GdiCanvas

config.add_general_setting_path("VROverlay (Experimental)", "output_ports.VROverlay")
config.addConfig("VROverlay (Experimental)", "IS_ENABLED", "Enable outputting to VROverlay?", "bool")
config.addConfig("VROverlay (Experimental)", "IS_RIGHT_HAND", "Attach overlay on the right hand?", "bool")

IS_ENABLED = False;
IS_RIGHT_HAND = True;

# TODO: Check if every Windows system has the font file "MSYH" (Microsoft YaHei)
FONT_NAME = "Segoe UI Light";
TRANSPARENT = (255,255,255,255,0);
OVERLAY_BACKGROUND = (0,0,0,170);
SIZE_RATIO = 1.6;
WIDTH = 500;
HEIGHT = round(WIDTH / SIZE_RATIO);
OVERLAY_PADDING = 10;

WIDTH_IN_METER = 0.15
VR_OVERLAY_KEY = "VRSlideshow_Overlay";
VR_OVERLAY_NAME = "VR Slideshow Overlay";

font = None;
img = None;
draw = None
overlay = None;
handle = None;
vrSystem = None;
imageData = None;
posMatrix = None;
controllerConstant = None;


def init():
    global posMatrix;
    global controllerConstant;
    if openvr.isRuntimeInstalled()==0 or openvr.isHmdPresent()==0:
        raise Exception("This feature requires a VR headset!");
    posMatrix = overlayMatrix();
    controllerConstant = openvr.TrackedControllerRole_RightHand if IS_RIGHT_HAND else openvr.TrackedControllerRole_LeftHand;
    isOutputReady();
    initImage();

def isOutputReady():
    global vrSystem;
    global handle;
    global overlay;
    try:
        if vrSystem is None:
            vrSystem = openvr.init(openvr.VRApplication_Background);
        controller = vrSystem.getTrackedDeviceIndexForControllerRole(controllerConstant)
        if controller==openvr.k_unTrackedDeviceIndexInvalid:
            raise Exception("No valid controller found. Did it turn off?")
        overlay = openvr.IVROverlay();
        try:
            handle = overlay.findOverlay(VR_OVERLAY_KEY);
        except openvr.error_code.OverlayError_UnknownOverlay:
            handle = createOverlay();
        # Attach the overlay on the "correct" right hand (In case user may switch their controllers)
        overlay.setOverlayTransformTrackedDeviceRelative(handle, controller, posMatrix);
        return True;
    except Exception as ex:
        print(translateError(ex))
        return False;

def initImage():
    global imageData;
    imageData = ctypes.c_buffer(b'', WIDTH * HEIGHT * 4);

def overlayMatrix():
    arr = openvr.HmdMatrix34_t();
    # https://www.brainvoyager.com/bv/doc/UsersGuide/CoordsAndTransforms/SpatialTransformationMatrices.html
    # Position
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    
    arr[0][3] = 0;      # X
    arr[1][3] = 0.05;   # Y
    arr[2][3] = 0       # Z 

    # Rotation
    arr[0][0] = 1
    arr[1][0] = 0
    arr[2][0] = 0

    arr[0][1] = 0
    arr[1][1] = 0
    arr[2][1] = -1

    arr[0][2] = 0
    arr[1][2] = 1
    arr[2][2] = 0

    return arr;

def createOverlay():
    handle=overlay.createOverlay(VR_OVERLAY_KEY, VR_OVERLAY_NAME);
    overlay.setOverlayAlpha(handle, 0.9)
    overlay.setOverlayWidthInMeters(handle, WIDTH_IN_METER);
    overlay.showOverlay(handle);
    return handle;

def translateError(ex):
    errType = type(ex);
    translation = str(ex);
    if errType==openvr.error_code.InitError_Init_NoServerForBackgroundApp:
        translation = "You're not in VR right now";
    elif errType==openvr.error_code.InitError_Init_HmdNotFound:
        translation = "Your headset hasn't connected to your PC yet";
    translation = translation if translation!="" else errType.__name__;
    return translation;

def createImage(pText):
    text = "\n".join(pText);
    text = text.replace("\v", "\n").replace("\t","  ")
    pText = text.split("\n");

    with GdiCanvas(WIDTH, HEIGHT) as canvas:
        canvas.clear((255, 255, 255, 0));
        text_w, text_h = canvas.measure_text(text, font_size=24, bold=True, font_name=FONT_NAME);

        textRectW = min(text_w, WIDTH);
        textRectH = min(text_h, HEIGHT);
    
        startX = max((WIDTH - textRectW) / 2, OVERLAY_PADDING)
        startY = HEIGHT - textRectH - OVERLAY_PADDING;
    
        canvas.draw_rectangle(
            startX - OVERLAY_PADDING, 
            startY - OVERLAY_PADDING, 
            min(startX + textRectW + OVERLAY_PADDING, WIDTH) - 1, 
            HEIGHT - startY + OVERLAY_PADDING - 1,
            fill_color=OVERLAY_BACKGROUND,
            border_color=(255, 255, 255, 255),
            border_width=1
        );

        canvas.draw_text(
            text=text,
            x=startX,
            y=startY,
            color=(255, 255, 255),
            font_size=24,
            bold=True,
            font_name=FONT_NAME,
            # align="center"
        )

        imageData.raw  = canvas.get_bytes();

def outputString(text):
    global vrSystem;
    try:
        if isOutputReady():
            createImage(text);
            # Cause Request_Failed after a number of calls
            # Log Message: Refusing to create memory block because 201 blocks are already outstanding
            overlay.setOverlayRaw(handle, imageData, WIDTH, HEIGHT, 4)
    except Exception as ex:
        if type(ex)==openvr.error_code.OverlayError_RequestFailed:
            # Not sure how to fix it, so the output will restart the overlay here
            print("Run out of memory block, restarting overlay...");
            openvr.shutdown();
            vrSystem = None;
            isOutputReady();
            time.sleep(0.5)
            overlay.setOverlayRaw(handle, imageData, WIDTH, HEIGHT, 4)
        else:
            print(translateError(ex));
