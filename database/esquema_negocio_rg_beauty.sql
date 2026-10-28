CREATE DATABASE IF NOT EXISTS `rg_beauty` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `rg_beauty`;

CREATE TABLE `categoria_producto` (
  `id_categoria_producto` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_categoria_producto`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `categoria_servicio`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categoria_servicio` (
  `id_categoria_servicio` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_categoria_servicio`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cliente`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cliente` (
  `id_cliente` int NOT NULL AUTO_INCREMENT,
  `id_persona` int NOT NULL,
  `fecha_registro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_cliente`),
  UNIQUE KEY `id_persona` (`id_persona`),
  CONSTRAINT `fk_cliente_persona` FOREIGN KEY (`id_persona`) REFERENCES `persona` (`id_persona`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `comuna`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `comuna` (
  `id_comuna` int NOT NULL AUTO_INCREMENT,
  `id_region` int NOT NULL,
  `nombre` varchar(100) NOT NULL,
  PRIMARY KEY (`id_comuna`),
  UNIQUE KEY `id_region` (`id_region`,`nombre`),
  CONSTRAINT `fk_comuna_region` FOREIGN KEY (`id_region`) REFERENCES `region` (`id_region`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `detalle_movimiento`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_movimiento` (
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `detalle_venta`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_venta` (
  `id_detalle_venta` int NOT NULL AUTO_INCREMENT,
  `id_venta` int NOT NULL,
  `id_producto` int NOT NULL,
  `cantidad` int NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL,
  `descuento` decimal(10,2) NOT NULL DEFAULT '0.00',
  `subtotal` decimal(12,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`id_detalle_venta`),
  KEY `fk_detalle_venta_venta` (`id_venta`),
  KEY `fk_detalle_venta_producto` (`id_producto`),
  CONSTRAINT `fk_detalle_venta_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
  CONSTRAINT `fk_detalle_venta_venta` FOREIGN KEY (`id_venta`) REFERENCES `venta` (`id_venta`),
  CONSTRAINT `detalle_venta_chk_1` CHECK ((`cantidad` > 0)),
  CONSTRAINT `detalle_venta_chk_2` CHECK ((`precio_unitario` >= 0)),
  CONSTRAINT `detalle_venta_chk_3` CHECK ((`descuento` >= 0)),
  CONSTRAINT `detalle_venta_chk_4` CHECK ((`subtotal` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `direccion`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `direccion` (
  `id_direccion` int NOT NULL AUTO_INCREMENT,
  `id_persona` int NOT NULL,
  `id_comuna` int NOT NULL,
  `calle` varchar(150) NOT NULL,
  `numero` varchar(20) NOT NULL,
  `departamento` varchar(30) DEFAULT NULL,
  `referencia` varchar(255) DEFAULT NULL,
  `principal` tinyint(1) NOT NULL DEFAULT '0',
  `activa` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_direccion`),
  KEY `fk_direccion_persona` (`id_persona`),
  KEY `fk_direccion_comuna` (`id_comuna`),
  CONSTRAINT `fk_direccion_comuna` FOREIGN KEY (`id_comuna`) REFERENCES `comuna` (`id_comuna`),
  CONSTRAINT `fk_direccion_persona` FOREIGN KEY (`id_persona`) REFERENCES `persona` (`id_persona`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_admin_log`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado_reserva` (
  `id_estado_reserva` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_estado_reserva`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `estado_venta`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado_venta` (
  `id_estado_venta` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_estado_venta`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `favorito`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `favorito` (
  `id_cliente` int NOT NULL,
  `id_producto` int NOT NULL,
  `fecha_agregado` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_cliente`,`id_producto`),
  KEY `fk_favorito_producto` (`id_producto`),
  CONSTRAINT `fk_favorito_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `fk_favorito_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `horario`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `horario` (
  `id_horario` int NOT NULL AUTO_INCREMENT,
  `dia_semana` tinyint NOT NULL,
  `hora_inicio` time NOT NULL,
  `hora_fin` time NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_horario`),
  CONSTRAINT `horario_chk_1` CHECK ((`dia_semana` between 1 and 7)),
  CONSTRAINT `horario_chk_2` CHECK ((`hora_fin` > `hora_inicio`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `horario_usuario`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `horario_usuario` (
  `id_horario` int NOT NULL,
  `id_usuario` int NOT NULL,
  PRIMARY KEY (`id_horario`,`id_usuario`),
  KEY `fk_horario_usuario_usuario` (`id_usuario`),
  CONSTRAINT `fk_horario_usuario_horario` FOREIGN KEY (`id_horario`) REFERENCES `horario` (`id_horario`),
  CONSTRAINT `fk_horario_usuario_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inventario`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventario` (
  `id_inventario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `ubicacion` varchar(150) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_inventario`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `marca`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `marca` (
  `id_marca` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_marca`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `metodo_pago`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `metodo_pago` (
  `id_metodo_pago` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_metodo_pago`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `movimiento_inventario`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `movimiento_inventario` (
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `permiso`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `permiso` (
  `id_permiso` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `modulo` varchar(50) NOT NULL,
  `accion` varchar(50) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_permiso`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `persona`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `persona` (
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `producto`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto` (
  `id_producto` int NOT NULL AUTO_INCREMENT,
  `id_categoria_producto` int NOT NULL,
  `id_marca` int NOT NULL,
  `sku` varchar(50) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `descripcion` text,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `fecha_creacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_producto`),
  UNIQUE KEY `sku` (`sku`),
  KEY `fk_producto_categoria` (`id_categoria_producto`),
  KEY `fk_producto_marca` (`id_marca`),
  CONSTRAINT `fk_producto_categoria` FOREIGN KEY (`id_categoria_producto`) REFERENCES `categoria_producto` (`id_categoria_producto`),
  CONSTRAINT `fk_producto_marca` FOREIGN KEY (`id_marca`) REFERENCES `marca` (`id_marca`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `producto_imagen`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto_imagen` (
  `id_imagen` int NOT NULL AUTO_INCREMENT,
  `id_producto` int NOT NULL,
  `url` varchar(500) NOT NULL,
  `texto_alternativo` varchar(255) DEFAULT NULL,
  `orden` int NOT NULL DEFAULT '1',
  `principal` tinyint(1) NOT NULL DEFAULT '0',
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_imagen`),
  UNIQUE KEY `id_producto` (`id_producto`,`orden`),
  CONSTRAINT `fk_producto_imagen_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
  CONSTRAINT `producto_imagen_chk_1` CHECK ((`orden` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `producto_precio`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto_precio` (
  `id_precio` int NOT NULL AUTO_INCREMENT,
  `id_producto` int NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `fecha_inicio` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_fin` datetime DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_precio`),
  KEY `fk_producto_precio_producto` (`id_producto`),
  CONSTRAINT `fk_producto_precio_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
  CONSTRAINT `producto_precio_chk_1` CHECK ((`precio` >= 0)),
  CONSTRAINT `producto_precio_chk_2` CHECK (((`fecha_fin` is null) or (`fecha_fin` > `fecha_inicio`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `region`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `region` (
  `id_region` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  PRIMARY KEY (`id_region`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reserva`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reserva` (
  `id_reserva` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `id_servicio` int NOT NULL,
  `id_usuario` int NOT NULL,
  `id_estado_reserva` int NOT NULL,
  `fecha` date NOT NULL,
  `hora_inicio` time NOT NULL,
  `hora_fin` time NOT NULL,
  `observacion` text,
  `fecha_creacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_reserva`),
  KEY `fk_reserva_cliente` (`id_cliente`),
  KEY `fk_reserva_servicio` (`id_servicio`),
  KEY `fk_reserva_usuario` (`id_usuario`),
  KEY `fk_reserva_estado` (`id_estado_reserva`),
  CONSTRAINT `fk_reserva_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `fk_reserva_estado` FOREIGN KEY (`id_estado_reserva`) REFERENCES `estado_reserva` (`id_estado_reserva`),
  CONSTRAINT `fk_reserva_servicio` FOREIGN KEY (`id_servicio`) REFERENCES `servicio` (`id_servicio`),
  CONSTRAINT `fk_reserva_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `reserva_chk_1` CHECK ((`hora_fin` > `hora_inicio`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rol`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rol` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_rol`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rol_permiso`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rol_permiso` (
  `id_rol` int NOT NULL,
  `id_permiso` int NOT NULL,
  PRIMARY KEY (`id_rol`,`id_permiso`),
  KEY `fk_rol_permiso_permiso` (`id_permiso`),
  CONSTRAINT `fk_rol_permiso_permiso` FOREIGN KEY (`id_permiso`) REFERENCES `permiso` (`id_permiso`),
  CONSTRAINT `fk_rol_permiso_rol` FOREIGN KEY (`id_rol`) REFERENCES `rol` (`id_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servicio`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicio` (
  `id_servicio` int NOT NULL AUTO_INCREMENT,
  `id_categoria_servicio` int NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `descripcion` text,
  `duracion_minutos` int NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `fecha_creacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_servicio`),
  UNIQUE KEY `nombre` (`nombre`),
  KEY `fk_servicio_categoria` (`id_categoria_servicio`),
  CONSTRAINT `fk_servicio_categoria` FOREIGN KEY (`id_categoria_servicio`) REFERENCES `categoria_servicio` (`id_categoria_servicio`),
  CONSTRAINT `servicio_chk_1` CHECK ((`duracion_minutos` > 0)),
  CONSTRAINT `servicio_chk_2` CHECK ((`precio` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stock`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock` (
  `id_inventario` int NOT NULL,
  `id_producto` int NOT NULL,
  `cantidad_actual` int NOT NULL DEFAULT '0',
  `fecha_actualizacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_inventario`,`id_producto`),
  KEY `fk_stock_producto` (`id_producto`),
  CONSTRAINT `fk_stock_inventario` FOREIGN KEY (`id_inventario`) REFERENCES `inventario` (`id_inventario`),
  CONSTRAINT `fk_stock_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`),
  CONSTRAINT `stock_chk_1` CHECK ((`cantidad_actual` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tipo_movimiento`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tipo_movimiento` (
  `id_tipo_movimiento` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `afecta_stock` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_tipo_movimiento`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuario`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario` (
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuario_rol`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario_rol` (
  `id_usuario` int NOT NULL,
  `id_rol` int NOT NULL,
  `fecha_asignacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_usuario`,`id_rol`),
  KEY `fk_usuario_rol_rol` (`id_rol`),
  CONSTRAINT `fk_usuario_rol_rol` FOREIGN KEY (`id_rol`) REFERENCES `rol` (`id_rol`),
  CONSTRAINT `fk_usuario_rol_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `venta`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `venta` (
  `id_venta` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int DEFAULT NULL,
  `id_usuario` int NOT NULL,
  `id_estado_venta` int NOT NULL,
  `id_metodo_pago` int NOT NULL,
  `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `subtotal` decimal(12,2) NOT NULL DEFAULT '0.00',
  `descuento` decimal(12,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`id_venta`),
  KEY `fk_venta_cliente` (`id_cliente`),
  KEY `fk_venta_usuario` (`id_usuario`),
  KEY `fk_venta_estado` (`id_estado_venta`),
  KEY `fk_venta_metodo_pago` (`id_metodo_pago`),
  CONSTRAINT `fk_venta_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `fk_venta_estado` FOREIGN KEY (`id_estado_venta`) REFERENCES `estado_venta` (`id_estado_venta`),
  CONSTRAINT `fk_venta_metodo_pago` FOREIGN KEY (`id_metodo_pago`) REFERENCES `metodo_pago` (`id_metodo_pago`),
  CONSTRAINT `fk_venta_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `venta_chk_1` CHECK ((`subtotal` >= 0)),
  CONSTRAINT `venta_chk_2` CHECK ((`descuento` >= 0)),
  CONSTRAINT `venta_chk_3` CHECK ((`total` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-23 22:11:01
