# Corrección del error `Table 'rg_beauty.categoria_producto' doesn't exist`

El código Django usa tablas existentes (`managed = False`), por lo que las migraciones de Django no crean estas tablas. El ZIP incluye `database/REPARAR_TABLAS_INVENTARIO.sql`, que crea las tablas necesarias solo cuando no existen y no borra ni reemplaza tablas existentes.

## Pasos

1. Abre MySQL Workbench y conéctate al servidor correcto.
2. Abre `database/REPARAR_TABLAS_INVENTARIO.sql` desde este proyecto.
3. Ejecuta el script completo con el botón del rayo.
4. Comprueba al final con:

   ```sql
   USE rg_beauty;
   SHOW TABLES LIKE 'categoria_producto';
   SHOW TABLES LIKE 'marca';
   SHOW TABLES LIKE 'producto';
   SHOW TABLES LIKE 'producto_precio';
   ```

5. En VS Code, activa el entorno virtual y ejecuta:

   ```bash
   python manage.py check
   python manage.py runserver
   ```

6. Inicia sesión y prueba `/productos/` y `/productos/nuevo/`.

## Importante

- No importes `Base_De_Datos_RG_Beauty.sql` completo si la base ya tiene datos: ese archivo contiene instrucciones `DROP TABLE`.
- El script de reparación usa `CREATE TABLE IF NOT EXISTS`; no borra tablas existentes. Si una tabla ya existe con columnas distintas, será necesario comparar su estructura antes de modificarla.
- Revisa que el archivo `.env` apunte a la base correcta y tenga credenciales válidas. Puedes copiar `.env.example` a `.env` y completar los datos locales.
