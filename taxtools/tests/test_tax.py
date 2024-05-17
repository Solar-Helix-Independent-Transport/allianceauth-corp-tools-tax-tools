from datetime import timedelta
from unittest import mock

from corptools import models as ct_models

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import (
    EveAllianceInfo, EveCharacter, EveCorporationInfo,
)
from allianceauth.tests.auth_utils import AuthUtils


class TestSecGroupBotFilters(TestCase):
    @classmethod
    def setUpTestData(cls):
        # make some users and make an audit log
        ct_models.CharacterAudit.objects.all().delete()
        EveCharacter.objects.all().delete()
        User.objects.all().delete()
        CharacterOwnership.objects.all().delete()

        # make some data thats clean
        ct_models.EveLocation.objects.all().delete()

        userids = range(1, 11)

        users = []
        characters = []
        for uid in userids:
            user = AuthUtils.create_user(f"User_{uid}")
            main_char = AuthUtils.add_main_character_2(user,
                                                       f"Main {uid}",
                                                       uid,
                                                       corp_id=1,
                                                       corp_name='Test Corp 1',
                                                       corp_ticker='TST1')
            CharacterOwnership.objects.create(
                user=user, character=main_char, owner_hash=f"main{uid}")

            characters.append(main_char)
            users.append(user)
        # add some extra characters to users in 2 corps/alliance
        for uid in range(0, 5):  # test corp 2
            character = EveCharacter.objects.create(character_name=f'Alt {uid}',
                                                    character_id=11+uid,
                                                    corporation_name='Test Corp 2',
                                                    corporation_id=2,
                                                    corporation_ticker='TST2')
            CharacterOwnership.objects.create(character=character,
                                              user=users[uid],
                                              owner_hash=f'ownalt{11+uid}')
            characters.append(character)
