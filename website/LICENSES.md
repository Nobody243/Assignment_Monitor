# Website: third-party code and assets

The site is a React + Vite app. Libraries are installed from npm with pinned versions (see `package.json`):

| Package | License |
| --- | --- |
| react, react-dom, react-router-dom | MIT |
| framer-motion | MIT |
| gsap (incl. ScrollTrigger) | GSAP Standard License (free for all uses, including commercial) |
| lenis | MIT |
| three (r143) and its example modules; DRACO decoders in `public/draco` | MIT (DRACO decoders: Apache 2.0) |

Assets:

| File | Source | License |
| --- | --- | --- |
| `public/assets/ascend/planet.glb`, `planet-lights.glb`, `planet-clouds.png` | Earth model and textures distributed with the free "Ascend" template by [getlayers.ai](https://www.getlayers.ai/layer/ascend), used as that template's instructions direct. Textures were re-encoded to power-of-two sizes and unused maps removed. | getlayers.ai free template assets |
| `public/assets/logo*.{svg,png}`, `og.png`, `favicon.ico`, screenshots | This project | MIT |
