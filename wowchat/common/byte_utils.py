from __future__ import annotations

from typing import Iterable


def short_to_bytes(value: int) -> bytes:
	return bytes(((value >> 8) & 0xFF, value & 0xFF))


def short_to_bytes_le(value: int) -> bytes:
	return bytes((value & 0xFF, (value >> 8) & 0xFF))


def int_to_bytes(value: int) -> bytes:
	return bytes(((value >> 24) & 0xFF, (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF))


def int_to_bytes_le(value: int) -> bytes:
	return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF))


def long_to_bytes(value: int) -> bytes:
	return bytes(
		(
			(value >> 56) & 0xFF,
			(value >> 48) & 0xFF,
			(value >> 40) & 0xFF,
			(value >> 32) & 0xFF,
			(value >> 24) & 0xFF,
			(value >> 16) & 0xFF,
			(value >> 8) & 0xFF,
			value & 0xFF,
		)
	)


def long_to_bytes_le(value: int) -> bytes:
	return bytes(
		(
			value & 0xFF,
			(value >> 8) & 0xFF,
			(value >> 16) & 0xFF,
			(value >> 24) & 0xFF,
			(value >> 32) & 0xFF,
			(value >> 40) & 0xFF,
			(value >> 48) & 0xFF,
			(value >> 56) & 0xFF,
		)
	)


def string_to_int(s: str) -> int:
	return bytes_to_long(s.encode("utf-8"))


def bytes_to_long(b: bytes) -> int:
	result = 0
	for i, byte in enumerate(reversed(b)):
		result |= (byte & 0xFF) << (i * 8)
	return result


def bytes_to_long_le(b: bytes) -> int:
	result = 0
	for i, byte in enumerate(b):
		result |= (byte & 0xFF) << (i * 8)
	return result


def to_hex_string(b: bytes, add_spaces: bool = False, resolve_plain_text: bool = True) -> str:
	parts = []
	for byte in b:
		if resolve_plain_text and 0x20 <= byte < 0x7F:
			parts.append(chr(byte) + (" " if add_spaces else ""))
		else:
			parts.append(f"{byte:02X}" + (" " if add_spaces else ""))
	return ("".join(parts)).strip()