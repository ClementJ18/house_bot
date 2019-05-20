import discord
from discord.ext import commands

from rings.admin import Admin
from rings.houses import Houses
from config import token, dbpass

import traceback
import asyncpg

class TheArbitrer(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="m!", 
            case_insensitive=True, 
            owner_id=241942232867799040, 
            activity=discord.Game(name="m!help for help"),
            max_messages=25000
        )

        self.error_channel = 00000000000000
        self.admins = [312324424093270017, 241942232867799040]

    async def on_ready(self):
        print("We're up")
        self.pool = await asyncpg.create_pool(database="postgres", user="postgres", password=dbpass)

    async def query_executer(self, query, *args):
        conn = await self.pool.acquire()
        result = []
        try:
            if query.startswith("SELECT"):
                result = await conn.fetch(query, *args)
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

        return result

if __name__ == '__main__':
    bot = TheArbitrer()
    bot.add_cog(Admin(bot))
    bot.add_cog(Houses(bot))
    bot.run(token)