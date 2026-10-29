// Camera helpers for the Plant 3D view: frame the whole plant, set the zoom limits, and glide back
// to the starting angle when the operator presses "Reset view". Used by plant3d.js.
import * as THREE from "three";

const deg = THREE.MathUtils.degToRad;
export const START_VIEW = { polar: deg(50), azimuth: deg(35) };   // camera 40° above the ground, turned a little
const RESET_SECONDS = 0.9;

/** Puts the camera at a distance, tilt (polar) and turn (azimuth) around the target, looking at it. */
export function placeCamera(camera, target, distance, polar, azimuth) {
  camera.position.setFromSpherical(new THREE.Spherical(distance, polar, azimuth)).add(target);
  camera.lookAt(target);
  camera.updateMatrixWorld();
}

/** Finds how far away the camera must be so the whole plant fits from every side, and sets the zoom limits.
 *  keepAngle = true keeps the user's current angle (after a resize); false jumps to the starting view. */
export function fitCamera(camera, controls, plant, keepAngle, previousFit) {
  const before = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  const edge = [];
  for (let i = 0; i < 24; i++) {   // a circle around the plant (+ tower height): while it turns, it stays in frame
    const a = (i / 24) * Math.PI * 2, r = plant.radius;
    edge.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r),
      new THREE.Vector3(Math.cos(a) * r * 0.7, plant.height, Math.sin(a) * r * 0.7));
  }
  const measure = () => {   // how much of the picture the plant covers (screen units: -1…1 = inside the picture)
    const points = edge.map((p) => p.clone().project(camera));
    const ys = points.map((p) => p.y);
    return { side: Math.max(...points.map((p) => Math.abs(p.x))), top: Math.max(...ys), bottom: Math.min(...ys) };
  };
  camera.clearViewOffset();
  let distance = plant.radius, size;
  for (; distance < plant.radius * 8; distance *= 1.02) {   // step back until everything fits
    placeCamera(camera, controls.target, distance, START_VIEW.polar, START_VIEW.azimuth);
    size = measure();
    if (size.side < 0.96 && size.top - size.bottom < 1.84) break;
  }
  // The near side of the plant looks bigger than the far side, so the plant sits low in the picture.
  // Shift the picture (not the camera) to centre it; the turning axis stays in the middle of the plant.
  const height = 1000, width = height * camera.aspect;
  camera.setViewOffset(width, height, 0, (-(size.top + size.bottom) / 2) * (height / 2), width, height);
  controls.minDistance = distance * 0.35;   // closest zoom: about one block fills the view
  controls.maxDistance = distance * 1.4;    // furthest zoom: the plant is still easy to see
  if (keepAngle) placeCamera(camera, controls.target, before.radius * (distance / previousFit), before.phi, before.theta);
  controls.update();
  return distance;
}

/** Starts the "Reset view" glide. Returns a move that stepReset() plays frame by frame. */
export function startReset(camera, controls) {
  controls.enableDamping = false;   // drop any leftover glide from a drag first
  controls.update();
  controls.enableDamping = true;
  const from = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  let turn = (START_VIEW.azimuth - from.theta) % (2 * Math.PI);   // go back the short way round
  if (turn > Math.PI) turn -= 2 * Math.PI;
  if (turn < -Math.PI) turn += 2 * Math.PI;
  return { from, turn, progress: 0 };
}

/** One frame of the reset glide (eases in and out). Returns true when the camera has arrived. */
export function stepReset(move, dt, camera, controls, fitDistance) {
  move.progress = Math.min(1, move.progress + dt / RESET_SECONDS);
  const t = move.progress;
  const k = t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
  const lerp = (a, b) => a + (b - a) * k;
  placeCamera(camera, controls.target, lerp(move.from.radius, fitDistance), lerp(move.from.phi, START_VIEW.polar),
    move.from.theta + move.turn * k);
  return move.progress === 1;
}

/** Where a block's centre appears inside the view, in pixels (used by our automated browser test). */
export function screenPoint(block, plant, camera, view) {
  const p = block.centre.clone().setY(1.5).add(plant.group.position).project(camera);
  return { x: ((p.x + 1) / 2) * view.clientWidth, y: ((1 - p.y) / 2) * view.clientHeight };
}
