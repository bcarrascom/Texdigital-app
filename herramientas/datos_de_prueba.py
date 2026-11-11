"""Material de prueba con stock casi ilimitado, para probar aprobar y recotizar
sin quedarse sin tela ni materiales (pedido de Bruno, 2026-11-11).

Solo en DropboxDev: se niega a correr si la app no está en modo desarrollo.

    py herramientas/datos_de_prueba.py                 crea lo que falte
    py herramientas/datos_de_prueba.py --cotizaciones  y además dos cotizaciones nuevas

Se puede volver a correr: lo que ya existe no se repite (las cotizaciones sí:
cada vez, dos más). Lo que crea está anotado en CLAUDE.md ("Material de prueba")."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import rutas

if "DropboxDev" not in str(rutas._detectar_dropbox()):
    raise SystemExit("No es DropboxDev: esto solo corre con la app en modo desarrollo.")

from core import catalogo

catalogo.refrescar()
from core import repositorio as repo
from core import repositorio_inventario as repo_inv
from core import repositorio_materiales as repo_mat
from core.repositorio_cotizaciones import siguiente_numero
from ui.api_configuracion import ApiConfiguracion
from ui.api_cotizacion import ApiCotizacion
from ui.api_inventario import ApiInventario

STOCK = 1_000_000
TEXTIL = "Textil de prueba"            # ancho 1,6 m, $5.000 el metro
PRODUCTO = "Producto de prueba"
ESTRUCTURA = "Estructura de prueba"    # un., $10.000 (se cobra por su material)
TERMINACION = "Terminación de prueba"  # un., $2.000
MAT_UNIDAD = "Material de prueba por unidad"  # 2 por cada Producto de prueba, $1.000 c/u
MAT_METRO = "Material de prueba por metro"    # el alto de cada pieza con Estructura de prueba, $500 el metro
CLIENTE, CONTACTO = "Cliente de prueba", "Contacto de prueba"

conf, inv = ApiConfiguracion(), ApiInventario()


def paso(nombre, r):
    print(f"  {nombre}: {r}")
    if isinstance(r, dict) and r.get("ok") is False:
        raise SystemExit(f"Falló: {nombre}")


# ── Configuración ──────────────────────────────────────────────────────────
if TEXTIL not in [t["nombre"] for t in catalogo.textiles()]:
    paso("textil", conf.agregar_textil({"nombre": TEXTIL, "ancho": 1.6, "backlight": False, "valor": 5000}))
if PRODUCTO not in repo.PRODUCTOS:
    paso("producto", conf.agregar_producto({"nombre": PRODUCTO}))
for tipo, nombre, valor in (("estructuras", ESTRUCTURA, 10000), ("terminaciones", TERMINACION, 2000)):
    if nombre not in [c["nombre"] for c in catalogo.componentes(tipo)]:
        paso(tipo, conf.agregar_componente(tipo, {"nombre": nombre, "unidad": "un.", "valor": valor}))
catalogo.refrescar()

if not any(c["empresa"] == CLIENTE for c in repo.cargar_clientes()):
    paso("cliente", conf.crear_cliente({"empresa": CLIENTE, "rut": "11.111.111-1",
                                        "razon_social": "Cliente de Prueba SpA", "email": "cliente.prueba@ejemplo.cl"}))
if not any(c["contacto"] == CONTACTO for c in repo.cargar_contactos()):
    paso("contacto", conf.crear_contacto({"contacto": CONTACTO, "email": "contacto.prueba@ejemplo.cl",
                                          "descuento": "0", "condicion": "30 días"}))

# ── Inventario ─────────────────────────────────────────────────────────────
rollos = [r for r in repo_inv.listar_rollos() if r.get("nombre_textil") == TEXTIL]
if not rollos:
    r = inv.crear_rollo(TEXTIL, STOCK, precio_compra=1000, valor=5000, proveedor="")
    print("  rollo:", r.get("id"), r.get("metros_restantes"), r.get("estado"))
else:
    print("  rollo ya existe:", [(r["id"], r.get("metros_restantes"), r.get("estado")) for r in rollos])

existentes = {m["nombre"] for m in repo_mat.listar_materiales()}
if MAT_UNIDAD not in existentes:
    m = inv.ingresar_material(MAT_UNIDAD, STOCK, tipo="unidad", costo_unitario=100, valor=1000,
                              tipo_consumo="fijo_por_producto", consumo_parametros={"n": 2},
                              productos_asociados=[PRODUCTO], estructuras_asociadas=[])
    print("  material:", m["nombre"], m.get("cantidad"))
if MAT_METRO not in existentes:
    m = inv.ingresar_material(MAT_METRO, STOCK, tipo="metro", costo_unitario=50, valor=500,
                              tipo_consumo="metro_lineal_directo", consumo_parametros={},
                              productos_asociados=[], estructuras_asociadas=[ESTRUCTURA])
    print("  material:", m["nombre"], m.get("cantidad"))


# ── Cotizaciones ───────────────────────────────────────────────────────────
def est(producto, ancho, alto, cantidad, estructuras=(), terminaciones=(), tiro_retiro=False, tema=""):
    return {"tipo": "estandar", "producto": producto, "textil": TEXTIL,
            "impresion": "Tiro y retiro" if tiro_retiro else "Cara única",
            "estructuras": list(estructuras), "terminaciones": list(terminaciones),
            "ancho": str(ancho), "alto": str(alto), "cantidad": str(cantidad),
            "tema": tema, "obs": "", "forzar": False, "calc": None}


COTIZACIONES = [
    {"nombre": "Prueba inventario A",
     "descripcion": "Prueba: material de prueba con stock ilimitado (producto y estructura)",
     "productos": [
         est(PRODUCTO, 1.0, 2.0, 5, estructuras=[ESTRUCTURA], terminaciones=[TERMINACION], tema="Con estructura"),
         est(PRODUCTO, 0.5, 0.5, 10, terminaciones=[TERMINACION], tema="Sin estructura"),
     ]},
    {"nombre": "Prueba inventario B",
     "descripcion": "Prueba: material de prueba con stock ilimitado (tiro y retiro, despacho)",
     "despacho": 10000,
     "productos": [
         est(PRODUCTO, 1.5, 1.0, 3, estructuras=[ESTRUCTURA], tiro_retiro=True, tema="Tiro y retiro"),
     ]},
]

if "--cotizaciones" in sys.argv:
    cli = next(c for c in repo.cargar_clientes() if c["empresa"] == CLIENTE)
    cont = next(c for c in repo.cargar_contactos() if c["contacto"] == CONTACTO)
    for c in COTIZACIONES:
        numero = siguiente_numero()
        estado = {
            "id": None, "nombre_trabajo": c["nombre"],
            "despacho": c.get("despacho"), "instalacion": c.get("instalacion"),
            "cliente": {"empresa": cli["empresa"], "rut": cli["rut"], "razon_social": cli["razon_social"],
                        "contacto": cont["contacto"], "email": cont["email"],
                        "descuento": cont.get("descuento") or "0", "condicion": cont["condicion"],
                        "fecha": date.today().isoformat(), "numero": str(numero), "descripcion": c["descripcion"]},
            "productos": c["productos"], "actual": 0,
        }
        print(f"  cotización {numero}:", ApiCotizacion().guardar_cotizacion(estado))
