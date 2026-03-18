#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_REQUIRED_MODULES = ["akshare", "pandas", "requests", "baostock", "certifi"];

function getProjectVenvPython(root) {
  return path.join(root, ".venv", os.platform() === "win32" ? "Scripts/python.exe" : "bin/python");
}

function spawnCapture(command, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
    });

    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (error) => resolve({ ok: false, code: null, stdout, stderr, error }));
    child.on("close", (code) => resolve({ ok: code === 0, code, stdout, stderr }));
  });
}

async function checkModules(pythonBin, modules, root) {
  const code = [
    "import importlib.util, json",
    `mods = ${JSON.stringify(modules)}`,
    "print(json.dumps({m: bool(importlib.util.find_spec(m)) for m in mods}))",
  ].join("; ");
  const result = await spawnCapture(pythonBin, ["-c", code], { cwd: root, env: process.env });
  if (!result.ok) {
    return null;
  }
  try {
    return JSON.parse(result.stdout.trim() || "{}");
  } catch {
    return null;
  }
}

function hasAllModules(state, modules) {
  return Boolean(state) && modules.every((name) => state[name]);
}

async function installRequirements(pythonBin, root) {
  const requirements = path.join(root, "requirements.txt");
  if (!fs.existsSync(requirements)) {
    return false;
  }
  const upgrade = await spawnCapture(pythonBin, ["-m", "pip", "install", "--upgrade", "pip"], {
    cwd: root,
    env: process.env,
  });
  if (!upgrade.ok) {
    return false;
  }
  const install = await spawnCapture(pythonBin, ["-m", "pip", "install", "-r", requirements], {
    cwd: root,
    env: process.env,
  });
  return install.ok;
}

export async function resolvePythonRuntime(options = {}) {
  const root = options.root || process.cwd();
  const requiredModules = options.requiredModules || DEFAULT_REQUIRED_MODULES;
  const projectVenvPython = getProjectVenvPython(root);
  const preferredEnvPython = process.env.AKSHARE_NODE_PYTHON_BIN?.trim();
  const candidates = [
    preferredEnvPython,
    fs.existsSync(projectVenvPython) ? projectVenvPython : null,
    os.platform() === "win32" ? "py" : "python3",
    "python",
  ].filter(Boolean);

  let bestCandidate = null;
  let bestScore = -1;

  for (const candidate of candidates) {
    const moduleState = await checkModules(candidate, requiredModules, root);
    if (moduleState === null) {
      continue;
    }
    const score = requiredModules.filter((name) => moduleState[name]).length;
    if (score > bestScore) {
      bestScore = score;
      bestCandidate = { pythonBin: candidate, moduleState };
    }
    if (hasAllModules(moduleState, requiredModules)) {
      return { pythonBin: candidate, moduleState, installed: false };
    }
  }

  if (fs.existsSync(projectVenvPython)) {
    const installed = await installRequirements(projectVenvPython, root);
    if (installed) {
      const moduleState = await checkModules(projectVenvPython, requiredModules, root);
      if (hasAllModules(moduleState, requiredModules)) {
        return { pythonBin: projectVenvPython, moduleState, installed: true };
      }
    }
  }

  if (bestCandidate) {
    return { pythonBin: bestCandidate.pythonBin, moduleState: bestCandidate.moduleState, installed: false };
  }

  throw new Error("No usable Python runtime found. Set AKSHARE_NODE_PYTHON_BIN or create akshareServer/.venv.");
}

export { DEFAULT_REQUIRED_MODULES, getProjectVenvPython };