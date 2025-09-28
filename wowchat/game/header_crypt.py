"""
Шифрування заголовків ігрових пакетів.

Портовано з JaNGOS проекту через Scala версію WoWChat.
"""
from __future__ import annotations

from typing import Optional


class GameHeaderCrypt:
    """Шифрування/розшифровка заголовків ігрових пакетів"""
    
    def __init__(self) -> None:
        self._initialized = False
        self._send_i = 0
        self._send_j = 0
        self._recv_i = 0
        self._recv_j = 0
        self._key: Optional[bytes] = None
    
    def decrypt(self, data: bytes) -> bytes:
        """Розшифрувати заголовок пакета"""
        if not self._initialized:
            return data
        
        result = bytearray(data)
        for i in range(len(result)):
            self._recv_i %= len(self._key)
            # Зберігаємо оригінальний байт для наступної ітерації
            original_byte = result[i]
            # Виконуємо розшифровку
            x = ((result[i] - self._recv_j) ^ self._key[self._recv_i]) & 0xFF
            self._recv_i += 1
            # Оновлюємо _recv_j ПІСЛЯ розшифровки
            self._recv_j = original_byte
            result[i] = x
        
        return bytes(result)
    
    def encrypt(self, data: bytes) -> bytes:
        """Зашифрувати заголовок пакета"""
        if not self._initialized:
            return data
        
        result = bytearray(data)
        for i in range(len(result)):
            self._send_i %= len(self._key)
            x = ((result[i] ^ self._key[self._send_i]) + self._send_j) & 0xFF
            self._send_i += 1
            result[i] = x
            self._send_j = x
        
        return bytes(result)
    
    def init(self, key: bytes) -> None:
        """Ініціалізувати шифрування з session key"""
        self._key = key
        self._send_i = 0
        self._send_j = 0
        self._recv_i = 0
        self._recv_j = 0
        self._initialized = True
    
    @property
    def is_initialized(self) -> bool:
        """Чи ініціалізовано шифрування"""
        return self._initialized
