from __future__ import annotations


class RealmPackets:
	CMD_AUTH_LOGON_CHALLENGE = 0x00
	CMD_AUTH_LOGON_PROOF = 0x01
	CMD_REALM_LIST = 0x10

	class AuthResult:
		WOW_SUCCESS = 0x00
		WOW_FAIL_BANNED = 0x03
		WOW_FAIL_UNKNOWN_ACCOUNT = 0x04
		WOW_FAIL_INCORRECT_PASSWORD = 0x05
		WOW_FAIL_ALREADY_ONLINE = 0x06
		WOW_FAIL_NO_TIME = 0x07
		WOW_FAIL_DB_BUSY = 0x08
		WOW_FAIL_VERSION_INVALID = 0x09
		WOW_FAIL_VERSION_UPDATE = 0x0A
		WOW_FAIL_INVALID_SERVER = 0x0B
		WOW_FAIL_SUSPENDED = 0x0C
		WOW_FAIL_FAIL_NOACCESS = 0x0D
		WOW_SUCCESS_SURVEY = 0x0E
		WOW_FAIL_PARENTCONTROL = 0x0F
		WOW_FAIL_LOCKED_ENFORCED = 0x10
		WOW_FAIL_TRIAL_ENDED = 0x11
		WOW_FAIL_USE_BATTLENET = 0x12
		WOW_FAIL_ANTI_INDULGENCE = 0x13
		WOW_FAIL_EXPIRED = 0x14
		WOW_FAIL_NO_GAME_ACCOUNT = 0x15
		WOW_FAIL_CHARGEBACK = 0x16
		WOW_FAIL_INTERNET_GAME_ROOM_WITHOUT_BNET = 0x17
		WOW_FAIL_GAME_ACCOUNT_LOCKED = 0x18
		WOW_FAIL_UNLOCKABLE_LOCK = 0x19
		WOW_FAIL_CONVERSION_REQUIRED = 0x20
		WOW_FAIL_DISCONNECTED = 0xFF

		@staticmethod
		def is_success(code: int) -> bool:
			return code in (RealmPackets.AuthResult.WOW_SUCCESS, RealmPackets.AuthResult.WOW_SUCCESS_SURVEY)

		@staticmethod
		def get_message(code: int) -> str:
			m = {
				RealmPackets.AuthResult.WOW_SUCCESS: "Success!",
				RealmPackets.AuthResult.WOW_SUCCESS_SURVEY: "Success!",
				RealmPackets.AuthResult.WOW_FAIL_BANNED: "Your account has been banned!",
				RealmPackets.AuthResult.WOW_FAIL_INCORRECT_PASSWORD: "Incorrect username or password!",
				RealmPackets.AuthResult.WOW_FAIL_UNKNOWN_ACCOUNT: "Login failed. Wait a moment and try again!",
				RealmPackets.AuthResult.WOW_FAIL_ALREADY_ONLINE: "Your account is already online. Wait a moment and try again!",
				RealmPackets.AuthResult.WOW_FAIL_VERSION_INVALID: "Invalid game version for this server!",
				RealmPackets.AuthResult.WOW_FAIL_VERSION_UPDATE: "Invalid game version for this server!",
				RealmPackets.AuthResult.WOW_FAIL_SUSPENDED: "Your account has been suspended!",
				RealmPackets.AuthResult.WOW_FAIL_FAIL_NOACCESS: "Login failed! You do not have access to this server!",
			}
			return m.get(code, f"Failed to login to realm server! Error code: {code:02X}")