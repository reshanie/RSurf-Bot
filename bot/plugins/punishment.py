import outlet
import time
import discord

from outlet import errors, Member, RelativeTime

from bot.database import Session, Timeouts

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


# plugin

# noinspection PyTypeChecker
class Plugin(outlet.Plugin):
    __plugin__ = "Punishment"

    async def timeout_user(self, member, seconds, reason):
        timeout = db.query(Timeouts).filter_by(user_id=member.id).first()
        if timeout:
            raise errors.CommandError("{} is already in timeout.".format(member))

        # get rsurf punished role
        punished_role = discord.utils.get(member.guild.roles, id=RSURF_PUNISHED)

        if punished_role is None:
            raise errors.CommandError("Punished role not found.")

        # convert roles to string
        roles = get_role_string(member)
        expires = int(time.time() + seconds)

        timeout = Timeouts(user_id=member.id, guild_id=member.guild.id, expires=expires, roles=roles)

        try:
            # replace roles
            await member.edit(roles=[punished_role], reason="{} second timeout. Reason: {}".format(seconds, reason))
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to take roles from {!s}".format(member))
        else:
            db.add(timeout)

            self.log.debug("committing db")
            db.commit()

    async def remove_from_timeout(self, member):
        timeout = db.query(Timeouts).filter_by(user_id=member.id).first()

        if not timeout:
            raise errors.ArgumentError("{!s} isn't in timeout".format(member))

        self.log.info("removing {!s} from timeout in {!s}".format(member, member.guild))

        roles = get_roles_from_string(member.guild, timeout.roles)

        try:
            await member.edit(roles=roles, reason="Timeout ended.")
        except discord.errors.Forbidden:
            raise errors.CommandError("Make sure I have the permissions to give roles back to {!s}".format(member))
        else:
            db.delete(timeout)

            self.log.debug("committing db")
            db.commit()

    @outlet.run_every(10)
    async def check_timeouts(self):
        """
        Checks for any expired timeouts and makes sure roles are still removed from people in timeout.
        :return:
        """
        self.log.debug("checking for expired timeouts")

        epoch = time.time()

        for timeout in db.query(Timeouts):
            guild = self.bot.get_guild(timeout.guild_id)

            if guild is None:  # make sure bot is still in guild
                self.log.debug("bot is no longer in guild. removing timeout")

                db.delete(timeout)
                continue

            member = guild.get_member(timeout.user_id)

            if member is None:  # make sure member is still in guild
                self.log.debug("user is no longer in guild. removing timeout")

                db.delete(timeout)
                continue

            if timeout.expires < epoch:  # timeout expired
                self.log.info("timeout expired for {!s} in {!s}".format(member, guild))

                try:
                    self.create_task(self.remove_from_timeout(member))
                except errors.CommandError:
                    pass

        self.log.debug("committing db")
        db.commit()

    @outlet.command("timeout")
    @outlet.require_permissions("manage_roles")
    async def timeout_cmd(self, ctx, user: Member, length: RelativeTime, *reason):
        reason = " ".join(reason)

        self.log.info("{} given {} second timeout in {}".format(user, length, user.guild))

        await self.timeout_user(user, length, reason)

    @outlet.command("untimeout")
    @outlet.require_permissions("manage_roles")
    async def untimeout_cmd(self, ctx, user: Member):
        await self.remove_from_timeout(user)

        await ctx.send("Removed {!s} from timeout.".format(user))
