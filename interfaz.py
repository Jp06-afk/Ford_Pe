"""Auxiliares de la interfaz: estado, validaciones y presentación de resultados."""

from contextlib import contextmanager
from functools import partial

import streamlit as st

from ford_fulkerson import cargar_ejemplo, crear_nodos


# Todas las tablas de la práctica comparten estas opciones de presentación.
mostrar_tabla = partial(st.dataframe, hide_index=True, width="stretch")


@contextmanager
def mostrar_validacion(detener=False):
    """Muestra los ValueError de una interacción sin ocultar otros errores."""
    try:
        yield
    except ValueError as error:
        st.error(str(error))
        if detener:
            st.stop()


def invalidar_resultados():
    st.session_state.update(resultado=None, iteraciones=[], paso=0)


def reemplazar_red(nodos, aristas, fuentes=None, sumideros=None):
    estado = st.session_state
    estado.nodos, estado.aristas = nodos, aristas
    estado.fuentes = list(fuentes) if fuentes is not None else ([nodos[0]] if nodos else [])
    estado.sumideros = list(sumideros) if sumideros is not None else ([nodos[-1]] if nodos else [])
    estado.fuente = estado.fuentes[0] if estado.fuentes else None
    estado.sumidero = estado.sumideros[0] if estado.sumideros else None
    estado.multiples = len(estado.fuentes) > 1 or len(estado.sumideros) > 1
    # Se ejecuta antes de construir los selectores de terminales de esta pasada.
    claves = ("fuente_ui", "sumidero_ui", "fuentes_ui", "sumideros_ui", "multiples_ui",
              "origen_arista", "destino_arista", "capacidad_arista", "arista_editar",
              "seleccion", "momento")
    for clave in list(estado):
        if clave in claves or clave.startswith("editar_"):
            estado.pop(clave, None)
    estado.posiciones = {}
    estado.vista_canvas = None
    estado.revision_red = estado.get("revision_red", 0) + 1
    invalidar_resultados()


def cambiar_modo():
    if st.session_state.modo == "Crear grafo manual":
        reemplazar_red([], {}, [], [])


def crear_nodos_manuales():
    reemplazar_red(crear_nodos(st.session_state.n), {}, [], [])


def agregar_nodo_manual():
    estado = st.session_state
    if len(estado.nodos) < 16:
        estado.nodos = estado.nodos + [chr(ord("A") + len(estado.nodos))]
        estado.n = max(7, len(estado.nodos))
        invalidar_resultados()


def usar_ejemplo():
    reemplazar_red(*cargar_ejemplo(st.session_state.ejemplo))
    st.session_state.n = 7
    st.session_state.modo = "Ejemplo cargado"


def cambiar_n():
    try:
        nodos = crear_nodos(st.session_state.n)
    except ValueError:
        invalidar_resultados()
        return
    if not st.session_state.nodos:
        return
    aristas = {e: c for e, c in st.session_state.aristas.items()
               if e[0] in nodos and e[1] in nodos}
    reemplazar_red(nodos, aristas, [], [])


def mover_paso(destino):
    st.session_state.paso = destino


def texto_camino(camino):
    if not camino:
        return "—"
    return " → ".join([camino[0]["origen"]] + [p["destino"] for p in camino])


def tabla_etiquetas(nodos, etiquetas):
    filas = []
    for nodo in nodos:
        e = etiquetas.get(nodo)
        filas.append({"Nodo": nodo, "Predecesor": (e["predecesor"] or "—") if e else "Sin etiqueta",
                      "Signo": (e["signo"] or "—") if e else "—",
                      "Delta": ("∞" if e["delta"] is None else str(e["delta"])) if e else "—"})
    return filas


def tabla_historial(iteraciones):
    return [{"Iteración": p["numero"], "Camino aumentante": texto_camino(p["camino"]),
             "Delta": p["delta"], "Flujo agregado": f"+{p['agregado']}",
             "Flujo acumulado": p["total"]} for p in iteraciones]


def exportar_resultado(resultado):
    lineas = ["FORD-FULKERSON · RESULTADOS", f"Flujo máximo: {resultado['maximo']}",
              "Fuentes: " + ", ".join(resultado["fuentes"]),
              "Sumideros: " + ", ".join(resultado["sumideros"]), "", "ARISTAS (capacidad/flujo)"]
    for (u, v), c in sorted(resultado["capacidades"].items()):
        extra = " [conexión ficticia]" if "*" in u + v else ""
        lineas.append(f"{u} -> {v}: {c}/{resultado['flujo'][u, v]}{extra}")
    lineas.extend(["", "ITERACIONES"])
    for p in resultado["iteraciones"]:
        signos = ", ".join(f"{a['origen']}->{a['destino']} ({a['signo']})" for a in p["camino"])
        lineas.append(f"{p['numero']}: {texto_camino(p['camino'])}; Delta={p['delta']}; agregado=+{p['agregado']}; total={p['total']}; {signos}")
    corte = resultado["corte"]
    lineas.extend(["", "CORTE MÍNIMO", "S = {" + ", ".join(corte["S"]) + "}",
                   "T = {" + ", ".join(corte["T"]) + "}"])
    lineas.extend(f"{u} -> {v}: {c}" for (u, v), c in sorted(corte["aristas"].items()))
    lineas.append(f"Capacidad del corte: {corte['capacidad']} = flujo máximo: {resultado['maximo']}")
    return "\n".join(lineas)
