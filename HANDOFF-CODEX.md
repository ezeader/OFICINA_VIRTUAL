# Handoff a Codex — Ader Oficina · Casa Ángel

Estado al 26/10/2026, 10:01 (-03). No contiene credenciales. No se descartó ningún cambio pendiente.

## 1. Proyecto y repositorio

| | |
|---|---|
| Repo | `https://github.com/ezeader/OFICINA_VIRTUAL` (rama base `main`, `2d9dca4`) |
| Checkout principal | `C:\Users\ezead\Desktop\OFICINA_VIRTUAL` → rama `claude/office-efficiency` (pusheada; trae este handoff; `.gitignore` modificado con `respaldos/`, sin commitear) |
| Worktree web (integración) | `C:\Users\ezead\Desktop\OFICINA_VIRTUAL\.claude\worktrees\aberturas-oficina-354ffd` → `claude/aberturas-oficina-354ffd` @ `10e4bd7` (pusheada, al día con `origin`) |
| Worktree Revit (rubros) | `C:\Users\ezead\Desktop\OFICINA_VIRTUAL\.claude\worktrees\revit-rubros-d67c29` → `claude/revit-rubros-d67c29` @ `1a69dcf` (pusheada, al día con `origin`) |
| Carpeta Revit / scripts | `C:\Users\ezead\Documents\Codex\2026-10-20\c-users-ezead-documents-codex-2026\` (`work\casa-angel-dimensioning`, `outputs\casa-angel`) |

Flujo de ramas: la rama Revit genera manifests y láminas (`public/casa-angel/rubros/**`) y se mergea en `claude/aberturas-oficina-354ffd`, que es la que sirve la oficina. Nada está en `main` ni hay PR abierto.

Stack: vinext 1.0.0-beta.5 (Vite 8), Next 16.3.4, React 19, Drizzle, Cloudflare Worker con D1 `DB` y R2 `BUCKET`. **No editar `.openai/hosting.json`** (apunta a producción).

## 2. Cómo correrlo

- Oficina de la rama de integración: `http://localhost:5180`, que hoy está corriendo desde el worktree de aberturas.
- El checkout principal sirve `http://127.0.0.1:5173` con `corepack pnpm run dev` (ver `.claude/launch.json`).
- Login local simulado: `/signin-with-chatgpt?return_to=/` (usuario `local_seedy`). La cookie es por host.
- Datos reales: `respaldos/ader-respaldo-2026-10-23.json`, ignorado en git. Ya está importado en el D1 local (ver `RESPALDO.md`).
- Tests: `node --test tests/*.test.mjs scripts/*.test.mjs`.
- Build: `pnpm run build` falla en `document-assets --check` por diferencias CRLF/LF. Para compilar se usó `node node_modules/vinext/dist/cli.js build`. No regenerar `lib/document-assets.json` sin revisar.

## 3. Estado por rubro (Casa Ángel)

Todo lo de esta tabla está commiteado y publicado en la oficina de 5180.

| Rubro | Estado | Link |
|---|---|---|
| Aberturas | Planilla de carpinterías por sector con dibujo acotado y código; sin hover. | `#documentacion/angel/aberturas` |
| Revestimientos | **Propuesta a confirmar** (13 láminas, 137 m² de cerámica, 507 m² de pintura). Esperan respuestas del usuario. | `#documentacion/angel/revestimientos` |
| Cielorrasos R30 | Terminado. 23 cielorrasos modelados. RH 69,45 m², ST 166,79 m², buña 290,15 ml, 7 tapas. 5 láminas. | `#documentacion/angel/cielorrasos` |
| Cubierta R30–R31 | Textos sin superposición y detalles D-01…D-04; CUB-D-01a con cotas parciales escalonadas, total y cabio aparte (R31). El presupuesto suma herrajes (226 u) y peine anti-pájaros (90,29 ml). | `#documentacion/angel/cubierta` |
| Estructura R31 | Platea PL-01 + ampliación PL-02 (374 m²). LO-PB-01 pasó a paquete de piso de 11 cm sin hormigón (−0,20/−0,09, sobre la platea). Ficha EST-F-PL-02 hecha. | `#documentacion/angel/estructura` |
| Climatización R32 | Etapas 1 (plantas con serpentina, 14 circuitos a CO-N y 12 a CO-S) y 2 (colectores CLI-CO-N/S) hechas. | `#documentacion/angel/climatizacion` |
| Presupuesto | 94+ partidas sin doble cómputo, todavía sin precios. | `#presupuesto/angel` |

Antes de publicar en ChatGPT Sites hay que pasar todo a `main`; todavía no se hizo.

## 4. Cambios sin commitear (no descartar)

**Worktree aberturas** (`claude/aberturas-oficina-354ffd`): exportación de láminas a PDF por rubro, en curso.
- Archivos modificados:
  - `components/documentation-desk.css`
  - `components/documentation-desk.tsx`
  - `components/project-studio.tsx`
  - `lib/documentation-route.ts`
  - `package.json` (agrega `pdf-lib 1.17.1`)
  - `pnpm-lock.yaml`
  - `tsconfig.tsbuildinfo`
- Archivos nuevos:
  - `components/documentation-export.tsx`
  - `lib/documentation-export.ts`
  - `public/urbetrack/rubros/**`, con los manifests de rubros del proyecto Urbetrack.

**Worktree Revit** (`claude/revit-rubros-d67c29`): 99 `.svg.gz` sin trackear en `public/casa-angel/rubros/equipamiento/`. Son vistas EQ-F-* exportadas que no entraron en ningún commit. Revisar si van con el manifest de Equipamiento.

**Checkout principal**: `.gitignore` (agrega `respaldos/`) y `.claude/` (`launch.json`, worktrees).

## 5. Estado de Revit

- Modelo principal: `outputs\casa-angel\Casa-Angel-piloto-documentacion.rvt`, de unos 263 MB.
- Criterio actual: **un .rvt de documentación por rubro**, que vincula el principal, en `outputs\casa-angel\documentacion\`. Cada uno pesa unos 4 MB:
  - `Casa-Angel-DOC-Cielorrasos.rvt`
  - `Casa-Angel-DOC-Cubierta.rvt`
  - `Casa-Angel-DOC-Estructura.rvt`
  - `Casa-Angel-DOC-Climatizacion.rvt`
- Documento activo al momento del handoff: el DOC de **Cubierta**, porque Revit estaba armando sus detalles. Verificarlo antes de lanzar trabajos.
- Trabajo `switch-document` en el puente pyRevit: abre y activa un archivo de `outputs\casa-angel\` y cierra y guarda el anterior. Tiene el OK del usuario.
- Cambios de geometría aplicados al modelo principal, todos con OK del usuario y backup previo en `outputs\casa-angel\backups\`:
  - Cielorrasos R30: 10 nuevos y 5 con cambio de tipo. CE-PA-03 (Sala TV) queda en ST a 2,70 m; CE-PA-02 (Sala de Máquinas) se borró.
  - Platea ampliada PL-02 bajo LO-PB-01.
  - LO-PB-01: el tipo pasó a paquete de 11 cm y el desfase a −0,09.
- En el principal siguen las vistas y láminas ADER viejas: 1.629 vistas y unas 450 láminas, entre ellas Cubierta R16 con 159 vistas y 42 láminas. **Borrarlas requiere el OK del usuario rubro por rubro.**
- En `documentacion\` hay copias automáticas `.0001`…`.0009` que se pueden borrar a mano.

## 6. Próximas tareas

1. ~~Revit: cotas de CUB-D-01~~ — hecho en `1a69dcf`; falta que la sesión de Cubierta lo revise.
2. Climatización etapa 3: fichas por local. Las etapas siguen el orden pedido; el usuario aprobó continuar.
3. Terminar y commitear la exportación a PDF (sección 4) y verificarla en la oficina.
4. Decidir qué hacer con los 99 `.svg.gz` de Equipamiento.
5. Revestimientos: cerrar la propuesta con las respuestas del usuario.
6. Migrar los rubros restantes a su DOC (Aberturas, Equipamiento, Pisos, Albañilería, Exteriores, Pileta, Revestimientos), **uno por vez**, y pedir OK para limpiar el principal.
7. Presupuesto: cargar precios (base vs opcionales).
8. Integración: PR de `claude/aberturas-oficina-354ffd` a `main`, cuando el usuario lo pida.
9. Elevador: dejar MC-1020586 como pieza real, ajustada a +0,83 / 5,61 y hosteada, y quitar el auxiliar MC-1020050. Definir los extremos redondeados. **Pendiente de OK del usuario.**

## 7. Problemas conocidos

- Los cambios de tipo de piso o losa en el principal pueden recalcular más de 2 h en una sola transacción. La última vez se trabó y terminó sola. Conviene hacer transacciones chicas, revisar antes qué depende del elemento y fijar un tiempo máximo.
- Revit puede quedar bloqueado por diálogos modales, como "Manage Links" al abrir un DOC. Ahí el usuario tiene que cerrarlos a mano.
- Un vínculo no permite colorear elementos sueltos. Los DOC resaltan con regiones o líneas y traducen ids a través del vínculo.
- CRLF/LF rompe `document-assets --check`. Ver sección 2.
- El plugin MCP de GitHub no conecta porque la cabecera de autorización es inválida. Usar `git`/`gh`.
- Las tres ramas están pusheadas; no hay PR abierto.

## 8. Reglas del usuario

- Responder en español, breve. En cada entrega, primero si terminó y qué necesita, y después el link local a la sección cambiada.
- La documentación sigue el formato de Sanitarias: grilla de láminas, botón por dibujo, etiquetas de local y elementos, tipografía Bahnschrift SB Condensed.
- Cualquier cambio de geometría o borrado en el modelo necesita OK explícito y backup previo.
- Un rubro por vez; si un archivo queda pesado, optimizarlo antes de seguir.
- No modificar los subtítulos ni los guiones de los videos. Esa línea sigue en otra sesión, con una tarea horaria que reedita un tema por hora (temas 05–14). La salida queda en `C:\Users\ezead\Documents\Codex\2026-10-06\quiero-que-trabajes-directamente-sobre-mi\outputs\storyboard_assets\exports\` y el editor corre en `http://127.0.0.1:18763`.
