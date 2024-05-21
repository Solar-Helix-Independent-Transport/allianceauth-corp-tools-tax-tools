from corptools.models import EveName
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from django.core.management.base import BaseCommand

from allianceauth.authentication.models import State

from taxtools.models import (
    CharacterPayoutTaxConfiguration, CharacterRattingTaxConfiguration,
    CorpTaxConfiguration, CorpTaxPayoutTaxConfiguration,
    CorpTaxPerMemberTaxConfiguration, CorpTaxPerServiceModuleConfiguration,
)
from taxtools.tasks import send_taxes


class Command(BaseCommand):
    help = 'Bootstrap the Tax Module'

    def handle(self, *args, **options):
        self.stdout.write("Checking for Taxes!")

        ct = CorpTaxConfiguration.objects.get(pk=1)
        taxes = {}
        for tax in ct.character_ratting_included.all():
            _type = "Ratting"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_console__())

        for tax in ct.character_taxes_included.all():
            _type = "Character Activity"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_console__())

        for tax in ct.corporate_taxes_included.all():
            _type = "Corporate Activity"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_console__())

        for tax in ct.corporate_member_tax_included.all():
            _type = "Corporate Members"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_console__())

        for tax in ct.corporate_structure_tax_included.all():
            _type = "Structure Services"
            if _type not in taxes:
                taxes[_type] = []
            taxes[_type].append(tax.__str_console__())

        self.stdout.write(
            f"Tax Status! See below configured taxes for \033[36;7m{ct.Name}\033[39;0m")
        for t, d in taxes.items():
            self.stdout.write("")
            self.stdout.write(f"\033[32;7m{t}\033[39;0m")
            for _t in d:
                self.stdout.write(f"  {_t}")

        included_alliances = ", ".join(ct.included_alliances.all().values_list(
            "alliance_name", flat=True))
        if not len(included_alliances):
            included_alliances = "None"

        exempted_corps = ", ".join(ct.exempted_corps.all().values_list(
            "corporation_name", flat=True))
        if not len(exempted_corps):
            exempted_corps = "None"

        self.stdout.write("")
        self.stdout.write(f"Included Alliances: \033[32m{included_alliances}\033[39m")
        self.stdout.write(f"Exempted Corps: \033[32m{exempted_corps}\033[39m")
        self.stdout.write("Done!")
