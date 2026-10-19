/* Hero scene: a living Earth in deep space. Day/night textures, city lights, drifting clouds, an
   atmosphere, radar pings on the three Bahria campus cities, an orbiting "monitor" satellite, and a
   keyframed journey across the opening sections (GSAP ScrollTrigger). It never stops turning. */
import * as THREE from "./vendor/three.module.min.js";

const canvas = document.getElementById("space");
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const coarse = window.matchMedia("(hover: none), (pointer: coarse)").matches;
if (!canvas) throw new Error("no canvas");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
renderer.setSize(window.innerWidth, window.innerHeight, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 0.15, 6.4);

/* ---------- stars (two layers for parallax) */
function makeStars(count, rMin, rMax, size, opacity) {
  const pos = new Float32Array(count * 3), col = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = rMin + Math.random() * (rMax - rMin), t = Math.random() * Math.PI * 2, p = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(p) * Math.cos(t); pos[i * 3 + 1] = r * Math.sin(p) * Math.sin(t); pos[i * 3 + 2] = r * Math.cos(p);
    const w = 0.55 + Math.random() * 0.45, warm = Math.random() < 0.12;
    col[i * 3] = w * (warm ? 1.15 : 1); col[i * 3 + 1] = w * 0.97; col[i * 3 + 2] = w * (warm ? 0.8 : 1.12);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ size, vertexColors: true, transparent: true, opacity, sizeAttenuation: true, depthWrite: false }));
}
const starsFar = makeStars(2400, 60, 90, 0.14, 0.75), starsNear = makeStars(600, 28, 45, 0.11, 0.95);
scene.add(starsFar, starsNear);

/* ---------- earth */
const SUN = new THREE.Vector3(-1.6, 0.55, 0.9).normalize();
const ACCENT = new THREE.Color("#ff6a3d");
const earth = new THREE.Group();
scene.add(earth);
const loader = new THREE.TextureLoader();
const tex = (p, srgb = true) => { const t = loader.load(p); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
const dayMap = tex("assets/earth/day.jpg"), nightMap = tex("assets/earth/night.jpg"), specMap = tex("assets/earth/specular.jpg", false);
const cloudMap = tex("assets/earth/clouds.jpg", false);

const globeMat = new THREE.ShaderMaterial({
  uniforms: { dayMap: { value: dayMap }, nightMap: { value: nightMap }, specMap: { value: specMap }, sunDir: { value: SUN }, rim: { value: ACCENT } },
  vertexShader: `
    varying vec2 vUv; varying vec3 vN; varying vec3 vV;
    void main(){ vUv = uv; vec4 wp = modelMatrix * vec4(position,1.0); vN = normalize(mat3(modelMatrix) * normal);
      vV = normalize(cameraPosition - wp.xyz); gl_Position = projectionMatrix * viewMatrix * wp; }`,
  fragmentShader: `
    uniform sampler2D dayMap, nightMap, specMap; uniform vec3 sunDir, rim;
    varying vec2 vUv; varying vec3 vN; varying vec3 vV;
    void main(){
      vec3 n = normalize(vN); float ndl = dot(n, sunDir);
      vec3 day = texture2D(dayMap, vUv).rgb; vec3 night = texture2D(nightMap, vUv).rgb; float ocean = texture2D(specMap, vUv).r;
      float lit = smoothstep(-0.12, 0.28, ndl);
      vec3 dayCol = day * (0.22 + 0.95 * max(ndl, 0.0));
      vec3 h = normalize(sunDir + vV); float spec = pow(max(dot(n, h), 0.0), 48.0) * ocean * 0.55 * max(ndl, 0.0);
      dayCol += vec3(1.0, 0.9, 0.75) * spec;
      vec3 nightCol = night * vec3(1.25, 1.05, 0.8) * 1.5 + day * 0.03;
      vec3 col = mix(nightCol, dayCol, lit);
      float fres = pow(1.0 - max(dot(n, vV), 0.0), 3.2);
      col += rim * fres * (0.35 + 0.55 * (1.0 - lit));
      col += vec3(0.45, 0.62, 1.0) * pow(fres, 1.6) * 0.18 * lit;
      gl_FragColor = vec4(col, 1.0);
    }`,
});
const globe = new THREE.Mesh(new THREE.SphereGeometry(2, 128, 128), globeMat);
earth.add(globe);
const clouds = new THREE.Mesh(new THREE.SphereGeometry(2.022, 96, 96),
  new THREE.MeshLambertMaterial({ color: 0xffffff, alphaMap: cloudMap, transparent: true, opacity: 0.55, depthWrite: false }));
earth.add(clouds);
scene.add(new THREE.AmbientLight(0x26304a, 0.9));
const sun = new THREE.DirectionalLight(0xfff2e0, 2.4); sun.position.copy(SUN).multiplyScalar(10); scene.add(sun);

const atmo = new THREE.Mesh(new THREE.SphereGeometry(2.2, 96, 96), new THREE.ShaderMaterial({
  side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
  uniforms: { c1: { value: new THREE.Color("#4f7cff") }, c2: { value: ACCENT }, sunDir: { value: SUN }, pulse: { value: 1 } },
  vertexShader: `varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position,1.0); vP = mv.xyz; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `uniform vec3 c1, c2, sunDir; uniform float pulse; varying vec3 vN; varying vec3 vP;
    void main(){ float i = pow(0.66 - dot(vN, normalize(-vP)), 3.0) * pulse; vec3 n = normalize(vN);
      float side = smoothstep(-0.6, 0.6, dot(n, sunDir)); vec3 col = mix(c2, c1, side) * i * 1.4; gl_FragColor = vec4(col, i); }`,
}));
earth.add(atmo);

/* ---------- orbit ring + the "monitor" satellite */
const orbit = new THREE.Group();
orbit.rotation.set(0.55, 0, -0.35);
earth.add(orbit);
orbit.add(new THREE.Mesh(new THREE.TorusGeometry(2.85, 0.004, 8, 240),
  new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.16, depthWrite: false })));
const sat = new THREE.Group();
sat.add(new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 16), new THREE.MeshBasicMaterial({ color: 0xffffff })));
const glowTex = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 64; const g = c.getContext("2d");
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(0.3, "rgba(255,160,120,0.6)"); grd.addColorStop(1, "rgba(255,106,61,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c);
})();
const satGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: ACCENT, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
satGlow.scale.setScalar(0.5); sat.add(satGlow);
orbit.add(sat);

/* ---------- campus pings (Bahria University campuses) */
const latLon = (lat, lon, r) => {
  const phi = (90 - lat) * Math.PI / 180, theta = (lon + 180) * Math.PI / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
};
const pings = [];
[[33.69, 73.04], [24.86, 67.0], [31.55, 74.35]].forEach(([lat, lon], i) => {
  const p = latLon(lat, lon, 2.01);
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 12, 12), new THREE.MeshBasicMaterial({ color: ACCENT }));
  dot.position.copy(p); globe.add(dot);
  for (let k = 0; k < 2; k++) {
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.026, 0.031, 48),
      new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }));
    ring.position.copy(p); ring.lookAt(p.clone().multiplyScalar(2)); globe.add(ring);
    pings.push({ ring, phase: i * 0.9 + k * 1.6 });
  }
});
globe.rotation.y = -((70 + 180) * Math.PI / 180) + Math.PI / 2;   // Pakistan toward the camera
clouds.rotation.y = globe.rotation.y + 0.4;

/* ---------- journey keyframes: p = 0 at the top of the page, 1 at the end of the tour */
const KEYS = [
  { p: 0.00, x: 0.0, y: 0.00, z: 0.0, rz: 0.20, rx: 0.00, s: 1.10, o: 1.00 },   // hero: big, below the copy
  { p: 0.22, x: 1.35, y: 0.60, z: -0.3, rz: 0.60, rx: 0.25, s: 1.10, o: 1.00 }, // rises into view, swings right
  { p: 0.55, x: 0.55, y: -0.75, z: -1.4, rz: 0.95, rx: 0.45, s: 0.95, o: 0.85 }, // sinks back, smaller, below the tour heading
  { p: 0.85, x: 0.20, y: -1.30, z: -2.0, rz: 1.15, rx: 0.55, s: 0.85, o: 0.55 }, // low behind the tour
  { p: 1.00, x: 0.20, y: -2.20, z: -2.4, rz: 1.25, rx: 0.60, s: 0.80, o: 0.00 }, // gone before the feature grid
];
const smooth = (t) => t * t * (3 - 2 * t);
function sample(p) {
  let a = KEYS[0], b = KEYS[KEYS.length - 1];
  for (let i = 0; i < KEYS.length - 1; i++) if (p >= KEYS[i].p && p <= KEYS[i + 1].p) { a = KEYS[i]; b = KEYS[i + 1]; break; }
  const t = smooth(Math.min(1, Math.max(0, (p - a.p) / Math.max(1e-6, b.p - a.p))));
  const out = {}; for (const k of ["x", "y", "z", "rz", "rx", "s", "o"]) out[k] = a[k] + (b[k] - a[k]) * t; return out;
}

const state = { p: 0, target: 0, mx: 0, my: 0, vel: 0, lastY: 0, intro: reduce ? 1 : 0 };
window.__sceneState = state;
// Journey progress is measured from the live layout every frame (pin spacers included), so it
// cannot drift out of sync with the pinned tour: 0 at the top, 1 when the tour's end reaches the bottom.
const journeyEnd = document.querySelector("#story") || document.querySelector(".hero");
function measureProgress() {
  if (reduce) return 0;
  const end = journeyEnd.getBoundingClientRect().bottom + window.scrollY - window.innerHeight;
  return Math.min(1, Math.max(0, window.scrollY / Math.max(1, end)));
}
if (window.gsap && !reduce) gsap.to(state, { intro: 1, duration: 1.9, ease: "power3.out", delay: 0.15 });
if (!coarse) window.addEventListener("pointermove", (e) => { state.mx = e.clientX / innerWidth - 0.5; state.my = e.clientY / innerHeight - 0.5; }, { passive: true });

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize); resize();

const clock = new THREE.Clock();
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  if (!document.hidden) {
    const narrow = window.innerWidth < 760;
    const base = narrow ? -4.3 : -3.65;
    state.target = measureProgress();
    state.p += (state.target - state.p) * Math.min(1, dt * 7);          // scrubbed, slightly lagging
    const v = (window.scrollY - state.lastY) / Math.max(dt, 1e-3) / 1000; state.lastY = window.scrollY;
    state.vel = state.vel * 0.9 + v * 0.1;
    const k = sample(state.p);
    const intro = smooth(state.intro);
    if (!reduce) {
      globe.rotation.y += dt * (0.11 + Math.min(Math.abs(state.vel), 6) * 0.08);
      clouds.rotation.y += dt * 0.145;
      starsFar.rotation.y += dt * 0.004; starsNear.rotation.y -= dt * 0.006;
      sat.position.set(Math.cos(t * 0.42) * 2.85, 0, Math.sin(t * 0.42) * 2.85);
      atmo.material.uniforms.pulse.value = 1 + Math.sin(t * 0.9) * 0.08;
    }
    earth.position.set(k.x, base + k.y - (1 - intro) * 1.4, k.z + (narrow ? 1.0 : 0));
    earth.rotation.set(k.rx, 0, k.rz + Math.sin(t * 0.25) * 0.012);
    earth.scale.setScalar(k.s * (0.92 + 0.08 * intro));
    canvas.style.opacity = (k.o * intro).toFixed(3);
    const driftX = Math.sin(t * 0.18) * 0.06, driftY = Math.cos(t * 0.14) * 0.04;
    camera.position.x += ((state.mx * 0.4 + driftX) - camera.position.x) * 0.04;
    camera.position.y += ((0.15 - state.my * 0.25 + driftY) - camera.position.y) * 0.04;
    starsNear.rotation.x += ((-state.my * 0.05) - starsNear.rotation.x) * 0.03;
    camera.lookAt(0, -0.25, 0);
    pings.forEach(({ ring, phase }) => {
      const q = ((t * 0.55 + phase) % 1.6) / 1.6;
      ring.scale.setScalar(1 + q * 2.8); ring.material.opacity = (1 - q) * 0.85;
    });
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
