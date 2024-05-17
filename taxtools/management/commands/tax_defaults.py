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
        self.stdout.write("Checking for Defaults!")

        ratting = None
        corp = []
        char = []
        member = None
        structure = None
        concord, _ = EveName.objects.get_or_create_from_esi(1000125)
        conclav, _ = EveName.objects.get_or_create_from_esi(1000298)

        if CharacterRattingTaxConfiguration.objects.all().exists():
            self.stdout.write("Ratting Taxes Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Ratting Tax Config!")
            ratting = CharacterRattingTaxConfiguration.objects.create(
                name="Global Ratting"
            )

        if CharacterPayoutTaxConfiguration.objects.all().exists():
            self.stdout.write("Character Taxes Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Character Taxes Configs!")
            char.append(
                CharacterPayoutTaxConfiguration.objects.create(
                    name="Missions",
                    wallet_transaction_type="agent_mission_reward,agent_mission_time_bonus_reward"
                )
            )
            char.append(
                CharacterPayoutTaxConfiguration.objects.create(
                    name="Incursions",
                    corporation=concord,
                    wallet_transaction_type="corporate_reward_payout"
                )
            )
            char.append(
                CharacterPayoutTaxConfiguration.objects.create(
                    name="Pochven",
                    corporation=conclav,
                    wallet_transaction_type="corporate_reward_payout"
                )
            )

        if CorpTaxPayoutTaxConfiguration.objects.all().exists():
            self.stdout.write("Corp Taxes Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Corp Taxes Configs!")
            corp.append(
                CorpTaxPayoutTaxConfiguration.objects.create(
                    name="Missions",
                    wallet_transaction_type="agent_mission_reward,agent_mission_time_bonus_reward"
                )
            )
            corp.append(
                CorpTaxPayoutTaxConfiguration.objects.create(
                    name="Incursions",
                    corporation=concord,
                    wallet_transaction_type="corporate_reward_payout"
                )
            )
            corp.append(
                CorpTaxPayoutTaxConfiguration.objects.create(
                    name="Pochven",
                    corporation=conclav,
                    wallet_transaction_type="corporate_reward_payout"
                )
            )

        if CorpTaxPerMemberTaxConfiguration.objects.all().exists():
            self.stdout.write("Member Taxes Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Member Tax Config!")
            member = CorpTaxPerMemberTaxConfiguration.objects.create(
                state=State.objects.get(name="Member")
            )

        if CorpTaxPerServiceModuleConfiguration.objects.all().exists():
            self.stdout.write("Service Taxes Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Service Tax Config!")
            structure = CorpTaxPerServiceModuleConfiguration.objects.create(
                module_filters="Composite Reactions,Material Efficiency Research,Blueprint Copying,Invention,Time Efficiency Research,Biochemical Reactions,Hybrid Reactions,Manufacturing (Standard),Manufacturing (Capitals),Manufacturing (Super Capitals)"
            )

        if CorpTaxConfiguration.objects.all().exists():
            self.stdout.write("Global Tax Already Configured Skipping!")
        else:
            self.stdout.write("Creating Default Global Tax Config!")
            tax = CorpTaxConfiguration.objects.create(
                Name="Master Tax",
                pk=1
            )
        self.stdout.write("Creating/Updating Tasks")

        schedule_tax, _ = CrontabSchedule.objects.get_or_create(minute='0',
                                                                hour='1',
                                                                day_of_week='*',
                                                                day_of_month='14,28',
                                                                month_of_year='*',
                                                                timezone='UTC'
                                                                )

        tax_invoice = PeriodicTask.objects.update_or_create(
            task='taxtools.tasks.send_taxes',
            defaults={
                'crontab': schedule_tax,
                'name': 'Send Invoices to all Corps!',
                'enabled': True
            }
        )

        self.stdout.write(
            "Done! Configure your specific requirements in the admin website in auth.")
