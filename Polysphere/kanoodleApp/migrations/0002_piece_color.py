from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanoodleApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='piece',
            name='color',
            field=models.CharField(default='#999999', max_length=7),
        ),
    ]
