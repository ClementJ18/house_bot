import discord
from discord.ext import commands

import ast
import psutil

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process()

    def _insert_returns(self, body):
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        if isinstance(body[-1], ast.If):
            self._insert_returns(body[-1].body)
            self._insert_returns(body[-1].orelse)

        if isinstance(body[-1], ast.With):
            self._insert_returns(body[-1].body)

    async def cog_check(self, ctx):
        return ctx.author.id in ctx.bot.admins

    @commands.command()
    async def logout(self, ctx):
        await self.bot.logout()

    @commands.command()
    async def terminate(self, ctx, house):
        pass

    @commands.command()
    async def distribute(self, ctx, house, land):
        pass

    @commands.command()
    async def legitimize(self, ctx, house, member):
        pass

    @commands.command()
    async def ratify(self, ctx, house, field, *, value):
        pass

    @commands.command()
    async def debug(self, ctx, *, cmd):
        """Evaluates code.
        
        {usage}
        
        The following global envs are available:
            `bot`: bot instance
            `discord`: discord module
            `commands`: discord.ext.commands module
            `ctx`: Context instance
            `__import__`: allows to import module
            `guild`: guild eval is being invoked in
            `channel`: channel eval is being invoked in
            `author`: user invoking the eval
        """
        fn_name = "_eval_expr"
        cmd = cmd.strip("` ")
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"
        python = '```py\n{}\n```'

        parsed = ast.parse(body)
        body = parsed.body[0].body
        self._insert_returns(body)

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author
        }
        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = (await eval(f"{fn_name}()", env))
            if result:
                await ctx.send(result)
            else:
                await ctx.send(":white_check_mark:")
        except Exception as e:
            await ctx.send(python.format(f'{type(e).__name__}: {e}'))
