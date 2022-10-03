import logging

from allianceauth.eveonline.models import EveCharacter
from corptools.models import EveItemType, EveLocation
from corptools.providers import esi
from corptools.schema import CharacterWalletEvent
from corptools.task_helpers.corp_helpers import get_corp_token
from django.conf import settings
from ninja import NinjaAPI
from ninja.responses import codes_4xx
from ninja.security import django_auth
from typing import List

from . import models

logger = logging.getLogger(__name__)

api = NinjaAPI(title="Tax Tools API", version="0.0.1",
               urls_namespace='taxtools:api', auth=django_auth, csrf=True,)
# openapi_url=settings.DEBUG and "/openapi.json" or "")


@api.get(
    "corp/tax/list",
    tags=["Corp Taxes"],
    response={200: List[CharacterWalletEvent]},
)
def get_tax_data(request):
    if not request.user.is_superuser:
        return []

    t = models.CorpPayoutTaxConfiguration.objects.all().first()

    output = []
    for w in t.get_payment_data():
        output.append(
            {
                "character": w.character.character,
                "id": w.entry_id,
                "date": w.date,
                "first_party": {
                    "id": w.first_party_id,
                    "name": w.first_party_name.name,
                    "cat": w.first_party_name.category,
                },
                "second_party":  {
                    "id": w.second_party_id,
                    "name": w.second_party_name.name,
                    "cat": w.second_party_name.category,
                },
                "ref_type": w.ref_type,
                "amount": w.amount,
                "balance": w.balance,
                "reason": w.reason,
            })

    return output


@api.get(
    "corp/tax/aggregates",
    tags=["Corp Taxes"],
)
def get_tax_aggregates(request):
    if not request.user.is_superuser:
        return []

    t = models.CorpPayoutTaxConfiguration.objects.all().first()
    tx = t.get_aggregates()
    output = []

    for w in tx:
        output.append(
            {
                "character": w['char'],
                "sum": w['sum_amount'],
                "tax": w['tax_amount'],
                "main": w['main'],
            }
        )

    return output
