// Screenshots for the README, taken from the running app (Vite on :5173, API with the real model on :7860).
// node scripts/screenshots.js [out-dir]
const puppeteer = require(process.env.PUPPETEER_PATH ||
  "/Users/okba/Documents/portflio/job-search/outreach/node_modules/puppeteer-core");
const out = process.argv[2] || "docs/screenshots";
const url = process.env.APP_URL || "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: "new",
  });
  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => localStorage.setItem("invoicedesk.lang", "en"));
  await page.setViewport({ width: 1512, height: 982, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: "networkidle0" });
  await sleep(500);
  await page.screenshot({ path: `${out}/start.png` });

  await page.click('button[aria-label="Use sample 1"]');
  await page.waitForSelector('article[aria-label="Entry sheet"]', { timeout: 120000 });
  await sleep(1200); // the stamp animation
  await page.evaluate(() => document.querySelector("article").scrollIntoView({ block: "start" }));
  await sleep(400);
  await page.screenshot({ path: `${out}/entry-sheet.png` });

  const ask = async (q) => {
    await page.type("#question", q);
    await page.keyboard.press("Enter");
    await page.waitForFunction((n) => document.querySelectorAll("li .font-typed.text-2xl").length >= n, { timeout: 120000 },
      await page.evaluate(() => document.querySelectorAll("li .font-typed.text-2xl").length + 1));
  };
  await ask("What is the total amount to pay?");
  await ask("Combien de TVA ?");
  await sleep(800);
  await page.screenshot({ path: `${out}/questions.png` });

  await page.evaluate(() => [...document.querySelectorAll("aside button")].find((b) => b.textContent.includes("New chat")).click());
  await page.waitForSelector('button[aria-label="Use sample 3"]');
  await page.click('button[aria-label="Use sample 3"]');
  await page.waitForFunction(() => document.querySelectorAll('article[aria-label="Entry sheet"]').length >= 1 &&
    document.querySelectorAll("nav li").length >= 2, { timeout: 120000 });
  await sleep(1200);
  await page.screenshot({ path: `${out}/history.png` });

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 3 }); // isMobile would reload the page and clear the in-memory chats
  await sleep(600);
  await page.evaluate(() => document.querySelector("article").scrollIntoView({ block: "start" }));
  await sleep(400);
  await page.screenshot({ path: `${out}/mobile.png` });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
