"""
core/reportes_inventario.py
Reportes mensuales de Inventario (pedido de Bruno, 2026-10-24): por cada
mes, cuánto se usó de cada textil y de cada material, cuánto quedó, y el
valor (precio de venta) de las dos cosas.

Un JSON por mes, en carpetas por año dentro de la carpeta de Inventario:

  reportes/2026/octubre-2026.json

El del mes en curso se vuelve a calcular cada vez que se abre la página de
reportes (ver actualizar_reportes). Uno de un mes que ya terminó se cierra:
la primera vez que se abre la página después de fin de mes se calcula una
última vez, con el mes completo, y queda marcado "cerrado" — desde ahí no
se toca más, aunque después cambie el inventario (un material que se borra,
un rollo al que se le cambia el valor). Es la foto de ese mes. Un mes con
datos que no tenga reporte (nadie abrió la página ese mes) se arma igual,
reconstruido desde los historiales.

Además del abrir la página: aprobar una cotización actualiza el reporte en
el momento (actualizar_reportes), y recotizar una OP —que devuelve su
consumo al stock— recalcula los reportes desde el mes en que se aprobó,
aunque estén cerrados (recalcular_desde).

Todo sale de los historiales de rollos y materiales, que guardan la
cantidad de antes y después de cada movimiento: con eso se puede saber
cuánto había cualquier día, sin haber guardado nunca una foto del stock.

Las cuatro cantidades de cada fila, en el orden en que pasan las cosas:
  "inicial"   lo que había al empezar el mes.
  "ingresado" lo que entró al stock: los rollos nuevos de ese textil (con
              los metros con que se cargaron) o los restocks del material,
              más los ajustes a mano que suman.
  "usado"     todo lo que salió del stock: lo consumido en OPs, los ajustes
              a mano que restan (merma, tela dañada, un recuento) y, en
              textiles, los metros que le quedaban a un rollo decomisionado.
  "restante"  lo que había al terminar el mes (o hoy, en el mes en curso).
Con eso inicial + ingresado − usado da siempre el restante.

El valor, igual para rollos y materiales (pedido de Bruno, 2026-10-24):
  "valores_vendidos" lo que se vendió: lo que COBRÓ la cotización por cada
                   consumo de OP (el "cobrado" que guardó la entrada al
                   aprobarla — decisión de Bruno, 2026-10-26; se revierte
                   con el consumo si la OP se recotiza), en las cuatro formas
                   de core.lista_precios.VARIANTES_COBRO: con y sin IVA, con
                   y sin descuento. La página de reportes deja elegir cuál
                   ver. Un consumo sin "cobrado" (anterior a esa fecha, o un
                   material que la cotización no cobró aparte) vale lo
                   consumido × lo que valía la cosa en ese momento, sin
                   descuento, y con el IVA de hoy en las formas "con IVA".
                   No sale de "usado": un ajuste que resta tela no es una
                   venta, así que gasta cantidad sin sumar valor.
  "valor_vendido"  el de "sin IVA, con descuento" (lo que de verdad entró,
                   neto), para quien lea el archivo sin elegir.
  "valor_restante" lo restante al valor que regía el último día del mes
                   (en el mes en curso, el de hoy), sacado de las entradas
                   tipo "precio" del historial.
Los consumos de rollos de antes de 2026-10-24 no guardaban su valor: se
valorizan con el que regía ese día según el historial de precios, y como
los rollos tampoco registraban sus cambios de valor hasta entonces, en la
práctica es el valor que tienen hoy.
"""

import json
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

from core.rutas import DATOS, _detectar_dropbox
from core import repositorio_inventario as _repo_inv
from core import repositorio_materiales as _repo_mat
from core.lista_precios import VARIANTES_COBRO, sumar_variantes, variantes

# La forma de "valores_vendidos" que va en "valor_vendido" (ver docstring).
VARIANTE_POR_DEFECTO = "sin_iva_con_descuento"
_CERO = {k: 0.0 for k in VARIANTES_COBRO}

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# "octubre-2026.json" — cualquier otro nombre en la carpeta (una copia en
# conflicto de Dropbox, un archivo puesto a mano) se ignora.
CANTIDADES = ("inicial", "ingresado", "usado", "restante")

_NOMBRE_ARCHIVO = re.compile(r"^(" + "|".join(MESES) + r")-(\d{4})\.json$")


def _ruta_base() -> Path:
    """La carpeta de Inventario — propia de este módulo, mismo criterio que
    core.repositorio_materiales._ruta_base."""
    dropbox = _detectar_dropbox()
    if dropbox:
        return dropbox / "SGTD" / "Inventario"
    return DATOS / "Inventario"


def carpeta_reportes() -> Path:
    p = _ruta_base() / "reportes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ruta_reporte(anio: int, mes: int) -> Path:
    return carpeta_reportes() / f"{anio:04d}" / f"{MESES[mes - 1]}-{anio:04d}.json"


def _fecha(texto) -> date | None:
    try:
        return datetime.strptime(texto or "", "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _limites(anio: int, mes: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def _cantidad_al(entradas: list[dict], dia: date, antes: str, despues: str, actual: float) -> float:
    """Cuánto había al terminar `dia`, desde un historial que guarda la
    cantidad de antes (`antes`) y de después (`despues`) de cada movimiento:
    lo que dejó el último movimiento hasta ese día; si todos son posteriores,
    lo que había antes del primero; sin movimientos, lo de hoy."""
    fechadas = [e for e in entradas if _fecha(e.get("fecha"))]
    hasta = [e for e in fechadas if _fecha(e.get("fecha")) <= dia]
    if hasta:
        return hasta[-1].get(despues, 0.0) or 0.0
    if fechadas:
        return fechadas[0].get(antes, 0.0) or 0.0
    return actual or 0.0


def _del_mes(entradas: list[dict], tipo: str, inicio: date, fin: date) -> list[dict]:
    return [e for e in entradas
            if e.get("tipo") == tipo and (f := _fecha(e.get("fecha"))) and inicio <= f <= fin]


def _movido(entradas: list[dict], antes: str, despues: str) -> float:
    """Lo que se movió en total en estas entradas (de antes a después), en
    positivo: lo consumido por los consumos, lo ingresado por los restocks."""
    return abs(sum((e.get(despues, 0.0) or 0.0) - (e.get(antes, 0.0) or 0.0) for e in entradas))


def _ajustes(entradas: list[dict], inicio: date, fin: date, antes: str, despues: str) -> tuple[float, float]:
    """(lo que restaron, lo que sumaron) los ajustes a mano del mes, los dos
    en positivo: lo primero es uso, lo segundo ingreso."""
    restado = sumado = 0.0
    for e in _del_mes(entradas, "ajuste", inicio, fin):
        delta = (e.get(despues, 0.0) or 0.0) - (e.get(antes, 0.0) or 0.0)
        if delta < 0:
            restado -= delta
        else:
            sumado += delta
    return restado, sumado


def _reporte_textiles(inicio: date, fin: date, iva_pct: float) -> list[dict]:
    """Una fila por textil, sumando sus rollos. Cuenta también los
    decomisionados: uno que se terminó a mitad de mes se usó ese mes."""
    from core.catalogo import nombre_textil

    por_textil: dict[str, dict] = {}
    for r in _repo_inv.listar_rollos() + _repo_inv.listar_decomisionados():
        ingreso = _fecha(r.get("fecha"))
        if ingreso and ingreso > fin:
            continue  # todavía no existía
        decomiso = _fecha(r.get("fecha_decomiso"))
        if decomiso and decomiso < inicio:
            continue  # ya no estaba
        usos = r.get("usos", [])
        antes, despues = "metros_restantes_anterior", "metros_restantes_nuevo"
        actual = r.get("metros_restantes", 0.0)
        # Un rollo entra entero el día que se carga (ver crear_rollo): esos
        # metros son lo que había antes de su primer movimiento. Si entró
        # este mes, al empezar el mes no estaba.
        if ingreso and ingreso >= inicio:
            inicial = 0.0
            ingresado = _cantidad_al(usos, ingreso - timedelta(days=1), antes, despues, actual)
        else:
            inicial = _cantidad_al(usos, inicio - timedelta(days=1), antes, despues, actual)
            ingresado = 0.0
        consumos = _del_mes(usos, "consumo", inicio, fin)
        restado, sumado = _ajustes(usos, inicio, fin, antes, despues)
        ingresado += sumado
        usado = _movido(consumos, antes, despues) + restado
        if decomiso and decomiso <= fin:
            # Lo que le quedaba al decomisionarlo sale del stock: es uso.
            usado += _cantidad_al(usos, decomiso, antes, despues, actual)
            restante = 0.0
        else:
            restante = _cantidad_al(usos, fin, antes, despues, actual)
        if not any((inicial, ingresado, usado, restante)):
            continue

        # Con el nombre actual: un decomisionado conserva el de antes de un
        # renombre (ver core.repositorio_inventario.renombrar_textil_rollos).
        nombre = nombre_textil(r.get("nombre_textil", "")) or "Sin textil"
        fila = por_textil.setdefault(nombre, {
            "nombre": nombre, "unidad": "m", "rollos": 0,
            "inicial": 0.0, "ingresado": 0.0, "usado": 0.0, "restante": 0.0,
            "valores_vendidos": dict(_CERO), "valor_restante": 0.0, "sin_valor": 0,
        })
        fila["rollos"] += 1
        fila["inicial"] += inicial
        fila["ingresado"] += ingresado
        fila["usado"] += usado
        fila["restante"] += restante
        vendidos, falta_vendido = _valor_vendido(usos, consumos, antes, despues, r.get("valor"), iva_pct)
        valor = _valor_al(usos, fin, r.get("valor"))
        fila["valores_vendidos"] = sumar_variantes(fila["valores_vendidos"], vendidos)
        if valor is not None:
            fila["valor_restante"] += restante * float(valor)
        if falta_vendido or (valor is None and restante > 0):
            fila["sin_valor"] += 1
    return sorted((_redondear(f) for f in por_textil.values()), key=lambda f: f["nombre"].lower())


def _valor_vendido(entradas: list[dict], consumos: list[dict], antes: str, despues: str,
                   actual: float | None, iva_pct: float) -> tuple[dict, bool]:
    """({variante: valor de lo consumido}, si a algo le faltó valor). Cada
    consumo vale lo que cobró la cotización ("cobrado", ver docstring del
    módulo); sin eso, lo consumido × lo que valía cuando se vendió: el
    valor_venta que guardó la entrada, o —en una entrada anterior a que
    existiera ese campo— el valor que regía ese día según el historial de
    precios (ver _valor_al)."""
    total, falta = dict(_CERO), False
    for e in consumos:
        if isinstance(e.get("cobrado"), dict):
            total = sumar_variantes(total, e["cobrado"])
            continue
        valor = e.get("valor_venta")
        if valor is None:
            valor = _valor_al(entradas, _fecha(e.get("fecha")), actual)
        if valor is None:
            falta = True
            continue
        total = sumar_variantes(total, variantes(_movido([e], antes, despues) * float(valor), 0.0, iva_pct))
    return total, falta


def _valor_al(entradas: list[dict], dia: date, actual: float | None) -> float | None:
    """El precio de venta que regía al terminar `dia`, desde las entradas
    tipo "precio" (mismo razonamiento que _cantidad_al)."""
    precios = [e for e in entradas if e.get("tipo") == "precio" and _fecha(e.get("fecha"))]
    hasta = [e for e in precios if _fecha(e.get("fecha")) <= dia]
    if hasta:
        return hasta[-1].get("valor_nuevo")
    if precios:
        return precios[0].get("valor_anterior")
    return actual


def _reporte_materiales(inicio: date, fin: date, iva_pct: float) -> list[dict]:
    """Una fila por material. Un material que se borró ya no está en
    ningún lado: no aparece en los meses que se calculen después."""
    filas = []
    for m in _repo_mat.listar_materiales():
        entradas = _repo_mat.historial_completo(m)
        fechas = [f for e in entradas if (f := _fecha(e.get("fecha")))]
        if fechas and min(fechas) > fin:
            continue  # todavía no existía
        antes, despues = "cantidad_anterior", "cantidad_nueva"
        actual = m.get("cantidad", 0.0)
        consumos = _del_mes(entradas, "consumo", inicio, fin)
        # Un material nuevo arranca con un restock desde 0, así que antes de
        # existir esto ya da 0: no hace falta mirar cuándo se creó.
        inicial = _cantidad_al(entradas, inicio - timedelta(days=1), antes, despues, actual)
        restado, sumado = _ajustes(entradas, inicio, fin, antes, despues)
        ingresado = _movido(_del_mes(entradas, "restock", inicio, fin), antes, despues) + sumado
        usado = _movido(consumos, antes, despues) + restado
        restante = _cantidad_al(entradas, fin, antes, despues, actual)
        if not any((inicial, ingresado, usado, restante)):
            continue

        vendidos, falta_vendido = _valor_vendido(entradas, consumos, antes, despues, m.get("valor"), iva_pct)
        valor = _valor_al(entradas, fin, m.get("valor"))
        sin_valor = 1 if falta_vendido or (valor is None and restante) else 0
        filas.append(_redondear({
            "nombre": m.get("nombre", ""), "unidad": "m" if m.get("tipo") == "metro" else "un.",
            "inicial": inicial, "ingresado": ingresado, "usado": usado, "restante": restante,
            "valores_vendidos": vendidos, "valor_restante": 0.0 if valor is None else restante * float(valor),
            "sin_valor": sin_valor,
        }))
    return filas


def _redondear(fila: dict) -> dict:
    for clave in CANTIDADES:
        fila[clave] = round(fila[clave], 3)
    fila["valores_vendidos"] = {k: round(v, 2) for k, v in fila["valores_vendidos"].items()}
    fila["valor_vendido"] = fila["valores_vendidos"][VARIANTE_POR_DEFECTO]
    fila["valor_restante"] = round(fila["valor_restante"], 2)
    return fila


def _totales(filas: list[dict]) -> dict:
    return {
        "valores_vendidos": {k: round(sum(f["valores_vendidos"][k] for f in filas), 2) for k in VARIANTES_COBRO},
        "valor_vendido":  round(sum(f["valor_vendido"] for f in filas), 2),
        "valor_restante": round(sum(f["valor_restante"] for f in filas), 2),
    }


def generar_reporte(anio: int, mes: int, hoy: date | None = None) -> dict:
    """El reporte de `anio`/`mes`, calculado ahora desde los historiales (no
    lo guarda). "cerrado" si el mes ya terminó."""
    hoy = hoy or date.today()
    inicio, fin = _limites(anio, mes)
    from core.reglas_cobro import cargar as reglas
    iva_pct = float(reglas()["iva"])   # solo para los consumos sin "cobrado"
    textiles = _reporte_textiles(inicio, fin, iva_pct)
    materiales = _reporte_materiales(inicio, fin, iva_pct)
    tot_textiles, tot_materiales = _totales(textiles), _totales(materiales)
    return {
        "anio":     anio,
        "mes":      mes,
        "cerrado":  fin < hoy,
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "totales": {
            "valores_vendidos": sumar_variantes(tot_textiles["valores_vendidos"], tot_materiales["valores_vendidos"]),
            "valor_vendido":  round(tot_textiles["valor_vendido"] + tot_materiales["valor_vendido"], 2),
            "valor_restante": round(tot_textiles["valor_restante"] + tot_materiales["valor_restante"], 2),
            "textiles": {
                **tot_textiles,
                **{clave: round(sum(f[clave] for f in textiles), 3) for clave in CANTIDADES},
            },
            "materiales": tot_materiales,
        },
        "textiles":   textiles,
        "materiales": materiales,
    }


def obtener_reporte(anio: int, mes: int) -> dict | None:
    try:
        anio, mes = int(anio), int(mes)
        if not 1 <= mes <= 12:
            return None
        return json.loads(ruta_reporte(anio, mes).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _guardar(reporte: dict) -> None:
    """Escribe el reporte solo si cambió algo más que la hora en que se
    calculó: abrir la página no reescribe un archivo idéntico, y así dos
    computadores que la abren a la vez no le dejan a Dropbox copias en
    conflicto de nada."""
    previo = obtener_reporte(reporte["anio"], reporte["mes"])
    sin_hora = lambda r: {k: v for k, v in (r or {}).items() if k != "generado"}
    if previo is not None and sin_hora(previo) == sin_hora(reporte):
        return
    ruta = ruta_reporte(reporte["anio"], reporte["mes"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")


def _primer_mes_con_datos() -> tuple[int, int] | None:
    """El mes del movimiento (o ingreso de rollo) más viejo de Inventario."""
    fechas = []
    for r in _repo_inv.listar_rollos() + _repo_inv.listar_decomisionados():
        fechas += [_fecha(r.get("fecha"))] + [_fecha(e.get("fecha")) for e in r.get("usos", [])]
    for m in _repo_mat.listar_materiales():
        fechas += [_fecha(e.get("fecha")) for e in _repo_mat.historial_completo(m)]
    fechas = [f for f in fechas if f]
    if not fechas:
        return None
    primera = min(fechas)
    return primera.year, primera.month


def actualizar_reportes(hoy: date | None = None) -> None:
    """Lo que pasa cada vez que se abre la página de reportes: recalcula el
    mes en curso, y cierra (calcula una última vez) los meses que terminaron
    y todavía no tienen su reporte cerrado. Un reporte cerrado no se vuelve
    a tocar. Se llama también al aprobar una cotización (ui/api_ver_
    cotizacion.py), para que el mes en curso cuente el consumo enseguida.
    Con Inventario apagado no hace nada."""
    if not _inventario_habilitado():
        return
    hoy = hoy or date.today()
    primero = _primer_mes_con_datos()
    anio, mes = primero if primero else (hoy.year, hoy.month)
    while (anio, mes) < (hoy.year, hoy.month):
        previo = obtener_reporte(anio, mes)
        if not (previo and previo.get("cerrado")):
            _guardar(generar_reporte(anio, mes, hoy))
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    _guardar(generar_reporte(hoy.year, hoy.month, hoy))


def recalcular_desde(fechas: list[str], hoy: date | None = None) -> None:
    """Vuelve a calcular y guardar los reportes desde el mes de la fecha
    (dd/mm/aaaa) más vieja de `fechas` hasta el mes en curso, CERRADOS
    INCLUIDOS — la única excepción a "un reporte cerrado no se toca"
    (pedido de Bruno, 2026-10-24): al recotizar una OP se revierte su
    consumo (ver core.repositorio_inventario.revertir_consumo_op), y el
    reporte del mes en que se aprobó tiene que dejar de contarla, igual que
    lo restante de los meses que siguen. Sin fechas que leer no hace nada.
    Con Inventario apagado tampoco."""
    if not _inventario_habilitado():
        return
    hoy = hoy or date.today()
    validas = [f for f in map(_fecha, fechas) if f]
    if not validas:
        return
    desde = min(validas)
    anio, mes = desde.year, desde.month
    while (anio, mes) <= (hoy.year, hoy.month):
        _guardar(generar_reporte(anio, mes, hoy))
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def _inventario_habilitado() -> bool:
    """Mismo interruptor que core.repositorio_inventario: con el módulo
    apagado, aprobar o recotizar no escribe reportes."""
    from core import config as _config
    return _config.MODULOS_HABILITADOS.get("inventario", True)


def listar_reportes() -> list[dict]:
    """[{"anio", "mes", "cerrado"}] de los reportes guardados, el más nuevo
    primero. Lee los archivos (son pocos: uno por mes)."""
    meses = []
    for archivo in carpeta_reportes().glob("*/*.json"):
        coincide = _NOMBRE_ARCHIVO.match(archivo.name)
        if not coincide:
            continue
        mes, anio = MESES.index(coincide.group(1)) + 1, int(coincide.group(2))
        reporte = obtener_reporte(anio, mes)
        if reporte is not None:
            meses.append({"anio": anio, "mes": mes, "cerrado": bool(reporte.get("cerrado"))})
    return sorted(meses, key=lambda m: (m["anio"], m["mes"]), reverse=True)
