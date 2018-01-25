import time
from datetime import timedelta

import discord
import outlet
from outlet import errors, Member, RelativeTime

import sys

sys.path.insert(0, "bot/plugins/resources/")

from database import Session, Timeout
from functools import wraps

db = Session()

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


def seconds_to_str(s):
    return str(timedelta(0, s))


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
    __plugin__ = "Punishment"

    async def timeout_user(self, member, seconds, reason):
        if member.bot:
            raise errors.ArgumentError("Bots can't be put in timeout.")

        timeout = db.query(Timeout).filter_by(user_id=member.id).first()
        if timeout:
            raise errors.CommandError("{} is already in timeout.".format(member))

        # get rsurf punished role
        punished_role = discord.utils.get(member.guild.roles, id=RSURF_PUNISHED)

        if punished_role is None:
            raise errors.CommandError("Punished role not found.")

        # convert roles to string
        roles = get_role_string(member)
        expires = int(time.time() + seconds)

        timeout = Timeout(user_id=member.id, guild_id=member.guild.id, expires=expires, roles=roles,
                          reason=reason or "None given.")

        try:
            # replace roles
            await member.edit(roles=[punished_role], reason="{} second timeout. Reason: {}".format(seconds, reason))
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to take roles from {!s}".format(member))
        else:
            db.add(timeout)

            self.log.debug("committing db")
            db.commit()

    async def remove_from_timeout(self, user_id, guild, member=None):
        timeout = db.query(Timeout).filter_by(user_id=user_id).first()

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
            db.delete(timeout)

            self.log.debug("committing db")
            db.commit()

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

        for timeout in db.query(Timeout):
            guild = self.bot.get_guild(timeout.guild_id)

            if guild is None:  # make sure bot is still in guild
                self.log.debug("bot is no longer in guild. removing timeout")

                db.delete(timeout)
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

        reason = " ".join(reason) if reason else "No reason given."

        self.log.info("{} given {} second timeout in {}".format(user, length, user.guild))

        await self.timeout_user(user, length, reason)

    @outlet.command("untimeout")
    @outlet.require_permissions("manage_roles")
    async def untimeout_cmd(self, ctx, user: Member):
        """Remove a user from timeout."""

        await self.remove_from_timeout(user.id, user.guild, user)

        await ctx.send("Removed {!s} from timeout.".format(user))

    @outlet.command("timeouts")
    async def list_timeouts(self, ctx):
        """List active timeouts for the guild"""

        timeouts = db.query(Timeout).filter_by(guild_id=ctx.guild.id).all()

        msg = "__**Timeouts**__\n\n"

        for timeout in timeouts:
            member = ctx.guild.get_member(timeout.user_id)

            if member is None:
                continue

            time_left = max(0, int(timeout.expires) - int(time.time()))  # can take up to 10 seconds to remove timeout

            msg += "{}: {} Reason: {}".format(member, seconds_to_str(time_left), timeout.reason)

        return msg if timeouts else "No one is in timeout."
