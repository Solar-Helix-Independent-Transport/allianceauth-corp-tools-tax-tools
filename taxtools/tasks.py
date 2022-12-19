import datetime
import json
import logging

from allianceauth.services.tasks import QueueOnce
from celery import shared_task
from django.core.cache import cache

from . import models

logger = logging.getLogger(__name__)


@shared_task(bind=True, base=QueueOnce)
def send_invoices_for_config_id(self, config_id=1):
    """
        Send invoices. job done...
    """
    tc = models.CorpTaxConfiguration.objects.get(id=config_id)
    tax = tc.send_invoices()
    return tax['taxes']
