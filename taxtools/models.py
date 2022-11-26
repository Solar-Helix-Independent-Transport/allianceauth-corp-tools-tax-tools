import decimal
import logging
from calendar import c
from datetime import datetime, timezone
from decimal import Decimal
from email.policy import default
from typing import Dict

import yaml
from allianceauth.authentication.models import State
from allianceauth.eveonline.models import (EveAllianceInfo, EveCharacter,
                                           EveCorporationInfo)
from corptools.models import (CharacterWalletJournalEntry, CorporationAudit,
                              CorporationWalletJournalEntry, EveLocation,
                              EveName, MapRegion, Notification,
                              StructureService)
from corptools.providers import esi
from discord import annotations
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, Max, Min, Sum
from esi.models import Token

logger = logging.getLogger(__name__)

MIN_DATE = datetime.min.replace(tzinfo=timezone.utc)
MAX_DATE = datetime.max.replace(tzinfo=timezone.utc)


class CharacterPayoutTaxConfiguration(models.Model):
    name = models.CharField(max_length=50)

    corporation = models.ForeignKey(
        EveName,
        on_delete=models.CASCADE,
        limit_choices_to={'category': "corporation"},
        blank=True,
        null=True,
        default=None
    )

    wallet_transaction_type = models.CharField(max_length=150)

    tax = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    def __str__(self):
        return self.corporation.name

    class Meta:
        permissions = (
            ('access_tax_tools_ui', 'Can View Tax Tools UI'),
        )

    def get_payment_data(self, start_date=MIN_DATE, end_date=MAX_DATE):
        ref_types = self.wallet_transaction_type.split(",")
        return CharacterWalletJournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            ref_type__in=ref_types,
            first_party_name_id=self.corporation_id
        ).exclude(taxed__processed=True)

    def get_character_aggregates(self, start_date=MIN_DATE, end_date=MAX_DATE):
        data = self.get_payment_data(start_date, end_date).values(
            'amount',
            'entry_id',
            'date',
            'tax',
            char=F('character__character__character_id'),
            corp=F('character__character__corporation_id'),
            char_name=F('character__character__character_name'),
            main=F(
                'character__character__character_ownership__user__profile__main_character__character_id'
            ),
            main_corp=F(
                'character__character__character_ownership__user__profile__main_character__corporation_id'
            )
        )
        output = {}
        tax_cache = {}
        trans_ids = set()

        for d in data:
            if d['entry_id'] not in trans_ids:
                cid = d['char']
                if d['main']:
                    cid = d['main']
                crpid = d['corp']
                if crpid not in tax_cache:
                    tax_cache[crpid] = CorpTaxHistory.get_corp_tax_list(crpid)
                corp_details = esi.client.Corporation.get_corporations_corporation_id(
                    corporation_id=crpid
                ).result()
                current_rate = Decimal(
                    corp_details.get('tax_rate', 0.1)
                )
                rate = CorpTaxHistory.get_tax_rate(
                    cid, d['date'], tax_rates=tax_cache[crpid], default=current_rate*100)

                if cid not in output:
                    output[cid] = {
                        "characters": [],
                        "corp": d['main_corp'],
                        "trans_ids": [],
                        "tax_rates_used": [],
                        "sum_earn": 0,
                        "pre_tax_total": 0,
                        "tax_to_pay": 0,
                        "cnt": 0,
                        "end": MIN_DATE,
                        "start": MAX_DATE
                    }

                try:
                    total_value = d['amount']/(100-Decimal(rate))*100
                except (ZeroDivisionError, decimal.InvalidOperation):  # 100% tax
                    # take the tax amount from the transaction. This has been flakey tho. SO YMMV

                    if d['tax']:
                        total_value = d['tax']
                    else:
                        logger.debug(f"NO TAX or ISK Tax:{rate}% Data:{d}")
                        total_value = Decimal(0)

                output[cid]["sum_earn"] += d['amount']
                output[cid]["pre_tax_total"] += total_value
                output[cid]["tax_to_pay"] += total_value*(self.tax/100)

                output[cid]["cnt"] += 1

                output[cid]["trans_ids"].append(d['entry_id'])

                trans_ids.add(d['entry_id'])

                if rate not in output[cid]["tax_rates_used"]:
                    output[cid]["tax_rates_used"].append(rate)

                if d['char_name'] not in output[cid]["characters"]:
                    output[cid]["characters"].append(d['char_name'])

                if d['date'] < output[cid]["start"]:
                    output[cid]["start"] = d['date']

                if d['date'] > output[cid]["end"]:
                    output[cid]["end"] = d['date']

        return output

    def get_character_aggregates_corp_level(self, start_date=MIN_DATE, end_date=MAX_DATE, full=False):
        data = self.get_character_aggregates(start_date, end_date)
        output = {}
        for id, t in data.items():
            cid = t['corp']
            if cid not in output:
                output[cid] = {
                    "characters": [],
                    "trans_ids": [],
                    "tax_rates_used": [],
                    "sum_earn": 0,
                    "pre_tax_total": 0,
                    "tax_to_pay": 0,
                    "cnt": 0,
                    "end": MIN_DATE,
                    "start": MAX_DATE
                }
            output[cid]['characters'] += t['characters']
            if full:
                output[cid]['trans_ids'] += t['trans_ids']
            for tr in t['tax_rates_used']:
                if tr not in output[cid]['tax_rates_used']:
                    output[cid]['tax_rates_used'].append(tr)
            output[cid]['sum_earn'] += t['sum_earn']
            output[cid]['pre_tax_total'] += t['pre_tax_total']
            output[cid]['tax_to_pay'] += t['tax_to_pay']
            output[cid]['cnt'] += t['cnt']
            if t['start'] < output[cid]["start"]:
                output[cid]["start"] = t['start']

            if t['end'] > output[cid]["end"]:
                output[cid]["end"] = t['start']
        return output


class CharacterPayoutTaxRecord(models.Model):
    entry = models.OneToOneField(
        CharacterWalletJournalEntry, on_delete=models.CASCADE, related_name="taxed")

    processed = models.BooleanField(default=True)


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
    def get_tax_rate(cls, corp_id, date, tax_rates: list = None, default=10):
        if not tax_rates:
            tax_rates = cls.get_corp_tax_list(corp_id)

        rate = default
        # force it to be in order
        tax_rates.sort(key=lambda i: i['start_date'])

        for tr in tax_rates:
            if tr['start_date'] < date:
                rate = tr['tax_rate']
            else:
                break
        return rate

    @classmethod
    def sync_all_corps(cls):
        output = {}
        for c in CorporationAudit.objects.all():
            created = cls.sync_corp_tax_changes(c.corporation.corporation_id)
            output[c.corporation.corporation_name] = created
        return output


class CorpTaxPayoutTaxConfiguration(models.Model):
    name = models.CharField(max_length=50)

    corporation = models.ForeignKey(
        EveName,
        on_delete=models.CASCADE,
        limit_choices_to={'category': "corporation"},
        blank=True,
        null=True,
        default=None
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
                corp_details = esi.client.Corporation.get_corporations_corporation_id(
                    corporation_id=cid
                ).result()
                current_rate = Decimal(
                    corp_details.get('tax_rate', 0.1)
                )
                rate = CorpTaxHistory.get_tax_rate(
                    cid, w.date, tax_rates=tax_cache[cid], default=current_rate*100)

                trans_ids.add(w.entry_id)
                if cid not in output:
                    output[cid] = {
                        "characters": [],
                        "trans_ids": [],
                        "tax_rates_used": [],
                        "tax_rates": tax_cache[cid],
                        "sum_earn": 0,
                        "pre_tax_total": 0,
                        "tax_to_pay": 0,
                        "cnt": 0,
                        "end": MIN_DATE,
                        "start": MAX_DATE
                    }

                total_value = w.amount/(Decimal(rate/100))

                output[cid]["sum_earn"] += w.amount
                output[cid]["pre_tax_total"] += total_value
                output[cid]["tax_to_pay"] += total_value*(self.tax/100)

                output[cid]["cnt"] += 1

                if full:
                    output[cid]["trans_ids"].append(w.entry_id)

                if rate not in output[cid]["tax_rates_used"]:
                    output[cid]["tax_rates_used"].append(rate)

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


class CorpTaxPerMemberTaxConfiguration(models.Model):
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
    )

    isk_per_main = models.IntegerField(default=20000000)

    def __str__(self):
        return self.state.name

    def get_main_counts(self):
        characters = EveCharacter.objects.filter(
            character_ownership__user__profile__state=self.state,
            character_id=F(
                "character_ownership__user__profile__main_character__character_id")
        ).values(
            "character_ownership__user__profile__main_character__corporation_id"
        ).annotate(
            Count("character_id"),
            corp_name=F(
                "character_ownership__user__profile__main_character__corporation_name")
        )
        return characters

    def get_invoice_data(self):
        corp_list = self.get_main_counts()
        corp_info = {}
        output = {}
        corps = EveCorporationInfo.objects.filter(corporation_id__in=corp_list.values_list(
            "character_ownership__user__profile__main_character__corporation_id"))

        for c in corps:
            corp_info[c.corporation_id] = {
                "ceo": c.ceo_id,
                "members": c.member_count
            }

        for corp in corp_list:
            cid = corp['character_ownership__user__profile__main_character__corporation_id']
            if cid in corp_info:
                output[cid] = {
                    "character_count": corp_info[cid]['members'],
                    "ceo": corp_info[cid]['ceo'],
                    "main_count": corp['character_id__count'],
                    "corp": corp['corp_name'],
                    "tax_to_pay": corp['character_id__count'] * self.isk_per_main
                }
        return output

    def get_invoice_stats(self):
        corp_list = self.get_invoice_data()
        output = {"corps": {}, "total": 0}

        for key, corp in corp_list.items():
            output['corps'][corp['corp']] = corp['main_count']
            output['total'] += corp['tax']

        return output


class CorpTaxPerServiceModuleConfiguration(models.Model):
    isk_per_service = models.IntegerField(default=20000000)

    module_filters = models.TextField()

    region_filter = models.ForeignKey(
        MapRegion, on_delete=models.CASCADE, null=True, blank=True, default=None)

    def get_service_counts(self):  # TODO update
        characters = EveCharacter.objects.filter(
            character_ownership__user__profile__state=self.state,
            character_id=F(
                "character_ownership__user__profile__main_character__character_id")
        ).values(
            "character_ownership__user__profile__main_character__corporation_id"
        ).annotate(
            Count("character_id"),
            corp_name=F(
                "character_ownership__user__profile__main_character__corporation_name")
        )
        return characters

    def get_invoice_data(self):  # TODO update
        corp_list = self.get_main_counts()
        corp_info = {}
        output = {}
        corps = EveCorporationInfo.objects.filter(corporation_id__in=corp_list.values_list(
            "character_ownership__user__profile__main_character__corporation_id"))

        for c in corps:
            corp_info[c.corporation_id] = {
                "ceo": c.ceo_id,
                "members": c.member_count
            }

        for corp in corp_list:
            cid = corp['character_ownership__user__profile__main_character__corporation_id']
            output[cid] = {
                "character_count": corp_info[cid]['members'],
                "ceo": corp_info[cid]['ceo'],
                "main_count": corp['character_id__count'],
                "corp": corp['corp_name'],
                "tax_to_pay": corp['character_id__count'] * self.isk_per_main
            }

        return output

    def get_invoice_stats(self):
        corp_list = self.get_invoice_data()
        output = {"corps": {}, "total": 0}

        for key, corp in corp_list.items():
            output['corps'][corp['corp']] = corp['main_count']
            output['total'] += corp['tax_to_pay']

        return output


class CorpTaxRecord(models.Model):
    Name = models.CharField(max_length=50)
    JsonDump = models.TextField()
    TotalTax = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, default=None)
    TotalCharacterEarnings = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, default=None)
    TotalCorporateEarnings = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, default=None)


class CorpTaxConfiguration(models.Model):
    Name = models.CharField(max_length=50)

    CharacterTaxesIncluded = models.ManyToManyField(
        CharacterPayoutTaxConfiguration, blank=True)
    CorporateTaxesIncluded = models.ManyToManyField(
        CorpTaxPayoutTaxConfiguration, blank=True)
    CorporateMemberTaxIncluded = models.ManyToManyField(
        CorpTaxPerMemberTaxConfiguration, blank=True)
    CorporateStructureTaxIncluded = models.ManyToManyField(
        CorpTaxPerServiceModuleConfiguration, blank=True)

    def calculate_tax(self, start_date=datetime.min, end_date=datetime.max):
        tax_invoices = {}
        output = {
            "char_tax": [],
            "corp_tax": [],
            "corp_member_tax": [],
            "corp_structure_tax": [],
            "total_tax": 0
        }
        for tax in self.CharacterTaxesIncluded.all():
            _taxes = tax.get_character_aggregates_corp_level(
                start_date=start_date, end_date=end_date)
            output["char_tax"].append(_taxes)
            for cid, data in _taxes.items():
                if cid not in tax_invoices:
                    tax_invoices[cid] = {
                        "total_tax": 0,
                        "messages": [],
                    }
                tax_invoices[cid]['total_tax'] += data['tax_to_pay']
                tax_invoices[cid]['messages'].append(
                    f"{tax.name}: {data['tax_to_pay']:,.2f} ({tax.tax:,.1f}% of Total Earnings)")

        for tax in self.CorporateTaxesIncluded.all():
            _taxes = tax.get_aggregates(
                start_date=start_date, end_date=end_date)
            output["corp_tax"].append(_taxes)
            for cid, data in _taxes.items():
                if cid not in tax_invoices:
                    tax_invoices[cid] = {
                        "total_tax": 0,
                        "messages": [],
                    }
                tax_invoices[cid]['total_tax'] += data['tax_to_pay']
                tax_invoices[cid]['messages'].append(
                    f"{tax.name}: {data['tax_to_pay']:,.2f} ({tax.tax:,.1f}% of Total Earnings)")

        for tax in self.CorporateMemberTaxIncluded.all():
            _taxes = tax.get_invoice_data()
            output["corp_member_tax"].append(_taxes)
            for cid, data in _taxes.items():
                if cid not in tax_invoices:
                    tax_invoices[cid] = {
                        "total_tax": 0,
                        "messages": [],
                    }
                tax_invoices[cid]['total_tax'] += data['tax_to_pay']
                tax_invoices[cid]['messages'].append(
                    f"Main Character Tax: {data['main_count']} Mains @ {tax.isk_per_main:,} Per")

        # for tax in self.CorporateStructureTaxIncluded.all():
        #    _taxes = tax.get_invoice_data()
        #    output["corp_structure_tax"].append(_taxes)

        return {"taxes": tax_invoices, "raw": output}

    def send_invoices(self):
        pass
