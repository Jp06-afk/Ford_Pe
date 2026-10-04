"""Pruebas con asserts. Ejecutar: python test_algorithm.py"""

from itertools import combinations
from pathlib import Path
import sys
from unittest import TestCase

from ford_fulkerson import (
    agregar_arista, cargar_ejemplo, crear_nodos, detectar_ciclo, ford_fulkerson,
    generar_grafo, preparar_red, validar_grafo,
)


def debe_fallar(funcion, *args):
    with TestCase().assertRaises(ValueError):
        funcion(*args)


def comprobar_factibilidad(resultado, flujo, valor):
    capacidades = resultado["capacidades"]
    assert set(flujo) == set(capacidades)
    for e, capacidad in capacidades.items():
        assert type(flujo[e]) is int and 0 <= flujo[e] <= capacidad
    for nodo in resultado["nodos"]:
        entrada = sum(f for (u, v), f in flujo.items() if v == nodo)
        salida = sum(f for (u, v), f in flujo.items() if u == nodo)
        balance = valor if nodo == resultado["fuente"] else -valor if nodo == resultado["sumidero"] else 0
        assert salida - entrada == balance, (nodo, entrada, salida)


def comprobar_resultado(resultado):
    assert resultado["maximo"] == resultado["corte"]["capacidad"]
    assert resultado["sumidero"] not in resultado["corte"]["S"]
    assert set(resultado["corte"]["aristas"]).issubset(resultado["originales"])
    comprobar_factibilidad(resultado, resultado["flujo"], resultado["maximo"])
    previo = 0
    for paso in resultado["iteraciones"]:
        comprobar_factibilidad(resultado, paso["flujo_antes"], previo)
        comprobar_factibilidad(resultado, paso["flujo_despues"], paso["total"])
        assert paso["total"] == previo + paso["delta"]
        assert paso["delta"] == min(paso["residual_antes"][p["origen"], p["destino"]]["capacidad"] for p in paso["camino"])
        for p in paso["camino"]:
            diferencia = paso["flujo_despues"][p["arista"]] - paso["flujo_antes"][p["arista"]]
            assert diferencia == (paso["delta"] if p["signo"] == "+" else -paso["delta"])
        previo = paso["total"]


def corte_por_enumeracion(nodos, capacidades, fuentes, sumideros):
    """Oráculo independiente: enumera cortes pequeños, sin resolver flujo."""
    intermedios = sorted(set(nodos) - set(fuentes) - set(sumideros))
    valores = []
    for cantidad in range(len(intermedios) + 1):
        for grupo in combinations(intermedios, cantidad):
            s = set(fuentes) | set(grupo)
            valores.append(sum(c for (u, v), c in capacidades.items() if u in s and v not in s))
    return min(valores)


def ejecutar_pruebas():
    nodos = crear_nodos(7)
    cadena = {(nodos[i], nodos[i + 1]): 3 + i for i in range(6)}
    simple = ford_fulkerson(nodos, cadena, ["A"], ["G"])
    assert simple["maximo"] == 3
    comprobar_resultado(simple)
    print("OK: red sencilla, capacidad, conservación y corte mínimo.")

    for numero, esperado in [(1, 14), (2, 18), (3, 2)]:
        datos = cargar_ejemplo(numero)
        resultado = ford_fulkerson(*datos)
        assert resultado["maximo"] == esperado
        assert len(resultado["iteraciones"]) > 1
        comprobar_resultado(resultado)
        assert resultado == ford_fulkerson(*datos), "El recorrido debe ser determinista."
        if numero == 2:
            assert "S*" in resultado["nodos"] and "T*" in resultado["nodos"]
        if numero == 3:
            inversa = resultado["iteraciones"][1]
            assert inversa["etiquetas"]["B"]["signo"] == "-"
            assert inversa["flujo_antes"]["B", "D"] == 1
            assert inversa["flujo_despues"]["B", "D"] == 0
        assert resultado["maximo"] == corte_por_enumeracion(*datos)
    print("OK: varias iteraciones, nodos ficticios y uso real de una arista inversa.")

    debe_fallar(agregar_arista, nodos, cadena, "G", "A", 1)
    debe_fallar(agregar_arista, nodos, cadena, "A", "B", 1)
    debe_fallar(agregar_arista, nodos, cadena, "A", "A", 1)
    for capacidad in [0, -1, 1.5, True, "5"]:
        debe_fallar(agregar_arista, nodos, {}, "A", "B", capacidad)
    for n in [6, 17, 7.5, True]:
        debe_fallar(crear_nodos, n)
    for fuentes, sumideros in [([], ["G"]), (["A"], []), (["A"], ["A"]),
                               (["A", "A"], ["G"]), (["A"], ["G", "G"]),
                               (["G"], ["A"]), (["Z"], ["G"]),
                               (["A", "B"], ["B", "G"])]:
        debe_fallar(preparar_red, nodos, cadena, fuentes, sumideros)
    debe_fallar(preparar_red, nodos, {}, ["A"], ["G"])
    debe_fallar(generar_grafo, 7, 0.5, 10, 2)
    parcial = agregar_arista(["A", "B"], {}, "A", "B", 4, en_construccion=True)
    parcial = agregar_arista(["A", "B"], parcial, "B", "A", 2, en_construccion=True)
    assert set(detectar_ciclo(["A", "B"], parcial)) == {("A", "B"), ("B", "A")}
    debe_fallar(ford_fulkerson, nodos, parcial, ["A"], ["B"])
    assert not detectar_ciclo(nodos, cadena)
    print("OK: ciclos, duplicados, autoaristas, capacidades y selecciones inválidas.")

    for semilla in range(30):
        n, c = generar_grafo(7, (semilla % 10) / 10, semilla=semilla)
        validar_grafo(n, c)
        for fuentes, sumideros in [(["A"], ["G"]), (["A", "B"], ["F", "G"]),
                                   (["A", "B"], ["G"]), (["A"], ["F", "G"])]:
            resultado = ford_fulkerson(n, c, fuentes, sumideros)
            comprobar_resultado(resultado)
            assert resultado["maximo"] == corte_por_enumeracion(n, c, fuentes, sumideros)
    for cantidad in [7, 16]:
        n, c = generar_grafo(cantidad, 1, semilla=0)
        comprobar_resultado(ford_fulkerson(n, c, [n[0]], [n[-1]]))
    print("OK: 120 redes/selecciones contrastadas con enumeración independiente de cortes; límites de 7 y 16 nodos.")
    print("Todas las pruebas pasaron.")


def probar_interfaz():
    """Prueba opcional de interacción, incluida en Streamlit: --interfaz."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=20).run()

    def interactuar(clave, valor=True):
        """Aplica un cambio, ejecuta la interfaz y comprueba las excepciones."""
        app.get_by_key(clave).set_value(valor).run()
        assert not app.exception, [e.message for e in app.exception]

    assert not app.exception, [e.message for e in app.exception]
    for ejemplo, esperado in [(1, 14), (2, 18), (3, 2)]:
        interactuar("ejemplo", ejemplo)
        interactuar("cargar_ejemplo")
        interactuar("iniciar")
        assert app.session_state["resultado"]["maximo"] == esperado
        assert app.session_state["paso"] == 0
        for _ in app.session_state["iteraciones"]:
            interactuar("siguiente")
        interactuar("momento", "Antes de actualizar")
        interactuar("momento", "Después de actualizar")
        interactuar("final")
        assert any(f"FLUJO MÁXIMO = {esperado}" in e.value for e in app.success)
        interactuar("anterior")
    interactuar("reiniciar")
    assert app.session_state["resultado"] is None
    interactuar("iniciar")
    interactuar("sumidero_ui", "A")
    assert app.session_state["resultado"] is None and app.error
    assert app.button(key="iniciar").disabled
    interactuar("sumidero_ui", "G")
    interactuar("iniciar")
    interactuar("arista_editar", ("A", "B"))
    capacidad = next(w for w in app.number_input if w.label == "Nueva capacidad")
    interactuar(capacidad.key, 9)
    interactuar("modificar")
    assert app.session_state["aristas"]["A", "B"] == 9
    assert app.session_state["resultado"] is None
    interactuar("origen_arista", "G")
    interactuar("destino_arista", "A")
    interactuar("FormSubmitter:nueva_arista-Agregar arista")
    assert app.error and ("G", "A") in app.session_state["aristas"]
    assert app.button(key="iniciar").disabled
    interactuar("arista_editar", ("G", "A"))
    interactuar("eliminar")
    assert not detectar_ciclo(app.session_state["nodos"], app.session_state["aristas"])
    assert not app.button(key="iniciar").disabled
    interactuar("arista_editar", ("A", "B"))
    interactuar("eliminar")
    assert ("A", "B") not in app.session_state["aristas"]
    interactuar("n", 6)
    assert app.error
    interactuar("n", 16)
    assert len(app.session_state["nodos"]) == 16
    interactuar("modo", "Aleatorio")
    interactuar("FormSubmitter:generador-Generar otro grafo")
    interactuar("iniciar")
    interactuar("final")
    assert app.success
    interactuar("multiples_ui")
    interactuar("fuentes_ui", [])
    assert app.error and app.session_state["resultado"] is None
    interactuar("vaciar")
    assert not app.session_state["aristas"]

    # Una red manual nueva debe olvidar incluso posiciones y widgets del ejemplo.
    interactuar("ejemplo", 2)
    interactuar("cargar_ejemplo")
    interactuar("iniciar")
    interactuar("final")
    interactuar("modo", "Crear grafo manual")
    for clave in ["nodos", "aristas", "fuentes", "sumideros", "iteraciones", "posiciones"]:
        assert not app.session_state[clave], clave
    assert app.session_state["fuente"] is None and app.session_state["sumidero"] is None
    assert app.session_state["resultado"] is None and app.session_state["paso"] == 0
    assert app.session_state["vista_canvas"] is None
    assert app.button(key="iniciar").disabled
    for _ in range(2):
        interactuar("agregar_nodo")
    app.selectbox(key="origen_arista").select("A")
    app.selectbox(key="destino_arista").select("B")
    app.number_input(key="capacidad_arista").set_value(8)
    interactuar("FormSubmitter:nueva_arista-Agregar arista")
    assert app.session_state["aristas"]["A", "B"] == 8
    assert app.button(key="iniciar").disabled  # Todavía hay menos de siete nodos.
    for _ in range(5):
        interactuar("agregar_nodo")
    app.selectbox(key="fuente_ui").select("A")
    interactuar("sumidero_ui", "B")
    assert not app.button(key="iniciar").disabled
    interactuar("iniciar")
    interactuar("final")
    assert app.session_state["resultado"]["maximo"] == 8
    final = next(df.value for df in app.dataframe if "Capacidad/Flujo" in df.value.columns)
    assert final.iloc[0]["Capacidad/Flujo"] == "8/8"
    for _ in range(9):
        interactuar("agregar_nodo")
    assert app.button(key="agregar_nodo").disabled and len(app.session_state["nodos"]) == 16
    interactuar("n", 17)
    assert app.error
    interactuar("n", 7)
    interactuar("nueva_manual")
    assert not app.session_state["nodos"]
    interactuar("crear_nodos")
    assert app.session_state["nodos"] == crear_nodos(7) and not app.session_state["aristas"]
    print("OK: interfaz, ejemplos, reinicio manual completo, creación incremental, límites 7/16, edición, bloqueo de ciclos y resultados.")


if __name__ == "__main__":
    ejecutar_pruebas()
    if "--interfaz" in sys.argv:
        probar_interfaz()
