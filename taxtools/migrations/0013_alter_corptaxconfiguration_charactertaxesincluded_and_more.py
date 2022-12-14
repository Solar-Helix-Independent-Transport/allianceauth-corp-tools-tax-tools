# Generated by Django 4.0.8 on 2022-11-26 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxtools', '0012_corptaxconfiguration_corptaxrecord_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corptaxconfiguration',
            name='CharacterTaxesIncluded',
            field=models.ManyToManyField(
                blank=True, to='taxtools.characterpayouttaxconfiguration'),
        ),
        migrations.AlterField(
            model_name='corptaxconfiguration',
            name='CorporateMemberTaxIncluded',
            field=models.ManyToManyField(
                blank=True, to='taxtools.corptaxpermembertaxconfiguration'),
        ),
        migrations.AlterField(
            model_name='corptaxconfiguration',
            name='CorporateStructureTaxIncluded',
            field=models.ManyToManyField(
                blank=True, to='taxtools.corptaxperservicemoduleconfiguration'),
        ),
        migrations.AlterField(
            model_name='corptaxconfiguration',
            name='CorporateTaxesIncluded',
            field=models.ManyToManyField(
                blank=True, to='taxtools.corptaxpayouttaxconfiguration'),
        ),
    ]
