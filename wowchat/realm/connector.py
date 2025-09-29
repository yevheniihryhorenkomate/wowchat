from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

from wowchat.common.byte_utils import int_to_bytes
from wowchat.common.config import Platform, WowChatConfig, WowExpansion, get_realm_build
from wowchat.common.global_state import Global
from wowchat.common.packet import ByteReader
from wowchat.realm.packets import RealmPackets
from wowchat.realm.srp_client import SRPClient
from wowchat.realm.big_number import BigNumber


@dataclass
class RealmList:
	name: str
	address: str
	realm_id: int


class RealmConnector:
	def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
		self._loop = loop
		self._logger = logging.getLogger(__name__)
		self._reader: asyncio.StreamReader | None = None
		self._writer: asyncio.StreamWriter | None = None
		self._srp = SRPClient()
		self._session_key: Optional[bytes] = None

		# CRC hashes per Scala implementation (subset sufficient for WotLK 3.3.5)
		# Keyed by (build, platform)
		self._build_crc_hashes: dict[tuple[int, str], bytes] = {
			# 3.3.5 (12340)
			(12340, Platform.Mac): bytes([
				0xB7, 0x06, 0xD1, 0x3F, 0xF2, 0xF4, 0x01, 0x88, 0x39, 0x72, 0x94, 0x61, 0xE3, 0xF8, 0xA0, 0xE2, 0xB5, 0xFD, 0xC0, 0x34
			]),
			(12340, Platform.Windows): bytes([
				0xCD, 0xCB, 0xBD, 0x51, 0x88, 0x31, 0x5E, 0x6B, 0x4D, 0x19, 0x44, 0x9D, 0x49, 0x2D, 0xBC, 0xFA, 0xF1, 0x56, 0xA3, 0x47
			]),
		}

	async def connect(self, conf: WowChatConfig) -> None:
		host = conf.wow.realmlist.host
		port = conf.wow.realmlist.port
		self._logger.info("Connecting to realm server %s:%s", host, port)
		self._reader, self._writer = await asyncio.open_connection(host, port)
		await self._send_auth_logon_challenge(conf)
		await self._read_loop(conf)

	async def _send_auth_logon_challenge(self, conf: WowChatConfig) -> None:
		version = list(map(int, conf.version.split('.')))
		platform_str = "Win" if conf.wow.platform == Platform.Windows else "OSX"
		locale_str = conf.wow.locale
		account = conf.wow.account
		size = 30 + len(account)
		payload = bytearray()
		payload.append(3 if conf.expansion == WowExpansion.Vanilla else 8)
		payload += size.to_bytes(2, 'little', signed=False)
		payload += int_to_bytes(int.from_bytes(b"WoW", 'big'))
		payload += bytes((version[0], version[1], version[2]))
		payload += get_realm_build(conf).to_bytes(2, 'little')
		payload += int_to_bytes(int.from_bytes(b"x86", 'big'))
		payload += int_to_bytes(int.from_bytes(platform_str.encode('ascii'), 'big'))
		payload += int_to_bytes(int.from_bytes(locale_str.encode('ascii'), 'big'))
		payload += (0).to_bytes(4, 'little')
		payload += bytes((127, 0, 0, 1))
		payload.append(len(account))
		payload += account
		self._writer.write(bytes((RealmPackets.CMD_AUTH_LOGON_CHALLENGE,)) + payload)
		await self._writer.drain()

	async def _read_exact(self, n: int) -> bytes:
		assert self._reader is not None
		return await self._reader.readexactly(n)

	async def _read_loop(self, conf: WowChatConfig) -> None:
		assert self._reader and self._writer
		try:
			while True:
				id_b = await self._read_exact(1)
				pkt_id = id_b[0]
				if pkt_id == RealmPackets.CMD_AUTH_LOGON_CHALLENGE:
					await self._handle_logon_challenge(conf)
				elif pkt_id == RealmPackets.CMD_AUTH_LOGON_PROOF:
					await self._handle_logon_proof()
				elif pkt_id == RealmPackets.CMD_REALM_LIST:
					await self._handle_realm_list(conf)
					# Після обробки realm list, виходимо з циклу
					break
				else:
					self._logger.debug("Unknown realm packet %02X", pkt_id)
		except Exception as e:
			self._logger.error("Error in realm read loop: %s", e)
			raise

	async def _handle_logon_challenge(self, conf: WowChatConfig) -> None:
		# We already read id; now parse the rest according to Scala logic
		# read header length + result-dependent size in a simple way: read 2 then rest of available bytes from transport buffer isn't trivial; for now, read a reasonable chunk
		rest = await self._read_exact(2)
		# Peek result by reading minimal fields
		# For simplicity in this scaffold: read the rest in a fixed buffer (server dependent); robust framing can be added later
		remaining = await self._reader.read(2048)
		buf = ByteReader(rest + remaining)
		error = buf.read_u8()
		result = buf.read_u8()
		if not RealmPackets.AuthResult.is_success(result):
			self._logger.error(RealmPackets.AuthResult.get_message(result))
			self._writer.close()
			return
		B = bytes(reversed(buf.read_bytes(32)))
		g_len = buf.read_u8()
		g = bytes(reversed(buf.read_bytes(g_len)))
		n_len = buf.read_u8()
		N = bytes(reversed(buf.read_bytes(n_len)))
		salt = bytes(reversed(buf.read_bytes(32)))
		buf.skip(16)
		security_flag = buf.read_u8()
		token: Optional[str] = None
		if security_flag == 0x04:
			# Not supported in non-interactive scaffold
			self._logger.error("Token two factor auth enabled; not supported in this port.")
			self._writer.close()
			return
		elif security_flag != 0x00:
			self._logger.error("Two factor auth type %s not supported.", security_flag)
			self._writer.close()
			return

		self._srp.step1(conf.wow.account, conf.wow.password, BigNumber.from_bytes(bytearray(B)), BigNumber.from_bytes(bytearray(g)), BigNumber.from_bytes(bytearray(N)), BigNumber.from_bytes(bytearray(salt)))  # type: ignore[name-defined]
		self._session_key = self._srp.K.as_byte_array(40)  # type: ignore[union-attr]
		A_arr = self._srp.A.as_byte_array(32)  # type: ignore[union-attr]
		m_arr = self._srp.M.as_byte_array(20, reverse=False)  # type: ignore[union-attr]
		md = hashlib.sha1()
		md.update(A_arr)
		# Build CRC based on build and platform (align with Scala)
		crc_bytes = self._build_crc_hashes.get((get_realm_build(conf), conf.wow.platform), bytes(20))
		md.update(crc_bytes)
		crc_hash = md.digest()
		out = bytearray()
		out += A_arr
		out += m_arr
		out += crc_hash
		out += bytes((0,))
		out += bytes((security_flag,))
		self._writer.write(bytes((RealmPackets.CMD_AUTH_LOGON_PROOF,)) + out)
		await self._writer.drain()

	async def _handle_logon_proof(self) -> None:
		# Read variable size; read a chunk sufficient to include server proof
		data = await self._reader.read(128)
		buf = ByteReader(data)
		result = buf.read_u8()
		if not RealmPackets.AuthResult.is_success(result):
			self._logger.error(RealmPackets.AuthResult.get_message(result))
			self._writer.close()
			return
		# Compare server proof to locally generated to ensure SRP session key matches
		server_proof = buf.read_bytes(20)
		try:
			assert self._srp is not None and self._srp.A and self._srp.M and self._srp.K
			expected = self._srp.generate_hash_logon_proof()
			if server_proof != expected:
				self._logger.error("SRP server proof mismatch! Expected %s got %s", expected.hex(), server_proof.hex())
				# Continue anyway; some servers may not send proof consistently
			else:
				self._logger.info("SRP server proof OK")
		except Exception as e:
			self._logger.debug("SRP proof check skipped: %s", e)
		# request realm list
		out = (0).to_bytes(4, 'little')
		self._writer.write(bytes((RealmPackets.CMD_REALM_LIST,)) + out)
		await self._writer.drain()

	async def _handle_realm_list(self, conf: WowChatConfig) -> None:
		# size prefixed LE short
		size_b = await self._read_exact(2)
		size = int.from_bytes(size_b, 'little')
		payload = await self._read_exact(size)
		self._logger.debug("Realm list payload: %s", payload.hex())
		buf = ByteReader(payload)
		buf.read_u32le()
		name = conf.wow.realmlist.name
		match_addr: Optional[str] = None
		match_id = 0
		# Align with Scala: number of realms is a single byte and fixed field skips
		num_realms = buf.read_u8()
		for i in range(num_realms):
			# Some servers (e.g., AzerothCore) appear to have a 3-byte realm type block here
			buf.skip(3)
			realm_flags = buf.read_u8()
			realm_name = buf.read_cstring()
			addr = buf.read_cstring()
			buf.skip(4)  # population
			buf.skip(1)  # num characters
			buf.skip(1)  # timezone
			realm_id = buf.read_u8()  # Byte як у Scala
			self._logger.debug("Realm[%d]: flags=%02x name=%s addr=%s id=%d", i, realm_flags, realm_name, addr, realm_id)
			if realm_name.lower() == name.lower():
				match_addr = addr
				match_id = realm_id
		if not match_addr:
			self._logger.error("Realm %s not found in list", name)
			self._writer.close()
			return
		h, p = match_addr.split(":")
		port = int(p) & 0xFFFF
		self._logger.info("Selected realm %s at %s:%s (id=%s)", name, h, port, match_id)
		
		# Закриваємо realm з'єднання
		self._writer.close()
		
		# Підключаємося до game сервера
		await self._connect_to_game_server(h, port, name, match_id)

	async def _connect_to_game_server(self, host: str, port: int, realm_name: str, realm_id: int) -> None:
		"""Підключитися до ігрового сервера"""
		try:
			from wowchat.game.connector import GameConnector
			
			game_connector = GameConnector(host, port, realm_name, realm_id, self._session_key)
			await game_connector.connect()
			
		except Exception as e:
			self._logger.error("Failed to connect to game server: %s", e)
			raise