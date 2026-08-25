"""
ui/api_historial_ops.py
Lógica de historial-ops.html — instanciada una sola vez por
ui.api_app.ApiApp (ver docstring de ese módulo).
"""

from datetime import datetime

from ui.api_ver_op import op_a_json
from core.repositorio_ops import listar_ops_del_mes, listar_todas_las_ops


def _clave_fecha_dma(fecha: str) -> int:
    """"23/08/2026" -> 20260823, para ordenar/comparar sin parsear fechas
    de verdad (mismo truco que ya usa demo.js::claveFecha)."""
    try:
        d, m, a = (int(x) for x in fecha.split("/"))
        return a * 10000 + m * 100 + d
    except (ValueError, AttributeError):
        return 0


def _clave_fecha_iso(fecha: str) -> int:
    """"2026-08-23" (input type=date) -> 20260823."""
    try:
        a, m, d = (int(x) for x in fecha.split("-"))
        return a * 10000 + m * 100 + d
    except (ValueError, AttributeError):
        return 0


def _tiene_material(op_json: dict, termino: str) -> bool:
    """Mismo criterio que demo.js::opTieneMaterial: para cada producto,
    candidatos = [tela, caja] si es backlight, [textil, *estructuras] si
    no — sensible a que `termino` aparezca como substring en cualquiera."""
    t = termino.lower()
    for p in op_json.get("productos", []):
        candidatos = (
            [p.get("tela", ""), p.get("caja", "")]
            if p.get("tipo") == "backlight"
            else [p.get("textil", ""), *p.get("estructuras", [])]
        )
        if any(c and t in c.lower() for c in candidatos):
            return True
    return False


class ApiHistorialOps:

    def contexto_extra(self) -> dict:
        hoy = datetime.now()
        return {"anio_actual": hoy.year, "mes_actual": hoy.month}

    def obtener_historial(self, anio, mes) -> list[dict]:
        """La "carpeta" de un año/mes puntual — ver
        core.repositorio_ops.listar_ops_del_mes."""
        crudos = [datos for datos, _origen in listar_ops_del_mes(int(anio), int(mes))]
        filas = [op_a_json(d) for d in crudos]
        filas.sort(key=lambda f: _clave_fecha_dma(f["fecha_entrega"]), reverse=True)
        return filas

    def buscar_historial(self, filtros: dict) -> list[dict]:
        """Cruza TODOS los meses — texto busca en número/nombre; cliente,
        material, desde/hasta son cada uno opcional y se combinan todos
        (Y, no O) — mismo criterio que demo.js::buscar_historial."""
        filtros = filtros or {}
        texto    = str(filtros.get("texto", "")).strip().lower()
        cliente  = str(filtros.get("cliente", "")).strip().lower()
        material = str(filtros.get("material", "")).strip()
        desde = _clave_fecha_iso(filtros["desde"]) if filtros.get("desde") else None
        hasta = _clave_fecha_iso(filtros["hasta"]) if filtros.get("hasta") else None

        resultado = []
        for datos in listar_todas_las_ops():
            if texto and not (
                texto in str(datos.get("Cotizacion", "")).lower()
                or texto in datos.get("Nombre", "").lower()
            ):
                continue
            if cliente and cliente not in datos.get("Empresa", "").lower():
                continue
            fila = op_a_json(datos)
            if material and not _tiene_material(fila, material):
                continue
            clave = _clave_fecha_dma(fila["fecha_entrega"])
            if desde is not None and clave < desde:
                continue
            if hasta is not None and clave > hasta:
                continue
            resultado.append(fila)

        resultado.sort(key=lambda f: _clave_fecha_dma(f["fecha_entrega"]), reverse=True)
        return resultado
