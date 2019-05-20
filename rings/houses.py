import discord
from discord.ext import commands

class Houses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def attack(self, ctx, house):
        pass

    @commands.command()
    async def create(self, ctx, *nobles):
        pass

    @commands.command()
    async def disband(self, ctx):
        pass

    @commands.command()
    async def info(self, ctx, house):
        pass

    @commands.command()
    async def map(self, ctx):
        pass

    @commands.command()
    async def pledge(self, ctx, house):
        pass

    @commands.command()
    async def renounce(self, ctx):
        pass

    @commands.command()
    async def edit(self, ctx, field, *, value):
        pass
