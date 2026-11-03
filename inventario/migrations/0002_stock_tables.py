from django.db import migrations


TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS `persona` (
      `id_persona` int NOT NULL AUTO_INCREMENT,
      `rut` varchar(12) NOT NULL,
      `nombre` varchar(100) NOT NULL,
      `apellido_paterno` varchar(100) NOT NULL,
      `apellido_materno` varchar(100) DEFAULT NULL,
      `fecha_nacimiento` date DEFAULT NULL,
      `telefono` varchar(20) DEFAULT NULL,
      `email` varchar(150) NOT NULL,
      `fecha_creacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id_persona`),
      UNIQUE KEY `rut` (`rut`),
      UNIQUE KEY `email` (`email`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `usuario` (
      `id_usuario` int NOT NULL AUTO_INCREMENT,
      `id_persona` int NOT NULL,
      `nombre_usuario` varchar(50) NOT NULL,
      `password_hash` varchar(255) NOT NULL,
      `activo` tinyint(1) NOT NULL DEFAULT '1',
      `fecha_registro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `ultimo_acceso` datetime DEFAULT NULL,
      PRIMARY KEY (`id_usuario`),
      UNIQUE KEY `id_persona` (`id_persona`),
      UNIQUE KEY `nombre_usuario` (`nombre_usuario`),
      CONSTRAINT `fk_usuario_persona` FOREIGN KEY (`id_persona`) REFERENCES `persona` (`id_persona`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `inventario` (
      `id_inventario` int NOT NULL AUTO_INCREMENT,
      `nombre` varchar(100) NOT NULL,
      `descripcion` varchar(255) DEFAULT NULL,
      `ubicacion` varchar(150) DEFAULT NULL,
      `activo` tinyint(1) NOT NULL DEFAULT '1',
      PRIMARY KEY (`id_inventario`),
      UNIQUE KEY `nombre` (`nombre`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `tipo_movimiento` (
      `id_tipo_movimiento` int NOT NULL AUTO_INCREMENT,
      `nombre` varchar(50) NOT NULL,
      `descripcion` varchar(255) DEFAULT NULL,
      `afecta_stock` tinyint(1) NOT NULL DEFAULT '1',
      PRIMARY KEY (`id_tipo_movimiento`),
      UNIQUE KEY `nombre` (`nombre`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `movimiento_inventario` (
      `id_movimiento` int NOT NULL AUTO_INCREMENT,
      `id_inventario` int NOT NULL,
      `id_usuario` int NOT NULL,
      `id_tipo_movimiento` int NOT NULL,
      `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `motivo` varchar(255) NOT NULL,
      `observacion` text,
      PRIMARY KEY (`id_movimiento`),
      KEY `fk_movimiento_inventario` (`id_inventario`),
      KEY `fk_movimiento_usuario` (`id_usuario`),
      KEY `fk_movimiento_tipo` (`id_tipo_movimiento`),
      CONSTRAINT `fk_movimiento_inventario` FOREIGN KEY (`id_inventario`) REFERENCES `inventario` (`id_inventario`),
      CONSTRAINT `fk_movimiento_tipo` FOREIGN KEY (`id_tipo_movimiento`) REFERENCES `tipo_movimiento` (`id_tipo_movimiento`),
      CONSTRAINT `fk_movimiento_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `detalle_movimiento` (
      `id_detalle_movimiento` int NOT NULL AUTO_INCREMENT,
      `id_movimiento` int NOT NULL,
      `id_producto` int NOT NULL,
      `cantidad` int NOT NULL,
      `stock_anterior` int NOT NULL,
      `stock_nuevo` int NOT NULL,
      PRIMARY KEY (`id_detalle_movimiento`),
      KEY `fk_detalle_movimiento_movimiento` (`id_movimiento`),
      KEY `fk_detalle_movimiento_producto` (`id_producto`),
      CONSTRAINT `fk_detalle_movimiento_movimiento` FOREIGN KEY (`id_movimiento`) REFERENCES `movimiento_inventario` (`id_movimiento`),
      CONSTRAINT `fk_detalle_movimiento_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
      CONSTRAINT `detalle_movimiento_chk_1` CHECK ((`cantidad` > 0)),
      CONSTRAINT `detalle_movimiento_chk_2` CHECK ((`stock_anterior` >= 0)),
      CONSTRAINT `detalle_movimiento_chk_3` CHECK ((`stock_nuevo` >= 0))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `stock` (
      `id_inventario` int NOT NULL,
      `id_producto` int NOT NULL,
      `cantidad_actual` int NOT NULL DEFAULT '0',
      `fecha_actualizacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id_inventario`,`id_producto`),
      KEY `fk_stock_producto` (`id_producto`),
      CONSTRAINT `fk_stock_inventario` FOREIGN KEY (`id_inventario`) REFERENCES `inventario` (`id_inventario`),
      CONSTRAINT `fk_stock_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
      CONSTRAINT `stock_chk_1` CHECK ((`cantidad_actual` >= 0))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
]


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=TABLES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
