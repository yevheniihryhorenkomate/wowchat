from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, TYPE_CHECKING

from wowchat.common.global_state import Global

if TYPE_CHECKING:  # Only for type hints; avoids importing discord at runtime
    import discord  # type: ignore


@dataclass
class WhoRequest:
	message_channel: discord.abc.Messageable
	player_name: str


@dataclass
class WhoResponse:
	player_name: str
	guild_name: str
	lvl: int
	cls: str
	race: str
	gender: Optional[str]
	zone: str


class CommandHandler:
	_logger = logging.getLogger(__name__)
	_trigger = "?"
	who_request: Optional[WhoRequest] = None

	@staticmethod
	def handle(from_channel: discord.abc.Messageable, message: str) -> bool:
		if not message.startswith(CommandHandler._trigger):
			return False
		parts = message[len(CommandHandler._trigger):].split(" ")
		cmd = parts[0].lower() if parts else ""
		arg = parts[1] if len(parts) > 1 and len(parts[1]) <= 16 else None

		try:
			if cmd in ("who", "online"):
				if Global.game is None:
					from_channel.send("Bot is not online.")  # type: ignore[attr-defined]
					return True
				res = Global.game.handle_who(arg)  # type: ignore[union-attr]
				if arg:
					CommandHandler.who_request = WhoRequest(from_channel, arg)
				return True
			elif cmd == "gmotd":
				if Global.game is None:
					from_channel.send("Bot is not online.")  # type: ignore[attr-defined]
					return True
				resp = Global.game.handle_gmotd()  # type: ignore[union-attr]
				if resp:
					from_channel.send(resp)  # type: ignore[attr-defined]
				return True
			else:
				return False
		except Exception:
			# Unrecognized; let it fall through to normal chat
			return False