# BlueRock Group investments — cPanel deployment

## cPanel Setup Python App
1. In cPanel, create a Python application matching the Python version supported by your Django version.
2. Set **Application root** to the folder containing `manage.py`, `passenger_wsgi.py`, and `alvis/`. For this ZIP, upload the *contents* of `capital_alvis/` into that application root, rather than nesting the whole folder inside the app root.
3. Set **Startup file** to `passenger_wsgi.py` and **Entry point** to `application`.
4. Create/activate the virtual environment cPanel provides, then install dependencies from `requirements.txt`.
5. Configure environment variables in the Python App interface. At minimum set `DJANGO_SECRET_KEY` to a long random secret, `DJANGO_DEBUG=0`, `ALLOWED_HOSTS=bluerockgroupinvestments.com,www.bluerockgroupinvestments.com`, and `CSRF_TRUSTED_ORIGINS=https://bluerockgroupinvestments.com,https://www.bluerockgroupinvestments.com`.
6. Configure a persistent database. Recommended: create a MySQL database and database user in cPanel, grant privileges, install `mysqlclient` in the app virtualenv, and set `DB_ENGINE=django.db.backends.mysql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT=3306`. cPanel often prefixes database/user names with the hosting account name.
7. Run migrations in the app virtualenv from the application root: `python manage.py migrate`. Create an admin user with `python manage.py createsuperuser`.
8. Ensure static files are collected if your hosting setup requires it: `python manage.py collectstatic --noinput`. Configure `STATIC_ROOT` if your cPanel static serving setup requires a dedicated directory.
9. Restart the application from cPanel's **Setup Python App** interface after code or environment changes.

## Important for existing customer logins
Django accounts live in the configured database. Registration, login, and `/admin/` must all point to the same database. If the website was previously using SQLite, switching to MySQL does not copy old users automatically. Migrate the schema and deliberately migrate existing data before switching; do not delete or overwrite the old database.

## Troubleshooting login
- Check the app's cPanel error log after a failed login or registration.
- Verify the user exists in the same database used by the live app.
- If password hashes were not saved correctly in a prior deployment, reset that user's password through Django Admin or `python manage.py changepassword USERNAME`. Never store plaintext passwords.
- Check that `accounts.backends.EmailOrUsernameBackend` remains in `AUTHENTICATION_BACKENDS`.
- Use HTTPS and keep `DJANGO_DEBUG=0` in production.
