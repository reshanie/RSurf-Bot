import asyncio
import re
import time
from datetime import datetime, timedelta
from functools import wraps
from math import floor as floor_
from random import randrange

import discord
import outlet
from outlet import errors, Member, RelativeTime

RSURF_PUNISHED = 353641063199801347

INVITE = re.compile(r"(discord(\.gg|app\.com/invite)/\w+|discord\.me/\w+)")
SELF_PROMOTION = 386618891012669441


# utilities

def snowflake():
    return (int(time.time()) << 3) | randrange(255)


def get_role_string(member):
    return "|".join(str(role.id) for role in member.roles)


def get_roles_from_string(guild, role_string):
    roles = []

    for role_id in role_string.split("|"):
        role = discord.utils.get(guild.roles, id=int(role_id))

        if role is not None:
            roles.append(role)

    return roles


floor = lambda x: int(floor_(x))


def seconds_to_str(seconds):
    return str(timedelta(0, seconds))


def seconds_to_long_str(seconds):
    seconds = int(seconds)

    minutes = floor(seconds / 60)
    hours = floor(minutes / 60)

    seconds %= 60
    minutes %= 60

    time_str = []
    if hours:
        time_str.append("{} hours".format(hours))
    if minutes:
        time_str.append("{} minutes".format(minutes))
    if seconds:
        time_str.append("{} seconds".format(seconds))

    return " ".join(time_str)[:-1]


# decorators


def debug_only(func):
    if getattr(func, "is_command", False):
        raise SyntaxError("@debug_only decorator should be placed under the @command decorator")

    @wraps(func)
    async def new_func(self_, ctx, *args):
        if ctx.author.id != 231658954831298560:
            raise errors.MissingPermission("This is a debug command and can only be used by reshanie#7510")

        return await func(self_, ctx, *args)

    return new_func


# mod log messages

BAN = "{mod} banned {user}. Reason: `{reason}`"
KICK = "{mod} kicked {user}. Reason: `{reason}`"

TIMEOUT = "{mod} punished {user}. Length: `{length}` Reason: `{reason}`"

UNTIMEOUT = "{mod} unpunished {user}"
UNBAN = "{mod} unbanned {user}"


def format_msg(content, **kwargs):
    content

    for key, value in kwargs.items():
        content = content.replace("{" + key + "}", str(value))

    return content


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Moderation"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        database = self.get_resource("database.py")

        self.db = database.Session()
        self.Timeout = database.Timeout
        self.TimeoutLog = database.TimeoutLog

        self.mod_log = None

    # --- #

    async def on_ready(self):
        self.mod_log = self.bot.get_channel(355845257881190400)

        if self.mod_log is None:
            self.log.error("mod log channel not found")

    async def timeout_user(self, member, seconds, reason):
        if member.bot:
            raise errors.ArgumentError("Bots can't be put in timeout.")

        timeout = self.db.query(self.Timeout).filter_by(user_id=member.id).first()
        if timeout:
            raise errors.CommandError("{} is already in timeout.".format(member))

        # get rsurf punished role
        punished_role = discord.utils.get(member.guild.roles, id=RSURF_PUNISHED)

        if punished_role is None:
            raise errors.CommandError("Punished role not found.")

        # convert roles to string
        roles = get_role_string(member)
        expires = int(time.time() + seconds)

        timeout = self.Timeout(user_id=member.id, guild_id=member.guild.id, expires=expires, roles=roles,
                               reason=reason or "None given.")

        timeout_log = self.TimeoutLog(id=snowflake(),
                                      user_id=member.id,
                                      given_at=datetime.utcnow(),
                                      length=timedelta(0, seconds),
                                      reason=reason)

        try:
            # replace roles
            await member.edit(roles=[punished_role], reason="{} second timeout. Reason: {}".format(seconds, reason))
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to take roles from {!s}".format(member))
        else:
            self.db.add(timeout)
            self.db.add(timeout_log)

            self.log.debug("committing db")
            self.db.commit()

    async def remove_from_timeout(self, user_id, guild, member=None):
        timeout = self.db.query(self.Timeout).filter_by(user_id=user_id).first()

        if not timeout:
            raise errors.ArgumentError("{!s} isn't in timeout".format(member))

        self.log.info("removing {!s} from timeout in {!s}".format(member or user_id, guild))

        roles = get_roles_from_string(guild, timeout.roles)

        try:
            if member:  # don't remove roles if not in guild
                await member.edit(roles=roles, reason="Timeout ended.")
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to give roles back to {!s}".format(member))
        else:
            self.db.delete(timeout)

            self.log.debug("committing db")
            self.db.commit()

            if member:
                # notify user if possible
                try:
                    await member.send("Your timeout in {} is over.".format(member.guild))
                except discord.errors.Forbidden:
                    pass

    @outlet.run_every(10)
    async def check_timeouts(self):
        """
        Checks for any expired timeouts and makes sure roles are still removed from people in timeout.
        :return:
        """
        self.log.debug("checking for expired timeouts")

        epoch = time.time()

        for timeout in self.db.query(self.Timeout):
            guild = self.bot.get_guild(timeout.guild_id)

            if guild is None:  # make sure bot is still in guild
                self.log.debug("bot is no longer in guild. removing timeout")

                self.db.delete(timeout)
                continue

            member = guild.get_member(timeout.user_id)

            if timeout.expires < epoch:  # timeout expired
                self.log.info("timeout expired for {!s} in {!s}".format(member, guild))

                try:
                    self.create_task(self.remove_from_timeout(timeout.user_id, guild, member=member))
                except errors.CommandError:
                    pass

    @outlet.command("timeout")
    @outlet.require_permissions("manage_roles")
    async def timeout_cmd(self, ctx, user: Member, length: RelativeTime, *reason):
        """Give a user timeout with an optional reason."""

        reason = " ".join(
            ctx.message.clean_content.split(" ")[-len(reason):]  # get message clean content and find reason
        )

        self.log.info("{} given {} second timeout in {}".format(user, length, user.guild))

        await self.timeout_user(user, length, reason)

        await self.mod_log.send(format_msg(TIMEOUT,
                                           mod=ctx.author.mention,
                                           user=user.mention,
                                           reason=reason,
                                           length=timedelta(0, length)))

    @outlet.command("untimeout")
    @outlet.require_permissions("manage_roles")
    async def untimeout_cmd(self, ctx, user: Member):
        """Remove a user from timeout."""

        await self.remove_from_timeout(user.id, user.guild, user)

        timeout = self.db.query(self.TimeoutLog).filter_by(user_id=user.id).order_by(self.TimeoutLog.given_at)[-1]

        self.db.delete(timeout)

        self.log.debug("committing db")
        self.db.commit()

        await ctx.send("Removed {!s} from timeout.".format(user))

        await self.mod_log.send(format_msg(UNTIMEOUT,
                                           mod=ctx.author.mention,
                                           user=user.mention))

    async def on_member_ban(self, guild, user):
        """log member bans"""

        self.log.info("member was banned.")

        if guild.id != 353615025589714946:  # make sure its rsurf
            return

        await asyncio.sleep(1)  # allow time for audit log to update (just in case)

        audit = await guild.audit_logs(limit=3, action=discord.AuditLogAction.ban).flatten()

        audit = discord.utils.get(audit, target=user)
        if audit is None:
            raise ValueError("Member ban not found in audit log.")

        await self.mod_log.send(format_msg(BAN,
                                           mod=audit.user.mention,
                                           user=user,
                                           reason=audit.reason or "None provided."))

        if audit.reason is None:
            await self.mod_log.send("{} please give reason when you ban!".format(audit.user.mention))

    async def on_member_unban(self, guild, user):
        """log member unbans"""

        self.log.info("member was unbanned.")

        if guild.id != 353615025589714946:  # make sure its rsurf
            return

        await asyncio.sleep(1)  # allow time for audit log to update (just in case)

        audit = await guild.audit_logs(limit=3, action=discord.AuditLogAction.unban).flatten()

        audit = discord.utils.get(audit, target=user)
        if audit is None:
            raise ValueError("Member ban not found in audit log.")

        await self.mod_log.send(format_msg(UNBAN,
                                           mod=audit.user.mention,
                                           user=user))

    async def on_member_remove(self, member):
        """check if member was kicked and if so, log"""

        guild = member.guild

        if guild.id != 353615025589714946:  # make sure its rsurf
            return

        await asyncio.sleep(1)

        t = int(time.time()) - 2
        after = datetime.utcfromtimestamp(t)

        audit = await guild.audit_logs(after=after, action=discord.AuditLogAction.kick).flatten()

        audit = discord.utils.get(audit, target=member)
        if audit is None:
            return

        await self.mod_log.send(format_msg(KICK,
                                           mod=audit.user.mention,
                                           user=member,
                                           reason=audit.reason))

        if audit.reason is None:
            await self.mod_log.send("{} please give reason when you kick!".format(audit.user.mention))

    @outlet.command("timeout-log")
    async def timeout_log(self, ctx, user: Member):
        """Shows a list of every timeout a user has received."""

        timeouts = self.db.query(self.TimeoutLog).filter_by(user_id=user.id).order_by(
            self.TimeoutLog.given_at).all()

        if len(timeouts) == 0:
            return "{} has never been timed out.".format(user)

        embed = discord.Embed(color=await self.bot.my_color(ctx.guild))
        embed.set_author(name=str(user), icon_url=user.avatar_url)

        for timeout in timeouts:
            embed.add_field(name="**{}** on {}".format(timeout.length, timeout.given_at.date()),
                            value=timeout.reason,
                            inline=False)

        embed.set_footer(text="Requested by {}".format(ctx.author))

        await ctx.send(embed=embed)

    @outlet.command("timeouts")
    async def list_timeouts(self, ctx):
        """List active timeouts for the guild"""

        timeouts = self.db.query(self.Timeout).filter_by(guild_id=ctx.guild.id)

        embed = discord.Embed(title="Timeouts", color=await self.bot.my_color(ctx.guild))

        for timeout in timeouts:
            member = ctx.guild.get_member(timeout.user_id)

            if member is None:
                continue

            time_left = max(0,
                            int(timeout.expires) - int(time.time()))  # can take up to 10 seconds to remove timeout

            embed.add_field(name=member, value="Reason: `{}`\nTime Left: `{}`".format(timeout.reason,
                                                                                      timedelta(0, time_left)),
                            inline=False)

        embed.set_footer(text="Requested by {}".format(ctx.author))

        if not timeouts:
            return "No one is in timeout."

        await ctx.send(embed=embed)

    @outlet.command("clear-timeout-log")
    @outlet.require_permissions("manage_roles")
    async def clear_timeout_log(self, ctx, user: Member):
        """Clears a user's timeout log."""

        try:
            self.db.query(self.TimeoutLog).filter_by(user_id=user.id).delete()

            self.log.debug("committing db")
            self.db.commit()

            await self.mod_log.send("{} cleared {}'s timeout log.".format(ctx.author.mention, user.mention))

            return "{}'s timeout log was successfully cleared!".format(user)
        except Exception as e:
            self.db.rollback()
            raise errors.CommandError("Failed to clear {}'s timeout log. ```{}```".format(user, str(e)))

    @outlet.events.on_message(channel="general")
    async def delete_invites(self, message):
        if message.author == self.bot.user:
            return

        if INVITE.search(message.content) is not None:
            await message.delete()

            warning = await message.channel.send("Invites belong in <#{}>".format(SELF_PROMOTION))

            await asyncio.sleep(5)
            await warning.delete()
