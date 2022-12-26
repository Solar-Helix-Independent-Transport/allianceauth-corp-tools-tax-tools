from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from esi.decorators import token_required

from . import __version__

"""
    add views?
"""
