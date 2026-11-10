# Despliegue de HidroSopó v1.2: GitHub → Supabase → Render → Netlify

Guía para dejar todo publicado, conectado y actualizándose solo. Tiempo: **≈ 60–90 minutos** la primera vez. Después, cada actualización es un `git push`.

## Cómo queda

```
           git push
GitHub ──────────────┬──────────────────────────────┐
(código + pruebas)   │                              │
                     ▼                              ▼
              Render (API FastAPI)          Netlify (sitio estático)
              /api/v1/...                   /            app del productor
                     │                      /laboratorio gemelo digital y pruebas
                     │  pooler IPv4         /agua        Sopó Cuida el Agua
                     ▼                      /resultados  página del jurado
              Supabase (PostgreSQL)         /api/*  ──►  reenvía a Render (sin CORS)
                     ▲
       ESP32 ────────┘ (POST /api/v1/telemetria)

GitHub Actions: corre las 102 pruebas en cada push y mantiene despiertos Render y Supabase.
```

| Servicio | Tu proyecto | Qué hace |
|---|---|---|
| GitHub | `alejopulidog-prog/Hidrosopo` | Código. Hoy está en la v1.0 del 14/09; se reemplaza por la v1.2 |
| Supabase | proyecto `eulaxkekwsxbajxonqwy` | Base de datos |
| Render | servicio `srv-daadakks728c7382hs4g` | API, IA y asistente |
| Netlify | proyecto `hidrosopo` | App, laboratorio y comunidad |

> **El repositorio es público.** La v1.2 ya saca de GitHub tu cédula (`datos_personales.json`), los informes con firma (`09_entregables/informes/`), la clave del WiFi (`secretos.h`) y la clave de la base (`.env`). Antes de cada `git push`, revisa `git status`: ninguno de esos debe aparecer.

---

## Paso 1 · Subir la v1.2 a GitHub (15 min)

Necesitas [Git](https://git-scm.com/downloads) instalado. Descomprime `HidroSopo_v12.zip` en una carpeta temporal.

**Windows (PowerShell):**
```powershell
cd $HOME\Documents
git clone https://github.com/alejopulidog-prog/Hidrosopo.git
cd Hidrosopo
# borra todo lo viejo menos el historial (.git)
Get-ChildItem -Force | Where-Object { $_.Name -ne '.git' } | Remove-Item -Recurse -Force
# copia el contenido NUEVO (ajusta la ruta a donde descomprimiste)
Copy-Item -Recurse -Force "$HOME\Downloads\HidroSopo_v12\hidrosopo\*" .
Copy-Item -Force "$HOME\Downloads\HidroSopo_v12\hidrosopo\.*" . -ErrorAction SilentlyContinue
git add -A
git status
```

**Mac o Linux:**
```bash
git clone https://github.com/alejopulidog-prog/Hidrosopo.git && cd Hidrosopo
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R ~/Downloads/HidroSopo_v12/hidrosopo/. .
git add -A && git status
```

Revisa la lista de `git status`. **No** deben aparecer `.env`, `secretos.h`, `datos_personales.json`, `hidrosopo.db` ni `09_entregables/informes/`. Si aparecen, no sigas: revisa que el `.gitignore` se haya copiado.

```bash
git commit -m "HidroSopó v1.2: gemelo digital, laboratorio, Sopó Cuida el Agua y despliegue"
git tag v1.2.0
git push && git push --tags
```

✅ En GitHub, pestaña **Actions**, el flujo **Pruebas** debe terminar en verde (102 pruebas).

---

## Paso 2 · Supabase (15 min)

### 2.1 La cadena de conexión correcta

Render no tiene IPv6 de salida, y la conexión directa de Supabase (`db.xxxx.supabase.co:5432`) es solo IPv6 en el plan gratuito. Si usas esa, Render falla con *Network is unreachable*. Hay que usar el **pooler**:

1. Abre tu proyecto en Supabase → botón **Connect** (arriba).
2. Pestaña **Connection string** → tipo **URI** → **Transaction pooler**.
3. Copia la cadena. Se ve así:
   `postgresql://postgres.eulaxkekwsxbajxonqwy:[YOUR-PASSWORD]@aws-0-XX-XXXX-X.pooler.supabase.com:6543/postgres`
4. Reemplaza `[YOUR-PASSWORD]` por la clave de la base. Si no la recuerdas: **Project Settings → Database → Reset database password**. Si la clave tiene símbolos como `@`, `#` o `/`, mejor genera una solo con letras y números.

Guárdala en un lugar seguro. **Nunca** la pegues en un archivo que vaya a GitHub.

### 2.2 Cerrar la puerta de la API pública

Supabase publica automáticamente las tablas del esquema `public` por su API REST. Si no tienen RLS (seguridad por filas), cualquiera con la clave pública del proyecto podría leerlas o modificarlas. El backend entra como dueño de la base, así que activar RLS no lo afecta.

**SQL Editor → New query**, pega y ejecuta (**Run**):

```sql
do $$
declare t record;
begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t.tablename);
  end loop;
end $$;
```

Vuelve a ejecutarlo si en el futuro el backend crea tablas nuevas. En **Advisors → Security Advisor** no debe quedar ningún aviso de «RLS disabled».

### 2.3 ¿Qué datos tiene la base?

Las tablas las crea el backend solo la primera vez que arranca. Si la base está vacía, la app muestra el predio de demostración. Para que la plataforma muestre el gemelo digital desde el servidor, carga los datos simulados **desde tu computador**:

```powershell
cd Hidrosopo\03_backend
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://postgres.eulaxk...:CLAVE@aws-0-...pooler.supabase.com:6543/postgres"
python cargar_datos_prueba.py
```
(Mac/Linux: `export DATABASE_URL="..."`.)

Con `FUENTE_DATOS=simulacion` en Render (paso 3), la app los rotula **«gemelo digital»** y no los hace pasar por datos de campo.

---

## Paso 3 · Render (15 min)

Abre tu servicio → **Settings**.

### 3.1 Construcción

| Campo | Valor |
|---|---|
| Repository / Branch | `alejopulidog-prog/Hidrosopo` · `main` |
| Root Directory | `03_backend` |
| Runtime | **Docker** (recomendado: usa el `Dockerfile` del repo) |
| Dockerfile Path | `./Dockerfile` |
| Health Check Path | `/api/v1/salud` |
| Auto-Deploy | **On Commit** |

Si tu servicio se creó como **Python** y no quieres cambiarlo:
Build Command `pip install -r requirements.txt` · Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT` · y agrega la variable `PYTHON_VERSION=3.12.8`.

### 3.2 Variables de entorno

En **Environment** (tu enlace `…/env`):

| Variable | Valor |
|---|---|
| `DATABASE_URL` | la cadena del **Transaction pooler** (paso 2.1) |
| `CORS_ORIGINS` | `https://hidrosopo.netlify.app` (tu dominio de Netlify) |
| `FUENTE_DATOS` | `simulacion` (cámbialo a `campo` cuando reporte el nodo real) |
| `CANAL_ALERTAS` | `consola` |
| `LLM_PROVEEDOR` | `ninguno` |
| `TZ` | `America/Bogota` |

**Save Changes** → arriba a la derecha **Manual Deploy → Clear build cache & deploy**.

### 3.3 Comprobar

Copia la URL del servicio (arriba, tipo `https://hidrosopo.onrender.com`) y abre:

- `…/api/v1/salud` → debe decir `"estado": "ok"`, `"version": "1.4.0"` y `"fuente_datos": "simulacion"`.
- `…/docs` → la documentación interactiva de la API.

La primera visita tras un rato puede tardar unos 50 segundos: el plan gratuito duerme el servicio y lo despierta con la visita. El paso 5 lo mantiene despierto.

> **Si tu URL de Render NO es `hidrosopo.onrender.com`**, cámbiala en: `netlify.toml` (redirect `/api/*`), `04_dashboard/index.html` (constante `API`), `render.yaml`, `02_firmware/src/config.h` y la variable de GitHub del paso 5. Luego haz commit y push.

---

## Paso 4 · Netlify (10 min)

### 4.1 Conectar el repo (si hoy despliegas arrastrando la carpeta)

**Project configuration → Build & deploy → Continuous deployment → Link repository** → GitHub → `Hidrosopo`. Deja vacíos *Base directory* y *Build command*: el `netlify.toml` del repo ya dice que publique `04_dashboard`. **Deploy**.

### 4.2 Nombre del sitio

**Project configuration → General → Project details → Change project name** → `hidrosopo`. Queda `https://hidrosopo.netlify.app`. Si ese nombre está tomado, usa otro y actualiza `CORS_ORIGINS` en Render.

### 4.3 Comprobar

| Dirección | Qué debe mostrar |
|---|---|
| `https://hidrosopo.netlify.app/` | App del productor; con el aviso «gemelo digital» si hay datos simulados |
| `/laboratorio` | Simulador de riego, pruebas en banco y estado del proyecto |
| `/agua` | Sopó Cuida el Agua: huerta, lluvia, hogar, escuela y PUEAA |
| `/resultados` | Página para el jurado |
| `/api/v1/salud` | El mismo JSON de Render, a través de Netlify |

En el celular: abre la app → menú del navegador → **Agregar a pantalla de inicio**.

---

## Paso 5 · GitHub Actions: pruebas y «mantener activo» (5 min)

1. GitHub → repo → **Settings → Secrets and variables → Actions → Variables → New repository variable**:
   `HIDROSOPO_API` = tu URL de Render (sin `/` al final).
2. Pestaña **Actions** → **Mantener activo** → **Run workflow** para probarlo.

Hace tres cosas:
- Llama a `/api/v1/salud` cada 14 minutos de 6 a. m. a 11 p. m. Así Render no se duerme y Supabase no pausa el proyecto por inactividad.
- Genera y guarda la recomendación del día a las 6:00 a. m.
- Corre las 102 pruebas en cada push (flujo **Pruebas**).

GitHub desactiva las tareas programadas de un repo público tras 60 días sin commits. Si pasa, el botón **Enable workflow** las reactiva.

---

## Paso 6 · Firmware del ESP32 (5 min)

1. En `02_firmware/src/`, copia `secretos.h.example` como `secretos.h` y pon el nombre y la clave del WiFi. Ese archivo no se sube a GitHub.
2. `BACKEND_URL` ya apunta a `https://hidrosopo.onrender.com/api/v1/telemetria`. Si tu URL es otra, defínela en `secretos.h`.
3. Compila y sube con PlatformIO. En `…/api/v1/salud` debe aparecer el nodo con `"en_linea": true`.

**Prueba real que puedes hacer ya con la ESP32:** sube el firmware y deja la placa enviando. Cada envío queda en Supabase con la hora, y la intensidad de señal a 5, 10, 20 y 30 m del router sirve para el Avance 2.

---

## Paso 7 · QR del póster y del plegable apuntando a Netlify (5 min)

En `09_entregables/poster/config.json` cambia:
```json
"url_qr": "https://hidrosopo.netlify.app/laboratorio",
"url_plegable": "https://hidrosopo.netlify.app/agua"
```
y regenera:
```bash
cd 09_entregables/poster && python generar_poster.py
cd ../plegable && python generar_plegable.py
```
**Escanea los dos QR con el celular antes de imprimir.**

---

## Paso 8 (opcional) · Asistente con conversación libre (10 min, $0)

El asistente ya responde como experto sin internet: recomendación, riego, heladas, ahorro y 32 temas técnicos. Con este paso, además conversa libremente cuando le preguntan algo fuera de esas reglas. Usa un modelo de IA generativa gratuito y **siempre con las cifras que calcula el sistema**: el modelo redacta, no inventa números.

1. Crea una cuenta gratis en **console.groq.com** → **API Keys** → **Create API Key**. Copia la clave (empieza por `gsk_`).
2. En Render → **Environment**:
   - `LLM_PROVEEDOR` = `groq`
   - `GROQ_API_KEY` = la clave que copiaste
3. **Save Changes**. Render se reinicia solo.
4. Prueba en la app → **Cuénteme** → algo libre, como «¿qué le puedo sembrar a una huerta en tierra fría?».

Si en los **Logs** de Render aparece que el modelo no existe, en la consola de Groq mira qué modelos hay disponibles y agrega `GROQ_MODEL` = ese nombre. La clave **nunca** va en GitHub, solo en Render. Para apagarlo: `LLM_PROVEEDOR` = `ninguno`.

---

## Cómo se actualiza de aquí en adelante

```bash
# 1. cambias algo
cd 03_backend && pytest -q        # 2. compruebas que todo pase
git add -A && git status          # 3. revisas que no vaya nada privado
git commit -m "qué cambiaste"
git push                          # 4. Render y Netlify se actualizan solos
```

- **Volver a la versión anterior.** En Render: **Events** → elige un despliegue anterior → **Rollback**. En Netlify: **Deploys** → elige uno → **Publish deploy**.
- **La app del celular sigue mostrando lo viejo.** El service worker cambia de versión con cada despliegue. Cierra y abre la app; en el computador, Ctrl + F5.

## Cuando el nodo real empiece a medir (2027)

1. En Supabase (SQL Editor), borra los datos simulados del predio 1:
   ```sql
   delete from lecturas_suelo  where predio_id = 1;
   delete from lecturas_caudal where predio_id = 1;
   delete from recomendaciones where predio_id = 1;
   ```
   (Primero exporta las tablas a CSV si quieres guardarlas: **Table Editor → Export**.)
2. En Render, `FUENTE_DATOS` = `campo` → Save. El aviso de «gemelo digital» desaparece de la app.
3. Tras 4 semanas de datos, reentrena: exporta las lecturas a un CSV con las mismas columnas de `06_datos/datos_sinteticos.csv`, corre `cd 03_backend && python -m ia.modelo_ml --csv ruta/al/archivo.csv`, haz commit de `modelos/` y push.
4. En `poster/config.json`, `"fuente_datos": "campo"` y regenera el póster.

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| Render: *Network is unreachable* o *could not translate host name* | Cadena de conexión directa de Supabase (IPv6) | Usar el **Transaction pooler**, puerto 6543 (paso 2.1) |
| Render: *password authentication failed* | Clave errada o con símbolos | Resetear la clave en Supabase, solo letras y números |
| La app dice «Datos de prueba» en Netlify | La API no responde | Abrir `/api/v1/salud`; si tarda, Render está despertando; revisar **Logs** en Render |
| Error de CORS al abrir la app desde otro dominio | `CORS_ORIGINS` no incluye ese dominio | Agregarlo en Render, separado por coma |
| Supabase: *Project paused* | 7 días sin actividad en el plan gratuito | **Restore project**; el flujo «Mantener activo» lo evita |
| GitHub Actions en rojo | Una prueba falló | Abrir el flujo, ver qué prueba y corregir antes de que Render lo publique |

## Lista final

- [ ] GitHub en v1.2.0 y **Pruebas** en verde
- [ ] Nada privado en el repo (`.env`, `secretos.h`, cédula, informes)
- [ ] Supabase: cadena del pooler y RLS activado sin avisos
- [ ] Render: `/api/v1/salud` → `version 1.4.0`, `fuente_datos simulacion`
- [ ] Netlify: `/`, `/laboratorio`, `/agua`, `/resultados` y `/api/v1/salud` funcionan
- [ ] Variable `HIDROSOPO_API` creada y **Mantener activo** en verde
- [ ] QR del póster y del plegable regenerados con Netlify y probados con el celular
- [ ] Enlace de Netlify y del repositorio actualizados en los correos y en el informe final
