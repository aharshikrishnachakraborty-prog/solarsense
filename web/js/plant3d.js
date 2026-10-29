// Plant 3D view on the Overview page: a slowly turning model of the plant with one block of panels per
// inverter, coloured by that inverter's status on the replay date. Drawn with Three.js (loaded from a CDN,
// see the import map in index.html). The numbers come from /api/inverters/status — nothing is computed here.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildPlant, disposePlant, paintBlock } from "./plant3d_models.js";
import { fitCamera, screenPoint, startReset, stepReset } from "./plant3d_camera.js";

const AUTO_ROTATE_SPEED = 1.0;          // OrbitControls unit: 1.0 = one full turn every 60 seconds
const RESUME_DELAY_MS = 4000;           // after the user stops touching the view, wait this long...
const EASE_IN_SECONDS = 1;              // ...then speed back up smoothly over this many seconds
const TILT_LIMITS = [20, 75];           // degrees from straight above: never below the ground, never flat
const CLICK_MAX_MOVE_PX = 6;            // moving more than this between press and release = a drag, not a click

const deg = THREE.MathUtils.degToRad;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
const raycaster = new THREE.Raycaster();

let view, renderer, scene, camera, controls, sky, sun;
let plant = null, rows = new Map(), where = { plant: null, date: null };
let frameId = null, lastFrame = 0, onScreen = true;
let paused = reducedMotion, spin = 0, lastTouch = -Infinity, dragging = false, resetMove = null;
let pointer = null, pointerMoved = false, pressedAt = null, hovered = null, fitDistance = 100, describe;

/** Creates the renderer, lights, camera and mouse controls inside the given element. Throws if WebGL is missing.
 *  options.describe(row) returns the tooltip HTML for one inverter (written in overview.js). */
export function start(container, options) {
  view = container;
  describe = options.describe;
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("webgl2", { antialias: true, alpha: true });
  if (!context) throw new Error("WebGL 2 is not available");   // overview.js then shows the friendly message
  renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: true });   // alpha: page colour shows through
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));   // sharp, but never more than 2× the pixels
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = view.clientWidth > 640;   // soft shadows on laptops; skipped on phones to stay smooth
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  view.prepend(canvas);

  scene = new THREE.Scene();
  sky = new THREE.HemisphereLight(0xe0f2fe, 0x3f4f3a, 1.2);   // soft light from all around (sky above, grass below)
  sun = new THREE.DirectionalLight(0xfff1d6, 2.4);              // the sun: bright side, dark side and shadows
  sun.castShadow = renderer.shadowMap.enabled;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.0004;
  scene.add(sky, sun, sun.target);

  camera = new THREE.PerspectiveCamera(35, 1, 1, 1000);
  controls = new OrbitControls(camera, canvas);
  Object.assign(controls, {
    enablePan: false, enableDamping: true, dampingFactor: 0.08,          // no sliding away; a soft glide after a drag
    minPolarAngle: deg(TILT_LIMITS[0]), maxPolarAngle: deg(TILT_LIMITS[1]),
    autoRotate: true, autoRotateSpeed: 0,                                // speed is set every frame (eases in and out)
  });
  controls.target.set(0, 1, 0);           // turn around the middle of the plant, never drifting off
  canvas.style.touchAction = "pan-y";     // phones: a vertical swipe still scrolls the page
  const hint = document.getElementById("plant3d-hint");
  if (coarsePointer) hint.textContent = "Drag sideways to rotate · Pinch to zoom";
  hint.hidden = false;   // fades away after the first drag or zoom
  controls.addEventListener("start", () => { dragging = true; spin = 0; resetMove = null; noteTouch(); hint.classList.add("faded"); });
  controls.addEventListener("end", () => { dragging = false; noteTouch(); });
  listen(canvas);
  // At the zoom limit, the mouse wheel scrolls the page again instead of getting stuck on the 3D view.
  view.addEventListener("wheel", (event) => {
    const distance = controls.getDistance();
    if (event.deltaY > 0 ? distance >= controls.maxDistance - 0.01 : distance <= controls.minDistance + 0.01) event.stopPropagation();
  }, { capture: true, passive: true });
  canvas.addEventListener("webglcontextlost", () => message("3D view not available on this device"));
  new ResizeObserver(resize).observe(view);
  new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; runLoop(); }).observe(view);
  document.addEventListener("visibilitychange", runLoop);   // hidden tab = no drawing
  document.getElementById("plant3d-reset").addEventListener("click", resetView);
  document.getElementById("plant3d-pause").addEventListener("click", () => setPaused(!paused));
  setPaused(paused);
  resize();
}

/** Shows one plant on one day: rebuilds the model if the inverter list changed, then colours every block. */
export function show(status, info) {
  where = info;
  if (!status || !status.inverters.length) {
    if (plant) plant.group.visible = false;
    message("Inverter status is not available for this day.");
    return;
  }
  const ids = status.inverters.map((row) => row.inverter);
  if (!plant || plant.ids.join() !== ids.join()) rebuild(ids);
  rows = new Map(status.inverters.map((row) => [row.inverter, row]));
  for (const block of plant.blocks) paintBlock(plant, block, rows.get(block.id)?.status || "offline");
  plant.group.visible = true;
  if (hovered) { const block = hovered; hovered = null; setHovered(block); }   // refresh the tooltip numbers
  message("");
  runLoop();
}

/** Live replay: the sun crosses the sky with the replay clock and gets dimmer when the sensor sees less sunlight. */
export function setSun(timestamp, irradiation) {
  if (!plant) return;
  const hour = Number(timestamp.slice(11, 13)) + Number(timestamp.slice(14, 16)) / 60;
  const angle = Math.PI * Math.min(Math.max((hour - 6) / 12, 0), 1);   // 6:00 east, 12:00 overhead, 18:00 west
  const r = plant.radius * 1.2;
  sun.position.set(Math.cos(angle) * r, Math.max(Math.sin(angle), 0.08) * r, plant.radius * 0.45);
  const strength = Math.min(Math.max(irradiation || 0, 0), 1.1);       // kW/m² from the plant's weather sensor
  sun.intensity = 0.15 + 2.6 * strength;
  sky.intensity = 0.55 + 0.7 * strength;
}

/** Back to the normal mid-morning sun (when the replay stops). */
export function resetSun() {
  if (!plant) return;
  sun.position.set(plant.radius * 0.5, plant.radius * 1.1, plant.radius * 0.6);
  sun.intensity = 2.4;
  sky.intensity = 1.2;
}

/** Numbers about the current view, used by our automated browser test. */
export function viewInfo() {
  return {
    azimuth: controls.getAzimuthalAngle(), polar: controls.getPolarAngle(), distance: controls.getDistance(),
    minDistance: controls.minDistance, maxDistance: controls.maxDistance, spin, paused, running: frameId !== null,
    blocks: plant ? plant.blocks.map((b) => ({ id: b.id, status: b.status, ...screenPoint(b, plant, camera, view) })) : [],
  };
}

function rebuild(ids) {
  setHovered(null);
  if (plant) { scene.remove(plant.group); disposePlant(plant); }
  plant = buildPlant(ids);
  scene.add(plant.group);
  const r = plant.radius;
  Object.assign(sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: r * 4 });
  sun.shadow.camera.updateProjectionMatrix();
  resetSun();
  fitDistance = fitCamera(camera, controls, plant, false);
}

/** "Reset view": glide back to the starting angle and zoom. */
function resetView() {
  if (!plant) return;
  resetMove = startReset(camera, controls);
  spin = 0;
  noteTouch();
}

function setPaused(value) {
  paused = value;
  document.getElementById("plant3d-pause").setAttribute("aria-pressed", String(paused));
  document.getElementById("plant3d-pause-label").textContent = paused ? "Play" : "Pause";
  document.getElementById("plant3d-pause-icon").setAttribute("d", paused ? "M5 3.5l7 4.5-7 4.5z" : "M5.5 3.5v9M10.5 3.5v9");
}

/** Mouse and finger handling on top of OrbitControls: hover tooltip, click to open, tap twice on phones. */
function listen(canvas) {
  canvas.addEventListener("pointermove", (event) => {
    pointer = pointAt(event);
    pointerMoved = true;
    if (event.pointerType === "mouse") noteTouch();   // the mouse is over the view: hold still
    if (pressedAt && Math.hypot(event.clientX - pressedAt.x, event.clientY - pressedAt.y) > CLICK_MAX_MOVE_PX) setHovered(null);   // a drag
  });
  canvas.addEventListener("pointerleave", (event) => {   // fingers "leave" after every tap, so only the mouse counts
    if (event.pointerType === "mouse") { pointer = null; setHovered(null); noteTouch(); }
  });
  canvas.addEventListener("pointerdown", (event) => { pressedAt = { x: event.clientX, y: event.clientY }; });
  canvas.addEventListener("pointerup", (event) => {
    const moved = !pressedAt || Math.hypot(event.clientX - pressedAt.x, event.clientY - pressedAt.y) > CLICK_MAX_MOVE_PX;
    pressedAt = null;
    if (moved) return;
    const block = blockAt(pointAt(event));
    if (block && (event.pointerType === "mouse" || hovered === block)) open(block);
    else { pointer = pointAt(event); setHovered(block); }   // first tap on a phone shows the numbers
  });
}

function pointAt(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top, width: rect.width, height: rect.height, mouse: event.pointerType === "mouse" };
}

/** Which block is under this point? (A ray from the camera through the mouse, tested against invisible boxes.) */
function blockAt(point) {
  if (!plant || !point) return null;
  raycaster.setFromCamera(new THREE.Vector2((point.x / point.width) * 2 - 1, 1 - (point.y / point.height) * 2), camera);
  const hit = raycaster.intersectObjects(plant.blocks.map((b) => b.hit), false)[0];
  return hit ? plant.blocks.find((b) => b.hit === hit.object) : null;
}

function setHovered(block) {
  const tip = document.getElementById("plant3d-tip");
  if (block !== hovered) {
    hovered = block;
    if (plant) plant.outline.visible = Boolean(block);
    view.style.cursor = block ? "pointer" : "";
    tip.hidden = !block;
    if (!block) return;
    plant.outline.position.set(block.centre.x, 1.3, block.centre.z);
    tip.innerHTML = describe(rows.get(block.id) || { inverter: block.id, status: block.status });
  }
  if (block && pointer) {   // keep the tooltip next to the pointer but inside the view
    tip.style.left = `${Math.min(pointer.x + 14, view.clientWidth - tip.offsetWidth - 8)}px`;
    tip.style.top = `${Math.min(pointer.y + 14, view.clientHeight - tip.offsetHeight - 8)}px`;
  }
}

function open(block) {
  window.location.href = `inverter.html?id=${encodeURIComponent(block.id)}&date=${where.date}&plant=${where.plant}`;
}

const noteTouch = () => { lastTouch = performance.now(); };

function message(text) {
  const box = document.getElementById("plant3d-message");
  box.textContent = text;
  box.hidden = !text;
}

function resize() {
  const width = view.clientWidth, height = view.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  if (plant) fitDistance = fitCamera(camera, controls, plant, true, fitDistance);
}

/** Draw only while the card is on screen and the tab is visible (saves battery and laptop fans). */
function runLoop() {
  const shouldRun = Boolean(plant) && onScreen && !document.hidden;
  if (shouldRun && frameId === null) { lastFrame = performance.now(); frameId = requestAnimationFrame(frame); }
  if (!shouldRun && frameId !== null) { cancelAnimationFrame(frameId); frameId = null; }
}

function frame(now) {
  frameId = requestAnimationFrame(frame);
  const dt = Math.min(Math.max((now - lastFrame) / 1000, 0), 0.25);   // seconds since the last frame (capped)
  lastFrame = now;
  // Turn only when nobody is using the view; speed up gently (smoothstep), stop within a quarter second.
  const wantSpin = !paused && !dragging && !resetMove && !hovered && now - lastTouch > RESUME_DELAY_MS;
  spin = wantSpin ? Math.min(1, spin + dt / EASE_IN_SECONDS) : Math.max(0, spin - dt * 4);
  controls.autoRotateSpeed = AUTO_ROTATE_SPEED * spin * spin * (3 - 2 * spin);
  if (resetMove && stepReset(resetMove, dt, camera, controls, fitDistance)) { resetMove = null; noteTouch(); }
  controls.update(dt);   // passing dt makes auto-rotate depend on time, not on the screen's frame rate
  if (!dragging && pointerMoved && pointer?.mouse) setHovered(blockAt(pointer));
  pointerMoved = false;
  if (!reducedMotion) {   // red markers bob and pulse gently
    const t = now / 1000;
    plant.markerMaterial.emissiveIntensity = 0.6 + 0.4 * Math.sin(t * 4);
    plant.materials.glow.critical.opacity = 0.5 + 0.15 * Math.sin(t * 4);
    for (const block of plant.blocks) if (block.marker.visible) block.marker.position.y = 4.2 + 0.25 * Math.sin(t * 2.5);
  }
  renderer.render(scene, camera);
}
