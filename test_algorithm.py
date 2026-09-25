"""Pruebas con asserts. Ejecutar: python test_algorithm.py"""

from itertools import combinations
from pathlib import Path
import sys

from ford_fulkerson import (
    agregar_arista, cargar_ejemplo, crear_nodos, ford_fulkerson,
    generar_grafo, preparar_red, validar_grafo,
)


def debe_fallar(funcion, *args):
    try:
        funcion(*args)
    except ValueError:
        return
    raise AssertionError("Se esperaba rechazar una entrada inválida.")


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

    def sin_errores():
        assert not app.exception, [e.message for e in app.exception]

    sin_errores()
    for ejemplo, esperado in [(1, 14), (2, 18), (3, 2)]:
        app.selectbox(key="ejemplo").select(ejemplo).run()
        app.button(key="cargar_ejemplo").click().run()
        sin_errores()
        app.button(key="iniciar").click().run()
        sin_errores()
        assert app.session_state["resultado"]["maximo"] == esperado
        assert app.session_state["paso"] == 0
        for _ in app.session_state["iteraciones"]:
            app.button(key="siguiente").click().run()
            sin_errores()
        app.radio(key="momento").set_value("Antes de actualizar").run()
        sin_errores()
        app.radio(key="momento").set_value("Después de actualizar").run()
        app.button(key="final").click().run()
        sin_errores()
        assert any(f"FLUJO MÁXIMO = {esperado}" in e.value for e in app.success)
        app.button(key="anterior").click().run()
        sin_errores()
    app.button(key="reiniciar").click().run()
    assert app.session_state["resultado"] is None
    app.button(key="iniciar").click().run()
    app.selectbox(key="sumidero_ui").select("A").run()
    sin_errores()
    assert app.session_state["resultado"] is None and app.error
    assert app.button(key="iniciar").disabled
    app.selectbox(key="sumidero_ui").select("G").run()
    app.button(key="iniciar").click().run()
    app.selectbox(key="arista_editar").set_value(("A", "B")).run()
    capacidad = next(w for w in app.number_input if w.label == "Nueva capacidad")
    capacidad.set_value(9).run()
    app.button(key="modificar").click().run()
    sin_errores()
    assert app.session_state["aristas"]["A", "B"] == 9
    assert app.session_state["resultado"] is None
    app.selectbox(key="origen_arista").select("G").run()
    app.selectbox(key="destino_arista").select("A").run()
    next(b for b in app.button if b.label == "Agregar arista").click().run()
    sin_errores()
    assert app.error and ("G", "A") not in app.session_state["aristas"]
    app.button(key="eliminar").click().run()
    sin_errores()
    assert ("A", "B") not in app.session_state["aristas"]
    app.number_input(key="n").set_value(6).run()
    sin_errores()
    assert app.error
    app.number_input(key="n").set_value(16).run()
    sin_errores()
    assert len(app.session_state["nodos"]) == 16
    app.radio(key="modo").set_value("Aleatorio").run()
    next(b for b in app.button if b.label == "Generar otro grafo").click().run()
    sin_errores()
    app.button(key="iniciar").click().run()
    sin_errores()
    app.button(key="final").click().run()
    sin_errores()
    assert app.success
    app.checkbox(key="multiples_ui").check().run()
    app.multiselect(key="fuentes_ui").set_value([]).run()
    sin_errores()
    assert app.error and app.session_state["resultado"] is None
    app.button(key="vaciar").click().run()
    sin_errores()
    assert not app.session_state["aristas"]
    print("OK: interfaz, tres ejemplos, navegación, reinicio, invalidación, edición, ciclos y generación con 16 nodos.")


if __name__ == "__main__":
    ejecutar_pruebas()
    if "--interfaz" in sys.argv:
        probar_interfaz()
