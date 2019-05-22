from discord.ext import commands

def is_admin(ctx):
    return ctx.message.author.id in ctx.bot.admin
        

class HouseConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            house_id = int(argument)
            house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE id=$1", house_id)
            if house:
                return house[0]
        except ValueError:
            pass

        house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE name=$1", argument)

        if house:
            return house[0]

        house = await ctx.bot.query_executer("SELECT * FROM Houses WHERE name LIKE $1", argument)

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
