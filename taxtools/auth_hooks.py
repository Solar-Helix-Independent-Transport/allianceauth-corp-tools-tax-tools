from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'taxtools', r'^tax/')


@hooks.register('discord_cogs_hook')
def register_cogs():
    return ["taxtools.tax_cog", ]
