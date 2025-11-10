# Generated manually to fix production database schema mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0002_submissionitem_annotations'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='flagged_for_human',
            field=models.BooleanField(default=False),
        ),
    ]
