// Vite: importar un archivo con ?url devuelve la dirección con la que se sirve (dev y build).
declare module '*?url' {
 const src: string;
 export default src;
}
