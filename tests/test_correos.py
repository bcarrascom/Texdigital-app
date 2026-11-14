"""
tests/test_correos.py
Los correos de la app (core/correos.py y ui/api_correos.py): los ajustes de
Configuración › Correos, la plantilla, el modo de prueba, la contraseña y el
envío por SMTP. Los archivos van a una carpeta temporal, la contraseña a un
almacén de mentira y el SMTP es falso: no toca Dropbox, ni la contraseña
guardada en este computador, ni manda nada.

Correr con:  python -m unittest tests.test_correos -v
"""

import email
import json
import smtplib
import sys
from datetime import datetime
import tempfile
import unittest
from email import policy
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.ajustes_globales as ajustes_globales
import core.bandeja as bandeja
import core.correos as correos
import core.repositorio as repo
import ui.api_correos as api_correos

COTIZACION = {
    "Cotizacion": 1004, "Nombre": "Vitrinas tienda", "Fecha": "06/11/2026", "Empresa": "Galería Norte",
    "RUT": "76.086.428-5", "Razon Social": "Galería Norte SpA", "Contacto": "Rodrigo Pérez",
    "Email": "rperez@galerianorte.cl", "Total": 2861979, "productos": [],
}


class _Base(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.almacen = {}
        falso = mock.Mock(
            leer=lambda servicio, cuenta: self.almacen.get((servicio, cuenta)),
            guardar=lambda servicio, cuenta, clave: self.almacen.__setitem__((servicio, cuenta), clave),
            borrar=lambda servicio, cuenta: self.almacen.pop((servicio, cuenta), None),
            NoDisponible=Exception,
        )
        for objetivo, valor in ((ajustes_globales, ("_CONF_DIR", self.base / "Conf")),
                                (correos, ("_detectar_dropbox", lambda: self.base)),
                                (correos, ("credenciales", falso)),
                                (correos, ("prueba_forzada", lambda: False)),
                                (repo, ("CLIENTES_PATH", self.base / "clientes.json")),
                                (repo, ("CONTACTOS_PATH", self.base / "contactos.json")),
                                (bandeja, ("DATOS", self.base / "local")),
                                (bandeja, ("_al_cambiar", []))):
            p = mock.patch.object(objetivo, *valor)
            p.start()
            self.addCleanup(p.stop)


class TestAjustes(_Base):

    def test_de_fabrica(self):
        a = correos.cargar()
        self.assertFalse(a["cotizaciones"]["al_cliente"])   # hasta que Bruno los habilite
        self.assertEqual(a["cuenta"]["remitente"], "sistema@texdigital.cl")
        self.assertEqual(a["prueba"], {"activo": True, "direccion": "brosky.spam@gmail.com"})
        self.assertEqual(a["areas"], {"ops": [], "inventario": [], "despachos": []})
        self.assertEqual(correos.validar(a), {})

    def test_guardar_y_volver_a_leer(self):
        r = correos.guardar({
            "cuenta": {"nombre": "  Texdigital   SpA ", "puerto": "587"},
            "cotizaciones": {"asunto": "Cotización {numero}", "copia": [{"correo": " ventas@texdigital.cl "}]},
            "areas": {"ops": [{"correo": "produccion@texdigital.cl", "nombre": "Producción"}]},
        })
        self.assertEqual(r, {"ok": True})
        a = correos.cargar()
        self.assertEqual(a["cuenta"]["nombre"], "Texdigital SpA")
        self.assertEqual(a["cuenta"]["puerto"], 587)
        self.assertEqual(a["cuenta"]["remitente"], "sistema@texdigital.cl")   # lo que no se mandó sigue
        self.assertEqual(a["cotizaciones"]["copia"], [{"correo": "ventas@texdigital.cl", "nombre": ""}])
        self.assertEqual(a["areas"]["ops"], [{"correo": "produccion@texdigital.cl", "nombre": "Producción"}])

    def test_lo_que_no_se_deja_guardar(self):
        r = correos.guardar({
            "cuenta": {"remitente": "sistema", "puerto": "0"},
            "prueba": {"activo": True, "direccion": ""},
            "cotizaciones": {"asunto": " "},
            "areas": {"ops": [{"correo": "a@b.cl"}, {"correo": "A@B.cl"}], "inventario": [{"correo": "malo"}]},
        })
        self.assertFalse(r["ok"])
        self.assertEqual(set(r["errores"]), {"cuenta.remitente", "cuenta.puerto", "prueba.direccion",
                                             "cotizaciones.asunto", "areas.ops:1", "areas.inventario:0"})
        self.assertFalse((self.base / "Conf" / "correos.json").exists())

    def test_aviso_de_cotizacion_nueva_aparte_del_correo_al_cliente(self):
        a = correos.cargar()
        self.assertEqual(a["cotizaciones_nuevas"]["para"], [])
        self.assertIn("{numero}", a["cotizaciones_nuevas"]["asunto"])
        r = correos.guardar({"cotizaciones_nuevas": {"asunto": " ", "para": [{"correo": "x@y.cl"}, {"correo": "X@y.cl"}]}})
        self.assertEqual(set(r["errores"]), {"cotizaciones_nuevas.asunto", "cotizaciones_nuevas.para:1"})
        self.assertEqual(correos.guardar({"cotizaciones_nuevas": {"para": [{"correo": " ventas@texdigital.cl "}]}}), {"ok": True})
        a = correos.cargar()
        self.assertEqual(a["cotizaciones_nuevas"]["para"], [{"correo": "ventas@texdigital.cl", "nombre": ""}])
        self.assertEqual(a["cotizaciones"]["asunto"], correos.POR_DEFECTO["cotizaciones"]["asunto"])   # el del cliente no cambia

    def test_switches_de_los_correos_automaticos(self):
        self.assertTrue(correos.automatico_activo("cotizaciones"))
        correos.guardar({"automaticos": {"cotizaciones": False}})
        self.assertFalse(correos.automatico_activo("cotizaciones"))
        self.assertTrue(correos.automatico_activo("ops"))
        # El general apaga todo, y al volver a encenderlo cada parte sigue como estaba.
        correos.guardar({"automaticos": {"activo": False, "cotizaciones": True}})
        self.assertFalse(correos.automatico_activo("cotizaciones"))
        self.assertFalse(correos.automatico_activo("ops"))
        correos.guardar({"automaticos": {"activo": True}})
        self.assertTrue(correos.automatico_activo("cotizaciones") and correos.automatico_activo("ops"))

    def test_sin_modo_de_prueba_no_hace_falta_la_direccion(self):
        self.assertEqual(correos.guardar({"prueba": {"activo": False, "direccion": ""}}), {"ok": True})


class TestPlantilla(unittest.TestCase):

    def test_rellenar(self):
        valores = correos.valores_cotizacion(COTIZACION)
        self.assertEqual(correos.rellenar("Cotización {numero} - {cliente}", valores), "Cotización 1004 - Galería Norte")
        self.assertEqual(correos.rellenar("Total {total}, {no_existe}", valores), "Total $2.861.979, {no_existe}")

    def test_sin_contacto_saluda_a_la_empresa(self):
        self.assertEqual(correos.valores_cotizacion({**COTIZACION, "Contacto": ""})["contacto"], "Galería Norte")

    def test_nombre_del_adjunto(self):
        self.assertEqual(correos.nombre_adjunto(COTIZACION), "1004 • Vitrinas tienda Galería Norte.pdf")


class TestDestinatarios(_Base):

    def test_contacto_y_cliente_sin_repetir(self):
        repo.crear_cliente({"empresa": "Galería Norte", "rut": "76.086.428-5", "email": "compras@galerianorte.cl"})
        self.assertEqual(correos.destinatarios_sugeridos(COTIZACION), [
            {"origen": "contacto", "nombre": "Rodrigo Pérez", "correo": "rperez@galerianorte.cl"},
            {"origen": "cliente", "nombre": "Galería Norte", "correo": "compras@galerianorte.cl"},
        ])
        self.assertEqual(len(correos.destinatarios_sugeridos({**COTIZACION, "Email": "COMPRAS@galerianorte.cl"})), 1)

    def test_sin_correos_guardados(self):
        self.assertEqual(correos.destinatarios_sugeridos({**COTIZACION, "Email": ""}), [])

    def test_cliente_con_correo_malo_no_se_guarda(self):
        r = repo.crear_cliente({"empresa": "X", "email": "x@"})
        self.assertEqual(r, {"ok": False, "errores": {"email": "El correo no es válido."}})


class TestMensaje(_Base):

    def setUp(self):
        super().setUp()
        self.pdf = self.base / "c.pdf"
        self.pdf.write_bytes(b"%PDF-1.4 prueba")

    def _armar(self, ajustes):
        return correos.armar_mensaje(ajustes=ajustes, para=["rperez@galerianorte.cl"], copia=["ventas@texdigital.cl"],
                                     asunto="Cotización 1004", mensaje="Hola", adjunto=self.pdf, nombre_adjunto="1004.pdf")

    def test_modo_de_prueba_va_solo_a_la_direccion_de_prueba(self):
        msg, reales = self._armar(correos.cargar())
        self.assertEqual(reales, ["brosky.spam@gmail.com"])
        self.assertEqual(msg["To"], "brosky.spam@gmail.com")
        self.assertIsNone(msg["Cc"])
        self.assertEqual(msg["Subject"], "[Prueba] Cotización 1004")
        self.assertIn("Iba a: rperez@galerianorte.cl; con copia a: ventas@texdigital.cl", msg.get_body(("plain",)).get_content())

    def test_sin_modo_de_prueba(self):
        a = correos.cargar()
        a["prueba"]["activo"] = False
        msg, reales = self._armar(a)
        self.assertEqual(reales, ["rperez@galerianorte.cl", "ventas@texdigital.cl"])
        self.assertEqual((msg["To"], msg["Cc"], msg["Subject"]), ("rperez@galerianorte.cl", "ventas@texdigital.cl", "Cotización 1004"))
        self.assertEqual(msg["From"], "Texdigital <sistema@texdigital.cl>")
        adjuntos = [p for p in msg.iter_attachments()]
        self.assertEqual([(p.get_filename(), p.get_content()) for p in adjuntos], [("1004.pdf", b"%PDF-1.4 prueba")])


class TestEnviarCotizacion(_Base):
    """El envío de punta a punta, sin Edge: el PDF y el HTML son de mentira."""

    def setUp(self):
        super().setUp()
        correos.guardar({"cotizaciones": {"al_cliente": True}})
        self.guardada = dict(COTIZACION)
        self.html = self.base / "1004.html"
        self.html.write_text("<html>cotización</html>", encoding="utf-8")

        def documento(numero):
            return self.guardada, dict(self.guardada), self.html

        def pdf(ruta_html, destino, **_):
            Path(destino).write_bytes(b"%PDF-1.4")
            return Path(destino)

        def guardar(datos):
            self.guardada = datos

        for nombre, valor in (("_documento", documento), ("html_a_pdf", pdf), ("guardar_cotizacion", guardar),
                              ("cargar_cotizacion", lambda numero: self.guardada)):
            p = mock.patch.object(api_correos, nombre, valor)
            p.start()
            self.addCleanup(p.stop)
        self.enviados = []
        p = mock.patch.object(correos, "enviar", lambda msg, para, ajustes=None: self.enviados.append((msg, para)))
        p.start()
        self.addCleanup(p.stop)
        self.api = api_correos.ApiCorreos()
        bandeja.al_cambiar(api_correos.anotar_aviso)

    def _enviar(self, **cambios):
        d = {"para": ["rperez@galerianorte.cl"], "copia": [], "asunto": "Cotización 1004", "mensaje": "Hola", **cambios}
        return self.api.enviar_correo_cotizacion(1004, d)

    def test_queda_como_eml_y_anotado_en_la_cotizacion(self):
        r = self._enviar()
        self.assertTrue(r["ok"] and r["prueba"])
        self.assertEqual(r["a"], ["brosky.spam@gmail.com"])
        [(_, para)] = self.enviados
        self.assertEqual(para, ["brosky.spam@gmail.com"])
        eml = Path(r["archivo"])
        self.assertTrue(eml.is_file())
        self.assertTrue(eml.is_relative_to(self.base / "SGTD" / "Correos"))
        msg = email.message_from_bytes(eml.read_bytes(), policy=policy.default)
        self.assertEqual(msg["X-Destinatarios-Originales"], "rperez@galerianorte.cl")
        [registro] = self.guardada["Correos"]
        self.assertEqual(registro["para"], ["rperez@galerianorte.cl"])
        self.assertEqual(registro["huella"], correos.huella(self.html))
        self.assertNotIn("simulado", registro)

    def test_si_no_sale_no_se_anota(self):
        def falla(msg, para, ajustes=None):
            raise correos.ErrorEnvio("No se pudo conectar.")
        with mock.patch.object(correos, "enviar", falla):
            r = self._enviar()
        self.assertEqual(r, {"ok": False, "error": "No se pudo conectar."})
        self.assertNotIn("Correos", self.guardada)
        self.assertFalse(list((self.base / "SGTD" / "Correos").rglob("*.eml")))

    def test_sin_cambios_desde_el_ultimo_envio(self):
        self.assertFalse(self.api.preparar_correo_cotizacion(1004)["sin_cambios"])
        self._enviar()
        p = self.api.preparar_correo_cotizacion(1004)
        self.assertTrue(p["sin_cambios"])
        self.assertEqual(p["ultimo"]["para"], ["rperez@galerianorte.cl"])
        # La cotización cambia: el documento ya no es el mismo.
        self.html.write_text("<html>cotización editada</html>", encoding="utf-8")
        self.assertFalse(self.api.preparar_correo_cotizacion(1004)["sin_cambios"])

    def test_estado_del_envio_para_ver_cotizacion(self):
        with mock.patch.object(api_correos, "generar_html", lambda datos: self.html):
            self.assertEqual(api_correos.estado_envio(self.guardada), "sin_enviar")
            self._enviar()
            self.assertEqual(api_correos.estado_envio(self.guardada), "al_dia")
            self.html.write_text("<html>cotización editada</html>", encoding="utf-8")
            self.assertEqual(api_correos.estado_envio(self.guardada), "con_cambios")
            # Un envío simulado (de antes del 2026-11-10) no salió: no cuenta.
            self.assertEqual(api_correos.estado_envio({"Correos": [{"simulado": True, "huella": "x"}]}), "sin_enviar")

    def test_aviso_de_cotizacion_nueva(self):
        correos.guardar({"cotizaciones_nuevas": {"para": [{"correo": "ventas@texdigital.cl", "nombre": "Ventas"}]}})
        r = self.api.enviar_aviso_cotizacion_nueva(1004, ["ventas@texdigital.cl", "jefe@texdigital.cl"])
        self.assertTrue(r["ok"])
        # No sale en el momento: queda en la bandeja, y la bandeja lo envía.
        self.assertFalse(self.enviados)
        [item] = bandeja.pendientes()
        self.assertEqual(item["destinatarios"], ["brosky.spam@gmail.com"])
        self.assertEqual(item["meta"]["para"], ["ventas@texdigital.cl", "jefe@texdigital.cl"])
        self.assertEqual(bandeja.procesar(), 1)
        [(msg, para)] = self.enviados
        self.assertIn("Nueva cotización 1004 - Galería Norte", msg["Subject"])
        self.assertTrue(list((self.base / "SGTD" / "Correos").rglob("*Nueva cotización 1004 - Galería Norte - cotización nueva.eml")))
        # Queda anotado en la cotización, y no cuenta como envío al cliente.
        [aviso] = self.guardada["Avisos"]
        self.assertEqual((aviso["tipo"], aviso["estado"]), ("cotizacion_nueva", "enviado"))
        self.assertNotIn("Correos", self.guardada)

    def test_aviso_apagado_no_sale(self):
        correos.guardar({"automaticos": {"activo": False}})
        self.assertFalse(self.api.opciones_aviso("cotizaciones")["activo"])
        r = self.api.enviar_aviso_cotizacion_nueva(1004, ["ventas@texdigital.cl"])
        self.assertTrue(r["apagado"])
        self.assertFalse(bandeja.pendientes())

    def test_aviso_sin_destinatarios_o_con_uno_malo(self):
        self.assertEqual(self.api.enviar_aviso_cotizacion_nueva(1004, []), {"ok": False, "error": "Falta a quién enviarlo."})
        self.assertFalse(self.api.enviar_aviso_cotizacion_nueva(1004, ["malo"])["ok"])
        self.assertFalse(bandeja.pendientes())

    def test_lo_que_ven_las_listas_de_destinatarios(self):
        correos.guardar({"cotizaciones_nuevas": {"para": [{"correo": "ventas@texdigital.cl", "nombre": "Ventas"}]},
                         "cotizaciones": {"copia": [{"correo": "jefe@texdigital.cl", "nombre": "Jefe"},
                                                    {"correo": "VENTAS@texdigital.cl", "nombre": ""}]},
                         "areas": {"ops": [{"correo": "produccion@texdigital.cl", "nombre": "Producción"}]}})
        r = self.api.opciones_aviso("cotizaciones")
        self.assertEqual([f["correo"] for f in r["inscritos"]], ["ventas@texdigital.cl"])
        # Para sumar a alguien: los demás guardados en la app, sin los inscritos ni repetidos.
        self.assertEqual([f["correo"] for f in r["guardados"]], ["jefe@texdigital.cl", "produccion@texdigital.cl"])
        r = self.api.opciones_aviso("ops")
        self.assertEqual([f["correo"] for f in r["inscritos"]], ["produccion@texdigital.cl"])
        self.assertTrue(r["activo"])
        correos.guardar({"automaticos": {"ops": False}})
        self.assertFalse(self.api.opciones_aviso("ops")["activo"])

    def test_preparar_rellena_la_plantilla(self):
        p = self.api.preparar_correo_cotizacion(1004)
        self.assertEqual(p["asunto"], "Cotización 1004 - Galería Norte")
        self.assertIn("Hola Rodrigo Pérez:", p["mensaje"])
        self.assertIn("$2.861.979", p["mensaje"])
        self.assertEqual(p["sugeridos"][0]["correo"], "rperez@galerianorte.cl")

    def test_con_los_correos_a_clientes_desactivados_no_sale(self):
        correos.guardar({"cotizaciones": {"al_cliente": False}})
        r = self._enviar()
        self.assertFalse(r["ok"])
        self.assertIn("desactivados", r["error"])
        self.assertFalse(self.enviados)
        self.assertNotIn("Correos", self.guardada)

    def test_lo_que_no_se_deja_enviar(self):
        r = self._enviar(para=[], asunto="", mensaje=" ")
        self.assertEqual(set(r["errores"]), {"para", "asunto", "mensaje"})
        r = self._enviar(copia=["malo"])
        self.assertEqual(r["errores"], {"copia": "«malo» no es un correo válido."})
        self.assertNotIn("Correos", self.guardada)



class _SmtpFalso:
    """Lo mínimo de smtplib.SMTP_SSL: anota lo que pasa."""
    claves = {"sistema@texdigital.cl": "buena"}

    def __init__(self, servidor, puerto, timeout=None, context=None):
        self.servidor, self.puerto = servidor, puerto
        self.enviados = []
        _SmtpFalso.ultimo = self

    def login(self, usuario, clave):
        if self.claves.get(usuario) != clave:
            raise smtplib.SMTPAuthenticationError(535, b"Incorrect authentication data")

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.enviados.append((from_addr, to_addrs, msg["Subject"]))
        return {}

    def quit(self):
        pass

    close = quit


class TestSmtp(_Base):

    def setUp(self):
        super().setUp()
        p = mock.patch.object(correos.smtplib, "SMTP_SSL", _SmtpFalso)
        p.start()
        self.addCleanup(p.stop)

    def test_la_contrasena_se_prueba_antes_de_guardarla(self):
        with self.assertRaises(correos.ErrorEnvio) as e:
            correos.guardar_contrasena("mala")
        self.assertIn("no aceptó la contraseña", str(e.exception))
        self.assertIsNone(correos.contrasena())
        correos.guardar_contrasena("buena")
        self.assertEqual(correos.contrasena(), "buena")
        self.assertEqual(self.almacen, {("SistemaGestion-correo", "sistema@texdigital.cl"): "buena"})
        correos.olvidar_contrasena()
        self.assertIsNone(correos.contrasena())

    def test_sin_contrasena_no_se_envia(self):
        msg, para = correos.mensaje_de_prueba()
        with self.assertRaises(correos.ErrorEnvio) as e:
            correos.enviar(msg, para)
        self.assertIn("Falta la contraseña", str(e.exception))

    def test_envia_desde_la_casilla_de_la_app(self):
        correos.guardar_contrasena("buena")
        msg, para = correos.mensaje_de_prueba()
        self.assertEqual(para, ["brosky.spam@gmail.com"])
        correos.enviar(msg, para)
        smtp = _SmtpFalso.ultimo
        self.assertEqual((smtp.servidor, smtp.puerto), ("mail.texdigital.cl", 465))
        self.assertEqual(smtp.enviados, [("sistema@texdigital.cl", ["brosky.spam@gmail.com"],
                                          "Correo de prueba del Sistema de Gestión")])

    def test_cada_correo_que_sale_avisa_para_la_animacion(self):
        salieron = []
        aviso = lambda msg, para: salieron.append(1)
        correos.al_enviar(aviso)
        self.addCleanup(correos._al_enviar.remove, aviso)
        with self.assertRaises(correos.ErrorEnvio):   # sin contraseña no sale: no avisa
            correos.enviar(*correos.mensaje_de_prueba())
        self.assertEqual(salieron, [])
        self.almacen[("SistemaGestion-correo", "sistema@texdigital.cl")] = "buena"
        correos.enviar(*correos.mensaje_de_prueba())
        self.assertEqual(salieron, [1])
        # Una animación que falla no hace fallar el envío.
        def rota(msg, para):
            raise RuntimeError("sin ventana")
        correos.al_enviar(rota)
        self.addCleanup(correos._al_enviar.remove, rota)
        correos.enviar(*correos.mensaje_de_prueba())
        self.assertEqual(salieron, [1, 1])

    def test_sin_conexion(self):
        correos.guardar_contrasena("buena")
        def sin_red(*a, **k):
            raise OSError("sin red")
        with mock.patch.object(correos.smtplib, "SMTP_SSL", sin_red):
            with self.assertRaises(correos.ErrorEnvio) as e:
                correos.enviar(*correos.mensaje_de_prueba())
        self.assertIn("No se pudo conectar con mail.texdigital.cl", str(e.exception))


class TestDesarrollo(_Base):

    def test_la_version_de_desarrollo_siempre_esta_en_modo_de_prueba(self):
        correos.guardar({"prueba": {"activo": False}})
        self.assertFalse(correos.cargar()["prueba"]["activo"])
        with mock.patch.object(correos, "prueba_forzada", lambda: True):
            self.assertTrue(correos.cargar()["prueba"]["activo"])


if __name__ == "__main__":
    unittest.main()


class TestBandeja(_Base):
    """La bandeja de salida (core/bandeja.py): guarda, envía, reintenta."""

    def setUp(self):
        super().setUp()
        self.estados = []
        bandeja.al_cambiar(lambda item, estado: self.estados.append(estado))
        self.enviados = []
        self.falla = None

        def enviar(msg, para, ajustes=None):
            if self.falla:
                raise correos.ErrorEnvio(self.falla)
            self.enviados.append((msg["Subject"], para))
        p = mock.patch.object(correos, "enviar", enviar)
        p.start()
        self.addCleanup(p.stop)

    def _encolar(self, asunto="OP 1005 - Cliente"):
        msg, reales = correos.armar_mensaje(ajustes=correos.cargar(), para=["produccion@texdigital.cl"], copia=[],
                                            asunto=asunto, mensaje="Hola")
        return bandeja.encolar(msg, reales, {"tipo": "op_nueva", "numero": 1005, "asunto": asunto, "operacion": "op_nueva"})

    def test_guarda_primero_y_despues_envia(self):
        item = self._encolar()
        self.assertTrue((bandeja.carpeta() / f"{item['id']}.eml").is_file())
        self.assertEqual(self.estados, ["pendiente"])
        self.assertEqual(bandeja.procesar(), 1)
        self.assertEqual(self.enviados, [("[Prueba] OP 1005 - Cliente", ["brosky.spam@gmail.com"])])
        self.assertEqual(self.estados, ["pendiente", "enviado"])
        self.assertEqual(bandeja.pendientes(), [])
        self.assertFalse(list(bandeja.carpeta().iterdir()))
        self.assertTrue(list((self.base / "SGTD" / "Correos").rglob("*OP 1005 - Cliente - aprobación.eml")))

    def test_sin_internet_queda_y_se_reintenta(self):
        self._encolar()
        self.falla = "No se pudo conectar con mail.texdigital.cl."
        self.assertEqual(bandeja.procesar(), 0)
        self.assertEqual(bandeja.procesar(), 0)
        [item] = bandeja.pendientes()
        self.assertEqual((item["intentos"], item["error"]), (2, "No se pudo conectar con mail.texdigital.cl."))
        self.falla = None
        self.assertEqual(bandeja.procesar(), 1)
        self.assertEqual(self.estados, ["pendiente", "error", "error", "enviado"])
        self.assertEqual(bandeja.pendientes(), [])

    def test_el_estado_queda_en_la_op(self):
        ruta = self.base / "1005.json"
        ruta.write_text(json.dumps({"Cotizacion": 1005, "Empresa": "Cliente"}), encoding="utf-8")
        bandeja.al_cambiar(api_correos.anotar_aviso)
        with mock.patch.object(api_correos.repo_ops, "_ruta_de_op", lambda numero: ruta):
            self._encolar()
            self.falla = "Sin internet."
            bandeja.procesar()
            [aviso] = json.loads(ruta.read_text(encoding="utf-8"))["Avisos"]
            self.assertEqual((aviso["estado"], aviso["error"], aviso["intentos"]), ("error", "Sin internet.", 1))
            self.falla = None
            bandeja.procesar()
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        [aviso] = datos["Avisos"]
        self.assertEqual((aviso["estado"], aviso["error"]), ("enviado", None))
        self.assertEqual(api_correos.resumen_aviso(api_correos.ultimo_aviso(datos, "op_nueva"))["estado"], "enviado")

    def test_op_nueva_y_recotizada(self):
        op = {"Cotizacion": 1005, "Nombre": "Toldo", "Empresa": "Cliente", "Contacto": "Ana",
              "Fecha_ingreso": "13/11/2026", "Fecha_entrega": "20/11/2026", "productos": []}
        html = self.base / "op.html"
        html.write_text("<html>op</html>", encoding="utf-8")

        def pdf(ruta_html, destino, **_):
            Path(destino).write_bytes(b"%PDF-1.4")
            return Path(destino)
        api = api_correos.ApiCorreos()
        with mock.patch.object(api_correos, "cargar_op", lambda numero: op), \
             mock.patch.object(api_correos, "generar_html_op", lambda datos: html), \
             mock.patch.object(api_correos, "html_a_pdf", pdf):
            self.assertTrue(api.avisar_op_nueva(1005, ["produccion@texdigital.cl"])["ok"])
            self.assertTrue(api.avisar_op_recotizada(1005, ["produccion@texdigital.cl"], op)["ok"])
        bandeja.procesar()
        asuntos = [a for a, _ in self.enviados]
        self.assertEqual(asuntos, ["[Prueba] OP 1005 - Cliente", "[Prueba] OP 1005 recotizada - Cliente"])


class TestHistorial(_Base):
    """La copia de cada correo que sale: SGTD/Correos/<año>/<mes>/<asunto> - <operación>.eml."""

    def _msg(self, asunto="OP 1005 - Cliente", para=("produccion@texdigital.cl",)):
        msg, _ = correos.armar_mensaje(ajustes=correos.cargar(), para=list(para), copia=[], asunto=asunto, mensaje="Hola")
        return msg

    def test_nombre_carpeta_y_repetidos(self):
        hoy = datetime.now()
        a = correos.guardar_eml(self._msg('OP 1005 - Cliente: "A/B"'), "op_nueva")
        b = correos.guardar_eml(self._msg('OP 1005 - Cliente: "A/B"'), "op_nueva")
        self.assertEqual(a.parent, self.base / "SGTD" / "Correos" / f"{hoy:%Y}" / f"{hoy:%m}")
        self.assertEqual(a.name, "[Prueba] OP 1005 - Cliente A B - aprobación.eml")
        self.assertEqual(b.name, "[Prueba] OP 1005 - Cliente A B - aprobación (2).eml")

    def test_el_historial_lee_las_copias(self):
        correos.guardar_eml(self._msg("OP 1005 recotizada - Cliente"), "op_recotizada")
        correos.guardar_eml(self._msg("Nueva cotización 1004 - Galería"), "cotizacion_nueva")
        hoy = datetime.now()
        r = api_correos.ApiCorreos().historial_correos()
        self.assertEqual((r["anio"], r["mes"]), (hoy.year, hoy.month))
        self.assertEqual(r["meses"], [{"anio": hoy.year, "mes": hoy.month, "cantidad": 2}])
        por_operacion = {c["operacion"]: c for c in r["correos"]}
        self.assertEqual(set(por_operacion), {"recotización", "cotización nueva"})
        c = por_operacion["recotización"]
        # En modo de prueba: el asunto sin "[Prueba]" y a quién iba de verdad.
        self.assertEqual((c["asunto"], c["para"], c["prueba"]), ("OP 1005 recotizada - Cliente", ["produccion@texdigital.cl"], True))
        self.assertIsNotNone(correos.ruta_copia(c["archivo"]))

    def test_un_mes_sin_correos(self):
        self.assertEqual(api_correos.ApiCorreos().historial_correos(2020, 1)["correos"], [])

    def test_no_abre_nada_fuera_de_la_carpeta(self):
        (self.base / "SGTD" / "secreto.eml").parent.mkdir(parents=True, exist_ok=True)
        (self.base / "SGTD" / "secreto.eml").write_bytes(b"x")
        self.assertIsNone(correos.ruta_copia("../secreto.eml"))
        self.assertIsNone(correos.ruta_copia("2026/11/no-existe.eml"))

    def test_el_correo_de_prueba_queda_en_el_historial(self):
        self.almacen[(correos.SERVICIO_CREDENCIAL, "sistema@texdigital.cl")] = "x"
        with mock.patch.object(correos, "enviar", lambda msg, para, ajustes=None: None):
            self.assertTrue(api_correos.ApiCorreos().enviar_correo_de_prueba()["ok"])
        [c] = api_correos.ApiCorreos().historial_correos()["correos"]
        self.assertEqual(c["operacion"], "prueba")
