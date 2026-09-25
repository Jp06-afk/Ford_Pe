"""Interfaz didáctica. Ejecutar con: streamlit run app.py"""

import math

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from ford_fulkerson import (
    agregar_arista, cargar_ejemplo, crear_nodos, crear_red_residual,
    ford_fulkerson, generar_grafo, preparar_red, validar_grafo,
)


st.set_page_config(page_title="Flujo máximo · Matemática computacional",
                   page_icon=":material/hub:", layout="centered")


def invalidar_resultados():
    st.session_state.resultado = None
    st.session_state.iteraciones = []
    st.session_state.paso = 0


def reemplazar_red(nodos, aristas, fuentes=None, sumideros=None):
    estado = st.session_state
    estado.nodos, estado.aristas = nodos, aristas
    estado.fuentes = fuentes or [nodos[0]]
    estado.sumideros = sumideros or [nodos[-1]]
    estado.fuente = estado.fuentes[0]
    estado.sumidero = estado.sumideros[0]
    estado.multiples = len(estado.fuentes) > 1 or len(estado.sumideros) > 1
    # Se ejecuta antes de construir los selectores de terminales de esta pasada.
    for clave in ("fuente_ui", "sumidero_ui", "fuentes_ui", "sumideros_ui", "multiples_ui"):
        estado.pop(clave, None)
    invalidar_resultados()


def usar_ejemplo():
    reemplazar_red(*cargar_ejemplo(st.session_state.ejemplo))
    st.session_state.n = 7
    st.session_state.modo = "Manual"


def cambiar_n():
    try:
        nodos = crear_nodos(st.session_state.n)
    except ValueError:
        invalidar_resultados()
        return
    aristas = {e: c for e, c in st.session_state.aristas.items()
               if e[0] in nodos and e[1] in nodos}
    reemplazar_red(nodos, aristas)


def mover_paso(destino):
    st.session_state.paso = destino


@st.cache_data(max_entries=24, show_spinner=False)
def obtener_posiciones(nodos, aristas):
    grafo = nx.DiGraph()
    grafo.add_nodes_from(nodos)
    grafo.add_edges_from(aristas)
    posiciones = nx.spring_layout(grafo, seed=21, k=1.2, iterations=120)
    return {nodo: (float(p[0]), float(p[1])) for nodo, p in posiciones.items()}


def dibujar_grafo(nodos, capacidades, posiciones, fuentes, sumideros,
                  flujo=None, residual=None, camino=None, corte=None, etiquetas=None,
                  mostrar_valores=True):
    figura = go.Figure()
    pasos = camino or []
    recorrido = {(p["origen"], p["destino"]) for p in pasos}
    originales_camino = {p["arista"] for p in pasos}
    aristas = residual if residual is not None else capacidades
    for (u, v), dato in sorted(aristas.items()):
        inversa = residual is not None and dato["signo"] == "-"
        actual = (u, v) in (recorrido if residual is not None else originales_camino)
        saturada = flujo is not None and residual is None and flujo[u, v] == capacidades[u, v]
        en_corte = corte is not None and (u, v) in corte
        color = "#9F1239" if en_corte else "#B45309" if actual else "#7C3AED" if inversa else "#DC2626" if saturada else "#64748B"
        ancho = 4 if actual or en_corte else 2
        estilo = "dash" if inversa or saturada else "solid"
        x0, y0 = posiciones[u]
        x1, y1 = posiciones[v]
        dx, dy = x1 - x0, y1 - y0
        largo = max(math.hypot(dx, dy), 0.001)
        # Las dos direcciones residuales se curvan a lados opuestos.
        curva = 0.12 if residual is not None and (v, u) in aristas else 0.035
        cx, cy = (x0 + x1) / 2 - dy / largo * curva, (y0 + y1) / 2 + dx / largo * curva

        def punto(t):
            return ((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
                    (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1)

        puntos = [punto(i / 30) for i in range(2, 29)]
        if residual is not None:
            valor = str(dato["capacidad"])
            detalle = f"Residual {'inversa (−)' if inversa else 'directa (+)'}: {valor}"
        else:
            valor = str(dato) if flujo is None else f"{flujo[u, v]}/{dato}"
            detalle = f"Capacidad: {dato}" if flujo is None else f"Flujo / capacidad: {valor}"
        figura.add_trace(go.Scatter(
            x=[p[0] for p in puntos], y=[p[1] for p in puntos], mode="lines",
            line=dict(color=color, width=ancho, dash=estilo),
            text=f"{u} → {v}<br>{detalle}", hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ))
        punta, cola = punto(0.90), punto(0.80)
        figura.add_annotation(x=punta[0], y=punta[1], ax=cola[0], ay=cola[1],
                              xref="x", yref="y", axref="x", ayref="y", text="",
                              showarrow=True, arrowhead=2, arrowsize=1.2,
                              arrowwidth=ancho, arrowcolor=color)
        if mostrar_valores:
            centro = punto(0.5)
            figura.add_annotation(x=centro[0], y=centro[1], text=valor, showarrow=False,
                                  font=dict(size=12, color=color), bgcolor="rgba(255,255,255,0.94)",
                                  borderpad=2, hovertext=f"{u} → {v}: {detalle}")
    colores, formas, textos = [], [], []
    for nodo in nodos:
        colores.append("#BE123C" if nodo in fuentes else "#18181B" if nodo in sumideros else "#475569")
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
    )
    return figura


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
              "Sumideros: " + ", ".join(resultado["sumideros"]), "", "ARISTAS (flujo/capacidad)"]
    for (u, v), c in sorted(resultado["capacidades"].items()):
        extra = " [conexión ficticia]" if "*" in u + v else ""
        lineas.append(f"{u} -> {v}: {resultado['flujo'][u, v]}/{c}{extra}")
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


if "nodos" not in st.session_state:
    reemplazar_red(*cargar_ejemplo(1))
    st.session_state.n = 7
    st.session_state.modo = "Manual"
estado = st.session_state

with st.sidebar:
    st.markdown("### Matemática computacional")
    st.caption("LABORATORIO DE GRAFOS")
    st.markdown("**Ford-Fulkerson**\n\nExplora cómo cada camino aumenta el flujo de una red.")
    st.selectbox("Ejemplos", [1, 2, 3], key="ejemplo", format_func=lambda n: {
        1: "1 · Fuente y sumidero únicos", 2: "2 · Múltiples fuentes y sumideros",
        3: "3 · Devolver flujo: etiqueta −"}[n])
    st.button("Cargar ejemplo", key="cargar_ejemplo", on_click=usar_ejemplo, width="stretch")
    st.caption("Cargar un ejemplo reemplaza la red actual. Cada ejemplo tiene 7 nodos.")
    st.markdown("**Recorrido de la práctica**\n\n01 · Configurar\n\n02 · Construir\n\n03 · Elegir terminales\n\n04 · Explorar pasos\n\n05 · Verificar el corte")

st.caption("MATEMÁTICA COMPUTACIONAL / REDES DE FLUJO")
st.title("Problema del flujo máximo")
st.markdown("**Algoritmo de Ford-Fulkerson** · Un camino, una etiqueta y un incremento a la vez.")

with st.expander("¿Cómo funciona Ford-Fulkerson?"):
    st.markdown("""
**Capacidad** es el límite de una arista; **flujo** es la cantidad que circula.
Se cumple `0 ≤ flujo ≤ capacidad` y, en nodos intermedios, entrada = salida.

Un **camino aumentante** conecta fuente y sumidero usando capacidad residual positiva.
La **red residual** permite avanzar con `c − f` o devolver flujo con `f`.
**Delta (Δ)** es el menor residual del camino: cuánto puede aumentarse el flujo.

- Fuente: etiqueta `(−, ∞)`.
- Etiqueta `(x+, Δ)`: llegar desde x permite **sumar** flujo en x → y.
- Etiqueta `(x−, Δ)`: llegar desde x permite **restar** flujo en y → x.

Aquí se continúa desde el último nodo etiquetado, probando vecinos en orden
alfabético y retrocediendo cuando no quedan vecinos: el recorrido es determinista.
Tras aumentar el flujo se borran las etiquetas y se empieza otra vez.
Con capacidades enteras, cada aumento es positivo y el algoritmo termina.

Termina cuando el sumidero no recibe etiqueta. Los nodos alcanzables en la residual
final forman S; los demás, T. Las aristas originales de S a T forman el **corte mínimo**.
Solo el grafo original debe ser acíclico: los ciclos residuales son válidos.
""")

st.subheader("01 · Configuración de la red")
st.number_input("Número de nodos (7 a 16)", step=1, key="n", on_change=cambiar_n)
try:
    crear_nodos(estado.n)
except ValueError as error:
    st.error(str(error))
    st.stop()
st.radio("Método de construcción", ["Manual", "Aleatorio"], key="modo", horizontal=True)
st.caption("Nodos: " + ", ".join(estado.nodos) + ". Cambiar n conserva las aristas cuyos extremos siguen existiendo.")

st.subheader("02 · Construcción y visualización")
if estado.modo == "Aleatorio":
    with st.form("generador"):
        densidad = st.slider("Densidad aproximada", 0.0, 1.0, 0.30, 0.05)
        minimo = st.number_input("Capacidad mínima", value=1, step=1)
        maximo = st.number_input("Capacidad máxima", value=20, step=1)
        generar = st.form_submit_button("Generar otro grafo", type="primary")
    st.caption("Densidad respecto a n(n−1)/2 aristas posibles en un DAG. Una cadena base garantiza una ruta que incluye todos los nodos.")
    if generar:
        try:
            nodos, aristas = generar_grafo(estado.n, densidad, minimo, maximo)
            reemplazar_red(nodos, aristas)
            st.success("Grafo generado. Selecciona sus terminales e inicia el algoritmo.")
        except ValueError as error:
            st.error(str(error))
else:
    with st.expander("Agregar arista", expanded=not estado.aristas):
        with st.form("nueva_arista"):
            origen = st.selectbox("Nodo origen de la arista", estado.nodos, key="origen_arista")
            destino = st.selectbox("Nodo destino de la arista", estado.nodos, index=1, key="destino_arista")
            capacidad = st.number_input("Capacidad", value=1, step=1, key="capacidad_arista")
            agregar = st.form_submit_button("Agregar arista", type="primary")
        if agregar:
            try:
                estado.aristas = agregar_arista(estado.nodos, estado.aristas, origen, destino, capacidad)
                invalidar_resultados()
                st.success(f"Arista {origen} → {destino} agregada.")
            except ValueError as error:
                st.error(str(error))

with st.expander("Editar o eliminar aristas"):
    if estado.aristas:
        arista = st.selectbox("Arista", sorted(estado.aristas),
                              format_func=lambda e: f"{e[0]} → {e[1]}", key="arista_editar")
        nueva = st.number_input("Nueva capacidad", value=estado.aristas[arista], step=1,
                                 key=f"editar_{arista}_{estado.aristas[arista]}")
        with st.container(horizontal=True):
            modificar = st.button("Modificar capacidad", key="modificar")
            eliminar = st.button("Eliminar arista", key="eliminar")
            limpiar = st.button("Vaciar red", key="vaciar")
        if modificar:
            try:
                candidatas = {**estado.aristas, arista: nueva}
                validar_grafo(estado.nodos, candidatas)
                estado.aristas = candidatas
                invalidar_resultados()
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if eliminar or limpiar:
            estado.aristas = {} if limpiar else {e: c for e, c in estado.aristas.items() if e != arista}
            invalidar_resultados()
            st.rerun()
    else:
        st.caption("La red está vacía. Agrega aristas o carga un ejemplo.")
with st.expander(f"Tabla de aristas · {len(estado.aristas)} conexiones"):
    st.dataframe([{"Origen": u, "Destino": v, "Capacidad": c}
                  for (u, v), c in sorted(estado.aristas.items())], hide_index=True, width="stretch")
vista_previa = st.container()

st.subheader("03 · Fuente y sumidero")
estado.setdefault("multiples_ui", estado.multiples)
multiples = st.checkbox("Múltiples fuentes y/o sumideros", key="multiples_ui")
if multiples:
    estado.setdefault("fuentes_ui", estado.fuentes)
    estado.setdefault("sumideros_ui", estado.sumideros)
    fuentes = st.multiselect("Fuentes", estado.nodos, key="fuentes_ui")
    sumideros = st.multiselect("Sumideros", estado.nodos, key="sumideros_ui")
else:
    estado.setdefault("fuente_ui", estado.fuente)
    estado.setdefault("sumidero_ui", estado.sumidero)
    fuentes = [st.selectbox("Fuente", estado.nodos, key="fuente_ui")]
    sumideros = [st.selectbox("Sumidero", estado.nodos, key="sumidero_ui")]
seleccion = (tuple(fuentes), tuple(sumideros), multiples)
if estado.get("seleccion") != seleccion:
    invalidar_resultados()
    estado.seleccion = seleccion
estado.fuentes, estado.sumideros, estado.multiples = fuentes, sumideros, multiples
if fuentes:
    estado.fuente = fuentes[0]
if sumideros:
    estado.sumidero = sumideros[0]
red, error_red = None, None
try:
    red = preparar_red(estado.nodos, estado.aristas, fuentes, sumideros)
except ValueError as error:
    error_red = str(error)
    st.error(error_red)
if red and ("S*" in red["nodos"] or "T*" in red["nodos"]):
    st.info(f"Los rombos S* y T* son nodos ficticios cuando corresponda. Sus conexiones usan "
            f"M = 1 + suma de capacidades = {red['capacidad_ficticia']}. "
            "Este valor supera cualquier flujo posible y equivale a capacidad infinita en esta red.")

with vista_previa:
    mostrar_valores = st.checkbox("Mostrar valores en las aristas", value=True, key="valores")
    if estado.resultado is None:
        grafico = red or {"nodos": estado.nodos, "capacidades": estado.aristas}
        posiciones = obtener_posiciones(tuple(grafico["nodos"]), tuple(sorted(grafico["capacidades"])))
        st.plotly_chart(dibujar_grafo(
            grafico["nodos"], grafico["capacidades"], posiciones,
            fuentes + (["S*"] if red and "S*" in red["nodos"] else []),
            sumideros + (["T*"] if red and "T*" in red["nodos"] else []),
            mostrar_valores=mostrar_valores), width="stretch", theme=None, key="previa")
        st.caption("Capacidad en cada arista · fuente: círculo rojo · sumidero: cuadrado negro · ficticio: rombo. Acerca el cursor para ver detalles.")
    else:
        st.caption("La red se muestra con su flujo en la etapa 04. Editarla descarta los resultados anteriores.")

st.subheader("04 · Ford-Fulkerson paso a paso")
if st.button("Iniciar Ford-Fulkerson", type="primary", key="iniciar",
             disabled=red is None or estado.resultado is not None):
    try:
        with st.spinner("Calculando etiquetas y caminos aumentantes…"):
            estado.resultado = ford_fulkerson(estado.nodos, estado.aristas, fuentes, sumideros)
        estado.iteraciones = estado.resultado["iteraciones"]
        estado.paso = 0
        st.rerun()
    except ValueError as error:
        st.error(str(error))

resultado = estado.resultado
if resultado is not None:
    pasos = resultado["iteraciones"]
    ultimo = len(pasos) + 1
    indice = estado.paso
    with st.container(horizontal=True):
        st.button("Anterior", key="anterior", disabled=indice == 0,
                  on_click=mover_paso, args=(indice - 1,))
        st.button("Siguiente", key="siguiente", disabled=indice == ultimo,
                  on_click=mover_paso, args=(indice + 1,))
        st.button("Ver resultado final", key="final", disabled=indice == ultimo,
                  on_click=mover_paso, args=(ultimo,))
        st.button("Reiniciar algoritmo", key="reiniciar", on_click=invalidar_resultados)
    st.progress(indice / ultimo, text=f"Estado {indice} de {ultimo} · incluye inicio y comprobación final")
    final = indice == ultimo
    actual = pasos[indice - 1] if 1 <= indice <= len(pasos) else None
    antes = False
    if actual:
        st.markdown(f"### Iteración {actual['numero']}")
        st.markdown(f"**Camino aumentante:** {texto_camino(actual['camino'])}")
        st.markdown(f"**Cuello de botella: Δ = {actual['delta']}** · Flujo agregado: **+{actual['agregado']}** · Flujo total después: **{actual['total']}**")
        momento = st.radio("Momento de la iteración", ["Después de actualizar", "Antes de actualizar"],
                            horizontal=True, key="momento")
        antes = momento == "Antes de actualizar"
        flujo = actual["flujo_antes"] if antes else actual["flujo_despues"]
        residual = actual["residual_antes"] if antes else actual["residual_despues"]
        etiquetas, camino = actual["etiquetas"], actual["camino"]
        total = actual["total"] - actual["delta"] if antes else actual["total"]
        st.caption("Las etiquetas y el camino se obtienen ANTES de actualizar. En la residual posterior, los arcos agotados desaparecen.")
        for paso in camino:
            if paso["signo"] == "-":
                u, v = paso["arista"]
                st.info(f"Etiqueta negativa: {paso['origen']} → {paso['destino']} devuelve {actual['delta']} unidades por la arista original {u} → {v}.")
    elif final:
        flujo, residual = resultado["flujo"], resultado["residual_final"]
        etiquetas, camino, total = resultado["etiquetas_finales"], [], resultado["maximo"]
        st.markdown("### Comprobación final: no hay camino aumentante")
        st.caption("El sumidero ya no puede etiquetarse. Las etiquetas que ves corresponden al último intento.")
    else:
        flujo = {e: 0 for e in resultado["capacidades"]}
        residual = crear_red_residual(resultado["capacidades"], flujo)
        etiquetas = {resultado["fuente"]: {"predecesor": None, "signo": None, "delta": None}}
        camino, total = [], 0
        st.markdown("### Estado inicial · flujo cero")
        st.caption("La fuente tiene la etiqueta (−, ∞). Pulsa Siguiente para explorar la primera iteración.")
    st.metric("Flujo representado en los gráficos", total)
    posiciones = obtener_posiciones(tuple(resultado["nodos"]), tuple(sorted(resultado["capacidades"])))
    tab_flujo, tab_residual = st.tabs(["Red de flujo", "Red residual"])
    for tab, es_residual in [(tab_flujo, False), (tab_residual, True)]:
        with tab:
            st.plotly_chart(dibujar_grafo(
                resultado["nodos"], resultado["capacidades"], posiciones,
                fuentes + [resultado["fuente"]], sumideros + [resultado["sumidero"]],
                flujo=flujo, residual=residual if es_residual else None, camino=camino,
                corte=resultado["corte"]["aristas"] if final and not es_residual else None,
                etiquetas=etiquetas, mostrar_valores=mostrar_valores), width="stretch", theme=None,
                key="residual" if es_residual else "flujo")
            if es_residual:
                st.caption("Gris continuo: residual directa (+) · violeta discontinuo: inversa (−) · ámbar grueso: camino actual. Solo se dibujan residuales positivas.")
            else:
                st.caption("Flujo/capacidad · ámbar grueso: aristas del camino · rojo discontinuo: saturadas · granate grueso: corte mínimo final.")
    st.caption("Fuente: rojo · sumidero: negro · nodos ficticios: rombos. Las posiciones permanecen fijas entre pasos.")
    st.markdown("**Etiquetas del procedimiento**")
    st.dataframe(tabla_etiquetas(resultado["nodos"], etiquetas), hide_index=True, width="stretch")
    if actual:
        with st.expander("Cambios de flujo en esta iteración"):
            st.dataframe([{"Arista": f"{u} → {v}", "Antes": actual["flujo_antes"][u, v],
                           "Después": actual["flujo_despues"][u, v], "Capacidad": c}
                          for (u, v), c in sorted(resultado["capacidades"].items())], hide_index=True, width="stretch")
    with st.expander("Capacidades de la red residual"):
        st.dataframe([{"Origen": u, "Destino": v, "Residual": a["capacidad"], "Signo": a["signo"]}
                      for (u, v), a in sorted(residual.items())], hide_index=True, width="stretch")
    st.markdown("**Historial de iteraciones**")
    vistos = len(pasos) if final else max(0, indice - int(antes))
    if vistos:
        st.dataframe(tabla_historial(pasos[:vistos]), hide_index=True, width="stretch")
    else:
        st.caption("Todavía no se ha aplicado ningún aumento de flujo en la vista actual.")

    if final:
        st.subheader("05 · Resultado y corte mínimo")
        st.success(f"FLUJO MÁXIMO = {resultado['maximo']} · CAPACIDAD DEL CORTE MÍNIMO = {resultado['corte']['capacidad']}")
        st.dataframe([{"Origen": u, "Destino": v, "Flujo": flujo[u, v], "Capacidad": c,
                       "Flujo/Capacidad": f"{flujo[u, v]}/{c}"}
                      for (u, v), c in sorted(resultado["originales"].items())], hide_index=True, width="stretch")
        corte = resultado["corte"]
        st.code("S = {" + ", ".join(corte["S"]) + "}\nT = {" + ", ".join(corte["T"]) + "}", language=None)
        st.caption("S contiene los nodos alcanzables desde la fuente en la red residual final; T contiene los demás, incluidos los ficticios si existen.")
        st.dataframe([{"Origen (S)": u, "Destino (T)": v, "Capacidad": c}
                      for (u, v), c in sorted(corte["aristas"].items())], hide_index=True, width="stretch")
        st.markdown("De acuerdo con el **teorema de Flujo Máximo – Corte Mínimo**, la igualdad entre ambos valores certifica que el flujo encontrado es máximo.")
        st.download_button("Descargar resultados TXT", exportar_resultado(resultado).encode("utf-8"),
                           file_name="resultado_ford_fulkerson.txt", mime="text/plain", key="descargar")
else:
    st.caption("Configura una red válida e inicia el algoritmo para recorrer sus estados.")

with st.expander("Aplicaciones del flujo máximo"):
    st.markdown("""
- **Logística y transporte:** capacidad = vehículos por hora; flujo = vehículos enviados.
- **Comunicaciones:** capacidad = ancho de banda; flujo = datos transmitidos por segundo.
- **Tuberías y distribución:** capacidad = litros por minuto; flujo = caudal transportado.
- **Energía:** capacidad = potencia de una línea; flujo = potencia transferida en un modelo simplificado.
- **Asignación de recursos:** capacidad = cupos disponibles; flujo = asignaciones realizadas.
""")
