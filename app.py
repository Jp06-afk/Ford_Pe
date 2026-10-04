"""Interfaz didáctica. Ejecutar con: streamlit run app.py"""

import streamlit as st

from ford_fulkerson import (
    agregar_arista, cargar_ejemplo, crear_nodos, crear_red_residual,
    detectar_ciclo, ford_fulkerson, generar_grafo, preparar_red, validar_grafo,
)
from canvas_grafo import mostrar_red
from interfaz import (
    agregar_nodo_manual, cambiar_modo, cambiar_n, crear_nodos_manuales,
    exportar_resultado, invalidar_resultados, mostrar_tabla, mostrar_validacion,
    mover_paso, reemplazar_red, tabla_etiquetas, tabla_historial, texto_camino, usar_ejemplo,
)


st.set_page_config(page_title="Flujo máximo · Matemática computacional",
                   page_icon=":material/hub:", layout="centered")


if "nodos" not in st.session_state:
    reemplazar_red(*cargar_ejemplo(1))
    st.session_state.n = 7
    st.session_state.modo = "Ejemplo cargado"
estado = st.session_state
estado.setdefault("posiciones", {})
estado.setdefault("vista_canvas", None)
estado.setdefault("revision_red", 0)
estado.setdefault("modo", "Ejemplo cargado")
if estado.modo == "Manual":
    estado.modo = "Ejemplo cargado"

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
st.radio("Método de construcción", ["Ejemplo cargado", "Crear grafo manual", "Aleatorio"],
         key="modo", horizontal=True, on_change=cambiar_modo)
with mostrar_validacion(detener=True):
    crear_nodos(estado.n)
st.caption(f"Nodos creados: {len(estado.nodos)}/16 · " + (", ".join(estado.nodos) or "Red vacía") +
           ". Para ejecutar se requieren entre 7 y 16. Cambiar n ajusta una red ya creada.")
if estado.modo == "Crear grafo manual":
    with st.container(horizontal=True):
        st.button("Crear los n nodos", key="crear_nodos", on_click=crear_nodos_manuales,
                  disabled=bool(estado.nodos))
        st.button("Agregar nodo", key="agregar_nodo", on_click=agregar_nodo_manual,
                  disabled=len(estado.nodos) >= 16)
        st.button("Nueva red manual", key="nueva_manual", on_click=cambiar_modo)

st.subheader("02 · Construcción y visualización")
if estado.modo == "Aleatorio":
    with st.form("generador"):
        densidad = st.slider("Densidad aproximada", 0.0, 1.0, 0.30, 0.05)
        minimo = st.number_input("Capacidad mínima", value=1, step=1)
        maximo = st.number_input("Capacidad máxima", value=20, step=1)
        generar = st.form_submit_button("Generar otro grafo", type="primary")
    st.caption("Densidad respecto a n(n−1)/2 aristas posibles en un DAG. Una cadena base garantiza una ruta que incluye todos los nodos.")
    if generar:
        with mostrar_validacion():
            nodos, aristas = generar_grafo(estado.n, densidad, minimo, maximo)
            reemplazar_red(nodos, aristas)
            st.success("Grafo generado. Selecciona sus terminales e inicia el algoritmo.")
elif len(estado.nodos) >= 2:
    with st.expander("Agregar arista", expanded=not estado.aristas):
        with st.form("nueva_arista"):
            origen = st.selectbox("Nodo origen de la arista", estado.nodos, key="origen_arista")
            destino = st.selectbox("Nodo destino de la arista", estado.nodos, index=1, key="destino_arista")
            capacidad = st.number_input("Capacidad", value=1, step=1, key="capacidad_arista")
            agregar = st.form_submit_button("Agregar arista", type="primary")
        if agregar:
            with mostrar_validacion():
                estado.aristas = agregar_arista(estado.nodos, estado.aristas, origen, destino,
                                               capacidad, en_construccion=True)
                invalidar_resultados()
                st.success(f"Arista {origen} → {destino} agregada.")

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
            with mostrar_validacion():
                candidatas = {**estado.aristas, arista: nueva}
                validar_grafo(estado.nodos, candidatas, en_construccion=True)
                estado.aristas = candidatas
                invalidar_resultados()
                st.rerun()
        if eliminar or limpiar:
            estado.aristas = {} if limpiar else {e: c for e, c in estado.aristas.items() if e != arista}
            invalidar_resultados()
            st.rerun()
    else:
        st.caption("La red está vacía. Agrega aristas o carga un ejemplo.")
with st.expander(f"Tabla de aristas · {len(estado.aristas)} conexiones"):
    mostrar_tabla([{"Origen": u, "Destino": v, "Capacidad": c}
                  for (u, v), c in sorted(estado.aristas.items())])
vista_previa = st.container()
ciclo_actual = detectar_ciclo(estado.nodos, estado.aristas)
if ciclo_actual:
    invalidar_resultados()
    recorrido_ciclo = [u for u, _ in ciclo_actual] + [ciclo_actual[0][0]]
    st.error("Ciclo detectado: " + " → ".join(recorrido_ciclo) +
             ". Está resaltado en rojo. Elimina una de sus aristas para poder ejecutar.")

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
    fuente = st.selectbox("Fuente", estado.nodos, index=None, key="fuente_ui")
    sumidero = st.selectbox("Sumidero", estado.nodos, index=None, key="sumidero_ui")
    fuentes = [fuente] if fuente is not None else []
    sumideros = [sumidero] if sumidero is not None else []
seleccion = (tuple(fuentes), tuple(sumideros), multiples)
if estado.get("seleccion") != seleccion:
    invalidar_resultados()
    estado.seleccion = seleccion
estado.fuentes, estado.sumideros, estado.multiples = fuentes, sumideros, multiples
estado.fuente = fuentes[0] if fuentes else None
estado.sumidero = sumideros[0] if sumideros else None
red = None
with mostrar_validacion():
    red = preparar_red(estado.nodos, estado.aristas, fuentes, sumideros)
if red and ("S*" in red["nodos"] or "T*" in red["nodos"]):
    st.info(f"Los rombos S* y T* son nodos ficticios cuando corresponda. Sus conexiones usan "
            f"M = 1 + suma de capacidades = {red['capacidad_ficticia']}. "
            "Este valor supera cualquier flujo posible y equivale a capacidad infinita en esta red.")

with vista_previa:
    mostrar_valores = st.checkbox("Mostrar valores en las aristas", value=True, key="valores")
    if estado.resultado is None:
        grafico = red or {"nodos": estado.nodos, "capacidades": estado.aristas}
        mostrar_red(grafico, fuentes, sumideros, key="previa",
                    mostrar_valores=mostrar_valores, ciclo=ciclo_actual)
        st.caption("Capacidad/flujo en cada arista · fuente: círculo rojo · sumidero: cuadrado negro · ficticio: rombo. Acerca el cursor para ver detalles.")
    else:
        st.caption("La red se muestra con su flujo en la etapa 04. Editarla descarta los resultados anteriores.")

st.subheader("04 · Ford-Fulkerson paso a paso")
if st.button("Iniciar Ford-Fulkerson", type="primary", key="iniciar",
             disabled=red is None or estado.resultado is not None):
    with mostrar_validacion():
        with st.spinner("Calculando etiquetas y caminos aumentantes…"):
            estado.resultado = ford_fulkerson(estado.nodos, estado.aristas, fuentes, sumideros)
        estado.iteraciones = estado.resultado["iteraciones"]
        estado.paso = 0
        st.rerun()

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
        flujo = dict.fromkeys(resultado["capacidades"], 0)
        residual = crear_red_residual(resultado["capacidades"], flujo)
        etiquetas = {resultado["fuente"]: {"predecesor": None, "signo": None, "delta": None}}
        camino, total = [], 0
        st.markdown("### Estado inicial · flujo cero")
        st.caption("La fuente tiene la etiqueta (−, ∞). Pulsa Siguiente para explorar la primera iteración.")
    st.metric("Flujo representado en los gráficos", total)
    tab_flujo, tab_residual = st.tabs(["Red de flujo", "Red residual"])
    for tab, es_residual in [(tab_flujo, False), (tab_residual, True)]:
        with tab:
            mostrar_red(resultado, fuentes, sumideros, key="residual" if es_residual else "flujo",
                        flujo=flujo, residual=residual if es_residual else None, camino=camino,
                        corte=resultado["corte"]["aristas"] if final and not es_residual else None,
                        etiquetas=etiquetas, mostrar_valores=mostrar_valores)
            if es_residual:
                st.caption("Gris continuo: residual directa (+) · violeta discontinuo: inversa (−) · ámbar grueso: camino actual. Solo se dibujan residuales positivas.")
            else:
                st.caption("Capacidad/flujo · ámbar grueso: aristas del camino · rojo discontinuo: saturadas · granate grueso: corte mínimo final.")
    st.caption("Fuente: rojo · sumidero: negro · nodos ficticios: rombos. Las posiciones permanecen fijas entre pasos.")
    st.markdown("**Etiquetas del procedimiento**")
    mostrar_tabla(tabla_etiquetas(resultado["nodos"], etiquetas))
    if actual:
        with st.expander("Camino y capacidades residuales antes del aumento"):
            mostrar_tabla([{
                "Paso": f"{p['origen']} → {p['destino']}", "Signo": p["signo"],
                "Residual disponible": actual["residual_antes"][p["origen"], p["destino"]]["capacidad"],
                "Delta aplicado": actual["delta"],
                "Flujo antes": actual["flujo_antes"][p["arista"]],
                "Flujo después": actual["flujo_despues"][p["arista"]],
            } for p in actual["camino"]])
        with st.expander("Cambios de flujo en esta iteración"):
            mostrar_tabla([{"Arista": f"{u} → {v}", "Antes": actual["flujo_antes"][u, v],
                           "Después": actual["flujo_despues"][u, v], "Capacidad": c}
                          for (u, v), c in sorted(resultado["capacidades"].items())])
    with st.expander("Capacidades de la red residual"):
        mostrar_tabla([{"Origen": u, "Destino": v, "Residual": a["capacidad"], "Signo": a["signo"]}
                      for (u, v), a in sorted(residual.items())])
    st.markdown("**Historial de iteraciones**")
    vistos = len(pasos) if final else max(0, indice - int(antes))
    if vistos:
        mostrar_tabla(tabla_historial(pasos[:vistos]))
    else:
        st.caption("Todavía no se ha aplicado ningún aumento de flujo en la vista actual.")

    if final:
        st.subheader("05 · Resultado y corte mínimo")
        certificado = resultado["maximo"] == resultado["corte"]["capacidad"]
        mensaje_final = f"FLUJO MÁXIMO = {resultado['maximo']} · CAPACIDAD DEL CORTE MÍNIMO = {resultado['corte']['capacidad']}"
        if certificado:
            st.success(mensaje_final)
        else:
            st.error(mensaje_final + ". La igualdad no se cumple; revisa la red.")
        mostrar_tabla([{"Origen": u, "Destino": v, "Flujo": flujo[u, v], "Capacidad": c,
                       "Capacidad/Flujo": f"{c}/{flujo[u, v]}"}
                      for (u, v), c in sorted(resultado["originales"].items())])
        corte = resultado["corte"]
        st.code("S = {" + ", ".join(corte["S"]) + "}\nT = {" + ", ".join(corte["T"]) + "}", language=None)
        st.caption("S contiene los nodos alcanzables desde la fuente en la red residual final; T contiene los demás, incluidos los ficticios si existen.")
        mostrar_tabla([{"Origen (S)": u, "Destino (T)": v, "Capacidad": c}
                      for (u, v), c in sorted(corte["aristas"].items())])
        if certificado:
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
