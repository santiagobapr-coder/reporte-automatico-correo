# Reporte semanal automático por correo

Script en Python que convierte el Excel o CSV de ventas en un **correo con el resumen de la semana**
y lo envía solo: ingresos, pedidos, ticket promedio, clientes, comparación contra la semana anterior,
gráfico por día y los 5 productos que más vendieron.

## Qué resuelve

Quien lleva el negocio deja de armar el resumen a mano cada lunes. El correo llega listo, con los
mismos indicadores siempre y la comparación contra la semana anterior.

## Cómo funciona

1. Lee `ventas.csv` (puede adaptarse a Excel con `pd.read_excel`).
2. Detecta la **última semana completa** (lunes a domingo) y la compara con la anterior.
3. Calcula indicadores y dibuja el gráfico diario.
4. Arma el correo HTML con el gráfico incrustado.
5. Lo envía por SMTP, o con `--dry-run` guarda `reporte.html` y `reporte.eml` para revisarlos.

## Uso

```bash
pip install -r requirements.txt

# Probar sin enviar nada
python reporte_semanal.py --dry-run

# Enviar de verdad (configura las variables de .env.example)
export SMTP_HOST=smtp.gmail.com SMTP_USER=... SMTP_PASS=... MAIL_TO=cliente@ejemplo.com
python reporte_semanal.py

# Elegir otra semana (el domingo en que termina)
python reporte_semanal.py --hasta 2026-10-18
```

## Programarlo para que corra solo

- **Windows (Programador de tareas):** acción "Iniciar un programa" → `python` con el argumento
  `C:\ruta\reporte_semanal.py`, desencadenador semanal, lunes 7:00.
- **Linux / Mac (cron):** `0 7 * * 1 cd /ruta/proyecto && python reporte_semanal.py`

## Seguridad

Las credenciales se leen de variables de entorno; nunca van escritas en el código ni en el repositorio.
Agrega `.env` a tu `.gitignore`.

## Tecnologías

Python, pandas, matplotlib, smtplib y email (biblioteca estándar).

> Los datos son de ejemplo (inventados).


## Qué busca (el problema)

Armar el reporte semanal a mano cada lunes toma tiempo y se olvida.

## Cómo se cumple

Genera solo el resumen de la última semana completa vs la anterior (gráfico + top de productos) y lo envía por correo.

## Cómo ofrecerlo como servicio

- **Qué entrego:** Automatización programada (Programador de tareas/cron) con tu correo y tus datos.
- **A quién:** Gerentes y dueños que reportan ventas a socios o equipo cada semana.
- **Precio de referencia (ajustar):** Instalación: 300.000–800.000 COP. Soporte mensual: 100.000–250.000 COP.
- **Frase para empezar:** «Cada lunes a las 7 a.m. te llega el resumen de la semana sin que muevas un dedo.»
- **Flujo:** 1) reunión corta y datos del cliente → 2) prototipo con sus datos → 3) ajustes → 4) entrega y capacitación.

> Datos del repositorio inventados; ejecutar los scripts para reproducir el tablero.

> Para generar `ventas.csv` de ejemplo ejecuta primero `python generate_data.py` (datos inventados).
