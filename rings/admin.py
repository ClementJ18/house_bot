import discord
from discord.ext import commands

from .utils.utils import HouseConverter, LandConverter, get_house_from_member

import ast
import psutil
import typing

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
        """Logs the bot out."""
        await self.bot.logout()

    @commands.command()
    async def terminate(self, ctx, *, house : HouseConverter):
        """Disband a house.

        Usage: `w!terminate [house]`

        __Examples__
        `w!terminate House of Tico` - terminate house named House of Tico
        `w!terminate 4` - terminate house with id 4
        """
        await self.bot.disband_house(ctx, house["id"])
        await ctx.send(f":white_check_mark: | **{house['name']}** has been terminated and now the rains weep o’er their hall")

    @commands.command()
    async def distribute(self, ctx, land : LandConverter, *, house : HouseConverter):
        """Change the owner of a land

        Usage: `w!distribute [land] [house]

        __Examples__
        `w!distribute 3 House of Tico` - give land with id 3 to House of Tico
        `w!distribute 3 4` give land with id 3 to house with id 4
        `w!distribute 'Grassland of Emyn Luin' House of Tico` give the land Grassland of Emyn Luin to House of Tico
        """
        await self.bot.log_battle(ctx, land, house["id"], house["id"], aid=True)
        await ctx.send(f":white_check_mark: | By the king's command, **{land['name']}** is now property of **{house['name']}**")

    @commands.command()
    async def offer(self, ctx, member : discord.Member, *, house : HouseConverter = None):
        """Offer a member to a house.

        Usage: `w!offer [member] [house]`

        __Examples__
        `w!offer @Necro House of Tico` - make Necro a member of the House of Tico
        `w!offer @Necro` - put Necro back in the House of the Raccoon, equivalent to having no house
        """
        if house is None:
            house = (await self.bot.query_executer("SELECT * FROM houses.Houses WHERE id=1"))[0]

        role = await get_house_from_member(member.id)["role"]
        await self.bot.query_executer("UPDATE houses.Members SET house=$1, noble='False' WHERE id=$2", house["id"], member.id)
        await ctx.send(f":white_check_mark: | By the king's command, **{member.display_name}** is now part of **{house['name']}**")

        role = discord.utils.get(ctx.guild.roles, id=role)
        if role:
            await member.remove_roles(role)

        role = discord.utils.get(ctx.guild.roles, id=house["role"])
        if role:
            await member.add_roles(role)

    @commands.command()
    async def ennoble(self, ctx, member : discord.Member):
        """Make a member a noble of his house, basically admin in the house.

        Usage: `w!ennoble [member]`

        __Examples__
        `w!ennoble @Necro` - make Necro a noble of whichever house he currently is in 
        """
        await self.bot.query_executer("UPDATE houses.Members SET noble='True' WHERE id=$1", member.id)
        await ctx.send(f":white_check_mark: | By the king's command, **{member.display_name}** is now a noble of their house")

    @commands.command()
    async def disennoble(self, ctx, member : discord.Member):
        """Remove a member as a noble of his house, removes the member's admin privilege within the house.

        Usage: `w!disennoble [member]`

        __Examples__
        `w!disennoble @Necro` - remove Necro as a noble of whichever house he currently is in 
        """
        await self.bot.query_executer("UPDATE houses.Members SET noble='False' WHERE id=$1", member.id)
        await ctx.send(f":white_check_mark: | By the king's command, **{member.display_name}** has been stripped of their nobility within their house")

    @commands.command()
    async def ratify(self, ctx, house : HouseConverter, field, *, value: typing.Union[discord.Role, discord.TextChannel, str]):
        """Edit any details of a house, rewriting history as you please. `field` has the following possible values
        - name
        - description
        - intitials
        - channel

        Usage: `w!ratify [house] [field] [value]`

        __Examples__
        `w!ratify "House of Tico" name House of Daiko` - change the name of House of Tico to House of Daiko
        `w!ratify 4 channel #house-of-daiko` - change the channel of the house with id 4 to #house-of-daiko. The role
        privilege will have to be overwritten manually, usually you shouldn't need to chang the role or the channel.
        """
        field = field.lower()
        await self.bot.update_names()
        if field in ["description", "name", "role", "intitials", "channel"]:
            try:
                if not self.bot.fields[field]["check"](value):
                    return await ctx.send(f":negative_squared_cross_mark: | {self.bot.fields[field]['req']}")
            except KeyError:
                pass

            if field in ["role", "channel"]:
                name = value.mention
                value = value.id
            else:
                name = value

            name = await self.bot.query_executer(f"UPDATE houses.Houses SET {field}=$1 WHERE id=$2 RETURNING name", value, house["id"], fetchval=True)
            await ctx.send(f":white_check_mark: | The {field} of **{house['name']}** is now **{name}**")

            if field == 'role':
                members = [discord.utils.get(ctx.guild.members, id=x[0]) for x in await self.bot.query_executer("SELECT id FROM houses.Members WHERE house=$1", house["id"])]
                for member in members:
                    await member.remove_roles(discord.utils.get(ctx.guild.roles, id=house["role"]))
                    await member.add_roles(discord.utils.get(ctx.guild.roles, id=value))

            if field == 'name':
                await self.bot.query_executer("UPDATE houses.Artefacts SET name=$1 WHERE name=$2", f'Banner of {name[0][0]}', f'Banner of {house["name"]}')

        else:
            await ctx.send(":negative_squared_cross_mark: | Not one of the given options")

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
