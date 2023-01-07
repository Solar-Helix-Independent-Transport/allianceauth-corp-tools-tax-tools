import datetime
import json
import logging

from allianceauth.services.tasks import QueueOnce
from celery import chain, shared_task
from django.core.cache import cache

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
