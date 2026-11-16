# render-screens

Renders marketing PNGs from the public OrroFi prototype.

```bash
cd tools/render-screens
npm install
npx playwright install chromium
npm run render
```

Output: `../../assets/screens/*.png` and `index.md`.

Config: `frames.json` (screen ids, flags, output filenames).