import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0004_alter_detallemovimiento_options_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="detallemovimiento",
                    name="movimiento",
                    field=models.ForeignKey(
                        db_column="id_movimiento",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detalles",
                        to="inventario.movimientoinventario",
                    ),
                ),
                migrations.AddField(
                    model_name="detallemovimiento",
                    name="producto",
                    field=models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detalles_movimiento",
                        to="inventario.producto",
                    ),
                ),
                migrations.AddField(
                    model_name="movimientoinventario",
                    name="inventario",
                    field=models.ForeignKey(
                        db_column="id_inventario",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos",
                        to="inventario.inventario",
                    ),
                ),
                migrations.AddField(
                    model_name="movimientoinventario",
                    name="tipo_movimiento",
                    field=models.ForeignKey(
                        db_column="id_tipo_movimiento",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos",
                        to="inventario.tipomovimiento",
                    ),
                ),
                migrations.AddField(
                    model_name="movimientoinventario",
                    name="usuario",
                    field=models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos",
                        to="inventario.usuarionegocio",
                    ),
                ),
                migrations.AddField(
                    model_name="usuarionegocio",
                    name="persona",
                    field=models.OneToOneField(
                        db_column="id_persona",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usuario_negocio",
                        to="inventario.persona",
                    ),
                ),
            ],
        ),
    ]
