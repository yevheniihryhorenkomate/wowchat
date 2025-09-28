from __future__ import annotations

import logging
import re
from typing import Optional

import discord

from wowchat.common.global_state import Global


class DiscordClient(discord.Client):
	def __init__(self) -> None:
		intents = discord.Intents.default()
		intents.members = True
		intents.presences = True
		intents.message_content = True
		super().__init__(intents=intents)
		self._logger = logging.getLogger(__name__)

	async def setup_hook(self) -> None:  # type: ignore[override]
		pass

	async def on_ready(self) -> None:  # type: ignore[override]
		self._logger.info("Discord connected as %s", self.user)
		# TODO: Build channel maps from Global.config similar to Scala implementation

	async def on_message(self, message: discord.Message) -> None:  # type: ignore[override]
		if message.author.id == self.user.id:  # type: ignore[attr-defined]
			return
		if message.guild is None or message.channel is None:
			return
		if message.type not in (discord.MessageType.default, discord.MessageType.reply):
			return
		content = message.content or ""
		attachments = " ".join(a.url for a in message.attachments)
		payload = (content + " " + attachments).strip()
		if not payload:
			self._logger.error(
				"Received a message in channel %s but content was empty. MESSAGE CONTENT INTENT might be missing.",
				message.channel.name,
			)
			return
		# TODO: route to WoW once game connector is implemented
		self._logger.info("Discord->(pending WoW) [%s] %s: %s", message.channel.name, message.author.display_name, payload)

	def change_guild_status(self, text: str) -> None:
		if self.user is None:
			return
		self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))

	def change_realm_status(self, text: str) -> None:
		self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=text))

	def send_message_from_wow(self, from_name: Optional[str], message: str, wow_type: int, wow_channel: Optional[str]) -> None:
		# TODO: Map WoW->Discord channels using Global.wow_to_discord
		self._logger.info("WoW->Discord (pending mapping) %s", message)

	async def start(self, token: str) -> None:  # type: ignore[override]
		await super().start(token)