import datetime
import json
import logging

from celery import chain, shared_task
from discord import Embed

from django.core.cache import cache

from allianceauth.services.tasks import QueueOnce

from . import models

logger = logging.getLogger(__name__)


@shared_task(bind=True, base=QueueOnce)
def send_invoices_for_config_id(self, config_id=1):
    """
        Send invoices.
    """
    tc = models.CorpTaxConfiguration.objects.get(id=config_id)
    tax = tc.send_invoices()
    return tax['taxes']


@shared_task(bind=True, base=QueueOnce)
def sync_all_corp_tax_rates(self):
    """
        Sync the tax rates.
    """
    return models.CorpTaxHistory.sync_all_corps()


@shared_task(bind=True, base=QueueOnce)
def send_taxes(self, config_id=1):
    """
        Sync all and send the invoices.
    """
    tasks = []
    tasks.append(sync_all_corp_tax_rates.si())
    tasks.append(send_invoices_for_config_id.si(config_id=config_id))

    chain(tasks).apply_async(priority=4)


@shared_task(bind=True, base=QueueOnce)
def send_tax_status(self, config_id=1, channel_id=0):
    if not channel_id:
        return "No Channel ID set"
    from aadiscordbot.tasks import send_message
    ct = models.CorpTaxConfiguration.objects.get(pk=config_id)
    start, end, data = ct.get_invoice_data()
    embed = Embed(title="Tax Pending",
                  description="Tax yet to be invoiced since last invoice date")
    embed.add_field(name="Start Date", value=start, inline=True)
    embed.add_field(name="End Date", value=end, inline=True)
    total = 0
    for c, d in data['taxes'].items():
        total += d['total_tax']
    embed.add_field(name="Corps to Invoice", inline=False,
                    value=f"{len(data['taxes'])}")

    if data['raw']['ratting']:
        embed.add_field(name="Ratting Tax", inline=True,
                        value=f"${data['raw']['ratting']:,}")
    if data['raw']['char']:
        embed.add_field(name="Character Activity Tax",
                        inline=True, value=f"${data['raw']['char']:,}")
    if data['raw']['corp']:
        embed.add_field(name="Corporate Activity Tax",
                        inline=True, value=f"${data['raw']['corp']:,}")
    if data['raw']['member']:
        embed.add_field(name="Member Taxes", inline=True,
                        value=f"${data['raw']['member']:,}")
    if data['raw']['structure']:
        embed.add_field(name="Structure Services Taxes",
                        inline=True, value=f"${data['raw']['structure']:,}")

    embed.add_field(name="Total Tax", inline=False, value=f"${total:,}")
    send_message(embed=embed, channel_id=channel_id)
