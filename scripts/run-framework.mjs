import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { readExecutionProfile } from "./execution-profile.mjs";

const [command, ...args] = process.argv.slice(2);
if (!["dev", "build"].includes(command)) throw new Error("Expected dev or build.");
const managedLinux = readExecutionProfile() === "managed-linux";
if(command==='build'){
 const check=spawnSync(process.execPath,[fileURLToPath(new URL('./document-assets.mjs',import.meta.url)),'--check'],{stdio:'inherit'});
 if(check.status!==0)process.exit(check.status??1);
}

if (managedLinux && command === "build") {
  const result = spawnSync("bash", [
    fileURLToPath(new URL("./build-verified.sh", import.meta.url)), ...args,
  ], { stdio: "inherit" });
  if (result.error) throw result.error;
  if(result.status===0){
    const compact=spawnSync(process.execPath,[fileURLToPath(new URL('./document-assets.mjs',import.meta.url)),'--check','--exclude-built-copies'],{stdio:'inherit'});
    process.exit(compact.status??1);
  }
  process.exit(result.status ?? 1);
}

// Import in this process so the preview owner retains its PID and signals.
const cli = new URL(managedLinux
  ? "../node_modules/vite/bin/vite.js"
  : "../node_modules/vinext/dist/cli.js", import.meta.url);
if(command==='build'){
 const result=spawnSync(process.execPath,[fileURLToPath(cli),'build',...args],{stdio:'inherit'});
 if(result.status!==0)process.exit(result.status??1);
 const compact=spawnSync(process.execPath,[fileURLToPath(new URL('./document-assets.mjs',import.meta.url)),'--check','--exclude-built-copies'],{stdio:'inherit'});
 process.exit(compact.status??1);
}
process.argv = [process.execPath, fileURLToPath(cli), command,
  ...(!managedLinux && command === "dev" ? ["--port", "5173"] : []), ...args];
await import(cli.href);
