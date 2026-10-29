// Small building blocks for the Plant 3D view: textures drawn on a canvas (solar cells, soft glow,
// glowing border) and helpers that place one box, many copies of a shape, or thin steel beams.
// Used by plant3d_models.js.
import * as THREE from "three";

/** A canvas drawn once and used as a texture (panel cells, soft glow). */
export function canvasTexture(width, height, draw) {
  const canvas = Object.assign(document.createElement("canvas"), { width, height });
  draw(canvas.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

// One solar module: dark blue cells, thin light grid lines, light frame.
export const panelTexture = canvasTexture(128, 204, (ctx, w, h) => {
  ctx.fillStyle = "#cbd5e1";                                            // light aluminium frame
  ctx.fillRect(0, 0, w, h);
  const cells = ctx.createLinearGradient(0, 0, w, h);
  [[0, "#1e3a8a"], [1, "#0f2557"]].forEach(([at, color]) => cells.addColorStop(at, color));
  ctx.fillStyle = cells;                                                // dark blue silicon cells
  ctx.fillRect(6, 6, w - 12, h - 12);
  Object.assign(ctx, { strokeStyle: "rgba(147, 197, 253, 0.45)", lineWidth: 1.5 });   // lines between the cells
  for (let i = 1; i < 6; i++) { const x = 6 + (i * (w - 12)) / 6; ctx.beginPath(); ctx.moveTo(x, 6); ctx.lineTo(x, h - 6); ctx.stroke(); }
  for (let i = 1; i < 10; i++) { const y = 6 + (i * (h - 12)) / 10; ctx.beginPath(); ctx.moveTo(6, y); ctx.lineTo(w - 6, y); ctx.stroke(); }
});

// White in the middle fading to clear at the edges; tinted by the status colour.
export const glowTexture = canvasTexture(128, 128, (ctx, w, h) => {
  const gradient = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
  [[0, 1], [0.6, 0.55], [1, 0]].forEach(([at, alpha]) => gradient.addColorStop(at, `rgba(255,255,255,${alpha})`));
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, w, h);
});

/** A glowing amber outline drawn on a canvas, sized to sit exactly on the edge of the base. */
export function borderGlowTexture(planeW, planeD, inset) {
  const width = 512, height = Math.round((512 * planeD) / planeW);
  return canvasTexture(width, height, (ctx) => {
    const px = (width * inset) / planeW;
    Object.assign(ctx, { strokeStyle: "rgba(245, 158, 11, 0.9)", shadowColor: "rgb(245, 158, 11)", lineWidth: 3 });
    for (const blur of [28, 14, 6]) { ctx.shadowBlur = blur; ctx.strokeRect(px, px, width - 2 * px, height - 2 * px); }
  });
}

export const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
export const standard = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, ...extra });

/** Adds a mesh to a parent at (x, y, z) and returns it. */
export function put(parent, geometry, material, x, y, z, shadows = true) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(x, y, z);
  mesh.castShadow = mesh.receiveShadow = shadows;
  parent.add(mesh);
  return mesh;
}

/** Many copies of one shape in a single draw call (fast): one matrix per copy. */
export function instanced(geometry, material, matrices) {
  const mesh = new THREE.InstancedMesh(geometry, material, matrices.length);
  matrices.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
  mesh.castShadow = mesh.receiveShadow = true;
  return mesh;
}

/** Thin beams between pairs of points, e.g. the steel lattice of the transmission tower. */
export function beams(pairs, thickness, material) {
  const up = new THREE.Vector3(0, 1, 0);
  return instanced(box(thickness, 1, thickness), material, pairs.map(([a, b]) => {
    const direction = b.clone().sub(a);
    const turn = new THREE.Quaternion().setFromUnitVectors(up, direction.clone().normalize());
    return new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5), turn, new THREE.Vector3(1, direction.length(), 1));
  }));
}
