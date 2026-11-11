"""Genera datos de ejemplo (inventados) de una tienda online de accesorios deportivos."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

PRODUCTS = [
    ("P01", "Botella térmica 750 ml", "Hidratación", 62000),
    ("P02", "Termo deportivo 1 L", "Hidratación", 78000),
    ("P03", "Mat de yoga antideslizante", "Yoga", 95000),
    ("P04", "Bloques de yoga (par)", "Yoga", 48000),
    ("P05", "Banda elástica set x5", "Fuerza", 54000),
    ("P06", "Mancuernas ajustables 10 kg", "Fuerza", 210000),
    ("P07", "Cuerda para saltar pro", "Cardio", 39000),
    ("P08", "Rodillo de espuma", "Recuperación", 68000),
    ("P09", "Pistola de masaje", "Recuperación", 289000),
    ("P10", "Guantes de gimnasio", "Fuerza", 45000),
    ("P11", "Maleta deportiva 40 L", "Accesorios", 135000),
    ("P12", "Gorra running", "Accesorios", 52000),
    ("P13", "Cinturón lumbar", "Fuerza", 88000),
    ("P14", "Reloj fitness básico", "Tecnología", 169000),
    ("P15", "Audífonos deportivos", "Tecnología", 119000),
    ("P16", "Kit de pesas rusas", "Fuerza", 245000),
    ("P17", "Toalla de microfibra", "Accesorios", 34000),
    ("P18", "Shaker proteína 700 ml", "Hidratación", 29000),
    ("P19", "Colchoneta plegable", "Yoga", 112000),
    ("P20", "Soporte para celular running", "Tecnología", 42000),
]
CHANNELS = ["Sitio web", "Instagram", "WhatsApp", "Marketplace"]
CH_P = [0.38, 0.27, 0.20, 0.15]

dates = pd.date_range("2025-01-01", "2026-10-31", freq="D")
rows = []
order_id = 10000
n_customers = 9000
cust_first = {}

for d in dates:
    months = (d.year - 2025) * 12 + d.month - 1
    growth = 1 + 0.025 * months
    season = {11: 1.45, 12: 1.6, 1: 1.2, 5: 1.15}.get(d.month, 1.0)
    weekday = 1.15 if d.weekday() in (4, 5) else 1.0
    lam = 7.5 * growth * season * weekday
    for _ in range(rng.poisson(lam)):
        order_id += 1
        # clientes recurrentes: 17% vuelven a clientes ya vistos
        if cust_first and rng.random() < 0.17:
            cust = int(rng.choice(list(cust_first.keys())))
        else:
            cust = int(rng.integers(1, n_customers + 1))
        cust_first.setdefault(cust, d)
        channel = rng.choice(CHANNELS, p=CH_P)
        n_items = rng.choice([1, 2, 3], p=[0.62, 0.28, 0.10])
        for _ in range(n_items):
            # algunos productos pierden tracción en 2026 (para alertas)
            weights = np.array([1.0] * len(PRODUCTS))
            weights[[0, 2, 8, 14]] *= 1.8
            if d >= pd.Timestamp("2026-07-01"):
                weights[[3, 9]] *= 0.25
            weights /= weights.sum()
            p = PRODUCTS[rng.choice(len(PRODUCTS), p=weights)]
            qty = int(rng.choice([1, 2, 3], p=[0.78, 0.17, 0.05]))
            disc = float(rng.choice([0, 0.05, 0.10, 0.15], p=[0.7, 0.12, 0.12, 0.06]))
            rows.append(
                (order_id, d.date(), f"C{cust:04d}", p[0], p[1], p[2], channel, qty, p[3], disc)
            )

df = pd.DataFrame(
    rows,
    columns=["order_id", "fecha", "cliente_id", "producto_id", "producto", "categoria",
             "canal", "cantidad", "precio_unitario", "descuento"],
)
df.to_csv("ventas.csv", index=False)
print(f"{len(df):,} líneas, {df.order_id.nunique():,} pedidos, {df.cliente_id.nunique():,} clientes")
