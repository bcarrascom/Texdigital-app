"""
tests/test_clientes_contactos.py
Gestión de clientes y contactos desde Configuración (core/repositorio.py):
alta, edición y baja con validación, y que las direcciones de un cliente lo
sigan si cambia de nombre o de RUT. Los archivos van a una carpeta temporal —
no toca Dropbox.

Correr con:  python -m unittest tests.test_clientes_contactos -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.repositorio as repo

RUT = "76.086.428-5"        # dígito verificador correcto
OTRO_RUT = "11.111.111-1"


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        for nombre, archivo in (("CLIENTES_PATH", "clientes.json"), ("CONTACTOS_PATH", "contactos.json"),
                                ("DIRECCIONES_PATH", "direcciones.json")):
            p = mock.patch.object(repo, nombre, self.base / archivo)
            p.start()
            self.addCleanup(p.stop)


class TestRut(unittest.TestCase):

    def test_digito_verificador(self):
        for bueno in (RUT, "760864285", OTRO_RUT, "12.345.678-5", "5.126.663-3", "10.000.013-K"):
            self.assertTrue(repo.rut_valido(bueno), bueno)
        for malo in ("76.086.428-4", "12.345.678-9", "", "K", "12K45-6"):
            self.assertFalse(repo.rut_valido(malo), malo)


class TestClientes(_Base):

    def test_crear_formatea_y_valida(self):
        self.assertEqual(repo.crear_cliente({"empresa": "  Café   del Puerto ", "rut": "760864285", "razon_social": "CDP SpA"}),
                         {"ok": True})
        self.assertEqual(repo.cargar_clientes(), [{"empresa": "Café del Puerto", "rut": RUT, "razon_social": "CDP SpA"}])

    def test_lo_que_no_se_deja_crear(self):
        repo.crear_cliente({"empresa": "Café del Puerto", "rut": RUT})
        casos = {
            "empresa": {"empresa": "café DEL puerto"},
            "rut": {"empresa": "Otra", "rut": "76.086.428-4"},
        }
        for campo, datos in casos.items():
            r = repo.crear_cliente(datos)
            self.assertIn(campo, r["errores"], campo)
        r = repo.crear_cliente({"empresa": "Otra", "rut": "760864285"})
        self.assertIn("Café del Puerto", r["errores"]["rut"])
        self.assertTrue(repo.crear_cliente({"empresa": "Sin RUT"})["ok"])   # el RUT es opcional

    def test_editar_se_lleva_sus_direcciones(self):
        repo.crear_cliente({"empresa": "Café del Puerto", "rut": RUT})
        repo.guardar_direccion(RUT, "Café del Puerto", calle="Matta", numero="500")
        r = repo.editar_cliente("café del puerto", {"empresa": "Café Puerto", "rut": OTRO_RUT, "razon_social": ""})
        self.assertEqual(r, {"ok": True, "direcciones": 1})
        d = repo.cargar_direcciones()[0]
        self.assertEqual((d["rut"], d["empresa"]), (OTRO_RUT, "Café Puerto"))
        self.assertEqual(len(repo.direcciones_de_cliente(OTRO_RUT)), 1)

    def test_con_direcciones_no_puede_quedar_sin_rut(self):
        repo.crear_cliente({"empresa": "Café del Puerto", "rut": RUT})
        repo.guardar_direccion(RUT, "Café del Puerto", calle="Matta", numero="500")
        r = repo.editar_cliente("Café del Puerto", {"empresa": "Café del Puerto", "rut": ""})
        self.assertIn("rut", r["errores"])

    def test_editar_no_choca_consigo_mismo(self):
        repo.crear_cliente({"empresa": "Café del Puerto", "rut": RUT})
        self.assertTrue(repo.editar_cliente("Café del Puerto", {"empresa": "Café del Puerto", "rut": RUT, "razon_social": "X"})["ok"])

    def test_eliminar_borra_sus_direcciones(self):
        repo.crear_cliente({"empresa": "Café del Puerto", "rut": RUT})
        repo.crear_cliente({"empresa": "Otra", "rut": OTRO_RUT})
        repo.guardar_direccion(RUT, "Café del Puerto", calle="Matta", numero="500")
        repo.guardar_direccion(OTRO_RUT, "Otra", calle="Prat", numero="1")
        self.assertEqual(repo.eliminar_cliente("Café del Puerto"), {"ok": True, "direcciones": 1})
        self.assertEqual([c["empresa"] for c in repo.cargar_clientes()], ["Otra"])
        self.assertEqual([d["empresa"] for d in repo.cargar_direcciones()], ["Otra"])
        self.assertFalse(repo.eliminar_cliente("Café del Puerto")["ok"])


class TestContactos(_Base):

    def test_crear_y_editar(self):
        self.assertTrue(repo.crear_contacto({"contacto": "Ana Pérez", "email": "ana@cdp.cl", "descuento": "10,5", "condicion": "30 días"})["ok"])
        self.assertEqual(repo.cargar_contactos(), [{"contacto": "Ana Pérez", "email": "ana@cdp.cl", "descuento": "10.5", "condicion": "30 días"}])
        self.assertTrue(repo.editar_contacto("ana pérez", {"contacto": "Ana Pérez", "email": "", "descuento": "", "condicion": ""})["ok"])
        self.assertEqual(repo.cargar_contactos()[0]["descuento"], "0")

    def test_lo_que_no_se_deja_guardar(self):
        repo.crear_contacto({"contacto": "Ana Pérez"})
        casos = {"contacto": {"contacto": "ANA PÉREZ"}, "email": {"contacto": "Otro", "email": "ana@cdp"},
                 "descuento": {"contacto": "Otro", "descuento": "100"}}
        for campo, datos in casos.items():
            self.assertIn(campo, repo.crear_contacto(datos)["errores"], campo)

    def test_eliminar(self):
        repo.crear_contacto({"contacto": "Ana Pérez"})
        self.assertTrue(repo.eliminar_contacto("Ana Pérez")["ok"])
        self.assertEqual(repo.cargar_contactos(), [])

    def test_el_descuento_guardado_con_el_nombre_viejo_se_lee(self):
        (self.base / "contactos.json").write_text(json.dumps(
            [{"contacto": "Viejo", "email": "", "fuente": "15", "condicion": ""}]), encoding="utf-8")
        self.assertEqual(repo.cargar_contactos()[0]["descuento"], "15")


if __name__ == "__main__":
    unittest.main()
