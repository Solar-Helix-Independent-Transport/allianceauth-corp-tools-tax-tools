# Generated by Django 4.0.7 on 2022-10-03 02:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corptools', '0077_fullyloadedfilter_reversed_logic'),
        ('taxtools', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corppayouttaxconfiguration',
            name='corporation',
            field=models.ForeignKey(limit_choices_to={
                                    'category': 'corporation'}, on_delete=django.db.models.deletion.CASCADE, to='corptools.evename'),
        ),
        migrations.AlterField(
            model_name='corppayouttaxrecord',
            name='entry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='taxed', to='corptools.characterwalletjournalentry'),
        ),
        migrations.CreateModel(
            name='CorpPayoutTaxHistory',
            fields=[
                ('id', models.AutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 to='taxtools.corppayouttaxconfiguration')),
            ],
        ),
    ]
