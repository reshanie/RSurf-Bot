import time
from datetime import timedelta

import discord
import outlet
from outlet import errors, Member, RelativeTime

from functools import wraps

from math import floor as floor_

RSURF_PUNISHED = 353641063199801347


# utilities

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

        await func(self_, ctx, *args)

    return new_func


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Moderation"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        database = self.get_resource("database.py")

        self.db = database.Session()
        self.Timeout = database.Timeout

        self.mod_log = None

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

        try:
            # replace roles
            await member.edit(roles=[punished_role], reason="{} second timeout. Reason: {}".format(seconds, reason))
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to take roles from {!s}".format(member))
        else:
            self.db.add(timeout)

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
                    self.create_task(self.remove_from_timeout(member.id, guild, member=member))
                except errors.CommandError:
                    pass

    @outlet.command("timeout")
    @outlet.require_permissions("manage_roles")
    async def timeout_cmd(self, ctx, user: Member, length: RelativeTime, *reason):
        """Give a user timeout with an optional reason."""

        reason = " ".join(reason) if reason else "No reason provided."

        self.log.info("{} given {} second timeout in {}".format(user, length, user.guild))

        await self.timeout_user(user, length, reason)

        await self.mod_log.send(
            "{} gave {} a {} timeout. Reason: `{}`".format(ctx.author.mention, user.mention,
                                                            seconds_to_long_str(length), reason))

        # dm user if possible
        try:
            await user.send("You were given a {} timeout in {}. Reason: {}".format(seconds_to_long_str(length),
                                                                                    user.guild, reason))
        except discord.errors.Forbidden:
            pass

    @outlet.command("untimeout")
    @outlet.require_permissions("manage_roles")
    async def untimeout_cmd(self, ctx, user: Member):
        """Remove a user from timeout."""

        await self.remove_from_timeout(user.id, user.guild, user)

        await ctx.send("Removed {!s} from timeout.".format(user))

        await self.mod_log.send("{} lifted {}'s timeout".format(ctx.author.mention, user.mention))

        # dm user if possible
        try:
            await user.send("Your timeout in RSurf was lifted.")
        except discord.errors.Forbidden:
            pass

    @outlet.command("timeouts")
    async def list_timeouts(self, ctx):
        """List active timeouts for the guild"""

        timeouts = self.db.query(self.Timeout).filter_by(guild_id=ctx.guild.id).all()

        msg = "__**Timeouts**__\n"

        for timeout in timeouts:
            member = ctx.guild.get_member(timeout.user_id)

            if member is None:
                continue

            time_left = max(0, int(timeout.expires) - int(time.time()))  # can take up to 10 seconds to remove timeout

            msg += "\n{}: {} Reason: {}".format(member, seconds_to_str(time_left), timeout.reason)

        return msg if timeouts else "No one is in timeout."

    async def on_member_ban(self, guild, user):
        self.log.info("member was banned.")

        if guild.id != 353615025589714946:  # make sure its rsurf
            return

        audit = await guild.audit_logs(limit=10, action=discord.AuditLogAction.ban).flatten()

        audit = discord.utils.get(audit, target=user)
        if audit is None:
            raise ValueError("Member ban not found in audit log.")

        msg = "{0.user.mention} banned `{0.target}` Reason: `{1}`".format(audit, audit.reason or "No reason provided.")

        await self.mod_log.send(msg)

    async def on_member_unban(self, guild, user):
        if guild.id != 353615025589714946:  # make sure its rsurf
            return

        audit = await guild.audit_logs(limit=10, action=discord.AuditLogAction.ban).flatten()

        audit = discord.utils.get(audit, target=user)
        if audit is None:
            raise ValueError("Member ban not found in audit log.")

        msg = "{0.user.mention} unbanned `{0.target}`".format(audit)

        await self.mod_log.send(msg)
