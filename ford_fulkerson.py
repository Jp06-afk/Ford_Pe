"""Ford-Fulkerson por etiquetado. NetworkX solo representa y valida el DAG."""

import random
import string

import networkx as nx


def crear_nodos(n):
    if type(n) is not int or not 7 <= n <= 16:
        raise ValueError("El número de nodos debe ser un entero entre 7 y 16.")
    return list(string.ascii_uppercase[:n])


def validar_capacidad(capacidad):
    if type(capacidad) is not int or capacidad <= 0:
        raise ValueError("La capacidad debe ser un número entero positivo.")


def detectar_ciclo(nodos, capacidades):
    grafo = nx.DiGraph()
    grafo.add_nodes_from(nodos)
    grafo.add_edges_from(capacidades)
    try:
        return list(nx.find_cycle(grafo))
    except nx.NetworkXNoCycle:
        return []


def validar_grafo(nodos, capacidades, en_construccion=False):
    if en_construccion:
        if len(nodos) > 16:
            raise ValueError("La red admite como máximo 16 nodos.")
        esperados = list(string.ascii_uppercase[:len(nodos)])
    else:
        esperados = crear_nodos(len(nodos))
    if list(nodos) != esperados:
        raise ValueError("Los nodos deben llamarse A, B, C, … en orden y sin repetir.")
    for (u, v), capacidad in capacidades.items():
        if u not in nodos or v not in nodos:
            raise ValueError("Los extremos de cada arista deben pertenecer a la red.")
        if u == v:
            raise ValueError("No se permiten autoaristas: origen y destino deben diferir.")
        validar_capacidad(capacidad)
    ciclo = detectar_ciclo(nodos, capacidades)
    if ciclo and not en_construccion:
        recorrido = [u for u, _ in ciclo] + [ciclo[0][0]]
        raise ValueError("La arista generaría un ciclo: " + " → ".join(recorrido))


def agregar_arista(nodos, capacidades, origen, destino, capacidad, en_construccion=False):
    if (origen, destino) in capacidades:
        raise ValueError("La arista ya existe. Usa Modificar capacidad.")
    nuevas = {**capacidades, (origen, destino): capacidad}
    validar_grafo(nodos, nuevas, en_construccion=en_construccion)
    return nuevas


def generar_grafo(n, densidad=0.3, minimo=1, maximo=20, semilla=None):
    nodos = crear_nodos(n)
    validar_capacidad(minimo)
    validar_capacidad(maximo)
    if minimo > maximo:
        raise ValueError("La capacidad mínima no puede superar la máxima.")
    if not 0 <= densidad <= 1:
        raise ValueError("La densidad debe estar entre 0 y 1.")
    azar = random.Random(semilla)
    # Una cadena base hace que todos los nodos participen en una ruta A → último.
    capacidades = {
        (nodos[i], nodos[i + 1]): azar.randint(minimo, maximo)
        for i in range(n - 1)
    }
    candidatas = [(nodos[i], nodos[j]) for i in range(n) for j in range(i + 2, n)]
    objetivo = max(n - 1, round(densidad * n * (n - 1) / 2))
    for arista in azar.sample(candidatas, objetivo - len(capacidades)):
        capacidades[arista] = azar.randint(minimo, maximo)
    return nodos, capacidades


def nodos_alcanzables(nodos, aristas, fuente):
    """Recorrido manual; aristas es un iterable de pares dirigidos."""
    vecinos = {nodo: [] for nodo in nodos}
    for u, v in aristas:
        vecinos[u].append(v)
    visitados = {fuente}
    pendientes = [fuente]
    while pendientes:
        u = pendientes.pop()
        for v in sorted(vecinos[u]):
            if v not in visitados:
                visitados.add(v)
                pendientes.append(v)
    return visitados


def preparar_red(nodos, capacidades, fuentes, sumideros):
    validar_grafo(nodos, capacidades)
    if not fuentes or not sumideros:
        raise ValueError("Selecciona al menos una fuente y un sumidero.")
    if len(set(fuentes)) != len(fuentes) or len(set(sumideros)) != len(sumideros):
        raise ValueError("No se permiten fuentes ni sumideros repetidos.")
    if not set(fuentes + sumideros).issubset(nodos):
        raise ValueError("Las fuentes y los sumideros deben pertenecer a la red.")
    if set(fuentes) & set(sumideros):
        raise ValueError("Fuente y sumidero deben ser distintos; las selecciones no pueden superponerse.")
    if not any(set(sumideros) & nodos_alcanzables(nodos, capacidades, s) for s in fuentes):
        raise ValueError("No existe un camino dirigido de las fuentes a los sumideros. Cambia la selección.")

    ampliados, nuevas = list(nodos), dict(capacidades)
    # Es mayor que cualquier flujo posible, y evita que un corte mínimo use
    # conexiones ficticias incluso cuando hay empates con capacidades originales.
    capacidad_ficticia = sum(capacidades.values()) + 1
    fuente, sumidero = fuentes[0], sumideros[0]
    if len(fuentes) > 1:
        fuente = "S*"
        ampliados.append(fuente)
        nuevas.update({(fuente, nodo): capacidad_ficticia for nodo in fuentes})
    if len(sumideros) > 1:
        sumidero = "T*"
        ampliados.append(sumidero)
        nuevas.update({(nodo, sumidero): capacidad_ficticia for nodo in sumideros})
    return {
        "nodos": ampliados, "capacidades": nuevas,
        "originales": dict(capacidades), "fuente": fuente, "sumidero": sumidero,
        "fuentes": list(fuentes), "sumideros": list(sumideros),
        "capacidad_ficticia": capacidad_ficticia,
    }


def crear_red_residual(capacidades, flujo):
    residual = {}
    for (u, v), capacidad in sorted(capacidades.items()):
        disponible = capacidad - flujo[u, v]
        if disponible > 0:
            residual[u, v] = {"capacidad": disponible, "signo": "+", "arista": (u, v)}
        if flujo[u, v] > 0:
            residual[v, u] = {"capacidad": flujo[u, v], "signo": "-", "arista": (u, v)}
    return residual


def etiquetar_nodos(nodos, residual, fuente, sumidero):
    """Etiquetado en profundidad, con vecinos en orden alfabético.

    None representa ∞ exclusivamente en la etiqueta de la fuente.
    Todas las capacidades, incrementos y flujos permanecen enteros.
    """
    etiquetas = {fuente: {"predecesor": None, "signo": None, "delta": None}}
    pendientes = [fuente]
    while pendientes and sumidero not in etiquetas:
        x = pendientes[-1]
        for y in sorted(nodos):
            if y in etiquetas or (x, y) not in residual:
                continue
            arco = residual[x, y]
            delta_x = etiquetas[x]["delta"]
            delta_y = arco["capacidad"] if delta_x is None else min(delta_x, arco["capacidad"])
            etiquetas[y] = {"predecesor": x, "signo": arco["signo"], "delta": delta_y}
            pendientes.append(y)
            break
        else:
            pendientes.pop()
    return etiquetas


def reconstruir_camino(etiquetas, fuente, sumidero):
    camino = []
    y = sumidero
    while y != fuente:
        etiqueta = etiquetas[y]
        x, signo = etiqueta["predecesor"], etiqueta["signo"]
        camino.append({"origen": x, "destino": y, "signo": signo,
                       "arista": (x, y) if signo == "+" else (y, x)})
        y = x
    return list(reversed(camino))


def actualizar_flujo(flujo, camino, delta):
    actualizado = dict(flujo)
    for paso in camino:
        # En un paso inverso se resta en la arista ORIGINAL, no se crea flujo negativo.
        actualizado[paso["arista"]] += delta if paso["signo"] == "+" else -delta
    return actualizado


def calcular_corte_minimo(nodos, capacidades, residual, fuente):
    s = nodos_alcanzables(nodos, residual, fuente)
    t = set(nodos) - s
    aristas = {e: c for e, c in capacidades.items() if e[0] in s and e[1] in t}
    return {"S": sorted(s), "T": sorted(t), "aristas": aristas,
            "capacidad": sum(aristas.values())}


def ford_fulkerson(nodos, capacidades, fuentes, sumideros):
    red = preparar_red(nodos, capacidades, fuentes, sumideros)
    capacidades = red["capacidades"]
    fuente, sumidero = red["fuente"], red["sumidero"]
    flujo = {arista: 0 for arista in capacidades}
    total, iteraciones = 0, []
    while True:
        residual = crear_red_residual(capacidades, flujo)
        etiquetas = etiquetar_nodos(red["nodos"], residual, fuente, sumidero)
        if sumidero not in etiquetas:
            break
        camino = reconstruir_camino(etiquetas, fuente, sumidero)
        delta = etiquetas[sumidero]["delta"]
        antes = dict(flujo)
        flujo = actualizar_flujo(flujo, camino, delta)
        total += delta
        iteraciones.append({
            "numero": len(iteraciones) + 1, "etiquetas": etiquetas,
            "camino": camino, "delta": delta, "agregado": delta, "total": total,
            "flujo_antes": antes, "flujo_despues": dict(flujo),
            "residual_antes": residual,
            "residual_despues": crear_red_residual(capacidades, flujo),
        })
    corte = calcular_corte_minimo(red["nodos"], capacidades, residual, fuente)
    return {**red, "flujo": flujo, "maximo": total, "iteraciones": iteraciones,
            "residual_final": residual, "etiquetas_finales": etiquetas, "corte": corte}


def cargar_ejemplo(numero=1):
    nodos = crear_nodos(7)
    if numero == 1:
        capacidades = {("A", "B"): 8, ("A", "C"): 6, ("B", "D"): 5,
                       ("B", "E"): 3, ("C", "E"): 4, ("C", "F"): 2,
                       ("D", "G"): 5, ("E", "G"): 7, ("F", "G"): 2}
        return nodos, capacidades, ["A"], ["G"]
    if numero == 2:
        capacidades = {("A", "C"): 6, ("A", "D"): 4, ("B", "C"): 3,
                       ("B", "D"): 5, ("C", "E"): 7, ("C", "F"): 2,
                       ("D", "E"): 4, ("D", "G"): 5, ("E", "F"): 6,
                       ("E", "G"): 5}
        return nodos, capacidades, ["A", "B"], ["F", "G"]
    if numero == 3:
        capacidades = {e: 1 for e in [("A", "B"), ("A", "C"), ("B", "D"),
                                    ("B", "E"), ("C", "D"), ("D", "G"),
                                    ("E", "F"), ("F", "G")]}
        return nodos, capacidades, ["A"], ["G"]
    raise ValueError("Elige un ejemplo entre 1 y 3.")
