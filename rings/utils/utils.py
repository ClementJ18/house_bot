from discord.ext import commands

def is_admin(ctx):
    return ctx.message.author.id in ctx.bot.admin

async def react_menu(ctx, max_pages, page_generator, page=0):
    msg = await ctx.send(embed=page_generator(page))
    while True:
        react_list = []
        if page > 0:
            react_list.append("\N{BLACK LEFT-POINTING TRIANGLE}")

        react_list.append("\N{BLACK SQUARE FOR STOP}")

        if page < max_pages:
            react_list.append("\N{BLACK RIGHT-POINTING TRIANGLE}")

        for reaction in react_list:
            await msg.add_reaction(reaction)

        def check(reaction, user):
            return user == ctx.message.author and reaction.emoji in react_list and msg.id == reaction.message.id

        try:
            reaction, _ = await ctx.bot.wait_for("reaction_add", check=check, timeout=300)
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return

        if reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
            await msg.clear_reactions()
            return
        elif reaction.emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
            page -= 1
        elif reaction.emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
            page += 1

        await msg.clear_reactions()
        await msg.edit(embed=page_generator(page))
        

class HouseConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            house_id = int(argument)
            house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE id=$1 AND active='True'", house_id)
            if house:
                return house[0]
        except ValueError:
            pass

        house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE name=$1 AND active='True'", argument)

        if house:
            return house[0]

        house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE name LIKE $1 AND active='True'", argument)

        if house:
            return house[0]

        raise commands.BadArgument("This house does not exist")

class LandConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            land_id = int(argument)
            land = await ctx.bot.query_executer("SELECT * FROM Lands WHERE id=$1", land_id)
            if land:
                return land[0]
        except ValueError:
            pass

        land = await ctx.bot.query_executer("SELECT * FROM Lands WHERE name=$1", argument)

        if land:
            return land[0]

        land = await ctx.bot.query_executer("SELECT * FROM Lands WHERE name LIKE $1", argument)

        if land:
            return land[0]

        raise commands.BadArgument("This land does not exist")

def reaction_check_factory(msg, nobles):
    approved = []

    def reaction_check(reaction, user):
        if not reaction.message.id == msg.id or not user.id in [x.id for x in nobles]:
            return False

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            return True

        if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            approved.append(user)
            if len(approved) == 1: #TODO: change back to len(nobles)
                return True

        return False

    return reaction_check
