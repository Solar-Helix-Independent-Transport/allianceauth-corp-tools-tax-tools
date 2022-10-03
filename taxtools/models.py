from datetime import datetime
from email.policy import default

import yaml
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from corptools.models import (CharacterWalletJournalEntry, EveLocation,
                              EveName, Notification)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, Max, Min, Sum
from esi.models import Token


class CorpPayoutTaxConfiguration(models.Model):

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


class CorpPayoutTaxRecord(models.Model):
    entry = models.ForeignKey(
        CharacterWalletJournalEntry, on_delete=models.CASCADE, related_name="taxed")

    processed = models.BooleanField(default=True)


class CorpPayoutTaxHistory(models.Model):
    entry = models.ForeignKey(
        CorpPayoutTaxConfiguration, on_delete=models.CASCADE)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


# CorpTaxChangeMsg
class CorpTaxHistory(models.Model):
    entry = models.ForeignKey(
        EveCorporationInfo, on_delete=models.CASCADE)

    start_date = models.DateTimeField()
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    @classmethod  # TODO make a manager if i want to long term use this.
    def get_corp_tax_list(cls, corp_id):
        taxes = cls.objects.filter(corporation__corporation_id=corp_id).values(
            "start_date", "tax_rate")
        return taxes

    @classmethod
    def find_corp_tax_changes(cls, corp_id):
        notes = Notification.objects.filter(
            character__character__corporation_id=corp_id,
            notification_type="CorpTaxChangeMsg"
            # TODO date limit this depending on the last instance
        ).select_related('notification_text')
        changes = {}
        for n in notes:
            data = yaml.safe_load(n.notification_text.notification_text)
            if data['corpID'] == corp_id:
                t = datetime.timestamp(n.timestamp)
                changes[t] = {"rate": data['newTaxRate'], "date": n.timestamp}
        return changes
