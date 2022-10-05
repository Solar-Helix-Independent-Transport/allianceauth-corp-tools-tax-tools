from django.contrib import admin

from . import models


@admin.register(models.CharacterPayoutTaxConfiguration)
class CharacterPayoutTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    autocomplete_fields = ['corporation']


@admin.register(models.CorpTaxPayoutTaxConfiguration)
class CorpTaxPayoutTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    autocomplete_fields = ['corporation']


@admin.register(models.CorpTaxPerMemberTaxConfiguration)
class CorpTaxPerMemberTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    pass
