import logging
from datetime import datetime, timezone
from decimal import Decimal
from email.policy import default
from typing import Dict

import yaml
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from corptools.models import (CharacterWalletJournalEntry,
                              CorporationWalletJournalEntry, EveLocation,
                              EveName, Notification)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, Max, Min, Sum
from esi.models import Token

logger = logging.getLogger(__name__)


class CharacterPayoutTaxConfiguration(models.Model):

    corporation = models.ForeignKey(
        EveName,
        on_delete=models.CASCADE,
        limit_choices_to={'category': "corporation"},
    )

    wallet_transaction_type = models.CharField(max_length=150)

    tax = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    def __str__(self):
        return self.corporation.name

    class Meta:
        permissions = (
            ('access_tax_tools_ui', 'Can View Tax Tools UI'),
        )

    def get_payment_data(self, start_date=datetime.min, end_date=datetime.max):
        return CharacterWalletJournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            ref_type=self.wallet_transaction_type,
            first_party_name_id=self.corporation_id
        ).exclude(taxed__processed=True)

    def get_aggregates(self, start_date=datetime.min, end_date=datetime.max):
        return self.get_payment_data(start_date, end_date).values(
            char=F('character__character__character_id')
        ).annotate(
            sum_amount=Sum('amount', distinct=True),
            tax_amount=(Sum('amount', distinct=True)*(self.tax/100)),
            cnt_amount=Count('amount', distinct=True),
            min_date=Min('date'),
            max_date=Max('date'),
        ).values(
            'char',
            'sum_amount',
            'tax_amount',
            'cnt_amount',
            'max_date',
            'min_date',
            main=F(
                'character__character__character_ownership__user__profile__main_character__character_id'
            )
        )


class CharacterPayoutTaxRecord(models.Model):
    entry = models.OneToOneField(
        CharacterWalletJournalEntry, on_delete=models.CASCADE, related_name="taxed")

    processed = models.BooleanField(default=True)


class CharacterPayoutTaxHistory(models.Model):
    entry = models.ForeignKey(
        CharacterPayoutTaxConfiguration, on_delete=models.CASCADE)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


# CorpTaxChangeMsg
class CorpTaxHistory(models.Model):
    corp = models.ForeignKey(
        EveCorporationInfo, on_delete=models.CASCADE)

    start_date = models.DateTimeField()
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    class Meta:
        unique_together = [['corp', 'start_date']]

    @classmethod  # TODO make a manager if i want to long term use this.
    def get_corp_tax_list(cls, corp_id: int):
        taxes = cls.objects.filter(
            corp__corporation_id=corp_id
        ).values(
            "start_date",
            "tax_rate"
        ).order_by('start_date')
        return list(taxes)

    @classmethod
    def find_corp_tax_changes(cls, corp_id: int):
        notes = Notification.objects.filter(
            character__character__corporation_id=corp_id,
            notification_type="CorpTaxChangeMsg"
            # TODO date limit this depending on the last instance
        ).order_by(
            'timestamp',  # Notifications are "minute" accurate
            # if 2 the same take the higher ID? hopefully...
            'notification_id'
        ).values(
            'notification_id',
            'timestamp',
            'notification_text__notification_text'
        ).distinct()

        changes = {}

        for n in notes:
            data = yaml.safe_load(n['notification_text__notification_text'])
            if data['corpID'] == corp_id:
                t = datetime.timestamp(n['timestamp'])
                changes[t] = {"tax_rate": data['newTaxRate'],
                              "start_date": n['timestamp']}

        return list(changes.values())

    @classmethod  # TODO make a manager if i want to long term use this.
    def sync_corp_tax_changes(cls, corp_id: int):
        corp = EveCorporationInfo.objects.get(corporation_id=corp_id)
        taxes = cls.find_corp_tax_changes(corp_id)
        db_models = []
        for t in taxes:
            db_models.append(
                cls(
                    corp=corp,
                    start_date=t['start_date'],
                    tax_rate=t['tax_rate']
                )
            )
        created = cls.objects.bulk_create(db_models, ignore_conflicts=True)
        return len(created)

    @classmethod
    def get_tax_rate(cls, corp_id, date, tax_rates: list = None):
        if not tax_rates:
            tax_rates = cls.get_corp_tax_list(corp_id)

        rate = 0
        # force it to be in order
        tax_rates.sort(key=lambda i: i['start_date'])

        for tr in tax_rates:
            if tr['start_date'] < date:
                rate = tr['tax_rate']
        return rate


class CorpTaxPayoutTaxConfiguration(models.Model):
    corporation = models.ForeignKey(
        EveName,
        on_delete=models.CASCADE,
        limit_choices_to={'category': "corporation"},
    )

    wallet_transaction_type = models.CharField(max_length=150)

    tax = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    def __str__(self):
        return self.corporation.name

    def get_payment_data(self, start_date=datetime.min, end_date=datetime.max):
        return CorporationWalletJournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            ref_type=self.wallet_transaction_type,
            first_party_name_id=self.corporation_id
        ).exclude(taxed__processed=True).select_related(
            "division__corporation__corporation",
            "first_party_name",
            "second_party_name"
        )

    def get_aggregates(self, start_date=datetime.min, end_date=datetime.max, full=True):
        output = {}
        tax_cache = {}
        trans_ids = set()
        for w in self.get_payment_data(start_date=start_date, end_date=end_date):
            if w.entry_id not in trans_ids:
                cid = w.division.corporation.corporation.corporation_id
                if cid not in tax_cache:
                    tax_cache[cid] = CorpTaxHistory.get_corp_tax_list(cid)
                if not len(tax_cache[cid]):
                    logger.debug(f"Corp: {cid} Has no tax data saved atm")
                    continue
                trans_ids.add(w.entry_id)
                if cid not in output:
                    output[cid] = {
                        "characters": [],
                        "trans_ids": [],
                        "sum": 0,
                        "earn": 0,
                        "tax": 0,
                        "cnt": 0,
                        "end": datetime.min.replace(tzinfo=timezone.utc),
                        "start": datetime.max.replace(tzinfo=timezone.utc)
                    }

                rate = CorpTaxHistory.get_tax_rate(
                    cid, w.date, tax_rates=tax_cache[cid])
                total_value = w.amount/(Decimal(rate/100))

                output[cid]["sum"] += w.amount
                output[cid]["earn"] += total_value
                output[cid]["tax"] += total_value*(self.tax/100)

                output[cid]["cnt"] += 1

                if full:
                    output[cid]["trans_ids"].append(w.entry_id)

                if w.second_party_name.name not in output[cid]["characters"]:
                    output[cid]["characters"].append(w.second_party_name.name)
                if w.date < output[cid]["start"]:
                    output[cid]["start"] = w.date
                if w.date > output[cid]["end"]:
                    output[cid]["end"] = w.date
        return output


class CorporatePayoutTaxRecord(models.Model):
    entry = models.OneToOneField(
        CorporationWalletJournalEntry, on_delete=models.CASCADE, related_name="taxed")

    processed = models.BooleanField(default=True)
