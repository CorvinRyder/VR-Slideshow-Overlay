from plugins.lib.MediaInfo import MediaWatcher
import math

MODULE_NAME = "NowPlayingWin10";
MODULE_DESC = "Showing the information of any media being played in Windows 10";
PLUGIN_ENABLED = False;
class NowPlayingWin10:
		def onUpdate(self, scriptUpTime):
			with MediaWatcher() as media:
				info = media.get_media_info()
				if(info is None):
					return "No media playing"

				sb = [info["title"], info["artist"]];
				if(info["status"] != "Playing"):
					sb.append("├──Paused──┤");
				else:
					progressbar = "├" + ("─" * 10) + "┤";
					index = min(10,math.floor(info["position"] / info["duration"] * 10) + 1);
					progressbar = progressbar[:index] + "■" + progressbar[index+1:]
					sb.append(progressbar);
				return "\n".join(sb);