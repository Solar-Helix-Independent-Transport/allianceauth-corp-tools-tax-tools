
# Corp Tools - Tax Tools

## Installation

Requires AllianceAuth - CorpTools and AllianceAuth - Invoice Manager

1. Install from pip `pip install allianceauth-corptools-tax-tools`
2. Add `'taxtools'` to INSTALLED_APPS in local.py
3. Run Migrations, collectstatic
4. `python manage.py tax_defaults`
5. Configure taxes as wanted
    Add Alliances and Taxes to `admin/taxtools/corptaxconfiguration/`
6. `python manage.py tax_explain`. Read it to see if you are happy.
7. Run `Send Invoices to all Corps!` on `admin/django_celery_beat/periodictask/` to generate a base level tax. If you dont want to back-charge people you can delete them.

## Features

## Permissions

Category | Perm | Admin Site | Auth Site
--- | --- | --- | ---

## Contributing

Make sure you have signed the [License Agreement](https://developers.eveonline.com/resource/license-agreement) by logging in at <https://developers.eveonline.com> before submitting any pull requests. All bug fixes or features must not include extra superfluous formatting changes.
