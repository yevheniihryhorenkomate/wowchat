from __future__ import annotations

from dataclasses import dataclass
from secrets import token_bytes


@dataclass
class BigNumber:
	value: int

	@staticmethod
	def from_hex(s: str) -> "BigNumber":
		return BigNumber(int(s, 16))

	@staticmethod
	def from_bytes(b: bytearray | bytes, reverse: bool = False) -> "BigNumber":
		arr = bytearray(b)
		if reverse:
			arr.reverse()
		# Ensure positive
		if arr and arr[0] & 0x80:
			arr = bytearray((0,)) + arr
		return BigNumber(int.from_bytes(arr, byteorder="big", signed=False))

	@staticmethod
	def rand(amount: int) -> "BigNumber":
		return BigNumber(int.from_bytes(token_bytes(amount), "big"))

	def mul(self, other: "BigNumber") -> "BigNumber":
		return BigNumber(self.value * abs(other.value))

	def sub(self, other: "BigNumber") -> "BigNumber":
		return BigNumber(self.value - abs(other.value))

	def add(self, other: "BigNumber") -> "BigNumber":
		return BigNumber(self.value + abs(other.value))

	def mod_pow(self, v1: "BigNumber", v2: "BigNumber") -> "BigNumber":
		return BigNumber(pow(self.value, abs(v1.value), abs(v2.value)))

	def to_hex_string(self) -> str:
		return format(self.value, "X")

	def as_byte_array(self, req_size: int = 0, reverse: bool = True) -> bytes:
		arr = self.value.to_bytes((self.value.bit_length() + 7) // 8 or 1, "big")
		if arr and arr[0] == 0:
			arr = arr[1:]
		if reverse:
			arr = arr[::-1]
		if req_size > len(arr):
			arr = arr + bytes(req_size - len(arr))
		return arr