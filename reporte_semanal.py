"""Reporte semanal automático por correo.

Lee ventas.csv, resume la última semana completa contra la anterior, arma un correo HTML
con un gráfico incrustado y lo envía por SMTP. Con --dry-run no envía nada: guarda
reporte.html y reporte.eml para revisarlos.

Uso:
    python reporte_semanal.py --dry-run
    python reporte_semanal.py                 # envía (requiere variables de entorno)
    python reporte_semanal.py --hasta 2026-10-25   # semana que termina en esa fecha (domingo)
"""
from __future__ import annotations

import argparse
import io
import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

AZUL, GRIS, ROJO, VERDE = "#2a6f97", "#8d99ae", "#c8553d", "#3a9d6e"


def cargar(ruta: str) -> pd.DataFrame:
    df = pd.read_csv(ruta, parse_dates=["fecha"])
    df["ingreso"] = df["cantidad"] * df["precio_unitario"] * (1 - df["descuento"])
    return df


def semana_objetivo(df: pd.DataFrame, hasta: str | None):
    """Devuelve (inicio, fin) de la última semana completa lunes-domingo."""
    if hasta:
        fin = pd.Timestamp(hasta)
    else:
        ult = df["fecha"].max()
        # si el último dato no es domingo, la semana en curso está incompleta
        fin = ult if ult.weekday() == 6 else ult - pd.Timedelta(days=ult.weekday() + 1)
    return fin - pd.Timedelta(days=6), fin


def resumen(df, ini, fin):
    s = df[(df.fecha >= ini) & (df.fecha <= fin)]
    return {
        "ingresos": s.ingreso.sum(),
        "pedidos": s.order_id.nunique(),
        "clientes": s.cliente_id.nunique(),
        "ticket": s.ingreso.sum() / max(s.order_id.nunique(), 1),
        "datos": s,
    }


def var(a, b):
    return (a / b - 1) * 100 if b else float("nan")


def flecha(v):
    color = VERDE if v >= 0 else ROJO
    signo = "▲" if v >= 0 else "▼"
    return f'<span style="color:{color};font-weight:600">{signo} {v:+.1f}%</span>'


def grafico_diario(actual, anterior) -> bytes:
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    a = actual.groupby(actual.fecha.dt.weekday)["ingreso"].sum().reindex(range(7), fill_value=0) / 1e6
    b = anterior.groupby(anterior.fecha.dt.weekday)["ingreso"].sum().reindex(range(7), fill_value=0) / 1e6
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(dias, b.values, color=GRIS, lw=2, marker="o", label="Semana anterior")
    ax.plot(dias, a.values, color=AZUL, lw=2.6, marker="o", label="Esta semana")
    ax.set_ylabel("Millones COP")
    ax.set_title("Ingresos por día", fontweight="bold")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e9ef")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def construir_html(ini, fin, cur, prev, cid: str) -> str:
    top = (
        cur["datos"].groupby("producto")["ingreso"].sum().sort_values(ascending=False).head(5)
    )
    filas = "".join(
        f'<tr><td style="padding:6px 8px;border-bottom:1px solid #eee">{p}</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">${v:,.0f}</td></tr>'
        for p, v in top.items()
    )
    def tarjeta(titulo, valor, delta):
        return (
            f'<td style="padding:12px;border:1px solid #e6e9ef;border-radius:8px;width:25%">'
            f'<div style="font-size:11px;color:#6b778c;text-transform:uppercase">{titulo}</div>'
            f'<div style="font-size:20px;font-weight:700;color:#1b2a41">{valor}</div>'
            f'<div style="font-size:12px">{delta}</div></td>'
        )
    tarjetas = (
        tarjeta("Ingresos", f"${cur['ingresos'] / 1e6:,.1f} M", flecha(var(cur["ingresos"], prev["ingresos"])))
        + tarjeta("Pedidos", f"{cur['pedidos']:,}", flecha(var(cur["pedidos"], prev["pedidos"])))
        + tarjeta("Ticket promedio", f"${cur['ticket']:,.0f}", flecha(var(cur["ticket"], prev["ticket"])))
        + tarjeta("Clientes", f"{cur['clientes']:,}", flecha(var(cur["clientes"], prev["clientes"])))
    )
    mejor = cur["datos"].groupby(cur["datos"].fecha.dt.date)["ingreso"].sum().idxmax()
    return f"""<html><body style="font-family:Arial,sans-serif;color:#1b2a41;max-width:680px;margin:auto">
<h2 style="margin-bottom:2px">Resumen semanal de ventas</h2>
<p style="color:#6b778c;margin-top:0">Del {ini:%d/%m/%Y} al {fin:%d/%m/%Y} · comparado con la semana anterior</p>
<table cellspacing="8" style="width:100%"><tr>{tarjetas}</tr></table>
<img src="cid:{cid}" style="width:100%;margin:12px 0" alt="Ingresos por día">
<p>El mejor día fue el <b>{mejor:%d/%m}</b>.</p>
<h3 style="margin-bottom:4px">Top 5 productos</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px">{filas}</table>
<p style="color:#8d99ae;font-size:12px;margin-top:24px">Reporte generado automáticamente. Datos de ejemplo.</p>
</body></html>"""


def construir_correo(html, png, asunto, remitente, destinatarios, cid) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = asunto, remitente, ", ".join(destinatarios)
    msg.set_content("Tu cliente de correo no muestra HTML. Abre este mensaje en un cliente compatible.")
    msg.add_alternative(html, subtype="html")
    msg.get_payload()[1].add_related(png, "image", "png", cid=f"<{cid}>")
    return msg


def enviar(msg: EmailMessage) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="ventas.csv")
    ap.add_argument("--hasta", help="Domingo en que termina la semana (AAAA-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="No envía; guarda reporte.html y reporte.eml")
    a = ap.parse_args()

    df = cargar(a.datos)
    ini, fin = semana_objetivo(df, a.hasta)
    cur = resumen(df, ini, fin)
    prev = resumen(df, ini - pd.Timedelta(days=7), fin - pd.Timedelta(days=7))
    png = grafico_diario(cur["datos"], prev["datos"])
    cid = make_msgid(domain="reporte.local")[1:-1]
    html = construir_html(ini, fin, cur, prev, cid)
    asunto = f"Resumen semanal de ventas · {ini:%d/%m} al {fin:%d/%m}"
    remitente = os.environ.get("MAIL_FROM", "reportes@ejemplo.com")
    destinos = [d.strip() for d in os.environ.get("MAIL_TO", "cliente@ejemplo.com").split(",")]
    msg = construir_correo(html, png, asunto, remitente, destinos, cid)

    if a.dry_run:
        with open("reporte.html", "w", encoding="utf-8") as f:
            f.write(html.replace(f"cid:{cid}", "grafico.png"))
        with open("grafico.png", "wb") as f:
            f.write(png)
        with open("reporte.eml", "wb") as f:
            f.write(bytes(msg))
        print(f"[dry-run] {asunto}\nGuardados: reporte.html, grafico.png, reporte.eml")
    else:
        enviar(msg)
        print(f"Enviado a {', '.join(destinos)}: {asunto}")


if __name__ == "__main__":
    main()
