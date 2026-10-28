# RG Beauty — Sistema de gestión de inventario

## 1. Descripción del proyecto

RG Beauty es un sistema web desarrollado con Django y MySQL para apoyar la gestión de productos, existencias y movimientos de inventario de una microempresa dedicada a la comercialización de productos y a la prestación de servicios de belleza.

El proyecto forma parte de una solución de gestión más amplia, cuyo propósito es digitalizar y centralizar procesos que actualmente requieren administrar información de manera coordinada entre distintas áreas del negocio.

El repositorio contiene la base del sistema web y el trabajo correspondiente al módulo de inventario. La solución contempla su futura integración con otros módulos, como ventas, reservas, administración de usuarios y gestión de productos y servicios.

Este repositorio está destinado al desarrollo colaborativo. Cada integrante debe poder obtener el código, configurar su propio entorno local, conectarse a una base de datos MySQL y desarrollar su parte sin depender de las credenciales o los archivos locales de otro integrante.

### 1.1. Objetivo general

Desarrollar una aplicación web que permita centralizar y mejorar la administración de productos, existencias y movimientos de inventario de RG Beauty, manteniendo una estructura preparada para su integración con los demás componentes del sistema.

### 1.2. Objetivos específicos

- Organizar la información de los productos y sus categorías.
- Disponer de una estructura de datos para registrar y consultar existencias.
- Representar las entradas, salidas y ajustes mediante movimientos de inventario.
- Mantener un modelo de datos compartido para facilitar la integración entre los integrantes.
- Establecer una base técnica para incorporar validaciones, control de acceso y reglas de negocio.
- Facilitar la colaboración mediante Git y GitHub.

### 1.3. Alcance

El alcance principal de este repositorio corresponde al sistema web y a la estructura del módulo de inventario. El modelo de datos también contempla entidades relacionadas con ventas, reservas, usuarios, clientes, productos y servicios.

La existencia de una tabla, una ruta o una pantalla no implica necesariamente que toda la funcionalidad asociada esté implementada. Las operaciones de negocio, las validaciones y las integraciones deben evaluarse según su estado real de desarrollo.

---

## 2. Tecnologías utilizadas

| Tecnología | Propósito |
|---|---|
| Python 3.14 | Lenguaje de programación utilizado en el entorno de desarrollo actual. |
| Django 5.2 | Framework web para la estructura y lógica de la aplicación. |
| MySQL | Sistema gestor de bases de datos relacional. |
| HTML | Estructura de las páginas web. |
| CSS | Presentación y estilos de la interfaz. |
| python-dotenv | Lectura de variables de configuración desde el archivo `.env`. |
| Git | Control de versiones del código fuente. |
| GitHub | Alojamiento del repositorio y colaboración entre integrantes. |
| MySQL Workbench | Herramienta gráfica para administrar la base de datos y ejecutar scripts SQL. |

Las versiones instaladas en el entorno local deben contrastarse con `requirements.txt`, que contiene las dependencias Python del proyecto.

---

## 3. Requisitos previos

Antes de instalar el proyecto, cada integrante debe disponer de:

- Python instalado y accesible desde la terminal.
- Git instalado.
- MySQL Server en ejecución.
- MySQL Workbench u otro cliente compatible para administrar e importar el esquema.
- Visual Studio Code u otro editor de código.
- Acceso al repositorio de GitHub.

Se recomienda utilizar Windows PowerShell para seguir los comandos de esta documentación. Los comandos de activación del entorno virtual pueden variar en otros sistemas operativos.

### 3.1. Información importante

Cada integrante debe configurar sus propias credenciales locales de MySQL. No se deben compartir contraseñas mediante el repositorio ni copiar el archivo `.env` de otro integrante.

Para trabajar en paralelo, cada integrante puede utilizar una base de datos local independiente con la misma estructura. Si el equipo necesita compartir una única base de datos, debe coordinar el acceso, los permisos y la gestión de cambios antes de conectarse a ella.

---

## 4. Obtener el proyecto

### 4.1. Clonar el repositorio

Desde PowerShell, ejecutar:

```powershell
git clone https://github.com/skyiwii/Sistema-RG-Beauty.git
cd Sistema-RG-Beauty
```

El repositorio remoto es:

https://github.com/skyiwii/Sistema-RG-Beauty

### 4.2. Crear el entorno virtual

Dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
```

El entorno virtual permite instalar las dependencias del proyecto de manera aislada de las demás instalaciones de Python del equipo.

### 4.3. Activar el entorno virtual

En Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell impide la ejecución del script de activación por la política de ejecución, se debe revisar la configuración local de PowerShell o utilizar otra terminal compatible. No es necesario modificar la política global del equipo para trabajar con el proyecto.

Una vez activado, la terminal normalmente mostrará `(.venv)` al comienzo de la línea.

### 4.4. Instalar las dependencias

Actualizar pip e instalar las dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si la instalación falla, se debe revisar el mensaje de error, la versión de Python y las dependencias especificadas en `requirements.txt`.

---

## 5. Configurar las variables de entorno

### 5.1. Crear el archivo `.env`

El repositorio incluye `.env.example` como plantilla de configuración.

Crear el archivo local ejecutando:

```powershell
Copy-Item .env.example .env
```

Si ya existe un `.env`, no es necesario sobrescribirlo. Se deben conservar las credenciales locales existentes y comprobar que sus variables estén correctamente configuradas.

### 5.2. Configurar la conexión a MySQL

Abrir `.env` y adaptar los valores al servidor MySQL local:

```dotenv
DB_NAME=rg_beauty
DB_USER=tu_usuario_mysql
DB_PASSWORD=tu_contrasena_mysql
DB_HOST=127.0.0.1
DB_PORT=3306
```

Significado de las variables:

| Variable | Descripción |
|---|---|
| `DB_NAME` | Nombre de la base de datos utilizada por Django. |
| `DB_USER` | Usuario de MySQL con permisos sobre la base de datos. |
| `DB_PASSWORD` | Contraseña de ese usuario. |
| `DB_HOST` | Dirección del servidor MySQL. |
| `DB_PORT` | Puerto de conexión de MySQL; habitualmente es `3306`. |

Los valores del ejemplo son orientativos. Cada integrante debe reemplazarlos por sus credenciales reales.

**Seguridad:** `.env` contiene información local y sensible. No debe subirse a GitHub. El archivo `.gitignore` debe continuar excluyéndolo, junto con `.venv/`.

Si se modifican las variables de entorno mientras el servidor está en ejecución, se recomienda reiniciar el proceso para que la aplicación vuelva a cargar la configuración.

---

## 6. Base de datos y modelo de datos

### 6.1. Archivos SQL disponibles

El directorio `database/` contiene archivos relacionados con la estructura de la base de datos.

| Archivo | Propósito | Uso recomendado |
|---|---|---|
| `database/esquema_negocio_rg_beauty.sql` | Esquema de las tablas de negocio de RG Beauty. | Archivo principal para instalar la estructura de negocio en una base nueva o de prueba. |
| `database/Base_De_Datos_RG_Beauty.sql` | Volcado SQL original de la base de datos. | Archivo de referencia; no utilizar como instalación rutinaria sin revisar sus instrucciones. |

El archivo `esquema_negocio_rg_beauty.sql` está destinado a crear las tablas de negocio y sus relaciones, sin incluir las tablas internas de Django que administra el sistema de migraciones del framework.

El volcado original puede contener instrucciones `DROP TABLE IF EXISTS` y definiciones de tablas internas. Por ello, **no debe ejecutarse sobre una base que contenga información que se quiera conservar**.

### 6.2. Entidades del modelo de negocio

El esquema de negocio contiene 31 tablas y contempla las siguientes áreas:

**Productos y catálogo**
- `producto`
- `categoria_producto`
- `marca`
- `producto_imagen`
- `producto_precio`
- `favorito`

**Inventario y movimientos**
- `inventario`
- `stock`
- `movimiento_inventario`
- `detalle_movimiento`
- `tipo_movimiento`

**Ventas y pagos**
- `venta`
- `detalle_venta`
- `estado_venta`
- `metodo_pago`

**Clientes y datos personales**
- `cliente`
- `persona`
- `direccion`
- `comuna`
- `region`

**Servicios y reservas**
- `servicio`
- `categoria_servicio`
- `reserva`
- `estado_reserva`
- `horario`
- `horario_usuario`

**Usuarios, roles y permisos del negocio**
- `usuario`
- `usuario_rol`
- `rol`
- `rol_permiso`
- `permiso`

Las tablas se relacionan mediante claves foráneas para representar dependencias entre entidades. La estructura validada del esquema de prueba contiene 35 claves foráneas.

Los nombres anteriores describen las entidades del modelo SQL. No implican que todos los formularios, operaciones CRUD, servicios o procesos asociados estén terminados en Django.

### 6.3. Crear e importar la base de datos

Para preparar una instalación nueva:

1. Comprobar que MySQL Server esté iniciado.
2. Abrir MySQL Workbench y conectarse al servidor local.
3. Abrir el archivo `database/esquema_negocio_rg_beauty.sql`.
4. Revisar que el encabezado utilice la base `rg_beauty`.
5. Ejecutar el script completo sobre una base nueva o destinada a pruebas.
6. Actualizar la lista de esquemas y comprobar que aparecen las tablas de negocio.

El script de instalación contiene instrucciones para seleccionar el esquema `rg_beauty`. Si se necesita utilizar otro nombre de base de datos, se debe modificar de forma coherente el nombre del esquema en el script y en el archivo `.env` antes de ejecutarlo.

No se deben importar ambos archivos SQL uno después del otro. El archivo de esquema de negocio es el procedimiento recomendado para preparar la estructura de las tablas de RG Beauty.

**Precaución:** no ejecutar scripts de instalación repetidamente sobre una base con información existente. Antes de importar un esquema, comprobar el destino seleccionado en MySQL Workbench.

### 6.4. Tablas internas de Django

Django utiliza sus propias tablas para funciones del framework, como usuarios de autenticación, permisos, sesiones y administración.

Estas tablas son diferentes de las entidades de negocio del sistema, aunque ambas se encuentren en la misma base de datos.

En una instalación nueva, las tablas internas de Django se crean mediante el sistema de migraciones del framework. Por ese motivo, el esquema de negocio no debe sustituirse por un volcado que intente recrear todas las tablas internas.

### 6.5. Migraciones y cambios en el modelo

Antes de ejecutar migraciones, el equipo debe identificar qué tablas administra Django y cuáles forman parte del esquema SQL compartido.

En el estado actual del proyecto, el módulo `inventario` no tiene migraciones de modelos de negocio. Las tablas del esquema compartido no deben recrearse automáticamente como si fueran tablas nuevas de Django sin revisar antes su correspondencia con los modelos y las migraciones.

Para una instalación local nueva, una vez importado el esquema de negocio y configurada la conexión, se pueden ejecutar las migraciones de Django para crear las tablas internas del framework:

```powershell
python manage.py migrate
```

Este procedimiento corresponde a una base de datos nueva y preparada para el proyecto. No se debe asumir que ejecutar migraciones sobre una base existente resolverá automáticamente las diferencias entre el SQL y los modelos.

Cuando se incorporen modelos Django que representen tablas de negocio existentes, será necesario coordinar sus definiciones, las migraciones y el esquema compartido para evitar duplicaciones o alteraciones involuntarias.

---

## 7. Verificar la instalación y ejecutar el sistema

Después de configurar `.env`, instalar las dependencias y preparar la base de datos, ejecutar las siguientes comprobaciones desde la carpeta que contiene `manage.py`.

### 7.1. Comprobar la configuración de Django

```powershell
python manage.py check
```

Este comando revisa aspectos de la configuración de Django. Un resultado satisfactorio no garantiza por sí solo que todas las funciones de negocio estén implementadas.

### 7.2. Comprobar la conexión a MySQL

```powershell
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Conexión a MySQL correcta')"
```

Si aparece un error, revisar:

- Que MySQL Server esté iniciado.
- Que el nombre de la base de datos exista.
- Que las credenciales de `.env` sean correctas.
- Que el usuario tenga permisos suficientes.
- Que el host y el puerto coincidan con la configuración local.

### 7.3. Ejecutar el servidor de desarrollo

```powershell
python manage.py runserver
```

Si el servidor inicia correctamente, abrir en el navegador:

- Aplicación: http://127.0.0.1:8000/
- Administración de Django: http://127.0.0.1:8000/admin/

La disponibilidad de una ruta depende de las URL y vistas implementadas en la versión actual del proyecto.

Para detener el servidor, presionar `Ctrl + C` en la terminal.

### 7.4. Crear un administrador de Django

En una instalación nueva, después de aplicar las migraciones:

```powershell
python manage.py createsuperuser
```

Seguir las instrucciones de la terminal para crear la cuenta administrativa local.

La cuenta creada por este comando corresponde al sistema de autenticación de Django. No debe confundirse automáticamente con los registros de las tablas de negocio `usuario`, `rol` y `usuario_rol`, cuya integración debe implementarse y verificarse según los requisitos del proyecto.

---

## 8. Estructura del repositorio

La estructura principal del proyecto se organiza de la siguiente manera:

```text
Sistema-RG-Beauty/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── inventario/
│   ├── models.py
│   ├── views.py
│   ├── ...
├── templates/
│   ├── components/
│   ├── registration/
│   ├── dashboard/
│   └── inventario/
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── database/
│   ├── Base_De_Datos_RG_Beauty.sql
│   └── esquema_negocio_rg_beauty.sql
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

Esta representación muestra la organización principal; pueden existir archivos adicionales en las carpetas.

### 8.1. Responsabilidad de las carpetas

| Ruta | Responsabilidad |
|---|---|
| `config/` | Configuración general del proyecto Django, URL principales y otros componentes de configuración. |
| `inventario/` | Aplicación Django correspondiente al módulo de inventario. |
| `templates/` | Plantillas HTML utilizadas para presentar las páginas y componentes de la interfaz. |
| `templates/components/` | Componentes de interfaz reutilizables. |
| `templates/registration/` | Plantillas relacionadas con las vistas de autenticación, según las URL y vistas configuradas. |
| `templates/dashboard/` | Plantillas de la sección principal o panel de la aplicación. |
| `templates/inventario/` | Plantillas correspondientes a las páginas del módulo de inventario. |
| `static/css/` | Hojas de estilo. |
| `static/js/` | Archivos JavaScript estáticos. |
| `static/img/` | Imágenes utilizadas por la interfaz. |
| `database/` | Scripts SQL y documentación relacionada con el modelo de datos. |
| `.env.example` | Plantilla de variables de entorno sin credenciales personales. |
| `requirements.txt` | Dependencias Python necesarias para instalar el proyecto. |
| `manage.py` | Punto de entrada para ejecutar comandos administrativos de Django. |

---

## 9. Funcionalidades y estado del desarrollo

El proyecto está orientado al desarrollo de un sistema de inventario integrado con otras áreas de RG Beauty.

Las funcionalidades contempladas incluyen:

- Gestión y consulta de productos.
- Consulta de existencias y disponibilidad.
- Registro de entradas y salidas.
- Ajustes de inventario.
- Consulta del historial de movimientos.
- Integración de las operaciones de inventario con ventas.
- Administración de usuarios y permisos.
- Integración futura con reservas, servicios y otras áreas del negocio.

Estas funcionalidades representan el alcance previsto, no una certificación de que todas estén terminadas.

El estado de cada funcionalidad debe verificarse en el código, sus vistas, modelos, formularios, servicios y pruebas. Las páginas de referencia o los componentes de interfaz no deben considerarse operaciones completas si todavía no realizan las acciones correspondientes sobre la base de datos.

### 9.1. Criterios para considerar una funcionalidad terminada

Antes de marcar una tarea como completada, comprobar que:

1. La interfaz permite ejecutar la operación requerida.
2. Se aplican las validaciones correspondientes.
3. Los datos se consultan o guardan correctamente en MySQL.
4. Se controlan los errores esperables.
5. Se respetan los permisos definidos para la operación.
6. Se han realizado las pruebas correspondientes.
7. Los cambios están integrados con el resto del proyecto.

---

## 10. Organización del trabajo en equipo

La distribución de tareas debe mantenerse coordinada entre los integrantes para evitar duplicaciones en vistas, modelos, servicios y consultas.

Como propuesta inicial, la división del trabajo puede organizarse de la siguiente manera:

| Área | Responsabilidades propuestas |
|---|---|
| Productos | Listado, registro, edición, consulta y validaciones de productos. |
| Stock | Consulta de existencias, disponibilidad y reglas de actualización del stock. |
| Movimientos | Registro de entradas, salidas y ajustes de inventario. |
| Historial e integración | Consulta de movimientos, pruebas de integración y coordinación con otros módulos. |

Esta distribución es orientativa. Debe adaptarse a los acuerdos del equipo y a las responsabilidades efectivamente asignadas.

### 10.1. Reglas de coordinación

- Revisar el esquema SQL antes de crear o modificar tablas.
- No duplicar entidades que ya existan en el modelo compartido.
- Acordar las relaciones y los nombres de campos antes de implementar funcionalidades dependientes.
- Coordinar cambios que afecten a varias áreas.
- Mantener actualizados los archivos compartidos.
- Documentar las decisiones que puedan afectar la integración.
- Probar las operaciones antes de considerar una tarea terminada.

---

## 11. Flujo de trabajo con Git y GitHub

El repositorio utiliza Git para controlar las versiones y GitHub para compartir los cambios.

Se recomienda que cada integrante trabaje en una rama propia y utilice Pull Requests para integrar modificaciones.

### 11.1. Actualizar la rama principal

Antes de comenzar una tarea:

```powershell
git switch main
git pull origin main
```

Si existen cambios locales sin guardar, resolverlos antes de cambiar de rama o actualizar el repositorio.

### 11.2. Crear una rama de trabajo

Crear una rama descriptiva para la tarea:

```powershell
git switch -c feature/nombre-de-la-tarea
```

Ejemplos:

```powershell
git switch -c feature/gestion-productos
git switch -c feature/consulta-stock
git switch -c feature/movimientos
git switch -c feature/historial
```

Cada ejemplo representa una rama alternativa. No es necesario ejecutarlos todos.

### 11.3. Revisar los cambios

Antes de registrar los archivos:

```powershell
git status
git diff
```

Comprobar que los cambios correspondan a la tarea y que no incluyan archivos locales, credenciales o modificaciones accidentales.

### 11.4. Registrar los cambios

Añadir los archivos necesarios:

```powershell
git add archivo_o_carpeta
```

Crear el commit:

```powershell
git commit -m "Descripción breve del cambio"
```

Los mensajes deben describir el propósito del cambio de forma clara.

### 11.5. Publicar la rama

```powershell
git push -u origin feature/nombre-de-la-tarea
```

Después, crear un Pull Request en GitHub para revisar los cambios antes de incorporarlos a `main`.

### 11.6. Buenas prácticas

- Evitar trabajar directamente sobre `main`.
- Actualizar la rama antes de comenzar tareas nuevas.
- Realizar commits pequeños y relacionados con un propósito concreto.
- No incluir `.env`, `.venv/`, contraseñas ni credenciales.
- No sobrescribir los cambios de otros integrantes sin coordinación.
- Resolver conflictos de Git antes de integrar una rama.
- Revisar el resultado de las pruebas después de integrar cambios.

---

## 12. Seguridad y manejo de información sensible

El repositorio debe contener el código fuente y la configuración de ejemplo, pero no los secretos de cada entorno.

Se deben cumplir las siguientes reglas:

- No subir el archivo `.env`.
- No escribir contraseñas reales en el código fuente ni en el README.
- No compartir credenciales de MySQL mediante commits.
- No importar scripts destructivos sobre bases con información importante.
- Limitar los permisos de las cuentas de MySQL según las necesidades de cada entorno.
- Validar los permisos de acceso a las operaciones de negocio.
- Revisar los cambios antes de publicarlos en GitHub.

Si una contraseña o credencial se publica accidentalmente, no basta con eliminarla del último commit: se debe cambiar o revocar la credencial afectada y revisar el historial cuando corresponda.

---

## 13. Solución de problemas frecuentes

### 13.1. No se encuentra Python

Verificar la instalación:

```powershell
python --version
```

Si el comando no funciona, revisar que Python esté instalado y disponible en el `PATH`.

### 13.2. No se puede activar el entorno virtual

Comprobar que exista `.venv` y que el comando se ejecute desde la carpeta raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si no existe el entorno virtual, crearlo nuevamente con `python -m venv .venv`.

### 13.3. No se puede conectar a MySQL

Comprobar el servicio MySQL, el nombre de la base de datos y las variables del archivo `.env`. También se deben verificar los permisos del usuario y el puerto configurado.

### 13.4. Error al importar el SQL

Antes de ejecutar un script:

- Confirmar que se seleccionó el archivo correcto.
- Comprobar el esquema de destino.
- Verificar que el archivo se encuentre completo.
- Revisar el mensaje exacto de MySQL Workbench.
- No ejecutar el volcado original sobre una base que contenga información que se quiera conservar.

### 13.5. Error al ejecutar migraciones

Comprobar qué migraciones están aplicadas y si existen tablas previas con nombres que Django intenta crear.

No se deben borrar tablas ni marcar migraciones como aplicadas para ocultar un error sin entender primero la diferencia entre el estado de la base de datos y el estado de las migraciones.

### 13.6. El servidor inicia, pero una función no trabaja

Que `runserver` inicie correctamente no garantiza que todas las operaciones estén implementadas. Revisar las URL, las vistas, las plantillas, los modelos, la conexión a la base de datos y las pruebas correspondientes.

---

## 14. Comandos de referencia

Los siguientes comandos son los más utilizados durante el desarrollo.

**Comprobar la versión de Python:**

```powershell
python --version
```

**Instalar dependencias:**

```powershell
python -m pip install -r requirements.txt
```

**Comprobar la configuración de Django:**

```powershell
python manage.py check
```

**Comprobar la conexión a MySQL:**

```powershell
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Conexión a MySQL correcta')"
```

**Aplicar migraciones de Django en una instalación preparada:**

```powershell
python manage.py migrate
```

**Crear un administrador de Django:**

```powershell
python manage.py createsuperuser
```

**Iniciar el servidor local:**

```powershell
python manage.py runserver
```

**Consultar el estado de Git:**

```powershell
git status
```

**Consultar las ramas locales:**

```powershell
git branch
```

---

## 15. Consideraciones para continuar el desarrollo

Antes de incorporar nuevas funcionalidades, el equipo debe mantener una referencia común del esquema de datos, los modelos y las responsabilidades de cada módulo.

Los cambios que afecten a la estructura de MySQL deben coordinarse y documentarse. Si se modifica el esquema, el equipo debe actualizar el SQL compartido y verificar que las instalaciones nuevas puedan reproducir la estructura esperada.

La implementación de una funcionalidad debe incluir las validaciones y pruebas necesarias, no solamente los elementos visuales de la interfaz.

Las decisiones sobre integración entre inventario, ventas, reservas y usuarios deben documentarse para evitar inconsistencias en el acceso y actualización de los datos.

**Principio de trabajo:** el código, la base de datos y la documentación deben mantenerse alineados. Ninguna funcionalidad debe darse por terminada únicamente porque exista una pantalla, una tabla o una ruta asociada.

---

## 16. Mantenimiento de esta documentación

El README debe actualizarse cuando se produzcan cambios relevantes en:

- Las dependencias y versiones utilizadas.
- La configuración de entorno.
- El esquema SQL compartido.
- La estructura del proyecto.
- Los procedimientos de instalación.
- Las responsabilidades de los módulos.
- Las funcionalidades implementadas.
- Los procedimientos de pruebas y despliegue.

La documentación debe describir el estado real del repositorio. Si una instrucción deja de ser válida o una funcionalidad cambia, se debe corregir el README en el mismo ciclo de trabajo en que se incorpora el cambio.

Este documento es la referencia inicial para instalar el proyecto y comprender su organización. Las decisiones técnicas específicas que todavía no estén implementadas deben acordarse y registrarse a medida que avance el desarrollo.


## Implementación Integrante 2: CRUD de productos

Se agregó la funcionalidad de productos sobre las tablas MySQL existentes (`producto`, `categoria_producto`, `marca` y `producto_precio`). Los modelos usan `managed = False` para evitar que las migraciones de Django intenten crear o alterar esas tablas existentes.

### Archivos implementados/modificados

- `inventario/models.py`: modelos Django mapeados a las tablas existentes.
- `inventario/forms.py`: formulario con campos obligatorios, precio no negativo y validación de SKU duplicado.
- `inventario/views.py`: listado con búsqueda y filtros, registro, edición, actualización de precio y desactivación segura.
- `inventario/urls.py`: rutas para listado, nuevo, editar y desactivar.
- `inventario/admin.py`: modelos disponibles en el administrador de Django.
- `templates/inventario/productos_lista.html`: catálogo conectado a los productos de la base de datos.
- `templates/inventario/producto_form.html`: formulario real para crear y editar.
- `static/css/inventario/productos.css`: estilos del catálogo, filtros, tabla, mensajes y estados.
- `static/css/inventario/producto_form.css`: estilos del formulario.

### Cómo probarlo

1. Configurar las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` en `.env` (no subir ese archivo a Git).
2. Instalar dependencias con `python -m pip install -r requirements.txt`.
3. Ejecutar `python manage.py check`.
4. Ejecutar `python manage.py runserver`.
5. Iniciar sesión y abrir `/productos/`.
6. Verificar que existan categorías activas y marcas activas para poder registrar un producto.

No se agregaron migraciones para las cuatro tablas de negocio porque se asume que ya existen en la base de datos compartida. La conexión real depende de las credenciales del entorno local.
