/* Hero scene: a living Earth in deep space, lit from the side, city lights on the night side,
   drifting clouds, and radar pings on the three Bahria campus cities. It sinks and swings as
   the page scrolls (GSAP ScrollTrigger), and idles gently when it is in view. */
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
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 0.15, 6.4);

/* ---------- stars */
{
  const count = 2200, pos = new Float32Array(count * 3), col = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = 40 + Math.random() * 40, t = Math.random() * Math.PI * 2, p = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(p) * Math.cos(t); pos[i * 3 + 1] = r * Math.sin(p) * Math.sin(t); pos[i * 3 + 2] = r * Math.cos(p);
    const w = 0.6 + Math.random() * 0.4, b = Math.random() < 0.15 ? 1.15 : 1;
    col[i * 3] = w; col[i * 3 + 1] = w * 0.98; col[i * 3 + 2] = w * b;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const m = new THREE.PointsMaterial({ size: 0.11, vertexColors: true, transparent: true, opacity: 0.85, sizeAttenuation: true, depthWrite: false });
  scene.add(new THREE.Points(g, m));
}

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
  uniforms: { c1: { value: new THREE.Color("#4f7cff") }, c2: { value: ACCENT }, sunDir: { value: SUN } },
  vertexShader: `varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position,1.0); vP = mv.xyz; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `uniform vec3 c1, c2, sunDir; varying vec3 vN; varying vec3 vP;
    void main(){ float i = pow(0.66 - dot(vN, normalize(-vP)), 3.0); vec3 n = normalize(vN);
      float side = smoothstep(-0.6, 0.6, dot(n, sunDir)); vec3 col = mix(c2, c1, side) * i * 1.4; gl_FragColor = vec4(col, i); }`,
}));
earth.add(atmo);

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
// face Pakistan toward the camera: longitude 70E to the front (+z)
globe.rotation.y = -((70 + 180) * Math.PI / 180) + Math.PI / 2;
clouds.rotation.y = globe.rotation.y + 0.4;
earth.rotation.z = 0.2;
earth.position.set(0, -3.65, 0);

/* ---------- scroll + pointer */
const state = { sink: 0, mx: 0, my: 0 };
if (window.gsap && window.ScrollTrigger && !reduce) {
  gsap.registerPlugin(ScrollTrigger);
  gsap.to(state, { sink: 1, ease: "none", scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: 0.8 } });
}
if (!coarse) window.addEventListener("pointermove", (e) => { state.mx = e.clientX / innerWidth - 0.5; state.my = e.clientY / innerHeight - 0.5; }, { passive: true });

let visible = true;
new IntersectionObserver(([e]) => (visible = e.isIntersecting), { threshold: 0 }).observe(document.querySelector(".hero"));
function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
  const narrow = window.innerWidth < 760;
  earth.position.y = narrow ? -4.9 : -3.65; camera.position.z = narrow ? 7.4 : 6.4;
}
window.addEventListener("resize", resize); resize();

const clock = new THREE.Clock();
let base = earth.position.y;
const stars = scene.children.find((o) => o.isPoints);
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  if (visible && !document.hidden) {
    if (!reduce) {
      globe.rotation.y += dt * 0.11;            // one turn in about a minute: clearly alive, never distracting
      clouds.rotation.y += dt * 0.145;
      if (stars) stars.rotation.y += dt * 0.004;
      earth.rotation.z = 0.2 + state.sink * 0.55 + Math.sin(t * 0.25) * 0.012;
    }
    const s = state.sink;
    const narrow = window.innerWidth < 760;
    base = narrow ? -4.9 : -3.65;
    earth.position.y = base - s * 0.9;
    earth.position.x = s * 0.9;
    earth.rotation.x = s * 0.35;
    const driftX = Math.sin(t * 0.18) * 0.06, driftY = Math.cos(t * 0.14) * 0.04;
    camera.position.x += ((state.mx * 0.35 + driftX) - camera.position.x) * 0.04;
    camera.position.y += ((0.15 - state.my * 0.2 + driftY) - camera.position.y) * 0.04;
    camera.lookAt(0, -0.25, 0);
    pings.forEach(({ ring, phase }) => {
      const k = ((t * 0.55 + phase) % 1.6) / 1.6;
      ring.scale.setScalar(1 + k * 2.8); ring.material.opacity = (1 - k) * 0.85;
    });
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
