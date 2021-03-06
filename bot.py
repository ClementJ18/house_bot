import discord
from discord.ext import commands, ext

from rings.admin import Admin
from rings.houses import Houses
from rings.utils import get_house_from_member, react_menu
from config import token, dbpass

import traceback
import asyncpg
from datetime import timedelta
import asyncio
import sys
import json
import random

class TheArbitrer(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="w!", 
            case_insensitive=True, 
            owner_id=241942232867799040, 
            activity=discord.Game(name="w!help for help"),
            max_messages=25000
        )

        self.names = []
        self.fields = {
            "name" : {"name": "name", "check": lambda x: len(x) <= 20 and x.lower() not in self.names, "req": "Must be less than or equal to 20 characters and be unique"},
            "description" : {"name": "description", "check": lambda x: len(x) <= 500, "req": "Must be less than or equal to 500 characters"},
            "initials" : {"name": "initials", "check": lambda x:2 <= len(x) <= 5, "req": "Must be between 2 and 5 characters"}
        }

        self.wars = []

        with open("config.json", "r") as f:
            config = json.load(f)
            self.error_channel = config["error_channel"]
            self.admins = config["admins"]
            self.permissions = config["permissions"]
            self.strengths = {int(key) : value for key, value in config["strengths"].items()}
            self.soldier_strings = config["soldier_strings"]
            self.prisoner_strings = config["prisoner_strings"]

    async def disband_house(self, ctx, house_id):
        house = await self.query_executer("UPDATE houses.Houses SET active='False' WHERE id=$1 RETURNING role, channel", house_id)
        await self.query_executer("UPDATE houses.Members SET house=1, noble='False' WHERE house=$1", house_id)
        await self.query_executer("UPDATE houses.Alliances SET broken=NOW() WHERE (house1=$1 OR house2=$1) AND BROKEN=NULL", house_id)
        await self.query_executer("UPDATE houses.Lands SET owner=2 WHERE owner=$1", house_id)
        await self.query_executer("DELETE FROM houses.Prisoners WHERE id=ANY(SELECT id FROM houses.Members WHERE house=$1)", house_id)

        await discord.utils.get(ctx.guild.roles, id=house[0][0]).delete()
        await discord.utils.get(ctx.guild.channels, id=house[0][1]).delete()

    async def take_prisoner(self, ctx, user, captor):
        user_house = await get_house_from_member(user.id)

        check = await self.query_executer("SELECT * FROM houses.Members WHERE house=$1 AND noble='True' AND NOT EXISTS (SELECT * FROM houses.Prisoners)", user_house["id"])
        if len(check) > 1:
            return await ctx.send(f"{user.mention} was captured, but as the last lord of his house, honor dictate he be released.")

        channel = discord.utils.get(ctx.guild.channels, id=user_house["channel"])
        await channel.set_permissions(user, overwrite=discord.PermissionOverwrite(read_messages=False))
        await self.query_executer("INSERT INTO houses.Prisoners VALUES ($1, $2)", user.id, captor)

        captor_house = await self.query_executer("SELECT * FROM houses.Houses WHERE id=$1", captor)
        await ctx.send(random.choice(self.prisoner_strings).format(house=captor_house["name"], member=user.mention))

    async def release_prisoner(self, ctx, user):
        await self.query_executer("DELETE FROM houses.Prisoners WHERE id=$1", user.id)
        user_house = await get_house_from_member(user.id)

        await discord.utils.get(ctx.guild.channels,id=user_house["channel"]).set_permissions(user, overwrite=None)
        await ctx.send(f"{user.mention} has been released")


    async def log_battle(self, ctx, land, attacker, victor, *, aid=False):
        await self.query_executer(
            "INSERT INTO houses.Battles(attacker, defender, victor, land, aid) VALUES($1, $2, $3, $4, $5)",
            attacker, land["owner"], victor, land["id"], aid
        )

        if attacker == victor:
            await self.query_executer("UPDATE houses.Lands SET owner=$1 WHERE id=$2", victor, land["id"])
            if not await self.query_executer("SELECT * FROM houses.Lands WHERE owner=$1", land["owner"]):
                await self.disband_house(ctx, land["owner"])
                defender = (await self.query_executer("SELECT name FROM houses.Houses WHERE id=$1", land["owner"]))[0][0]
                await self.query_executer("UPDATE houses.Artefacts SET owner=$1 WHERE owner=$2 AND name=$3", victor, defender["id"], f'Banner of {defender["name"]}')
                await ctx.send(f"**{defender}** has been wiped from existence, all that is left is the echoing laughter of thirsting gods.")

                await self.query_executer("""
                    UPDATE houses.Artefacts SET owner=$1 WHERE owner=$2 LIMIT (
                        SELECT (COUNT(*) / 4) FROM houses.Artefacts WHERE owner=$2 
                    )
                """, victor, defender["id"])

                await self.query_executer("UPDATE houses.Artefacts SET owner=2 WHERE owner=$1", defender["id"])

    async def update_names(self):
        self.names = [x[0].lower() for x in await self.query_executer("SELECT name FROM houses.Houses")]

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

        ids = [x[0] for x in await self.query_executer("SELECT id FROM houses.Members")]
        to_add = [x.id for x in self.get_all_members() if x.id not in ids]
        for user in to_add:
            if user == 312324424093270017:
                await self.query_executer("INSERT INTO houses.Members(id, noble) VALUES($1, 'True')", user)
            else:
                await self.query_executer("INSERT INTO houses.Members(id) VALUES($1)", user)

        await self.update_names()

        self.news = discord.utils.get(self.get_all_channels(), name="news-of-war")
        self.halls = discord.utils.get(self.get_all_channels(), name="House Halls")
        self.reports = discord.utils.get(self.get_all_channels(), name="war-reports")
        self.admin = discord.utils.get(self.get_all_channels(), name="sebubus-royal-house")
        print("We're up")

    async def on_member_join(self, member):
        await self.query_executer("INSERT INTO houses.Members(id) VALUES($1)", member.id)

    async def on_member_leave(self, member):
        await self.query_executer("DELETE FROM houses.Members WHERE id=$1", member.id)

    async def war_news_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            now = datetime.datetime.now()
            noon = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=18, minute=0, second=0)
            time = (noon - now).total_seconds()
            try:
                await asyncio.sleep(time if time > 0 else 86400 - time)
            except asyncio.CancelledError:
                return

            await self.war_news()

    async def war_news(self):
        battles = await self.query_executer("SELECT * FROM houses.Battles WHERE created_at BETWEEN NOW() - INTERVAL '24 HOURS' AND NOW() ORDER BY created_at DESC")
        embed = discord.Embed(title="Today's Battles", description="A list of battles that have occured today")

        for battle in battles[:20]:
            participants = await self.query_executer("SELECT * FROM houses.Houses WHERE id = ANY($1)", [battle["attacker"], battle["defender"]])
            victor = next(item for item in participants if item["id"] == battle["victor"])
            embed.add_field(name=f"{participants[0]['name']} vs. {participants[1]['name']}", value=f"The winner was **{victor['name']}**")

        await self.news.send(embed=embed)

    async def on_command_error(self, ctx, error):
        """Catches error and sends a message to the user that caused the error with a helpful message."""
        channel = ctx.channel
        if isinstance(error, commands.MissingRequiredArgument):
            await channel.send(f":negative_squared_cross_mark: | Missing required argument: `{error.param.name}`! Check help guide with `w!help {ctx.command.qualified_name}`", delete_after=10)
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

            the_traceback = "```py\n" + (" ".join(traceback.format_exception(type(error), error, error.__traceback__, chain=True))[:1985]) + "\n```"
            embed = discord.Embed(title="Command Error", description=the_traceback, colour=discord.Colour(0x277b0))
            embed.set_footer(text="Generated by The Arbitrer", icon_url=self.user.avatar_url_as(format="png", size=128))
            embed.add_field(name="Command", value=ctx.command.name)
            embed.add_field(name="Author", value=ctx.author.mention)
            embed.add_field(name="Location", value=f"**Guild:** {ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'DM'}) \n**Channel:** {ctx.channel.name if ctx.guild else 'DM'} ({ctx.channel.id})")
            embed.add_field(name="Message", value=ctx.message.content, inline=False)
            try:
                await self.admin.send(embed=embed)
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
