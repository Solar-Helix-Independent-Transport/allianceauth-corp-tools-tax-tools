# Cog Stuff
import datetime
import io
import logging
from typing import Optional

import discord
from discord import Embed, SlashCommandGroup, option, ui
from discord.ext import commands
from discord.utils import get_or_fetch

# AA Contexts
from django.conf import settings
from django.utils import timezone

from allianceauth.services.modules.discord.models import DiscordUser

from taxtools.models import CorpTaxConfiguration
from taxtools.tasks import send_tax_status

logger = logging.getLogger(__name__)


try:
    from django_redis import get_redis_connection
    _client = get_redis_connection("default")
except (NotImplementedError, ModuleNotFoundError):
    from django.core.cache import caches
    default_cache = caches['default']
    _client = default_cache.get_master_client()

cache_client = _client


def sender_is_su(author):
    id = author.id
    try:
        has_perm = DiscordUser.objects.get(
            uid=id).user.is_superuser
        if has_perm:
            return True
        else:
            return False
    except Exception as e:
        return False


class Taxes(commands.Cog):
    """
        Tax Related thingies
    """

    def __init__(self, bot):
        self.bot = bot

    comp_commands = SlashCommandGroup("tax", "tax", guild_ids=[
                                      int(settings.DISCORD_GUILD_ID)])

    @comp_commands.command(name='pending', guild_ids=[int(settings.DISCORD_GUILD_ID)])
    async def slash_tax_pending(
        self,
        ctx
    ):
        """
            Run this to see current outstanding tax
        """
        if not sender_is_su(ctx.user):
            return await ctx.respond("Missing Permissions...", ephemeral=True)
        await ctx.defer(ephemeral=True)
        send_tax_status.delay(channel_id=ctx.channel_id)
        await ctx.respond("Requested Tax Stats!", ephemeral=True)

    @comp_commands.command(name='status', guild_ids=[int(settings.DISCORD_GUILD_ID)])
    async def slash_tax_status(
        self,
        ctx
    ):
        """
            Run this to see current tax configuration
        """
        if not sender_is_su(ctx.user):
            return await ctx.respond("Missing Permissions...", ephemeral=True)
        await ctx.defer(ephemeral=False)
        ct = CorpTaxConfiguration.objects.get(pk=1)
        taxes = {}
        for tax in ct.character_ratting_included.all():
            _type = "Ratting"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_discord__())

        for tax in ct.character_taxes_included.all():
            _type = "Character Activity"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_discord__())

        for tax in ct.corporate_taxes_included.all():
            _type = "Corporate Activity"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_discord__())

        for tax in ct.corporate_member_tax_included.all():
            _type = "Corporate Members"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_discord__())

        for tax in ct.corporate_structure_tax_included.all():
            _type = "Structure Services"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_discord__())

        embed = Embed(title="Tax Status!",
                      description=f"See below configured taxes for `{ct.Name}`!")
        for t, d in taxes.items():
            embed.add_field(name=t, value="\n".join(d), inline=False)

        included_alliances = ", ".join(ct.included_alliances.all().values_list(
            "alliance_name", flat=True))
        if not len(included_alliances):
            included_alliances = "None"

        exempted_corps = ", ".join(ct.exempted_corps.all().values_list(
            "corporation_name", flat=True))
        if not len(exempted_corps):
            exempted_corps = "None"

        embed.add_field(name="Included Alliances", value=f"`{included_alliances}`")
        embed.add_field(name="Exempted Corps", value=f"`{exempted_corps}`")

        await ctx.respond(embed=embed, ephemeral=False)


def setup(bot):
    bot.add_cog(Taxes(bot))
