/* SPDX-License-Identifier: Apache-2.0 */
/**
 * Stagehand <-> revar bridge.
 *
 * Reads a single JSON request from stdin:
 *   {
 *     goal: string,
 *     base_url: string,
 *     model: string,
 *     max_steps: number,
 *     viewport: "desktop" | "mobile_iphone15" | "mobile_pixel7",
 *     credentials?: { email, password }
 *   }
 *
 * Writes a single-line JSON response on stdout:
 *   { steps: [...], tokens_in, tokens_out, error?: string }
 *
 * Run:  node bridge.mjs
 */

import readline from "node:readline";

async function readJson() {
  const rl = readline.createInterface({ input: process.stdin });
  let buf = "";
  for await (const line of rl) {
    buf += line + "\n";
  }
  return JSON.parse(buf);
}

async function main() {
  const req = await readJson();

  let Stagehand;
  try {
    ({ Stagehand } = await import("@browserbasehq/stagehand"));
  } catch (err) {
    process.stdout.write(
      JSON.stringify({
        steps: [],
        tokens_in: 0,
        tokens_out: 0,
        error:
          "Stagehand is not installed. Run `npm install @browserbasehq/stagehand` " +
          "or use a different adapter.",
      }) + "\n",
    );
    process.exit(2);
  }

  const stagehand = new Stagehand({
    env: "LOCAL",
    modelName: req.model || "gpt-4o",
    headless: req.headless !== false,
    enableCaching: false,
  });

  await stagehand.init();
  const page = stagehand.page;

  // Pre-auth via API (so the agent doesn't have to sign in)
  if (req.credentials) {
    try {
      const meRes = await page.request.get(`${req.base_url}/api/auth/me`);
      const me = await meRes.json();
      const csrf = me.csrf_token;
      await page.request.post(`${req.base_url}/api/auth/login`, {
        data: req.credentials,
        headers: { "X-CSRF-Token": csrf || "_dummy_" },
      });
    } catch (err) {
      // best-effort; surface but don't abort
      console.error("pre-auth failed:", err.message);
    }
  }

  await page.goto(req.base_url + "/");

  const steps = [];
  let tokens_in = 0;
  let tokens_out = 0;

  try {
    const result = await stagehand.act({ action: req.goal });
    steps.push({
      type: "stagehand_act",
      action: { goal: req.goal, result: String(result).slice(0, 500) },
      url: page.url(),
      tokens_in: 0,
      tokens_out: 0,
    });
  } catch (err) {
    steps.push({
      type: "error",
      action: { error: err.message },
      url: page.url(),
    });
  }

  try {
    await stagehand.close();
  } catch {}

  process.stdout.write(
    JSON.stringify({ steps, tokens_in, tokens_out }) + "\n",
  );
}

main().catch((err) => {
  process.stderr.write("bridge fatal: " + (err?.stack || err) + "\n");
  process.exit(1);
});
