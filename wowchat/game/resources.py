from __future__ import annotations

import csv
import importlib.resources as pkg_resources
from typing import Dict

from wowchat.common.config import WowExpansion


class GameResources:
	AREA: Dict[int, str] = {}
	ACHIEVEMENT: Dict[int, str] = {}

	@staticmethod
	def load(expansion: str) -> None:
		area_file = "pre_cata_areas.csv" if expansion in (WowExpansion.Vanilla, WowExpansion.TBC, WowExpansion.WotLK) else "post_cata_areas.csv"
		GameResources.AREA = GameResources._read_id_name_file(area_file)
		GameResources.ACHIEVEMENT = GameResources._read_id_name_file("achievements.csv")

	@staticmethod
	def _read_id_name_file(filename: str) -> Dict[int, str]:
		text = pkg_resources.read_text("wowchat.resources", filename, encoding="utf-8")
		reader = csv.reader(text.splitlines())
		return {int(row[0]): row[1] for row in reader}