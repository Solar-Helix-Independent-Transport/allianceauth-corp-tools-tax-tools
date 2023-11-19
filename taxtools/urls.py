from django.urls import re_path

from . import views
from .api import api

app_name = 'taxtools'

urlpatterns = [
    # re_path(r'^/', views.react_bootstrap, name='view'),
    # re_path(r'^add_corp_token/$', views.ghost_corp_add, name='add'),
    # re_path(r'^set_ghost_char/$', views.ghost_setkick_character, name='set'),
    re_path(r'^api/', api.urls),
]
