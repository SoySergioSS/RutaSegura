"""Persistencia de reportes ciudadanos en SQLite."""
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

RUTA_DB = Path(__file__).resolve().parent / "data" / "focos.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS reportes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria       TEXT    NOT NULL,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    descripcion     TEXT    NOT NULL DEFAULT '',
    severidad       INTEGER NOT NULL DEFAULT 2 CHECK (severidad BETWEEN 1 AND 3),
    fecha_hecho     TEXT    NOT NULL,          -- ISO 8601
    hora_hecho      INTEGER,                   -- 0-23, solo incidentes
    creado_en       TEXT    NOT NULL,
    confirmaciones  INTEGER NOT NULL DEFAULT 0,
    votos_resuelto  INTEGER NOT NULL DEFAULT 0,
    estado          TEXT    NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','resuelto','descartado')),
    origen          TEXT    NOT NULL DEFAULT 'ciudadano',   -- 'ciudadano' | 'demo'
    autor_hash      TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_reportes_estado ON reportes(estado);

-- Un mismo dispositivo anonimo solo puede votar una vez por reporte
CREATE TABLE IF NOT EXISTS votos (
    reporte_id  INTEGER NOT NULL REFERENCES reportes(id),
    autor_hash  TEXT    NOT NULL,
    tipo        TEXT    NOT NULL CHECK (tipo IN ('confirmar','resuelto')),
    creado_en   TEXT    NOT NULL,
    PRIMARY KEY (reporte_id, autor_hash)
);
"""

VOTOS_PARA_RESOLVER = 3


def conectar():
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def hash_anonimo(token):
    """Nunca se guarda el token del dispositivo, solo un hash irreversible."""
    return hashlib.sha256(("focos-alerta:" + (token or "")).encode()).hexdigest()[:20]


def _a_dict(fila):
    r = dict(fila)
    r["fecha_hecho"] = datetime.fromisoformat(r["fecha_hecho"])
    r.pop("autor_hash", None)
    return r


def listar(con, solo_activos=True):
    sql = "SELECT * FROM reportes" + (" WHERE estado = 'activo'" if solo_activos else "")
    return [_a_dict(f) for f in con.execute(sql)]


def crear(con, datos, autor_hash):
    cur = con.execute(
        """INSERT INTO reportes (categoria, lat, lon, descripcion, severidad, fecha_hecho,
                                 hora_hecho, creado_en, origen, autor_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (datos["categoria"], datos["lat"], datos["lon"], datos.get("descripcion", ""),
         datos.get("severidad", 2), datos["fecha_hecho"], datos.get("hora_hecho"),
         datos.get("creado_en", datetime.now().isoformat(timespec="seconds")),
         datos.get("origen", "ciudadano"), autor_hash))
    con.commit()
    return cur.lastrowid


def reportes_recientes_de(con, autor_hash, desde_iso):
    return con.execute("SELECT COUNT(*) FROM reportes WHERE autor_hash = ? AND creado_en >= ?",
                       (autor_hash, desde_iso)).fetchone()[0]


def votar(con, reporte_id, autor_hash, tipo):
    """Registra un voto. Devuelve (ok, mensaje)."""
    fila = con.execute("SELECT autor_hash, estado FROM reportes WHERE id = ?", (reporte_id,)).fetchone()
    if fila is None:
        return False, "El reporte no existe."
    if fila["estado"] != "activo":
        return False, "El reporte ya no está activo."
    if fila["autor_hash"] == autor_hash and tipo == "confirmar":
        return False, "No puedes confirmar tu propio reporte."
    try:
        con.execute("INSERT INTO votos VALUES (?,?,?,?)",
                    (reporte_id, autor_hash, tipo, datetime.now().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        return False, "Ya votaste sobre este reporte."
    campo = "confirmaciones" if tipo == "confirmar" else "votos_resuelto"
    con.execute(f"UPDATE reportes SET {campo} = {campo} + 1 WHERE id = ?", (reporte_id,))
    con.execute("""UPDATE reportes SET estado = 'resuelto'
                   WHERE id = ? AND votos_resuelto >= ? AND votos_resuelto > confirmaciones""",
                (reporte_id, VOTOS_PARA_RESOLVER))
    con.commit()
    return True, "Gracias, tu voto fue registrado."
