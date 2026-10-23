# Ader Oficina — respaldo en GitHub

Respaldo privado del código de la oficina virtual (`work\office`), hecho el 23/10/2026.
Base: `main` en el commit `c74e5d4654327325882e3e6a1ebeb585c84ee1fb` del repositorio local, más este archivo.
Si había cambios sin commit al momento del respaldo, están en la rama `respaldo/cambios-sin-commit-2026-10-23`.

Este repositorio es solo un respaldo. No está conectado a la publicación: hacer push aquí **no** despliega nada ni cambia el sitio publicado.

## Cómo ejecutarlo en local

Requisitos: Node.js 22.13 o superior, pnpm 11 (`corepack enable`) y Git.

```powershell
git clone https://github.com/ezeader/OFICINA_VIRTUAL.git ader-oficina
cd ader-oficina
corepack enable
pnpm install
pnpm run dev            # http://127.0.0.1:5173 (otro puerto: pnpm run dev -- --port 5180)
```

- En local, el inicio de sesión se simula: abrí `/signin-with-chatgpt?return_to=/` (usuario de prueba `local_seedy`).
- D1 y R2 se simulan en local en `.wrangler/state`. Arranca **vacío**: no contiene los datos de la oficina publicada.
- Vista previa del build: `pnpm run build` y después `pnpm start`. Ninguno de los dos publica nada.
- Las migraciones locales de D1 se explican en el `README.md` (sección *Local D1 migrations*).
- La publicación la maneja la plataforma Sites, con `.openai/hosting.json`. Ese archivo solo tiene identificadores del proyecto, no claves. No lo cambies si no querés tocar producción.

## Qué NO está en este repositorio

| Fuera del respaldo | Dónde vive | Cómo respaldarlo |
|---|---|---|
| Datos reales de la oficina (workspace: tareas, proveedores, precios, lecturas guardadas) | Base D1 publicada (`DB`) | Descargar `GET /api/workspace` estando autenticado en el sitio |
| Archivos subidos o almacenados en la nube | Bucket R2 publicado (`BUCKET`) | Desde la plataforma de hosting |
| Base local de pruebas | `office\.wrangler\` (ignorada) | Desechable |
| Dependencias y builds | `node_modules`, `.next`, `.vinext`, `dist`, `.sites-runtime` (ignorados) | Se regeneran con `pnpm install` y `pnpm run build` |
| Variables de entorno y claves | `.env*`, `*.pem` (ignorados; no había ninguno versionado) | Nunca subirlos |
| Modelo Revit de Casa Ángel | `outputs\casa-angel\Casa-Angel-piloto-documentacion.rvt` | Copia manual u OneDrive |
| Puente local Revit (lectura de schedules y `Abrir en Revit`, puerto 18764) | `work\revit-quantities-bridge\` e `Iniciar-consulta-Revit.ps1` | Está fuera del repo |
| Datos de dimensionado y aberturas que usa el puente | `work\casa-angel-dimensioning\` (openings-r1/r2/r3) | Está fuera del repo |
| Piloto Baton y su referencia | `work\baton-casa-angel\`, `work\baton-reference\` | Está fuera del repo |
| Worktree de Codex | `work\office-openings-r4-ui\` (rama `baton/openings-r4-ui`, igual a `main` al respaldar) | No se tocó |
| Paquetes, scripts sueltos y análisis | `work\*.tar.gz`, `work\*.py`, `casa-angel-audit`, `compulsa-analysis`, `skills`, etc. | Está fuera del repo |
| Sistema audiovisual Urbetrack (`proyecto_actual.json`, MP4, editor en 18763) | `OneDrive\Documentos\URBE MARKETING\...` | OneDrive |

## Desarrollo posterior

No trabajar sobre `main` de este respaldo ni sobre la carpeta de Codex. Para desarrollar, usar una rama propia (por ejemplo `claude/office-efficiency`) en una carpeta de trabajo separada.
