package wowchat.realm

import wowchat.common._
import com.typesafe.scalalogging.StrictLogging
import io.netty.buffer.{ByteBuf, PooledByteBufAllocator}
import io.netty.channel.{ChannelHandlerContext, ChannelInboundHandlerAdapter}

private[realm] case class RealmList(name: String, address: String, realmId: Byte)

class RealmPacketHandler(realmConnectionCallback: RealmConnectionCallback)
  extends ChannelInboundHandlerAdapter with StrictLogging {

  private val srpClient = new SRPClient
  private var ctx: Option[ChannelHandlerContext] = None
  private var expectedDisconnect = false
  private var sessionKey: Array[Byte] = _

  override def channelInactive(ctx: ChannelHandlerContext): Unit = {
    if (!expectedDisconnect) {
      realmConnectionCallback.disconnected
    }
    super.channelInactive(ctx)
  }

  override def channelActive(ctx: ChannelHandlerContext): Unit = {
    logger.info(s"Connected! Sending account login information...")
    this.ctx = Some(ctx)
    val version = WowChatConfig.getVersion.split("\\.").map(_.toByte)
    val accountConfig = Global.config.wow.account.toUpperCase
    val platformString = Global.config.wow.platform match {
      case Platform.Windows => "Win"
      case Platform.Mac => "OSX"
    }
    val localeString = Global.config.wow.locale

    val byteBuf = PooledByteBufAllocator.DEFAULT.buffer(50, 100)

    // seems to be 3 for vanilla and 8 for bc/wotlk
    if (WowChatConfig.getExpansion == WowExpansion.Vanilla) {
      byteBuf.writeByte(3)
    } else {
      byteBuf.writeByte(8)
    }
    byteBuf.writeShortLE(30 + accountConfig.length) // size
    byteBuf.writeIntLE(ByteUtils.stringToInt("WoW"))
    byteBuf.writeByte(version(0))
    byteBuf.writeByte(version(1))
    byteBuf.writeByte(version(2))
    byteBuf.writeShortLE(WowChatConfig.getBuild)
    byteBuf.writeIntLE(ByteUtils.stringToInt("x86"))
    byteBuf.writeIntLE(ByteUtils.stringToInt(platformString))
    byteBuf.writeIntLE(ByteUtils.stringToInt(localeString))
    byteBuf.writeIntLE(0)
    byteBuf.writeByte(127)
    byteBuf.writeByte(0)
    byteBuf.writeByte(0)
    byteBuf.writeByte(1)
    byteBuf.writeByte(accountConfig.length)
    byteBuf.writeBytes(accountConfig.getBytes)

    ctx.writeAndFlush(Packet(RealmPackets.CMD_AUTH_LOGON_CHALLENGE, byteBuf))

    super.channelActive(ctx)
  }

  override def channelRead(ctx: ChannelHandlerContext, msg: Any): Unit = {
    msg match {
      case msg: Packet =>
        msg.id match {
          case RealmPackets.CMD_AUTH_LOGON_CHALLENGE => handle_CMD_AUTH_LOGON_CHALLENGE(msg)
          case RealmPackets.CMD_AUTH_LOGON_PROOF => handle_CMD_AUTH_LOGON_PROOF(msg)
          case RealmPackets.CMD_REALM_LIST => handle_CMD_REALM_LIST(msg)
        }
        msg.byteBuf.release
      case msg =>
        logger.error(s"Packet is instance of ${msg.getClass}")
    }
  }

  private def handle_CMD_AUTH_LOGON_CHALLENGE(msg: Packet): Unit = {
    val error = msg.byteBuf.readByte // ?
    val result = msg.byteBuf.readByte
    if (!RealmPackets.AuthResult.isSuccess(result)) {
      logger.error(RealmPackets.AuthResult.getMessage(result))
      ctx.get.close
      realmConnectionCallback.error
      return
    }

    val B = toArray(msg.byteBuf, 32)
    val gLength = msg.byteBuf.readByte
    val g = toArray(msg.byteBuf, gLength)
    val nLength = msg.byteBuf.readByte
    val n = toArray(msg.byteBuf, nLength)
    val salt = toArray(msg.byteBuf, 32)
    val unk3 = toArray(msg.byteBuf, 16)
    val securityFlag = msg.byteBuf.readByte

    srpClient.step1(
      Global.config.wow.account.toUpperCase,
      Global.config.wow.password,
      BigNumber(B),
      BigNumber(g),
      BigNumber(n),
      BigNumber(salt)
    )

    sessionKey = srpClient.K.asByteArray()

    val ret = PooledByteBufAllocator.DEFAULT.buffer(74, 74)
    ret.writeBytes(srpClient.A.asByteArray(32))
    ret.writeBytes(srpClient.M.asByteArray(20, false))
    ret.writeBytes(srpClient.M.asByteArray(20, false))
    ret.writeByte(0)
    ret.writeByte(0)

    ctx.get.writeAndFlush(Packet(RealmPackets.CMD_AUTH_LOGON_PROOF, ret))
  }

  private def handle_CMD_AUTH_LOGON_PROOF(msg: Packet): Unit = {
    val result = msg.byteBuf.readByte

    if (!RealmPackets.AuthResult.isSuccess(result)) {
      logger.error(RealmPackets.AuthResult.getMessage(result))
      expectedDisconnect = true
      ctx.get.close
      if (result == RealmPackets.AuthResult.WOW_FAIL_UNKNOWN_ACCOUNT) {
        // seems sometimes this error happens even on a legit connect. so just run regular reconnect loop
        realmConnectionCallback.disconnected
      } else {
        if (result == RealmPackets.AuthResult.WOW_FAIL_VERSION_INVALID && Global.config.wow.platform == Platform.Mac) {
          logger.error(
            s"It is likely server ${Global.config.wow.realmlist.host} is blocking logins from Mac clients. " +
            "You can try using platform=Windows but the bot will disconnect soon after login if Warden anti-cheat is enabled."
          )
        }
        realmConnectionCallback.error
      }
      return
    }

    val proof = toArray(msg.byteBuf, 20, false)
    if (!proof.sameElements(srpClient.generateHashLogonProof)) {
      logger.error("Logon proof generated by client and server differ. Something is very wrong! Will try to reconnect in a moment.")
      expectedDisconnect = true
      ctx.get.close
      // Also sometimes happens on a legit connect.
      realmConnectionCallback.disconnected
      return
    }

    val accountFlag = msg.byteBuf.readIntLE

    // ask for realm list
    logger.info(s"Successfully logged into realm server. Looking for realm ${Global.config.wow.realmlist.name}")
    val ret = PooledByteBufAllocator.DEFAULT.buffer(4, 4)
    ret.writeIntLE(0)
    ctx.get.writeAndFlush(Packet(RealmPackets.CMD_REALM_LIST, ret))
  }

  private def handle_CMD_REALM_LIST(msg: Packet): Unit = {
    val configRealm = Global.config.wow.realmlist.name

    val parsedRealmList = parseRealmList(msg)
    val realms = parsedRealmList
      .filter {
        case RealmList(name, _, _) => name.equalsIgnoreCase(configRealm)
      }

    if (realms.isEmpty) {
      logger.error(s"Realm $configRealm not found!")
      logger.error(s"${parsedRealmList.length} possible realms:")
      parsedRealmList.foreach(realm => logger.error(realm.name))
    } else if (realms.length > 1) {
      logger.error("Too many realms returned. Something is very wrong! This should never happen.")
    } else {
      val splt = realms.head.address.split(":")
      val port = splt(1).toInt & 0xFFFF // some servers "overflow" the port on purpose to dissuade rudimentary bots
      realmConnectionCallback.success(splt(0), port, realms.head.name, realms.head.realmId, sessionKey)
    }
    expectedDisconnect = true
    ctx.get.close
  }

  protected def parseRealmList(msg: Packet): Seq[RealmList] = {
    msg.byteBuf.readIntLE // unknown
    val numRealms = msg.byteBuf.readByte

    (0 until numRealms).map(i => {
      msg.byteBuf.skipBytes(4) // realm type (pvp/pve)
      val realmFlags = msg.byteBuf.readByte // realm flags (offline/recommended/for newbs)
      val name = if ((realmFlags & 0x04) == 0x04) {
        // On Vanilla MaNGOS, there is some string manipulation to insert the build information into the name itself
        // if realm flags specify to do so. But that is counter-intuitive to matching the config, so let's remove it.
        msg.readString.replaceAll(" \\(\\d+,\\d+,\\d+\\)", "")
      } else {
        msg.readString
      }
      val address = msg.readString
      msg.byteBuf.skipBytes(4) // population
      msg.byteBuf.skipBytes(1) // num characters
      msg.byteBuf.skipBytes(1) // timezone
      val realmId = msg.byteBuf.readByte

      RealmList(name, address, realmId)
    })
  }

  // Helper functions
  private def toArray(byteBuf: ByteBuf, size: Int, reverse: Boolean = true): Array[Byte] = {
    val ret = Array.newBuilder[Byte]
    (0 until size).foreach(_ => ret += byteBuf.readByte)
    if (reverse) {
      ret.result().reverse
    } else {
      ret.result()
    }
  }
}
