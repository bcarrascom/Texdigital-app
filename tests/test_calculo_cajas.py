"""
tests/test_calculo_cajas.py
Verifica core/calculo_cajas.py contra logica_cajas_backlight.md. Usa
catálogos fijos (no los de Dropbox/SGTD/Conf) para que el test sea
autocontenido y no dependa del estado de la máquina donde corre.

Correr con:  python -m unittest tests.test_calculo_cajas -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.calculo_cajas import (
    calcular_caja,
    lados_a_cubrir,
    luces1_default,
    luces_x_caja_grilla,
    plan_tiras,
    seleccionar_fp,
    traseras_tipo,
)

CATALOGO_LUCES = [
    {"corto": "Basic 5", "largo": "Basic led lateral 5F 5K, 53 cms max 500mm", "medida": 0.53, "watts": 15},
    {"corto": "Basic 3", "largo": "Basic led lateral 3F 5K, 33 cms max 500mm", "medida": 0.33, "watts": 9},
    {"corto": "M12", "largo": "Led Lateral Actilum M12 -6k, 90 cms max 1000mm", "medida": 0.6, "watts": 21},
    {"corto": "M9", "largo": "Led Lateral Actilum M9 -6k, 52 cms max 700mm", "medida": 0.52, "watts": 15},
    {"corto": "M6", "largo": "Led lateral Actilum M6 6k, 35 cms max 700mm", "medida": 0.35, "watts": 10},
    {"corto": "M3", "largo": "Led lateral Actilum M3 6k 19 cms. max 700 mm", "medida": 0.19, "watts": 5},
    {"corto": "Malla 150", "largo": "Malla Front Led 50x150 5k", "medida": 0.3, "watts": 6},
    {"corto": "Malla 12v", "largo": "Malla front led 12v 6000 k", "medida": 1, "watts": 120},
    {"corto": "sin luces", "largo": "sin luces", "medida": 0, "watts": 0},
]

CATALOGO_FP = [
    {"watts": 35, "nombre": "FP 35 watts- 24v MEAN WELL"},
    {"watts": 50, "nombre": "FP 50 watts- 24v MEAN WELL"},
    {"watts": 75, "nombre": "FP 75 watts- 24v MEAN WELL"},
    {"watts": 100, "nombre": "FP 100 watts- 24v MEAN WELL"},
    {"watts": 150, "nombre": "FP 150 watts- 24v MEAN WELL"},
    {"watts": 200, "nombre": "FP 200 watts- 24v MEAN WELL"},
    {"watts": 350, "nombre": "FP 350 watts - 24v MEAN WELL"},
    {"watts": 450, "nombre": "FP 450 watts-24v- MEAN WELL"},
    {"watts": 600, "nombre": "FP 600 watts-24v- MEAN WELL"},
]


def _fila(resultado, material):
    return next(f for f in resultado["filas"] if f["material"] == material)


class TestEjemploValidado(unittest.TestCase):
    """§9: caja 1.2×0.9, cantidad 2, PERFIL 80 MM, luces por defecto."""

    def setUp(self):
        self.luces1 = luces1_default("PERFIL 80 MM", 1.2, 0.9)
        self.r = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=2, perfil="PERFIL 80 MM",
            luces1=self.luces1, luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )

    def test_luces1_default_es_m12(self):
        self.assertEqual(self.luces1, "M12")

    def test_traseras_trovicel(self):
        self.assertEqual(_fila(self.r, "Traseras")["tipo"], "Trovicel 122")

    def test_traseras_redondeada_por_caja(self):
        # (1.2*0.9)/(1.22*2.44) = 0.3628... -> se redondea a 1 POR CAJA
        # (no se puede cortar 0.36 de una plancha), y de ahí sale el total.
        f = _fila(self.r, "Traseras")
        self.assertEqual(f["cantidad_x_caja"], 1)
        self.assertEqual(f["cantidad_total"], 2)  # 1 x caja * 2 cajas

    def test_perfil_x_caja(self):
        f = _fila(self.r, "Perfil")
        self.assertAlmostEqual(f["cantidad_x_caja"], 0.7)
        self.assertAlmostEqual(f["cantidad_total"], 1.4)

    def test_luces1_cantidad(self):
        f = _fila(self.r, "Luces 1")
        self.assertEqual(f["cantidad_x_caja"], 2)
        self.assertEqual(f["cantidad_total"], 4)

    def test_watts_y_fp(self):
        self.assertAlmostEqual(self.r["watts"], 42)
        self.assertEqual(self.r["fp"]["nombre"], "FP 50 watts- 24v MEAN WELL")
        self.assertEqual(self.r["fp"]["cantidad"], 1)


class TestUmbralLuces1Default(unittest.TestCase):

    def test_lado_corto_1_5_exacto_da_malla(self):
        self.assertEqual(luces1_default("PERFIL 80 MM", 2.0, 1.5), "Malla 150")

    def test_lado_corto_1_49_da_m12(self):
        self.assertEqual(luces1_default("PERFIL 80 MM", 2.0, 1.49), "M12")


class TestPerfil60mm(unittest.TestCase):

    def test_default_es_malla_150_con_cualquier_dimension(self):
        self.assertEqual(luces1_default("PERFIL 60 MM", 0.2, 0.2), "Malla 150")
        self.assertEqual(luces1_default("PERFIL 60 MM", 3.0, 3.0), "Malla 150")

    def test_lados_a_cubrir_siempre_1(self):
        self.assertEqual(lados_a_cubrir("PERFIL 60 MM", "M12", 0.2, 0.2), 1)
        self.assertEqual(lados_a_cubrir("PERFIL 60 MM", "sin luces", 3.0, 3.0), 1)
        self.assertEqual(lados_a_cubrir("PERFIL 60 MM", "Malla 150", 1.0, 1.0), 1)


class TestTraseras(unittest.TestCase):

    def test_perfil_doble_sin_traseras(self):
        self.assertEqual(traseras_tipo("PERFIL 100 MM DOBLE", "M12"), "Sin traseras")
        self.assertEqual(traseras_tipo("PERFIL 120 MM DOBLE", "Malla 150"), "Sin traseras")

    def test_luz_malla_sin_traseras(self):
        # Corrección sobre la versión original del MD: las mallas NUNCA
        # llevan traseras (la luz misma cubre el fondo), no "Alucobond".
        self.assertEqual(traseras_tipo("PERFIL 80 MM", "Malla 150"), "Sin traseras")
        self.assertEqual(traseras_tipo("PERFIL 100 MM SIMPLE", "Malla 12v"), "Sin traseras")

    def test_led_lateral_trovicel(self):
        self.assertEqual(traseras_tipo("PERFIL 80 MM", "M12"), "Trovicel 122")


class TestFP(unittest.TestCase):

    def test_watts_0_sin_fp(self):
        self.assertIsNone(seleccionar_fp(0, CATALOGO_FP))

    def test_42_watts_fp_50(self):
        fp = seleccionar_fp(42, CATALOGO_FP)
        self.assertEqual(fp["watts_unidad"], 50)
        self.assertEqual(fp["cantidad"], 1)

    def test_350_watts_fp_450(self):
        fp = seleccionar_fp(350, CATALOGO_FP)
        self.assertEqual(fp["watts_unidad"], 450)
        self.assertEqual(fp["cantidad"], 1)

    def test_451_watts_2x_fp_350(self):
        fp = seleccionar_fp(451, CATALOGO_FP)
        self.assertEqual(fp["watts_unidad"], 350)
        self.assertEqual(fp["cantidad"], 2)

    def test_750_watts_3x_fp_350(self):
        fp = seleccionar_fp(750, CATALOGO_FP)
        self.assertEqual(fp["watts_unidad"], 350)
        self.assertEqual(fp["cantidad"], 3)


class TestSinLucesEnAmbas(unittest.TestCase):

    def test_0_leds_0_watts_sin_fp(self):
        r = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=3, perfil="PERFIL 80 MM",
            luces1="sin luces", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        self.assertEqual(_fila(r, "Luces 1")["cantidad_x_caja"], 0)
        self.assertEqual(_fila(r, "Luces 2")["cantidad_x_caja"], 0)
        self.assertEqual(r["watts"], 0)
        self.assertIsNone(r["fp"])


class TestGrillaMallas(unittest.TestCase):

    def test_65x55_120_luces_12_tiras_fp_75(self):
        self.assertEqual(luces_x_caja_grilla(0.65, 0.55), 120)
        r = calcular_caja(
            ancho=0.65, alto=0.55, cantidad=1, perfil="PERFIL 80 MM",
            luces1="Malla 150", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "Luces 1")
        self.assertAlmostEqual(f["cantidad_x_caja"], 12.0)
        self.assertAlmostEqual(r["watts"], 72)
        self.assertEqual(r["fp"]["watts_unidad"], 75)

    def test_63x55_mismos_120_luces_12_tiras(self):
        self.assertEqual(luces_x_caja_grilla(0.63, 0.55), 120)
        r = calcular_caja(
            ancho=0.63, alto=0.55, cantidad=1, perfil="PERFIL 80 MM",
            luces1="Malla 150", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        self.assertAlmostEqual(_fila(r, "Luces 1")["cantidad_x_caja"], 12.0)

    def test_lado_menor_igual_10cm_da_n_1(self):
        self.assertEqual(luces_x_caja_grilla(0.05, 0.05), 1)
        self.assertEqual(luces_x_caja_grilla(0.10, 2.0), luces_x_caja_grilla(0.001, 2.0))


class TestPlanTiras(unittest.TestCase):

    def test_65x55_estrategia_optima(self):
        p = plan_tiras(0.65, 0.55)
        self.assertEqual(p["n_tiras"], 12)
        self.assertEqual(p["n_recortadas"], 0)

    def test_coordenadas_respetan_paso_y_bordes(self):
        p = plan_tiras(0.65, 0.55)
        xs = sorted({round(l["x"], 6) for l in p["luces"]})
        ys = sorted({round(l["y"], 6) for l in p["luces"]})
        # paso de 5 cm entre posiciones consecutivas
        for a, b in zip(xs, xs[1:]):
            self.assertAlmostEqual(b - a, 5.0, places=6)
        for a, b in zip(ys, ys[1:]):
            self.assertAlmostEqual(b - a, 5.0, places=6)
        # ninguna luz a más de 5 cm de un borde
        self.assertLessEqual(xs[0], 5.0 + 1e-9)
        self.assertLessEqual(p["ancho_cm"] - xs[-1], 5.0 + 1e-9)
        self.assertLessEqual(ys[0], 5.0 + 1e-9)
        self.assertLessEqual(p["alto_cm"] - ys[-1], 5.0 + 1e-9)
        # todas las luces dentro de la caja
        for l in p["luces"]:
            self.assertGreaterEqual(l["x"], 0)
            self.assertLessEqual(l["x"], p["ancho_cm"])
            self.assertGreaterEqual(l["y"], 0)
            self.assertLessEqual(l["y"], p["alto_cm"])


class TestMalla12v(unittest.TestCase):

    def test_sin_cantidad_manual_queda_pendiente(self):
        r = calcular_caja(
            ancho=1.0, alto=1.0, cantidad=1, perfil="PERFIL 80 MM",
            luces1="Malla 12v", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "Luces 1")
        self.assertTrue(f["pendiente_manual"])
        self.assertEqual(f["cantidad_x_caja"], 0)

    def test_con_cantidad_manual_watts_120_por_cantidad(self):
        r = calcular_caja(
            ancho=1.0, alto=1.0, cantidad=1, perfil="PERFIL 80 MM",
            luces1="Malla 12v", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
            cantidad_malla12v_1=2.5,
        )
        f = _fila(r, "Luces 1")
        self.assertFalse(f["pendiente_manual"])
        self.assertEqual(f["cantidad_x_caja"], 2.5)
        self.assertAlmostEqual(r["watts"], 120 * 2.5)


class TestRedondeoTrasteras(unittest.TestCase):
    """Traseras se corta de planchas enteras — no existe "0.4 planchas" —
    así que calcular_caja() redondea hacia arriba POR CAJA y de ahí saca el
    total. Redondear el total ya sumado (en vez de cada caja) da un número
    distinto y menor al real: con 2 cajas que necesitan 0.4 cada una, el
    total correcto es 1+1=2 planchas, no TECHO(0.4*2)=TECHO(0.8)=1."""

    def test_redondea_por_caja_no_el_total_ya_sumado(self):
        # (1.0*1.19)/(1.22*2.44) = 0.3998... por caja -> 1 x caja, no 0.4.
        r = calcular_caja(
            ancho=1.0, alto=1.19, cantidad=2, perfil="PERFIL 80 MM",
            luces1="sin luces", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "Traseras")
        self.assertEqual(f["cantidad_x_caja"], 1)
        self.assertEqual(f["cantidad_total"], 2)  # NO 1 (que daría redondear el total)

    def test_caja_grande_redondea_hacia_arriba(self):
        # 2.0 x 2.0 -> (2*2)/(1.22*2.44) = 1.3436... -> 2 x caja, no 1.34.
        r = calcular_caja(
            ancho=2.0, alto=2.0, cantidad=1, perfil="PERFIL 80 MM",
            luces1="sin luces", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        self.assertEqual(_fila(r, "Traseras")["cantidad_x_caja"], 2)

    def test_perfil_doble_sigue_en_cero(self):
        r = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=5, perfil="PERFIL 100 MM DOBLE",
            luces1="sin luces", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "Traseras")
        self.assertEqual(f["cantidad_x_caja"], 0)
        self.assertEqual(f["cantidad_total"], 0)

    def test_malla_150_sin_traseras(self):
        # Las mallas NUNCA llevan traseras, sin importar el tamaño de la caja.
        r = calcular_caja(
            ancho=2.0, alto=2.0, cantidad=3, perfil="PERFIL 80 MM",
            luces1="Malla 150", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "Traseras")
        self.assertEqual(f["tipo"], "Sin traseras")
        self.assertEqual(f["cantidad_x_caja"], 0)
        self.assertEqual(f["cantidad_total"], 0)

    def test_malla_12v_sin_traseras(self):
        r = calcular_caja(
            ancho=1.0, alto=1.0, cantidad=2, perfil="PERFIL 80 MM",
            luces1="Malla 12v", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
            cantidad_malla12v_1=5,
        )
        f = _fila(r, "Traseras")
        self.assertEqual(f["tipo"], "Sin traseras")
        self.assertEqual(f["cantidad_x_caja"], 0)
        self.assertEqual(f["cantidad_total"], 0)

    def test_fp_ya_era_entero(self):
        r = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=2, perfil="PERFIL 80 MM",
            luces1="M12", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        f = _fila(r, "FP")
        self.assertEqual(f["cantidad_x_caja"], 1)
        self.assertEqual(f["cantidad_total"], 2)


class TestPerfil60mmDefaultSinMedidas(unittest.TestCase):
    """El bug reportado: el default de Luces 1 para PERFIL 60 MM no debe
    necesitar Ancho/Alto (a diferencia del resto de los perfiles, ver §4) —
    la UI usa esto para fijarlo apenas se elige el perfil (ver
    es_perfil_60() e _actualizar_caja() en cotizador_backlight.py)."""

    def test_es_perfil_60_no_depende_de_mayusculas_ni_espacios(self):
        from core.calculo_cajas import es_perfil_60
        self.assertTrue(es_perfil_60("PERFIL 60 MM"))
        self.assertTrue(es_perfil_60("  PERFIL 60 MM  "))
        self.assertFalse(es_perfil_60("PERFIL 80 MM"))
        self.assertFalse(es_perfil_60(""))
        self.assertFalse(es_perfil_60(None))


if __name__ == "__main__":
    unittest.main()
