# Actualizar HidroSopó a la v1.5 (Mac)

Tiempo: 5 minutos. No hay que tocar Supabase ni las variables de Render: solo subir el código.

## 1. Descomprimir
Descarga `HidroSopo_v15.zip` y descomprímelo dentro de `Documents/Proyecto CTeI` (si ya existe una carpeta `hidrosopo` vieja, bórrala antes). Comprueba que es la nueva:
```bash
grep -n 'version="1.5.0"' "/Users/alejandropulido/Documents/Proyecto CTeI/hidrosopo/03_backend/main.py"
```
Debe mostrar una línea.

## 2. Copiar, revisar y subir
```bash
cd ~/Documents/Hidrosopo
cp -R "/Users/alejandropulido/Documents/Proyecto CTeI/hidrosopo/." .
git add -A
git status --short | grep -iE "\.env$|datos_personales|informes/|\.docx|\.db$"
```
La última línea **no debe mostrar nada**. Luego:
```bash
git commit -m "HidroSopó v1.5: Mi recibo de agua y navegación unificada"
git push
```

## 3. Qué pasa solo
- **GitHub Actions** corre las 119 pruebas (pestaña Actions, en verde en 2–3 min).
- **Render** reconstruye el servidor (3–6 min).
- **Netlify** publica la app y la página nueva (1 min). El `netlify.toml` ya trae la dirección corta `/recibo`.

## 4. Comprobar
| Abre | Debe mostrar |
|---|---|
| https://hidrosopo.netlify.app/api/v1/salud | `"version": "1.5.0"` |
| https://hidrosopo.netlify.app | en el menú (☰) aparece «Mi recibo de agua» |
| https://hidrosopo.netlify.app/recibo | la página del recibo con la barra «← Volver a la app» |
| En /recibo, los botones «Pagar con PSE», «AvalPayCenter» y «Descargar mi factura» | abren cada portal en una pestaña nueva |
| https://hidrosopo.netlify.app/laboratorio y /agua | la misma barra arriba y el botón flotante «App» al bajar |

En el celular: cierra la app y ábrela de nuevo (la versión del service worker cambió y se actualiza sola).

## Si algo falla
- `salud` sigue en 1.4.0: Render todavía está construyendo; mira **Logs** en Render.
- Netlify en rojo: abre el despliegue y copia las últimas líneas del log.
- Actions en rojo: abre el flujo **Pruebas** y copia el error.

## Cuando haya convenio con Emsersopó (no ahora)
Con los datos que entregue la empresa, en Render → Environment agrega `EMSERSOPO_API_URL`, `EMSERSOPO_API_TOKEN` y `EMSERSOPO_PAGO_URL`, Antes de eso, la consulta responde «se activa con el convenio» y no se muestra ninguna factura que no venga del usuario.

## Si Emsersopó cambia un enlace de pago o de factura
Abre `04_dashboard/recibo.html`, busca `const CANALES` (al inicio del script) y cambia la dirección. Luego `git add -A`, `git commit` y `git push`.
