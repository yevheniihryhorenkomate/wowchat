from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # Only for type hints; avoids importing discord at runtime
    import discord  # type: ignore

from wowchat.common.config import WowExpansion
from wowchat.game.resources import GameResources


@dataclass
class _RegexSpec:
	key: str
	pattern: re.Pattern


class MessageResolver:
    def __init__(self, client: 'discord.Client', expansion: str) -> None:
		self._client = client
		self._expansion = expansion
		self._link_site = self._site_for_expansion(expansion)
		self._regexes = self._regexes_for_expansion(expansion)

	def _site_for_expansion(self, expansion: str) -> str:
		if expansion == WowExpansion.Vanilla:
			return "http://classicdb.ch"
		if expansion == WowExpansion.TBC:
			return "http://tbc-twinhead.twinstar.cz"
		if expansion == WowExpansion.WotLK:
			return "http://wotlk-twinhead.twinstar.cz"
		if expansion == WowExpansion.Cataclysm:
			return "https://cata-twinhead.twinstar.cz/"
		if expansion == WowExpansion.MoP:
			return "http://mop-shoot.tauri.hu"
		return "http://classicdb.ch"

	def _regexes_for_expansion(self, expansion: str) -> Sequence[_RegexSpec]:
		pairs: List[Tuple[str, str]] = [
			("item", r"\|.+?\|Hitem:(\d+):.+?\|h\[(.+?)]\|h\|r"),
			("spell", r"\|.+?\|(?:Hspell|Henchant)?:(\d+).*?\|h\[(.+?)]\|h\|r"),
			("quest", r"\|.+?\|Hquest:(\d+):.+?\|h\[(.+?)]\|h\|r"),
		]
		if expansion in (WowExpansion.WotLK, WowExpansion.Cataclysm, WowExpansion.MoP):
			pairs.append(("achievement", r"\|.+?\|Hachievement:(\d+):.+?\|h\[(.+?)]\|h\|r"))
		if expansion == WowExpansion.WotLK:
			pairs.append(("spell", r"\|Htrade:(\d+):.+?\|h\[(.+?)]\|h"))
		if expansion == WowExpansion.MoP:
			pairs.append(("spell", r"\|Htrade:.+?:(\d+):.+?\|h\[(.+?)]\|h"))
		return [_RegexSpec(k, re.compile(p)) for (k, p) in pairs]

	def resolve_links(self, message: str) -> str:
		for spec in self._regexes:
			message = spec.pattern.sub(lambda m: f"[[{m.group(2)}]]({self._link_site}?{spec.key}={m.group(1)})", message)
		return message

	def resolve_achievement_id(self, achievement_id: int) -> str:
		name = GameResources.ACHIEVEMENT.get(achievement_id, str(achievement_id))
		return f"[[{name}]]({self._link_site}?achievement={achievement_id})"

	def strip_color_coding(self, message: str) -> str:
		hex_pat = re.compile(r"\|c[0-9a-fA-F]{8}")
		pass1 = re.compile(r"\|c[0-9a-fA-F]{8}(.*?)\|r")
		return hex_pat.sub("", pass1.sub(lambda m: m.group(1), message))

    def resolve_tags(self, channel: 'discord.TextChannel', message: str, on_error) -> str:
		regexes = [re.compile(r'"@(.+?)"'), re.compile(r"@([\w]+)")]
		members = [m for m in channel.members if m.id != self._client.user.id]  # type: ignore[union-attr]
		effective = [(m.display_name, m.id) for m in members]
		usernames = [(f"{m.name}#{m.discriminator}", m.id) for m in members]
		roles = [(r.name, r.id) for r in channel.guild.roles if r.name != "@everyone"]

		def resolve_group(names: List[Tuple[str, int]], tag: str, is_role: bool) -> List[Tuple[str, str]]:
			l = tag.lower()
			if l == "here":
				return []
			matches = [(n, str(i) if not is_role else f"&{i}") for (n, i) in names if l in n.lower()]
			if len(matches) > 1 and " " not in l:
				exact = [m for m in matches if m[0].lower() == l]
				if exact:
					return exact
				words = [m for m in matches if l in re.split(r"\W+", m[0].lower())]
				return words or matches
			return matches

		for rx in regexes:
			def replace(m):
				tag = m.group(1)
				matches: List[Tuple[str, str]] = []
				for group, is_role in ((effective, False), (usernames, False), (roles, True)):
					if matches:
						resolved = resolve_group(group, tag, is_role)
						if len(matches) == 1:
							break
						matches.extend(resolved)
					else:
						matches = resolve_group(group, tag, is_role)
				if len(matches) == 1:
					return f"<@{matches[0][1]}>"
				if 1 < len(matches) < 5:
					on_error(f"Your tag @{tag} matches multiple channel members: {', '.join(n for n,_ in matches)}. Be more specific in your tag!")
					return m.group(0)
				if len(matches) >= 5:
					on_error(f"Your tag @{tag} matches too many channel members. Be more specific in your tag!")
					return m.group(0)
				return m.group(0)
			message = rx.sub(replace, message)
		return message

	def resolve_emojis(self, message: str) -> str:
		regex = re.compile(r"(?<=:).*?(?=:)")
		emoji_map = {e.name.lower(): e.id for e in getattr(self._client, 'emojis', [])}
		seen = set()
		def repl(m):
			name = m.group(0).lower()
			if name in seen:
				return m.group(0)
			seen.add(name)
			if name in emoji_map:
				return f"<:{m.group(0)}:{emoji_map[name]}>"
			return m.group(0)
		return regex.sub(repl, message)