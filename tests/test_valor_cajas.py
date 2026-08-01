"""
tests/test_valor_cajas.py
Verifica core/valor_cajas.py contra los ejemplos del prompt de valor de
cajas backlight. Usa catálogos fijos (no los de Dropbox/SGTD/Conf) para
que el test sea autocontenido — mismo criterio que tests/test_calculo_cajas.py
y tests/test_precios.py.

Correr con:  python -m unittest tests.test_valor_cajas -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.calculo_cajas import calcular_caja, seleccionar_fp
from core.valor_cajas import calcular_valor_caja, _tramo_armado

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

PRECIOS = {
    "luces": {
        "Basic 5": 14507, "Basic 3": 11196, "M12": 25488, "M9": 23269,
        "M6": 15513, "M3": 7756, "Malla 150": 40128, "Malla 12v": 25000,
    },
    "traseras": {"Trovicel 122": 5000, "Alucobond 122x244": 14040},
    "armado": {"minimo": 10000, "simple": 7000, "medio": 6000, "complejo": 5000, "jumbo": 4500},
    "fp": {35: 13992, 50: 13680, 75: 17628, 100: 18794, 150: 29089,
           200: 32296, 350: 40374, 450: 88472, 600: 110102},
    "perfiles": {
        "PERFIL 60 MM": 6974, "PERFIL 80 MM": 7995, "PERFIL 100 MM SIMPLE": 9830,
        "PERFIL 100 MM DOBLE": 11485, "PERFIL 120 MM DOBLE": 14000,
    },
    "pintura_por_ml": 4000,
}


def _fila_vacia(material, tipo=None):
    return {"material": material, "tipo": tipo, "cantidad_x_caja": 0,
            "cantidad_total": 0, "pendiente_manual": False}


class TestValorCajas(unittest.TestCase):

    def test_1_caja_completa_ejemplo_del_prompt(self):
        # 1.2 x 0.9, Cantidad 2, PERFIL 80 MM, luces default (Luces1=M12,
        # Luces2=sin luces) -> ml=4.2, tramo medio.
        materiales = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=2, perfil="PERFIL 80 MM",
            luces1="M12", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        self.assertEqual(materiales["mts_lineales_x_caja"], 4.2)

        valor = calcular_valor_caja(
            materiales, perfil="PERFIL 80 MM", precios=PRECIOS,
            otros_unit=0, cantidad=2,
        )
        self.assertEqual(valor["iluminacion"], 50976)   # 2 * 25488
        self.assertEqual(valor["traseras"], 5000)        # 1 * 5000
        self.assertEqual(valor["armado"], 25200)         # 6000 * 4.2
        self.assertEqual(valor["fp"], 13680)              # FP 50 * 1
        self.assertEqual(valor["perfil"], 33579)          # 7995 * 4.2
        self.assertEqual(valor["pintura"], 16800)         # 4.2 * 4000
        self.assertEqual(valor["otros"], 0)
        self.assertEqual(valor["valor_caja"], 145235)
        self.assertEqual(valor["valor_total"], 290470)

    def test_2_bordes_de_tramo_de_armado(self):
        self.assertEqual(_tramo_armado(0), None)
        self.assertEqual(_tramo_armado(1), "simple")
        self.assertEqual(_tramo_armado(4), "simple")
        self.assertEqual(_tramo_armado(4.01), "medio")
        self.assertEqual(_tramo_armado(6), "medio")
        self.assertEqual(_tramo_armado(7.99), "complejo")
        self.assertEqual(_tramo_armado(8), "jumbo")

    def _resultado_solo_fp(self, watts):
        fp_info = seleccionar_fp(watts, CATALOGO_FP)
        return {
            "filas": [
                _fila_vacia("Perfil", "PERFIL 60 MM"),
                _fila_vacia("Traseras", "Sin traseras"),
                _fila_vacia("Luces 1"),
                _fila_vacia("Luces 2"),
                {"material": "FP", "tipo": fp_info["nombre"],
                 "cantidad_x_caja": fp_info["cantidad"],
                 "cantidad_total": fp_info["cantidad"], "pendiente_manual": False},
            ],
            "fp": fp_info,
            "mts_lineales_x_caja": 0,
        }

    def test_3_fp_mayor_a_450w_multiplica_fp_350(self):
        r1 = self._resultado_solo_fp(679)
        v1 = calcular_valor_caja(r1, perfil="PERFIL 60 MM", precios=PRECIOS)
        self.assertEqual(v1["fp"], 80748)          # 2 * 40374
        self.assertEqual(v1["valor_caja"], 80748)  # ml=0 -> todo lo demás en 0

        r2 = self._resultado_solo_fp(1380.6)
        v2 = calcular_valor_caja(r2, perfil="PERFIL 60 MM", precios=PRECIOS)
        self.assertEqual(v2["fp"], 161496)         # 4 * 40374

    def test_4_perfil_doble_sin_traseras(self):
        # Perfil doble -> traseras_tipo() da "Sin traseras"; el componente
        # de traseras en el valor debe quedar en 0 sin importar cuánto
        # mida la caja.
        materiales = calcular_caja(
            ancho=1.5, alto=1.0, cantidad=1, perfil="PERFIL 100 MM DOBLE",
            luces1="M12", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        fila_traseras = next(f for f in materiales["filas"] if f["material"] == "Traseras")
        self.assertEqual(fila_traseras["tipo"], "Sin traseras")

        valor = calcular_valor_caja(materiales, perfil="PERFIL 100 MM DOBLE", precios=PRECIOS)
        self.assertEqual(valor["traseras"], 0)

    def test_5_otros_unit_se_suma_directo(self):
        materiales = calcular_caja(
            ancho=1.2, alto=0.9, cantidad=2, perfil="PERFIL 80 MM",
            luces1="M12", luces2="sin luces",
            catalogo_luces=CATALOGO_LUCES, catalogo_fp=CATALOGO_FP,
        )
        sin_otros = calcular_valor_caja(materiales, perfil="PERFIL 80 MM", precios=PRECIOS, otros_unit=0)
        con_otros = calcular_valor_caja(materiales, perfil="PERFIL 80 MM", precios=PRECIOS, otros_unit=12345)
        self.assertEqual(con_otros["valor_caja"] - sin_otros["valor_caja"], 12345)
        self.assertEqual(con_otros["otros"], 12345)


if __name__ == "__main__":
    unittest.main()
