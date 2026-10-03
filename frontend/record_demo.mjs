// Records the 3-minute demo flow (see docs/demo-script.md) as a fallback video and fails on any
// console error or failed API call.  Usage: node record_demo.mjs [uiUrl] [outDir]
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const ui = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "../results/demo_video";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 860 }, recordVideo: { dir: out, size: { width: 1440, height: 860 } } });
const page = await ctx.newPage();
const problems = [];
page.on("console", (m) => { if (m.type() === "error" && !/tile\.openstreetmap|ERR_INTERNET|Failed to load resource/.test(m.text())) problems.push(m.text()); });
page.on("pageerror", (e) => problems.push(String(e)));
page.on("response", (r) => { if (r.url().includes("/api/") && r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });

await page.goto(ui + "#app");
await page.getByRole("button", { name: "About" }).click();
await page.waitForTimeout(2500);
await page.getByRole("button", { name: "Plan" }).click();
const solve = page.getByRole("button", { name: "Solve", exact: true });
await solve.waitFor({ state: "visible", timeout: 60000 });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent === "Solve" && !b.disabled), null, { timeout: 60000 });
const live = page.getByLabel("Live traffic (TomTom)");
if (await live.count()) await live.check();
await solve.click();
await page.getByRole("status").filter({ hasText: "Done" }).waitFor({ timeout: 90000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${out}/../demo_plan.png` }); // Phase 0: routes in the Delhi zone
await page.getByLabel("Time of day").fill("600"); // 10:00
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "Incident" }).click();
await page.getByRole("button", { name: /Draw blockage/ }).click();
const map = page.locator(".leaflet-container");
const box = await map.boundingBox();
for (const [fx, fy] of [[0.40, 0.35], [0.60, 0.35], [0.60, 0.65], [0.40, 0.65]]) {
  await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  await page.waitForTimeout(250);
}
await page.keyboard.press("Enter");
await page.getByRole("button", { name: "Simulate incident" }).click();
await page.getByText(/Safe plan ready in/).waitFor({ timeout: 20000 });
await page.waitForTimeout(2500);
await page.getByRole("status").filter({ hasText: "Done" }).waitFor({ timeout: 60000 });
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "Benchmark" }).click();
await page.waitForTimeout(3000);
await page.getByRole("button", { name: "Path" }).click();
await page.waitForTimeout(2000);
await ctx.close();
await browser.close();
if (problems.length) { console.error("PROBLEMS:\n" + problems.join("\n")); process.exit(1); }
console.log("demo flow OK, video in", out);
