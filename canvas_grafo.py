"""Figuras Plotly, posiciones persistentes y enlace con los gestos del canvas."""

import json
import math
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
import streamlit as st
import streamlit.components.v2 as components


# Plotly se sirve desde el paquete instalado; el canvas funciona sin CDN.
GESTOS = Path(__file__).with_name("canvas_gestos.js").read_text(encoding="utf-8")

_CANVAS = components.component(
    "ford_fulkerson_canvas",
    html='<div class="ff-plot" role="img" aria-label="Red dirigida interactiva"></div>',
    css="""
    .ff-plot { width: 100%; height: 480px; touch-action: none; user-select: none; cursor: grab; }
    """,
    js=get_plotlyjs() + GESTOS,
    # Plotly inserta sus estilos SVG en document; necesita ese mismo ámbito.
    isolate_styles=False,
)


def guardar_canvas(clave):
    estado = st.session_state
    cambio = estado.get(clave, {}).get("cambio")
    if not cambio or cambio.get("revision") != estado.revision_red:
        return
    posiciones, vista = cambio.get("posiciones", {}), cambio.get("vista", {})
    pares = list(posiciones.values()) + [vista.get("x", []), vista.get("y", [])]
    if not all(isinstance(p, list) and len(p) == 2 and
               all(type(v) in (int, float) and math.isfinite(v) for v in p) for p in pares):
        return
    if vista["x"][0] >= vista["x"][1] or vista["y"][0] >= vista["y"][1]:
        return
    for nodo, posicion in posiciones.items():
        if nodo in estado.posiciones:
            estado.posiciones[nodo] = posicion
    estado.vista_canvas = vista


def centrar_canvas():
    st.session_state.vista_canvas = None


def mostrar_canvas(figura, key):
    estado = st.session_state
    puntos = list(figura.layout.meta["posiciones"].values()) or [(0, 0)]
    vista = estado.vista_canvas or {
        "x": [min(-1, min(p[0] for p in puntos)) - .22, max(1, max(p[0] for p in puntos)) + .22],
        "y": [min(-1, min(p[1] for p in puntos)) - .22, max(1, max(p[1] for p in puntos)) + .22],
    }
    clave = f"canvas_{key}_{estado.revision_red}"
    _CANVAS(data={"figura": json.loads(figura.to_json()), "vista": vista,
                  "revision": estado.revision_red}, key=clave, height=480, width="stretch",
            on_cambio_change=lambda: guardar_canvas(clave))
    st.button("Centrar vista", key=f"centrar_{key}", on_click=centrar_canvas)
    st.caption("Arrastra el fondo con clic izquierdo o derecho para mover la vista; arrastra un nodo para moverlo. "
               "Rueda: zoom. En móvil: un dedo desplaza y dos dedos amplían o reducen.")


@st.cache_data(max_entries=24, show_spinner=False)
def obtener_posiciones(nodos, aristas):
    grafo = nx.DiGraph()
    grafo.add_nodes_from(nodos)
    grafo.add_edges_from(aristas)
    posiciones = nx.spring_layout(grafo, seed=21, k=1.2, iterations=120)
    return {nodo: (float(p[0]), float(p[1])) for nodo, p in posiciones.items()}


def posiciones_actuales(nodos, aristas):
    iniciales = obtener_posiciones(tuple(nodos), tuple(sorted(aristas)))
    posiciones = st.session_state.posiciones
    for nodo in nodos:
        posiciones.setdefault(nodo, iniciales[nodo])
    return {nodo: posiciones[nodo] for nodo in nodos}


def dibujar_grafo(nodos, capacidades, posiciones, fuentes, sumideros,
                  flujo=None, residual=None, camino=None, corte=None, etiquetas=None,
                  mostrar_valores=True, ciclo=None):
    figura = go.Figure()
    pasos = camino or []
    recorrido = {(p["origen"], p["destino"]) for p in pasos}
    originales_camino = {p["arista"] for p in pasos}
    aristas = residual if residual is not None else capacidades
    geometria = []
    for (u, v), dato in sorted(aristas.items()):
        inversa = residual is not None and dato["signo"] == "-"
        actual = (u, v) in (recorrido if residual is not None else originales_camino)
        saturada = flujo is not None and residual is None and flujo[u, v] == capacidades[u, v]
        en_corte = corte is not None and (u, v) in corte
        en_ciclo = ciclo is not None and (u, v) in ciclo
        color = "#DC2626" if en_ciclo else "#9F1239" if en_corte else "#B45309" if actual else "#7C3AED" if inversa else "#DC2626" if saturada else "#64748B"
        ancho = 4 if actual or en_corte or en_ciclo else 2
        estilo = "dash" if inversa or saturada else "solid"
        # El renderer calcula la curva inicial y la actualiza al mover sus extremos.
        curva = 0.12 if (v, u) in aristas else 0.035
        if residual is not None:
            valor = str(dato["capacidad"])
            detalle = f"Residual {'inversa (−)' if inversa else 'directa (+)'}: {valor}"
        else:
            valor = f"{dato}/{0 if flujo is None else flujo[u, v]}"
            detalle = f"Capacidad / flujo: {valor}"
        geometria.append({"u": u, "v": v, "curva": curva, "traza": len(figura.data),
                          "flecha": len(figura.layout.annotations),
                          "texto": len(figura.layout.annotations) + 1 if mostrar_valores else None})
        figura.add_trace(go.Scatter(
            x=[], y=[], mode="lines",
            line=dict(color=color, width=ancho, dash=estilo),
            text=f"{u} → {v}<br>{detalle}", hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ))
        figura.add_annotation(x=0, y=0, ax=0, ay=0,
                              xref="x", yref="y", axref="x", ayref="y", text="",
                              showarrow=True, arrowhead=2, arrowsize=1.2,
                              arrowwidth=ancho, arrowcolor=color)
        if mostrar_valores:
            figura.add_annotation(x=0, y=0, text=valor, showarrow=False,
                                  font=dict(size=12, color=color), bgcolor="rgba(255,255,255,0.94)",
                                  borderpad=2, hovertext=f"{u} → {v}: {detalle}")
    colores, formas, textos = [], [], []
    for nodo in nodos:
        en_ciclo = ciclo and any(nodo in arista for arista in ciclo)
        colores.append("#DC2626" if en_ciclo else "#BE123C" if nodo in fuentes else "#18181B" if nodo in sumideros else "#475569")
        formas.append("diamond" if "*" in nodo else "square" if nodo in sumideros else "circle")
        rol = "Fuente" if nodo in fuentes else "Sumidero" if nodo in sumideros else "Nodo intermedio"
        texto = f"{nodo} · {rol}" + (" ficticio" if "*" in nodo else "")
        if etiquetas and nodo in etiquetas:
            e = etiquetas[nodo]
            valor = "(−, ∞)" if e["predecesor"] is None else f"({e['predecesor']}{e['signo']}, {e['delta']})"
            texto += f"<br>Etiqueta: {valor}"
        textos.append(texto)
    figura.add_trace(go.Scatter(
        x=[posiciones[n][0] for n in nodos], y=[posiciones[n][1] for n in nodos],
        mode="markers+text", text=nodos, textposition="middle center",
        textfont=dict(color="white", size=13),
        marker=dict(size=34, color=colores, symbol=formas, line=dict(color="white", width=2)),
        hovertext=textos, hovertemplate="%{hovertext}<extra></extra>", showlegend=False,
    ))
    figura.update_layout(
        height=480, margin=dict(l=15, r=15, t=15, b=15),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#18181B"),
        xaxis=dict(visible=False, range=[-1.22, 1.22]),
        yaxis=dict(visible=False, range=[-1.22, 1.22]),
        hovermode="closest", uirevision=str(tuple(nodos)) + str(tuple(capacidades)),
        dragmode=False, meta={"aristas": geometria, "nodos": list(nodos),
                              "posiciones": posiciones},
    )
    return figura


def mostrar_red(red, fuentes, sumideros, key, **opciones):
    """Dibuja una red con posiciones persistentes y sus terminales ficticios."""
    mostrar_canvas(dibujar_grafo(
        red["nodos"], red["capacidades"], posiciones_actuales(red["nodos"], red["capacidades"]),
        fuentes + (["S*"] if "S*" in red["nodos"] else []),
        sumideros + (["T*"] if "T*" in red["nodos"] else []), **opciones), key=key)
