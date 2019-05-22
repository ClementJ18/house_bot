import discord
from discord.ext import commands
from .utils.utils import HouseConverter, reaction_check_factory

import asyncio

class Houses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def string_validator(self, ctx, field, nobles, content):
        msg = await ctx.send(f"Do all members agree to the house {field['name']} of: **{content}**")

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check_factory(msg, nobles), timeout=600)

        await msg.clear_reactions()

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            raise Exception(f"**{user.display_name}** does not agree with the house {field['name']}")

        return content        


    @commands.command()
    async def attack(self, ctx, *, house : HouseConverter):
        """Attack a house. This is a command heavy of consequences, do not use it lightly, in addition,
        it has a 14 day cooldown. You cannot attack houses that were created in the last 28 days except if
        they have attacked someone themselves. You cannot attack a house you are in an alliance with or were
        with in the last 14 days. You cannot attack the House of the Raccoon

        Usage: `w!attack [house]`

        __Examples__
        `w!attack House of Tico` - Attack the House of Tico
        `w!attack 4` - Attack the house with the id 4
        """
        pass

    @commands.command()
    async def map(self, ctx):
        """Show a map of the realm.

        Usage: `w!map`
        """
        pass

    @commands.command()
    @commands.has_role("Noble Racoon")
    async def create(self, ctx, *nobles: discord.Member):
        """Create a house with nobles you have mentionned, one of those mentions must be yourself. All three 
        mentionned members must be part of the House of the Raccoon. Once the process is started the nobles will be
        asked to agree on a name, a description and initials for their house.

        Usage: `w!create [member] [member] [member]`

        __Examples__
        `w!create @Necro @Sebubu @Elf` - begin the creation process to create a house with Necro, Sebubu and Elf as the
        nobles.
        """
        # nobles = list(set(nobles)) #TODO: add back in later to avoid duplicates
        if any(x.id == 312324424093270017 for x in nobles):
            return await ctx.send(":negative_squared_cross_mark: | You cannot ask the King to join your House")

        if len(nobles) != 3:
            return await ctx.send(":negative_squared_cross_mark: | Please select exactly three nobles to be part of the house")

        raw_royals = await self.bot.query_executer("SELECT FROM Members WHERE id=ANY($1) AND noble='True'", [x.id for x in nobles])
        royals = [f"**{x.display_name}**" for x in nobles if x.id in raw_royals]
        if royals:
            return await ctx.send(f":negative_squared_cross_mark: | {', '.join(royals)} are already in a house")

        msg = await ctx.send(f"**{nobles[0].mention}**, **{nobles[1].mention}**, **{nobles[2].mention}**, you have been asked to form a house. Do you accept? If you accept react with :white_check_mark:, else react with :negative_squared_cross_mark:.")

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check_factory(msg, nobles), timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send(":negative_squared_cross_mark: | Please reply within 10 minutes next time")
        finally:
            await msg.clear_reactions()

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            return await ctx.send(f"**{user.display_name}** has refused to join the house")

        values = {}

        await self.bot.update_names()
        for field in self.bot.fields:
            await ctx.send(f"Now please, {ctx.author.mention}, pick a {field['name']} for the house and all the nobles will have to agree to it. {field['req']}")
            
            def message_check(message):
                return ctx.author.id == message.author.id and ctx.channel.id == message.channel.id and field['check'](message.content)

            message = await self.bot.wait_for("message", check=message_check, timeout=600)

            values[field["name"]] = await self.string_validator(ctx, field, nobles, message.content)

        role = await ctx.guild.create_role(
            name=values["name"]
        )

        channel = await ctx.guild.create_text_channel(
            values["name"], 
            category=discord.utils.get(ctx.guild.channels, name="Family Houses"),
            overwrites={
                role : discord.PermissionOverwrite(read_messages=True),
                ctx.guild.default_role : discord.PermissionOverwrite(read_messages=False)
            }
        )
        result = await self.bot.query_executer(
            "INSERT INTO Houses(name, initials, description, role, channel) VALUES ($1, $2, $3, $4, $5) RETURNING id;",
            values["name"], values["initials"], values["description"], role.id, channel.id, fetchval=True
        )
        await self.bot.query_executer("UPDATE Members SET house=$2, noble='True' WHERE id=ANY($1)", [x.id for x in nobles], result)

        for royal in nobles:
            try:
                await royal.add_roles(role)
            except discord.Forbidden:
                await ctx.send(f":negative_squared_cross_mark: | Couldn't add the role for **{royal.display_name}**")

        await ctx.send(f"Alright, the {values['name']} has been created. Long may it endure.")

    @commands.command()
    @commands.has_role("Noble Raccoon")
    async def disband(self, ctx):
        """Disbands the house. This does not remove the house completly but rather de-activates it, users will be
        removed from the house and you will no longer be able to join it. You will still be able to ead about this
        house's history in the logs but you won't be able to interact with it. All nobles from the house will have to
        agree on disbanding the house once the command has been called.

        Usage: `w!disband`
        """
        house_id =  await self.bot.query_executer("SELECT house FROM house.Members where id=$1;", ctx.author.id)
        query = await self.bot.query_executer("SELECT id FROM Members WHERE house=$1 AND noble='True';", house_id)

        royals = [member for member in ctx.guild.members if member.id in query]

        msg = await ctx.send(f"{', '.join([member.mention for member in royals])}, do you all agree to disband the house? React with :white_check_mark: if you do, if you are against it react with :negative_squared_cross_mark:.")
        
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check_factory(msg, royals), timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send(":negative_squared_cross_mark: | Please reply within 10 minutes next time")
        finally:
            await msg.clear_reactions()

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await self.bot.disband_house(house_id)
            await ctx.send(":white_check_mark: | So be it, you and your people are released from your oaths.")
        elif reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            await ctx.send(f":white_check_mark: | **{user.display_name}** has refused to disband the house")

    @commands.command()
    async def info(self, ctx, *, house : HouseConverter = None):
        """Get info on a house. If no house is specific it will return info on your own house.

        Usage: `w!info [house]`

        __Examples__
        `w!info 4` - get the info for house with id 4
        `w!info House of Tico` - get info for the house named House of Tico
        `w!info` - get info for your own house 
        """
        if house is None:
            house_id = await self.bot.query_executer("SELECT house FROM Members WHERE id=$1", ctx.author.id)
            house = await HouseConverter().convert(house_id[0][0])

        members = await self.bot.query_executer("SELECT * FROM Members WHERE house=$1", house["id"])
        embed = discord.Embed(title=f'{house["name"]} ({house["id"]})', description=house["description"])
        embed.add_field(name="Members", value=len(members))

        nobles = [f"**{discord.utils.get(ctx.guild.members, id=x['id']).display_name}**" for x in members if x["noble"]]
        embed.add_field(name="Nobles", value=", ".join(nobles))

        embed.add_field(name="initials", value=house["initials"])

        lands = await self.bot.query_executer("SELECT * FROM Lands WHERE owner=$1", house["id"])
        embed.add_field(name="Lands", value=len(lands))

        embed.add_field(name="Role", value=discord.utils.get(ctx.guild.roles, id=house["role"]).mention)
        embed.add_field(name="Channel", value=discord.utils.get(ctx.guild.channels, id=house["channel"]).mention)

    @commands.command()
    async def pledge(self, ctx, *, house : HouseConverter):
        """Pledge yourself to a house. Only works if you are currently part of the House of the Raccoon.

        Usage: `w!pledge [house]`

        __Exmaples__
        `w!pledge House of Tico` - join the house of tico
        `w!pledge 4` - join the house with id 4
        """
        if (await self.bot.query_executer("SELECT house from Members WHERE id=$1", ctx.author.id))[0][0] != 1:
            return await ctx.send(":negative_squared_cross_mark: | You are already part of a house you snake")

        if house["id"] in [1, 2]:
            await ctx.send(":negative_squared_cross_mark: | You cannot join this house, if you wish to leave your house use `w!renounce`")

        def reaction_check(reaction, user):
            if not reaction.message.id == msg.id or not user.id == ctx.author.id:
                return False

            if reaction.emoji in ["\N{NEGATIVE SQUARED CROSS MARK}", "\N{WHITE HEAVY CHECK MARK}"]:
                return True

            return False

        msg = await ctx.send(f"Do you wish to join the **{house['name']}**? React with :white_check_mark: if you do, else react with :negative_squared_cross_mark:")
        
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        reaction, _ = await self.bot.wait_for("reaction_add", check=reaction_check, timeout=300)

        if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            try:
                await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, id=house["role"]))
            except discord.Forbidden:
                await ctx.send(":negative_squared_cross_mark: | Unable to add role")

            await self.bot.query_executer("UPDATE Members SET house=$2 WHERE id=$1", ctx.author.id, house["id"])
            await ctx.send(f"Welcome to the {house['name']}")

        await msg.clear_reactions()            

    @commands.command()
    async def renounce(self, ctx):
        """Leave your current house and become a denizen of the House of the Raccoon once again.

        Usage: `w!renounce`
        """
        house_id = (await self.bot.query_executer("SELECT house FROM Members WHERE id=$1", ctx.author.id))[0][0]
        if house_id == 1:
            return await ctx.send(":negative_squared_cross_mark: | You are not part of any houses")

        house = await HouseConverter().convert(ctx, house_id)

        try:
            await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, id=house["role"]))
        except discord.Forbidden:
            await ctx.send(":negative_squared_cross_mark: | Unable to remove role")

        await self.bot.query_executer("UPDATE Members SET house=1 WHERE id=$1", ctx.author.id)
        await ctx.send(":white_check_mark: | You have left your house, you are now a free man once again.")

    @commands.group()
    @commands.has_role("Noble Racoon")
    async def edit(self, ctx, field, *, value):
        """Allows nobles of a house to edit the description and initials of a house. Changes made must be approved by
        all other nobles. Possible options for the the field paramater are:
            - description
            - initials

        Usage: `w!edit [field] [value]`

        __Examples__
        `w!edit description This is the best house.` - change the description of your house to "This is the best house.".
        `w!edit initials tic` - change the initials of your house to "tic"

        """
        house = await self.bot.query_executer("SELECT house FROM Members WHERE id=$1 AND noble='True'", ctx.author.id)       
        if not house:
            return await ctx.send(":negative_squared_cross_mark: | You cannot edit the history of your house")

        house = house[0][0]
        nobles = [discord.utils.get(ctx.guild.members, id=x["id"]) for x in await self.bot.query_executer("SELECT * FROM Members WHERE house=$1 AND noble='True'", house)]

        field = field.lower()
        if field in ["description", "initials"]:
            await self.bot.update_names()
            await self.string_validator(ctx, self.bot.fields[field], nobles, value)


            if not self.bot.fields[field]["check"](value):
                return await ctx.send(f":negative_squared_cross_mark: | {self.bot.fields[field]['req']}")

            await self.bot.query_executer("UPDATE House SET $1=$2 WHERE id=$3", field, value, house)
        else:
            await ctx.send(":negative_squared_cross_mark: | Not one of the given options")

