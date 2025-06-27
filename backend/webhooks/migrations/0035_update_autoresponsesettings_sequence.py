from django.db import migrations

SQL = """
SELECT setval(
    pg_get_serial_sequence('webhooks_autoresponsesettings','id'),
    (SELECT MAX(id) FROM webhooks_autoresponsesettings)
);
"""

def update_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL)

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0034_celerytasklog_traceback'),
    ]

    operations = [
        migrations.RunPython(update_sequence, migrations.RunPython.noop),
    ]
