# Document publication

Casa Ángel originals stay in `public/casa-angel`, tracked in Git. The deployment
archive omits only their generated copies in `dist/client/casa-angel`. All 301
original files, including historical PDFs and compressed vector drawings, are
preserved without recompression, resampling, editing or conversion.

`node scripts/document-assets.mjs` creates the version-pinned SHA-256 inventory.
Builds check it before packaging. If a document changes, regenerate the inventory.
R2 objects are immutable and addressed by SHA-256. The upload endpoint accepts
only the exact paths, lengths and hashes listed in the current source inventory,
requires the private Sites access boundary and same-origin requests, and does not allow
arbitrary new files. Site access remains owner-private.

Publish the compact archive with the native Sites workflow, then run
`node scripts/upload-document-assets.mjs`. Supply `{origin,bearer,reportPath}` via
hidden stdin only, using the short-lived authorization returned by `get_site`.
Never put the bearer in arguments, files, logs or committed source. The fixed
destination is the existing Ader office. Uploads can resume: already verified
objects are skipped. Every document is downloaded again and SHA-256 checked.
The service bearer is sent with the `Bearer ` prefix. Sites consumes it and
does not inject visitor identity for this access. Shared document routes rely on
the private Sites boundary; user-owned workspace records retain their separate
visitor-identity requirements.

Publication is not complete until the transfer report verifies every inventory
entry. During first migration only, an untransferred document returns HTTP 503
with a synchronization message. Do not describe this intermediate state as a
complete publication. The previous saved Site version remains available for
rollback if transfer cannot complete. R2 does not change on rollback.

The original URLs are retained. PDF GET/HEAD, byte ranges, conditional requests,
MIME types, and gzip-file payloads are preserved. Future interface-only updates
reuse the R2 objects without transferring the documents again. An amended
document gets a new hash; old objects are retained for saved-version rollback.

Validation: `node --test scripts/document-storage.test.mjs`, TypeScript, build,
local built-Worker PUT/GET/range checks, then production readback of all files.
