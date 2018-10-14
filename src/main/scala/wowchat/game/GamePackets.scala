package wowchat.game

import wowchat.common.{WowChatConfig, WowExpansion}
import io.netty.util.AttributeKey

trait GamePackets {

  val CRYPT: AttributeKey[GameHeaderCrypt] = AttributeKey.valueOf("CRYPT")

  val CMSG_CHAR_ENUM = 0x37
  val SMSG_CHAR_ENUM = 0x3B
  val CMSG_PLAYER_LOGIN = 0x3D
  val CMSG_LOGOUT_REQUEST = 0x4B
  val CMSG_NAME_QUERY = 0x50
  val SMSG_NAME_QUERY = 0x51
  val CMSG_WHO = 0x62
  val SMSG_WHO = 0x63
  val CMSG_GUILD_ROSTER = 0x89
  val SMSG_GUILD_ROSTER = 0x8A
  val SMSG_GUILD_EVENT = 0x92
  val CMSG_CHATMESSAGE = 0x95
  val SMSG_CHATMESSAGE = 0x96
  val CMSG_JOIN_CHANNEL = 0x97
  val SMSG_CHANNEL_NOTIFY = 0x99

  val SMSG_NOTIFICATION = 0x01CB
  val CMSG_PING = 0x01DC
  val SMSG_AUTH_CHALLENGE = 0x01EC
  val CMSG_AUTH_CHALLENGE = 0x01ED
  val SMSG_AUTH_RESPONSE = 0x01EE
  val SMSG_LOGIN_VERIFY_WORLD = 0x0236

  val SMSG_WARDEN_DATA = 0x02E6
  val CMSG_WARDEN_DATA = 0x02E7

  // tbc/wotlk only
  val SMSG_TIME_SYNC_REQ = 0x0390
  val CMSG_TIME_SYNC_RESP = 0x0391

  // cataclysm
  val WOW_CONNECTION = 0x4F57 // same hack as in mangos :D

  object ChatEvents {
    // err...
    lazy val CHAT_MSG_SAY = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x00.toByte else 0x01.toByte
    lazy val CHAT_MSG_GUILD = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x03.toByte else 0x04.toByte
    lazy val CHAT_MSG_OFFICER = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x04.toByte else 0x05.toByte
    lazy val CHAT_MSG_YELL = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x05.toByte else 0x06.toByte
    lazy val CHAT_MSG_WHISPER = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x06.toByte else 0x07.toByte
    lazy val CHAT_MSG_EMOTE = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x08.toByte else 0x0A.toByte
    lazy val CHAT_MSG_TEXT_EMOTE = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x09.toByte else 0x0B.toByte
    lazy val CHAT_MSG_CHANNEL = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x0E.toByte else 0x11.toByte
    lazy val CHAT_MSG_SYSTEM = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x0A.toByte else 0x00.toByte
    lazy val CHAT_MSG_CHANNEL_JOIN = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x0F.toByte else 0x12.toByte
    lazy val CHAT_MSG_CHANNEL_LEAVE = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x10.toByte else 0x13.toByte
    lazy val CHAT_MSG_CHANNEL_LIST = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x11.toByte else 0x14.toByte
    lazy val CHAT_MSG_CHANNEL_NOTICE = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x12.toByte else 0x15.toByte
    lazy val CHAT_MSG_CHANNEL_NOTICE_USER = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) 0x13.toByte else 0x16.toByte

    def parse(tp: String): Byte = {
      (tp.toLowerCase match {
        case "system" => CHAT_MSG_SYSTEM
        case "say" => CHAT_MSG_SAY
        case "guild" => CHAT_MSG_GUILD
        case "officer" => CHAT_MSG_OFFICER
        case "yell" => CHAT_MSG_YELL
        case "emote" => CHAT_MSG_EMOTE
        case "channel" | "custom" => CHAT_MSG_CHANNEL
        case _ => -1
      }).toByte
    }

    def valueOf(tp: Byte): String = {
      tp match {
        case CHAT_MSG_SAY => "Say"
        case CHAT_MSG_GUILD => "Guild"
        case CHAT_MSG_OFFICER => "Officer"
        case CHAT_MSG_YELL => "Yell"
        case CHAT_MSG_WHISPER => "Whisper"
        case CHAT_MSG_EMOTE | CHAT_MSG_TEXT_EMOTE => "Emote"
        case CHAT_MSG_CHANNEL => "Channel"
        case CHAT_MSG_SYSTEM => "System"
        case _ => "Unknown"
      }
    }
  }

  object GuildEvents {
    val GE_JOINED = 0x03
    val GE_LEFT = 0x04
    val GE_REMOVED = 0x05
    val GE_SIGNED_ON = 0x0C
    val GE_SIGNED_OFF = 0x0D
  }

  object Races {
    val RACE_HUMAN = 0x01
    val RACE_ORC = 0x02
    val RACE_DWARF = 0x03
    val RACE_NIGHTELF = 0x04
    val RACE_UNDEAD = 0x05
    val RACE_TAUREN = 0x06
    val RACE_GNOME = 0x07
    val RACE_TROLL = 0x08
    val RACE_BLOODELF = 0x0A
    val RACE_DRAENEI = 0x0B

    def getLanguage(race: Byte): Byte = {
      race match {
        case RACE_ORC | RACE_UNDEAD | RACE_TAUREN | RACE_TROLL | RACE_BLOODELF => 0x01 // orcish
        case _ => 0x07 // common
      }
    }

    def valueOf(charClass: Byte): String = {
      charClass match {
        case RACE_HUMAN => "Human"
        case RACE_ORC => "Orc"
        case RACE_DWARF => "Dwarf"
        case RACE_NIGHTELF => "Night Elf"
        case RACE_UNDEAD => "Undead"
        case RACE_TAUREN => "Tauren"
        case RACE_GNOME => "Gnome"
        case RACE_TROLL => "Troll"
        case RACE_BLOODELF => "Blood Elf"
        case RACE_DRAENEI => "Draenei"
        case _ => "Unknown"
      }
    }
  }

  object Classes {
    val CLASS_WARRIOR = 0x01
    val CLASS_PALADIN = 0x02
    val CLASS_HUNTER = 0x03
    val CLASS_ROGUE = 0x04
    val CLASS_PRIEST = 0x05
    val CLASS_SHAMAN = 0x07
    val CLASS_MAGE = 0x08
    val CLASS_WARLOCK = 0x09
    val CLASS_DRUID = 0x0B

    def valueOf(charClass: Byte): String = {
      charClass match {
        case CLASS_WARRIOR => "Warrior"
        case CLASS_PALADIN => "Paladin"
        case CLASS_HUNTER => "Hunter"
        case CLASS_ROGUE => "Rogue"
        case CLASS_PRIEST => "Priest"
        case CLASS_SHAMAN => "Shaman"
        case CLASS_MAGE => "Mage"
        case CLASS_WARLOCK => "Warlock"
        case CLASS_DRUID => "Druid"
        case _ => "Unknown"
      }
    }
  }

  object Genders {
    val GENDER_MALE = 0
    val GENDER_FEMALE = 1
    val GENDER_NONE = 2

    def valueOf(gender: Byte): String = {
      gender match {
        case GENDER_MALE => "Male"
        case GENDER_FEMALE => "Female"
        case _ => "Unknown"
      }
    }
  }

  object AuthResponseCodes {
    val AUTH_OK = 0x0C
    val AUTH_FAILED = 0x0D
    val AUTH_REJECT = 0x0E
    val AUTH_BAD_SERVER_PROOF = 0x0F
    val AUTH_UNAVAILABLE = 0x10
    val AUTH_SYSTEM_ERROR = 0x11
    val AUTH_BILLING_ERROR = 0x12
    val AUTH_BILLING_EXPIRED = 0x13
    val AUTH_VERSION_MISMATCH = 0x14
    val AUTH_UNKNOWN_ACCOUNT = 0x15
    val AUTH_INCORRECT_PASSWORD = 0x16
    val AUTH_SESSION_EXPIRED = 0x17
    val AUTH_SERVER_SHUTTING_DOWN = 0x18
    val AUTH_ALREADY_LOGGING_IN = 0x19
    val AUTH_LOGIN_SERVER_NOT_FOUND = 0x1A
    val AUTH_WAIT_QUEUE = 0x1B
    val AUTH_BANNED = 0x1C
    val AUTH_ALREADY_ONLINE = 0x1D
    val AUTH_NO_TIME = 0x1E
    val AUTH_DB_BUSY = 0x1F
    val AUTH_SUSPENDED = 0x20
    val AUTH_PARENTAL_CONTROL = 0x21

    def getMessage(authResult: Int): String = {
      authResult match {
        case AUTH_OK => "Success!"
        case AUTH_UNKNOWN_ACCOUNT | AUTH_INCORRECT_PASSWORD => "Incorrect username or password!"
        case AUTH_VERSION_MISMATCH => "Invalid game version for this server!"
        case AUTH_BANNED => "Your account has been banned!"
        case AUTH_ALREADY_LOGGING_IN | AUTH_ALREADY_ONLINE => "Your account is already online! Log it off or wait a minute if already logging off."
        case AUTH_SUSPENDED => "Your account has been suspended!"
        case x => f"Failed to login! Error code: $x%02X"
      }
    }
  }
}
