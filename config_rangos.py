"""
Rangos de temperatura aceptables por sede y cámara.
Cada entrada es una tupla (min, max) en °C.
Si min == max, se interpreta como un valor máximo aceptable (<=).
"""

RANGOS_TEMPERATURA = {
    "Fontibón": {
        "1":                    (-25, -16),
        "2":                    (-25, -16),
        "3":                    (-25, -16),
        "5":                    (0, 4),
        "7":                    (0, 4),
        "10":                   (-25, -18),
        "11":                   (-25, -18),
        "15":                   (0, 4),
        "16":                   (None, 25),   # Max. 25°C
        "17":                   (0, 4),
        "A01":                  (-25, -18),
        "Devoluciones":         (0, 4),
        "Prec. A01":            (-12, -8),
        "Bahía A01":            (8, 15),
        "Pre Cong. 10 y 11":    (-16, -12),
        "Pre Refrig.":          (0, 6),
        "Pre Cong.1":           (-16, -12),
        "Bahía OPL":            (8, 14),
    },
    "Pereira": {
        "Contenedor #1":        (None, -18),  # <= -18°C
        "Contenedor #2":        (None, -18),
        "Contenedor #3":        (None, -18),
        "Contenedor #4":        (None, -18),
        "Cava Refrigerado":     (0, 0),       # 0.0°C exacto -> tolerancia aplicada abajo
    },
    "Funza": {
        "Precámara de refrigeración":             (0, 5),     # ~3.0°C
        "Cámara de refrigeración":                (0, 4),     # ~1.8°C
        "Pre-cámara de congelación":              (-18, -12), # ~-15.0°C
        "Cámara de congelación 1 (RICH'S)":       (-25, -18), # ~-22.0°C
        "Cámara de congelación 2 (ANTILLANA)":    (-25, -18), # ~-22.0°C
        "Túnel de Congelación #1":                (-28, -20), # ~-24.0°C
        "Túnel de Congelación #2 (RICH'S)":       (-32, -24), # ~-28.0°C
    },
    "Cali": {
        "Precámara de fruver":          (8, 12),
        "Cámara de fruver 1":           (8, 12),
        "Cámara de refrigerado 1":      (0, 4),
        "Cámara de refrigerado 2":      (0, 4),
        "Precámara de refrigerado":     (0, 4),
        "Cámara de congelado 1":        (-20, -18),
        "Cámara de congelado 2":        (-20, -18),
        "Cámara de congelado 3":        (-20, -18),
    },
    "Galapa": {
        "Pasillo 403":             (-20, -18),
        "Pasillo 402":             (-20, -18),
        "Pasillo 401":             (-20, -18),
        "Pasillo 301":             (-20, -18),
        "Pasillo 201":             (0, 4),
        "Pasillo 101":             (0, 4),
        "Precava Refrigerado":     (0, 4),
        "Precava Congelado":       (None, -10),  # <= -10°C
        "Bahía":                   (None, 16),    # <= 16°C
    },
}


def verificar_cumplimiento(sede_nombre: str, camara_nombre: str, temperatura: float) -> dict:
    """
    Verifica si la temperatura registrada cumple con el rango esperado.
    
    Returns:
        dict con claves: cumple (bool), rango (str), mensaje (str)
    """
    rangos_sede = RANGOS_TEMPERATURA.get(sede_nombre)
    if not rangos_sede:
        return {
            "cumple": None,
            "rango": "No definido",
            "mensaje": f"No hay rango definido para la sede '{sede_nombre}'"
        }

    rango = rangos_sede.get(camara_nombre)
    if not rango:
        return {
            "cumple": None,
            "rango": "No definido",
            "mensaje": f"No hay rango definido para la cámara '{camara_nombre}'"
        }

    temp_min, temp_max = rango

    # Build range string
    if temp_min is None:
        rango_str = f"<= {temp_max}°C"
        cumple = temperatura <= temp_max
    elif temp_min == temp_max:
        rango_str = f"{temp_min}°C"
        cumple = abs(temperatura - temp_min) <= 2  # 2° tolerance for exact values
    else:
        rango_str = f"{temp_min} a {temp_max}°C"
        cumple = temp_min <= temperatura <= temp_max

    if cumple:
        mensaje = f"Temperatura en cumplimiento (rango: {rango_str})"
    else:
        mensaje = f"Temperatura fuera de rango (esperado: {rango_str}, registrado: {temperatura}°C)"

    return {
        "cumple": cumple,
        "rango": rango_str,
        "mensaje": mensaje
    }
