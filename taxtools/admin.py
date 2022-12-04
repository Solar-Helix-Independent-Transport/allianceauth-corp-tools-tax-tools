from django.contrib import admin

from . import models


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
                         "exempted_corps"]


@admin.register(models.CorpTaxPerServiceModuleConfiguration)
class CorpTaxPerServiceModuleConfigurationAdmin(admin.ModelAdmin):
    filter_horizontal = ["region_filter"]
