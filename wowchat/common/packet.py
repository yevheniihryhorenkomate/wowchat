from __future__ import annotations

import struct
from typing import Optional


class ByteReader:
	def __init__(self, data: bytes) -> None:
		self._data = memoryview(data)
		self._pos = 0

	def remaining(self) -> int:
		return len(self._data) - self._pos

	def read_u8(self) -> int:
		b = self._data[self._pos]
		self._pos += 1
		return int(b)

	def read_i8(self) -> int:
		v = struct.unpack_from('<b', self._data, self._pos)[0]
		self._pos += 1
		return v

	def read_u16le(self) -> int:
		v = struct.unpack_from('<H', self._data, self._pos)[0]
		self._pos += 2
		return v

	def read_i16le(self) -> int:
		v = struct.unpack_from('<h', self._data, self._pos)[0]
		self._pos += 2
		return v

	def read_u32le(self) -> int:
		v = struct.unpack_from('<I', self._data, self._pos)[0]
		self._pos += 4
		return v

	def read_i32le(self) -> int:
		v = struct.unpack_from('<i', self._data, self._pos)[0]
		self._pos += 4
		return v

	def read_u64le(self) -> int:
		v = struct.unpack_from('<Q', self._data, self._pos)[0]
		self._pos += 8
		return v

	def read_f32le(self) -> float:
		v = struct.unpack_from('<f', self._data, self._pos)[0]
		self._pos += 4
		return v

	def read_cstring(self) -> str:
		start = self._pos
		while self._pos < len(self._data) and self._data[self._pos] != 0:
			self._pos += 1
		val = bytes(self._data[start:self._pos]).decode('utf-8', errors='ignore')
		if self._pos < len(self._data) and self._data[self._pos] == 0:
			self._pos += 1
		return val

	def read_bytes(self, n: int) -> bytes:
		b = bytes(self._data[self._pos:self._pos + n])
		self._pos += n
		return b

	def skip(self, n: int) -> None:
		self._pos += n