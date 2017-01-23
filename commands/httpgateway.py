import loader
import aiohttp.web
import weakref
import discord
import config

@loader.context_class
class HttpGateway(object):
    async def init_with_context(self, bot):
        event_loop = bot.client.loop
        self.app = aiohttp.web.Application()
        self.app.router.add_post("/msg", self.recv_msg)

        http_config_host = config.get("httpgateway.host", "0.0.0.0")
        http_config_port = config.get("httpgateway.port", 8002)

        self.handler = self.app.make_handler()
        self.service = await event_loop.create_server(self.handler, http_config_host, http_config_port)

        self.bot_ref = weakref.proxy(bot)

    async def deinit(self, bot):
        self.service.close()
        await self.service.wait_closed()
        await self.app.shutdown()
        await self.handler.shutdown(60.0)
        await self.app.cleanup()

    async def recv_msg(self, request):
        payload = await request.json()
        target = self.bot_ref.client.get_channel(payload["target"])

        await self.bot_ref.client.send_message(target, payload["text"])
        return aiohttp.web.Response(text="OK")
