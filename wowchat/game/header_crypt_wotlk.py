"""
Шифрування заголовків ігрових пакетів для WotLK.

Використовує RC4 з HMAC-SHA1 для генерації ключів.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Optional


class RC4:
    """RC4 шифр"""
    
    def __init__(self, key: bytes) -> None:
        self.sbox_length = 256
        self.sbox = self._init_sbox(key)
        self.i = 0
        self.j = 0
    
    def _init_sbox(self, key: bytes) -> list[int]:
        """Ініціалізувати S-box"""
        sbox = list(range(self.sbox_length))
        j = 0
        
        for i in range(self.sbox_length):
            j = (j + sbox[i] + key[i % len(key)]) % self.sbox_length
            sbox[i], sbox[j] = sbox[j], sbox[i]
        
        return sbox
    
    def crypt_to_byte_array(self, data: bytes) -> bytes:
        """Зашифрувати/розшифрувати дані"""
        result = bytearray()
        
        for byte in data:
            self.i = (self.i + 1) % self.sbox_length
            self.j = (self.j + self.sbox[self.i]) % self.sbox_length
            self.sbox[self.i], self.sbox[self.j] = self.sbox[self.j], self.sbox[self.i]
            rand = self.sbox[(self.sbox[self.i] + self.sbox[self.j]) % self.sbox_length]
            result.append(rand ^ byte)
        
        return bytes(result)


class GameHeaderCryptWotLK:
    """Шифрування заголовків для WotLK"""
    
    # Константи з Scala версії
    SERVER_HMAC_SEED = bytes([
        0xCC, 0x98, 0xAE, 0x04, 0xE8, 0x97, 0xEA, 0xCA, 
        0x12, 0xDD, 0xC0, 0x93, 0x42, 0x91, 0x53, 0x57
    ])
    
    CLIENT_HMAC_SEED = bytes([
        0xC2, 0xB3, 0x72, 0x3C, 0xC6, 0xAE, 0xD9, 0xB5, 
        0x34, 0x3C, 0x53, 0xEE, 0x2F, 0x43, 0x67, 0xCE
    ])
    
    def __init__(self) -> None:
        self._initialized = False
        self._client_crypt: Optional[RC4] = None
        self._server_crypt: Optional[RC4] = None
    
    def decrypt(self, data: bytes) -> bytes:
        """Розшифрувати заголовок пакета"""
        if not self._initialized:
            return data
        
        return self._server_crypt.crypt_to_byte_array(data)
    
    def encrypt(self, data: bytes) -> bytes:
        """Зашифрувати заголовок пакета"""
        if not self._initialized:
            return data
        
        return self._client_crypt.crypt_to_byte_array(data)
    
    def init(self, key: bytes) -> None:
        """Ініціалізувати шифрування з session key"""
        # Генеруємо ключі для сервера та клієнта
        server_key = hmac.new(self.SERVER_HMAC_SEED, key, hashlib.sha1).digest()
        client_key = hmac.new(self.CLIENT_HMAC_SEED, key, hashlib.sha1).digest()
        
        # Створюємо RC4 шифри
        self._server_crypt = RC4(server_key)
        self._client_crypt = RC4(client_key)
        
        # Ініціалізуємо шифри (пропускаємо перші 1024 байти)
        self._server_crypt.crypt_to_byte_array(bytes(1024))
        self._client_crypt.crypt_to_byte_array(bytes(1024))
        
        self._initialized = True
    
    @property
    def is_initialized(self) -> bool:
        """Чи ініціалізовано шифрування"""
        return self._initialized
