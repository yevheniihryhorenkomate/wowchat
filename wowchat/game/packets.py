"""Game packets and constants for WoW protocol"""

# Game packet IDs
CMSG_CHAR_ENUM = 0x37
SMSG_CHAR_ENUM = 0x3B
CMSG_PLAYER_LOGIN = 0x3D
CMSG_LOGOUT_REQUEST = 0x4B
CMSG_NAME_QUERY = 0x50
SMSG_NAME_QUERY = 0x51
CMSG_GUILD_QUERY = 0x54
SMSG_GUILD_QUERY = 0x55
CMSG_WHO = 0x62
SMSG_WHO = 0x63
CMSG_GUILD_ROSTER = 0x89
SMSG_GUILD_ROSTER = 0x8A
SMSG_GUILD_EVENT = 0x92
CMSG_MESSAGECHAT = 0x95
SMSG_MESSAGECHAT = 0x96
CMSG_JOIN_CHANNEL = 0x97
SMSG_CHANNEL_NOTIFY = 0x99

SMSG_NOTIFICATION = 0x01CB
CMSG_PING = 0x01DC
SMSG_AUTH_CHALLENGE = 0x01EC
CMSG_AUTH_CHALLENGE = 0x01ED
SMSG_AUTH_RESPONSE = 0x01EE
SMSG_LOGIN_VERIFY_WORLD = 0x0236
SMSG_SERVER_MESSAGE = 0x0291

SMSG_WARDEN_DATA = 0x02E6
CMSG_WARDEN_DATA = 0x02E7

SMSG_INVALIDATE_PLAYER = 0x031C

# TBC/WotLK only
SMSG_TIME_SYNC_REQ = 0x0390
CMSG_TIME_SYNC_RESP = 0x0391


class AuthResponseCodes:
    AUTH_OK = 0x0C
    AUTH_FAILED = 0x0D
    AUTH_REJECT = 0x0E
    AUTH_BAD_SERVER_PROOF = 0x0F
    AUTH_UNAVAILABLE = 0x10
    AUTH_SYSTEM_ERROR = 0x11
    AUTH_BILLING_ERROR = 0x12
    AUTH_BILLING_EXPIRED = 0x13
    AUTH_VERSION_MISMATCH = 0x14
    AUTH_UNKNOWN_ACCOUNT = 0x15
    AUTH_INCORRECT_PASSWORD = 0x16
    AUTH_SESSION_EXPIRED = 0x17
    AUTH_SERVER_SHUTTING_DOWN = 0x18
    AUTH_ALREADY_LOGGING_IN = 0x19
    AUTH_LOGIN_SERVER_NOT_FOUND = 0x1A
    AUTH_WAIT_QUEUE = 0x1B
    AUTH_BANNED = 0x1C
    AUTH_ALREADY_ONLINE = 0x1D
    AUTH_NO_TIME = 0x1E
    AUTH_DB_BUSY = 0x1F
    AUTH_SUSPENDED = 0x20
    AUTH_PARENTAL_CONTROL = 0x21
    AUTH_LOCKED_ENFORCED = 0x22

    @staticmethod
    def get_message(code: int) -> str:
        messages = {
            AuthResponseCodes.AUTH_OK: "Success!",
            AuthResponseCodes.AUTH_UNKNOWN_ACCOUNT: "Incorrect username or password!",
            AuthResponseCodes.AUTH_INCORRECT_PASSWORD: "Incorrect username or password!",
            AuthResponseCodes.AUTH_VERSION_MISMATCH: "Invalid game version for this server!",
            AuthResponseCodes.AUTH_BANNED: "Your account has been banned!",
            AuthResponseCodes.AUTH_ALREADY_LOGGING_IN: "Your account is already online!",
            AuthResponseCodes.AUTH_ALREADY_ONLINE: "Your account is already online!",
            AuthResponseCodes.AUTH_SUSPENDED: "Your account has been suspended!",
        }
        return messages.get(code, f"Failed to login to game server! Error code: 0x{code:02X}")

    @staticmethod
    def is_success(code: int) -> bool:
        return code == AuthResponseCodes.AUTH_OK
