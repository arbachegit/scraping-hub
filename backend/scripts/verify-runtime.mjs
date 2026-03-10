import { readdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildHealthPayload, startServer } from "../src/index.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendDir = path.resolve(__dirname, "..");
const srcDir = path.join(backendDir, "src");
const verifyPorts = [3106, 3107, 3108, 3906];
async function listJsFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        return listJsFiles(fullPath);
      }
      return entry.name.endsWith(".js") ? [fullPath] : [];
    }),
  );
  return files.flat();
}

async function syntaxCheck() {
  const files = await listJsFiles(srcDir);
  for (const file of files) {
    execFileSync(process.execPath, ["--check", file], {
      cwd: backendDir,
      stdio: "pipe",
    });
  }
  console.log(`syntax-ok ${files.length} files`);
}

async function stopServer(server) {
  if (!server?.listening) return;
  await new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

async function verifyRuntime() {
  await syntaxCheck();
  process.env.BACKEND_ALLOW_NONSTANDARD_PORTS = "true";

  let server = null;
  let port = null;

  for (const candidatePort of verifyPorts) {
    try {
      server = await startServer({ port: candidatePort });
      port = candidatePort;
      break;
    } catch (error) {
      if (error?.code !== "EADDRINUSE") {
        throw error;
      }
    }
  }

  if (!server || port === null) {
    throw new Error(
      `Could not start backend on verify ports: ${verifyPorts.join(", ")}`,
    );
  }

  try {
    const health = buildHealthPayload();
    if (health?.status !== "healthy" || health?.service !== "iconsai-scraping-backend") {
      throw new Error(`Unexpected health payload: ${JSON.stringify(health)}`);
    }
    console.log(`health-ok port=${port} mode=direct-start`);
  } finally {
    await stopServer(server);
  }
}

verifyRuntime()
  .then(() => {
    process.exit(0);
  })
  .catch((error) => {
    console.error(`backend-verify-failed: ${error.message}`);
    process.exit(1);
  });
