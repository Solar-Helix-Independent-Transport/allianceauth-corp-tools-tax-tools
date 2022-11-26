# Generated by Django 4.0.8 on 2022-11-26 07:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corptools', '0078_characterwalletjournalentry_corptools_c_date_aebcea_idx_and_more'),
        ('taxtools', '0011_corptaxperservicemoduleconfiguration'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorpTaxConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='CorpTaxRecord',
            fields=[
                ('id', models.AutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.CharField(max_length=50)),
                ('JsonDump', models.TextField()),
                ('TotalTax', models.DecimalField(decimal_places=2,
                 default=None, max_digits=20, null=True)),
                ('TotalCharacterEarnings', models.DecimalField(
                    decimal_places=2, default=None, max_digits=20, null=True)),
                ('TotalCorporateEarnings', models.DecimalField(
                    decimal_places=2, default=None, max_digits=20, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='characterpayouttaxconfiguration',
            name='name',
            field=models.CharField(default='Name', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='corptaxpayouttaxconfiguration',
            name='name',
            field=models.CharField(default='Name', max_length=50),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='characterpayouttaxconfiguration',
            name='corporation',
            field=models.ForeignKey(blank=True, default=None, limit_choices_to={
                                    'category': 'corporation'}, null=True, on_delete=django.db.models.deletion.CASCADE, to='corptools.evename'),
        ),
        migrations.AlterField(
            model_name='corptaxpayouttaxconfiguration',
            name='corporation',
            field=models.ForeignKey(blank=True, default=None, limit_choices_to={
                                    'category': 'corporation'}, null=True, on_delete=django.db.models.deletion.CASCADE, to='corptools.evename'),
        ),
        migrations.DeleteModel(
            name='CharacterPayoutTaxHistory',
        ),
        migrations.AddField(
            model_name='corptaxconfiguration',
            name='CharacterTaxesIncluded',
            field=models.ManyToManyField(
                blank=True, default=None, null=True, to='taxtools.characterpayouttaxconfiguration'),
        ),
        migrations.AddField(
            model_name='corptaxconfiguration',
            name='CorporateMemberTaxIncluded',
            field=models.ManyToManyField(
                blank=True, default=None, null=True, to='taxtools.corptaxpermembertaxconfiguration'),
        ),
        migrations.AddField(
            model_name='corptaxconfiguration',
            name='CorporateStructureTaxIncluded',
            field=models.ManyToManyField(
                blank=True, default=None, null=True, to='taxtools.corptaxperservicemoduleconfiguration'),
        ),
        migrations.AddField(
            model_name='corptaxconfiguration',
            name='CorporateTaxesIncluded',
            field=models.ManyToManyField(
                blank=True, default=None, null=True, to='taxtools.corptaxpayouttaxconfiguration'),
        ),
    ]
