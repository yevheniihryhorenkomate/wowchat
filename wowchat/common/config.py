from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple, Any

try:
	from pyhocon import ConfigFactory  # type: ignore
except Exception:  # pragma: no cover
	ConfigFactory = None  # type: ignore
try:
	import yaml  # type: ignore
except Exception:  # pragma: no cover
	yaml = None  # type: ignore


@dataclass
class FiltersConfig:
	enabled: bool
	patterns: Sequence[str]


@dataclass
class DiscordChannelConfig:
	channel: str
	format: str
	filters: Optional[FiltersConfig]


@dataclass
class WowChannelConfig:
	id: Optional[int]
	tp: int
	channel: Optional[str]
	format: str
	filters: Optional[FiltersConfig]


@dataclass
class ChannelConfig:
	chatDirection: str
	wow: WowChannelConfig
	discord: DiscordChannelConfig


@dataclass
class GuildNotificationConfig:
	enabled: bool
	format: str
	channel: Optional[str]


@dataclass
class GuildConfig:
	notificationConfigs: Dict[str, GuildNotificationConfig]


class Platform:
	Windows = "Windows"
	Mac = "Mac"

	@staticmethod
	def value_of(platform: str) -> str:
		p = (platform or "").lower()
		if p in ("win", "windows"):
			return Platform.Windows
		return Platform.Mac


class WowExpansion:
	Vanilla = "Vanilla"
	TBC = "TBC"
	WotLK = "WotLK"
	Cataclysm = "Cataclysm"
	MoP = "MoP"

	@staticmethod
	def value_of(version: str) -> str:
		if version.startswith("1."):
			return WowExpansion.Vanilla
		if version.startswith("2."):
			return WowExpansion.TBC
		if version.startswith("3."):
			return WowExpansion.WotLK
		if version == "4.3.4":
			return WowExpansion.Cataclysm
		if version == "5.4.8":
			return WowExpansion.MoP
		raise ValueError(f"Version {version} not supported!")


@dataclass
class RealmListConfig:
	name: str
	host: str
	port: int


@dataclass
class DiscordConfig:
	token: str
	enableDotCommands: bool
	dotCommandsWhitelist: Set[str]
	enableCommandsChannels: Set[str]
	enableTagFailedNotifications: bool


@dataclass
class Wow:
	locale: str
	platform: str
	realmBuild: Optional[int]
	gameBuild: Optional[int]
	realmlist: RealmListConfig
	account: bytes
	password: str
	character: str
	enableServerMotd: bool


@dataclass
class WowChatConfig:
	discord: DiscordConfig
	wow: Wow
	guildConfig: GuildConfig
	channels: Sequence[ChannelConfig]
	filters: Optional[FiltersConfig]
	version: str
	expansion: str


def _get_optional(cfg, path, default=None):
	return cfg.get(path) if cfg.has_path(path) else default


def _parse_realmlist(wow_cfg) -> RealmListConfig:
	realmlist = wow_cfg.get_string("realmlist")
	parts = realmlist.split(":", 1)
	if len(parts) == 1:
		return RealmListConfig(wow_cfg.get_string("realm"), parts[0], 3724)
	return RealmListConfig(wow_cfg.get_string("realm"), parts[0], int(parts[1]))


def _parse_realmlist_from_yaml(doc: Dict[str, Any]) -> RealmListConfig:
	host: str = str(doc.get("realmlist", "127.0.0.1"))
	port: int = int(doc.get("realm_port", 3724))
	name: str = str(doc.get("realm", ""))
	return RealmListConfig(name, host, port)


def _parse_simple_yaml_text(text: str) -> Dict[str, Any]:
	result: Dict[str, Any] = {}
	for raw_line in text.splitlines():
		line = raw_line.split('#', 1)[0].strip()
		if not line:
			continue
		if ':' not in line:
			continue
		key, val = line.split(':', 1)
		key = key.strip()
		val = val.strip()
		if val.startswith(('"', "'")) and val.endswith(('"', "'")) and len(val) >= 2:
			val = val[1:-1]
		# Try int
		try:
			ival = int(val)
			result[key] = ival
			continue
		except Exception:
			pass
		# Bool
		lval = val.lower()
		if lval in ("true", "false"):
			result[key] = (lval == "true")
			continue
		result[key] = val
	return result


def _parse_filters(cfg_opt) -> Optional[FiltersConfig]:
	if cfg_opt is None:
		return None
	return FiltersConfig(
		enabled=bool(_get_optional(cfg_opt, "enabled", False)),
		patterns=list(_get_optional(cfg_opt, "patterns", [])),
	)


def _parse_channels(channels_cfg) -> Sequence[ChannelConfig]:
	channels_list = channels_cfg.get_list("channels")
	result: List[ChannelConfig] = []
	for ch in channels_list:
		wow_channel_name = _get_optional(ch, "wow.channel")
		result.append(
			ChannelConfig(
				chatDirection=ch.get_string("direction"),
				wow=WowChannelConfig(
					id=_get_optional(ch, "wow.id"),
					tp=int(ch.get_string("wow.type") if ch.get_string("wow.type").isdigit() else 0),
					channel=wow_channel_name,
					format=_get_optional(ch, "wow.format", ""),
					filters=_parse_filters(_get_optional(ch, "wow.filters")),
				),
				discord=DiscordChannelConfig(
					channel=ch.get_string("discord.channel"),
					format=ch.get_string("discord.format"),
					filters=_parse_filters(_get_optional(ch, "discord.filters")),
				),
			)
		)
	return result


def _defaults_discord_config() -> DiscordConfig:
	return DiscordConfig(
		token="",
		enableDotCommands=True,
		dotCommandsWhitelist=set(),
		enableCommandsChannels=set(),
		enableTagFailedNotifications=True,
	)


def _parse_yaml_config(doc: Dict[str, Any]) -> WowChatConfig:
	# Build minimal config from a simplified YAML structure
	version = str(doc.get("version", "1.12.1"))
	expansion = WowExpansion.value_of(version)
	platform = Platform.value_of(str(doc.get("platform", "Mac")))
	locale = str(doc.get("locale", "enUS"))
	build = doc.get("build")
	realm_build = int(build) if build is not None else None
	game_build = int(build) if build is not None else None
	account = _convert_to_upper_bytes(str(doc.get("account", "")))
	password = str(doc.get("password", ""))
	character = str(doc.get("character", ""))
	realm = _parse_realmlist_from_yaml(doc)
	return WowChatConfig(
		discord=_defaults_discord_config(),
		wow=Wow(
			locale=locale,
			platform=platform,
			realmBuild=realm_build,
			gameBuild=game_build,
			realmlist=realm,
			account=account,
			password=password,
			character=character,
			enableServerMotd=True,
		),
		guildConfig=_parse_guild_config(None),
		channels=[],
		filters=None,
		version=version,
		expansion=expansion,
	)


def _parse_guild_config(guild_cfg_opt) -> GuildConfig:
	defaults = {
		"promoted": (True, "`[%user] has promoted [%target] to [%rank].`"),
		"demoted": (True, "`[%user] has demoted [%target] to [%rank].`"),
		"online": (False, "`[%user] has come online.`"),
		"offline": (False, "`[%user] has gone offline.`"),
		"joined": (True, "`[%user] has joined the guild.`"),
		"left": (True, "`[%user] has left the guild.`"),
		"removed": (True, "`[%target] has been kicked out of the guild by [%user].`"),
		"motd": (True, "`Guild Message of the Day: %message`"),
		"achievement": (True, "%user has earned the achievement %achievement!"),
	}
	configs: Dict[str, GuildNotificationConfig] = {}
	for key, (enabled, fmt) in defaults.items():
		if guild_cfg_opt is None or not guild_cfg_opt.has_path(key):
			configs[key] = GuildNotificationConfig(enabled, fmt, None)
		else:
			conf = guild_cfg_opt.get_config(key)
			configs[key] = GuildNotificationConfig(
				enabled=bool(_get_optional(conf, "enabled", enabled)),
				format=_get_optional(conf, "format", fmt),
				channel=_get_optional(conf, "channel"),
			)
	return GuildConfig(configs)


def load_config(conf_file: str) -> WowChatConfig:
	file_exists = os.path.exists(conf_file)
	# If a YAML file is provided, parse a simplified YAML structure
	if conf_file.endswith((".yml", ".yaml")) and file_exists:
		with open(conf_file, "r", encoding="utf-8") as fh:
			text = fh.read()
		if yaml is not None:
			doc = yaml.safe_load(text) or {}
			if not isinstance(doc, dict):
				raise ValueError("YAML config root must be a mapping/dictionary")
			return _parse_yaml_config(doc)
		# Fallback tiny parser (no external deps)
		doc2 = _parse_simple_yaml_text(text)
		return _parse_yaml_config(doc2)

	# Default: HOCON config (original format)
	if ConfigFactory is None:
		raise RuntimeError("pyhocon is required for HOCON configs. Install pyhocon or use a YAML file.")
	cfg = (ConfigFactory.parse_file(conf_file) if file_exists else ConfigFactory.load(conf_file)).resolve()

	discord_cfg = cfg.get_config("discord")
	wow_cfg = cfg.get_config("wow")
	guild_cfg_opt = cfg.get_config("guild") if cfg.has_path("guild") else None
	channels_cfg = cfg.get_config("chat")
	filters_cfg_opt = cfg.get_config("filters") if cfg.has_path("filters") else None

	version = _get_optional(wow_cfg, "version") or "1.12.1"
	expansion = WowExpansion.value_of(version)

	return WowChatConfig(
		discord=DiscordConfig(
			token=str(discord_cfg.get_string("token")),
			enableDotCommands=bool(_get_optional(discord_cfg, "enable_dot_commands", True)),
			dotCommandsWhitelist=set(map(str.lower, _get_optional(discord_cfg, "dot_commands_whitelist", []))),
			enableCommandsChannels=set(map(str.lower, _get_optional(discord_cfg, "enable_commands_channels", []))),
			enableTagFailedNotifications=bool(_get_optional(discord_cfg, "enable_tag_failed_notifications", True)),
		),
		wow=Wow(
			locale=_get_optional(wow_cfg, "locale") or "enUS",
			platform=Platform.value_of(_get_optional(wow_cfg, "platform") or "Mac"),
			realmBuild=_get_optional(wow_cfg, "realm_build") or _get_optional(wow_cfg, "build"),
			gameBuild=_get_optional(wow_cfg, "game_build") or _get_optional(wow_cfg, "build"),
			realmlist=_parse_realmlist(wow_cfg),
			account=_convert_to_upper_bytes(wow_cfg.get_string("account")),
			password=wow_cfg.get_string("password"),
			character=wow_cfg.get_string("character"),
			enableServerMotd=bool(_get_optional(wow_cfg, "enable_server_motd", True)),
		),
		guildConfig=_parse_guild_config(guild_cfg_opt),
		channels=_parse_channels(channels_cfg),
		filters=_parse_filters(filters_cfg_opt),
		version=version,
		expansion=expansion,
	)


def _convert_to_upper_bytes(account: str) -> bytes:
	upper = ''.join(c.upper() if 'a' <= c <= 'z' else c for c in account)
	return upper.encode("utf-8")


def get_build_from_version(version: str) -> int:
	mapping = {
		"1.6.1": 4544,
		"1.6.2": 4565,
		"1.6.3": 4620,
		"1.7.1": 4695,
		"1.8.4": 4878,
		"1.9.4": 5086,
		"1.10.2": 5302,
		"1.11.2": 5464,
		"1.12.1": 5875,
		"1.12.2": 6005,
		"1.12.3": 6141,
		"2.4.3": 8606,
		"3.2.2": 10505,
		"3.3.0": 11159,
		"3.3.2": 11403,
		"3.3.3": 11723,
		"3.3.5": 12340,
		"4.3.4": 15595,
		"5.4.8": 18414,
	}
	if version not in mapping:
		raise ValueError(f"Build {version} not supported!")
	return mapping[version]


def get_realm_build(conf: WowChatConfig) -> int:
	return conf.wow.realmBuild or get_build_from_version(conf.version)


def get_game_build(conf: WowChatConfig) -> int:
	return conf.wow.gameBuild or get_build_from_version(conf.version)