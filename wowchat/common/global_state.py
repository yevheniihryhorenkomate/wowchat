from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional, Set, Tuple

from wowchat.common.config import WowChatConfig


class Global:
	config: WowChatConfig = None  # type: ignore
	discord = None
	game = None

	# Maps for channel routing
	discord_to_wow: Dict[str, Set[object]] = {}
	wow_to_discord: Dict[Tuple[int, Optional[str]], Set[Tuple[object, object]]] = {}
	guild_events_to_discord: Dict[str, Set[object]] = {}

	@staticmethod
	def get_time() -> str:
		return _dt.datetime.now().strftime("%H:%M:%S")