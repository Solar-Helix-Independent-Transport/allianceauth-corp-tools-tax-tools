from django.contrib import admin

from . import models


@admin.register(models.CharacterRattingTaxConfiguration)
class CharacterRattingTaxConfigurationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'tax']
    filter_horizontal = ["region_filter"]


@admin.register(models.CharacterPayoutTaxConfiguration)
class CharacterPayoutTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    autocomplete_fields = ['corporation']
    list_display = ['name', 'corporation', 'wallet_transaction_type', 'tax']


@admin.register(models.CorpTaxPayoutTaxConfiguration)
class CorpTaxPayoutTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    autocomplete_fields = ['corporation']
    list_display = ['name', 'corporation', 'wallet_transaction_type', 'tax']


@admin.register(models.CorpTaxPerMemberTaxConfiguration)
class CorpTaxPerMemberTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    list_display = ['state', 'isk_per_main']


@admin.register(models.CorpTaxConfiguration)
class CorpTaxConfigurationAdmin(admin.ModelAdmin):
    filter_horizontal = ["character_taxes_included", "corporate_taxes_included",
                         "corporate_member_tax_included", "corporate_structure_tax_included",
                         "exempted_corps", "character_ratting_included", "included_alliances"]


@admin.register(models.CorpTaxPerServiceModuleConfiguration)
class CorpTaxPerServiceModuleConfigurationAdmin(admin.ModelAdmin):
    filter_horizontal = ["region_filter", "structure_type_filter"]

def generate_formatter(name, str_format):
    def formatter(o): return str_format.format(getattr(o, name) or 0)
    formatter.short_description = name
    formatter.admin_order_field = name
    return formatter


@admin.register(models.CorpTaxRecord)
class CorpTaxRecordAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', "end_date", ('total_tax', "{:,}")]

    # generate a custom formater cause i am lazy...
    def __init__(self, *args, **kwargs):
        all_fields = []
        for f in self.list_display:
            if isinstance(f, str):
                all_fields.append(f)
            else:
                new_field_name = "_" + f[0]
                setattr(self, new_field_name, generate_formatter(f[0], f[1]))
                all_fields.append(new_field_name)
        self.list_display = all_fields

        super().__init__(*args, **kwargs)


@admin.register(models.CorporateTaxCredits)
class CorpTaxCreditAdmin(admin.ModelAdmin):
    autocomplete_fields = ['corp']
    list_display = ['corp', ('credit_balance', "{:,.2f}"), "last_updated"]

    # generate a custom formater cause i am lazy...
    def __init__(self, *args, **kwargs):
        all_fields = []
        for f in self.list_display:
            if isinstance(f, str):
                all_fields.append(f)
            else:
                new_field_name = "_" + f[0]
                setattr(self, new_field_name, generate_formatter(f[0], f[1]))
                all_fields.append(new_field_name)
        self.list_display = all_fields

        super().__init__(*args, **kwargs)
