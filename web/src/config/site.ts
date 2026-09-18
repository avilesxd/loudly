import fs from "node:fs";
import path from "node:path";

const versionPy = fs.readFileSync(
  path.join(process.cwd(), "..", "src", "version.py"),
  "utf-8",
);

export const VERSION =
  versionPy.match(/APP_VERSION\s*=\s*"([^"]+)"/)?.[1] ?? "0.0.0";

export const REPO = "https://github.com/avilesxd/loudly";
export const RELEASE = `${REPO}/releases/latest`;
export const LINKEDIN = "https://www.linkedin.com/in/ignacioavilescardenasso/";
export const YEAR = new Date().getFullYear();
