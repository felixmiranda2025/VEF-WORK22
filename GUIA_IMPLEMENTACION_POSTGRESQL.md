# VEF Automatización — Guía de Implementación PostgreSQL
## Sistema Multi-usuario en Red Local o Servidor

---

## ÍNDICE

1. Arquitectura del sistema
2. Requisitos
3. Instalación de PostgreSQL en el servidor
4. Creación de la base de datos y usuario
5. Configuración del firewall y red
6. Instalación de dependencias Python en cada PC
7. Despliegue del sistema en cada equipo cliente
8. Primer arranque y usuarios
9. Migración de datos desde SQLite (opcional)
10. Mantenimiento y respaldos
11. Solución de problemas

---

## 1. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────┐
│                    RED LOCAL / VPN                       │
│                                                         │
│  PC Usuario 1          PC Usuario 2        PC Usuario 3 │
│  ┌──────────┐          ┌──────────┐        ┌──────────┐ │
│  │ vef_pg.py│          │ vef_pg.py│        │ vef_pg.py│ │
│  │ (cliente)│          │ (cliente)│        │ (cliente)│ │
│  └────┬─────┘          └────┬─────┘        └────┬─────┘ │
│       │                     │                   │       │
│       └─────────────────────┴───────────────────┘       │
│                             │  Puerto 5432              │
│                    ┌────────▼────────┐                  │
│                    │   SERVIDOR      │                  │
│                    │  PostgreSQL 16  │                  │
│                    │  Windows/Linux  │                  │
│                    │  (1 sola BD)    │                  │
│                    └─────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

**Roles de usuario:**
| Rol          | Permisos                                          |
|--------------|---------------------------------------------------|
| `admin`      | Todo + gestión de usuarios                        |
| `gerente`    | Todo excepto gestión de usuarios                  |
| `operador`   | Crear/editar/ver registros propios y de todos     |
| `solo_lectura` | Solo consultar, sin crear ni modificar          |

---

## 2. REQUISITOS

### Servidor (la computadora que tiene la BD)
- Windows 10/11 o Windows Server 2019/2022 o Ubuntu 20+
- PostgreSQL 14, 15 o 16
- RAM mínima: 4 GB (8 GB recomendado)
- Disco: 20 GB libres mínimo
- Red local estable (cable o WiFi 5GHz)

### Cada PC cliente (usuarios)
- Windows 10/11 o macOS o Linux
- Python 3.9 o superior
- Acceso a la red local donde está el servidor
- Las librerías: `psycopg2-binary`, `reportlab`, `pillow`

---

## 3. INSTALACIÓN DE POSTGRESQL EN EL SERVIDOR

### 3A — Windows Server / Windows 10/11

1. Descarga el instalador oficial:
   👉 https://www.postgresql.org/download/windows/
   Versión recomendada: **PostgreSQL 16**

2. Ejecuta el instalador como Administrador.
   - Componentes a instalar: ✅ PostgreSQL Server  ✅ pgAdmin 4  ✅ Command Line Tools
   - Directorio: dejar el predeterminado (`C:\Program Files\PostgreSQL\16`)
   - **Contraseña del superusuario `postgres`**: elige una segura, ej. `Postgres2024#`
   - Puerto: **5432** (dejar predeterminado)
   - Locale: `Spanish, Mexico` o `Default locale`

3. Al terminar, **NO** ejecutes Stack Builder a menos que quieras extensiones extra.

4. Verifica que el servicio esté corriendo:
   - Abre **Servicios** de Windows (`services.msc`)
   - Busca `postgresql-x64-16`
   - Estado: **En ejecución** ✅
   - Tipo de inicio: **Automático** ✅

### 3B — Ubuntu / Debian Linux

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib

# Verificar que el servicio está activo
sudo systemctl status postgresql
sudo systemctl enable postgresql

# Entrar como superusuario de postgres
sudo -u postgres psql
```

---

## 4. CREACIÓN DE BASE DE DATOS Y USUARIO

Abre una terminal con acceso a `psql`. En Windows usa el programa
**SQL Shell (psql)** que instaló PostgreSQL, o pgAdmin 4.

```sql
-- Conectarte como superusuario postgres
-- En Windows: busca "SQL Shell (psql)" en el menú inicio
-- En Linux: sudo -u postgres psql

-- 1. Crear el usuario de la aplicación
CREATE USER vef_user WITH PASSWORD 'VefPass2024#Segura!';

-- 2. Crear la base de datos
CREATE DATABASE vef_db
    WITH OWNER = vef_user
    ENCODING = 'UTF8'
    LC_COLLATE = 'es_MX.UTF-8'
    LC_CTYPE = 'es_MX.UTF-8'
    TEMPLATE = template0;

-- Si el locale español da error, usa:
-- CREATE DATABASE vef_db WITH OWNER = vef_user ENCODING = 'UTF8';

-- 3. Otorgar todos los privilegios
GRANT ALL PRIVILEGES ON DATABASE vef_db TO vef_user;

-- 4. Conectarse a la BD para otorgar schema
\c vef_db

GRANT ALL ON SCHEMA public TO vef_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vef_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO vef_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO vef_user;

-- 5. Salir
\q
```

> **¡Guarda estas credenciales!** Las necesitarás para `db_config.json`.

---

## 5. CONFIGURACIÓN DEL FIREWALL Y RED

### Para que los equipos clientes puedan conectarse al servidor:

### 5A — Permitir conexiones remotas en PostgreSQL

**Edita `postgresql.conf`:**
- Windows: `C:\Program Files\PostgreSQL\16\data\postgresql.conf`
- Linux: `/etc/postgresql/16/main/postgresql.conf`

Busca y cambia:
```
# Antes:
#listen_addresses = 'localhost'

# Después:
listen_addresses = '*'
```

**Edita `pg_hba.conf`** (mismo directorio):
```
# Agrega al final del archivo:
# Permite conexiones desde cualquier IP de la red local 192.168.x.x
host    vef_db    vef_user    192.168.0.0/16    scram-sha-256

# Si tu red es 10.x.x.x:
host    vef_db    vef_user    10.0.0.0/8        scram-sha-256
```

**Reinicia PostgreSQL:**
- Windows: En Servicios → clic derecho sobre postgresql-x64-16 → **Reiniciar**
- Linux: `sudo systemctl restart postgresql`

### 5B — Firewall de Windows (Servidor)

1. Abre **Windows Defender Firewall con seguridad avanzada**
2. Reglas de entrada → **Nueva regla**
3. Tipo: **Puerto**
4. TCP, puerto específico: **5432**
5. Permitir la conexión
6. Aplicar a: Dominio ✅  Privado ✅  Público ❌
7. Nombre: `PostgreSQL VEF`

### 5C — Obtener la IP del servidor

En el servidor, abre CMD y ejecuta:
```cmd
ipconfig
```
Anota la dirección IPv4, por ejemplo: `192.168.1.100`

> **Recomendación**: Asigna IP fija al servidor desde el router (reserva por MAC).

---

## 6. INSTALACIÓN DE DEPENDENCIAS PYTHON EN CADA PC

Ejecuta esto en **cada computadora cliente** (una sola vez):

```cmd
# Abre CMD o PowerShell como usuario normal

# Verificar versión de Python (necesita 3.9+)
python --version

# Instalar todas las dependencias
pip install psycopg2-binary reportlab pillow

# Verificar instalación
python -c "import psycopg2; print('psycopg2 OK')"
python -c "import reportlab; print('reportlab OK')"
```

Si `python` no está instalado:
👉 https://www.python.org/downloads/
Marca ✅ **Add Python to PATH** durante la instalación.

---

## 7. DESPLIEGUE DEL SISTEMA EN CADA PC CLIENTE

1. **Copia los archivos** al equipo cliente (USB, red, OneDrive, etc.):
   ```
   📁 VEF_Sistema/
   ├── vef_postgresql.py     ← Archivo principal
   ├── db_config.json        ← Configuración de conexión (ver paso 7.2)
   └── logo.png              ← Logo de la empresa (opcional)
   ```

2. **Crea el archivo `db_config.json`** en la misma carpeta:
   ```json
   {
     "host":     "192.168.1.100",
     "port":     5432,
     "database": "vef_db",
     "user":     "vef_user",
     "password": "VefPass2024#Segura!"
   }
   ```
   Cambia `host` por la IP real de tu servidor.

3. **Crea un acceso directo** para los usuarios:
   - Clic derecho en el escritorio → Nuevo → Acceso directo
   - Ubicación: `python "C:\VEF_Sistema\vef_postgresql.py"`
   - Nombre: `VEF Automatización`
   - (Opcional) Cambia el ícono del acceso directo

4. **O crea un archivo .bat** para doble clic:
   ```bat
   @echo off
   cd /d "C:\VEF_Sistema"
   python vef_postgresql.py
   pause
   ```
   Guárdalo como `Iniciar_VEF.bat`

---

## 8. PRIMER ARRANQUE Y USUARIOS

### Primera ejecución

1. Ejecuta `vef_postgresql.py` (o el `.bat`)
2. El sistema creará automáticamente todas las tablas en PostgreSQL
3. Se crea un usuario admin por defecto:
   - **Usuario:** `admin`
   - **Contraseña:** `Admin123!`

### ⚠️ IMPORTANTE: Cambia la contraseña del admin de inmediato

Al entrar como admin, ve al menú **👥 Usuarios** y cambia la contraseña.

### Crear usuarios para cada empleado

1. Entra con el usuario `admin`
2. En la barra superior, clic en **👥 Usuarios**
3. Clic en **➕ Nuevo usuario**
4. Llena: usuario, nombre completo, contraseña y rol:
   - `admin` — Acceso total + gestión de usuarios
   - `gerente` — Acceso total a módulos comerciales
   - `operador` — Uso diario: cotizar, reportes, OC
   - `solo_lectura` — Solo consultar

Ejemplo de usuarios a crear:
| Usuario    | Nombre             | Rol       |
|------------|--------------------|-----------|
| `jgarcia`  | Juan García        | gerente   |
| `mlopez`   | María López        | operador  |
| `crodriguez`| Carlos Rodríguez  | operador  |

---

## 9. MIGRACIÓN DE DATOS DESDE SQLITE (OPCIONAL)

Si ya tienes datos en el sistema anterior (`automatizacion.db`), usa este script
para migrarlos a PostgreSQL. **Ejecuta solo una vez.**

```python
# migrar_datos.py
import sqlite3
import psycopg2
import json

# Configuración
SQLITE_FILE = "automatizacion.db"
with open("db_config.json") as f:
    PG_CONFIG = json.load(f)

def migrar():
    sq = sqlite3.connect(SQLITE_FILE)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(**PG_CONFIG)
    pg_cur = pg.cursor()

    tablas = [
        "clientes", "proveedores", "proyectos", "cotizaciones",
        "items_cotizacion", "seguimientos", "ordenes_compra",
        "facturas", "pagos", "ordenes_proveedor",
        "items_orden_proveedor", "seguimientos_oc",
        "reportes_servicio", "rst_materiales"
    ]

    for tabla in tablas:
        try:
            rows = sq.execute(f"SELECT * FROM {tabla}").fetchall()
            if not rows:
                print(f"  {tabla}: vacía, saltando.")
                continue
            cols = rows[0].keys()
            # Excluir columna 'id' para dejar que PostgreSQL asigne SERIAL
            cols_no_id = [c for c in cols if c != "id"]
            ph = ",".join(["%s"] * len(cols_no_id))
            col_str = ",".join(cols_no_id)
            sql = f"INSERT INTO {tabla} ({col_str}) VALUES ({ph}) ON CONFLICT DO NOTHING"
            for row in rows:
                vals = [row[c] for c in cols_no_id]
                pg_cur.execute(sql, vals)
            pg.commit()
            print(f"  ✅ {tabla}: {len(rows)} registros migrados")
        except Exception as e:
            pg.rollback()
            print(f"  ⚠️  {tabla}: {e}")

    # Sincronizar secuencias SERIAL
    for tabla in tablas:
        try:
            pg_cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{tabla}','id'), "
                f"COALESCE(MAX(id),0)+1, false) FROM {tabla}"
            )
        except Exception:
            pass
    pg.commit()
    sq.close(); pg.close()
    print("\n✅ Migración completada.")

if __name__ == "__main__":
    migrar()
```

Ejecuta con:
```cmd
python migrar_datos.py
```

---

## 10. MANTENIMIENTO Y RESPALDOS

### Respaldo automático diario (Windows)

Crea el archivo `backup_vef.bat`:
```bat
@echo off
set FECHA=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%
set RUTA_BACKUP=C:\Backups_VEF
mkdir %RUTA_BACKUP% 2>nul
"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" ^
    -h localhost -U vef_user -d vef_db ^
    -F c -f "%RUTA_BACKUP%\vef_db_%FECHA%.backup"
echo Backup completado: vef_db_%FECHA%.backup
```

Agrega a **Programador de tareas de Windows** para ejecutarse cada día.

### Respaldo manual desde CMD:
```cmd
pg_dump -h localhost -U vef_user -d vef_db -F c -f vef_backup.backup
```

### Restaurar un respaldo:
```cmd
pg_restore -h localhost -U vef_user -d vef_db vef_backup.backup
```

### Monitoreo básico con pgAdmin 4

pgAdmin 4 se instala junto con PostgreSQL y permite:
- Ver conexiones activas
- Ejecutar consultas
- Ver estadísticas de la BD
- Administrar usuarios y permisos

---

## 11. SOLUCIÓN DE PROBLEMAS

### ❌ "No se pudo conectar a PostgreSQL"
- Verifica que el servicio PostgreSQL esté corriendo en el servidor
- Verifica que la IP en `db_config.json` sea la correcta
- Verifica que el puerto 5432 esté abierto en el firewall del servidor
- Prueba hacer `ping 192.168.1.100` desde el cliente para verificar conectividad
- Asegúrate de que `listen_addresses = '*'` esté en `postgresql.conf`

### ❌ "password authentication failed"
- Verifica usuario y contraseña en `db_config.json`
- Verifica que el usuario tenga acceso en `pg_hba.conf`
- Reinicia PostgreSQL después de editar `pg_hba.conf`

### ❌ "psycopg2 not found"
```cmd
pip install psycopg2-binary
```

### ❌ Dos usuarios guardan al mismo tiempo y hay conflicto
- PostgreSQL maneja concurrencia automáticamente con transacciones ACID
- Si hay un error de conflicto, el sistema mostrará un mensaje y la operación
  se puede reintentar sin pérdida de datos

### ❌ El sistema es lento en red WiFi
- Usa cable de red cuando sea posible
- Verifica que el router/switch no tenga saturación
- Considera usar un switch dedicado para la red de trabajo

---

## RESUMEN RÁPIDO

```
SERVIDOR                          CLIENTES
────────                          ────────
1. Instalar PostgreSQL 16         1. Instalar Python 3.9+
2. Crear BD: vef_db               2. pip install psycopg2-binary
3. Crear usuario: vef_user              reportlab pillow
4. Editar postgresql.conf         3. Copiar vef_postgresql.py
5. Editar pg_hba.conf             4. Crear db_config.json con IP
6. Abrir puerto 5432              5. Ejecutar y crear usuarios
7. Anotar IP del servidor
```

---

*VEF Automatización — Sistema de Gestión Comercial v2.0 PostgreSQL*
*Soporte: soporte.ventas@vef-automatizacion.com · Tel: +52 (722) 115-7792*
