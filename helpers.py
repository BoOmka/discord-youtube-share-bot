import typing as t

import discord
import discord_slash.error


async def suppress_expired_token_error(
        f: t.Callable[..., t.Awaitable[t.Any]],
        *args,
        **kwargs,
) -> t.Any:
    try:
        return await f(*args, **kwargs)
    except discord_slash.error.RequestFailure as ex:
        if ex.msg == '{"message": "Invalid Webhook Token", "code": 50027}':
            return None


async def _send_video(ctx: discord_slash.SlashContext, link: str) -> None:
    await ctx.channel.send(
        f"{ctx.author.mention}: {link}",
        allowed_mentions=discord.AllowedMentions(users=False)
    )
