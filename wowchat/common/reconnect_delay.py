from __future__ import annotations

import logging


class ReconnectDelay:
	def __init__(self) -> None:
		self._logger = logging.getLogger(__name__)
		self._reconnect_delay: int | None = None

	def reset(self) -> None:
		self._reconnect_delay = None

	def get_next(self) -> int:
		self._reconnect_delay = 10
		self._logger.debug("GET RECONNECT DELAY %s", self._reconnect_delay)
		return self._reconnect_delay