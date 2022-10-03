from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from esi.decorators import token_required

from . import __version__

#from .models import GhostKickToken

"""
@login_required
@permission_required('ghosttools.access_ghost_tools')
def react_bootstrap(request):
    return render(request,
                  'ghosttools/react_base.html',
                  context={"version": __version__,
                           "app_name": "ghosttools",
                           "page_title": "Ghost Tools!"})


@login_required
@permission_required('ghosttools.access_ghost_tools')
@token_required(scopes=['esi-corporations.track_members.v1', 'esi-characters.read_corporation_roles.v1'])
def ghost_corp_add(request, token):
    return redirect('ghosttools:view')


@login_required
@permission_required('ghosttools.access_ghost_tools')
@token_required(['esi-ui.open_window.v1', 'esi-location.read_online.v1'])
def ghost_setkick_character(request, token):
    if token:
        srp_link = False
        try:
            srp_link = GhostKickToken.objects.get(user=request.user)
        except:
            pass
        if srp_link:
            srp_link.token = token
            srp_link.save()
        else:
            GhostKickToken.objects.create(user=request.user, token=token)
        messages.success(request,
                         "Linked Ghost Character: {}".format(token.character_name))

    return redirect("ghosttools:view")
"""
