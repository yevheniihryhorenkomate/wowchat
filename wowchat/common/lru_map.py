from __future__ import annotations

from collections import OrderedDict
from typing import Generic, Iterable, Iterator, MutableMapping, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUMap(OrderedDict, Generic[K, V]):
	def __init__(self, max_size: int = 10000):
		super().__init__()
		self._max_size = max_size

	def __getitem__(self, key: K) -> V:
		value = super().__getitem__(key)
		super().__delitem__(key)
		super().__setitem__(key, value)
		return value

	def __setitem__(self, key: K, value: V) -> None:
		while len(self) >= self._max_size:
			super().popitem(last=False)
		super().__setitem__(key, value)