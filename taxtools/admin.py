from django.contrib import admin

from . import models


@admin.register(models.CorpPayoutTaxConfiguration)
class CorpPayoutTaxConfigurationAdmin(admin.ModelAdmin):
    # filter_horizontal = []
    autocomplete_fields = ['corporation']
