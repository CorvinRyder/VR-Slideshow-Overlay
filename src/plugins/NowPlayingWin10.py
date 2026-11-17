from plugins.lib.MediaInfo import MediaWatcher
import math
import config;

MODULE_NAME = "NowPlayingWin10";
MODULE_DESC = "Showing the information of any media being played.\n This plugin only works on Windows 10+";
config.addConfig(__name__, "SHOW_MUSIC_ONLY", "Show the playing music only?\nIgnore videos like Youtube or Tiktok", "bool")
config.addConfig(__name__, "SHOW_PROGRESS_BAR", "Show progress bar?", "bool")

PLUGIN_ENABLED = False;
SHOW_MUSIC_ONLY = True;
SHOW_PROGRESS_BAR = True;
class NowPlayingWin10:
		def onUpdate(self, scriptUpTime):
			with MediaWatcher() as media:
				info = media.get_media_info()
				if(info is None):
					return "No media playing"
   
				if(SHOW_MUSIC_ONLY and info["type"] != "Music"):
					return "No music playing"

				sb = [info["title"], info["artist"]];
				if SHOW_PROGRESS_BAR:
					if(info["status"] != "Playing"):
						sb.append("├───Paused───┤");
					else:
						progressbar = "├" + ("─" * 10) + "┤";
						index = min(10,math.floor(info["position"] / info["duration"] * 10) + 1);
						progressbar = progressbar[:index] + "■" + progressbar[index+1:]
						sb.append(progressbar);
				return "\n".join(sb);