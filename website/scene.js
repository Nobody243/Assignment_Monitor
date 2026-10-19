/* Ascend-style planet scene (ported from the template spec): a GLTF Earth with a custom
   day/night · city-lights · ocean-glint · rim shader, an additive atmosphere halo, three drifting
   cloud shells, ambient motes, a twinkling starfield and radar-ping land markers, composited through
   bloom and a corner-flame final pass. Scroll drives a keyframed zoom-out and side-to-side swing
   across the WHOLE page; the globe is always on screen and always turning. */
import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { GammaCorrectionShader } from "three/examples/jsm/shaders/GammaCorrectionShader.js";
import { CopyShader } from "three/examples/jsm/shaders/CopyShader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const canvas = document.getElementById("space");
if (!canvas) throw new Error("no canvas");
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const ASSETS = "assets/ascend";
const PLANET_GLB = `${ASSETS}/planet.glb`, LIGHTS_GLB = `${ASSETS}/planet-lights.glb`, CLOUDS_PNG = `${ASSETS}/planet-clouds.png`;

const CONFIG = {
  rimColor: "#c1faff", rimPower: 2.4, nightLights: 10, terrainDepth: 0.33, terrainShade: 1.3,
  oceanGlint: 0.45, oceanDeep: 0.12, oceanFlow: 3, oceanFlowSpeed: 0.8, oceanFlowScale: 2.1,
  glowColor: "#3a6cff", glowIntensity: 1.3, planetRadius: 1.95, spin: 0.03, initRotation: 2.07,
  tilt: 0.37, autoRotate: 0,
  cloud1Height: 1.004, cloud1Opacity: 0.6, cloud1Spin: 0.06,
  cloud2Height: 1.014, cloud2Opacity: 0.5, cloud2Spin: 0.14,
  cloud3Height: 1.028, cloud3Opacity: 0.5, cloud3Spin: 0.1,
  bgColor: "#07080d",
  atmoColor: "#9fc4ff", atmoCount: 320, atmoSize: 22, atmoSpeed: 0.8,
  starColor: "#cfe0ff", starCount: 1400, starSize: 1.6, starFlicker: 1,
  markerColor: "#ffb48a", markerCount: 60, markerSize: 16, markerSpeed: 0.5,
};
const LAYERS = { NONE: 0, TORUS_SCENE: 1, BLOOM_SCENE: 2, ENTIRE_SCENE: 3 };
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const hexToVec3 = (hex) => { const c = new THREE.Color(hex); return new THREE.Vector3(c.r, c.g, c.b); };
const smoothstep = (t) => t * t * (3 - 2 * t);
function sample(stops, p) {
  if (p <= stops[0].p) return stops[0].v;
  for (let i = 0; i < stops.length - 1; i++) {
    const a = stops[i], b = stops[i + 1];
    if (p <= b.p) return a.v + (b.v - a.v) * smoothstep((p - a.p) / Math.max(1e-6, b.p - a.p));
  }
  return stops[stops.length - 1].v;
}

const SNOISE = `
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
float snoise(vec3 v){
  const vec2 C = vec2(1.0/6.0, 1.0/3.0); const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy)); vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz); vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy); vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + 1.0 * C.xxx; vec3 x2 = x0 - i2 + 2.0 * C.xxx; vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0);
  vec4 p = permute(permute(permute(i.z + vec4(0.0, i1.z, i2.z, 1.0)) + i.y + vec4(0.0, i1.y, i2.y, 1.0)) + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 1.0/7.0; vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
  vec4 x_ = floor(j * ns.z); vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ *ns.x + ns.yyyy; vec4 y = y_ *ns.x + ns.yyyy; vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy); vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0)*2.0 + 1.0; vec4 s1 = floor(b1)*2.0 + 1.0; vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy; vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
  vec3 p0 = vec3(a0.xy,h.x); vec3 p1 = vec3(a0.zw,h.y); vec3 p2 = vec3(a1.xy,h.z); vec3 p3 = vec3(a1.zw,h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.5 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0); m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}`;

/* ---------- renderer / scene / camera */
const renderer = new THREE.WebGL1Renderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
renderer.setSize(window.innerWidth, window.innerHeight, false);
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.VSMShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 0, 8);
camera.layers.enable(LAYERS.TORUS_SCENE); camera.layers.enable(LAYERS.BLOOM_SCENE); camera.layers.enable(LAYERS.ENTIRE_SCENE);
scene.add(camera);
const amb = new THREE.AmbientLight(0xffffff, 1.8); amb.layers.set(LAYERS.ENTIRE_SCENE); scene.add(amb);
const dir = new THREE.DirectionalLight(0xffffff, 0.8); dir.position.set(0, 10, 2); dir.layers.set(LAYERS.ENTIRE_SCENE); scene.add(dir);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.06; controls.enablePan = false; controls.enabled = false;
controls.autoRotate = true; controls.autoRotateSpeed = CONFIG.autoRotate; controls.minDistance = 3.5; controls.maxDistance = 16; controls.target.set(0, 0, 0);

/* ---------- composers */
const size = new THREE.Vector2(window.innerWidth, window.innerHeight);
const torusComposer = new EffectComposer(renderer); torusComposer.renderToScreen = false;
torusComposer.addPass(new RenderPass(scene, camera));
torusComposer.addPass(new ShaderPass(GammaCorrectionShader));
torusComposer.addPass(new UnrealBloomPass(size.clone(), 0.22, 0.2, 0));
torusComposer.addPass(new ShaderPass(CopyShader));
const bloomComposer = new EffectComposer(renderer); bloomComposer.renderToScreen = false;
bloomComposer.addPass(new RenderPass(scene, camera));
bloomComposer.addPass(new UnrealBloomPass(size.clone(), 0.3, 0.45, 0));
bloomComposer.addPass(new ShaderPass(GammaCorrectionShader));

const blackTex = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1); blackTex.needsUpdate = true;
const FinalPass = {
  uniforms: {
    iTime: { value: 0 }, tDiffuse: { value: null }, torusTexture: { value: null }, bloomTexture: { value: null }, haloTexture: { value: blackTex },
    uBg: { value: hexToVec3(CONFIG.bgColor) }, uBgLow: { value: hexToVec3("#0b1230") },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position, 1.0); }`,
  fragmentShader: `
    uniform float iTime; uniform sampler2D tDiffuse; uniform sampler2D bloomTexture; uniform sampler2D torusTexture; uniform sampler2D haloTexture;
    uniform vec3 uBg; uniform vec3 uBgLow;
    varying vec2 vUv;
    /* a quiet sky: deep navy low on the screen fading to near-black above, plus a hair of noise so the
       gradient never bands on 8-bit displays. (The template's animated "flame" bands were dropped on purpose.) */
    void main(){
      vec2 uv = 2.*vUv - 1.;
      float low = smoothstep(1.1, -0.9, uv.y) * (1.0 - 0.35 * abs(uv.x));
      vec3 bg = mix(uBg * 0.75, uBgLow, low * 0.9);
      float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
      vec3 col = bg + texture2D(bloomTexture, vUv).xyz + texture2D(torusTexture, vUv).xyz + texture2D(tDiffuse, vUv).xyz + texture2D(haloTexture, vUv).xyz;
      gl_FragColor = vec4(col + n / 255.0, 1.0);
    }`,
};
const finalPass = new ShaderPass(FinalPass);
finalPass.uniforms.bloomTexture.value = bloomComposer.renderTarget1.texture;
finalPass.uniforms.torusTexture.value = torusComposer.renderTarget1.texture;
const finalComposer = new EffectComposer(renderer);
finalComposer.addPass(new RenderPass(scene, camera));
finalComposer.addPass(finalPass);

/* ---------- groups + scroll keyframes */
const STOPS_X = [{ p: 0, v: 0 }, { p: 0.32, v: -3.1 }, { p: 0.64, v: 3.2 }, { p: 1, v: 0 }];
const heroY = () => (window.innerWidth < 760 ? -6.6 : -5.3);
const STOPS_Y = [{ p: 0, v: heroY() }, { p: 0.32, v: 0.55 }, { p: 0.64, v: 0.45 }, { p: 1, v: 0.15 }];
const STOPS_S = [{ p: 0, v: 2.15 }, { p: 0.32, v: 1.0 }, { p: 0.64, v: 0.92 }, { p: 1, v: 1.12 }];
const worldGroup = new THREE.Group();
const planetGroup = new THREE.Group(); planetGroup.rotation.z = CONFIG.tilt;
const cloudGroup = new THREE.Group(); cloudGroup.rotation.z = CONFIG.tilt; cloudGroup.visible = false;
worldGroup.add(planetGroup, cloudGroup);
worldGroup.position.set(STOPS_X[0].v, STOPS_Y[0].v, 0); worldGroup.scale.setScalar(STOPS_S[0].v);
scene.add(worldGroup);

/* ---------- atmosphere halo */
const glowMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  transparent: true, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uGlow: { value: hexToVec3(CONFIG.glowColor) }, uGlowEdge: { value: hexToVec3("#bfe4ff") }, uIntensity: { value: CONFIG.glowIntensity } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `uniform vec3 uGlow; uniform vec3 uGlowEdge; uniform float uIntensity; varying vec2 vUv;
    void main(){ float d = length(vUv - 0.5) * 2.0;
      float disc = 1.0 / 2.3;                                    /* planet limb in plane units (half-extent = 2.3 radii) */
      float x = clamp((d - disc) / (1.0 - disc), 0.0, 1.0);      /* 0 at the limb, 1 at the plane edge */
      float outer = exp(-x * 6.0) * (1.0 - x);                   /* one smooth exponential falloff, no shoulders */
      float inner = smoothstep(disc - 0.015, disc + 0.01, d);     /* the disc itself stays clear so the surface reads */
      float a = outer * inner;
      vec3 col = mix(uGlowEdge, uGlow, smoothstep(0.0, 0.3, x));  /* pale cyan at the limb easing into deep blue */
      gl_FragColor = vec4(col * a * uIntensity, a); }`,
}));
glowMesh.scale.setScalar(CONFIG.planetRadius * 2.3); glowMesh.layers.set(LAYERS.BLOOM_SCENE); worldGroup.add(glowMesh);

/* ---------- shared time uniforms */
const planetTime = { value: 0 }, cloudTime = { value: 0 }, starTime = { value: 0 }, markerTime = { value: 0 };
const uRes = { value: new THREE.Vector2(window.innerWidth, window.innerHeight) };

/* ---------- motes */
{
  const n = CONFIG.atmoCount, pos = new Float32Array(n * 3), sz = new Float32Array(n), seed = new Float32Array(n);
  for (let i = 0; i < n; i++) { pos[i * 3] = Math.random() * 2 - 1; pos[i * 3 + 1] = Math.random() * 2 - 1; pos[i * 3 + 2] = Math.random() * 2 - 1; sz[i] = CONFIG.atmoSize * (0.4 + Math.random()); seed[i] = Math.random() * 100; }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("size", new THREE.BufferAttribute(sz, 1)); g.setAttribute("seed", new THREE.BufferAttribute(seed, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uRes, uColor: { value: hexToVec3(CONFIG.atmoColor) } },
    vertexShader: `attribute float size; attribute float seed; uniform float uTime; uniform vec2 uRes; varying float vA;
      vec3 warp(vec3 p, float t){ float c=0.9,a=1.9,b=0.02,s=0.05; p*=2.;
        p.x+=c*sin(s*t+a*p.y)+t*b; p.y+=c*cos(s*t+a*p.x); p.y+=c*sin(s*t+a*p.z)+t*b;
        p.z+=c*cos(s*t+a*p.y); p.z+=c*sin(s*t+a*p.x)+t*b; p.x+=c*cos(s*t+a*p.z); return cos(p+vec3(1,2,4)); }
      void main(){ vec3 v = position*4.0 + warp(position, uTime)*1.2; vec4 mv = modelViewMatrix * vec4(v, 1.0);
        float r = length(v); float farF = 1.0 - smoothstep(5.0, 6.5, r); float nearF = smoothstep(0.0, 0.5, -mv.z); vA = farF * nearF;
        gl_PointSize = size * uRes.y / 900.0 / -mv.z; gl_PointSize = max(gl_PointSize, 1.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uColor; varying float vA; void main(){ vec2 p = gl_PointCoord - 0.5; float l = length(p); if (l > 0.5) discard;
      float tex = smoothstep(0.5, 0.0, l); gl_FragColor = vec4(uColor * tex, tex * vA * 0.55); }` });
  const motes = new THREE.Points(g, m); motes.frustumCulled = false; motes.layers.set(LAYERS.BLOOM_SCENE);
  motes.onBeforeRender = () => { const now = performance.now() / 1000; m.uniforms.uTime.value = now * CONFIG.atmoSpeed * 8; motes.position.copy(camera.position); finalPass.uniforms.iTime.value = now; };
  scene.add(motes);
}

/* ---------- starfield */
{
  const n = CONFIG.starCount, pos = new Float32Array(n * 3), seed = new Float32Array(n), bright = new Float32Array(n);
  for (let i = 0; i < n; i++) { const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = Math.sqrt(1 - u * u);
    pos[i * 3] = 90 * r * Math.cos(th); pos[i * 3 + 1] = 90 * r * Math.sin(th); pos[i * 3 + 2] = 90 * u; seed[i] = Math.random() * 100; bright[i] = 0.35 + Math.random() * 0.65; }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("seed", new THREE.BufferAttribute(seed, 1)); g.setAttribute("bright", new THREE.BufferAttribute(bright, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, depthTest: true, blending: THREE.AdditiveBlending,
    uniforms: { uTime: starTime, uSize: { value: CONFIG.starSize }, uFlicker: { value: CONFIG.starFlicker }, uColor: { value: hexToVec3(CONFIG.starColor) }, uRes },
    vertexShader: `attribute float seed; attribute float bright; uniform float uTime; uniform float uSize; uniform float uFlicker; uniform vec2 uRes; varying float vTw;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); float tw = 0.6 + 0.4 * sin(uTime * uFlicker + seed); vTw = bright * tw;
        gl_PointSize = max(uSize * uRes.y / 900.0 * (90.0 / max(-mv.z, 1.0)), 1.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uColor; varying float vTw; void main(){ vec2 p = gl_PointCoord - 0.5; float l = length(p); if (l > 0.5) discard;
      float core = smoothstep(0.5, 0.0, l); gl_FragColor = vec4(uColor, core * vTw); }` });
  const stars = new THREE.Points(g, m); stars.frustumCulled = false; stars.layers.set(LAYERS.TORUS_SCENE); scene.add(stars);
}

/* ---------- loaders */
const draco = new DRACOLoader(); draco.setDecoderPath("vendor/three143/draco/");
const gltfLoader = new GLTFLoader(); gltfLoader.setDRACOLoader(draco);
const firstMesh = (root) => { let m = null; root.traverse((o) => { if (!m && o.isMesh) m = o; }); return m; };
let planetMesh = null, nightTex = null, entryStart = -1;
const ENTRY_DUR = 1.9, ENTRY_START_Y = -6.5;

/* loading progress for the intro screen, and the hand-off: the planet floats up only once the intro has lifted */
const prog = { lights: 0, planet: 0, clouds: 0 }, weights = { lights: 0.15, planet: 0.7, clouds: 0.15 };
const emit = () => window.dispatchEvent(new CustomEvent("scene:progress", { detail: { p: Object.keys(prog).reduce((a, k) => a + prog[k] * weights[k], 0) } }));
const report = (key, e) => { prog[key] = Math.max(prog[key], e && e.total ? e.loaded / e.total : 0.5); emit(); };
let introDone = !document.getElementById("intro");
window.addEventListener("intro:done", () => { introDone = true; maybeStartEntry(); }, { once: true });
function maybeStartEntry() { if (planetMesh && introDone && entryStart === -1) entryStart = reduce ? -2 : performance.now() / 1000; }

/* ---------- cloud shells */
new THREE.TextureLoader().load(CLOUDS_PNG, (tex) => {
  prog.clouds = 1; emit();
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(5, 5);
  const layers = [
    { h: CONFIG.cloud1Height, o: CONFIG.cloud1Opacity, s: "cloud1Spin", ry: 0.0, phase: 0.0 },
    { h: CONFIG.cloud2Height, o: CONFIG.cloud2Opacity, s: "cloud2Spin", ry: 2.2, phase: 13.0 },
    { h: CONFIG.cloud3Height, o: CONFIG.cloud3Opacity, s: "cloud3Spin", ry: 4.3, phase: 27.0 },
  ];
  layers.forEach((L) => {
    const mat = new THREE.MeshStandardMaterial({ map: tex, transparent: true, depthWrite: false });
    mat.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, { uTime: cloudTime, noiseScale: { value: 20 }, uSpeedX: { value: 1 }, uSpeedY: { value: 2 }, uSpeedZ: { value: 2 }, uOpacity: { value: L.o }, uPhase: { value: L.phase } });
      sh.vertexShader = "varying vec2 vCloudUv;\n" + sh.vertexShader.replace("void main() {", "void main() {\n vCloudUv = uv;");
      sh.fragmentShader = "uniform float uTime; uniform float noiseScale; uniform float uSpeedX; uniform float uSpeedY; uniform float uSpeedZ; uniform float uOpacity; uniform float uPhase; varying vec2 vCloudUv;\n" + SNOISE + "\n" +
        sh.fragmentShader.replace("#include <dithering_fragment>", `#include <dithering_fragment>
gl_FragColor.rgb = vec3(1.0);
float cloudNoise = snoise(vec3(vCloudUv.x * noiseScale + uTime * uSpeedX + uPhase, vCloudUv.y * noiseScale - uTime * uSpeedY + uPhase, uTime * uSpeedZ + uPhase));
float cloudNdv = max(dot(normalize(vNormal), normalize(vViewPosition)), 0.0);
float cloudEdge = pow(1.0 - cloudNdv, 3.0);
float cloudMod = cloudNoise * (1.0 - cloudEdge * 0.9);   /* clouds thin out at the limb instead of stacking into bright rings */
float cloudNdl = dot(normalize(vNormal), normalize(vec3(-0.9, 0.18, 0.4)));
float cloudDay = 1.0 - smoothstep(0.30, -0.30, cloudNdl) * 0.9;
gl_FragColor.a *= cloudMod * uOpacity * cloudDay;`);
    };
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(CONFIG.planetRadius * L.h, 64, 64), mat);
    mesh.rotation.y = L.ry; mesh.renderOrder = 2; mesh.userData.spinKey = L.s; mesh.layers.set(LAYERS.ENTIRE_SCENE); cloudGroup.add(mesh);
  });
});

/* ---------- planet */
gltfLoader.load(LIGHTS_GLB, (g) => {
  prog.lights = 1; emit();
  const lm = firstMesh(g.scene); nightTex = lm && lm.material && lm.material.map;
  gltfLoader.load(PLANET_GLB, onPlanet, (e) => report("planet", e), (e) => console.warn("planet failed", e));
}, (e) => report("lights", e), () => gltfLoader.load(PLANET_GLB, onPlanet, (e) => report("planet", e)));

function onPlanet(g) {
  const mesh = firstMesh(g.scene); if (!mesh) return;
  mesh.geometry.computeBoundingSphere();
  mesh.scale.setScalar(CONFIG.planetRadius / mesh.geometry.boundingSphere.radius);
  const mat = mesh.material.clone(); mat.metalness = 0; mat.roughness = 1; mat.envMapIntensity = 0;
  mat.extensions = { derivatives: true };
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, { time: planetTime, noiseScale: { value: 30 }, speedX: { value: 1.5 }, speedY: { value: 2.0 }, speedZ: { value: 2.5 },
      rimColor: { value: hexToVec3(CONFIG.rimColor) }, rimPower: { value: CONFIG.rimPower }, nightBlendTexture: { value: nightTex || blackTex }, nightLights: { value: CONFIG.nightLights },
      terrainDepth: { value: CONFIG.terrainDepth }, terrainShade: { value: CONFIG.terrainShade }, oceanGlint: { value: CONFIG.oceanGlint }, oceanDeep: { value: CONFIG.oceanDeep },
      oceanFlow: { value: CONFIG.oceanFlow }, oceanFlowSpeed: { value: CONFIG.oceanFlowSpeed }, oceanFlowScale: { value: CONFIG.oceanFlowScale } });
    sh.vertexShader = "varying vec2 vCustomUv;\n" + sh.vertexShader.replace("void main() {", "void main() {\n vCustomUv = uv;");
    sh.fragmentShader = `uniform float time; uniform float noiseScale; uniform float speedX; uniform float speedY; uniform float speedZ; uniform vec3 rimColor; uniform float rimPower;
uniform sampler2D nightBlendTexture; uniform float nightLights; uniform float terrainDepth; uniform float terrainShade; uniform float oceanGlint; uniform float oceanDeep;
uniform float oceanFlow; uniform float oceanFlowSpeed; uniform float oceanFlowScale; varying vec2 vCustomUv;
` + SNOISE + "\n" + sh.fragmentShader.replace("#include <dithering_fragment>", `#include <dithering_fragment>
vec3 normalizedNormal = normalize(vNormal);
vec3 viewDir = normalize(vViewPosition);
float rim = 1.0 - max(dot(viewDir, normalizedNormal), 0.0);
rim = pow(rim, rimPower); rim = pow(rim, 1.5); rim *= 0.7;
vec3 currentColor = gl_FragColor.rgb;
float blueDom = currentColor.b - max(currentColor.r, currentColor.g);
float waterMask = clamp(smoothstep(-0.005, 0.03, blueDom), 0.0, 1.0);
float shimmer = snoise(vec3(vCustomUv.x * noiseScale + time * speedX, vCustomUv.y * noiseScale - time * speedY, time * speedZ));
gl_FragColor.rgb += waterMask * shimmer * 0.025;
float fT = time * oceanFlowSpeed * 4.0;
float fS = 4.0 * oceanFlowScale;
float warp = snoise(vec3(vCustomUv.x * fS - fT * 0.5, vCustomUv.y * fS + fT * 0.4, fT * 0.5));
float flow = snoise(vec3(vCustomUv.x * fS * 2.0 + fT * 0.6 + warp, vCustomUv.y * fS * 2.0 - fT * 0.5, fT * 0.7));
flow = warp * 0.6 + flow * 0.4;
gl_FragColor.rgb += waterMask * flow * 0.12 * oceanFlow;
gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.01, 0.06, 0.16), waterMask * oceanDeep);
vec3 finalColor = mix(gl_FragColor.rgb, rimColor, rim);
gl_FragColor = vec4(finalColor, 1.0);
vec3 surfPos = -vViewPosition;
float terrH = dot(texture2D(map, vCustomUv).rgb, vec3(0.299, 0.587, 0.114));
vec3 sigX = dFdx(surfPos), sigY = dFdy(surfPos);
vec3 vR1 = cross(sigY, normalizedNormal), vR2 = cross(normalizedNormal, sigX);
float fDet = dot(sigX, vR1);
vec3 vGrad = sign(fDet) * (dFdx(terrH) * vR1 + dFdy(terrH) * vR2);
vec3 bumpedNormal = normalize(abs(fDet) * normalizedNormal - terrainDepth * vGrad);
vec3 shadeNormal = mix(bumpedNormal, normalizedNormal, waterMask);
vec3 cityLights = texture2D(nightBlendTexture, vCustomUv).rgb * gl_FragColor.rgb * nightLights;
vec3 viewSunDir = normalize(vec3(-0.9, 0.18, 0.4));
float ndl = dot(normalizedNormal, viewSunDir);
float dayAmt = smoothstep(-0.05, 0.35, ndl);
float relief = dot(shadeNormal, viewSunDir) - ndl;
gl_FragColor.rgb *= clamp(1.0 + relief * terrainShade * dayAmt, 0.55, 1.6);
float nightFactor  = smoothstep(0.18, -0.30, ndl);
float lightsFactor = smoothstep(0.30, -0.35, ndl);
gl_FragColor.rgb = mix(gl_FragColor.rgb, gl_FragColor.rgb * 0.08, nightFactor);
gl_FragColor.rgb += cityLights * lightsFactor;
vec3 halfDir = normalize(viewSunDir + viewDir);
float ripple = snoise(vec3(vCustomUv * 240.0, time * 4.0));
float ndh = max(dot(normalizedNormal, halfDir) + ripple * 0.02, 0.0);
float glint = pow(ndh, 140.0);
gl_FragColor.rgb += glint * waterMask * dayAmt * oceanGlint * vec3(1.0, 0.97, 0.88);`);
  };
  mesh.material = mat; mesh.layers.set(LAYERS.ENTIRE_SCENE);
  planetGroup.add(mesh); planetMesh = mesh; cloudGroup.visible = true;
  prog.planet = 1; emit(); window.dispatchEvent(new Event("scene:ready"));
  maybeStartEntry();
  try { buildMarkers(mesh); } catch (e) { console.warn("markers skipped", e); }
}

/* ---------- land markers (radar pings on land) */
function buildMarkers(mesh) {
  const map = mesh.material.map; if (!map || !map.image) return;
  const img = map.image, cw = img.width || 1024, ch = img.height || 512;
  const cv = document.createElement("canvas"); cv.width = cw; cv.height = ch;
  const ctx = cv.getContext("2d"); ctx.drawImage(img, 0, 0, cw, ch);
  const data = ctx.getImageData(0, 0, cw, ch).data;
  const geo = mesh.geometry, pos = geo.attributes.position, uv = geo.attributes.uv, idx = geo.index;
  if (!uv) return;
  const triCount = idx ? idx.count / 3 : pos.count / 3;
  const cum = new Float32Array(triCount); let total = 0;
  const A = new THREE.Vector3(), B = new THREE.Vector3(), C = new THREE.Vector3();
  const tri = (i) => idx ? [idx.getX(i * 3), idx.getX(i * 3 + 1), idx.getX(i * 3 + 2)] : [i * 3, i * 3 + 1, i * 3 + 2];
  for (let i = 0; i < triCount; i++) { const [a, b, c] = tri(i); A.fromBufferAttribute(pos, a); B.fromBufferAttribute(pos, b); C.fromBufferAttribute(pos, c);
    total += B.sub(A).cross(C.sub(A)).length() * 0.5; cum[i] = total; }
  const out = [], seeds = []; let guard = 0;
  while (out.length < CONFIG.markerCount * 3 && guard++ < CONFIG.markerCount * 60) {
    const r = Math.random() * total; let lo = 0, hi = triCount - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cum[mid] < r) lo = mid + 1; else hi = mid; }
    const [a, b, c] = tri(lo); let u = Math.random(), v = Math.random(); if (u + v > 1) { u = 1 - u; v = 1 - v; } const w = 1 - u - v;
    const tu = uv.getX(a) * w + uv.getX(b) * u + uv.getX(c) * v, tv = uv.getY(a) * w + uv.getY(b) * u + uv.getY(c) * v;
    const px = Math.floor(((tu % 1) + 1) % 1 * (cw - 1)), py = Math.floor((1 - (((tv % 1) + 1) % 1)) * (ch - 1));
    const k = (py * cw + px) * 4, cr = data[k], cg = data[k + 1], cb = data[k + 2];
    if (cb > cr + 6 && cb > cg + 6) continue;   // ocean
    A.fromBufferAttribute(pos, a); B.fromBufferAttribute(pos, b); C.fromBufferAttribute(pos, c);
    const P = A.multiplyScalar(w).add(B.multiplyScalar(u)).add(C.multiplyScalar(v)).multiplyScalar(1.012);
    out.push(P.x, P.y, P.z); seeds.push(Math.random());
  }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(out, 3)); g.setAttribute("seed", new THREE.Float32BufferAttribute(seeds, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthTest: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: markerTime, uColor: { value: hexToVec3(CONFIG.markerColor) }, uSize: { value: CONFIG.markerSize }, uSpeed: { value: CONFIG.markerSpeed }, uRes },
    vertexShader: `attribute float seed; uniform float uSize; uniform vec2 uRes; varying float vSeed; varying float vFade;
      void main(){ vSeed = seed; vec4 mv = modelViewMatrix * vec4(position, 1.0); vec3 vn = normalize(normalMatrix * normalize(position)); vec3 vd = normalize(-mv.xyz);
        vFade = smoothstep(0.15, 0.5, dot(vn, vd)); gl_PointSize = max(uSize * uRes.y / 900.0 * (7.0 / max(-mv.z, 1.0)), 2.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uTime; uniform float uSpeed; varying float vSeed; varying float vFade;
      void main(){ if (vFade <= 0.001) discard; vec2 p = gl_PointCoord - 0.5; float d = length(p) * 2.0; if (d > 1.0) discard;
        float core = smoothstep(0.30, 0.0, d) * 1.2; float ph = fract(uTime * uSpeed + vSeed); float ring = smoothstep(0.07, 0.0, abs(d - ph)) * (1.0 - ph);
        gl_FragColor = vec4(uColor, clamp(core + ring, 0.0, 1.0) * vFade); }` });
  const pts = new THREE.Points(g, m); pts.frustumCulled = false; pts.layers.set(LAYERS.BLOOM_SCENE); mesh.add(pts);
}

/* ---------- scroll choreography + loop */
let curP = 0, curX = STOPS_X[0].v, curY = STOPS_Y[0].v, curS = STOPS_S[0].v, spinPhase = 0;
window.__sceneState = { get p() { return curP; }, get loaded() { return !!planetMesh; } };
function resize() {
  const w = window.innerWidth, h = window.innerHeight, pr = Math.min(window.devicePixelRatio || 1, 1.5);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  renderer.setPixelRatio(pr); renderer.setSize(w, h, false);
  [torusComposer, bloomComposer, finalComposer].forEach((c) => { c.setPixelRatio(pr); c.setSize(w, h); });
  uRes.value.set(w, h); STOPS_Y[0].v = heroY();
}
window.addEventListener("resize", resize); resize();

const clock = new THREE.Clock();
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05);
  if (!document.hidden) {
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const pTarget = reduce ? 0 : clamp(window.scrollY / max, 0, 1);
    curP += (pTarget - curP) * Math.min(1, dt * 4.5);
    const sideScale = clamp(window.innerWidth / 1200, 0.5, 1);
    const k = Math.min(1, dt * 3.2);
    curX += (sample(STOPS_X, curP) * sideScale - curX) * k;
    curY += (sample(STOPS_Y, curP) - curY) * k;
    const narrow = window.innerWidth < 760 ? 0.72 : 1;
    curS += (sample(STOPS_S, curP) * narrow - curS) * k;
    let entryY = 0;
    if (entryStart >= 0) { const t = clamp((performance.now() / 1000 - entryStart) / ENTRY_DUR, 0, 1); entryY = ENTRY_START_Y * (1 - (1 - Math.pow(1 - t, 3))); }
    else if (entryStart === -1) entryY = ENTRY_START_Y;       // not loaded yet: keep it below the fold
    worldGroup.position.set(curX, curY + entryY, 0); worldGroup.scale.setScalar(curS);
    if (!reduce) spinPhase += dt * CONFIG.spin;
    planetGroup.rotation.y = CONFIG.initRotation + spinPhase + curP * Math.PI * 1.6;
    cloudGroup.rotation.y = planetGroup.rotation.y;
    cloudGroup.children.forEach((c) => { if (!reduce) c.rotation.y += dt * CONFIG[c.userData.spinKey]; });
    glowMesh.quaternion.copy(camera.quaternion);
    glowMesh.material.uniforms.uIntensity.value = CONFIG.glowIntensity * Math.min(1, 1.1 / Math.max(0.3, curS));   // a close-up planet gets a quieter halo so the hero copy stays readable
    if (!reduce) { planetTime.value += dt / 12; cloudTime.value += dt / 20; starTime.value += dt; markerTime.value += dt; }
    controls.update();
    camera.layers.set(LAYERS.TORUS_SCENE); torusComposer.render();
    camera.layers.set(LAYERS.BLOOM_SCENE); bloomComposer.render();
    camera.layers.set(LAYERS.ENTIRE_SCENE); finalComposer.render();
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
