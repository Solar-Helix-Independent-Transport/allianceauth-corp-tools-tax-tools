from django.shortcuts import render

from . import __version__
from .models import CorpTaxConfiguration

"""
    add views?
"""


def react_bootstrap(request):
    data = []
    ct = CorpTaxConfiguration.objects.get(pk=1)
    ct.send_invoices()
    return render(request, 'taxtools/react_base.html', context={"data": "\n".join(data)})
