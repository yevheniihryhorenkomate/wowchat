THIS SHOULD BE A LINTER ERRORimport argparse
import asyncio
import logging
import os
import sys

from wowchat.common.config import load_config
from wowchat.common.global_state import Global
from wowchat.game.resources import GameResources


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="WoWChat Python")
	parser.add_argument("config", nargs="?", default="wowchat.conf", help="Path to wowchat.conf")
	return parser.parse_args()


async def main_async() -> None:
	args = parse_args()
	conf_path = args.config
	if not os.path.exists(conf_path):
		print(f"No configuration file supplied or not found at {conf_path}.", file=sys.stderr)
		print("Trying with default wowchat.conf in current directory.", file=sys.stderr)

	Global.config = load_config(conf_path)

	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s %(levelname)s %(name)s | %(message)s",
	)
	logger = logging.getLogger("wowchat")
	logger.info("Running WoWChat - v1.3.8-py")

	# Load static game resources first
	GameResources.load(Global.config.expansion)

	# Start Discord only if a token is configured
	token = (getattr(Global.config.discord, "token", "") or "").strip()
	if not token:
		logger.info("No Discord token configured. Skipping Discord client startup.")
		return

	# Import Discord client lazily to avoid requiring discord.py when not used
	try:
		from wowchat.discord.client import DiscordClient  # local import
	except Exception as e:  # pragma: no cover
		logger.error("Discord token provided but Discord client is unavailable: %s", e)
		logger.error("Install discord.py or remove the token to run without Discord.")
		return
	discord = DiscordClient()
	Global.discord = discord
	await discord.start(token)


def main() -> None:
	try:
		asyncio.run(main_async())
	except KeyboardInterrupt:
		pass


if __name__ == "__main__":
	main()