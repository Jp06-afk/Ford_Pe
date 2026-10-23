"""Coordenadas de los ejemplos y distribución de las dos partes de un corte."""


# Edita aquí la presentación de cada ejemplo: número -> nodo -> (x, y).
# x aumenta hacia la derecha; y aumenta hacia arriba. Usa valores entre -1 y 1.
# S* y T* son los terminales ficticios del ejemplo con múltiples terminales.
POSICIONES_EJEMPLOS = {
    1: {
        "A": (-1.0, 0.0), "B": (-0.45, 0.55), "C": (-0.45, -0.55),
        "D": (0.2, 0.85), "E": (0.2, 0.0), "F": (0.2, -0.85),
        "G": (1.0, 0.0),
    },
    2: {
        "S*": (-1.0, 0.0), "A": (-0.7, 0.6), "B": (-0.7, -0.6),
        "C": (-0.25, 0.6), "D": (-0.25, -0.6), "E": (0.25, 0.0),
        "F": (0.7, 0.6), "G": (0.7, -0.6), "T*": (1.0, 0.0),
    },
    3: {
        "A": (-1.0, 0.0), "B": (-0.5, 0.6), "C": (-0.5, -0.6),
        "D": (0.0, 0.0), "E": (0.0, 0.85), "F": (0.5, 0.85),
        "G": (1.0, 0.0),
    },
    4: {
        "A": (-1.0, 0.0), "B": (0.0, 1.0), "D": (1.0, 1.0),
        "G": (2.0, 1.0), "S": (0.0, -1.0), "E": (1.0, -1.0),
        "H": (2.0, -1.0), "Z": (3.0, 0.0),
    },
}


def posiciones_del_corte(corte):
    """Separa S a la izquierda y T a la derecha sin cambiar la red ni su flujo."""
    posiciones = {}
    # Una columna por conjunto evita que una arista del corte pase sobre
    # un nodo intermedio que no sea su extremo.
    for grupo, x in [(corte["S"], -0.65), (corte["T"], 0.65)]:
        for i, nodo in enumerate(grupo):
            y = 0.0 if len(grupo) == 1 else 0.85 - 1.7 * i / (len(grupo) - 1)
            posiciones[nodo] = (x, y)
    return posiciones
