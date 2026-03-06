# ══════════════════════════════════════════════════════════════════════════════
#  Sistema de Gestión Comercial
#  Versión PostgreSQL · Multi-usuario · 2025
# ══════════════════════════════════════════════════════════════════════════════
import datetime
import os
import hashlib
import json
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tempfile

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    raise SystemExit(
        "Falta instalar psycopg2.\n"
        "Ejecuta:  pip install psycopg2-binary"
    )

# ReportLab para PDF profesional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether, Image)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

# ─────────────────────────── PALETA DE COLORES ───────────────────────────────
AZUL_OSCURO  = "#0D2B55"
AZUL_MEDIO   = "#1A4A8A"
AZUL_CLARO   = "#2E6DB4"
AZUL_SUAVE   = "#D6E4F7"
BLANCO       = "#FFFFFF"
GRIS_CLARO   = "#F4F6FA"
GRIS_TEXTO   = "#4A4A4A"
VERDE_OK     = "#27AE60"
ROJO_ERR     = "#C0392B"
NARANJA_WARN = "#E67E22"

VEF_TELEFONO = "+52 (722) 115-7792"
VEF_CORREO   = "soporte.ventas@vef-automatizacion.com"
VEF_NOMBRE   = "VEF Automatización"

# ─────────────────────── CONFIGURACIÓN POSTGRESQL ────────────────────────────
_CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_config.json")

def _cargar_config():
    defaults = {
        "host": "localhost", "port": 5432,
        "database": "vef_db", "user": "vef_user",
        "password": "CambiaEstaContrasena123!"
    }
    if os.path.isfile(_CFG_FILE):
        try:
            with open(_CFG_FILE) as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults

DB_CONFIG = _cargar_config()
SESION    = {"id": None, "nombre": "", "rol": "", "usuario": ""}
DB_NAME   = None  # Solo para compatibilidad con código existente


def _detectar_logo():
    base = os.path.dirname(os.path.abspath(__file__))
    for nombre in ("logo.png", "logo.PNG", "logo.jpg", "logo.JPG",
                   "logo.jpeg", "logo.JPEG", "logo.bmp", "logo.BMP"):
        p = os.path.join(base, nombre)
        if os.path.isfile(p):
            return p
    return ""

LOGO_PATH = _detectar_logo()


# ══════════════════════════ CAPA DE BASE DE DATOS ═════════════════════════════
class Database:
    """Wrapper PostgreSQL (psycopg2) con la misma interfaz que el original SQLite."""

    def __init__(self):
        self.conn   = None
        self.cursor = None

    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def execute(self, sql, params=()):
        # Convierte ? (SQLite) a %s (PostgreSQL) automáticamente
        pg_sql = sql.replace("?", "%s")
        self.cursor.execute(pg_sql, params)
        return self.cursor

    def fetchall(self):
        rows = self.cursor.fetchall()
        # RealDictCursor devuelve dicts; convertir a tuplas para compatibilidad
        return [tuple(r.values()) for r in rows]

    def fetchone(self):
        row = self.cursor.fetchone()
        return tuple(row.values()) if row else None

    def lastrowid(self):
        self.cursor.execute("SELECT lastval()")
        return self.cursor.fetchone()[0]


# ══════════════════════════════ ESQUEMA BD ════════════════════════════════════
_SCHEMA_SQL = """
-- ── Usuarios del sistema ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id          SERIAL PRIMARY KEY,
    usuario     VARCHAR(60) UNIQUE NOT NULL,
    nombre      VARCHAR(120) NOT NULL,
    password_hash TEXT NOT NULL,
    rol         VARCHAR(30) NOT NULL DEFAULT 'operador',
    activo      BOOLEAN DEFAULT TRUE,
    creado_en   TIMESTAMP DEFAULT NOW(),
    ultimo_acceso TIMESTAMP
);

-- ── Catálogos ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clientes (
    id          SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL,
    contacto    TEXT,
    direccion   TEXT,
    telefono    TEXT,
    email       TEXT,
    creado_por  INTEGER REFERENCES usuarios(id),
    creado_en   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS proveedores (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    contacto        TEXT,
    direccion       TEXT,
    telefono        TEXT,
    email           TEXT,
    rfc             TEXT,
    condiciones_pago TEXT,
    creado_por      INTEGER REFERENCES usuarios(id),
    creado_en       TIMESTAMP DEFAULT NOW()
);

-- ── Proyectos ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proyectos (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    cliente_id      INTEGER REFERENCES clientes(id),
    responsable     TEXT DEFAULT 'VEF Automatización',
    fecha_creacion  DATE DEFAULT CURRENT_DATE,
    estatus         TEXT DEFAULT 'activo',
    creado_por      INTEGER REFERENCES usuarios(id)
);

-- ── Cotizaciones ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cotizaciones (
    id                    SERIAL PRIMARY KEY,
    proyecto_id           INTEGER REFERENCES proyectos(id),
    numero_cotizacion     TEXT UNIQUE,
    fecha_emision         DATE DEFAULT CURRENT_DATE,
    validez_hasta         DATE,
    alcance_tecnico       TEXT,
    notas_importantes     TEXT,
    comentarios_generales TEXT,
    servicio_postventa    TEXT,
    condiciones_entrega   TEXT,
    condiciones_pago      TEXT,
    garantia              TEXT,
    responsabilidad       TEXT,
    validez               TEXT,
    fuerza_mayor          TEXT,
    ley_aplicable         TEXT,
    firmas                TEXT,
    total                 NUMERIC(14,2),
    moneda                TEXT DEFAULT 'USD',
    estatus               TEXT DEFAULT 'borrador',
    creado_por            INTEGER REFERENCES usuarios(id),
    creado_en             TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS items_cotizacion (
    id              SERIAL PRIMARY KEY,
    cotizacion_id   INTEGER REFERENCES cotizaciones(id) ON DELETE CASCADE,
    descripcion     TEXT,
    cantidad        NUMERIC(12,4),
    precio_unitario NUMERIC(14,4),
    total           NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS seguimientos (
    id              SERIAL PRIMARY KEY,
    cotizacion_id   INTEGER REFERENCES cotizaciones(id) ON DELETE CASCADE,
    fecha           TIMESTAMP DEFAULT NOW(),
    tipo            TEXT,
    notas           TEXT,
    proxima_accion  TEXT,
    usuario_id      INTEGER REFERENCES usuarios(id)
);

-- ── Órdenes de compra (cliente) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ordenes_compra (
    id              SERIAL PRIMARY KEY,
    cotizacion_id   INTEGER UNIQUE REFERENCES cotizaciones(id),
    numero_oc       TEXT,
    fecha           DATE DEFAULT CURRENT_DATE,
    archivo         TEXT,
    archivo_oc      TEXT,
    archivo_factura TEXT
);

CREATE TABLE IF NOT EXISTS facturas (
    id              SERIAL PRIMARY KEY,
    cotizacion_id   INTEGER REFERENCES cotizaciones(id),
    numero_factura  TEXT,
    fecha_emision   DATE DEFAULT CURRENT_DATE,
    monto           NUMERIC(14,2),
    estatus_pago    TEXT DEFAULT 'pendiente',
    archivo         TEXT
);

CREATE TABLE IF NOT EXISTS pagos (
    id              SERIAL PRIMARY KEY,
    factura_id      INTEGER REFERENCES facturas(id),
    fecha           DATE DEFAULT CURRENT_DATE,
    monto           NUMERIC(14,2),
    metodo          TEXT
);

-- ── Órdenes a proveedores ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ordenes_proveedor (
    id                SERIAL PRIMARY KEY,
    proveedor_id      INTEGER REFERENCES proveedores(id),
    numero_op         TEXT UNIQUE,
    fecha_emision     DATE DEFAULT CURRENT_DATE,
    fecha_entrega     DATE,
    condiciones_pago  TEXT,
    lugar_entrega     TEXT,
    notas             TEXT,
    total             NUMERIC(14,2) DEFAULT 0,
    moneda            TEXT DEFAULT 'USD',
    estatus           TEXT DEFAULT 'borrador',
    cotizacion_ref_pdf TEXT,
    creado_por        INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS items_orden_proveedor (
    id              SERIAL PRIMARY KEY,
    orden_id        INTEGER REFERENCES ordenes_proveedor(id) ON DELETE CASCADE,
    descripcion     TEXT,
    cantidad        NUMERIC(12,4),
    precio_unitario NUMERIC(14,4),
    total           NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS seguimientos_oc (
    id              SERIAL PRIMARY KEY,
    orden_id        INTEGER REFERENCES ordenes_proveedor(id) ON DELETE CASCADE,
    fecha           TIMESTAMP DEFAULT NOW(),
    tipo            TEXT,
    notas           TEXT,
    proxima_accion  TEXT,
    usuario_id      INTEGER REFERENCES usuarios(id)
);

-- ── Reportes de Servicio Técnico ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reportes_servicio (
    id                   SERIAL PRIMARY KEY,
    numero_reporte       TEXT UNIQUE,
    fecha                DATE,
    hora_inicio          TIME,
    hora_termino         TIME,
    empresa              TEXT,
    contacto             TEXT,
    telefono_cliente     TEXT,
    correo_cliente       TEXT,
    direccion            TEXT,
    tipo_equipo          TEXT,
    marca                TEXT,
    modelo               TEXT,
    numero_serie         TEXT,
    ubicacion_fisica     TEXT,
    srv_preventivo       BOOLEAN DEFAULT FALSE,
    srv_correctivo       BOOLEAN DEFAULT FALSE,
    srv_instalacion      BOOLEAN DEFAULT FALSE,
    srv_garantia         BOOLEAN DEFAULT FALSE,
    srv_diagnostico      BOOLEAN DEFAULT FALSE,
    srv_retiro           BOOLEAN DEFAULT FALSE,
    descripcion_problema TEXT,
    trabajos_realizados  TEXT,
    observaciones        TEXT,
    est_finalizado       BOOLEAN DEFAULT FALSE,
    est_pendiente        BOOLEAN DEFAULT FALSE,
    est_no_procede       BOOLEAN DEFAULT FALSE,
    est_autorizacion     BOOLEAN DEFAULT FALSE,
    nombre_tecnico       TEXT,
    subtotal             NUMERIC(14,2) DEFAULT 0,
    iva                  NUMERIC(14,2) DEFAULT 0,
    total                NUMERIC(14,2) DEFAULT 0,
    creado_por           INTEGER REFERENCES usuarios(id),
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rst_materiales (
    id              SERIAL PRIMARY KEY,
    reporte_id      INTEGER NOT NULL REFERENCES reportes_servicio(id) ON DELETE CASCADE,
    cantidad        NUMERIC(12,4),
    descripcion     TEXT,
    numero_parte    TEXT,
    precio_unit     NUMERIC(14,4),
    total           NUMERIC(14,2)
);

-- ── Índices de rendimiento ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cotizaciones_proyecto  ON cotizaciones(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_cotizaciones_estatus   ON cotizaciones(estatus);
CREATE INDEX IF NOT EXISTS idx_proyectos_cliente      ON proyectos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_items_cotizacion       ON items_cotizacion(cotizacion_id);
CREATE INDEX IF NOT EXISTS idx_reportes_fecha         ON reportes_servicio(fecha);
CREATE INDEX IF NOT EXISTS idx_ordenes_proveedor      ON ordenes_proveedor(proveedor_id);
"""


def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def crear_tablas():
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    # Ejecutar sentencias una a una (psycopg2 no tiene executescript)
    for stmt in _SCHEMA_SQL.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except Exception as e:
                conn.rollback()
                print(f"[WARN] {e}")
                conn = psycopg2.connect(**DB_CONFIG)
                cur  = conn.cursor()
    conn.commit()

    # Crear usuario admin por defecto si no existe
    cur.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (usuario, nombre, password_hash, rol) VALUES (%s,%s,%s,%s)",
            ("admin", "Administrador", _hash_password("Admin123!"), "admin")
        )
        conn.commit()
    conn.close()


def _migrar_db():
    """PostgreSQL no necesita migración manual — el esquema usa CREATE IF NOT EXISTS."""
    pass


# ══════════════════════════ CONFIGURACIÓN DE CONEXIÓN ════════════════════════
class ConfigConexionDialog(tk.Toplevel):
    """Diálogo para editar db_config.json antes de conectar."""
    def __init__(self, parent=None):
        if parent:
            super().__init__(parent)
        else:
            super().__init__()
        self.title("⚙️  Configurar Conexión PostgreSQL")
        self.geometry("460x360")
        self.configure(bg=GRIS_CLARO)
        self.resizable(False, False)
        self.grab_set()
        self._result = False
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=AZUL_OSCURO, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="  ⚙️  Configuración de Base de Datos PostgreSQL",
                 bg=AZUL_OSCURO, fg=BLANCO,
                 font=("Segoe UI", 11, "bold")).pack(side="left", pady=8)

        f = tk.Frame(self, bg=GRIS_CLARO, padx=30, pady=20)
        f.pack(fill="both", expand=True)

        cfg = DB_CONFIG
        fields = [
            ("Servidor (host):",     "host",     cfg.get("host","localhost")),
            ("Puerto:",              "port",     str(cfg.get("port", 5432))),
            ("Base de datos:",       "database", cfg.get("database","vef_db")),
            ("Usuario PostgreSQL:",  "user",     cfg.get("user","vef_user")),
            ("Contraseña:",          "password", cfg.get("password","")),
        ]
        self._vars = {}
        for lbl, key, default in fields:
            tk.Label(f, text=lbl, font=("Segoe UI",9), bg=GRIS_CLARO,
                     fg=GRIS_TEXTO, anchor="w", width=22).pack(fill="x", pady=(6,0))
            v = tk.StringVar(value=default)
            show = "*" if key == "password" else ""
            ttk.Entry(f, textvariable=v, font=("Segoe UI",9), show=show).pack(fill="x")
            self._vars[key] = v

        bf = tk.Frame(self, bg=GRIS_CLARO, pady=10); bf.pack(fill="x", padx=30)
        tk.Button(bf, text="💾  Guardar y Conectar",
                  command=self._guardar,
                  bg=VERDE_OK, fg=BLANCO,
                  font=("Segoe UI",10,"bold"),
                  relief="flat", cursor="hand2", padx=14, pady=6
                  ).pack(side="left", padx=(0,8))
        tk.Button(bf, text="✖  Cancelar",
                  command=self.destroy,
                  bg="#555", fg=BLANCO,
                  font=("Segoe UI",9),
                  relief="flat", cursor="hand2", padx=10, pady=6
                  ).pack(side="left")

    def _guardar(self):
        nuevo = {k: (int(v.get()) if k == "port" else v.get())
                 for k, v in self._vars.items()}
        try:
            with open(_CFG_FILE, "w") as f:
                json.dump(nuevo, f, indent=2)
            DB_CONFIG.update(nuevo)
            self._result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=self)


# ═══════════════════════════════════════════════════════════════════════════════
#  MÓDULO: Login de película + Dashboard + Config empresa + Navbar dropdown
#  Reemplaza: LoginWindow, App class, make_contact_bar
# ═══════════════════════════════════════════════════════════════════════════════

import math, threading, time as _time

# ──────────────────── CONFIG EMPRESA (guardada en empresa_config.json) ────────
_EMP_CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "empresa_config.json")

def _cargar_empresa():
    defaults = {
        "nombre":    "VEF Automatización",
        "slogan":    "Soluciones de automatización industrial",
        "telefono":  "+52 (722) 115-7792",
        "correo":    "soporte.ventas@vef-automatizacion.com",
        "direccion": "Estado de México, México",
        "sitio_web": "www.vef-automatizacion.com",
        "color_primario":   "#0D2B55",
        "color_secundario": "#1A4A8A",
        "color_acento":     "#2E6DB4",
        "video_path":       "",
    }
    if os.path.isfile(_EMP_CFG_FILE):
        try:
            with open(_EMP_CFG_FILE) as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults

def _guardar_empresa(cfg: dict):
    with open(_EMP_CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

EMP = _cargar_empresa()

def _sync_globals():
    """Sincroniza EMP con las variables globales de colores y VEF_*."""
    global VEF_NOMBRE, VEF_TELEFONO, VEF_CORREO
    global AZUL_OSCURO, AZUL_MEDIO, AZUL_CLARO
    VEF_NOMBRE   = EMP["nombre"]
    VEF_TELEFONO = EMP["telefono"]
    VEF_CORREO   = EMP["correo"]
    AZUL_OSCURO  = EMP["color_primario"]
    AZUL_MEDIO   = EMP["color_secundario"]
    AZUL_CLARO   = EMP["color_acento"]

_sync_globals()


# ─────────────────────── PANTALLA DE LOGIN ESTILO WEB ─────────────────────────
class LoginWindow(tk.Tk):
    """
    Login de pantalla completa tipo landing page:
    • Fondo animado con partículas flotantes (canvas)
    • Panel izquierdo: branding inclinado / video
    • Panel derecho: formulario con dropdown de usuario
    • Animación de entrada (fade-in)
    """
    _PARTICLES = 55          # cantidad de partículas
    _SPEED     = 0.35        # velocidad base

    def __init__(self):
        super().__init__()
        self.title(f"{EMP['nombre']} — Acceso al sistema")
        self.attributes("-fullscreen", True)          # pantalla completa
        self.configure(bg=EMP["color_primario"])
        self.resizable(True, True)
        self._login_ok   = False
        self._anim_after = None
        self._particles  = []
        self._alpha      = 0.0          # para fade-in
        self._video_frames = []
        self._video_idx    = 0
        self._logo_img     = None
        self._logo_big_img = None

        # Cargar usuarios para el dropdown
        self._usernames = self._get_usernames()

        self._build()
        self._init_particles()
        self._animate_bg()
        self._fade_in()

        # Esc = salir
        self.bind("<Escape>", lambda e: self._exit())
        self.bind("<F11>", lambda e: self.attributes("-fullscreen",
                  not self.attributes("-fullscreen")))

    # ── helpers ───────────────────────────────────────────────────────────────
    def _get_usernames(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur  = conn.cursor()
            cur.execute("SELECT usuario FROM usuarios WHERE activo=TRUE ORDER BY nombre")
            rows = [r[0] for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def _exit(self):
        if self._anim_after:
            self.after_cancel(self._anim_after)
        self.destroy()

    # ── construcción UI ───────────────────────────────────────────────────────
    def _build(self):
        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()

        # Canvas de fondo (toda la pantalla)
        self.bg_canvas = tk.Canvas(self, bg=EMP["color_primario"],
                                    highlightthickness=0, cursor="none")
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # ── PANEL IZQUIERDO (branding + video) ────────────────────────────────
        panel_w = int(W * 0.52)
        self.left = tk.Frame(self, bg="", bd=0)
        self.left.place(x=0, y=0, width=panel_w, relheight=1)

        # Canvas del panel izquierdo (tono más oscuro, forma inclinada dibujada en bg_canvas)
        self.left_canvas = tk.Canvas(self.left,
                                      bg=EMP["color_primario"],
                                      highlightthickness=0)
        self.left_canvas.pack(fill="both", expand=True)

        # Video o imagen de presentación
        self.video_label = tk.Label(self.left_canvas,
                                     bg=EMP["color_primario"])
        # Centrar verticalmente dentro del panel izq
        self.left_canvas.create_window(panel_w//2, H//2 - 60,
                                        window=self.video_label, tags="video_win")

        self._try_load_video()

        # Logo grande
        logo_y = 80
        if LOGO_PATH:
            try:
                from PIL import Image as PILImg, ImageTk
                img = PILImg.open(LOGO_PATH)
                ratio = min(180/img.width, 90/img.height)
                img = img.resize((int(img.width*ratio), int(img.height*ratio)),
                                  PILImg.LANCZOS)
                self._logo_big_img = ImageTk.PhotoImage(img)
                self.left_canvas.create_image(panel_w//2, logo_y,
                                               image=self._logo_big_img,
                                               anchor="n", tags="logo_big")
                logo_y += img.height + 20
            except Exception:
                pass

        # Texto de marca
        self.left_canvas.create_text(panel_w//2, logo_y,
            text=EMP["nombre"],
            font=("Segoe UI", 28, "bold"),
            fill=BLANCO, anchor="n", tags="brand_name")

        self.left_canvas.create_text(panel_w//2, logo_y + 46,
            text=EMP.get("slogan",""),
            font=("Segoe UI", 13),
            fill="#A8C8F0", anchor="n", tags="brand_slogan")

        # Línea decorativa inclinada (dibujada en bg_canvas después del resize)
        self.bg_canvas.bind("<Configure>", self._draw_bg_shapes)

        # Info de contacto abajo-izquierda
        info_frame = tk.Frame(self.left, bg=EMP["color_primario"])
        self.left_canvas.create_window(panel_w//2, H - 60,
                                        window=info_frame, tags="info_win")
        for txt in [f"☎  {EMP['telefono']}",
                    f"✉  {EMP['correo']}",
                    f"🌐  {EMP.get('sitio_web','')}"]:
            tk.Label(info_frame, text=txt,
                     font=("Segoe UI",9), bg=EMP["color_primario"],
                     fg="#7AAFD4").pack(anchor="center")

        # ── PANEL DERECHO (formulario) ────────────────────────────────────────
        card_w = min(420, W - panel_w - 40)
        card_x = panel_w + (W - panel_w - card_w) // 2
        card_y = (H - 480) // 2

        self.card = tk.Frame(self, bg=BLANCO,
                              bd=0, relief="flat")
        self.card.place(x=card_x, y=card_y, width=card_w, height=500)

        self._build_card(card_w)

    def _build_card(self, card_w):
        """Formulario de login dentro del card blanco."""
        c = self.card

        # Franja superior de color
        top = tk.Frame(c, bg=EMP["color_secundario"], height=8)
        top.pack(fill="x")

        body = tk.Frame(c, bg=BLANCO, padx=40, pady=28)
        body.pack(fill="both", expand=True)

        # Logo pequeño dentro del card
        if LOGO_PATH:
            try:
                from PIL import Image as PILImg, ImageTk
                img = PILImg.open(LOGO_PATH)
                ratio = min(64/img.width, 32/img.height)
                img = img.resize((int(img.width*ratio), int(img.height*ratio)),
                                  PILImg.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(body, image=self._logo_img, bg=BLANCO).pack(pady=(0,6))
            except Exception:
                pass

        tk.Label(body, text="Iniciar Sesión",
                 bg=BLANCO, fg=EMP["color_primario"],
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(body, text="Ingresa tus credenciales para continuar",
                 bg=BLANCO, fg="#888",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 18))

        # ── Usuario (Combobox dropdown) ───────────────────────────────────────
        tk.Label(body, text="Usuario", bg=BLANCO, fg=GRIS_TEXTO,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.cb_user = ttk.Combobox(body,
                                     values=self._usernames,
                                     font=("Segoe UI", 11),
                                     state="normal")
        if self._usernames:
            self.cb_user.set(self._usernames[0])
        self.cb_user.pack(fill="x", pady=(3, 12), ipady=4)
        self.cb_user.bind("<Return>", lambda e: self.e_pass.focus())

        # ── Contraseña ────────────────────────────────────────────────────────
        tk.Label(body, text="Contraseña", bg=BLANCO, fg=GRIS_TEXTO,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        pw_frame = tk.Frame(body, bg=BLANCO); pw_frame.pack(fill="x", pady=(3,12))
        self.e_pass = ttk.Entry(pw_frame, font=("Segoe UI", 11), show="●")
        self.e_pass.pack(side="left", fill="x", expand=True, ipady=4)
        self.e_pass.bind("<Return>", lambda e: self._login())

        # Toggle mostrar contraseña
        self._show_pw = False
        def _toggle_pw():
            self._show_pw = not self._show_pw
            self.e_pass.config(show="" if self._show_pw else "●")
            btn_eye.config(text="🙈" if self._show_pw else "👁")
        btn_eye = tk.Button(pw_frame, text="👁", command=_toggle_pw,
                            bg=BLANCO, fg="#999", relief="flat",
                            cursor="hand2", font=("Segoe UI",11))
        btn_eye.pack(side="right")

        # ── Mensaje de error ──────────────────────────────────────────────────
        self.lbl_error = tk.Label(body, text="", bg=BLANCO, fg=ROJO_ERR,
                                   font=("Segoe UI", 9))
        self.lbl_error.pack(anchor="w", pady=(0, 8))

        # ── Botón Entrar ──────────────────────────────────────────────────────
        self.btn_login = tk.Button(body,
                                    text="  ENTRAR  →",
                                    command=self._login,
                                    bg=EMP["color_secundario"],
                                    fg=BLANCO,
                                    font=("Segoe UI", 12, "bold"),
                                    relief="flat", cursor="hand2",
                                    activebackground=EMP["color_acento"],
                                    activeforeground=BLANCO,
                                    pady=12)
        self.btn_login.pack(fill="x")

        # Hover effect
        self.btn_login.bind("<Enter>", lambda e: self.btn_login.config(
            bg=EMP["color_acento"]))
        self.btn_login.bind("<Leave>", lambda e: self.btn_login.config(
            bg=EMP["color_secundario"]))

        # ── Links pie de card ─────────────────────────────────────────────────
        pie = tk.Frame(body, bg=BLANCO); pie.pack(fill="x", pady=(18, 0))
        tk.Button(pie, text="⚙️ Configurar BD",
                  bg=BLANCO, fg="#AAA",
                  font=("Segoe UI", 8), relief="flat", cursor="hand2",
                  command=self._config_bd).pack(side="left")
        tk.Button(pie, text="🏢 Datos de empresa",
                  bg=BLANCO, fg="#AAA",
                  font=("Segoe UI", 8), relief="flat", cursor="hand2",
                  command=self._config_empresa).pack(side="right")

        # Franja inferior
        bot = tk.Frame(c, bg=EMP["color_primario"], height=6)
        bot.pack(fill="x", side="bottom")

    # ── Fondo animado ─────────────────────────────────────────────────────────
    def _draw_bg_shapes(self, event=None):
        """Dibuja la forma inclinada del panel izquierdo sobre el fondo."""
        W = self.winfo_width() or self.winfo_screenwidth()
        H = self.winfo_height() or self.winfo_screenheight()
        pw = int(W * 0.52)
        slant = 60  # píxeles de inclinación

        self.bg_canvas.delete("bg_shape")
        # Forma del panel izquierdo (inclinada a la derecha)
        pts = [0, 0, pw + slant, 0, pw, H, 0, H]
        self.bg_canvas.create_polygon(pts,
            fill=EMP["color_primario"],
            outline="", tags="bg_shape")

        # Fondo general más oscuro
        darker = "#091E3A"
        self.bg_canvas.create_rectangle(0, 0, W, H,
            fill=darker, outline="", tags="bg_shape")
        self.bg_canvas.create_polygon(pts,
            fill=EMP["color_primario"],
            outline="", tags="bg_shape")
        # Línea brillante en el borde inclinado
        self.bg_canvas.create_line(pw + slant, 0, pw, H,
            fill=EMP["color_acento"], width=3, tags="bg_shape")

        self.bg_canvas.tag_lower("bg_shape")

    def _init_particles(self):
        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()
        for _ in range(self._PARTICLES):
            x  = W * 0.52 * (0.05 + 0.9 * __import__("random").random())
            y  = __import__("random").random() * H
            r  = __import__("random").uniform(1.5, 4.5)
            dx = __import__("random").uniform(-self._SPEED, self._SPEED)
            dy = __import__("random").uniform(-self._SPEED * 0.5, -self._SPEED * 0.1)
            alpha = __import__("random").uniform(0.2, 0.7)
            self._particles.append([x, y, r, dx, dy, alpha])

    def _animate_bg(self):
        """Anima partículas en el bg_canvas cada 33 ms (~30 fps)."""
        import random
        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()
        pw = int(W * 0.52)

        self.bg_canvas.delete("particle")
        for p in self._particles:
            x, y, r, dx, dy, alpha = p
            # Color con alpha simulado mezclando con fondo
            grey = int(255 * alpha)
            col = f"#{grey:02x}{grey+20 if grey+20<=255 else 255:02x}{min(grey+60,255):02x}"
            self.bg_canvas.create_oval(x-r, y-r, x+r, y+r,
                                        fill=col, outline="", tags="particle")
            p[0] += dx
            p[1] += dy
            # Rebotar en bordes del panel izquierdo
            if p[0] < 0 or p[0] > pw + 60:
                p[2] = random.uniform(1.5, 4.5)
                p[0] = random.uniform(10, pw - 10)
                p[1] = H + 5
            if p[1] < -10:
                p[1] = H + 5
                p[0] = random.uniform(10, pw - 10)

        self.bg_canvas.tag_lower("particle")
        self.bg_canvas.tag_lower("bg_shape")
        self._anim_after = self.after(33, self._animate_bg)

    def _fade_in(self):
        """Efecto fade-in de la ventana (0→1 en ~0.6 s)."""
        try:
            self.attributes("-alpha", self._alpha)
        except Exception:
            return
        if self._alpha < 1.0:
            self._alpha = min(1.0, self._alpha + 0.06)
            self.after(20, self._fade_in)

    # ── Video ─────────────────────────────────────────────────────────────────
    def _try_load_video(self):
        """Carga frames de video MP4/GIF para mostrar en el panel izquierdo."""
        vpath = EMP.get("video_path", "")
        if not vpath or not os.path.isfile(vpath):
            self._load_logo_anim()
            return
        ext = os.path.splitext(vpath)[1].lower()
        if ext == ".gif":
            self._load_gif(vpath)
        else:
            self._load_mp4(vpath)

    def _load_gif(self, path):
        try:
            from PIL import Image as PILImg, ImageTk
            gif = PILImg.open(path)
            frames = []
            try:
                while True:
                    frame = gif.copy().convert("RGBA")
                    # Escalar al panel
                    pw = int(self.winfo_screenwidth() * 0.52) - 40
                    ph = int(self.winfo_screenheight() * 0.50)
                    ratio = min(pw/frame.width, ph/frame.height)
                    frame = frame.resize((int(frame.width*ratio), int(frame.height*ratio)),
                                         PILImg.LANCZOS)
                    frames.append(ImageTk.PhotoImage(frame))
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass
            if frames:
                self._video_frames = frames
                self._play_gif(0)
        except Exception:
            self._load_logo_anim()

    def _play_gif(self, idx):
        if not self._video_frames:
            return
        self.video_label.config(image=self._video_frames[idx])
        nxt = (idx + 1) % len(self._video_frames)
        self.after(80, lambda: self._play_gif(nxt))

    def _load_mp4(self, path):
        """Intenta usar opencv-python para reproducir MP4."""
        try:
            import cv2
            from PIL import Image as PILImg, ImageTk

            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24
            delay = int(1000 / fps)

            def _next_frame():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.after(delay, _next_frame)
                    return
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pw = int(self.winfo_screenwidth() * 0.52) - 40
                ph = int(self.winfo_screenheight() * 0.45)
                from PIL import Image as PILImg
                img = PILImg.fromarray(frame)
                ratio = min(pw/img.width, ph/img.height)
                img = img.resize((int(img.width*ratio), int(img.height*ratio)))
                photo = ImageTk.PhotoImage(img)
                self.video_label.config(image=photo)
                self.video_label._photo = photo  # evitar GC
                self.after(delay, _next_frame)

            self.after(200, _next_frame)
        except ImportError:
            self._load_logo_anim()
        except Exception:
            self._load_logo_anim()

    def _load_logo_anim(self):
        """Animación de pulso del logo cuando no hay video."""
        if not LOGO_PATH:
            return
        try:
            from PIL import Image as PILImg, ImageTk
            base_img = PILImg.open(LOGO_PATH).convert("RGBA")
            pw = int(self.winfo_screenwidth() * 0.52) - 60
            ph = int(self.winfo_screenheight() * 0.35)
            ratio = min(pw/base_img.width, ph/base_img.height)
            base_img = base_img.resize(
                (int(base_img.width*ratio), int(base_img.height*ratio)),
                PILImg.LANCZOS)
            self._logo_anim_base = base_img
            self._logo_anim_t    = 0.0
            self._animate_logo()
        except Exception:
            pass

    def _animate_logo(self):
        """Efecto de escala suave (respiración)."""
        try:
            from PIL import Image as PILImg, ImageTk
            t = self._logo_anim_t
            scale = 1.0 + 0.04 * math.sin(t * 2)
            base  = self._logo_anim_base
            nw = max(1, int(base.width * scale))
            nh = max(1, int(base.height * scale))
            img = base.resize((nw, nh), PILImg.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.video_label.config(image=photo)
            self.video_label._photo = photo
            self._logo_anim_t += 0.05
            self.after(50, self._animate_logo)
        except Exception:
            pass

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _login(self):
        usuario  = self.cb_user.get().strip()
        password = self.e_pass.get()
        if not usuario or not password:
            self._shake_error("⚠  Ingresa usuario y contraseña.")
            return
        self.btn_login.config(state="disabled", text="  Verificando…")
        self.update()
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "SELECT id,nombre,rol,activo FROM usuarios "
                "WHERE usuario=%s AND password_hash=%s",
                (usuario, _hash_password(password))
            )
            row = cur.fetchone()
            if row and row["activo"]:
                SESION["id"]      = row["id"]
                SESION["nombre"]  = row["nombre"]
                SESION["rol"]     = row["rol"]
                SESION["usuario"] = usuario
                cur.execute("UPDATE usuarios SET ultimo_acceso=NOW() WHERE id=%s",
                            (row["id"],))
                conn.commit(); conn.close()
                self._login_ok = True
                if self._anim_after:
                    self.after_cancel(self._anim_after)
                self._fade_out()
            else:
                conn.close()
                self._shake_error("❌  Usuario o contraseña incorrectos.")
                self.btn_login.config(state="normal", text="  ENTRAR  →")
        except psycopg2.OperationalError as e:
            self._shake_error("❌  Sin conexión a la BD.")
            self.btn_login.config(state="normal", text="  ENTRAR  →")
            messagebox.showerror("Error de conexión",
                f"No se pudo conectar:\n{e}\n\nVerifica 'Configurar BD'.")

    def _shake_error(self, msg):
        """Muestra error y sacude el card."""
        self.lbl_error.config(text=msg)
        x0 = self.card.winfo_x()
        y0 = self.card.winfo_y()
        def shake(n=0):
            offsets = [8, -8, 6, -6, 4, -4, 2, -2, 0]
            if n < len(offsets):
                self.card.place_configure(x=x0 + offsets[n])
                self.after(30, lambda: shake(n+1))
            else:
                self.card.place_configure(x=x0)
        shake()

    def _fade_out(self):
        """Fade-out antes de cerrar."""
        alpha = self.attributes("-alpha")
        if alpha > 0.05:
            self.attributes("-alpha", alpha - 0.08)
            self.after(18, self._fade_out)
        else:
            self.destroy()

    def _config_bd(self):
        dlg = ConfigConexionDialog(self)
        self.wait_window(dlg)

    def _config_empresa(self):
        dlg = ConfigEmpresaDialog(self)
        self.wait_window(dlg)
        # Reconstruir login con nuevos datos
        _sync_globals()
        # Solo actualizamos labels (sin reconstruir todo)
        try:
            self._usernames = self._get_usernames()
            self.cb_user["values"] = self._usernames
        except Exception:
            pass


# ──────────────────────── CONFIGURACIÓN DE EMPRESA ────────────────────────────
class ConfigEmpresaDialog(tk.Toplevel):
    """Diálogo para cambiar nombre, logo, colores, slogan, video, etc."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🏢  Configuración de Empresa")
        self.geometry("620x680")
        self.configure(bg=GRIS_CLARO)
        self.resizable(True, True)
        self.grab_set()
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=AZUL_OSCURO, height=50)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="  🏢  Configuración de Empresa / Presentación",
                 bg=AZUL_OSCURO, fg=BLANCO,
                 font=("Segoe UI", 12, "bold")).pack(side="left", pady=10)

        # Canvas con scroll
        outer = tk.Frame(self, bg=GRIS_CLARO)
        outer.pack(fill="both", expand=True)
        cv  = tk.Canvas(outer, bg=GRIS_CLARO, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        f = ttk.Frame(cv, padding=24)
        fid = cv.create_window((0,0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(fid, width=e.width))

        self._vars = {}
        campos = [
            ("Nombre de la empresa:", "nombre",    EMP["nombre"]),
            ("Slogan / descripción:", "slogan",    EMP.get("slogan","")),
            ("Teléfono:",             "telefono",  EMP["telefono"]),
            ("Correo electrónico:",   "correo",    EMP["correo"]),
            ("Dirección:",            "direccion", EMP.get("direccion","")),
            ("Sitio web:",            "sitio_web", EMP.get("sitio_web","")),
        ]

        # ── Datos generales ───────────────────────────────────────────────────
        self._sec(f, "📋  Datos Generales")
        for lbl, key, val in campos:
            self._field(f, lbl, key, val)

        # ── Colores ───────────────────────────────────────────────────────────
        self._sec(f, "🎨  Colores del Sistema")
        for lbl, key, val in [
            ("Color primario (fondo/barras):", "color_primario",   EMP["color_primario"]),
            ("Color secundario (botones):",    "color_secundario", EMP["color_secundario"]),
            ("Color acento (highlights):",     "color_acento",     EMP["color_acento"]),
        ]:
            self._color_field(f, lbl, key, val)

        # ── Logo ──────────────────────────────────────────────────────────────
        self._sec(f, "🖼  Logo de la Empresa")
        logo_row = tk.Frame(f, bg=GRIS_CLARO); logo_row.pack(fill="x", pady=4)
        self._logo_var = tk.StringVar(value=LOGO_PATH or "")
        tk.Label(logo_row, text="Ruta del logo:",
                 font=("Segoe UI",9), bg=GRIS_CLARO, fg=GRIS_TEXTO, width=26,
                 anchor="w").pack(side="left")
        ttk.Entry(logo_row, textvariable=self._logo_var,
                  font=("Segoe UI",9), width=30).pack(side="left", padx=(0,4))
        tk.Button(logo_row, text="📂 Buscar",
                  font=("Segoe UI",8), bg=AZUL_MEDIO, fg=BLANCO,
                  relief="flat", cursor="hand2",
                  command=self._pick_logo).pack(side="left")

        # Preview logo
        self._logo_preview = tk.Label(f, bg=GRIS_CLARO, text="(sin logo)")
        self._logo_preview.pack(pady=6)
        self._refresh_logo_preview()

        # ── Video ─────────────────────────────────────────────────────────────
        self._sec(f, "🎬  Video de Presentación (Opcional)")
        tk.Label(f, text="Formatos soportados: .gif  (también .mp4 con opencv-python instalado)",
                 font=("Segoe UI",8,"italic"), bg=GRIS_CLARO, fg="#888").pack(anchor="w")
        vid_row = tk.Frame(f, bg=GRIS_CLARO); vid_row.pack(fill="x", pady=4)
        self._video_var = tk.StringVar(value=EMP.get("video_path",""))
        tk.Label(vid_row, text="Ruta del video/GIF:",
                 font=("Segoe UI",9), bg=GRIS_CLARO, fg=GRIS_TEXTO, width=26,
                 anchor="w").pack(side="left")
        ttk.Entry(vid_row, textvariable=self._video_var,
                  font=("Segoe UI",9), width=30).pack(side="left", padx=(0,4))
        tk.Button(vid_row, text="📂 Buscar",
                  font=("Segoe UI",8), bg=AZUL_MEDIO, fg=BLANCO,
                  relief="flat", cursor="hand2",
                  command=self._pick_video).pack(side="left")
        tk.Label(f, text="Si se deja vacío, se mostrará el logo animado.",
                 font=("Segoe UI",8), bg=GRIS_CLARO, fg="#888").pack(anchor="w", pady=(2,0))

        # ── Botones ───────────────────────────────────────────────────────────
        bf = tk.Frame(self, bg=GRIS_CLARO, pady=10)
        bf.pack(fill="x", padx=24)
        tk.Button(bf, text="💾  Guardar cambios",
                  command=self._guardar,
                  bg=VERDE_OK, fg=BLANCO,
                  font=("Segoe UI",11,"bold"),
                  relief="flat", cursor="hand2",
                  padx=16, pady=8).pack(side="left", padx=(0,10))
        tk.Button(bf, text="✖  Cancelar",
                  command=self.destroy,
                  bg="#555", fg=BLANCO,
                  font=("Segoe UI",9),
                  relief="flat", cursor="hand2",
                  padx=10, pady=8).pack(side="left")
        tk.Label(bf, text="Los cambios se aplican en el siguiente inicio.",
                 font=("Segoe UI",8,"italic"), bg=GRIS_CLARO, fg="#888"
                 ).pack(side="right")

    def _sec(self, parent, txt):
        fr = tk.Frame(parent, bg=AZUL_OSCURO, pady=4)
        fr.pack(fill="x", pady=(14,6))
        tk.Label(fr, text=txt, font=("Segoe UI",10,"bold"),
                 bg=AZUL_OSCURO, fg=BLANCO, padx=10).pack(anchor="w")

    def _field(self, parent, lbl, key, val):
        row = tk.Frame(parent, bg=GRIS_CLARO); row.pack(fill="x", pady=2)
        tk.Label(row, text=lbl, font=("Segoe UI",9), bg=GRIS_CLARO,
                 fg=GRIS_TEXTO, width=26, anchor="w").pack(side="left")
        v = tk.StringVar(value=val)
        ttk.Entry(row, textvariable=v, font=("Segoe UI",9), width=40
                  ).pack(side="left", fill="x", expand=True)
        self._vars[key] = v

    def _color_field(self, parent, lbl, key, val):
        row = tk.Frame(parent, bg=GRIS_CLARO); row.pack(fill="x", pady=3)
        tk.Label(row, text=lbl, font=("Segoe UI",9), bg=GRIS_CLARO,
                 fg=GRIS_TEXTO, width=26, anchor="w").pack(side="left")
        v = tk.StringVar(value=val)
        e = ttk.Entry(row, textvariable=v, font=("Segoe UI",9), width=12)
        e.pack(side="left", padx=(0,6))
        preview = tk.Label(row, bg=val, width=4, relief="flat")
        preview.pack(side="left")
        def _pick(var=v, prev=preview):
            from tkinter import colorchooser
            color = colorchooser.askcolor(color=var.get(), parent=self)[1]
            if color:
                var.set(color); prev.config(bg=color)
        tk.Button(row, text="🎨", command=_pick,
                  bg=GRIS_CLARO, fg=AZUL_OSCURO,
                  relief="flat", cursor="hand2",
                  font=("Segoe UI",10)).pack(side="left")
        self._vars[key] = v

    def _pick_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self._logo_var.set(path)
            self._refresh_logo_preview()

    def _refresh_logo_preview(self):
        path = self._logo_var.get()
        if path and os.path.isfile(path):
            try:
                from PIL import Image as PILImg, ImageTk
                img = PILImg.open(path)
                ratio = min(120/img.width, 60/img.height)
                img = img.resize((int(img.width*ratio), int(img.height*ratio)),
                                  PILImg.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._logo_preview.config(image=photo, text="")
                self._logo_preview._photo = photo
            except Exception:
                self._logo_preview.config(text="(no se pudo cargar)")
        else:
            self._logo_preview.config(text="(sin logo)", image="")

    def _pick_video(self):
        path = filedialog.askopenfilename(
            title="Seleccionar video o GIF",
            filetypes=[("Video/GIF","*.gif *.mp4 *.avi *.mov"),("GIF","*.gif"),("MP4","*.mp4")])
        if path:
            self._video_var.set(path)

    def _guardar(self):
        global LOGO_PATH
        nuevo = {k: v.get() for k, v in self._vars.items()}
        nuevo["video_path"] = self._video_var.get()
        logo = self._logo_var.get()
        if logo and os.path.isfile(logo):
            LOGO_PATH = logo
        _guardar_empresa(nuevo)
        EMP.update(nuevo)
        _sync_globals()
        messagebox.showinfo("✅ Guardado",
            "Los datos de empresa se guardaron correctamente.\n"
            "Los cambios de color y logo se verán en el próximo inicio de sesión.",
            parent=self)
        self.destroy()


# ════════════════════════════════ APP PRINCIPAL ════════════════════════════════
class App(tk.Tk):
    """Ventana principal con navbar de estilo web y dashboard de bienvenida."""

    def __init__(self):
        super().__init__()
        self.title(f"{EMP['nombre']}  —  {SESION['nombre']}  [{SESION['rol'].upper()}]")
        self.geometry("1360x800")
        self.minsize(1100, 660)
        self.configure(bg=EMP["color_primario"])

        aplicar_tema(self)
        self._build_navbar()
        self._build_body()

    # ── NAVBAR estilo web ──────────────────────────────────────────────────────
    def _build_navbar(self):
        nav = tk.Frame(self, bg=EMP["color_primario"], height=56)
        nav.pack(fill="x", side="top")
        nav.pack_propagate(False)

        # Logo + nombre
        if LOGO_PATH:
            try:
                from PIL import Image as PILImg, ImageTk
                img = PILImg.open(LOGO_PATH)
                ratio = min(40/img.width, 32/img.height)
                img = img.resize((int(img.width*ratio), int(img.height*ratio)),
                                  PILImg.LANCZOS)
                self._nav_logo = ImageTk.PhotoImage(img)
                tk.Label(nav, image=self._nav_logo,
                         bg=EMP["color_primario"]).pack(side="left", padx=(12,4), pady=8)
            except Exception:
                pass

        tk.Label(nav, text=EMP["nombre"],
                 bg=EMP["color_primario"], fg=BLANCO,
                 font=("Segoe UI",13,"bold")).pack(side="left", padx=(0,24))

        # Separador vertical
        tk.Frame(nav, bg="#FFFFFF22", width=1).pack(side="left", fill="y", pady=8)

        # Botones de navegación (van al tab correspondiente)
        self._nav_btns = {}
        nav_items = [
            ("🏠 Inicio",         self._go_home),
            ("👤 Clientes",       lambda: self._go_tab(0)),
            ("🏭 Proveedores",    lambda: self._go_tab(1)),
            ("📁 Proyectos",      lambda: self._go_tab(2)),
            ("📄 Cotizaciones",   lambda: self._go_tab(3)),
            ("🧾 Facturas",       lambda: self._go_tab(4)),
            ("📦 OC Proveedores", lambda: self._go_tab(5)),
            ("🔍 Consultas",      lambda: self._go_tab(6)),
            ("🛠️ RST",            lambda: self._go_tab(7)),
        ]
        for txt, cmd in nav_items:
            b = tk.Button(nav, text=txt, command=cmd,
                          bg=EMP["color_primario"], fg=BLANCO,
                          font=("Segoe UI",9), relief="flat",
                          cursor="hand2", padx=10, pady=18,
                          activebackground=EMP["color_secundario"],
                          activeforeground=BLANCO,
                          bd=0)
            b.pack(side="left")
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=EMP["color_secundario"]))
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=EMP["color_primario"]))
            self._nav_btns[txt] = b

        # ── Dropdown de usuario (lado derecho) ────────────────────────────────
        self._dropdown_visible = False
        user_btn_frame = tk.Frame(nav, bg=EMP["color_primario"])
        user_btn_frame.pack(side="right", padx=12)

        self.user_btn = tk.Button(
            user_btn_frame,
            text=f"  👤  {SESION['nombre']}  ▾",
            bg=EMP["color_secundario"], fg=BLANCO,
            font=("Segoe UI",9,"bold"), relief="flat",
            cursor="hand2", padx=12, pady=10,
            activebackground=EMP["color_acento"],
            command=self._toggle_dropdown)
        self.user_btn.pack()

        # Dropdown panel (oculto por defecto, se posiciona sobre el resto)
        self._dropdown = tk.Frame(self,
                                   bg=BLANCO, bd=1,
                                   relief="solid")
        # Se posiciona en _toggle_dropdown

        opciones_dd = [
            ("👤  Mi perfil",           self._mi_perfil),
            ("🏢  Datos de empresa",    self._config_empresa),
        ]
        if SESION["rol"] == "admin":
            opciones_dd.append(("👥  Gestión de usuarios", self._gestionar_usuarios))
        opciones_dd += [
            ("─────────────────", None),
            ("🔓  Cerrar sesión",        self._cerrar_sesion),
        ]
        for txt, cmd in opciones_dd:
            if cmd is None:
                tk.Frame(self._dropdown, bg="#E0E0E0", height=1).pack(fill="x", pady=2)
            else:
                b = tk.Button(self._dropdown, text=txt, command=lambda c=cmd: self._run_dd(c),
                              bg=BLANCO, fg=GRIS_TEXTO,
                              font=("Segoe UI",9), relief="flat",
                              cursor="hand2", anchor="w",
                              padx=16, pady=7,
                              activebackground=AZUL_SUAVE,
                              activeforeground=AZUL_OSCURO)
                b.pack(fill="x")
                b.bind("<Enter>", lambda e, btn=b: btn.config(bg=AZUL_SUAVE))
                b.bind("<Leave>", lambda e, btn=b: btn.config(bg=BLANCO))

        # Ocultar dropdown al hacer clic en cualquier parte
        self.bind("<Button-1>", self._hide_dropdown_if_outside)

    def _toggle_dropdown(self):
        if self._dropdown_visible:
            self._dropdown.place_forget()
            self._dropdown_visible = False
        else:
            # Posicionar debajo del botón de usuario
            self.update_idletasks()
            bx = self.user_btn.winfo_rootx() - self.winfo_rootx()
            by = self.user_btn.winfo_rooty() - self.winfo_rooty() + self.user_btn.winfo_height()
            self._dropdown.place(x=bx, y=by, width=220)
            self._dropdown.lift()
            self._dropdown_visible = True

    def _hide_dropdown_if_outside(self, event):
        if not self._dropdown_visible:
            return
        wx = self._dropdown.winfo_rootx()
        wy = self._dropdown.winfo_rooty()
        ww = self._dropdown.winfo_width()
        wh = self._dropdown.winfo_height()
        ax = event.x_root; ay = event.y_root
        if not (wx <= ax <= wx+ww and wy <= ay <= wy+wh):
            self._dropdown.place_forget()
            self._dropdown_visible = False

    def _run_dd(self, cmd):
        self._dropdown.place_forget()
        self._dropdown_visible = False
        cmd()

    # ── CUERPO: notebook + dashboard ──────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self, bg=GRIS_CLARO)
        body.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill="both", expand=True)

        # Dashboard de bienvenida (Tab 0 especial)
        self.dashboard = DashboardPage(self.notebook, self)
        self.notebook.add(self.dashboard, text="🏠  Inicio")

        # Resto de páginas
        self.clientes_page     = ClientesPage(self.notebook, self)
        self.proveedores_page  = ProveedoresPage(self.notebook, self)
        self.proyectos_page    = ProyectosPage(self.notebook, self)
        self.cotizaciones_page = CotizacionesPage(self.notebook, self)
        self.ordenes_page      = OrdenesFacturasPage(self.notebook, self)
        self.ordenes_prov_page = OrdenesProveedorPage(self.notebook, self)
        self.consultas_page    = ConsultasPage(self.notebook, self)
        self.rst_page          = ReporteServicioPage(self.notebook, self)

        for page, label in [
            (self.clientes_page,      "👤  Clientes"),
            (self.proveedores_page,   "🏭  Proveedores"),
            (self.proyectos_page,     "📁  Proyectos"),
            (self.cotizaciones_page,  "📄  Cotizaciones"),
            (self.ordenes_page,       "🧾  Órdenes y Facturas"),
            (self.ordenes_prov_page,  "📦  OC Proveedores"),
            (self.consultas_page,     "🔍  Consultas"),
            (self.rst_page,           "🛠️  Reporte Servicio"),
        ]:
            self.notebook.add(page, text=label)

        # Status bar + contact bar
        self.status_bar = tk.Label(self, text=f"  ✔  Bienvenido, {SESION['nombre']}",
                                    bg=EMP["color_primario"], fg="#90E0A0",
                                    font=("Helvetica",9), anchor=tk.W, pady=3)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        make_contact_bar(self).pack(side=tk.BOTTOM, fill=tk.X)

    # ── Helpers navbar ─────────────────────────────────────────────────────────
    def _go_home(self):
        self.notebook.select(0)

    def _go_tab(self, idx):
        # idx 0=clientes ... offset +1 por dashboard
        self.notebook.select(idx + 1)

    def set_status(self, text, ok=True):
        color = "#90E0A0" if ok else "#E09090"
        icon  = "✔" if ok else "✖"
        self.status_bar.config(text=f"  {icon}  {text}", fg=color)

    def _seleccionar_logo(self):
        global LOGO_PATH
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            LOGO_PATH = path
            self.set_status(f"Logo cargado: {os.path.basename(path)}")

    def _gestionar_usuarios(self):
        GestionUsuariosDialog(self)

    def _config_empresa(self):
        dlg = ConfigEmpresaDialog(self)
        self.wait_window(dlg)
        _sync_globals()

    def _mi_perfil(self):
        MiPerfilDialog(self)

    def _cerrar_sesion(self):
        if messagebox.askyesno("Cerrar sesión",
                "¿Deseas cerrar sesión?\nSe cerrará la aplicación."):
            self.destroy()


# ────────────────────────── DASHBOARD DE BIENVENIDA ──────────────────────────
class DashboardPage(ttk.Frame):
    """
    Página de inicio: métricas en tarjetas, video/logo animado,
    accesos rápidos y últimas actividades.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._video_frames = []
        self._logo_anim_base = None
        self._logo_anim_t = 0.0
        self._build()
        self.after(200, self._load_media)

    def _build(self):
        # Canvas con scroll
        canvas = tk.Canvas(self, bg=GRIS_CLARO, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(canvas, bg=GRIS_CLARO)
        win = canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Hero: video/logo + bienvenida ────────────────────────────────────
        hero = tk.Frame(self.inner, bg=EMP["color_primario"], height=220)
        hero.pack(fill="x")

        # Contenido izquierdo
        left_hero = tk.Frame(hero, bg=EMP["color_primario"])
        left_hero.pack(side="left", fill="both", expand=True, padx=40, pady=20)

        tk.Label(left_hero,
                 text=f"¡Bienvenido, {SESION['nombre']}!",
                 bg=EMP["color_primario"], fg=BLANCO,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(left_hero,
                 text=EMP.get("slogan","Sistema de Gestión Comercial"),
                 bg=EMP["color_primario"], fg="#A8C8F0",
                 font=("Segoe UI", 12)).pack(anchor="w", pady=(4,16))
        tk.Label(left_hero,
                 text=f"Fecha: {datetime.date.today().strftime('%A %d de %B de %Y')}   "
                      f"│  Usuario: {SESION['usuario']}  [{SESION['rol']}]",
                 bg=EMP["color_primario"], fg="#7AAFD4",
                 font=("Segoe UI", 9)).pack(anchor="w")

        # Accesos rápidos en el hero
        btns_frame = tk.Frame(left_hero, bg=EMP["color_primario"])
        btns_frame.pack(anchor="w", pady=(14,0))
        for txt, tab in [("📄 Nueva cotización", 3),
                          ("👤 Clientes", 0),
                          ("🛠️ Nuevo RST", 7)]:
            tk.Button(btns_frame, text=txt,
                      command=lambda t=tab: self.app._go_tab(t),
                      bg=EMP["color_acento"], fg=BLANCO,
                      font=("Segoe UI",9,"bold"), relief="flat",
                      cursor="hand2", padx=12, pady=6).pack(side="left", padx=(0,8))

        # Video/logo animado lado derecho del hero
        self.media_label = tk.Label(hero, bg=EMP["color_primario"])
        self.media_label.pack(side="right", padx=30, pady=16)

        # ── Tarjetas de métricas ──────────────────────────────────────────────
        cards_frame = tk.Frame(self.inner, bg=GRIS_CLARO, pady=16)
        cards_frame.pack(fill="x", padx=20)
        self._metric_labels = {}
        metrics = [
            ("clientes",    "👤  Clientes",      "#3498DB"),
            ("proyectos",   "📁  Proyectos",      "#2ECC71"),
            ("cotizaciones","📄  Cotizaciones",   "#E67E22"),
            ("pendientes",  "⏳  Pendientes",     "#E74C3C"),
            ("rst",         "🛠️  RST emitidos",   "#9B59B6"),
            ("facturas",    "🧾  Facturas",        "#1ABC9C"),
        ]
        for i, (key, lbl, color) in enumerate(metrics):
            card = tk.Frame(cards_frame, bg=BLANCO,
                            relief="flat", bd=1, padx=18, pady=14)
            card.grid(row=0, column=i, padx=8, pady=4, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)

            # Franja de color superior
            tk.Frame(card, bg=color, height=5).pack(fill="x")
            num_lbl = tk.Label(card, text="—",
                               font=("Segoe UI", 28, "bold"),
                               bg=BLANCO, fg=color)
            num_lbl.pack(pady=(8,0))
            tk.Label(card, text=lbl,
                     font=("Segoe UI", 9), bg=BLANCO,
                     fg=GRIS_TEXTO).pack(pady=(0,4))
            self._metric_labels[key] = num_lbl

        # ── Últimas actividades ───────────────────────────────────────────────
        act_frame = tk.Frame(self.inner, bg=GRIS_CLARO, pady=6)
        act_frame.pack(fill="x", padx=20, pady=(6, 20))

        # Últimas cotizaciones
        self._block(act_frame, "📄  Últimas Cotizaciones",
                    side="left", expand=True)
        # Últimos RST
        self._block(act_frame, "🛠️  Últimos Reportes de Servicio",
                    side="right", expand=True)

        # Cargar datos en un hilo para no bloquear la UI
        threading.Thread(target=self._load_metrics, daemon=True).start()

    def _block(self, parent, title, side="left", expand=False):
        fr = tk.Frame(parent, bg=BLANCO, relief="flat", bd=1, padx=0)
        fr.pack(side=side, fill="both", expand=expand, padx=8, pady=4)
        tk.Frame(fr, bg=AZUL_OSCURO, height=4).pack(fill="x")
        tk.Label(fr, text=title,
                 font=("Segoe UI", 10, "bold"),
                 bg=BLANCO, fg=AZUL_OSCURO, padx=14, pady=8).pack(anchor="w")
        attr = "tree_cot" if "Cot" in title else "tree_rst"
        cols = ("num","fecha","cliente","estatus") if "Cot" in title else ("num","fecha","empresa","estatus")
        hdrs = ("Número","Fecha","Cliente/Empresa","Estatus")
        widths = (120,80,180,80)
        tree = ttk.Treeview(fr, columns=cols, show="headings", height=6)
        for c,h,w in zip(cols,hdrs,widths):
            tree.heading(c, text=h); tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(fr, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=8, pady=(0,8))
        setattr(self, attr, tree)

    def _load_metrics(self):
        try:
            db = Database(); db.connect()
            queries = {
                "clientes":     "SELECT COUNT(*) FROM clientes",
                "proyectos":    "SELECT COUNT(*) FROM proyectos WHERE estatus='activo'",
                "cotizaciones": "SELECT COUNT(*) FROM cotizaciones",
                "pendientes":   "SELECT COUNT(*) FROM cotizaciones WHERE estatus IN ('borrador','enviada')",
                "rst":          "SELECT COUNT(*) FROM reportes_servicio",
                "facturas":     "SELECT COUNT(*) FROM facturas WHERE estatus_pago='pendiente'",
            }
            for key, q in queries.items():
                db.execute(q)
                val = db.fetchone()[0]
                self.after(0, lambda k=key, v=val:
                           self._metric_labels[k].config(text=str(v)))

            # Últimas cotizaciones
            db.execute("""
                SELECT c.numero_cotizacion, c.fecha_emision,
                       cl.nombre, c.estatus
                FROM cotizaciones c
                JOIN proyectos p ON c.proyecto_id=p.id
                JOIN clientes cl ON p.cliente_id=cl.id
                ORDER BY c.id DESC LIMIT 8
            """)
            rows_cot = db.fetchall()

            # Últimos RST
            db.execute("""
                SELECT numero_reporte, fecha, empresa,
                       CASE WHEN est_finalizado THEN 'Finalizado'
                            WHEN est_pendiente  THEN 'Pendiente'
                            WHEN est_no_procede THEN 'No procede'
                            ELSE 'En proceso' END
                FROM reportes_servicio
                ORDER BY id DESC LIMIT 8
            """)
            rows_rst = db.fetchall()
            db.close()

            def _fill():
                for item in self.tree_cot.get_children():
                    self.tree_cot.delete(item)
                for r in rows_cot:
                    self.tree_cot.insert("","end", values=r)
                for item in self.tree_rst.get_children():
                    self.tree_rst.delete(item)
                for r in rows_rst:
                    self.tree_rst.insert("","end", values=r)

            self.after(0, _fill)
        except Exception:
            pass

    def _load_media(self):
        """Carga el video/GIF o anima el logo en el panel hero."""
        vpath = EMP.get("video_path","")
        if vpath and os.path.isfile(vpath):
            ext = os.path.splitext(vpath)[1].lower()
            if ext == ".gif":
                self._load_gif_dash(vpath)
            else:
                self._load_mp4_dash(vpath)
        elif LOGO_PATH:
            self._animate_logo_dash()

    def _load_gif_dash(self, path):
        try:
            from PIL import Image as PILImg, ImageTk
            gif = PILImg.open(path)
            frames = []
            try:
                while True:
                    f = gif.copy().convert("RGBA")
                    f = f.resize((220, 140), PILImg.LANCZOS)
                    frames.append(ImageTk.PhotoImage(f))
                    gif.seek(gif.tell()+1)
            except EOFError:
                pass
            if frames:
                self._video_frames = frames
                self._play_gif_dash(0)
        except Exception:
            self._animate_logo_dash()

    def _play_gif_dash(self, idx):
        if not self._video_frames:
            return
        self.media_label.config(image=self._video_frames[idx])
        self.after(80, lambda: self._play_gif_dash((idx+1) % len(self._video_frames)))

    def _load_mp4_dash(self, path):
        try:
            import cv2
            from PIL import Image as PILImg, ImageTk
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24
            delay = int(1000/fps)
            def _nxt():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.after(delay, _nxt); return
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = PILImg.fromarray(frame).resize((240, 148), PILImg.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.media_label.config(image=photo)
                self.media_label._photo = photo
                self.after(delay, _nxt)
            self.after(100, _nxt)
        except Exception:
            self._animate_logo_dash()

    def _animate_logo_dash(self):
        if not LOGO_PATH:
            return
        try:
            from PIL import Image as PILImg, ImageTk
            img = PILImg.open(LOGO_PATH).convert("RGBA")
            ratio = min(200/img.width, 120/img.height)
            self._logo_anim_base = img.resize(
                (int(img.width*ratio), int(img.height*ratio)), PILImg.LANCZOS)
            self._logo_anim_t = 0.0
            self._pulse_logo()
        except Exception:
            pass

    def _pulse_logo(self):
        try:
            from PIL import Image as PILImg, ImageTk
            s = 1.0 + 0.03 * math.sin(self._logo_anim_t * 1.5)
            b = self._logo_anim_base
            img = b.resize((max(1,int(b.width*s)), max(1,int(b.height*s))),
                            PILImg.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.media_label.config(image=photo)
            self.media_label._photo = photo
            self._logo_anim_t += 0.04
            self.after(40, self._pulse_logo)
        except Exception:
            pass


# ──────────────────────────── MI PERFIL ──────────────────────────────────────
class MiPerfilDialog(tk.Toplevel):
    """Permite al usuario cambiar su nombre y contraseña."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("👤  Mi perfil")
        self.geometry("380x340")
        self.configure(bg=GRIS_CLARO)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=AZUL_OSCURO, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  👤  {SESION['nombre']}  —  {SESION['rol']}",
                 bg=AZUL_OSCURO, fg=BLANCO,
                 font=("Segoe UI",11,"bold")).pack(side="left", pady=8)
        f = tk.Frame(self, bg=GRIS_CLARO, padx=28, pady=20); f.pack(fill="both", expand=True)
        tk.Label(f, text="Nombre completo:", font=("Segoe UI",9), bg=GRIS_CLARO,
                 fg=GRIS_TEXTO).pack(anchor="w", pady=(8,1))
        self.v_nombre = tk.StringVar(value=SESION["nombre"])
        ttk.Entry(f, textvariable=self.v_nombre, font=("Segoe UI",9)).pack(fill="x")
        tk.Label(f, text="Nueva contraseña (dejar vacío para no cambiar):",
                 font=("Segoe UI",9), bg=GRIS_CLARO, fg=GRIS_TEXTO).pack(anchor="w", pady=(12,1))
        self.v_pw1 = tk.StringVar()
        ttk.Entry(f, textvariable=self.v_pw1, show="●", font=("Segoe UI",9)).pack(fill="x")
        tk.Label(f, text="Confirmar contraseña:",
                 font=("Segoe UI",9), bg=GRIS_CLARO, fg=GRIS_TEXTO).pack(anchor="w", pady=(8,1))
        self.v_pw2 = tk.StringVar()
        ttk.Entry(f, textvariable=self.v_pw2, show="●", font=("Segoe UI",9)).pack(fill="x")
        tk.Button(f, text="💾  Guardar cambios",
                  command=self._guardar,
                  bg=VERDE_OK, fg=BLANCO,
                  font=("Segoe UI",10,"bold"),
                  relief="flat", cursor="hand2", pady=8).pack(fill="x", pady=16)

    def _guardar(self):
        nombre = self.v_nombre.get().strip()
        pw1    = self.v_pw1.get()
        pw2    = self.v_pw2.get()
        if not nombre:
            messagebox.showerror("Requerido","El nombre no puede estar vacío.", parent=self)
            return
        if pw1 and pw1 != pw2:
            messagebox.showerror("Error","Las contraseñas no coinciden.", parent=self)
            return
        db = Database(); db.connect()
        if pw1:
            db.execute("UPDATE usuarios SET nombre=%s, password_hash=%s WHERE id=%s",
                       (nombre, _hash_password(pw1), SESION["id"]))
        else:
            db.execute("UPDATE usuarios SET nombre=%s WHERE id=%s",
                       (nombre, SESION["id"]))
        db.commit(); db.close()
        SESION["nombre"] = nombre
        messagebox.showinfo("✅ Guardado","Perfil actualizado correctamente.", parent=self)
        self.destroy()



# ──────────────────────── PÁGINA CLIENTES ────────────────────────────────────
class ClientesPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.db = Database(); self.selected_id = None
        self.configure(style="TFrame"); self._build(); self.refresh_list()

    def _build(self):
        self.configure(padding=12)
        form = ttk.LabelFrame(self, text="Datos del Cliente", padding=14)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        fields = [("Nombre *","entry_nombre"),("Contacto","entry_contacto"),
                  ("Dirección","entry_direccion"),("Teléfono","entry_telefono"),("Email","entry_email")]
        for i,(lbl,attr) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=5)
            e = ttk.Entry(form, width=32); e.grid(row=i, column=1, pady=5, padx=(8,0))
            setattr(self, attr, e)
        btn_row = ttk.Frame(form); btn_row.grid(row=len(fields), column=0, columnspan=2, pady=14)
        make_button(btn_row,"💾  Guardar",self.guardar_cliente,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(btn_row,"➕  Nuevo",self.limpiar).pack(side=tk.LEFT,padx=4)
        make_button(btn_row,"🗑  Eliminar",self.eliminar_cliente).pack(side=tk.LEFT,padx=4)
        lst = ttk.LabelFrame(self, text="Clientes Registrados", padding=10)
        lst.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.tree = make_treeview(lst,('id','nombre','contacto','direccion','telefono','email'),('ID','Nombre','Contacto','Dirección','Teléfono','Email'),(45,160,120,150,100,160))
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

    def refresh_list(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.db.connect()
        self.db.execute("SELECT id,nombre,contacto,direccion,telefono,email FROM clientes ORDER BY nombre")
        for row in self.db.fetchall(): self.tree.insert('',tk.END,values=row)
        self.db.close()

    def _on_select(self,_):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel[0])['values']; self.selected_id = v[0]
        for attr,val in zip(['entry_nombre','entry_contacto','entry_direccion','entry_telefono','entry_email'],v[1:]):
            w=getattr(self,attr); w.delete(0,tk.END); w.insert(0,val or '')

    def limpiar(self):
        for a in ['entry_nombre','entry_contacto','entry_direccion','entry_telefono','entry_email']:
            getattr(self,a).delete(0,tk.END)
        self.selected_id = None

    def guardar_cliente(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre: messagebox.showerror("Campo requerido","El nombre del cliente es obligatorio."); return
        data=(nombre,self.entry_contacto.get().strip(),self.entry_direccion.get().strip(),self.entry_telefono.get().strip(),self.entry_email.get().strip())
        self.db.connect()
        if self.selected_id:
            self.db.execute('UPDATE clientes SET nombre=?,contacto=?,direccion=?,telefono=?,email=? WHERE id=?',data+(self.selected_id,))
        else:
            self.db.execute('INSERT INTO clientes(nombre,contacto,direccion,telefono,email) VALUES(?,?,?,?,?)',data)
        self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
        self.app.set_status("Cliente guardado correctamente")

    def eliminar_cliente(self):
        if not self.selected_id: messagebox.showwarning("Sin selección","Seleccione un cliente."); return
        if messagebox.askyesno("Confirmar eliminación","¿Eliminar este cliente?"):
            self.db.connect(); self.db.execute("DELETE FROM clientes WHERE id=?",(self.selected_id,))
            self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
            self.app.set_status("Cliente eliminado",ok=False)


# ──────────────────────── PÁGINA PROYECTOS ───────────────────────────────────
class ProyectosPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database()
        self.selected_id=None; self.clientes_list=[]; self._build(); self.refresh_list()

    def _build(self):
        self.configure(padding=12)
        form=ttk.LabelFrame(self,text="Datos del Proyecto",padding=14); form.pack(fill=tk.X,pady=(0,10))
        ttk.Label(form,text="Nombre *").grid(row=0,column=0,sticky=tk.W,pady=5)
        self.entry_nombre=ttk.Entry(form,width=50); self.entry_nombre.grid(row=0,column=1,pady=5,padx=8)
        ttk.Label(form,text="Cliente *").grid(row=1,column=0,sticky=tk.W,pady=5)
        self.combo_cliente=ttk.Combobox(form,state="readonly",width=47); self.combo_cliente.grid(row=1,column=1,pady=5,padx=8)
        self._cargar_clientes()
        ttk.Label(form,text="Responsable").grid(row=2,column=0,sticky=tk.W,pady=5)
        self.entry_resp=ttk.Entry(form,width=50); self.entry_resp.insert(0,"VEF Automatización"); self.entry_resp.grid(row=2,column=1,pady=5,padx=8)
        bf=ttk.Frame(form); bf.grid(row=3,column=0,columnspan=2,pady=12)
        make_button(bf,"💾  Guardar",self.guardar,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(bf,"➕  Nuevo",self.limpiar).pack(side=tk.LEFT,padx=4)
        make_button(bf,"🔒  Cerrar Proyecto",self.cerrar).pack(side=tk.LEFT,padx=4)
        make_button(bf,"🔄  Recargar Clientes",self._cargar_clientes).pack(side=tk.LEFT,padx=4)
        lst=ttk.LabelFrame(self,text="Proyectos",padding=10); lst.pack(fill=tk.BOTH,expand=True)
        self.tree=make_treeview(lst,('id','nombre','cliente','resp','fecha','estatus'),('ID','Nombre','Cliente','Responsable','Fecha','Estatus'),(50,180,160,130,100,90))
        self.tree.bind('<<TreeviewSelect>>',self._on_select)

    def _cargar_clientes(self):
        self.db.connect(); self.db.execute("SELECT id,nombre FROM clientes ORDER BY nombre")
        self.clientes_list=self.db.fetchall(); self.db.close()
        self.combo_cliente['values']=[f"{r[0]} – {r[1]}" for r in self.clientes_list]

    def refresh_list(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.db.connect()
        self.db.execute('SELECT p.id,p.nombre,c.nombre,p.responsable,p.fecha_creacion,p.estatus FROM proyectos p JOIN clientes c ON p.cliente_id=c.id ORDER BY p.id DESC')
        for row in self.db.fetchall():
            self.tree.insert('',tk.END,values=row,tags=('cerrado',) if row[5]=='cerrado' else ())
        self.tree.tag_configure('cerrado',foreground='#999999'); self.db.close()

    def _on_select(self,_):
        sel=self.tree.selection()
        if not sel: return
        v=self.tree.item(sel[0])['values']; self.selected_id=v[0]
        self.entry_nombre.delete(0,tk.END); self.entry_nombre.insert(0,v[1])
        for i,(cid,cnm) in enumerate(self.clientes_list):
            if cnm==v[2]: self.combo_cliente.current(i); break
        self.entry_resp.delete(0,tk.END); self.entry_resp.insert(0,v[3] or '')

    def limpiar(self):
        self.entry_nombre.delete(0,tk.END); self.combo_cliente.set('')
        self.entry_resp.delete(0,tk.END); self.entry_resp.insert(0,"VEF Automatización"); self.selected_id=None

    def guardar(self):
        nombre=self.entry_nombre.get().strip()
        if not nombre: messagebox.showerror("Campo requerido","El nombre del proyecto es obligatorio."); return
        cs=self.combo_cliente.get()
        if not cs: messagebox.showerror("Campo requerido","Seleccione un cliente."); return
        cid=int(cs.split(' – ')[0]); resp=self.entry_resp.get().strip() or "VEF Automatización"
        self.db.connect()
        if self.selected_id:
            self.db.execute('UPDATE proyectos SET nombre=?,cliente_id=?,responsable=? WHERE id=?',(nombre,cid,resp,self.selected_id))
        else:
            self.db.execute('INSERT INTO proyectos(nombre,cliente_id,responsable) VALUES(?,?,?)',(nombre,cid,resp))
        self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
        self.app.set_status("Proyecto guardado")

    def cerrar(self):
        if not self.selected_id: messagebox.showwarning("Sin selección","Seleccione un proyecto."); return
        if messagebox.askyesno("Confirmar","¿Marcar este proyecto como cerrado?"):
            self.db.connect(); self.db.execute("UPDATE proyectos SET estatus='cerrado' WHERE id=?",(self.selected_id,))
            self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
            self.app.set_status("Proyecto cerrado",ok=False)


# ──────────────────────── PÁGINA COTIZACIONES ────────────────────────────────
class CotizacionesPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database()
        self.selected_cotizacion_id=None; self._build(); self.refresh_list()

    def _build(self):
        self.configure(padding=12)
        lst=ttk.LabelFrame(self,text="Cotizaciones",padding=8); lst.pack(fill=tk.BOTH,expand=True)
        self.tree=make_treeview(lst,('id','numero','proyecto','cliente','fecha','total','moneda','estatus'),('ID','Número','Proyecto','Cliente','Fecha','Total','Moneda','Estatus'),(45,120,150,150,90,100,65,90),height=13)
        self.tree.bind('<<TreeviewSelect>>',self._on_select)
        bf=ttk.Frame(self); bf.pack(fill=tk.X,pady=8)
        for txt,cmd,prim in [("➕  Nueva",self.nueva_cotizacion,True),("✏️  Modificar",self.modificar_cotizacion,True),("🔍  Ver Detalle",self.ver_detalle,False),("🔄  Cambiar Estatus",self.cambiar_estatus,False),("📝  Seguimiento",self.agregar_seguimiento,False),("📄  Generar PDF",self.generar_pdf,True),("✉️  Enviar Correo",self.enviar_correo,False),("🗑  Eliminar",self.eliminar_cotizacion,False)]:
            make_button(bf,txt,cmd,primary=prim).pack(side=tk.LEFT,padx=4)
        res=ttk.LabelFrame(self,text="Resumen rápido",padding=8); res.pack(fill=tk.X)
        self.detalle_text=scrolledtext.ScrolledText(res,height=6,state='disabled',bg="#EEF4FC",fg=GRIS_TEXTO,font=('Helvetica',9),relief="flat",borderwidth=0)
        self.detalle_text.pack(fill=tk.X)

    def refresh_list(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.db.connect()
        self.db.execute('SELECT c.id,c.numero_cotizacion,p.nombre,cl.nombre,c.fecha_emision,c.total,COALESCE(c.moneda,"USD"),c.estatus FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id ORDER BY c.id DESC')
        palette={'aceptada':'#d4edda','rechazada':'#f8d7da','enviada':'#fff3cd','facturada':'#cce5ff','cerrada':'#e2e3e5','borrador':'#f8f9fa'}
        for row in self.db.fetchall():
            sym="$" if row[6]=="USD" else "MX$"
            self.tree.insert('',tk.END,values=(row[0],row[1],row[2],row[3],row[4],f"{sym}{row[5]:,.2f}" if row[5] else f"{sym}0.00",row[6],row[7]),tags=(row[7],))
        for tag,bg in palette.items(): self.tree.tag_configure(tag,background=bg)
        self.db.close()

    def _on_select(self,_):
        sel=self.tree.selection()
        if not sel: return
        v=self.tree.item(sel[0])['values']; self.selected_cotizacion_id=v[0]; self._mostrar_resumen(v[0])

    def _mostrar_resumen(self,cid):
        self.db.connect()
        self.db.execute('SELECT c.numero_cotizacion,p.nombre,cl.nombre,c.fecha_emision,c.total,c.estatus,c.alcance_tecnico FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id WHERE c.id=?',(cid,))
        r=self.db.fetchone(); self.db.close()
        if not r: return
        txt=f"Número:  {r[0]}    Proyecto: {r[1]}    Cliente: {r[2]}\nFecha:   {r[3]}    Total: ${r[4]:,.2f} USD    Estatus: {r[5].upper()}\n\nAlcance técnico:\n{(r[6] or 'No especificado')[:300]}"
        self.detalle_text.config(state='normal'); self.detalle_text.delete(1.0,tk.END)
        self.detalle_text.insert(1.0,txt); self.detalle_text.config(state='disabled')

    def nueva_cotizacion(self): NuevaCotizacionDialog(self)
    def ver_detalle(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        DetalleCotizacionDialog(self,self.selected_cotizacion_id)
    def cambiar_estatus(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        CambiarEstatusDialog(self,self.selected_cotizacion_id)
    def agregar_seguimiento(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        SeguimientoDialog(self,self.selected_cotizacion_id)

    def generar_pdf(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        self.db.connect(); self.db.execute("SELECT numero_cotizacion FROM cotizaciones WHERE id=?",(self.selected_cotizacion_id,))
        row=self.db.fetchone(); self.db.close()
        num=(row[0].replace('/','- ') if row else f"cot_{self.selected_cotizacion_id}")
        filename=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("Archivo PDF","*.pdf")],initialfile=f"Cotizacion_{num}.pdf",title="Guardar cotización como PDF")
        if not filename: return
        try:
            generar_pdf_cotizacion(self.selected_cotizacion_id,filename)
            messagebox.showinfo("PDF generado",f"El PDF se guardó en:\n{filename}")
            self.app.set_status(f"PDF generado: {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error al generar PDF",str(e)); self.app.set_status("Error al generar PDF",ok=False)

    def enviar_correo(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        cid=self.selected_cotizacion_id; tmp=os.path.join(tempfile.gettempdir(),f"cotizacion_{cid}.pdf")
        try: generar_pdf_cotizacion(cid,tmp)
        except Exception as e: messagebox.showerror("Error",f"No se pudo generar el PDF:\n{e}"); return
        num=self._get_numero(cid)
        self.db.connect(); self.db.execute('SELECT cl.email,cl.nombre,cl.contacto FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id WHERE c.id=?',(cid,))
        row=self.db.fetchone(); self.db.close()
        CorreoDialog(self,cid,tmp,num,row[0] if row else "",row[1] if row else "",row[2] if row else "")

    def modificar_cotizacion(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización para modificar."); return
        EditarCotizacionDialog(self,self.selected_cotizacion_id)

    def eliminar_cotizacion(self):
        if not self.selected_cotizacion_id: messagebox.showwarning("Sin selección","Seleccione una cotización."); return
        self.db.connect(); self.db.execute("SELECT numero_cotizacion FROM cotizaciones WHERE id=?",(self.selected_cotizacion_id,))
        r=self.db.fetchone(); self.db.close(); num=r[0] if r else str(self.selected_cotizacion_id)
        if not messagebox.askyesno("Confirmar eliminación",f"¿Eliminar la cotización {num}?\n\nTambién se eliminarán sus partidas y seguimientos.\nEsta acción NO puede deshacerse."): return
        self.db.connect()
        self.db.execute("DELETE FROM items_cotizacion WHERE cotizacion_id=?",(self.selected_cotizacion_id,))
        self.db.execute("DELETE FROM seguimientos WHERE cotizacion_id=?",(self.selected_cotizacion_id,))
        self.db.execute("DELETE FROM cotizaciones WHERE id=?",(self.selected_cotizacion_id,))
        self.db.commit(); self.db.close(); self.selected_cotizacion_id=None; self.refresh_list()
        self.app.set_status(f"Cotización {num} eliminada",ok=False)

    def _get_numero(self,cid):
        self.db.connect(); self.db.execute("SELECT numero_cotizacion FROM cotizaciones WHERE id=?",(cid,))
        r=self.db.fetchone(); self.db.close(); return r[0] if r else str(cid)


# ──────────────────────── DIÁLOGO CORREO ─────────────────────────────────────
class CorreoDialog(tk.Toplevel):
    def __init__(self,parent,cid,pdf_path,numero,email_cliente="",nombre_cliente="",contacto_cliente=""):
        super().__init__(parent); self.pdf_path=pdf_path
        self.title("Enviar Cotización — Zoho Mail"); self.geometry("560x600")
        self.configure(bg=GRIS_CLARO); self.resizable(True,True); self.minsize(520,560)
        self._build(numero,email_cliente,nombre_cliente,contacto_cliente)

    def _build(self,numero,email_cliente,nombre_cliente,contacto_cliente):
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(side=tk.TOP,fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr,text="  ✉  Enviar por Zoho Mail",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',11,'bold')).pack(side=tk.LEFT,pady=10)
        outer=tk.Frame(self,bg=GRIS_CLARO); outer.pack(fill=tk.BOTH,expand=True)
        cv=tk.Canvas(outer,bg=GRIS_CLARO,highlightthickness=0); vsb=ttk.Scrollbar(outer,orient="vertical",command=cv.yview)
        cv.configure(yscrollcommand=vsb.set); vsb.pack(side=tk.RIGHT,fill=tk.Y); cv.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        frame=ttk.Frame(cv,padding=16); fid=cv.create_window((0,0),window=frame,anchor="nw")
        frame.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(fid,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        row=0
        if nombre_cliente:
            ttk.Label(frame,text=f"Cliente: {nombre_cliente}"+(f"  |  Contacto: {contacto_cliente}" if contacto_cliente else ""),foreground=AZUL_MEDIO,font=('Helvetica',9,'italic')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(0,8))
        row+=1
        ttk.Label(frame,text="─── Cuenta Zoho Mail (remitente) ───",foreground=AZUL_OSCURO,font=('Helvetica',9,'bold')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(4,6)); row+=1
        REMITENTE_FIJO="soporte.ventas@vef-automatizacion.com"; PASSWORD_FIJO="Brabata2323!"
        for lbl,attr,default,es_pass in [("Correo remitente:","entry_from",REMITENTE_FIJO,False),("Contraseña:","entry_pass",PASSWORD_FIJO,True)]:
            ttk.Label(frame,text=lbl).grid(row=row,column=0,sticky=tk.W,pady=5)
            e=ttk.Entry(frame,width=40,show='*' if es_pass else ''); e.insert(0,default); e.config(state='readonly')
            e.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); setattr(self,attr,e); row+=1
        ttk.Label(frame,text="✔ Cuenta configurada: VEF Automatización",foreground=VERDE_OK,font=('Helvetica',8)).grid(row=row,column=1,sticky=tk.W,padx=8); row+=1
        ttk.Label(frame,text="Servidor SMTP:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.combo_smtp=ttk.Combobox(frame,state="readonly",width=37,values=["smtp.zoho.com  (puerto 587 – TLS)","smtp.zoho.com  (puerto 465 – SSL)","smtp.zoho.eu   (puerto 587 – TLS)","smtp.zoho.eu   (puerto 465 – SSL)"])
        self.combo_smtp.current(0); self.combo_smtp.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="─── Destinatario ───",foreground=AZUL_OSCURO,font=('Helvetica',9,'bold')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(10,6)); row+=1
        ttk.Label(frame,text="Para *:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_to=ttk.Entry(frame,width=40); self.entry_to.insert(0,email_cliente or "")
        self.entry_to.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="✔ Email obtenido del registro del cliente" if email_cliente else "⚠ Este cliente no tiene email registrado",foreground=VERDE_OK if email_cliente else NARANJA_WARN,font=('Helvetica',8)).grid(row=row,column=1,sticky=tk.W,padx=8); row+=1
        ttk.Label(frame,text="CC (opcional):").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_cc=ttk.Entry(frame,width=40); self.entry_cc.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="Asunto *:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_asunto=ttk.Entry(frame,width=40); self.entry_asunto.insert(0,f"Cotización {numero}")
        self.entry_asunto.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="Mensaje:").grid(row=row,column=0,sticky=tk.NW,pady=5)
        self.text_msg=scrolledtext.ScrolledText(frame,height=6,width=38,font=('Helvetica',9))
        contacto_str=contacto_cliente or "estimado/a cliente"
        self.text_msg.insert('1.0',f"Estimado/a {contacto_str},\n\nAdjunto a este correo encontrará la cotización {numero} elaborada especialmente para su proyecto.\n\nQuedamos a sus órdenes para cualquier consulta.\n\nAtentamente,\n{VEF_NOMBRE}\nTel: {VEF_TELEFONO}\nCorreo: {VEF_CORREO}")
        self.text_msg.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Separator(frame,orient='horizontal').grid(row=row,column=0,columnspan=2,sticky=tk.EW,pady=10); row+=1
        bf=ttk.Frame(frame); bf.grid(row=row,column=0,columnspan=2,pady=(4,16))
        tk.Button(bf,text="  ✉   ENVIAR COTIZACIÓN   ",command=self._enviar,bg=AZUL_MEDIO,fg=BLANCO,font=('Helvetica',11,'bold'),relief="flat",cursor="hand2",activebackground=AZUL_CLARO,activeforeground=BLANCO,padx=18,pady=10).pack(side=tk.LEFT,padx=8)
        tk.Button(bf,text="✖  Cancelar",command=self.destroy,bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',9),relief="flat",cursor="hand2",activebackground="#E0E0E0",padx=10,pady=10).pack(side=tk.LEFT,padx=4)

    def _enviar(self):
        self.entry_from.config(state='normal'); self.entry_pass.config(state='normal')
        remitente=self.entry_from.get().strip(); password=self.entry_pass.get().strip()
        self.entry_from.config(state='readonly'); self.entry_pass.config(state='readonly')
        dest=self.entry_to.get().strip(); cc=self.entry_cc.get().strip()
        asunto=self.entry_asunto.get().strip(); mensaje=self.text_msg.get('1.0',tk.END).strip()
        smtp_sel=self.combo_smtp.get()
        if not all([remitente,password,dest,asunto]): messagebox.showerror("Campos incompletos","Todos los campos marcados * son obligatorios."); return
        use_ssl="465" in smtp_sel; smtp_host=smtp_sel.split()[0]; smtp_port=465 if use_ssl else 587
        try:
            msg=MIMEMultipart(); msg['From']=remitente; msg['To']=dest; msg['Subject']=asunto
            if cc: msg['Cc']=cc
            msg.attach(MIMEText(mensaje,'plain','utf-8'))
            with open(self.pdf_path,"rb") as f:
                part=MIMEBase('application','octet-stream'); part.set_payload(f.read())
                encoders.encode_base64(part); part.add_header('Content-Disposition',f'attachment; filename="{os.path.basename(self.pdf_path)}"')
                msg.attach(part)
            recipients=[dest]+([cc] if cc else [])
            if use_ssl:
                import ssl; ctx=ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host,smtp_port,context=ctx) as server:
                    server.login(remitente,password); server.sendmail(remitente,recipients,msg.as_bytes())
            else:
                with smtplib.SMTP(smtp_host,smtp_port) as server:
                    server.ehlo(); server.starttls(); server.ehlo(); server.login(remitente,password)
                    server.sendmail(remitente,recipients,msg.as_bytes())
            messagebox.showinfo("✔ Correo enviado",f"Correo enviado correctamente a:\n{dest}"+(f"\nCC: {cc}" if cc else ""))
            self.destroy()
        except smtplib.SMTPAuthenticationError:
            messagebox.showerror("Error de autenticación","Usuario o contraseña incorrectos.")
        except Exception as e:
            messagebox.showerror("Error inesperado",str(e))


# ─── Diálogos cotización (NuevaCotizacionDialog, ItemDialog, etc.) ───────────
# Se mantienen idénticos al código original — incluidos a continuación:

class NuevaCotizacionDialog(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent); self.parent=parent; self.title("Nueva Cotización")
        self.geometry("860x720"); self.configure(bg=GRIS_CLARO)
        self.db=Database(); self.items=[]; self.proyectos=self._load_proyectos(); self._build()

    def _load_proyectos(self):
        self.db.connect(); self.db.execute('SELECT p.id,p.nombre,c.nombre FROM proyectos p JOIN clientes c ON p.cliente_id=c.id WHERE p.estatus="activo" ORDER BY p.nombre')
        r=self.db.fetchall(); self.db.close(); return r

    def _build(self):
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(fill=tk.X)
        tk.Label(hdr,text="  Nueva Cotización",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',12,'bold')).pack(side=tk.LEFT,pady=10)
        canvas=tk.Canvas(self,bg=GRIS_CLARO,highlightthickness=0); sb=ttk.Scrollbar(self,orient="vertical",command=canvas.yview)
        self.scroll_frame=ttk.Frame(canvas)
        self.scroll_frame.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=self.scroll_frame,anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True); sb.pack(side=tk.RIGHT,fill=tk.Y)
        f=self.scroll_frame; pad=dict(pady=5,padx=8)
        ttk.Label(f,text="Proyecto *").grid(row=0,column=0,sticky=tk.W,**pad)
        self.combo_proyecto=ttk.Combobox(f,state="readonly",width=55)
        self.combo_proyecto['values']=[f"{p[0]} – {p[1]}  (Cliente: {p[2]})" for p in self.proyectos]
        self.combo_proyecto.grid(row=0,column=1,**pad)
        ttk.Label(f,text="Moneda *").grid(row=1,column=0,sticky=tk.W,**pad)
        mf=ttk.Frame(f); mf.grid(row=1,column=1,sticky=tk.W,**pad)
        self.moneda_var=tk.StringVar(value="USD")
        tk.Radiobutton(mf,text="USD  (Dólares)",variable=self.moneda_var,value="USD",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT,padx=(0,20))
        tk.Radiobutton(mf,text="MXN  (Pesos MXN)",variable=self.moneda_var,value="MXN",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT)
        DEFAULTS={"text_comentarios":"• La propuesta se basa en la información proporcionada por el cliente.\n• Cualquier modificación solicitada deberá notificarse por escrito.\n• El servicio debe prestarse en instalaciones seguras.","text_postventa":"Servicios adicionales como mantenimiento, modernización, reubicación, repuestos o reparaciones pueden solicitarse bajo contrato independiente.","text_entrega":"• Entrega: [Plazo estimado] días hábiles tras recibir pedido confirmado.\n• Pago:\n   • 50% anticipo tras confirmación de pedido.\n   • 50% contra entrega.\n   • Plazo máximo: 30 días después de facturación.","text_garantia":"• Periodo de garantía: 12 meses a partir de la instalación.\n• Incluye reparación o reemplazo en caso de defectos.\n• Responsabilidad máxima: hasta el valor del contrato.","text_validez":"La presente cotización es válida por 1 mes a partir de la fecha de emisión.","text_fuerza":"Cualquiera de las partes podrá suspender obligaciones en caso de circunstancias fuera de su control.","text_ley":"Se aplicarán las leyes de los Estados Unidos Mexicanos."}
        all_fields=[("Alcance Técnico *","text_alcance",5),("Notas Importantes","text_notas",3),("Comentarios Generales","text_comentarios",4),("Servicio Postventa","text_postventa",3),("Condic. Entrega y Pago","text_entrega",4),("Garantía","text_garantia",5),("Validez","text_validez",2),("Fuerza Mayor","text_fuerza",3),("Ley Aplicable","text_ley",2)]
        for i,(lbl,attr,h) in enumerate(all_fields,2):
            ttk.Label(f,text=lbl).grid(row=i,column=0,sticky=tk.NW,**pad)
            w=scrolledtext.ScrolledText(f,width=65,height=h,font=('Helvetica',9))
            if attr in DEFAULTS: w.insert('1.0',DEFAULTS[attr])
            w.grid(row=i,column=1,**pad); setattr(self,attr,w)
        base_row=len(all_fields)+2
        items_lf=ttk.LabelFrame(f,text="Partidas / Items de la Cotización",padding=8)
        items_lf.grid(row=base_row,column=0,columnspan=2,sticky=tk.EW,**pad)
        self.tree_items=make_treeview(items_lf,('desc','cant','pu','total'),('Descripción','Cantidad','P. Unitario','Total'),(340,70,120,120),height=5)
        ibf=ttk.Frame(f); ibf.grid(row=base_row+1,column=0,columnspan=2,pady=4)
        make_button(ibf,"➕ Agregar Partida",self.agregar_item,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(ibf,"🗑 Eliminar Partida",self.eliminar_item).pack(side=tk.LEFT,padx=4)
        self.lbl_total=ttk.Label(f,text="Total:  $0.00 USD",font=('Helvetica',13,'bold'),foreground=AZUL_OSCURO)
        self.lbl_total.grid(row=base_row+2,column=0,columnspan=2,pady=10)
        bf=ttk.Frame(f); bf.grid(row=base_row+3,column=0,columnspan=2,pady=12)
        make_button(bf,"💾  Guardar Cotización",self.guardar,primary=True).pack(side=tk.LEFT,padx=6)
        make_button(bf,"✖  Cancelar",self.destroy).pack(side=tk.LEFT,padx=6)

    def agregar_item(self): ItemDialog(self)
    def eliminar_item(self):
        sel=self.tree_items.selection()
        if not sel: return
        v=self.tree_items.item(sel[0])['values']
        for it in self.items:
            if str(it[0])==str(v[0]) and str(it[1])==str(v[1]): self.items.remove(it); break
        self.tree_items.delete(sel[0]); self._recalc()

    def adicionar_item(self,desc,cant,pu,total):
        moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.items.append((desc,cant,pu,total))
        self.tree_items.insert('',tk.END,values=(desc,cant,f"{sym}{pu:,.2f}",f"{sym}{total:,.2f}")); self._recalc()

    def _recalc(self):
        total=sum(i[3] for i in self.items); moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.lbl_total.config(text=f"Total:  {sym}{total:,.2f} {moneda}")
        for rid in self.tree_items.get_children():
            v=self.tree_items.item(rid)['values']
            try:
                pu_v=float(str(v[2]).replace('MX$','').replace('$','').replace(',','')); tot_v=float(str(v[3]).replace('MX$','').replace('$','').replace(',',''))
                self.tree_items.item(rid,values=(v[0],v[1],f"{sym}{pu_v:,.2f}",f"{sym}{tot_v:,.2f}"))
            except: pass

    def guardar(self):
        ps=self.combo_proyecto.get()
        if not ps: messagebox.showerror("Campo requerido","Seleccione un proyecto."); return
        pid=int(ps.split(' – ')[0]); alcance=self.text_alcance.get('1.0',tk.END).strip()
        if not alcance: messagebox.showerror("Campo requerido","El alcance técnico es obligatorio."); return
        moneda=self.moneda_var.get(); hoy=datetime.date.today(); fecha_str=hoy.strftime("%Y%m%d")
        self.db.connect(); self.db.execute("SELECT COUNT(*) FROM cotizaciones WHERE numero_cotizacion LIKE ?",(f"%{fecha_str}%",))
        count=self.db.fetchone()[0]+1; numero=f"COT-{fecha_str}-{count:03d}"; validez=(hoy+datetime.timedelta(days=30)).isoformat()
        def txt(attr): return getattr(self,attr).get('1.0',tk.END).strip()
        self.db.execute('INSERT INTO cotizaciones (proyecto_id,numero_cotizacion,validez_hasta,alcance_tecnico,notas_importantes,comentarios_generales,servicio_postventa,condiciones_entrega,condiciones_pago,garantia,responsabilidad,validez,fuerza_mayor,ley_aplicable,total,moneda,estatus) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (pid,numero,validez,alcance,txt('text_notas'),txt('text_comentarios'),txt('text_postventa'),txt('text_entrega'),"",txt('text_garantia'),"",txt('text_validez'),txt('text_fuerza'),txt('text_ley'),sum(i[3] for i in self.items),moneda,'borrador'))
        cid=self.db.lastrowid()
        for it in self.items:
            self.db.execute('INSERT INTO items_cotizacion (cotizacion_id,descripcion,cantidad,precio_unitario,total) VALUES (?,?,?,?,?)',(cid,it[0],it[1],it[2],it[3]))
        self.db.commit(); self.db.close()
        messagebox.showinfo("Cotización creada",f"Cotización {numero} guardada en {moneda} (ID {cid}).")
        self.parent.refresh_list(); self.destroy()


class ItemDialog(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent); self.parent=parent; self.title("Agregar Partida")
        self.geometry("520x220"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        hdr=tk.Frame(self,bg=AZUL_MEDIO,height=36); hdr.pack(fill=tk.X)
        tk.Label(hdr,text="  Agregar Partida / Item",bg=AZUL_MEDIO,fg=BLANCO,font=('Helvetica',10,'bold')).pack(side=tk.LEFT,pady=8)
        f=ttk.Frame(self,padding=14); f.pack(fill=tk.BOTH,expand=True)
        ttk.Label(f,text="Descripción *").grid(row=0,column=0,sticky=tk.W,pady=6)
        self.entry_desc=ttk.Entry(f,width=48); self.entry_desc.grid(row=0,column=1,pady=6,padx=8)
        ttk.Label(f,text="Cantidad *").grid(row=1,column=0,sticky=tk.W,pady=6)
        self.entry_cant=ttk.Entry(f,width=20); self.entry_cant.grid(row=1,column=1,sticky=tk.W,pady=6,padx=8)
        ttk.Label(f,text="Precio Unitario *").grid(row=2,column=0,sticky=tk.W,pady=6)
        self.entry_pu=ttk.Entry(f,width=20); self.entry_pu.grid(row=2,column=1,sticky=tk.W,pady=6,padx=8)
        bf=ttk.Frame(f); bf.grid(row=3,column=0,columnspan=2,pady=12)
        make_button(bf,"✔  Aceptar",self._aceptar,primary=True).pack(side=tk.LEFT,padx=6)
        make_button(bf,"✖  Cancelar",self.destroy).pack(side=tk.LEFT,padx=6)

    def _aceptar(self):
        desc=self.entry_desc.get().strip()
        if not desc: messagebox.showerror("Requerido","La descripción es obligatoria."); return
        try:
            cant=int(self.entry_cant.get().strip()); pu=float(self.entry_pu.get().strip())
            if cant<=0 or pu<=0: raise ValueError
        except ValueError: messagebox.showerror("Valor inválido","Cantidad y precio deben ser números positivos."); return
        self.parent.adicionar_item(desc,cant,pu,cant*pu); self.destroy()


class DetalleCotizacionDialog(tk.Toplevel):
    def __init__(self,parent,cid):
        super().__init__(parent); self.title("Detalle de Cotización"); self.geometry("860x620"); self.configure(bg=GRIS_CLARO)
        db=Database(); db.connect()
        db.execute('SELECT c.*,p.nombre,cl.nombre,cl.contacto,cl.direccion FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id WHERE c.id=?',(cid,))
        row=db.fetchone()
        if not row: self.destroy(); return
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(fill=tk.X)
        tk.Label(hdr,text=f"  Cotización: {row[2]}",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',12,'bold')).pack(side=tk.LEFT,pady=10)
        txt=scrolledtext.ScrolledText(self,wrap=tk.WORD,font=('Courier',9),bg="#EEF4FC",relief="flat")
        txt.pack(fill=tk.BOTH,expand=True,padx=12,pady=10)
        content=f"\n{'─'*80}\n  COTIZACIÓN No. {row[2]}\n  Fecha: {row[3]}   ·   Válida hasta: {row[4] or 'N/A'}\n  Proyecto: {row[19]}   ·   Cliente: {row[20]}\n{'─'*80}\n\nALCANCE TÉCNICO:\n{row[5] or '—'}\n\nNOTAS IMPORTANTES:\n{row[6] or '—'}\n\nTOTAL   : ${row[17]:,.2f} USD\nESTATUS : {row[18].upper()}\n{'─'*80}\n"
        db.execute("SELECT descripcion,cantidad,precio_unitario,total FROM items_cotizacion WHERE cotizacion_id=?",(cid,))
        items=db.fetchall(); db.close()
        if items:
            content+=f"\n{'Descripción':<44} {'Cant':>5}  {'P.Unit':>12}  {'Total':>12}\n"+"─"*80+"\n"
            for it in items: content+=f"{str(it[0])[:43]:<44} {it[1]:>5}  ${it[2]:>11,.2f}  ${it[3]:>11,.2f}\n"
        txt.insert(tk.END,content); txt.config(state='disabled')


class CambiarEstatusDialog(tk.Toplevel):
    def __init__(self,parent,cid):
        super().__init__(parent); self.parent=parent; self.cid=cid; self.title("Cambiar Estatus")
        self.geometry("320x180"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        ttk.Label(self,text="Seleccione el nuevo estatus:",font=('Helvetica',10)).pack(pady=(20,8))
        self.combo=ttk.Combobox(self,state='readonly',width=30,values=['borrador','enviada','aceptada','rechazada','facturada','cerrada'])
        self.combo.pack(pady=6); make_button(self,"✔  Actualizar",self._actualizar,primary=True).pack(pady=14)

    def _actualizar(self):
        val=self.combo.get()
        if not val: return
        db=Database(); db.connect(); db.execute("UPDATE cotizaciones SET estatus=? WHERE id=?",(val,self.cid))
        db.commit(); db.close(); messagebox.showinfo("Actualizado",f"Estatus cambiado a '{val}'."); self.parent.refresh_list(); self.destroy()


class SeguimientoDialog(tk.Toplevel):
    def __init__(self,parent,cid):
        super().__init__(parent); self.cid=cid; self.title("Registro de Seguimiento")
        self.geometry("440x320"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        ttk.Label(self,text="Tipo de contacto:").pack(pady=(18,4))
        self.combo=ttk.Combobox(self,state='readonly',width=30,values=['llamada','correo','reunión','whatsapp']); self.combo.pack(pady=4)
        ttk.Label(self,text="Notas:").pack(pady=(10,4))
        self.text_notas=scrolledtext.ScrolledText(self,height=5,font=('Helvetica',9)); self.text_notas.pack(padx=14,fill=tk.X)
        ttk.Label(self,text="Próxima acción:").pack(pady=(10,4))
        self.entry_prox=ttk.Entry(self,width=44); self.entry_prox.pack(pady=4)
        make_button(self,"💾  Guardar",self._guardar,primary=True).pack(pady=14)

    def _guardar(self):
        tipo=self.combo.get()
        if not tipo: messagebox.showerror("Requerido","Seleccione el tipo."); return
        db=Database(); db.connect(); db.execute("INSERT INTO seguimientos(cotizacion_id,tipo,notas,proxima_accion) VALUES(?,?,?,?)",(self.cid,tipo,self.text_notas.get('1.0',tk.END).strip(),self.entry_prox.get().strip()))
        db.commit(); db.close(); messagebox.showinfo("Guardado","Seguimiento registrado correctamente."); self.destroy()


# ──────────────────────── PÁGINA ÓRDENES Y FACTURAS ──────────────────────────
class OrdenesFacturasPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database()
        self._build(); self.refresh_oc(); self.refresh_facturas()

    def _build(self):
        self.configure(padding=10); nb=ttk.Notebook(self); nb.pack(fill=tk.BOTH,expand=True)

        # ── Pestaña OC ────────────────────────────────────────────────────────
        self.oc_frame=ttk.Frame(nb,padding=8); nb.add(self.oc_frame,text="📦  Órdenes de Compra")
        self.tree_oc=make_treeview(self.oc_frame,
            ('id','num_oc','cotizacion','fecha','arch_oc','arch_fact'),
            ('ID','Número OC','Cotización','Fecha','PDF Orden de Compra','PDF Factura'),
            (45,120,180,90,180,180))
        bf=ttk.Frame(self.oc_frame); bf.pack(fill=tk.X,pady=6)
        make_button(bf,"➕  Registrar OC",self.registrar_oc,primary=True).pack(side=tk.LEFT,padx=4)

        # Separador visual
        ttk.Separator(bf,orient='vertical').pack(side=tk.LEFT,fill='y',padx=8,pady=2)

        # Botón Adjuntar OC PDF
        tk.Button(bf,text="📎  Adjuntar OC (PDF)",command=self.adjuntar_oc_pdf,
                  bg="#2980B9",fg=BLANCO,font=('Helvetica',9,'bold'),
                  relief="flat",cursor="hand2",padx=10,pady=4).pack(side=tk.LEFT,padx=3)
        tk.Button(bf,text="📂  Ver OC",command=self.abrir_oc_pdf,
                  bg=AZUL_SUAVE,fg=AZUL_OSCURO,font=('Helvetica',9),
                  relief="flat",cursor="hand2",padx=8,pady=4).pack(side=tk.LEFT,padx=2)

        ttk.Separator(bf,orient='vertical').pack(side=tk.LEFT,fill='y',padx=8,pady=2)

        # Botón Adjuntar Factura PDF (desde OC)
        tk.Button(bf,text="🧾  Adjuntar Factura (PDF)",command=self.adjuntar_factura_desde_oc,
                  bg="#27AE60",fg=BLANCO,font=('Helvetica',9,'bold'),
                  relief="flat",cursor="hand2",padx=10,pady=4).pack(side=tk.LEFT,padx=3)
        tk.Button(bf,text="📂  Ver Factura",command=self.abrir_factura_desde_oc,
                  bg=AZUL_SUAVE,fg=AZUL_OSCURO,font=('Helvetica',9),
                  relief="flat",cursor="hand2",padx=8,pady=4).pack(side=tk.LEFT,padx=2)

        # Leyenda
        tk.Label(bf,text="  ← Selecciona una fila y luego adjunta el PDF",
                 font=('Helvetica',8,'italic'),fg="#888").pack(side=tk.LEFT,padx=6)

        # ── Pestaña Facturas ──────────────────────────────────────────────────
        self.fact_frame=ttk.Frame(nb,padding=8); nb.add(self.fact_frame,text="🧾  Facturas")
        self.tree_fact=make_treeview(self.fact_frame,
            ('id','num_fact','cotizacion','monto','estatus','archivo'),
            ('ID','Número Factura','Cotización','Monto','Estatus Pago','Archivo PDF'),
            (50,130,170,110,90,200))
        bf2=ttk.Frame(self.fact_frame); bf2.pack(fill=tk.X,pady=6)
        make_button(bf2,"➕  Registrar Factura",self.registrar_factura,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(bf2,"💳  Registrar Pago",self.registrar_pago).pack(side=tk.LEFT,padx=4)

        ttk.Separator(bf2,orient='vertical').pack(side=tk.LEFT,fill='y',padx=8,pady=2)

        tk.Button(bf2,text="📎  Adjuntar Factura PDF",command=self.adjuntar_factura,
                  bg="#27AE60",fg=BLANCO,font=('Helvetica',9,'bold'),
                  relief="flat",cursor="hand2",padx=10,pady=4).pack(side=tk.LEFT,padx=3)
        tk.Button(bf2,text="📂  Abrir PDF",command=self.abrir_factura,
                  bg=AZUL_SUAVE,fg=AZUL_OSCURO,font=('Helvetica',9),
                  relief="flat",cursor="hand2",padx=8,pady=4).pack(side=tk.LEFT,padx=2)

    # ── Refresh ───────────────────────────────────────────────────────────────
    def refresh_oc(self):
        for r in self.tree_oc.get_children(): self.tree_oc.delete(r)
        self.db.connect()
        self.db.execute('''
            SELECT oc.id, oc.numero_oc, c.numero_cotizacion, oc.fecha,
                   COALESCE(oc.archivo_oc,""), COALESCE(oc.archivo_factura,"")
            FROM ordenes_compra oc
            JOIN cotizaciones c ON oc.cotizacion_id=c.id
            ORDER BY oc.id DESC
        ''')
        for row in self.db.fetchall():
            arch_oc   = ("✅ " + os.path.basename(row[4])) if row[4] else "— sin adjunto —"
            arch_fact = ("✅ " + os.path.basename(row[5])) if row[5] else "— sin adjunto —"
            self.tree_oc.insert('',tk.END,values=(row[0],row[1],row[2],row[3],arch_oc,arch_fact))
        self.db.close()

    def refresh_facturas(self):
        for r in self.tree_fact.get_children(): self.tree_fact.delete(r)
        self.db.connect()
        self.db.execute('''
            SELECT f.id,f.numero_factura,c.numero_cotizacion,f.monto,f.estatus_pago,
                   COALESCE(f.archivo,""),COALESCE(c.moneda,"USD")
            FROM facturas f JOIN cotizaciones c ON f.cotizacion_id=c.id
            ORDER BY f.id DESC
        ''')
        for row in self.db.fetchall():
            sym  = "$" if row[6]=="USD" else "MX$"
            arch = ("✅ " + os.path.basename(row[5])) if row[5] else "— sin adjunto —"
            self.tree_fact.insert('',tk.END,
                values=(row[0],row[1],row[2],
                        f"{sym}{row[3]:,.2f}" if row[3] else f"{sym}0.00",
                        row[4], arch),
                tags=(row[4],))
        self.tree_fact.tag_configure('pagada',background='#d4edda')
        self.tree_fact.tag_configure('pendiente',background='#fff3cd')
        self.db.close()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _simple_dialog(self,title,fields,callback):
        dlg=tk.Toplevel(self); dlg.title(title); dlg.configure(bg=GRIS_CLARO)
        dlg.geometry("420x"+str(100+len(fields)*55)); dlg.resizable(False,False)
        entries={}
        for i,(lbl,key,default) in enumerate(fields):
            ttk.Label(dlg,text=lbl).pack(pady=(10 if i==0 else 4,2))
            e=ttk.Entry(dlg,width=44); e.insert(0,default); e.pack(); entries[key]=e
        make_button(dlg,"💾  Guardar",lambda: callback(entries,dlg),primary=True).pack(pady=14)

    def _get_selected_oc_id(self):
        sel=self.tree_oc.selection(); return self.tree_oc.item(sel[0])['values'][0] if sel else None
    def _get_selected_fact_id(self):
        sel=self.tree_fact.selection(); return self.tree_fact.item(sel[0])['values'][0] if sel else None

    def _abrir_archivo(self, path):
        if not os.path.isfile(path):
            messagebox.showerror("No encontrado", f"Archivo no encontrado:\n{path}"); return
        if os.name == 'nt':
            os.startfile(path)
        else:
            os.system(f'xdg-open "{path}"')

    # ── Adjuntar OC PDF ───────────────────────────────────────────────────────
    def adjuntar_oc_pdf(self):
        oid = self._get_selected_oc_id()
        if not oid: messagebox.showwarning("Sin selección","Selecciona una Orden de Compra primero."); return
        path = filedialog.askopenfilename(
            title="Adjuntar PDF de la Orden de Compra",
            filetypes=[("PDF","*.pdf"),("Todos","*.*")])
        if not path: return
        db=Database(); db.connect()
        db.execute("UPDATE ordenes_compra SET archivo_oc=? WHERE id=?",(path,oid))
        db.commit(); db.close()
        self.refresh_oc()
        self.app.set_status(f"OC PDF adjunto: {os.path.basename(path)} ✅")

    def abrir_oc_pdf(self):
        oid = self._get_selected_oc_id()
        if not oid: messagebox.showwarning("Sin selección","Selecciona una OC."); return
        db=Database(); db.connect()
        db.execute("SELECT archivo_oc FROM ordenes_compra WHERE id=?",(oid,))
        r=db.fetchone(); db.close()
        if not r or not r[0]: messagebox.showinfo("Sin archivo","Esta OC no tiene PDF de orden adjunto."); return
        self._abrir_archivo(r[0])

    # ── Adjuntar Factura PDF desde pestaña OC ─────────────────────────────────
    def adjuntar_factura_desde_oc(self):
        oid = self._get_selected_oc_id()
        if not oid: messagebox.showwarning("Sin selección","Selecciona una Orden de Compra primero."); return
        path = filedialog.askopenfilename(
            title="Adjuntar PDF de Factura a esta OC",
            filetypes=[("PDF","*.pdf"),("Todos","*.*"),("XML","*.xml")])
        if not path: return
        db=Database(); db.connect()
        db.execute("UPDATE ordenes_compra SET archivo_factura=? WHERE id=?",(path,oid))
        db.commit(); db.close()
        self.refresh_oc()
        self.app.set_status(f"Factura PDF adjunta a OC: {os.path.basename(path)} ✅")

    def abrir_factura_desde_oc(self):
        oid = self._get_selected_oc_id()
        if not oid: messagebox.showwarning("Sin selección","Selecciona una OC."); return
        db=Database(); db.connect()
        db.execute("SELECT archivo_factura FROM ordenes_compra WHERE id=?",(oid,))
        r=db.fetchone(); db.close()
        if not r or not r[0]: messagebox.showinfo("Sin archivo","Esta OC no tiene PDF de factura adjunto."); return
        self._abrir_archivo(r[0])

    # ── Adjuntar Factura PDF (pestaña Facturas) ───────────────────────────────
    def adjuntar_factura(self):
        fid = self._get_selected_fact_id()
        if not fid: messagebox.showwarning("Sin selección","Selecciona una factura primero."); return
        path = filedialog.askopenfilename(
            title="Adjuntar PDF de Factura",
            filetypes=[("PDF","*.pdf"),("XML","*.xml"),("Todos","*.*")])
        if not path: return
        db=Database(); db.connect()
        db.execute("UPDATE facturas SET archivo=? WHERE id=?",(path,fid))
        db.commit(); db.close()
        self.refresh_facturas()
        self.app.set_status(f"Factura PDF adjunta: {os.path.basename(path)} ✅")

    def abrir_factura(self):
        fid = self._get_selected_fact_id()
        if not fid: messagebox.showwarning("Sin selección","Selecciona una factura."); return
        db=Database(); db.connect()
        db.execute("SELECT archivo FROM facturas WHERE id=?",(fid,))
        r=db.fetchone(); db.close()
        if not r or not r[0]: messagebox.showinfo("Sin archivo","Esta factura no tiene PDF adjunto."); return
        self._abrir_archivo(r[0])

    # ── Adjuntar OC genérico (retrocompatibilidad) ────────────────────────────
    def adjuntar_oc(self):
        self.adjuntar_oc_pdf()

    def abrir_oc(self):
        self.abrir_oc_pdf()

    # ── Registrar OC / Factura / Pago ─────────────────────────────────────────
    def registrar_oc(self):
        def save(entries,dlg):
            cot_id_s=entries['cot_id'].get().strip(); num_oc=entries['num_oc'].get().strip()
            if not cot_id_s or not num_oc: messagebox.showerror("Requerido","Complete todos los campos."); return
            try: cot_id=int(cot_id_s)
            except: messagebox.showerror("Error","ID debe ser número."); return
            db=Database(); db.connect(); db.execute("SELECT id FROM cotizaciones WHERE id=?",(cot_id,))
            if not db.fetchone(): messagebox.showerror("No encontrada","Cotización no encontrada."); db.close(); return
            try: db.execute("INSERT INTO ordenes_compra(cotizacion_id,numero_oc) VALUES(?,?)",(cot_id,num_oc)); db.commit()
            except sqlite3.IntegrityError: messagebox.showerror("Duplicado","Ya existe una OC para esta cotización."); db.close(); return
            db.close(); messagebox.showinfo("Guardado","Orden de compra registrada."); self.refresh_oc(); dlg.destroy()
        self._simple_dialog("Registrar OC",[("ID de Cotización:","cot_id",""),("Número de OC:","num_oc","")],save)

    def registrar_factura(self):
        def save(entries,dlg):
            cot_id_s=entries['cot_id'].get().strip(); num_fact=entries['num_fact'].get().strip()
            if not cot_id_s or not num_fact: messagebox.showerror("Requerido","Complete los campos obligatorios."); return
            try: cot_id=int(cot_id_s)
            except: messagebox.showerror("Error","ID debe ser número."); return
            monto_s=entries['monto'].get().strip(); db=Database(); db.connect()
            if monto_s:
                try: monto=float(monto_s)
                except: messagebox.showerror("Error","Monto inválido."); db.close(); return
            else:
                db.execute("SELECT total FROM cotizaciones WHERE id=?",(cot_id,)); r=db.fetchone()
                if not r: messagebox.showerror("No encontrada","Cotización no existe."); db.close(); return
                monto=r[0]
            db.execute("INSERT INTO facturas(cotizacion_id,numero_factura,monto) VALUES(?,?,?)",(cot_id,num_fact,monto)); db.commit(); db.close()
            messagebox.showinfo("Guardado","Factura registrada."); self.refresh_facturas(); dlg.destroy()
        self._simple_dialog("Registrar Factura",[("ID de Cotización:","cot_id",""),("Número de Factura (SAT):","num_fact",""),("Monto (vacío = total cot.):","monto","")],save)

    def registrar_pago(self):
        def save(entries,dlg):
            fid_s=entries['fact_id'].get().strip(); monto_s=entries['monto'].get().strip(); metodo=entries['metodo'].get().strip()
            if not fid_s or not monto_s or not metodo: messagebox.showerror("Requerido","Complete todos los campos."); return
            try: fid=int(fid_s); monto=float(monto_s)
            except: messagebox.showerror("Error","ID y monto deben ser números."); return
            db=Database(); db.connect(); db.execute("INSERT INTO pagos(factura_id,monto,metodo) VALUES(?,?,?)",(fid,monto,metodo))
            db.execute("SELECT SUM(monto) FROM pagos WHERE factura_id=?",(fid,)); total_pag=db.fetchone()[0] or 0
            db.execute("SELECT monto FROM facturas WHERE id=?",(fid,)); r=db.fetchone()
            if r and total_pag>=r[0]-0.01: db.execute("UPDATE facturas SET estatus_pago='pagada' WHERE id=?",(fid,))
            db.commit(); db.close(); messagebox.showinfo("Guardado","Pago registrado."); self.refresh_facturas(); dlg.destroy()
        self._simple_dialog("Registrar Pago",[("ID de Factura:","fact_id",""),("Monto:","monto",""),("Método de pago:","metodo","Transferencia")],save)


# ──────────────────────── PÁGINA CONSULTAS ───────────────────────────────────
class ConsultasPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database(); self._build()

    def _build(self):
        self.configure(padding=14)
        ttk.Label(self,text="Panel de Consultas y Reportes",font=('Helvetica',14,'bold'),foreground=AZUL_OSCURO).pack(pady=(20,6))
        cards=ttk.Frame(self); cards.pack(pady=10)
        for txt,cmd in [("📊  Resumen de cotizaciones",self._resumen_cotizaciones),("💰  Facturas pendientes",self._facturas_pendientes),("📁  Proyectos activos",self._proyectos_activos)]:
            make_button(cards,txt,cmd,primary=True).pack(side=tk.LEFT,padx=8)
        self.result_text=scrolledtext.ScrolledText(self,height=22,font=('Courier',9),bg="#EEF4FC",relief="flat")
        self.result_text.pack(fill=tk.BOTH,expand=True,pady=10)

    def _show(self,content):
        self.result_text.config(state='normal'); self.result_text.delete('1.0',tk.END)
        self.result_text.insert('1.0',content); self.result_text.config(state='disabled')

    def _resumen_cotizaciones(self):
        self.db.connect(); self.db.execute('SELECT c.estatus,COUNT(*),SUM(c.total) FROM cotizaciones c GROUP BY c.estatus')
        rows=self.db.fetchall(); self.db.execute('SELECT c.numero_cotizacion,cl.nombre,c.total,c.estatus,c.fecha_emision FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id ORDER BY c.id DESC LIMIT 10')
        detalle=self.db.fetchall(); self.db.close()
        txt="─"*70+"\n  RESUMEN DE COTIZACIONES\n"+"─"*70+"\n\n"+f"{'Estatus':<15} {'Cantidad':>8}  {'Total USD':>16}\n"+"─"*45+"\n"
        for r in rows: txt+=f"{str(r[0]):<15} {r[1]:>8}  ${r[2]:>15,.2f}\n"
        txt+="\n"+"─"*70+"\n  ÚLTIMAS 10 COTIZACIONES\n"+"─"*70+f"\n\n{'Número':<20} {'Cliente':<22} {'Total':>12}  {'Estatus':<12} {'Fecha'}\n"+"─"*80+"\n"
        for r in detalle: txt+=f"{str(r[0]):<20} {str(r[1])[:21]:<22} ${r[2]:>11,.2f}  {str(r[3]):<12} {r[4]}\n"
        self._show(txt)

    def _facturas_pendientes(self):
        self.db.connect(); self.db.execute("SELECT f.numero_factura,c.numero_cotizacion,f.monto,f.estatus_pago,f.fecha_emision FROM facturas f JOIN cotizaciones c ON f.cotizacion_id=c.id WHERE f.estatus_pago='pendiente' ORDER BY f.id DESC")
        rows=self.db.fetchall(); self.db.close()
        txt="─"*70+"\n  FACTURAS PENDIENTES DE PAGO\n"+"─"*70+"\n\n"
        if rows:
            txt+=f"{'Factura':<18} {'Cotización':<18} {'Monto':>14}  {'Estatus':<12} {'Fecha'}\n"+"─"*80+"\n"
            for r in rows: txt+=f"{str(r[0]):<18} {str(r[1]):<18} ${r[2]:>13,.2f}  {r[3]:<12} {r[4]}\n"
        else: txt+="  No hay facturas pendientes.\n"
        self._show(txt)

    def _proyectos_activos(self):
        self.db.connect(); self.db.execute("SELECT p.nombre,c.nombre,p.responsable,p.fecha_creacion FROM proyectos p JOIN clientes c ON p.cliente_id=c.id WHERE p.estatus='activo' ORDER BY p.nombre")
        rows=self.db.fetchall(); self.db.close()
        txt="─"*70+"\n  PROYECTOS ACTIVOS\n"+"─"*70+f"\n\n{'Proyecto':<30} {'Cliente':<25} {'Responsable':<20} {'Fecha'}\n"+"─"*80+"\n"
        for r in rows: txt+=f"{str(r[0])[:29]:<30} {str(r[1])[:24]:<25} {str(r[2])[:19]:<20} {r[3]}\n"
        self._show(txt)


# ──────────────────────── PÁGINA PROVEEDORES ─────────────────────────────────
class ProveedoresPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database(); self.selected_id=None
        self.configure(padding=12); self._build(); self.refresh_list()

    def _build(self):
        form=ttk.LabelFrame(self,text="Datos del Proveedor",padding=14); form.pack(side=tk.LEFT,fill=tk.Y,padx=(0,10))
        fields=[("Nombre *","entry_nombre"),("Contacto","entry_contacto"),("Dirección","entry_direccion"),("Teléfono","entry_telefono"),("Email","entry_email"),("RFC","entry_rfc"),("Condiciones de Pago","entry_condpago")]
        for i,(lbl,attr) in enumerate(fields):
            ttk.Label(form,text=lbl).grid(row=i,column=0,sticky=tk.W,pady=5)
            e=ttk.Entry(form,width=32); e.grid(row=i,column=1,pady=5,padx=(8,0)); setattr(self,attr,e)
        btn_row=ttk.Frame(form); btn_row.grid(row=len(fields),column=0,columnspan=2,pady=14)
        make_button(btn_row,"💾  Guardar",self.guardar,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(btn_row,"➕  Nuevo",self.limpiar).pack(side=tk.LEFT,padx=4)
        make_button(btn_row,"🗑  Eliminar",self.eliminar).pack(side=tk.LEFT,padx=4)
        lst=ttk.LabelFrame(self,text="Proveedores Registrados",padding=10); lst.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        self.tree=make_treeview(lst,('id','nombre','contacto','telefono','email','rfc','condpago'),('ID','Nombre','Contacto','Teléfono','Email','RFC','Cond. Pago'),(40,155,120,90,155,90,130))
        self.tree.bind('<<TreeviewSelect>>',self._on_select)

    def refresh_list(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.db.connect(); self.db.execute("SELECT id,nombre,contacto,telefono,email,rfc,condiciones_pago FROM proveedores ORDER BY nombre")
        for row in self.db.fetchall(): self.tree.insert('',tk.END,values=row)
        self.db.close()

    def _on_select(self,_):
        sel=self.tree.selection()
        if not sel: return
        v=self.tree.item(sel[0])['values']; self.selected_id=v[0]
        for attr,val in zip(['entry_nombre','entry_contacto','entry_telefono','entry_email','entry_rfc','entry_condpago'],v[1:]):
            w=getattr(self,attr); w.delete(0,tk.END); w.insert(0,val or '')

    def limpiar(self):
        for a in ['entry_nombre','entry_contacto','entry_direccion','entry_telefono','entry_email','entry_rfc','entry_condpago']:
            getattr(self,a).delete(0,tk.END)
        self.selected_id=None

    def guardar(self):
        nombre=self.entry_nombre.get().strip()
        if not nombre: messagebox.showerror("Campo requerido","El nombre es obligatorio."); return
        data=(nombre,self.entry_contacto.get().strip(),self.entry_direccion.get().strip(),self.entry_telefono.get().strip(),self.entry_email.get().strip(),self.entry_rfc.get().strip(),self.entry_condpago.get().strip())
        self.db.connect()
        if self.selected_id:
            self.db.execute('UPDATE proveedores SET nombre=?,contacto=?,direccion=?,telefono=?,email=?,rfc=?,condiciones_pago=? WHERE id=?',data+(self.selected_id,))
        else:
            self.db.execute('INSERT INTO proveedores(nombre,contacto,direccion,telefono,email,rfc,condiciones_pago) VALUES(?,?,?,?,?,?,?)',data)
        self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
        self.app.set_status("Proveedor guardado")

    def eliminar(self):
        if not self.selected_id: messagebox.showwarning("Sin selección","Seleccione un proveedor."); return
        if messagebox.askyesno("Confirmar","¿Eliminar este proveedor?"):
            self.db.connect(); self.db.execute("DELETE FROM proveedores WHERE id=?",(self.selected_id,))
            self.db.commit(); self.db.close(); self.limpiar(); self.refresh_list()
            self.app.set_status("Proveedor eliminado",ok=False)


# ──────────────────────── PDF ORDEN PROVEEDOR ────────────────────────────────
def generar_pdf_orden_proveedor(orden_id,pdf_path):
    db=Database(); db.connect()
    db.execute('SELECT op.id,op.numero_op,op.fecha_emision,op.fecha_entrega,op.condiciones_pago,op.lugar_entrega,op.notas,op.total,op.estatus,p.nombre,p.contacto,p.direccion,p.email,p.telefono,p.rfc,COALESCE(op.moneda,"USD") AS moneda FROM ordenes_proveedor op JOIN proveedores p ON op.proveedor_id=p.id WHERE op.id=?',(orden_id,))
    cab=db.fetchone()
    if not cab: db.close(); raise ValueError("Orden no encontrada")
    db.execute('SELECT descripcion,cantidad,precio_unitario,total FROM items_orden_proveedor WHERE orden_id=?',(orden_id,))
    items=db.fetchall(); db.close()
    RL_AZUL=colors.HexColor("#0D2B55"); RL_AZUL_MED=colors.HexColor("#1A4A8A"); RL_AZUL_SUV=colors.HexColor("#D6E4F7")
    RL_GRIS=colors.HexColor("#F4F6FA"); RL_GRIS_BORD=colors.HexColor("#CCCCCC"); RL_BLANCO=colors.white
    page_w,page_h=A4
    doc=SimpleDocTemplate(pdf_path,pagesize=A4,rightMargin=1.8*cm,leftMargin=1.8*cm,topMargin=2*cm,bottomMargin=2*cm)
    styles=getSampleStyleSheet()
    def ps(name,parent='Normal',**kw): return ParagraphStyle(name+'_op',parent=styles[parent],**kw)
    s_titulo=ps('T',fontSize=20,textColor=RL_BLANCO,alignment=TA_CENTER,fontName='Helvetica-Bold')
    s_sub=ps('S',fontSize=9,textColor=RL_BLANCO,alignment=TA_CENTER,fontName='Helvetica')
    s_sec=ps('Se',fontSize=11,textColor=RL_AZUL,fontName='Helvetica-Bold',spaceBefore=10,spaceAfter=4)
    s_body=ps('B',fontSize=9,textColor=colors.HexColor('#333333'),fontName='Helvetica',leading=13)
    s_bold=ps('Bo',fontSize=9,textColor=colors.HexColor('#333333'),fontName='Helvetica-Bold')
    s_total=ps('To',fontSize=13,textColor=RL_BLANCO,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    s_footer=ps('F',fontSize=8,textColor=colors.grey,alignment=TA_CENTER)
    s_contact=ps('Co',fontSize=9,textColor=RL_BLANCO,fontName='Helvetica-Bold',alignment=TA_CENTER)
    styles_dict={'footer':s_footer,'contact':s_contact}
    story=[]
    hdr_rows=[[Paragraph("ORDEN DE COMPRA",s_titulo)],[Paragraph(f"No. {cab[1]}  |  Fecha emisión: {cab[2]}  |  Entrega estimada: {cab[3] or 'Por definir'}",s_sub)]]
    logo_disp=bool(LOGO_PATH and os.path.isfile(LOGO_PATH))
    if logo_disp:
        try:
            logo_img=Image(LOGO_PATH); max_w,max_h=5*cm,3*cm; ratio=min(max_w/logo_img.imageWidth,max_h/logo_img.imageHeight)
            logo_img.drawWidth=logo_img.imageWidth*ratio; logo_img.drawHeight=logo_img.imageHeight*ratio
            inner=Table(hdr_rows,colWidths=[11.8*cm]); inner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),RL_AZUL),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            ht=Table([[logo_img,inner]],colWidths=[5.4*cm,12.2*cm]); ht.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),RL_BLANCO),('BACKGROUND',(1,0),(1,-1),RL_AZUL),('ALIGN',(0,0),(0,-1),'CENTER'),('VALIGN',(0,0),(0,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        except: logo_disp=False
    if not logo_disp:
        ht=Table(hdr_rows,colWidths=[17.6*cm]); ht.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),RL_AZUL),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),14)]))
    story.append(ht); story.append(Spacer(1,14))
    story.append(Paragraph("Datos del Proveedor",s_sec)); story.append(HRFlowable(width="100%",thickness=1.5,color=RL_AZUL_MED)); story.append(Spacer(1,6))
    prov_data=[[Paragraph("<b>Proveedor:</b>",s_body),Paragraph(cab[9] or "—",s_body),Paragraph("<b>Contacto:</b>",s_body),Paragraph(cab[10] or "—",s_body)],[Paragraph("<b>Dirección:</b>",s_body),Paragraph(cab[11] or "—",s_body),Paragraph("<b>Email:</b>",s_body),Paragraph(cab[12] or "—",s_body)],[Paragraph("<b>Teléfono:</b>",s_body),Paragraph(cab[13] or "—",s_body),Paragraph("<b>RFC:</b>",s_body),Paragraph(cab[14] or "—",s_body)]]
    pt=Table(prov_data,colWidths=[3*cm,5.8*cm,3*cm,5.8*cm]); pt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),RL_GRIS),('BOX',(0,0),(-1,-1),0.5,RL_GRIS_BORD),('INNERGRID',(0,0),(-1,-1),0.3,RL_GRIS_BORD),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),6)]))
    story.append(pt); story.append(Spacer(1,10))
    moneda_oc=cab[15] if len(cab)>15 else "USD"; sym_oc="$" if moneda_oc=="USD" else "MX$"
    story.append(Paragraph("Partidas / Materiales Solicitados",s_sec)); story.append(HRFlowable(width="100%",thickness=1.5,color=RL_AZUL_MED)); story.append(Spacer(1,6))
    item_rows=[[Paragraph("<b>Descripción</b>",s_bold),Paragraph("<b>Cant.</b>",s_bold),Paragraph("<b>P. Unitario</b>",s_bold),Paragraph(f"<b>Total {moneda_oc}</b>",s_bold)]]
    subtotal=0
    for it in items:
        item_rows.append([Paragraph(str(it[0]),s_body),Paragraph(str(it[1]),s_body),Paragraph(f"{sym_oc}{it[2]:,.2f}",s_body),Paragraph(f"{sym_oc}{it[3]:,.2f}",s_body)]); subtotal+=it[3]
    if not items: item_rows.append([Paragraph("Sin partidas registradas",s_body),"","",""])
    it_tbl=Table(item_rows,colWidths=[9.6*cm,2*cm,3*cm,3*cm])
    rc=[('BACKGROUND',(0,0),(-1,0),RL_AZUL_MED),('TEXTCOLOR',(0,0),(-1,0),RL_BLANCO),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BOX',(0,0),(-1,-1),0.5,RL_GRIS_BORD),('INNERGRID',(0,0),(-1,-1),0.3,RL_GRIS_BORD),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),6),('ALIGN',(1,1),(-1,-1),'CENTER'),('ALIGN',(2,1),(-1,-1),'RIGHT'),('ALIGN',(3,1),(-1,-1),'RIGHT')]
    for i in range(1,len(item_rows)): rc.append(('BACKGROUND',(0,i),(-1,i),RL_AZUL_SUV if i%2==1 else RL_BLANCO))
    it_tbl.setStyle(TableStyle(rc)); story.append(it_tbl); story.append(Spacer(1,6))
    total_val=cab[7] or subtotal
    tot=Table([[Paragraph(f"TOTAL ORDEN:  {sym_oc}{total_val:,.2f} {moneda_oc}",s_total)]],colWidths=[17.6*cm])
    tot.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),RL_AZUL),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),14)]))
    story.append(tot); story.append(Spacer(1,12))
    if cab[6] and cab[6].strip():
        story.append(Paragraph("Notas / Observaciones",s_sec)); story.append(HRFlowable(width="100%",thickness=1.5,color=RL_AZUL_MED))
        story.append(Spacer(1,4)); story.append(Paragraph(cab[6].replace('\n','<br/>'),s_body)); story.append(Spacer(1,10))
    story.append(Spacer(1,20))
    firma_data=[[Paragraph("_______________________________",s_body),Paragraph("_______________________________",s_body)],[Paragraph(f"Autorizado por: {VEF_NOMBRE}",s_bold),Paragraph(f"Proveedor: {cab[9]}",s_bold)]]
    ft=Table(firma_data,colWidths=[8.8*cm,8.8*cm]); ft.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),4)])); story.append(ft)
    _pie_vef(story,styles_dict,RL_AZUL_MED)
    def _wm(cv,doc_obj):
        if not (LOGO_PATH and os.path.isfile(LOGO_PATH)): return
        try:
            from reportlab.lib.utils import ImageReader; cv.saveState(); ir=ImageReader(LOGO_PATH); iw,ih=ir.getSize()
            scale=min(12*cm/iw,12*cm/ih); cv.setFillAlpha(0.12); cv.setStrokeAlpha(0.12)
            cv.drawImage(ir,(page_w-iw*scale)/2,(page_h-ih*scale)/2,width=iw*scale,height=ih*scale,preserveAspectRatio=True,mask='auto'); cv.restoreState()
        except: pass
    doc.build(story,onFirstPage=_wm,onLaterPages=_wm)


# ──────────────────────── PÁGINA OC PROVEEDORES ──────────────────────────────
class OrdenesProveedorPage(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent); self.app=app; self.db=Database()
        self.selected_orden_id=None; self.configure(padding=10); self._build(); self.refresh_list()

    def _build(self):
        nb=ttk.Notebook(self); nb.pack(fill=tk.BOTH,expand=True)
        self.lista_frame=ttk.Frame(nb,padding=8); nb.add(self.lista_frame,text="📋  Órdenes de Compra")
        self._build_lista()
        self.seg_frame=ttk.Frame(nb,padding=8); nb.add(self.seg_frame,text="📝  Seguimientos")
        self._build_seguimientos()

    def _build_lista(self):
        lst=ttk.LabelFrame(self.lista_frame,text="Órdenes a Proveedores",padding=6); lst.pack(fill=tk.BOTH,expand=True)
        self.tree=make_treeview(lst,('id','numero','proveedor','fecha','entrega','total','moneda','estatus','cot_pdf'),('ID','Número OP','Proveedor','Emisión','Entrega Est.','Total','Mon.','Estatus','PDF Cot.'),(40,110,160,85,85,85,50,80,90),height=11)
        self.tree.bind('<<TreeviewSelect>>',self._on_select)
        bf=ttk.Frame(self.lista_frame); bf.pack(fill=tk.X,pady=6)
        for txt,cmd,prim in [("➕  Nueva OC",self.nueva_oc,True),("🔍  Ver Detalle",self.ver_detalle,False),("🔄  Cambiar Estatus",self.cambiar_estatus,False),("📝  Agregar Seguimiento",self.agregar_seguimiento,False),("📎  Adjuntar PDF Cot.",self.adjuntar_cotizacion_pdf,False),("📂  Abrir PDF Cot.",self.abrir_cotizacion_pdf,False),("📄  Generar PDF OC",self.generar_pdf,True),("✉️  Enviar a Proveedor",self.enviar_correo,False)]:
            make_button(bf,txt,cmd,primary=prim).pack(side=tk.LEFT,padx=3)
        res=ttk.LabelFrame(self.lista_frame,text="Detalle rápido",padding=6); res.pack(fill=tk.X,pady=(4,0))
        self.detalle_text=scrolledtext.ScrolledText(res,height=5,state='disabled',bg="#EEF4FC",fg=GRIS_TEXTO,font=('Helvetica',9),relief="flat"); self.detalle_text.pack(fill=tk.X)

    def _build_seguimientos(self):
        lst=ttk.LabelFrame(self.seg_frame,text="Historial de Seguimientos",padding=6); lst.pack(fill=tk.BOTH,expand=True)
        self.tree_seg=make_treeview(lst,('id','orden','fecha','tipo','notas','proxima'),('ID','Orden','Fecha','Tipo','Notas','Próxima Acción'),(45,110,130,80,280,180),height=16)
        bf=ttk.Frame(self.seg_frame); bf.pack(fill=tk.X,pady=6)
        make_button(bf,"🔄  Actualizar",self.refresh_seguimientos).pack(side=tk.LEFT,padx=4); self.refresh_seguimientos()

    def refresh_list(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.db.connect(); self.db.execute('SELECT op.id,op.numero_op,p.nombre,op.fecha_emision,op.fecha_entrega,op.total,COALESCE(op.moneda,"USD"),op.estatus,COALESCE(op.cotizacion_ref_pdf,"") FROM ordenes_proveedor op JOIN proveedores p ON op.proveedor_id=p.id ORDER BY op.id DESC')
        palette={'aprobada':'#d4edda','cancelada':'#f8d7da','enviada':'#fff3cd','recibida':'#cce5ff','cerrada':'#e2e3e5','borrador':'#f8f9fa'}
        for row in self.db.fetchall():
            cot_pdf="📎 "+os.path.basename(row[8]) if row[8] else "—"
            self.tree.insert('',tk.END,values=(row[0],row[1],row[2],row[3],row[4] or "—",f"${row[5]:,.2f}" if row[5] else "$0.00",row[6],row[7],cot_pdf),tags=(row[7],))
        for tag,bg in palette.items(): self.tree.tag_configure(tag,background=bg)
        self.db.close()

    def refresh_seguimientos(self):
        for r in self.tree_seg.get_children(): self.tree_seg.delete(r)
        self.db.connect(); self.db.execute('SELECT s.id,op.numero_op,s.fecha,s.tipo,s.notas,s.proxima_accion FROM seguimientos_oc s JOIN ordenes_proveedor op ON s.orden_id=op.id ORDER BY s.id DESC')
        for row in self.db.fetchall(): self.tree_seg.insert('',tk.END,values=row)
        self.db.close()

    def _on_select(self,_):
        sel=self.tree.selection()
        if not sel: return
        v=self.tree.item(sel[0])['values']; self.selected_orden_id=v[0]; self._mostrar_resumen(v[0])

    def _mostrar_resumen(self,oid):
        self.db.connect(); self.db.execute('SELECT op.numero_op,p.nombre,p.contacto,op.fecha_emision,op.fecha_entrega,op.total,op.estatus,op.condiciones_pago,COALESCE(op.cotizacion_ref_pdf,"") FROM ordenes_proveedor op JOIN proveedores p ON op.proveedor_id=p.id WHERE op.id=?',(oid,))
        r=self.db.fetchone(); self.db.close()
        if not r: return
        cot_pdf_info=f"PDF Cot.: {os.path.basename(r[8])}" if r[8] else "Sin PDF cotización"
        txt=f"Orden:  {r[0]}    Proveedor: {r[1]}    Contacto: {r[2]}\nEmisión: {r[3]}    Entrega: {r[4] or 'N/D'}    Total: ${r[5]:,.2f}    Estatus: {r[6].upper()}\nCond. Pago: {r[7] or '—'}    {cot_pdf_info}"
        self.detalle_text.config(state='normal'); self.detalle_text.delete(1.0,tk.END); self.detalle_text.insert(1.0,txt); self.detalle_text.config(state='disabled')

    def nueva_oc(self): NuevaOrdenProveedorDialog(self)
    def ver_detalle(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        DetalleOrdenProveedorDialog(self,self.selected_orden_id)
    def cambiar_estatus(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        CambiarEstatusOCDialog(self,self.selected_orden_id)
    def agregar_seguimiento(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        SeguimientoOCDialog(self,self.selected_orden_id)

    def adjuntar_cotizacion_pdf(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden primero."); return
        path=filedialog.askopenfilename(title="Seleccionar PDF de cotización de referencia",filetypes=[("PDF","*.pdf"),("Todos los archivos","*.*")])
        if not path: return
        db=Database(); db.connect(); db.execute("UPDATE ordenes_proveedor SET cotizacion_ref_pdf=? WHERE id=?",(path,self.selected_orden_id)); db.commit(); db.close()
        self.refresh_list(); self.app.set_status(f"PDF cotización adjunto: {os.path.basename(path)}")
        messagebox.showinfo("PDF adjunto",f"PDF de cotización adjunto:\n{os.path.basename(path)}")

    def abrir_cotizacion_pdf(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        db=Database(); db.connect(); db.execute("SELECT cotizacion_ref_pdf FROM ordenes_proveedor WHERE id=?",(self.selected_orden_id,)); r=db.fetchone(); db.close()
        if not r or not r[0]: messagebox.showinfo("Sin PDF","Esta OC no tiene PDF de cotización adjunto."); return
        if not os.path.isfile(r[0]): messagebox.showerror("No encontrado",f"El archivo no se encontró:\n{r[0]}"); return
        os.startfile(r[0]) if os.name=='nt' else os.system(f'xdg-open "{r[0]}"')

    def generar_pdf(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        self.db.connect(); self.db.execute("SELECT numero_op FROM ordenes_proveedor WHERE id=?",(self.selected_orden_id,)); row=self.db.fetchone(); self.db.close()
        num=(row[0] or str(self.selected_orden_id)).replace('/','- ')
        filename=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("Archivo PDF","*.pdf")],initialfile=f"OrdenCompra_{num}.pdf",title="Guardar Orden de Compra como PDF")
        if not filename: return
        try:
            generar_pdf_orden_proveedor(self.selected_orden_id,filename)
            messagebox.showinfo("PDF generado",f"PDF guardado en:\n{filename}"); self.app.set_status(f"PDF OC generado: {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error al generar PDF",str(e)); self.app.set_status("Error al generar PDF OC",ok=False)

    def enviar_correo(self):
        if not self.selected_orden_id: messagebox.showwarning("Sin selección","Seleccione una orden."); return
        oid=self.selected_orden_id; tmp=os.path.join(tempfile.gettempdir(),f"orden_proveedor_{oid}.pdf")
        try: generar_pdf_orden_proveedor(oid,tmp)
        except Exception as e: messagebox.showerror("Error",f"No se pudo generar el PDF:\n{e}"); return
        self.db.connect(); self.db.execute('SELECT op.numero_op,p.email,p.nombre,p.contacto,COALESCE(op.cotizacion_ref_pdf,"") FROM ordenes_proveedor op JOIN proveedores p ON op.proveedor_id=p.id WHERE op.id=?',(oid,))
        row=self.db.fetchone(); self.db.close()
        CorreoOrdenProveedorDialog(self,oid,tmp,row[0] if row else str(oid),row[1] if row else "",row[2] if row else "",row[3] if row else "",cot_pdf_path=row[4] if row else "")


# ─── Diálogos OC Proveedor ───────────────────────────────────────────────────
class NuevaOrdenProveedorDialog(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent); self.parent=parent; self.title("Nueva Orden de Compra a Proveedor")
        self.geometry("860x720"); self.configure(bg=GRIS_CLARO); self.db=Database()
        self.items=[]; self.proveedores=self._load_proveedores(); self.cot_pdf_path=""; self._build()

    def _load_proveedores(self):
        self.db.connect(); self.db.execute("SELECT id,nombre,contacto,condiciones_pago FROM proveedores ORDER BY nombre")
        r=self.db.fetchall(); self.db.close(); return r

    def _build(self):
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(fill=tk.X)
        tk.Label(hdr,text="  Nueva Orden de Compra — Proveedor",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',12,'bold')).pack(side=tk.LEFT,pady=10)
        canvas=tk.Canvas(self,bg=GRIS_CLARO,highlightthickness=0); sb=ttk.Scrollbar(self,orient="vertical",command=canvas.yview)
        self.sf=ttk.Frame(canvas); self.sf.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=self.sf,anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True); sb.pack(side=tk.RIGHT,fill=tk.Y)
        canvas.bind_all("<MouseWheel>",lambda e: canvas.yview_scroll(int(-1*(e.delta/120)),"units"))
        f=self.sf; pad=dict(pady=5,padx=8)
        ttk.Label(f,text="Proveedor *").grid(row=0,column=0,sticky=tk.W,**pad)
        self.combo_prov=ttk.Combobox(f,state="readonly",width=60)
        self.combo_prov['values']=[f"{p[0]} – {p[1]}" for p in self.proveedores]
        self.combo_prov.grid(row=0,column=1,**pad); self.combo_prov.bind("<<ComboboxSelected>>",self._on_prov_select)
        ttk.Label(f,text="Moneda *").grid(row=1,column=0,sticky=tk.W,**pad)
        mf=ttk.Frame(f); mf.grid(row=1,column=1,sticky=tk.W,**pad); self.moneda_var=tk.StringVar(value="USD")
        tk.Radiobutton(mf,text="USD  (Dólares)",variable=self.moneda_var,value="USD",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT,padx=(0,20))
        tk.Radiobutton(mf,text="MXN  (Pesos MXN)",variable=self.moneda_var,value="MXN",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT)
        for i,(lbl,attr,default) in enumerate([("Fecha Entrega Estimada","entry_entrega",datetime.date.today().strftime("%Y-%m-%d")),("Condiciones de Pago","entry_pago",""),("Lugar de Entrega","entry_lugar","Planta VEF Automatización")],2):
            ttk.Label(f,text=lbl).grid(row=i,column=0,sticky=tk.W,**pad)
            e=ttk.Entry(f,width=60); e.insert(0,default); e.grid(row=i,column=1,**pad); setattr(self,attr,e)
        ttk.Label(f,text="Notas / Observaciones").grid(row=5,column=0,sticky=tk.NW,**pad)
        self.text_notas=scrolledtext.ScrolledText(f,width=60,height=3,font=('Helvetica',9)); self.text_notas.grid(row=5,column=1,**pad)
        ttk.Label(f,text="PDF Cotización (ref.)").grid(row=6,column=0,sticky=tk.W,**pad)
        cot_frame=ttk.Frame(f); cot_frame.grid(row=6,column=1,sticky=tk.W,**pad)
        self.lbl_cot_pdf=ttk.Label(cot_frame,text="Sin PDF adjunto",foreground="#888888",font=('Helvetica',8,'italic')); self.lbl_cot_pdf.pack(side=tk.LEFT)
        make_button(cot_frame,"📎  Seleccionar PDF",self._seleccionar_cot_pdf).pack(side=tk.LEFT,padx=(10,0))
        make_button(cot_frame,"✖  Quitar",self._quitar_cot_pdf).pack(side=tk.LEFT,padx=4)
        items_lf=ttk.LabelFrame(f,text="Partidas / Materiales",padding=8); items_lf.grid(row=7,column=0,columnspan=2,sticky=tk.EW,**pad)
        self.tree_items=make_treeview(items_lf,('desc','cant','pu','total'),('Descripción','Cantidad','P. Unitario','Total'),(340,70,120,120),height=5)
        ibf=ttk.Frame(f); ibf.grid(row=8,column=0,columnspan=2,pady=4)
        make_button(ibf,"➕ Agregar Partida",self.agregar_item,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(ibf,"🗑 Eliminar Partida",self.eliminar_item).pack(side=tk.LEFT,padx=4)
        self.lbl_total=ttk.Label(f,text="Total:  $0.00 USD",font=('Helvetica',13,'bold'),foreground=AZUL_OSCURO); self.lbl_total.grid(row=9,column=0,columnspan=2,pady=10)
        bf=ttk.Frame(f); bf.grid(row=10,column=0,columnspan=2,pady=12)
        make_button(bf,"💾  Guardar Orden",self.guardar,primary=True).pack(side=tk.LEFT,padx=6)
        make_button(bf,"✖  Cancelar",self.destroy).pack(side=tk.LEFT,padx=6)

    def _seleccionar_cot_pdf(self):
        path=filedialog.askopenfilename(title="Seleccionar PDF de cotización",filetypes=[("PDF","*.pdf"),("Todos","*.*")])
        if path: self.cot_pdf_path=path; self.lbl_cot_pdf.config(text=f"📎 {os.path.basename(path)}",foreground=VERDE_OK)

    def _quitar_cot_pdf(self): self.cot_pdf_path=""; self.lbl_cot_pdf.config(text="Sin PDF adjunto",foreground="#888888")

    def _on_prov_select(self,_):
        ps=self.combo_prov.get()
        if not ps: return
        prov_id=int(ps.split(' – ')[0]); prov=next((p for p in self.proveedores if p[0]==prov_id),None)
        if prov and prov[3]: self.entry_pago.delete(0,tk.END); self.entry_pago.insert(0,prov[3])

    def agregar_item(self): ItemOrdenDialog(self)
    def eliminar_item(self):
        sel=self.tree_items.selection()
        if not sel: return
        v=self.tree_items.item(sel[0])['values']
        for it in self.items:
            if str(it[0])==str(v[0]): self.items.remove(it); break
        self.tree_items.delete(sel[0]); self._recalc()

    def adicionar_item(self,desc,cant,pu,total):
        moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.items.append((desc,cant,pu,total))
        self.tree_items.insert('',tk.END,values=(desc,cant,f"{sym}{pu:,.2f}",f"{sym}{total:,.2f}")); self._recalc()

    def _recalc(self):
        total=sum(i[3] for i in self.items); moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.lbl_total.config(text=f"Total:  {sym}{total:,.2f} {moneda}")

    def guardar(self):
        ps=self.combo_prov.get()
        if not ps: messagebox.showerror("Campo requerido","Seleccione un proveedor."); return
        prov_id=int(ps.split(' – ')[0]); moneda=self.moneda_var.get()
        hoy=datetime.date.today(); fecha_str=hoy.strftime("%Y%m%d")
        self.db.connect(); self.db.execute("SELECT COUNT(*) FROM ordenes_proveedor WHERE numero_op LIKE ?",(f"%{fecha_str}%",))
        count=self.db.fetchone()[0]+1; numero=f"OCP-{fecha_str}-{count:03d}"; total=sum(i[3] for i in self.items)
        self.db.execute('INSERT INTO ordenes_proveedor(proveedor_id,numero_op,fecha_entrega,condiciones_pago,lugar_entrega,notas,total,moneda,estatus,cotizacion_ref_pdf) VALUES(?,?,?,?,?,?,?,?,"borrador",?)',
            (prov_id,numero,self.entry_entrega.get().strip(),self.entry_pago.get().strip(),self.entry_lugar.get().strip(),self.text_notas.get('1.0',tk.END).strip(),total,moneda,self.cot_pdf_path or None))
        oid=self.db.lastrowid()
        for it in self.items: self.db.execute('INSERT INTO items_orden_proveedor(orden_id,descripcion,cantidad,precio_unitario,total) VALUES(?,?,?,?,?)',(oid,it[0],it[1],it[2],it[3]))
        self.db.commit(); self.db.close()
        messagebox.showinfo("Orden creada",f"Orden {numero} guardada en {moneda} (ID {oid})."); self.parent.refresh_list(); self.destroy()


class ItemOrdenDialog(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent); self.parent=parent; self.title("Agregar Partida")
        self.geometry("520x220"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        hdr=tk.Frame(self,bg=AZUL_MEDIO,height=36); hdr.pack(fill=tk.X)
        tk.Label(hdr,text="  Agregar Partida / Material",bg=AZUL_MEDIO,fg=BLANCO,font=('Helvetica',10,'bold')).pack(side=tk.LEFT,pady=8)
        f=ttk.Frame(self,padding=14); f.pack(fill=tk.BOTH,expand=True)
        ttk.Label(f,text="Descripción *").grid(row=0,column=0,sticky=tk.W,pady=6)
        self.entry_desc=ttk.Entry(f,width=48); self.entry_desc.grid(row=0,column=1,pady=6,padx=8)
        ttk.Label(f,text="Cantidad *").grid(row=1,column=0,sticky=tk.W,pady=6)
        self.entry_cant=ttk.Entry(f,width=20); self.entry_cant.grid(row=1,column=1,sticky=tk.W,pady=6,padx=8)
        ttk.Label(f,text="Precio Unitario *").grid(row=2,column=0,sticky=tk.W,pady=6)
        self.entry_pu=ttk.Entry(f,width=20); self.entry_pu.grid(row=2,column=1,sticky=tk.W,pady=6,padx=8)
        bf=ttk.Frame(f); bf.grid(row=3,column=0,columnspan=2,pady=12)
        make_button(bf,"✔  Aceptar",self._aceptar,primary=True).pack(side=tk.LEFT,padx=6)
        make_button(bf,"✖  Cancelar",self.destroy).pack(side=tk.LEFT,padx=6)

    def _aceptar(self):
        desc=self.entry_desc.get().strip()
        if not desc: messagebox.showerror("Requerido","Descripción obligatoria."); return
        try:
            cant=int(self.entry_cant.get().strip()); pu=float(self.entry_pu.get().strip())
            if cant<=0 or pu<=0: raise ValueError
        except ValueError: messagebox.showerror("Valor inválido","Cantidad y precio deben ser números positivos."); return
        self.parent.adicionar_item(desc,cant,pu,cant*pu); self.destroy()


class DetalleOrdenProveedorDialog(tk.Toplevel):
    def __init__(self,parent,oid):
        super().__init__(parent); self.title("Detalle Orden de Compra"); self.geometry("860x600"); self.configure(bg=GRIS_CLARO)
        db=Database(); db.connect()
        db.execute('SELECT op.*,p.nombre,p.contacto,p.direccion,p.email,p.rfc FROM ordenes_proveedor op JOIN proveedores p ON op.proveedor_id=p.id WHERE op.id=?',(oid,))
        row=db.fetchone()
        if not row: self.destroy(); return
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(fill=tk.X)
        tk.Label(hdr,text=f"  Orden: {row[2]}",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',12,'bold')).pack(side=tk.LEFT,pady=10)
        txt=scrolledtext.ScrolledText(self,wrap=tk.WORD,font=('Courier',9),bg="#EEF4FC",relief="flat")
        txt.pack(fill=tk.BOTH,expand=True,padx=12,pady=10)
        try: cot_pdf=row[11] or ""
        except: cot_pdf=""
        try: prov_nombre=row[12] or ""; prov_contact=row[13] or ""; prov_dir=row[14] or ""; prov_email=row[15] or ""; prov_rfc=row[16] or ""
        except: prov_nombre=prov_contact=prov_dir=prov_email=prov_rfc=""
        content=f"\n{'─'*80}\n  ORDEN DE COMPRA No. {row[2]}\n  Fecha Emisión: {row[3]}   ·   Entrega Estimada: {row[4] or 'N/D'}\n  Proveedor: {prov_nombre}   ·   Contacto: {prov_contact}\n{'─'*80}\n  Condiciones de Pago : {row[5] or '—'}\n  Lugar de Entrega    : {row[6] or '—'}\n  Notas               : {row[7] or '—'}\n  TOTAL               : ${row[8]:,.2f} USD\n  ESTATUS             : {row[9].upper()}\n  PDF Cotización ref. : {os.path.basename(cot_pdf) if cot_pdf else '—'}\n{'─'*80}\n"
        db.execute("SELECT descripcion,cantidad,precio_unitario,total FROM items_orden_proveedor WHERE orden_id=?",(oid,))
        items=db.fetchall(); db.close()
        if items:
            content+=f"\n{'Descripción':<44} {'Cant':>5}  {'P.Unit':>12}  {'Total':>12}\n"+"─"*80+"\n"
            for it in items: content+=f"{str(it[0])[:43]:<44} {it[1]:>5}  ${it[2]:>11,.2f}  ${it[3]:>11,.2f}\n"
        txt.insert(tk.END,content); txt.config(state='disabled')


class CambiarEstatusOCDialog(tk.Toplevel):
    def __init__(self,parent,oid):
        super().__init__(parent); self.parent=parent; self.oid=oid; self.title("Cambiar Estatus OC")
        self.geometry("320x180"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        ttk.Label(self,text="Nuevo estatus de la orden:",font=('Helvetica',10)).pack(pady=(20,8))
        self.combo=ttk.Combobox(self,state='readonly',width=30,values=['borrador','enviada','aprobada','recibida','cancelada','cerrada']); self.combo.pack(pady=6)
        make_button(self,"✔  Actualizar",self._actualizar,primary=True).pack(pady=14)

    def _actualizar(self):
        val=self.combo.get()
        if not val: return
        db=Database(); db.connect(); db.execute("UPDATE ordenes_proveedor SET estatus=? WHERE id=?",(val,self.oid)); db.commit(); db.close()
        messagebox.showinfo("Actualizado",f"Estatus cambiado a '{val}'."); self.parent.refresh_list(); self.destroy()


class SeguimientoOCDialog(tk.Toplevel):
    def __init__(self,parent,oid):
        super().__init__(parent); self.parent=parent; self.oid=oid; self.title("Registro de Seguimiento — OC Proveedor")
        self.geometry("440x320"); self.configure(bg=GRIS_CLARO); self.resizable(False,False)
        ttk.Label(self,text="Tipo de contacto:").pack(pady=(18,4))
        self.combo=ttk.Combobox(self,state='readonly',width=30,values=['llamada','correo','reunión','whatsapp','visita']); self.combo.pack(pady=4)
        ttk.Label(self,text="Notas:").pack(pady=(10,4))
        self.text_notas=scrolledtext.ScrolledText(self,height=5,font=('Helvetica',9)); self.text_notas.pack(padx=14,fill=tk.X)
        ttk.Label(self,text="Próxima acción:").pack(pady=(10,4))
        self.entry_prox=ttk.Entry(self,width=44); self.entry_prox.pack(pady=4)
        make_button(self,"💾  Guardar",self._guardar,primary=True).pack(pady=14)

    def _guardar(self):
        tipo=self.combo.get()
        if not tipo: messagebox.showerror("Requerido","Seleccione el tipo."); return
        db=Database(); db.connect(); db.execute("INSERT INTO seguimientos_oc(orden_id,tipo,notas,proxima_accion) VALUES(?,?,?,?)",(self.oid,tipo,self.text_notas.get('1.0',tk.END).strip(),self.entry_prox.get().strip()))
        db.commit(); db.close(); messagebox.showinfo("Guardado","Seguimiento registrado."); self.parent.refresh_seguimientos(); self.destroy()


class CorreoOrdenProveedorDialog(tk.Toplevel):
    def __init__(self,parent,oid,pdf_path,numero,email_prov="",nombre_prov="",contacto_prov="",cot_pdf_path=""):
        super().__init__(parent); self.pdf_path=pdf_path; self.cot_pdf_path=cot_pdf_path
        self.title("Enviar Orden de Compra — Zoho Mail"); self.geometry("580x640")
        self.configure(bg=GRIS_CLARO); self.resizable(True,True); self.minsize(540,580)
        self._build(numero,email_prov,nombre_prov,contacto_prov)

    def _build(self,numero,email_prov,nombre_prov,contacto_prov):
        hdr=tk.Frame(self,bg=AZUL_OSCURO,height=44); hdr.pack(side=tk.TOP,fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr,text="  ✉  Enviar Orden de Compra — Zoho Mail",bg=AZUL_OSCURO,fg=BLANCO,font=('Helvetica',11,'bold')).pack(side=tk.LEFT,pady=10)
        outer=tk.Frame(self,bg=GRIS_CLARO); outer.pack(fill=tk.BOTH,expand=True)
        cv=tk.Canvas(outer,bg=GRIS_CLARO,highlightthickness=0); vsb=ttk.Scrollbar(outer,orient="vertical",command=cv.yview)
        cv.configure(yscrollcommand=vsb.set); vsb.pack(side=tk.RIGHT,fill=tk.Y); cv.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        frame=ttk.Frame(cv,padding=16); fid=cv.create_window((0,0),window=frame,anchor="nw")
        frame.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(fid,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        row=0
        if nombre_prov:
            ttk.Label(frame,text=f"Proveedor: {nombre_prov}"+(f"  |  Contacto: {contacto_prov}" if contacto_prov else ""),foreground=AZUL_MEDIO,font=('Helvetica',9,'italic')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(0,8)); row+=1
        if self.cot_pdf_path and os.path.isfile(self.cot_pdf_path):
            cot_info=f"📎 PDF cotización adjunto: {os.path.basename(self.cot_pdf_path)}"; cot_color=VERDE_OK
        elif self.cot_pdf_path:
            cot_info=f"⚠ PDF cotización no encontrado: {os.path.basename(self.cot_pdf_path)}"; cot_color=NARANJA_WARN
        else:
            cot_info="ℹ Sin PDF de cotización adjunto"; cot_color="#888888"
        ttk.Label(frame,text=cot_info,foreground=cot_color,font=('Helvetica',8,'italic')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(0,6)); row+=1
        REMITENTE_FIJO="soporte.ventas@vef-automatizacion.com"; PASSWORD_FIJO="Brabata2323!"
        ttk.Label(frame,text="─── Remitente (VEF Automatización) ───",foreground=AZUL_OSCURO,font=('Helvetica',9,'bold')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(4,6)); row+=1
        for lbl,attr,default,es_pass in [("Correo remitente:","entry_from",REMITENTE_FIJO,False),("Contraseña:","entry_pass",PASSWORD_FIJO,True)]:
            ttk.Label(frame,text=lbl).grid(row=row,column=0,sticky=tk.W,pady=5)
            e=ttk.Entry(frame,width=40,show='*' if es_pass else ''); e.insert(0,default); e.config(state='readonly')
            e.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); setattr(self,attr,e); row+=1
        ttk.Label(frame,text="✔ Cuenta configurada: VEF Automatización",foreground=VERDE_OK,font=('Helvetica',8)).grid(row=row,column=1,sticky=tk.W,padx=8); row+=1
        ttk.Label(frame,text="Servidor SMTP:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.combo_smtp=ttk.Combobox(frame,state="readonly",width=37,values=["smtp.zoho.com  (puerto 587 – TLS)","smtp.zoho.com  (puerto 465 – SSL)","smtp.zoho.eu   (puerto 587 – TLS)","smtp.zoho.eu   (puerto 465 – SSL)"])
        self.combo_smtp.current(0); self.combo_smtp.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="─── Destinatario (Proveedor) ───",foreground=AZUL_OSCURO,font=('Helvetica',9,'bold')).grid(row=row,column=0,columnspan=2,sticky=tk.W,pady=(10,6)); row+=1
        ttk.Label(frame,text="Para *:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_to=ttk.Entry(frame,width=40); self.entry_to.insert(0,email_prov or "")
        self.entry_to.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="✔ Email obtenido del registro del proveedor" if email_prov else "⚠ Este proveedor no tiene email registrado",foreground=VERDE_OK if email_prov else NARANJA_WARN,font=('Helvetica',8)).grid(row=row,column=1,sticky=tk.W,padx=8); row+=1
        ttk.Label(frame,text="CC (opcional):").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_cc=ttk.Entry(frame,width=40); self.entry_cc.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="Asunto *:").grid(row=row,column=0,sticky=tk.W,pady=5)
        self.entry_asunto=ttk.Entry(frame,width=40); self.entry_asunto.insert(0,f"Orden de Compra {numero} — {VEF_NOMBRE}")
        self.entry_asunto.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Label(frame,text="Mensaje:").grid(row=row,column=0,sticky=tk.NW,pady=5)
        self.text_msg=scrolledtext.ScrolledText(frame,height=7,width=38,font=('Helvetica',9))
        adj_cot=(f"\n\nAdjunto también el PDF de cotización de referencia: {os.path.basename(self.cot_pdf_path)}.") if (self.cot_pdf_path and os.path.isfile(self.cot_pdf_path)) else ""
        self.text_msg.insert('1.0',f"Estimado/a {contacto_prov or nombre_prov or 'estimado proveedor'},\n\nAdjunto la Orden de Compra {numero} emitida por {VEF_NOMBRE}.{adj_cot}\n\nLe pedimos confirmar la recepción y disponibilidad de los materiales.\n\nAtentamente,\n{VEF_NOMBRE}\nTel: {VEF_TELEFONO}\nCorreo: {VEF_CORREO}")
        self.text_msg.grid(row=row,column=1,pady=5,padx=8,sticky=tk.W); row+=1
        ttk.Separator(frame,orient='horizontal').grid(row=row,column=0,columnspan=2,sticky=tk.EW,pady=10); row+=1
        bf=ttk.Frame(frame); bf.grid(row=row,column=0,columnspan=2,pady=(4,16))
        tk.Button(bf,text="  ✉   ENVIAR ORDEN DE COMPRA   ",command=self._enviar,bg=AZUL_MEDIO,fg=BLANCO,font=('Helvetica',11,'bold'),relief="flat",cursor="hand2",activebackground=AZUL_CLARO,activeforeground=BLANCO,padx=18,pady=10).pack(side=tk.LEFT,padx=8)
        tk.Button(bf,text="✖  Cancelar",command=self.destroy,bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',9),relief="flat",cursor="hand2",activebackground="#E0E0E0",padx=10,pady=10).pack(side=tk.LEFT,padx=4)

    def _enviar(self):
        self.entry_from.config(state='normal'); self.entry_pass.config(state='normal')
        remitente=self.entry_from.get().strip(); password=self.entry_pass.get().strip()
        self.entry_from.config(state='readonly'); self.entry_pass.config(state='readonly')
        dest=self.entry_to.get().strip(); cc=self.entry_cc.get().strip()
        asunto=self.entry_asunto.get().strip(); mensaje=self.text_msg.get('1.0',tk.END).strip()
        smtp_sel=self.combo_smtp.get()
        if not all([remitente,password,dest,asunto]): messagebox.showerror("Campos incompletos","Destinatario y asunto son obligatorios."); return
        use_ssl="465" in smtp_sel; smtp_host=smtp_sel.split()[0]; smtp_port=465 if use_ssl else 587
        try:
            msg=MIMEMultipart(); msg['From']=remitente; msg['To']=dest; msg['Subject']=asunto
            if cc: msg['Cc']=cc
            msg.attach(MIMEText(mensaje,'plain','utf-8'))
            with open(self.pdf_path,"rb") as f:
                part=MIMEBase('application','octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
                part.add_header('Content-Disposition',f'attachment; filename="{os.path.basename(self.pdf_path)}"'); msg.attach(part)
            if self.cot_pdf_path and os.path.isfile(self.cot_pdf_path):
                with open(self.cot_pdf_path,"rb") as f:
                    part2=MIMEBase('application','octet-stream'); part2.set_payload(f.read()); encoders.encode_base64(part2)
                    part2.add_header('Content-Disposition',f'attachment; filename="Cotizacion_{os.path.basename(self.cot_pdf_path)}"'); msg.attach(part2)
            recipients=[dest]+([cc] if cc else [])
            if use_ssl:
                import ssl; ctx=ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host,smtp_port,context=ctx) as server: server.login(remitente,password); server.sendmail(remitente,recipients,msg.as_bytes())
            else:
                with smtplib.SMTP(smtp_host,smtp_port) as server: server.ehlo(); server.starttls(); server.ehlo(); server.login(remitente,password); server.sendmail(remitente,recipients,msg.as_bytes())
            messagebox.showinfo("✔ Correo enviado",f"Orden enviada correctamente a:\n{dest}"+(f"\nCC: {cc}" if cc else "")); self.destroy()
        except smtplib.SMTPAuthenticationError: messagebox.showerror("Error de autenticación","Verifica usuario y contraseña Zoho.")
        except Exception as e: messagebox.showerror("Error al enviar",str(e))


# ──────────────────────── EDITAR COTIZACIÓN ──────────────────────────────────
class EditarCotizacionDialog(tk.Toplevel):
    def __init__(self,parent,cot_id):
        super().__init__(parent); self.parent=parent; self.cot_id=cot_id; self.db=Database()
        self.items=[]; self.title("Modificar Cotización"); self.geometry("880x760"); self.configure(bg=GRIS_CLARO)
        self._load_data(); self._build(); self._populate()

    def _load_data(self):
        self.db.connect()
        self.db.execute('SELECT c.id,c.numero_cotizacion,c.fecha_emision,c.validez_hasta,c.alcance_tecnico,c.notas_importantes,c.comentarios_generales,c.servicio_postventa,c.condiciones_entrega,c.condiciones_pago,c.garantia,c.responsabilidad,c.total,c.estatus,COALESCE(c.moneda,"USD"),c.validez,c.fuerza_mayor,c.ley_aplicable,c.proyecto_id,p.nombre AS proy_nombre,cl.nombre AS cli_nombre FROM cotizaciones c JOIN proyectos p ON c.proyecto_id=p.id JOIN clientes cl ON p.cliente_id=cl.id WHERE c.id=?',(self.cot_id,))
        self.data=self.db.fetchone()
        self.db.execute('SELECT id,descripcion,cantidad,precio_unitario,total FROM items_cotizacion WHERE cotizacion_id=? ORDER BY id',(self.cot_id,)); self.items_db=self.db.fetchall()
        self.db.execute('SELECT p.id,p.nombre,cl.nombre FROM proyectos p JOIN clientes cl ON p.cliente_id=cl.id ORDER BY p.nombre'); self.proyectos=self.db.fetchall()
        self.db.close()
        for it in self.items_db: self.items.append((it[1],it[2],it[3],it[4]))

    def _build(self):
        hdr=tk.Frame(self,bg=AZUL_MEDIO,height=44); hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr,text=f"  ✏️  Modificar Cotización  —  {self.data[1]}",bg=AZUL_MEDIO,fg=BLANCO,font=('Helvetica',12,'bold')).pack(side=tk.LEFT,pady=10)
        outer=tk.Frame(self,bg=GRIS_CLARO); outer.pack(fill=tk.BOTH,expand=True)
        cv=tk.Canvas(outer,bg=GRIS_CLARO,highlightthickness=0); vsb=ttk.Scrollbar(outer,orient="vertical",command=cv.yview)
        cv.configure(yscrollcommand=vsb.set); vsb.pack(side=tk.RIGHT,fill=tk.Y); cv.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        f=ttk.Frame(cv,padding=14); fid=cv.create_window((0,0),window=f,anchor="nw")
        f.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(fid,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        self.sf=f; pad=dict(pady=5,padx=8)
        ttk.Label(f,text="Proyecto *").grid(row=0,column=0,sticky=tk.W,**pad)
        self.combo_proyecto=ttk.Combobox(f,state="readonly",width=60)
        self.combo_proyecto['values']=[f"{p[0]} – {p[1]}  (Cliente: {p[2]})" for p in self.proyectos]
        self.combo_proyecto.grid(row=0,column=1,**pad)
        ttk.Label(f,text="Moneda *").grid(row=1,column=0,sticky=tk.W,**pad)
        mf=ttk.Frame(f); mf.grid(row=1,column=1,sticky=tk.W,**pad); self.moneda_var=tk.StringVar(value="USD")
        tk.Radiobutton(mf,text="USD  (Dólares)",variable=self.moneda_var,value="USD",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT,padx=(0,20))
        tk.Radiobutton(mf,text="MXN  (Pesos MXN)",variable=self.moneda_var,value="MXN",bg=GRIS_CLARO,fg=GRIS_TEXTO,font=('Helvetica',10,'bold'),activebackground=GRIS_CLARO,command=self._recalc).pack(side=tk.LEFT)
        text_fields=[("Alcance Técnico *","text_alcance",5),("Notas Importantes","text_notas",3),("Comentarios Generales","text_comentarios",4),("Servicio Postventa","text_postventa",3),("Condic. Entrega y Pago","text_entrega",4),("Garantía","text_garantia",5),("Validez","text_validez",2),("Fuerza Mayor","text_fuerza",3),("Ley Aplicable","text_ley",2)]
        for i,(lbl,attr,h) in enumerate(text_fields,2):
            ttk.Label(f,text=lbl).grid(row=i,column=0,sticky=tk.NW,**pad)
            w=scrolledtext.ScrolledText(f,width=65,height=h,font=('Helvetica',9)); w.grid(row=i,column=1,**pad); setattr(self,attr,w)
        base=len(text_fields)+2
        items_lf=ttk.LabelFrame(f,text="Partidas / Items",padding=8); items_lf.grid(row=base,column=0,columnspan=2,sticky=tk.EW,**pad)
        self.tree_items=make_treeview(items_lf,('desc','cant','pu','total'),('Descripción','Cantidad','P. Unitario','Total'),(340,70,120,120),height=5)
        ibf=ttk.Frame(f); ibf.grid(row=base+1,column=0,columnspan=2,pady=4)
        make_button(ibf,"➕ Agregar Partida",self._agregar_item,primary=True).pack(side=tk.LEFT,padx=4)
        make_button(ibf,"🗑 Eliminar Partida",self._eliminar_item).pack(side=tk.LEFT,padx=4)
        self.lbl_total=ttk.Label(f,text="Total:  $0.00 USD",font=('Helvetica',13,'bold'),foreground=AZUL_OSCURO); self.lbl_total.grid(row=base+2,column=0,columnspan=2,pady=10)
        bf=ttk.Frame(f); bf.grid(row=base+3,column=0,columnspan=2,pady=14)
        make_button(bf,"💾  Guardar Cambios",self._guardar,primary=True).pack(side=tk.LEFT,padx=6)
        make_button(bf,"✖  Cancelar",self.destroy).pack(side=tk.LEFT,padx=6)

    def _populate(self):
        d=self.data
        for idx,p in enumerate(self.proyectos):
            if p[0]==d[18]: self.combo_proyecto.current(idx); break
        self.moneda_var.set(d[14] or "USD")
        for attr,val in [("text_alcance",d[4]),("text_notas",d[5]),("text_comentarios",d[6]),("text_postventa",d[7]),("text_entrega",d[8]),("text_garantia",d[10]),("text_validez",d[15]),("text_fuerza",d[16]),("text_ley",d[17])]:
            w=getattr(self,attr); w.delete('1.0',tk.END)
            if val: w.insert('1.0',val)
        sym="$" if (d[14] or "USD")=="USD" else "MX$"
        for it in self.items: self.tree_items.insert('',tk.END,values=(it[0],it[1],f"{sym}{it[2]:,.2f}",f"{sym}{it[3]:,.2f}"))
        self._recalc()

    def _agregar_item(self): ItemDialog(self)
    def adicionar_item(self,desc,cant,pu,total):
        moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.items.append((desc,cant,pu,total)); self.tree_items.insert('',tk.END,values=(desc,cant,f"{sym}{pu:,.2f}",f"{sym}{total:,.2f}")); self._recalc()

    def _eliminar_item(self):
        sel=self.tree_items.selection()
        if not sel: return
        v=self.tree_items.item(sel[0])['values']
        for it in self.items:
            if str(it[0])==str(v[0]): self.items.remove(it); break
        self.tree_items.delete(sel[0]); self._recalc()

    def _recalc(self):
        total=sum(i[3] for i in self.items); moneda=self.moneda_var.get(); sym="$" if moneda=="USD" else "MX$"
        self.lbl_total.config(text=f"Total:  {sym}{total:,.2f} {moneda}")

    def _guardar(self):
        ps=self.combo_proyecto.get()
        if not ps: messagebox.showerror("Campo requerido","Seleccione un proyecto."); return
        pid=int(ps.split(' – ')[0]); moneda=self.moneda_var.get()
        def txt(attr): return getattr(self,attr).get('1.0',tk.END).strip()
        alcance=txt('text_alcance')
        if not alcance: messagebox.showerror("Campo requerido","El alcance técnico es obligatorio."); return
        total=sum(i[3] for i in self.items)
        self.db.connect()
        self.db.execute('UPDATE cotizaciones SET proyecto_id=?,alcance_tecnico=?,notas_importantes=?,comentarios_generales=?,servicio_postventa=?,condiciones_entrega=?,garantia=?,validez=?,fuerza_mayor=?,ley_aplicable=?,total=?,moneda=? WHERE id=?',
            (pid,alcance,txt('text_notas'),txt('text_comentarios'),txt('text_postventa'),txt('text_entrega'),txt('text_garantia'),txt('text_validez'),txt('text_fuerza'),txt('text_ley'),total,moneda,self.cot_id))
        self.db.execute("DELETE FROM items_cotizacion WHERE cotizacion_id=?",(self.cot_id,))
        for it in self.items: self.db.execute('INSERT INTO items_cotizacion (cotizacion_id,descripcion,cantidad,precio_unitario,total) VALUES(?,?,?,?,?)',(self.cot_id,it[0],it[1],it[2],it[3]))
        self.db.commit(); self.db.close()
        messagebox.showinfo("✔ Guardado",f"Cotización {self.data[1]} actualizada correctamente."); self.parent.refresh_list(); self.destroy()


# ══════════════════════════════════ MAIN ═════════════════════════════════════
if __name__ == "__main__":
    # 0. Cargar config de empresa
    EMP = _cargar_empresa()
    _sync_globals()

    # 1. Intentar conectar / crear tablas
    try:
        crear_tablas()
    except Exception:
        # No hay conexión — mostrar configurador primero
        cfg_root = tk.Tk(); cfg_root.withdraw()
        dlg = ConfigConexionDialog(cfg_root)
        cfg_root.wait_window(dlg)
        cfg_root.destroy()
        if not dlg._result:
            raise SystemExit("No se configuró la conexión a la BD.")
        crear_tablas()

    # 2. Pantalla de login con animaciones
    login = LoginWindow()
    login.mainloop()
    if not login._login_ok:
        raise SystemExit("Sesión cancelada.")

    # 3. Abrir aplicación principal con navbar + dashboard
    app = App()
    app.mainloop()
