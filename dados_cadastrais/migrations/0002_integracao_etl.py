"""Migração proposta SOMENTE para a 0001_initial da branch base dos ZIPs 23/11.

Revisar o histórico do repositório e preservar backup antes de aplicar em banco existente.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dados_cadastrais', '0001_initial')]

    operations = [
        migrations.AlterField(model_name='cliente', name='razao_social',
                              field=models.CharField(max_length=255)),
        migrations.AlterField(model_name='cliente', name='cnpj',
                              field=models.CharField(max_length=18, null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='telefone',
                              field=models.CharField(max_length=20, null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='email',
                              field=models.EmailField(max_length=254, null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='bairro_informado',
                              field=models.CharField(max_length=100, null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='cep',
                              field=models.CharField(max_length=9, null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='data_cadastro',
                              field=models.DateField(null=True, blank=True)),
        migrations.AlterField(model_name='cliente', name='vendedor_id',
                              field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                      related_name='clientes', to='dados_cadastrais.vendedor')),
        migrations.AddField(model_name='cliente', name='id_cliente',
                            field=models.CharField(max_length=24, unique=True, null=True, blank=True)),
        migrations.AddField(model_name='cliente', name='cnpj_original',
                            field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name='cliente', name='telefone_original',
                            field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name='cliente', name='email_original',
                            field=models.CharField(max_length=254, blank=True)),
        migrations.AddField(model_name='cliente', name='bairro_informado_original',
                            field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name='cliente', name='cep_original',
                            field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name='cliente', name='data_cadastro_original',
                            field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name='cliente', name='bairro_via_cep',
                            field=models.CharField(max_length=100, null=True, blank=True)),
        migrations.AddField(model_name='cliente', name='status_cep',
                            field=models.CharField(max_length=32, blank=True)),
        migrations.AddField(model_name='cliente', name='status_consistencia',
                            field=models.CharField(max_length=32, blank=True)),
        migrations.AddField(model_name='cliente', name='cep_confirmado_via_cep',
                            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='cliente', name='necessita_revisao',
                            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='cliente', name='motivos_pendencia',
                            field=models.TextField(blank=True)),
        migrations.CreateModel(
            name='AuditoriaETL',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('execucao_id', models.CharField(max_length=36, db_index=True)),
                ('id_cliente', models.CharField(max_length=24, db_index=True)),
                ('campo', models.CharField(max_length=100)),
                ('valor_original', models.TextField(blank=True)),
                ('valor_tratado', models.TextField(blank=True)),
                ('criterio', models.TextField()),
                ('fonte', models.TextField()),
                ('status', models.CharField(max_length=40)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name_plural': 'Auditorias ETL'},
        ),
    ]
