# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-06-19 10:27
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_merge_20180613_1942'),
    ]

    operations = [
        migrations.AddField(
            model_name='check',
            name='escalation_down',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='check',
            name='escalation_interval',
            field=models.DurationField(default=datetime.timedelta(0, 3600)),
        ),
        migrations.AddField(
            model_name='check',
            name='escalation_list',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='check',
            name='escalation_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='check',
            name='escalation_up',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='check',
            name='priority',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='check',
            name='status',
            field=models.CharField(choices=[('up', 'Up'), ('down', 'Down'), ('new', 'New'), ('paused', 'Paused'), ('too often', 'Too Often')], default='new', max_length=9),
        ),
    ]
