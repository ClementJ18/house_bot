import discord
from discord.ext import commands

from rings.admin import Admin
from rings.houses import Houses
from config import token, dbpass

import traceback
import asyncpg
from datetime import timedelta
import asyncio
import sys

class TheArbitrer(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="w!", 
            case_insensitive=True, 
            owner_id=241942232867799040, 
            activity=discord.Game(name="w!help for help"),
            max_messages=25000
        )

        self.error_channel = 415169176693506048
        self.admins = [312324424093270017, 241942232867799040]

        self.names = []
        self.fields = {
            "name" : {"name": "name", "check": lambda x: len(x) <= 20 and x.lower() not in self.names, "req": "Must be less than or equal to 20 characters and be unique"},
            "description" : {"name": "description", "check": lambda x: len(x) <= 500, "req": "Must be less than or equal to 500 characters"},
            "initials" : {"name": "initials", "check": lambda x:2 <= len(x) <= 5, "req": "Must be between 2 and 5 characters"}
        }

        self.strengths = {
            480803366369492992 : 10,
            497831361969782794 : 8,
            480804715123179530 : 6,
            480804634710114305 : 4,
            480805221904416793 : 2,
            480806133150253065 : 1
        }

    async def disband_house(self, house_id):
        house = await self.query_executer("UPDATE Houses SET active='False' WHERE id=$1 RETURNING role, channel", house_id)
        await self.query_executer("UPDATE Members SET house=1, noble='False' WHERE house=$1", house_id)
        await self.query_executer("UPDATE Alliances SET broken=NOW() WHERE (house1=$1 OR house2=$1) AND BROKEN=NULL", house_id)
        await self.query_executer("UPDATE Lands SET owner=2 WHERE owner=$1", house_id)

        await discord.utils.get(ctx.guild.roles, id=house[0]).delete()
        await discord.utils.get(ctx.guild.channels, id=house[1]).delete()

    async def log_battle(self, land, attacker, victor, *, aid=False):
        await self.query_executer(
            "INSERT INTO Battles(attacker, defender, victor, land, aid) VALUES($1, $2, $3, $4, $5)",
            attacker, land["owner"], victor, land["id"], aid
        )

        if attacker == victor:
            await self.query_executer("UPDATE Lands SET owner=$1 WHERE id=$2", victor, land["id"])

    async def update_names(self):
        self.names = [x[0].lower() for x in await self.query_executer("SELECT name FROM Houses")]

    async def query_executer(self, query, *args, fetchval=False):
        conn = await self.pool.acquire()
        results = []
        try:
            if query.startswith("SELECT"):
                results = await conn.fetch(query, *args)
            elif fetchval:
                result = await conn.fetchval(query, *args)
                return result
            else:
                await conn.execute(query, *args)
        except Exception as error:
            channel = self.get_channel(self.error_channel)
            the_traceback = f"```py\n{' '.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))}\n```"
            embed = discord.Embed(title="DB Error", description=the_traceback, colour=discord.Colour(0x277b0))
            embed.add_field(name='Event', value=error)
            embed.add_field(name="Query", value=query)
            embed.add_field(name="Arguments", value=args)
            embed.set_footer(text="Generated by TheArbitrer", icon_url=self.user.avatar_url_as(format="png", size=128))
            await channel.send(embed=embed) 
        finally:        
            await self.pool.release(conn)

        return results

    async def on_ready(self):
        self.pool = await asyncpg.create_pool(database="postgres", user="postgres", password=dbpass)

        ids = [x[0] for x in await self.query_executer("SELECT id from Members")]
        to_add = [x.id for x in self.get_all_members() if x.id not in ids]
        for user in to_add:
            if user == 312324424093270017:
                await self.query_executer("INSERT INTO Members(id, noble) VALUES($1, 'True')", user)
            else:
                await self.query_executer("INSERT INTO Members(id) VALUES($1)", user)

        await self.update_names()

        print("We're up")

    async def on_member_join(self, member):
        await self.query_executer("INSERT INTO Members(id) VALUES($1)", member.id)

    async def on_member_leave(self, member):
        results = await self.query_executer("DELETE FROM Members WHERE id=$1 RETURNING house, noble", member.id, fetchval=True)
        if results[0][1]:
            pass
            #do something?

    async def on_command_error(self, ctx, error):
        """Catches error and sends a message to the user that caused the error with a helpful message."""
        channel = ctx.channel
        if isinstance(error, commands.MissingRequiredArgument):
            await channel.send(f":negative_squared_cross_mark: | Missing required argument: `{error.param.name}`! Check help guide with `n!help {ctx.command.qualified_name}`", delete_after=10)
            #this can be used to print *all* the missing arguments (bit hacky tho)
            # index = list(ctx.command.clean_params.keys()).index(error.param.name)
            # missing = list(ctx.command.clean_params.values())[index:]
            # print(f"missing following: {', '.join([x.name for x in missing])}")
        elif isinstance(error, commands.CheckFailure):
            await channel.send(f":negative_squared_cross_mark: | {error}", delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            retry_after = str(timedelta(seconds=error.retry_after)).partition(".")[0].replace(":", "{}").format("hours, ", "minutes and ")
            await channel.send(f":negative_squared_cross_mark: | This command is on cooldown, retry after **{retry_after}seconds**", delete_after=10)
        elif isinstance(error, commands.NoPrivateMessage):
            await channel.send(":negative_squared_cross_mark: | This command cannot be used in private messages.", delete_after=10)
        elif isinstance(error, commands.DisabledCommand):
            await channel.send(":negative_squared_cross_mark: | This command is disabled and cannot be used for now.", delete_after=10)
        elif isinstance(error, (commands.BadUnionArgument, commands.BadArgument)):
            await channel.send(f":negative_squared_cross_mark: | {error}", delete_after=10)
        elif isinstance(error, asyncio.TimeoutError):
            await channel.send(f":negative_squared_cross_mark: | You took too long to reply, please reply quicker next time", delete_after=10)
        elif isinstance(error, commands.CommandInvokeError):
            if "Forbidden" in error.args[0]:
                await channel.send(":negative_squared_cross_mark: | Something went wrong, check my permission level, it seems I'm not allowed to do that on your server.", delete_after=10)
                return

            channel = self.get_channel(self.error_channel)
            the_traceback = "```py\n" + (" ".join(traceback.format_exception(type(error), error, error.__traceback__, chain=True))[:1985]) + "\n```"
            embed = discord.Embed(title="Command Error", description=the_traceback, colour=discord.Colour(0x277b0))
            embed.set_footer(text="Generated by The Arbitrer", icon_url=self.user.avatar_url_as(format="png", size=128))
            embed.add_field(name="Command", value=ctx.command.name)
            embed.add_field(name="Author", value=ctx.author.mention)
            embed.add_field(name="Location", value=f"**Guild:** {ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'DM'}) \n**Channel:** {ctx.channel.name if ctx.guild else 'DM'} ({ctx.channel.id})")
            embed.add_field(name="Message", value=ctx.message.content, inline=False)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                print(f'Bot: Ignoring exception in command {ctx.command}:', file=sys.stderr)
                traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            
            thing = ctx.guild or ctx.author
            if thing.id != 311630847969198082:
                await ctx.send(f":negative_squared_cross_mark: | {error}", delete_after=10)
            
if __name__ == '__main__':
    bot = TheArbitrer()
    bot.add_cog(Admin(bot))
    bot.add_cog(Houses(bot))
    bot.run(token)
