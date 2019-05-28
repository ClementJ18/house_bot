import discord
from discord.ext import commands
from .utils.utils import HouseConverter, reaction_check_factory, react_menu, RarityCategory, ConditionStatus, \
                         get_house_from_member

import asyncio
import random
import dice
import datetime

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

    async def calculate_modifiers(self, attacker, defender, land):
        landmarks = await self.bot.query_executer("SELECT attack, defense, capped FROM houses.Landmarks WHERE location=$1", land["id"])
        atk_modifiers = await self.bot.query_executer("SELECT attack, capped FROM houses.Artefacts WHERE owner = $1", attacker["id"])
        def_modifiers = await self.bot.query_executer("SELECT defense capped FROM houses.Artefacts WHERE owner = $1", defender["id"])

        atk_modifiers.extend([[x[0], x[2]] for x in landmarks])
        def_modifiers.extend([[x[1], x[2]] for x in landmarks])

        def calc(sequence):
            capped = 0
            uncapped = 0
            for modifier in :
                if modifier[1]:
                    capped += modifier[0]
                else:
                    uncapped += modifier[0]

            return min(0.50, capped) + uncapped 

        modifiers_atk = calc(atk_modifiers)
        modifiers_def = calc(def_modifiers)

        if defender["id"] == 2:
            modifiers_def = 0

        return modifiers_atk, modifiers_def

    async def calculate_strengths(self, ctx, house, attacker, defender):
        members_atk = [x for x in ctx.guild.members if x.id in [y[0] for y in await self.bot.query_executer("SELECT id FROM houses.Members WHERE house=$1", attacker["id"])]]
        strength_atk = 0
        for member in members_atk:
            strength_atk += self.bot.strengths[discord.utils.find(lambda x: x in self.bot.strengths, [x.id for x in member.roles])]
        # strength_atk = len(members_atk)

        if house["id"] == 2:
            strength_def = round(strength_atk * 0.66)
        else:
            members_def = [x for x in ctx.guild.members if x.id in [y[0] for y in await self.bot.query_executer("SELECT id FROM houses.Members WHERE house=$1", defender["id"])]]
            strength_def = 0
            for member in members_def:
                strength_def += self.bot.strengths[discord.utils.find(lambda x: x in self.bot.strengths, [x.id for x in member.roles])]
            # strength_def = len(members_def)

        return strength_atk, strength_def

    @commands.command()
    async def houses(self, ctx):
        """Show a list of all houses.

        Usage: `w!houses`
        """
        houses = await self.bot.query_executer("SELECT * FROM houses.Houses WHERE id > 2 AND active='True'")

        def embed_generator(page):
            embed = discord.Embed(title="Houses of the Raccoon Kingdom", description="List of all the houses of the raccoon kingdom")

            for house in houses[page*5:(page+1)*5]:
                embed.add_field(name=f'{house["name"]} ({house["id"]})', value=house["description"], inline=False)

            return embed

        await react_menu(ctx, len(houses)//5, embed_generator)

    @commands.command()
    async def lands(self, ctx, *, house : HouseConverter = None):
        """Show a list of all lands.

        Usage: `w!lands [house]`

        __Examples__
        - `w!lands` - show all the lands
        - `w!lands House of Tico` - show all the lands owned by house of tico
        """
        if house:
            lands = await self.bot.query_executer("SELECT l.id, l.name, l.description, h.name, h.id FROM houses.Lands l, houses.Houses h WHERE l.owner = $1 AND h.id = $1", house["id"])
        else:
            lands = await self.bot.query_executer("SELECT l.id, l.name, l.description, h.name, h.id FROM houses.Lands l, houses.Houses h WHERE l.owner = h.id")

        def embed_generator(page):
            embed = discord.Embed(title="Lands of the Raccoon Kingdom", description="List of all the lands of the raccoon kingdom")

            for land in lands[page*5:(page+1)*5]:
                embed.add_field(name=f'{land[1]} ({land[0]})', value=f'{land[2]}\n**Owner**: {land[3]}({land[4]})', inline=False)

            return embed

        await react_menu(ctx, len(lands)//5, embed_generator)

    @commands.command()
    async def artefacts(self, ctx, *, house : HouseConverter = None):
        """Show a list of all the artefacts.

        Usage: `w!artefacts [house]`

        __Examples__
        - `w!artefacts` - show all the artefacts
        - `w!artefacts House of Tico` - show all the artefacts owned by house of tico
        """
        if house:
            if house["id"] == 2:
                return await ctx.send(":negative_squared_cross_mark: | You cannot see the artefacts for this house.")

            modifiers = await self.bot.query_executer("SELECT m.id, m.name, m.description, h.name, h.id FROM houses.Artefacts m, houses.Houses h WHERE m.owner = $1 AND h.id = $1", house["id"])
        else:
            modifiers = await self.bot.query_executer("SELECT m.id, m.name, m.description, h.name, h.id FROM houses.Artefacts m, houses.Houses h WHERE m.owner = h.id AND m.owner != 2")

        def embed_generator(page):
            embed = discord.Embed(title="Artefacts of the Raccoon Kingdom", description="List of all the artefacts of the raccoon kingdom")

            for modifier in modifiers[page*5:(page+1)*5]:
                embed.add_field(name=f'{modifier[1]} ({modifier[0]})', value=f'{modifier[2]}\n**Owner**: {modifier[3]}({modifier[4]})', inline=False)

            return embed

        await react_menu(ctx, len(modifiers)//5, embed_generator)


    @commands.command()
    async def attack(self, ctx, *, house : HouseConverter):
        """Attack a house. This is a command heavy of consequences, do not use it lightly, in addition,
        it has a 4 day cooldown. You cannot attack houses that were created in the last 7 days except if
        they have attacked someone themselves. You cannot attack a house you are in an alliance with or were
        with in the last 4 days. You cannot attack the House of the Raccoon

        Usage: `w!attack [house]`

        __Examples__
        `w!attack House of Tico` - Attack the House of Tico
        `w!attack 4` - Attack the house with the id 4
        """
        attacker = await get_house_from_member(ctx.author.id, noble=True)
        if not attacker:
            return await ctx.send(":negative_squared_cross_mark: | You are not allowed to order an attack")       

        defender = house

        if attacker["id"] == defender["id"]:
            return await ctx.send(":negative_squared_cross_mark: | You cannot attack yourself.")

        last_attack_atk = await self.bot.query_executer("SELECT created_at FROM houses.Battles WHERE attacker = $1 ORDER BY created_at DESC LIMIT 1", attacker["id"])
        if last_attack_atk[0][0].replace(tzinfo=None) + datetime.timedelta(days=4) > datetime.datetime.now():
            return await ctx.send(":negative_squared_cross_mark: | You can only attack once every 4 days")

        last_attack_def = await self.bot.query_executer("SELECT * FROM houses.Battles WHERE attacker = $1 AND aid='False'", defender["id"])
        if not last_attack_def and defender["created_at"].replace(tzinfo=None) + datetime.timedelta(days=14) > datetime.datetime.now():
            return await ctx.send(":negative_squared_cross_mark: | This house is still in its grace period, you cannot attack it.")

        alliance = self.bot.query_executer("SELECT * FROM houses.Alliances WHERE (house1 = $1 AND house2 = $2) OR (house1 = $2 AND house2 = $1) AND (broken IS NULL OR broken < NOW() - interval '7 days')", attacker["id"], defender["id"])
        if alliance:
            return await ctx.send(":negative_squared_cross_mark: | You cannot attack a house you are or recently were in an alliance with.")

        land = random.choice(await self.bot.query_executer("SELECT * FROM houses.Lands WHERE owner=$1", house["id"]))
        
        strength_atk, strength_def = await self.calculate_strengths(ctx, house, attacker, defender)
        modifiers_atk, modifiers_def = await self.calculate_modifiers(attacker, defender, land)
        
        while strength_def > 0 and strength_atk > 0: 

            #battle advantage capped at half of the winning house's strength  
            raw_battle_advantage = min(strength_atk//2, strength_atk - strength_def) if strength_atk - strength_def > 0 else max(strength_def//2, strength_atk - strength_def)
            battle_advantage = raw_battle_advantage * (modifiers_atk + 1 - modifiers_def)

            dice_atk = dice.roll("1d100")[0]
            dice_def = dice.roll("1d100")[0]

            battle = (dice_atk + battle_advantage) - dice_def

            string = random.choice(self.bot.soldier_strings)
            if battle > 0:
                soldier_lost_b = random.choice(list(range(1, battle//2+1)))
                strength_def -= soldier_lost_b
                await ctx.send(string.format(house=defender["name"], soldiers=soldier_lost_b))
            elif battle < 0:
                soldier_lost_a = random.choice(list(range(1, abs(battle)//2+1)))
                strength_atk -= soldier_lost_a
                await ctx.send(string.format(house=attacker["name"], soldiers=soldier_lost_a))
            else:
                await ctx.send("Both houses stare at each other, but neither moves in.")

            # await asyncio.sleep(600)

        if strength_atk > 0:
            await ctx.send(f":white_check_mark: | {attacker['name']} has won and successfully seized **{land['name']}**")
            victor = attacker
            base_prisoner = 0.1
            defeated = defender

        if strength_def > 0:
            await ctx.send(f":white_check_mark: | {defender['name']} has won and successfully defended **{land['name']}**")
            victor = defender
            base_prisoner = 0.2
            defeated = attacker

        prisoner_artefacts = await self.bot.query_executer("SELECT prisoner, capped FROM houses.Artefacts WHERE owner=$1", victor["id"])
        capped = 0
        uncapped = 0
        for artefact in prisoner_artefacts:
            if artefact[1]:
                capped += artefact[0]
            else:
                capped += artefact[0]

        prisoner_chance = uncapped + base_prisoner + min(0.2, capped)

        if random.random() < prisoner_chance:
            nobles = await self.bot.query_executer("SELECT * FROM houses.Members WHERE house=$1 AND noble='True' AND NOT EXIST (SELECT id FROM houses.Prisoners)", defeated["id"])
            prisoner = random.choice(nobles)
            await self.bot.take_prisoner(ctx, discord.utils.get(ctx.members, id=prisoner[0]), victor["id"])

        await self.bot.log_battle(ctx, land, attacker["id"], victor["id"])

    @commands.command()
    async def map(self, ctx):
        """Show a map of the realm.

        Usage: `w!map`
        """
        file = discord.File("rings/utils/map.png")
        await ctx.send(file=file)

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
        nobles = list(set(nobles))
        if any(x.id == 312324424093270017 for x in nobles):
            return await ctx.send(":negative_squared_cross_mark: | You cannot ask the King to join your House")

        if len(nobles) != 3:
            return await ctx.send(":negative_squared_cross_mark: | Please select exactly three nobles to be part of the house")

        if any(discord.utils.get(member.roles, name="Noble Raccoon") is None for member in nobles):
            return await ctx.send(":negative_squared_cross_mark: | All users must have the `Noble Raccoon` role.")

        raw_royals = await self.bot.query_executer("SELECT FROM houses.Members WHERE id=ANY($1) AND noble='True'", [x.id for x in nobles])
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
        for field in self.bot.fields.values():            
            def message_check(message):
                return ctx.author.id == message.author.id and ctx.channel.id == message.channel.id and field['check'](message.content)

            await ctx.send(f"Now please, {ctx.author.mention}, pick a {field['name']} for the house and all the nobles will have to agree to it. {field['req']}")
            message = await self.bot.wait_for("message", check=message_check, timeout=600)
            values[field["name"]] = await self.string_validator(ctx, field, nobles, message.content)

        role = await ctx.guild.create_role(
            name=values["name"]
        )

        channel = await ctx.guild.create_text_channel(
            values["name"], 
            category=discord.utils.get(ctx.guild.channels, name="Family Halls"),
            overwrites={
                role : discord.PermissionOverwrite(read_messages=True),
                ctx.guild.default_role : discord.PermissionOverwrite(read_messages=False)
            }
        )
        result = await self.bot.query_executer(
            "INSERT INTO houses.Houses(name, initials, description, role, channel) VALUES ($1, $2, $3, $4, $5) RETURNING id;",
            values["name"], values["initials"], values["description"], role.id, channel.id, fetchval=True
        )
        await self.bot.query_executer("UPDATE houses.Members SET house=$2, noble='True' WHERE id=ANY($1)", [x.id for x in nobles], result)

        for royal in nobles:
            try:
                await royal.add_roles(role)
            except discord.Forbidden:
                await ctx.send(f":negative_squared_cross_mark: | Couldn't add the role for **{royal.display_name}**")

        await ctx.send(f"Alright, the {values['name']} has been created. Long may it endure.")

        land = random.choice(await self.bot.query_executer("SELECT * FROM houses.Lands WHERE owner=2"))
        await self.bot.log_battle(ctx, land, result, result, aid=True)

        await self.bot.query_executer(
            """INSERT INTO houses.Artefacts(name, description, defense, owner, rarity, condition, hidden) 
            VALUES($1, $2, $3, $4, $5, $6, $7)""",
            f'Banner of {values["name"]}', f'The proud banner of the house, symbol of its might.', 0, 
            result, RarityCategory.rare, ConditionStatus.gift, False
        )

    @commands.command()
    @commands.has_role("Noble Raccoon")
    async def disband(self, ctx):
        """Disbands the house. This does not remove the house completly but rather de-activates it, users will be
        removed from the house and you will no longer be able to join it. You will still be able to ead about this
        house's history in the logs but you won't be able to interact with it. All nobles from the house will have to
        agree on disbanding the house once the command has been called.

        Usage: `w!disband`
        """
        house_id =  await self.bot.query_executer("SELECT house FROM houses.house.Members where id=$1;", ctx.author.id)
        query = await self.bot.query_executer("SELECT id FROM houses.Members WHERE house=$1 AND noble='True';", house_id)

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
            await self.bot.disband_house(ctx, house_id)
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
            house = await get_house_from_member(ctx.author.id)

        members = await self.bot.query_executer("SELECT * FROM houses.Members WHERE house=$1", house["id"])
        embed = discord.Embed(title=f'{house["name"]} ({house["id"]})', description=house["description"])
        embed.add_field(name="Members", value=len(members))

        nobles = [discord.utils.get(ctx.guild.members, id=x['id']).mention for x in members if x["noble"]]
        embed.add_field(name="Nobles", value=", ".join(nobles))

        embed.add_field(name="initials", value=house["initials"])

        lands = await self.bot.query_executer("SELECT * FROM houses.Lands WHERE owner=$1", house["id"])
        embed.add_field(name="Lands", value=len(lands))

        embed.add_field(name="Creation Date", value=str(house["created_at"]))

        if house["id"] > 2:
            embed.add_field(name="Role", value=discord.utils.get(ctx.guild.roles, id=house["role"]).mention)
            embed.add_field(name="Channel", value=discord.utils.get(ctx.guild.channels, id=house["channel"]).mention)

        if ctx.channel.id == house["channel"]:
            #extra info 1
            pass

            if ctx.author.id in [x for x in members if x["noble"]]:
                #extra info 2
                pass

        await ctx.send(embed=embed)

    @commands.command()
    async def pledge(self, ctx, *, house : HouseConverter):
        """Pledge yourself to a house. Only works if you are currently part of the House of the Raccoon.

        Usage: `w!pledge [house]`

        __Exmaples__
        `w!pledge House of Tico` - join the house of tico
        `w!pledge 4` - join the house with id 4
        """
        if (await self.bot.query_executer("SELECT house from Members WHERE id=$1", ctx.author.id))[0][0] != 1:
            return await ctx.send(":negative_squared_cross_mark: | You are already part of a house you snake, if you wish to leave your house use `w!renounce`")

        if house["id"] < 3:
            await ctx.send(":negative_squared_cross_mark: | You cannot join this house")

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

            await self.bot.query_executer("UPDATE houses.Members SET house=$2 WHERE id=$1", ctx.author.id, house["id"])
            await ctx.send(f"Welcome to the {house['name']}")

        await msg.clear_reactions()            

    @commands.command()
    async def renounce(self, ctx):
        """Leave your current house and become a denizen of the House of the Raccoon once again.

        Usage: `w!renounce`
        """
        house_id = (await self.bot.query_executer("SELECT house FROM houses.Members WHERE id=$1", ctx.author.id))[0][0]
        if house_id == 1:
            return await ctx.send(":negative_squared_cross_mark: | You are not part of any houses")

        house = await HouseConverter().convert(ctx, house_id)

        try:
            await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, id=house["role"]))
        except discord.Forbidden:
            await ctx.send(":negative_squared_cross_mark: | Unable to remove role")

        await self.bot.query_executer("UPDATE houses.Members SET house=1 WHERE id=$1", ctx.author.id)
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
        house = await self.bot.query_executer("SELECT house FROM houses.Members WHERE id=$1 AND noble='True'", ctx.author.id)       
        if not house:
            return await ctx.send(":negative_squared_cross_mark: | You cannot edit the history of your house")

        house = house[0][0]
        nobles = [discord.utils.get(ctx.guild.members, id=x["id"]) for x in await self.bot.query_executer("SELECT * FROM houses.Members WHERE house=$1 AND noble='True'", house)]

        field = field.lower()
        if field in ["description", "initials"]:
            await self.bot.update_names()
            await self.string_validator(ctx, self.bot.fields[field], nobles, value)


            if not self.bot.fields[field]["check"](value):
                return await ctx.send(f":negative_squared_cross_mark: | {self.bot.fields[field]['req']}")

            await self.bot.query_executer(f"UPDATE houses.Houses SET {field}=$1 WHERE id=$2", value, house)
            await ctx.send(f":white_check_mark: | {field} is now: {value}")
        else:
            await ctx.send(":negative_squared_cross_mark: | Not one of the given options")

    @commands.group()
    async def alliance(self, ctx):
        pass

    @alliance.command(name="create")
    async def alliance_create(self, ctx, *, house : HouseConverter):
        proposer = await get_house_from_member(ctx.author.id)
        alliance = self.bot.query_executer("SELECT * FROM houses.Alliances WHERE (house1 = $1 AND house2 = $2) OR (house1 = $2 AND house2 = $1) AND broken IS NULL", house["id"], proposer["id"])

        if alliance:
            return await ctx.send(":negative_squared_cross_mark: | You already have an alliance with this house")

        nobles = [discord.utils.get(ctx.guild.members, id=x).mention for x in await self.bot.query_executer("SELECT * FROM houses.Members WHERE noble = 'True' AND (house=$1 or house=$2)", proposer["id"], house["id"])]

        msg = await ctx.send(f"{', '.join([x.mention for x in nobles])}, do you all agree to ally your houses?")

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check_factory(msg, nobles), timeout=500)

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            return await ctx.send(f":negative_squared_cross_mark: | **{user.display_name}** is opposed to this alliance")

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await ctx.send(f":white_check_mark: | **{proposer['name']}** and **{house['name']}** are now allied.")
            await self.bot.query_executer("INSERT INTO houses.Alliances VALUES($1, $2)", house["id"], proposer["id"])

    @alliance.command(name="cancel")
    async def alliance_cancel(self, ctx, *, house : HouseConverter):
        proposer = await get_house_from_member(ctx.author.id)
        alliance = self.bot.query_executer("SELECT * FROM houses.Alliances WHERE (house1 = $1 AND house2 = $2) OR (house1 = $2 AND house2 = $1 AND broken IS NULL)", house["id"], proposer["id"])

        if not alliance:
            return await ctx.send(":negative_squared_cross_mark: | You don't have any alliances with this house")

        nobles = [discord.utils.get(ctx.guild.members, id=x).mention for x in await self.bot.query_executer("SELECT * FROM houses.Members WHERE noble = 'True' AND house=$1", proposer["id"])]

        msg = await ctx.send(f"{', '.join([x.mention for x in nobles])}, do you all agree to break this alliance?")

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check_factory(msg, nobles), timeout=500)

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            return await ctx.send(f":negative_squared_cross_mark: | **{user.display_name}** is opposed to breaking this alliance")

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await ctx.send(f":white_check_mark: | The alliance between **{proposer['name']}** and **{house['name']}** is now broken.")
            await self.bot.query_executer("UPDATE houses.Alliances SET broken=NOW() WHERE broken IS NULL AND ((house1=$1 AND house2=$2) OR (house1=$2 AND house2=$1))", house["id"], proposer["id"])

    @commands.group()
    async def exchange(self, ctx):
        pass

    @exchange.command(name="artefact")
    async def exchange_weapon(self, ctx):
        pass

    @exchange.command(name="prisoner")
    async def exchange_prisoner(self, ctx,):
        pass
