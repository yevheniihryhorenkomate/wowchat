from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import struct
from typing import Optional

from wowchat.common.config import WowChatConfig
from wowchat.common.global_state import Global
from wowchat.game.packets import (
    CMSG_AUTH_CHALLENGE, CMSG_CHAR_ENUM, CMSG_PLAYER_LOGIN,
    SMSG_AUTH_CHALLENGE, SMSG_AUTH_RESPONSE, SMSG_CHAR_ENUM, 
    SMSG_LOGIN_VERIFY_WORLD, AuthResponseCodes
)
from wowchat.game.header_crypt_wotlk import GameHeaderCryptWotLK


class GameConnector:
    def __init__(self, host: str, port: int, realm_name: str, realm_id: int, session_key: bytes) -> None:
        self._host = host
        self._port = port
        self._realm_name = realm_name
        self._realm_id = realm_id
        self._session_key = session_key
        self._logger = logging.getLogger(__name__)
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._character_guid: Optional[int] = None
        self._header_crypt = GameHeaderCryptWotLK()
        self._in_world = False

    async def connect(self) -> None:
        """Підключитися до ігрового сервера"""
        self._logger.info("Connecting to game server %s:%s (realm: %s)", self._host, self._port, self._realm_name)
        
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
            self._logger.info("Successfully connected to game server!")
            
            # Запускаємо основний цикл обробки пакетів
            await self._game_loop()
            
        except Exception as e:
            self._logger.error("Failed to connect to game server: %s", e)
            raise

    async def _game_loop(self) -> None:
        """Основний цикл обробки ігрових пакетів"""
        try:
            while True:
                try:
                    # Читаємо заголовок пакета
                    header_size = 4
                    self._logger.debug("Attempting to read %d bytes for header", header_size)
                    header = await self._reader.readexactly(header_size)
                    if not header:
                        self._logger.info("Game server closed connection")
                        break
                    self._logger.debug("Read header: %s", header.hex())
                    
                    # Розшифровуємо заголовок якщо потрібно
                    if self._header_crypt.is_initialized:
                        self._logger.debug("Encrypted header: %s", header.hex())
                        header = self._header_crypt.decrypt(header)
                        self._logger.debug("Decrypted header: %s", header.hex())
                        
                        # WotLK може мати 5-байтний заголовок якщо розмір > 0x7FFF
                        if (header[0] & 0x80) == 0x80:
                            # Читаємо додатковий байт
                            extra_byte = await self._reader.readexactly(1)
                            if self._header_crypt.is_initialized:
                                extra_byte = self._header_crypt.decrypt(extra_byte)
                            
                            # Парсимо 5-байтний заголовок
                            size = (((header[0] & 0x7F) << 16) | ((header[1] & 0xFF) << 8) | (header[2] & 0xFF)) - 2
                            packet_id = ((extra_byte[0] & 0xFF) << 8) | (header[3] & 0xFF)
                        else:
                            # Парсимо 4-байтний заголовок
                            size = ((header[0] & 0xFF) << 8 | header[1] & 0xFF) - 2
                            packet_id = (header[3] & 0xFF) << 8 | header[2] & 0xFF
                    else:
                        # Нешифрований заголовок (big-endian size, little-endian ID)
                        size = struct.unpack('>H', header[:2])[0] - 2
                        packet_id = struct.unpack('<H', header[2:4])[0]
                    
                    # Читаємо дані пакета
                    if size > 0:
                        data = await self._reader.readexactly(size)
                    else:
                        data = b''
                    
                    self._logger.info("Received packet 0x%04X, size: %d", packet_id, size)
                    
                    # Обробляємо пакет
                    await self._handle_packet(packet_id, data)
                    
                except asyncio.IncompleteReadError as e:
                    self._logger.error("Incomplete read error: %s", e)
                    # Можливо сервер відключився після автентифікації
                    if self._header_crypt.is_initialized:
                        self._logger.info("Server may have disconnected after authentication")
                        # Спробуємо прочитати ще раз з невеликою затримкою
                        try:
                            await asyncio.sleep(0.1)
                            # Перевіряємо чи є дані в буфері
                            if hasattr(self._reader, '_buffer') and len(self._reader._buffer) > 0:
                                self._logger.info("Buffer contains %d bytes: %s", len(self._reader._buffer), self._reader._buffer.hex())
                            header = await asyncio.wait_for(self._reader.readexactly(4), timeout=1.0)
                            self._logger.info("Successfully read header after retry: %s", header.hex())
                            continue
                        except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                            self._logger.info("No more data available")
                    break
                except ConnectionResetError:
                    self._logger.info("Connection reset by server")
                    break
                except Exception as e:
                    self._logger.error("Unexpected error in game loop: %s", e)
                    break
                
        except asyncio.CancelledError:
            self._logger.info("Game loop cancelled")
        except Exception as e:
            self._logger.error("Error in game loop: %s", e)
        finally:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()

    async def _handle_packet(self, packet_id: int, data: bytes) -> None:
        """Обробка вхідних пакетів"""
        if packet_id == SMSG_AUTH_CHALLENGE:
            self._logger.info("Handling SMSG_AUTH_CHALLENGE")
            await self._handle_auth_challenge(data)
        elif packet_id == SMSG_AUTH_RESPONSE:
            self._logger.info("Handling SMSG_AUTH_RESPONSE")
            await self._handle_auth_response(data)
        elif packet_id == SMSG_CHAR_ENUM:
            self._logger.info("Handling SMSG_CHAR_ENUM")
            await self._handle_char_enum(data)
        elif packet_id == SMSG_LOGIN_VERIFY_WORLD:
            self._logger.info("Handling SMSG_LOGIN_VERIFY_WORLD")
            await self._handle_login_verify_world(data)
        else:
            self._logger.info("Unhandled packet: 0x%04X", packet_id)

    async def _handle_auth_challenge(self, data: bytes) -> None:
        """Обробка SMSG_AUTH_CHALLENGE"""
        self._logger.info("Received auth challenge")
        self._logger.info("Auth challenge data hex: %s", data.hex())
        
        # Парсимо дані (WotLK версія - пропускаємо 4 байти)
        server_seed = struct.unpack('>I', data[4:8])[0]  # Big-endian як у Scala readInt
        # Match Scala's Random.nextInt range (0..0x7FFFFFFF)
        client_seed = random.randint(0, 0x7FFFFFFF)
        self._logger.info("Server seed: 0x%08X, Client seed: 0x%08X", server_seed, client_seed)
        self._logger.info("Session key: %s", self._session_key.hex())
        
        # Створюємо відповідь (WotLK версія) - точно як у Scala
        response = bytearray()
        response.extend(struct.pack('<H', 0))  # Size placeholder
        response.extend(struct.pack('<I', Global.config.wow.gameBuild or 12340))  # Build
        response.extend(struct.pack('<I', 0))  # Unknown
        response.extend(Global.config.wow.account)  # Account
        response.append(0)  # Null terminator
        response.extend(struct.pack('>I', 0))  # WotLK - додаткове поле (big-endian)
        response.extend(struct.pack('>I', client_seed))  # Client seed (big-endian як у Scala рядок 44)
        response.extend(struct.pack('<I', 0))  # WotLK - додаткове поле (little-endian як у Scala рядок 45)
        response.extend(struct.pack('<I', 0))  # WotLK - додаткове поле (little-endian як у Scala рядок 46)
        response.extend(struct.pack('<I', self._realm_id))  # WotLK - realm ID (little-endian як у Scala рядок 47)
        response.extend(struct.pack('<Q', 3))  # WotLK - додаткове поле (little-endian як у Scala рядок 48)
        
        # Обчислюємо хеш - як у Scala: account, 4x00, client_seed (BE), server_seed (BE), session_key
        md = hashlib.sha1()
        md.update(Global.config.wow.account)
        md.update(b'\x00\x00\x00\x00')
        md.update(struct.pack('>I', client_seed))  # BE client_seed
        md.update(struct.pack('>I', server_seed))  # BE server_seed
        md.update(self._session_key)
        hash_result = md.digest()
        self._logger.debug("Hash input - account: %s, client_seed: 0x%08X, server_seed: 0x%08X, session_key: %s", 
                          Global.config.wow.account, client_seed, server_seed, self._session_key.hex())
        self._logger.debug("Hash result: %s", hash_result.hex())
        response.extend(hash_result)
        
        # Додаємо addonInfo (статичні дані для WotLK) - точно як у Scala версії
        addon_info = bytes([
            0x9E, 0x02, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xD2, 0xC1, 0x6A, 0xC3, 0x30, 0x0C, 0xC6, 0x71, 0xEF,
            0x29, 0x76, 0xE9, 0x9B, 0xEC, 0xB4, 0xB4, 0x50, 0xC2, 0xEA, 0xCB, 0xE2, 0x9E, 0x8B, 0x62, 0x7F,
            0x4B, 0x44, 0x6C, 0x39, 0x38, 0x4E, 0xB7, 0xF6, 0x3D, 0xFA, 0xBE, 0x65, 0xB7, 0x0D, 0x94, 0xF3,
            0x4F, 0x48, 0xF0, 0x47, 0xAF, 0xC6, 0x98, 0x26, 0xF2, 0xFD, 0x4E, 0x25, 0x5C, 0xDE, 0xFD, 0xC8,
            0xB8, 0x22, 0x41, 0xEA, 0xB9, 0x35, 0x2F, 0xE9, 0x7B, 0x77, 0x32, 0xFF, 0xBC, 0x40, 0x48, 0x97,
            0xD5, 0x57, 0xCE, 0xA2, 0x5A, 0x43, 0xA5, 0x47, 0x59, 0xC6, 0x3C, 0x6F, 0x70, 0xAD, 0x11, 0x5F,
            0x8C, 0x18, 0x2C, 0x0B, 0x27, 0x9A, 0xB5, 0x21, 0x96, 0xC0, 0x32, 0xA8, 0x0B, 0xF6, 0x14, 0x21,
            0x81, 0x8A, 0x46, 0x39, 0xF5, 0x54, 0x4F, 0x79, 0xD8, 0x34, 0x87, 0x9F, 0xAA, 0xE0, 0x01, 0xFD,
            0x3A, 0xB8, 0x9C, 0xE3, 0xA2, 0xE0, 0xD1, 0xEE, 0x47, 0xD2, 0x0B, 0x1D, 0x6D, 0xB7, 0x96, 0x2B,
            0x6E, 0x3A, 0xC6, 0xDB, 0x3C, 0xEA, 0xB2, 0x72, 0x0C, 0x0D, 0xC9, 0xA4, 0x6A, 0x2B, 0xCB, 0x0C,
            0xAF, 0x1F, 0x6C, 0x2B, 0x52, 0x97, 0xFD, 0x84, 0xBA, 0x95, 0xC7, 0x92, 0x2F, 0x59, 0x95, 0x4F,
            0xE2, 0xA0, 0x82, 0xFB, 0x2D, 0xAA, 0xDF, 0x73, 0x9C, 0x60, 0x49, 0x68, 0x80, 0xD6, 0xDB, 0xE5,
            0x09, 0xFA, 0x13, 0xB8, 0x42, 0x01, 0xDD, 0xC4, 0x31, 0x6E, 0x31, 0x0B, 0xCA, 0x5F, 0x7B, 0x7B,
            0x1C, 0x3E, 0x9E, 0xE1, 0x93, 0xC8, 0x8D
        ])
        response.extend(addon_info)
        
        # Встановлюємо розмір в response (як у Scala) - 0, розмір встановлюється пізніше
        struct.pack_into('<H', response, 0, 0)
        
        # Ініціалізуємо шифрування заголовків ПЕРЕД відправкою автентифікації (як у Scala)
        self._header_crypt.init(self._session_key)
        self._logger.debug("Header encryption initialized")
        
        # Відправляємо відповідь (розмір - big-endian, ID - little-endian)
        # CMSG_AUTH_CHALLENGE НЕ ШИФРУЄТЬСЯ (як у Scala версії)
        header_size = 4
        total_size = len(response) + header_size - 2
        packet = struct.pack('>H', total_size) + struct.pack('<H', CMSG_AUTH_CHALLENGE) + response
        
        self._logger.info("Sending CMSG_AUTH_CHALLENGE, size: %d", len(packet))
        self._logger.info("Packet hex: %s", packet.hex())
        self._logger.info("Packet data hex: %s", response.hex())
        self._writer.write(packet)
        await self._writer.drain()

    async def _handle_auth_response(self, data: bytes) -> None:
        """Обробка SMSG_AUTH_RESPONSE"""
        if not data:
            self._logger.error("Empty auth response")
            return
            
        code = data[0]
        self._logger.info("Auth response code: 0x%02X", code)
        
        if AuthResponseCodes.is_success(code):
            self._logger.info("Successfully authenticated!")
            # Запитуємо список персонажів
            await self._send_char_enum()
        else:
            self._logger.error("Authentication failed: %s", AuthResponseCodes.get_message(code))
            await self.disconnect()

    async def _send_char_enum(self) -> None:
        """Відправити запит на список персонажів"""
        packet = struct.pack('>H', 4) + struct.pack('<H', CMSG_CHAR_ENUM)
        
        # Шифруємо заголовок якщо потрібно
        if self._header_crypt.is_initialized:
            header = packet[:4]
            encrypted_header = self._header_crypt.encrypt(header)
            packet = encrypted_header + packet[4:]
        
        self._writer.write(packet)
        await self._writer.drain()
        self._logger.info("Requested character list")

    async def _handle_char_enum(self, data: bytes) -> None:
        """Обробка SMSG_CHAR_ENUM"""
        if not data:
            self._logger.error("Empty char enum response")
            return
            
        # Парсимо кількість персонажів
        char_count = data[0]
        self._logger.info("Found %d characters", char_count)
        
        if char_count == 0:
            self._logger.error("No characters found!")
            return
        
        # Шукаємо нашого персонажа
        target_name = Global.config.wow.character.lower()
        offset = 1
        
        for i in range(char_count):
            if offset >= len(data):
                break
                
            # Читаємо GUID
            guid = struct.unpack('<Q', data[offset:offset+8])[0]
            offset += 8
            
            # Читаємо ім'я
            name_end = data.find(b'\x00', offset)
            if name_end == -1:
                break
            name = data[offset:name_end].decode('utf-8', errors='ignore')
            offset = name_end + 1
            
            # Пропускаємо решту даних персонажа
            offset += 1  # race
            offset += 1  # class
            offset += 1  # gender
            offset += 1  # skin
            offset += 1  # face
            offset += 1  # hair style
            offset += 1  # hair color
            offset += 1  # facial hair
            offset += 1  # level
            offset += 4  # zone
            offset += 4  # map
            offset += 12  # x, y, z
            offset += 4  # guild guid
            offset += 4  # character flags
            offset += 1  # first login
            offset += 12  # pet info
            offset += 19 * 5  # equipment info
            offset += 5  # first bag display info
            
            if name.lower() == target_name:
                self._logger.info("Found character: %s (GUID: %d)", name, guid)
                self._character_guid = guid
                await self._send_player_login()
                return
        
        self._logger.error("Character '%s' not found!", Global.config.wow.character)

    async def _send_player_login(self) -> None:
        """Відправити запит на вхід на персонажа"""
        if not self._character_guid:
            self._logger.error("No character GUID available")
            return
            
        packet = struct.pack('>H', 12) + struct.pack('<H', CMSG_PLAYER_LOGIN) + struct.pack('<Q', self._character_guid)
        
        # Шифруємо заголовок якщо потрібно
        if self._header_crypt.is_initialized:
            header = packet[:4]
            encrypted_header = self._header_crypt.encrypt(header)
            packet = encrypted_header + packet[4:]
        
        self._writer.write(packet)
        await self._writer.drain()
        self._logger.info("Requesting login for character GUID: %d", self._character_guid)

    async def _handle_login_verify_world(self, data: bytes) -> None:
        """Обробка SMSG_LOGIN_VERIFY_WORLD"""
        if self._in_world:
            return
            
        self._logger.info("Successfully joined the world!")
        self._in_world = True
        # Тут можна додати логіку для обробки повідомлень чату тощо

    async def disconnect(self) -> None:
        """Відключитися від ігрового сервера"""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._logger.info("Disconnected from game server")
