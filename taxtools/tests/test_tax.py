import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

from corptools.models import (
    CharacterAudit, CorporationAudit, CorporationWalletDivision,
    CorporationWalletJournalEntry, EveName,
)

from django.test import TestCase

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo

from taxtools.models import (
    CharacterPayoutTaxConfiguration, CharacterRattingTaxConfiguration,
    CorpTaxConfiguration, CorpTaxHistory, CorpTaxPayoutTaxConfiguration,
    CorpTaxRecord, MIN_DATE, MAX_DATE,
)


def _dt(year, month, day):
    return datetime(year, month, day, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# CorpTaxHistory.get_tax_rate — pure logic, no DB writes needed
# ---------------------------------------------------------------------------

class TestCorpTaxHistoryGetTaxRate(TestCase):

    def test_returns_default_when_no_history(self):
        rate = CorpTaxHistory.get_tax_rate(1, _dt(2024, 6, 1), tax_rates=[], default=10)
        self.assertEqual(rate, 10)

    def test_returns_default_when_all_changes_in_future(self):
        tax_rates = [{'start_date': _dt(2024, 7, 1), 'tax_rate': 15}]
        rate = CorpTaxHistory.get_tax_rate(1, _dt(2024, 6, 1), tax_rates=tax_rates, default=10)
        self.assertEqual(rate, 10)

    def test_returns_most_recent_rate_before_date(self):
        tax_rates = [
            {'start_date': _dt(2024, 1, 1), 'tax_rate': 5},
            {'start_date': _dt(2024, 3, 1), 'tax_rate': 10},
            {'start_date': _dt(2024, 6, 1), 'tax_rate': 15},
        ]
        rate = CorpTaxHistory.get_tax_rate(1, _dt(2024, 4, 1), tax_rates=tax_rates, default=20)
        self.assertEqual(rate, 10)

    def test_returns_latest_rate_when_date_after_all_changes(self):
        tax_rates = [
            {'start_date': _dt(2024, 1, 1), 'tax_rate': 5},
            {'start_date': _dt(2024, 3, 1), 'tax_rate': 10},
        ]
        rate = CorpTaxHistory.get_tax_rate(1, _dt(2025, 1, 1), tax_rates=tax_rates, default=20)
        self.assertEqual(rate, 10)

    def test_handles_unsorted_input(self):
        tax_rates = [
            {'start_date': _dt(2024, 6, 1), 'tax_rate': 15},
            {'start_date': _dt(2024, 1, 1), 'tax_rate': 5},
            {'start_date': _dt(2024, 3, 1), 'tax_rate': 10},
        ]
        rate = CorpTaxHistory.get_tax_rate(1, _dt(2024, 4, 1), tax_rates=tax_rates, default=20)
        self.assertEqual(rate, 10)


# ---------------------------------------------------------------------------
# process_character_aggregates_corp_level date range (Bug #1 regression)
# ---------------------------------------------------------------------------

class TestCorpLevelAggregationDateRange(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.ratting = CharacterRattingTaxConfiguration.objects.create(
            name="Test Ratting", tax=Decimal("5.00")
        )
        cls.payout = CharacterPayoutTaxConfiguration.objects.create(
            name="Test Payout",
            wallet_transaction_type="bounty_prizes",
            tax=Decimal("5.00"),
        )

    def _char_entry(self, corp_id, start, end, char_id, trans_id):
        return {
            "characters": [f"Char {char_id}"],
            "corp": corp_id,
            "trans_ids": [trans_id],
            "tax_rates_used": [10],
            "sum_earn": Decimal("1000000"),
            "pre_tax_total": Decimal("1000000"),
            "tax_to_pay": Decimal("50000"),
            "cnt": 1,
            "start": start,
            "end": end,
        }

    def test_ratting_corp_end_is_latest_character_end_not_latest_start(self):
        # Two characters in the same corp. The second has a later *start* but
        # the first has a later *end*.  The corp-level end must track the true
        # maximum end, not the start of whichever bucket ran longest.
        data = {
            1: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 31), 1, 1),
            2: self._char_entry(100, _dt(2024, 1, 10), _dt(2024, 1, 15), 2, 2),
        }
        result = self.ratting.process_character_aggregates_corp_level(data)
        self.assertEqual(result[100]["end"], _dt(2024, 1, 31))

    def test_ratting_corp_end_is_max_across_multiple_chars(self):
        data = {
            1: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 10), 1, 1),
            2: self._char_entry(100, _dt(2024, 1, 5), _dt(2024, 1, 20), 2, 2),
            3: self._char_entry(100, _dt(2024, 1, 2), _dt(2024, 1, 31), 3, 3),
        }
        result = self.ratting.process_character_aggregates_corp_level(data)
        self.assertEqual(result[100]["end"], _dt(2024, 1, 31))

    def test_payout_corp_end_is_latest_character_end_not_latest_start(self):
        data = {
            1: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 31), 1, 1),
            2: self._char_entry(100, _dt(2024, 1, 10), _dt(2024, 1, 15), 2, 2),
        }
        result = self.payout.process_character_aggregates_corp_level(data)
        self.assertEqual(result[100]["end"], _dt(2024, 1, 31))

    def test_corp_start_is_earliest_character_start(self):
        data = {
            1: self._char_entry(100, _dt(2024, 1, 10), _dt(2024, 1, 20), 1, 1),
            2: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 15), 2, 2),
        }
        result = self.ratting.process_character_aggregates_corp_level(data)
        self.assertEqual(result[100]["start"], _dt(2024, 1, 1))

    def test_aggregates_totals_across_chars_in_same_corp(self):
        data = {
            1: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 10), 1, 1),
            2: self._char_entry(100, _dt(2024, 1, 5), _dt(2024, 1, 15), 2, 2),
        }
        result = self.ratting.process_character_aggregates_corp_level(data)
        self.assertEqual(result[100]["cnt"], 2)
        self.assertEqual(result[100]["tax_to_pay"], Decimal("100000"))

    def test_separates_different_corps(self):
        data = {
            1: self._char_entry(100, _dt(2024, 1, 1), _dt(2024, 1, 10), 1, 1),
            2: self._char_entry(200, _dt(2024, 1, 1), _dt(2024, 1, 10), 2, 2),
        }
        result = self.ratting.process_character_aggregates_corp_level(data)
        self.assertIn(100, result)
        self.assertIn(200, result)
        self.assertEqual(result[100]["tax_to_pay"], Decimal("50000"))
        self.assertEqual(result[200]["tax_to_pay"], Decimal("50000"))


# ---------------------------------------------------------------------------
# CharacterRattingTaxConfiguration — tax math
# ---------------------------------------------------------------------------

class TestRattingTaxMath(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.config = CharacterRattingTaxConfiguration.objects.create(
            name="Test ESS On", tax=Decimal("5.00"), include_ess_section=True
        )
        cls.config_no_ess = CharacterRattingTaxConfiguration.objects.create(
            name="Test ESS Off", tax=Decimal("5.00"), include_ess_section=False
        )

    def _entry(self, amount, corp_tax, char_id=1, entry_id=1):
        gross = amount + corp_tax
        total_ratted = gross / Decimal("0.6")
        ess_cut = total_ratted * Decimal("0.35")
        return {
            'entry_id': entry_id,
            'amount': amount,
            'tax': corp_tax,
            'tax_receiver_id': 100,
            'date': _dt(2024, 6, 1),
            'char': char_id,
            'corp': 100,
            'char_name': f'Char {char_id}',
            'total_ratted': total_ratted,
            'ess_cut': ess_cut,
            'main': None,
            'main_corp': 100,
        }

    def test_tax_base_includes_ess_reserve_when_flag_on(self):
        # 600 ISK received + 60 ISK corp tax at 10% → total_ratted = 1100
        # base = 1100 × 0.95 = 1045;  tax = 1045 × 0.05 = 52.25
        data = [self._entry(Decimal("600"), Decimal("60"))]
        result = self.config.process_character_aggregates(data)
        self.assertAlmostEqual(float(result[1]["tax_to_pay"]), 52.25, places=2)

    def test_tax_base_excludes_ess_reserve_when_flag_off(self):
        # base = 1100 × 0.95 − 1100 × 0.35 = 660;  tax = 660 × 0.05 = 33.0
        data = [self._entry(Decimal("600"), Decimal("60"))]
        result = self.config_no_ess.process_character_aggregates(data)
        self.assertAlmostEqual(float(result[1]["tax_to_pay"]), 33.0, places=2)

    def test_groups_by_main_character_when_present(self):
        entry = self._entry(Decimal("600"), Decimal("60"))
        entry['main'] = 99
        result = self.config.process_character_aggregates([entry])
        self.assertIn(99, result)
        self.assertNotIn(1, result)

    def test_deduplicates_same_entry_id(self):
        entry = self._entry(Decimal("600"), Decimal("60"))
        result = self.config.process_character_aggregates([entry, entry])
        self.assertEqual(result[1]["cnt"], 1)

    def test_accumulates_multiple_entries_for_same_character(self):
        entries = [
            self._entry(Decimal("600"), Decimal("60"), entry_id=1),
            self._entry(Decimal("600"), Decimal("60"), entry_id=2),
        ]
        result = self.config.process_character_aggregates(entries)
        self.assertEqual(result[1]["cnt"], 2)
        self.assertAlmostEqual(float(result[1]["tax_to_pay"]), 52.25 * 2, places=2)


# ---------------------------------------------------------------------------
# CharacterPayoutTaxConfiguration — tax math with ESI mock
# ---------------------------------------------------------------------------

class TestCharacterPayoutTaxMath(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.config = CharacterPayoutTaxConfiguration.objects.create(
            name="Missions",
            wallet_transaction_type="agent_mission_reward",
            tax=Decimal("10.00"),
        )

    def _entry(self, char_id, corp_id, amount, entry_id=1):
        return {
            'entry_id': entry_id,
            'amount': amount,
            'tax': None,
            'date': _dt(2024, 6, 1),
            'char': char_id,
            'corp': corp_id,
            'char_name': f'Char {char_id}',
            'main': None,
            'main_corp': corp_id,
        }

    @mock.patch('taxtools.models.esi_openapi')
    def test_backs_out_corp_tax_to_find_gross(self, mock_esi):
        # 900 ISK received after 10% corp tax → gross = 1000
        # alliance tax = 10% of 1000 = 100
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = Decimal('0.10')

        data = [self._entry(1, 100, Decimal("900"))]
        result = self.config.process_character_aggregates(data)

        self.assertAlmostEqual(float(result[1]["pre_tax_total"]), 1000.0, delta=1)
        self.assertAlmostEqual(float(result[1]["tax_to_pay"]), 100.0, delta=1)

    @mock.patch('taxtools.models.esi_openapi')
    def test_uses_historical_corp_tax_rate_not_current(self, mock_esi):
        # Current ESI rate is 5%, but a historical 20% rate was set before the entry
        # 800 ISK received after 20% corp tax → gross = 1000
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = Decimal('0.05')

        corp = EveCorporationInfo.objects.create(
            corporation_id=55001, corporation_name="Historic Corp",
            corporation_ticker="HIS", member_count=1
        )
        CorpTaxHistory.objects.create(
            corp=corp, start_date=_dt(2024, 1, 1), tax_rate=Decimal("20.00")
        )

        data = [self._entry(1, 55001, Decimal("800"))]
        result = self.config.process_character_aggregates(data)

        self.assertAlmostEqual(float(result[1]["pre_tax_total"]), 1000.0, delta=1)
        self.assertAlmostEqual(float(result[1]["tax_to_pay"]), 100.0, delta=1)

    @mock.patch('taxtools.models.esi_openapi')
    def test_groups_by_main_when_present(self, mock_esi):
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = Decimal('0.10')

        entry = self._entry(1, 100, Decimal("900"))
        entry['main'] = 99
        result = self.config.process_character_aggregates([entry])

        self.assertIn(99, result)
        self.assertNotIn(1, result)

    @mock.patch('taxtools.models.esi_openapi')
    def test_deduplicates_same_entry_id(self, mock_esi):
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = Decimal('0.10')

        entry = self._entry(1, 100, Decimal("900"))
        result = self.config.process_character_aggregates([entry, entry])
        self.assertEqual(result[1]["cnt"], 1)


# ---------------------------------------------------------------------------
# CorpTaxPayoutTaxConfiguration.get_aggregates_ids (new method)
# ---------------------------------------------------------------------------

class TestCorpTaxPayoutAggregateIds(TestCase):

    @classmethod
    def setUpTestData(cls):
        corp = EveCorporationInfo.objects.create(
            corporation_id=98000001, corporation_name="AggTest Corp",
            corporation_ticker="AGG", member_count=10
        )
        audit = CorporationAudit.objects.create(corporation=corp)
        division = CorporationWalletDivision.objects.create(
            corporation=audit, name="Main", balance=Decimal("0"), division=1
        )
        cls.npc_corp = EveName.objects.create(
            eve_id=1000001, name="NPC Corp", category="corporation"
        )
        second = EveName.objects.create(
            eve_id=98000001, name="AggTest Corp", category="corporation"
        )
        cls.entry = CorporationWalletJournalEntry.objects.create(
            division=division,
            entry_id=100001,
            date=_dt(2024, 6, 1),
            amount=Decimal("1000000"),
            description="",
            ref_type="bounty_prizes",
            first_party_id=1000001,
            first_party_name=cls.npc_corp,
            second_party_id=98000001,
            second_party_name=second,
        )
        cls.config = CorpTaxPayoutTaxConfiguration.objects.create(
            name="Test Corp Tax",
            corporation=cls.npc_corp,
            wallet_transaction_type="bounty_prizes",
            tax=Decimal("10.00"),
        )

    def _mock_esi(self, mock_esi, tax_rate=Decimal('0.10')):
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = tax_rate

    @mock.patch('taxtools.models.esi_openapi')
    def test_returns_result_for_matching_entry_id(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.config.get_aggregates_ids([self.entry.entry_id])
        self.assertIn(98000001, result)

    @mock.patch('taxtools.models.esi_openapi')
    def test_returns_empty_for_unknown_entry_ids(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.config.get_aggregates_ids([999999])
        self.assertEqual(result, {})

    @mock.patch('taxtools.models.esi_openapi')
    def test_calculates_gross_by_backing_out_corp_tax(self, mock_esi):
        # 1M in corp wallet at 10% corp tax → 10M gross → 10% alliance = 1M
        self._mock_esi(mock_esi, tax_rate=Decimal('0.10'))
        result = self.config.get_aggregates_ids([self.entry.entry_id])
        self.assertAlmostEqual(float(result[98000001]["pre_tax_total"]), 10_000_000, delta=1)
        self.assertAlmostEqual(float(result[98000001]["tax_to_pay"]), 1_000_000, delta=1)

    @mock.patch('taxtools.models.esi_openapi')
    def test_includes_entry_id_in_trans_ids_when_full_true(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.config.get_aggregates_ids([self.entry.entry_id], full=True)
        self.assertIn(self.entry.entry_id, result[98000001]["trans_ids"])

    @mock.patch('taxtools.models.esi_openapi')
    def test_trans_ids_empty_when_full_false(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.config.get_aggregates_ids([self.entry.entry_id], full=False)
        self.assertEqual(result[98000001]["trans_ids"], [])

    @mock.patch('taxtools.models.esi_openapi')
    def test_deduplicates_entries(self, mock_esi):
        self._mock_esi(mock_esi)
        # Passing the same ID twice should count once
        result = self.config.get_aggregates_ids(
            [self.entry.entry_id, self.entry.entry_id]
        )
        self.assertEqual(result[98000001]["cnt"], 1)


# ---------------------------------------------------------------------------
# CorpTaxConfiguration.rerun_taxes includes corporate wallet taxes (Bug #2 regression)
# ---------------------------------------------------------------------------

class TestRerunTaxesIncludesCorporateTaxes(TestCase):

    @classmethod
    def setUpTestData(cls):
        corp = EveCorporationInfo.objects.create(
            corporation_id=98000002, corporation_name="Rerun Corp",
            corporation_ticker="RRN", member_count=5
        )
        audit = CorporationAudit.objects.create(corporation=corp)
        division = CorporationWalletDivision.objects.create(
            corporation=audit, name="Main", balance=Decimal("0"), division=1
        )
        npc = EveName.objects.create(
            eve_id=1000002, name="NPC Rerun", category="corporation"
        )
        second = EveName.objects.create(
            eve_id=98000002, name="Rerun Corp", category="corporation"
        )
        # Amount large enough that rounded tax exceeds the 1M threshold
        cls.entry = CorporationWalletJournalEntry.objects.create(
            division=division,
            entry_id=200001,
            date=_dt(2024, 6, 1),
            amount=Decimal("3000000"),  # at 10%/10% → tax_to_pay=3M
            description="",
            ref_type="corporate_reward_payout",
            first_party_id=1000002,
            first_party_name=npc,
            second_party_id=98000002,
            second_party_name=second,
        )
        corp_tax = CorpTaxPayoutTaxConfiguration.objects.create(
            name="Rerun Corp Tax",
            corporation=npc,
            wallet_transaction_type="corporate_reward_payout",
            tax=Decimal("10.00"),
        )
        cls.tax_config = CorpTaxConfiguration.objects.create(Name="Rerun Config")
        cls.tax_config.corporate_taxes_included.add(corp_tax)

        cls.record = CorpTaxRecord.objects.create(
            name="Old Record",
            start_date=_dt(2024, 5, 1),
            end_date=_dt(2024, 6, 1),
            total_tax=Decimal("0"),
            json_dump=json.dumps({
                "char_trans_ids": [],
                "corp_trans_ids": [cls.entry.entry_id],
            }),
        )

    def _mock_esi(self, mock_esi):
        mock_esi.client.Corporation.GetCorporationsCorporationId.return_value \
            .result.return_value.tax_rate = Decimal('0.10')

    @mock.patch('taxtools.models.esi_openapi')
    def test_rerun_includes_corp_in_invoices(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.tax_config.rerun_taxes(self.record.id)
        self.assertIn(98000002, result["taxes"])

    @mock.patch('taxtools.models.esi_openapi')
    def test_rerun_corp_tax_amount_is_non_zero(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.tax_config.rerun_taxes(self.record.id)
        self.assertGreater(result["taxes"][98000002]["total_tax"], 0)

    @mock.patch('taxtools.models.esi_openapi')
    def test_rerun_populates_corp_output_totals(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.tax_config.rerun_taxes(self.record.id)
        self.assertGreater(result["raw"]["corp"], 0)

    @mock.patch('taxtools.models.esi_openapi')
    def test_rerun_corp_trans_ids_in_output(self, mock_esi):
        self._mock_esi(mock_esi)
        result = self.tax_config.rerun_taxes(self.record.id)
        self.assertIn(self.entry.entry_id, result["corp_trans_ids"])
