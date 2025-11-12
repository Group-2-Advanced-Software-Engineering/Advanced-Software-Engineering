import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='KanoodleBoard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('width', models.IntegerField(default=5)),
                ('height', models.IntegerField(default=11)),
            ],
        ),
        migrations.CreateModel(
            name='Piece',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('shapeData', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='partialSolution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state_data', models.JSONField(default=dict)),
                ('board', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kanoodleApp.kanoodleboard')),
            ],
        ),
    ]
