package wowchat.realm

import java.net.InetSocketAddress
import java.util.concurrent.TimeUnit

import wowchat.common._
import com.typesafe.scalalogging.StrictLogging
import io.netty.bootstrap.Bootstrap
import io.netty.channel.socket.SocketChannel
import io.netty.channel.socket.nio.NioSocketChannel
import io.netty.channel.{Channel, ChannelInitializer, ChannelOption}
import io.netty.handler.timeout.IdleStateHandler
import io.netty.util.concurrent.Future

import scala.util.Try

class RealmConnector(realmConnectionCallback: RealmConnectionCallback) extends StrictLogging {

  private var channel: Option[Channel] = None

  def connect: Unit = {
    logger.info(s"Connecting to realm server ${Global.config.wow.realmlist.host}:${Global.config.wow.realmlist.port}")

    val bootstrap = new Bootstrap
    bootstrap.group(Global.group)
      .channel(classOf[NioSocketChannel])
      .option[java.lang.Integer](ChannelOption.CONNECT_TIMEOUT_MILLIS, 10000)
      .option[java.lang.Boolean](ChannelOption.SO_KEEPALIVE, true)
      .remoteAddress(new InetSocketAddress(Global.config.wow.realmlist.host, Global.config.wow.realmlist.port))
      .handler(new ChannelInitializer[SocketChannel]() {

        @throws[Exception]
        override protected def initChannel(socketChannel: SocketChannel): Unit = {
          val handler = if (WowChatConfig.getExpansion == WowExpansion.Vanilla) {
            new RealmPacketHandler(realmConnectionCallback)
          } else {
            new RealmPacketHandlerTBC(realmConnectionCallback)
          }

          socketChannel.pipeline.addLast(
            new IdleStateHandler(60, 120, 0),
            new IdleStateCallback,
            new RealmPacketDecoder,
            new RealmPacketEncoder,
            handler
          )
        }
      })

    channel = Some(bootstrap.connect.addListener((future: Future[_ >: Void]) => {
      Try {
        future.get(10, TimeUnit.SECONDS)
      }.fold(throwable => {
        logger.error(s"Failed to connect to realm server! ${throwable.getMessage}")
        realmConnectionCallback.disconnected
      }, _ => Unit)
    }).channel)
  }
}
