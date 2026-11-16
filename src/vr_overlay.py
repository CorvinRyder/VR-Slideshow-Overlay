from gui import S1_StartWindow, S2_SettingWindow;
import tkinter as tk;
from updateloop import MainLoop, LoadPlugins;
import config;
import os;
import threading;

root = None;
mainLoop = None;

def commandCallback(command):
    global root;
    if command=="startscript":
        mainLoop = threading.Thread(target = MainLoop.update_loop);
        mainLoop.start();
    if command=="configwindow":
        switchWindow(S2_SettingWindow.App)
    if command=="settingwinclose":
        # print("Window Closed!");
        config.saveConfig();
        switchWindow(S1_StartWindow.App);
    if command=="mainwindowclose":
        MainLoop.FORCE_TERMINATE = True;
        if root is not None:
            root.destroy();

def switchWindow(windowClass):
    global root;
    if root is not None:
        root.destroy();
    root = tk.Tk();
    windowClass(root, commandCallback)
    root.mainloop();

if __name__ == '__main__':
    LoadPlugins.read_plugins(os.path.join(os.getcwd(),"plugins"));
    config.register_general_setting();
    config.readConfig();
    switchWindow(S1_StartWindow.App);
