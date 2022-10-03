from django.apps import AppConfig

from . import __version__


class TaxToolsConfig(AppConfig):
    name = 'taxtools'
    label = 'taxtools'

    verbose_name = f"Tax Tools v{__version__}"
