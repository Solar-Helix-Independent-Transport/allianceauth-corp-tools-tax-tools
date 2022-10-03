from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook
from django.utils.translation import gettext_lazy as _

from . import urls

"""
class TaxDash(MenuItemHook):
    def __init__(self):

        MenuItemHook.__init__(self,
                              "Ghost Tools",
                              'fas fa-ghost fa-fw',
                              'taxtools:view',
                              navactive=['taxtools:'])

    def render(self, request):
        if request.user.has_perm('taxtools.access_tax_tools_ui'):
            return MenuItemHook.render(self, request)
        return ''


@hooks.register('menu_item_hook')
def register_menu():
    return TaxDash()
"""


@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'taxtools', r'^tax/')
