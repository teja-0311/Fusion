# Generated migration for adding timestamps and unique constraint to Research models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0006_staff_management_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchgroup',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='researchgroup',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='researcharea',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='researcharea',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='researchgroup',
            name='name',
            field=models.CharField(max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='researcharea',
            name='parent_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='sub_areas', to='research_procedures.researcharea'),
        ),
        migrations.AlterModelOptions(
            name='researchgroup',
            options={'ordering': ['-created_date'], 'verbose_name': 'Research Group', 'verbose_name_plural': 'Research Groups'},
        ),
        migrations.AlterModelOptions(
            name='researcharea',
            options={'ordering': ['-created_date'], 'verbose_name': 'Research Area', 'verbose_name_plural': 'Research Areas'},
        ),
    ]
