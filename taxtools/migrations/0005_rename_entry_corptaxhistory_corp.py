# Generated by Django 4.0.7 on 2022-10-04 05:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxtools', '0004_corptaxhistory'),
    ]

    operations = [
        migrations.RenameField(
            model_name='corptaxhistory',
            old_name='entry',
            new_name='corp',
        ),
    ]
