# Handoff a Codex — Ader Oficina · Casa Ángel

Estado al 30/10/2026, 17:00 (-03). No contiene credenciales. No se descartó ningún cambio pendiente.

## 1. Proyecto y repositorio

| | |
|---|---|
| Repo | `https://github.com/ezeader/OFICINA_VIRTUAL` (rama base `main`, `2d9dca4`) |
| Checkout principal | `C:\Users\ezead\Desktop\OFICINA_VIRTUAL` → rama `claude/office-efficiency` (trae este handoff) |
| Worktree web (integración) | `.claude\worktrees\aberturas-oficina-354ffd` → `claude/aberturas-oficina-354ffd` @ `296f584`. Pusheada. Tiene mergeadas **todas** las ramas de rubros de la tabla de abajo. |
| Worktree Revit | `.claude\worktrees\revit-rubros-d67c29` → `claude/revit-rubros-d67c29` @ `73e9361` (pusheada) |
| Carpeta Revit / scripts | `C:\Users\ezead\Documents\Codex\2026-10-20\c-users-ezead-documents-codex-2026\` (`work\casa-angel-dimensioning`, `outputs\casa-angel`) |

Ramas por rubro. Cada chat de rubro trabaja en su worktree; todas están pusheadas y mergeadas en la integración:

| Rubro | Rama | Último commit |
|---|---|---|
| Parrilla | `claude/rubro-parrilla` | `e527ff3` |
| Gas | `claude/cool-shtern-660ca4` | `fa6789f` |
| Equipamiento + Mesadas | `claude/compassionate-tereshkova-c097a4` | `f1141c9` |
| Solar | `claude/cool-knuth-346fc8` | `4956025` |
| Exteriores | `claude/exciting-archimedes-fc155e` | `21f9e07` |
| Albañilería | `claude/loving-carson-ff6df4` | `a5dfb69` |
| Eléctrica | `claude/nifty-ellis-ac6226` | `2690d93` |
| Pisos | `claude/recursing-euler-9b7705` | `9c21d6b` |
| Domótica | `claude/rubro-domotica-99b8c4` | sin commits propios |
| Ascensor | `claude/rubro-ascensor-84b8cb` | sin commits propios |

Flujo: cada rama de rubro (y la de Revit, que genera manifests y láminas en `public/casa-angel/rubros/**`) se mergea en `claude/aberturas-oficina-354ffd`, que es la que sirve la oficina. Nada está en `main` ni hay PR abierto.

Stack: vinext 1.0.0-beta.5 (Vite 8), Next 16.3.4, React 19, Drizzle, Cloudflare Worker con D1 `DB` y R2 `BUCKET`. **No editar `.openai/hosting.json`** (apunta a producción).

## 2. Cómo correrlo

- Oficina de integración: `http://localhost:5180`, con `node scripts/run-framework.mjs dev -- --port 5180` desde el worktree de aberturas. Si se agrega una carpeta nueva en `public/`, reiniciar el servidor (si no, da 404).
- El checkout principal sirve `http://127.0.0.1:5173` con `corepack pnpm run dev` (ver `.claude/launch.json`).
- Login local simulado: `/signin-with-chatgpt?return_to=/` (usuario `local_seedy`). La cookie es por host.
- Datos reales: `respaldos/ader-respaldo-2026-10-23.json`, ignorado en git. Ya está importado en el D1 local (ver `RESPALDO.md`).
- Tests: `node --test tests/*.test.mjs scripts/*.test.mjs` → 69/69 en `296f584`.
- Build: `pnpm run build` falla en `document-assets --check` por diferencias CRLF/LF. Para compilar se usó `node node_modules/vinext/dist/cli.js build`. No regenerar `lib/document-assets.json` sin revisar.

## 3. Estado por rubro (Casa Ángel)

Todo publicado en 5180 (`#documentacion/angel/<rubro>`). Las láminas y partidas salen de cada `manifest.json`.

| Rubro | Láminas / partidas | Estado |
|---|---|---|
| Aberturas | planilla | Planilla de carpinterías por sector con dibujo acotado y código. |
| Cielorrasos | 5 / 10 | Terminado (R30). |
| Cubierta | 8 / 24 | Terminado (R31); se quitaron las láminas R16 del modelo previo. |
| Estructura | — / — | Platea PL-01 + PL-02; LO-PB-01 como paquete de piso de 11 cm. |
| Climatización | 37 / 9 | Etapas 1–3 hechas (plantas, colectores, 26 fichas por circuito). |
| Parrilla | 6 / 17 | Parrilla de obra en su DOC; conductos a la vista negro mate, doble pared; pase 0,50×0,50 en losa L01 modelado (OK usuario). |
| Equipamiento | 36 / 13 | Decisiones 1–4 cerradas: melamina 18 mm, placares y racks integrados. |
| Mesadas | 0 / 5 | Rubro nuevo; las mesadas de piedra salieron de Equipamiento. |
| Pisos | 17 / 9 | Lógica por categorías A–E; porcelanato en locales húmedos. |
| Albañilería | 14 / 5 | Muros en 3 categorías (H° visto / ext-int / int-int). La sesión de Revit era la próxima en trabajarlo. |
| Exteriores | 7 / 10 | Solados, cerco medianero 74,25 ml, tranquera, extracción de 12 pinos. |
| Revestimientos | 13 / 4 | **Propuesta a confirmar**; esperan respuestas del usuario. |
| Pileta | 4 / 5 | Con preguntas abiertas. |
| Gas | 0 / 1 | Etapa 1 con GLP aprobada; el chat ahora **recomienda red pública** (3–4× más barata) y espera el OK. |
| Eléctrica | 0 / 2 | Proyecto propio; división de alcance con Domótica. |
| Domótica | 0 / 1 | Sistemas definidos (iluminación con sensores, cortinas, losa radiante, cámaras, AP, audio, accesos, riego). **En pausa:** el usuario va a dibujar el primer esquema de ubicación. |
| Solar | 0 / 1 | Fotovoltaico como dirección provisoria; se define al final. |
| Ascensor | — | El PVE52 no entra. El usuario eligió la opción A: correr el tabique 10 cm y hacer una linterna sobre el pasadizo. **Falta su confirmación directa en el chat de Revit** para tocar el modelo principal. |
| Presupuesto | `#presupuesto/angel` | Partidas sin doble cómputo, todavía sin precios. |

Antes de publicar en ChatGPT Sites hay que pasar todo a `main`; todavía no se hizo.

## 4. Cambios sin commitear (no descartar)

- **Worktree Revit:** 99 `.svg.gz` sin trackear en `public/casa-angel/rubros/equipamiento/` (vistas EQ-F-* exportadas). Revisar si van con el manifest de Equipamiento.
- **Worktree `dazzling-lehmann-b707db`:** `public/casa-angel/rubros/revestimientos/manifest.json` modificado; es trabajo en curso del chat de Revestimientos.
- **Worktree `great-euler-3bb143`:** `public/casa-angel/rubros/pileta/manifest.json` modificado; es trabajo en curso del chat de Pileta.
- `tsconfig.tsbuildinfo` modificado en varios worktrees (artefacto de build).
- **Checkout principal:** `.claude/` (`launch.json`, worktrees).

## 5. Estado de Revit

- Modelo principal: `outputs\casa-angel\Casa-Angel-piloto-documentacion.rvt`, de unos 264 MB. Ya se le hizo una limpieza por rubro con OK del usuario (R33): Cielorrasos, Climatización, Estructura, Cubierta y R16. El peso que queda está en geometría y familias; una auditoría de familias y materiales quedó propuesta, sin respuesta.
- Criterio: **un .rvt de documentación por rubro**, que vincula el principal, en `outputs\casa-angel\documentacion\`. Cada uno pesa unos 4 MB:
  - `Casa-Angel-DOC-Cielorrasos.rvt`
  - `Casa-Angel-DOC-Cubierta.rvt`
  - `Casa-Angel-DOC-Estructura.rvt`
  - `Casa-Angel-DOC-Climatizacion.rvt`
  - `Casa-Angel-DOC-Parrilla.rvt`
  - `Casa-Angel-DOC-Domotica.rvt`
- Puente pyRevit:
  - Trabajo `switch-document`: abre y activa un archivo de `outputs\casa-angel\`, y cierra y guarda el anterior.
  - **Manejo de fallas (R37, `73e9361`):** los warnings se borran solos; los "no puede mantener unidos" se resuelven desuniendo; cualquier otro error hace rollback. Nunca borra elementos por su cuenta. Todo queda registrado en `openings-r4/failures.jsonl`. El archivo de trabajo compartido solo se escribe cuando Revit está libre.
  - Origen de los errores de unión: los símbolos de Domótica estaban dibujados como dos medios arcos con extremos compartidos. Ahora son arcos únicos.
- Cambios de geometría en el principal, todos con OK del usuario y backup en `outputs\casa-angel\backups\`:
  - Cielorrasos R30.
  - Platea PL-02.
  - LO-PB-01: paquete de 11 cm.
  - Parrilla: K42DB reemplazado y pase en la losa L01.
- Hay copias automáticas `.0001`…`.0643` en `outputs\casa-angel\` y en `documentacion\`; se pueden borrar a mano.

## 6. Próximas tareas

1. Ascensor: confirmar la opción A en el chat de Revit y modelarla.
2. Domótica: esperar el esquema del usuario y arrancar por el sistema que elija (iluminación va en un plano aparte).
3. Gas: OK del usuario para pasar a red pública.
4. Revestimientos y Pileta: cerrar sus preguntas abiertas.
5. Albañilería: pasarla a su DOC (un rubro por vez).
6. Decidir qué hacer con los 99 `.svg.gz` de Equipamiento.
7. Presupuesto: cargar precios (base vs opcionales).
8. Integración: PR de `claude/aberturas-oficina-354ffd` a `main`, cuando el usuario lo pida.

## 7. Problemas conocidos

- Los cambios de tipo de piso o losa en el principal pueden recalcular más de 2 h. Conviene hacer transacciones chicas y fijar un tiempo máximo.
- Un diálogo modal de Revit (por ejemplo "Manage Links") bloquea los trabajos hasta que el usuario lo cierra. R37 cubre los diálogos de fallas, no los de interfaz.
- Las sesiones en modo auto no aceptan aprobaciones reenviadas: el usuario tiene que aprobar en la sesión que toca el modelo.
- Un vínculo no permite colorear elementos sueltos. Los DOC resaltan con regiones o líneas.
- CRLF/LF rompe `document-assets --check`. Ver sección 2.
- `lib/documentation-route.ts` importa `./rubros` sin extensión. Vite lo resuelve; en Node, el test usa un hook de resolución (`296f584`).
- El plugin MCP de GitHub no conecta porque la cabecera de autorización es inválida. Usar `git`/`gh`.

## 8. Reglas del usuario

- Responder en español, breve. En cada entrega, primero si terminó y qué necesita, y después el link local a la sección cambiada.
- Documentación con formato de Sanitarias: grilla de láminas, botón por dibujo, etiquetas de local y elementos, tipografía Bahnschrift SB Condensed.
- Cualquier cambio de geometría o borrado en el modelo necesita OK explícito y backup previo.
- Un rubro por vez y un chat por rubro; si un archivo queda pesado, optimizarlo antes de seguir.
- No modificar los subtítulos ni los guiones de los videos (otra sesión, con su propia tarea horaria).
