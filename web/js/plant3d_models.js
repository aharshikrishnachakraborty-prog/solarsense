// Shapes for the Plant 3D view (Overview page): the ground base, one block of solar panels per inverter,
// an inverter cabinet per block, the control building, the substation and a transmission tower.
// Everything is made in code from boxes, cylinders and planes, so there are no 3D model files to download.
import * as THREE from "three";
import { beams, borderGlowTexture, box, glowTexture, instanced, panelTexture, put, standard } from "./plant3d_shapes.js";

// Same colours as the green / amber / red / grey status badges elsewhere in SolarSense.
export const STATUS_COLORS = { normal: 0x4ade80, warning: 0xfbbf24, critical: 0xef4444, offline: 0x94a3b8 };
const GLOW_OPACITY = { normal: 0.22, warning: 0.5, critical: 0.6, offline: 0.4 };   // faults glow brighter
const AMBER = 0xf59e0b;

// Sizes in scene units (think metres; not to scale).
const PANEL = { width: 1.0, length: 1.6, gap: 0.06, thickness: 0.05 };
const TABLE = { across: 8, tiers: 2, tilt: THREE.MathUtils.degToRad(25), legHeight: 0.45 };
const ROWS_PER_BLOCK = 2;     // two rows (tables) of panels per inverter
const ROW_PITCH = 4.6;        // front-to-front distance between rows, so rows do not shade each other
const GAP = 2.2;              // walkway between blocks
const MARGIN = 4;             // grass around the outside of the plant
const YARD_DEPTH = 12;        // strip behind the panels for the building, substation and tower
const TOWER_HEIGHT = 14;

const tableWidth = TABLE.across * (PANEL.width + PANEL.gap);
const slope = TABLE.tiers * (PANEL.length + PANEL.gap);                 // panel length along the tilt
const tableDepth = slope * Math.cos(TABLE.tilt);
const tableRise = slope * Math.sin(TABLE.tilt);
const blockWidth = tableWidth + 1.6;                                    // + room for the cabinet
const blockDepth = (ROWS_PER_BLOCK - 1) * ROW_PITCH + tableDepth;

/** Panels, legs and rails of every row in every block (three InstancedMeshes for the whole plant). */
function addPanelRows(group, centres) {
  const panels = [], legs = [], rails = [];
  const tilt = new THREE.Matrix4().makeRotationX(TABLE.tilt);   // +25°: panels lean back and face the front (south)
  const centreY = TABLE.legHeight + tableRise / 2 + PANEL.thickness;
  const edge = slope / 2 - 0.3;                                  // where the legs and rails meet the panels
  for (const centre of centres) {
    for (let row = 0; row < ROWS_PER_BLOCK; row++) {
      const x0 = centre.x - 0.8;   // panels sit left, the cabinet right
      const z0 = centre.z - blockDepth / 2 + tableDepth / 2 + row * ROW_PITCH;
      const table = tilt.clone().setPosition(x0, centreY, z0);
      for (let tier = 0; tier < TABLE.tiers; tier++) {
        for (let i = 0; i < TABLE.across; i++) {
          const x = (i - (TABLE.across - 1) / 2) * (PANEL.width + PANEL.gap);
          const z = ((TABLE.tiers - 1) / 2 - tier) * (PANEL.length + PANEL.gap);
          panels.push(table.clone().multiply(new THREE.Matrix4().makeTranslation(x, 0, z)));
        }
      }
      for (const side of [1, -1]) {   // front (low) and back (high) edge of the table
        const y = centreY - side * edge * Math.sin(TABLE.tilt) - PANEL.thickness;
        const z = z0 + side * edge * Math.cos(TABLE.tilt);
        rails.push(table.clone().multiply(new THREE.Matrix4().makeTranslation(0, -PANEL.thickness, side * edge)));
        for (const x of [-3.6, -1.2, 1.2, 3.6]) legs.push(new THREE.Matrix4().compose(
          new THREE.Vector3(x0 + x, y / 2, z), new THREE.Quaternion(), new THREE.Vector3(1, y, 1)));
      }
    }
  }
  const panelGeometry = box(PANEL.width, PANEL.thickness, PANEL.length);
  group.add(instanced(panelGeometry, standard(0xffffff, { map: panelTexture, roughness: 0.35, metalness: 0.25 }), panels));
  group.add(instanced(box(0.08, 1, 0.08), standard(0x94a3b8, { metalness: 0.5 }), legs));
  group.add(instanced(box(tableWidth, 0.06, 0.1), standard(0xe2e8f0, { metalness: 0.4 }), rails));
}

/** Control building, fenced substation with transformers, and a lattice transmission tower with wires. */
function addYard(group, left, right, z) {
  const walls = standard(0xe5e7eb), dark = standard(0x334155), steel = standard(0x9ca3af, { metalness: 0.6 });
  put(group, new THREE.PlaneGeometry(right - left, YARD_DEPTH - 2).rotateX(-Math.PI / 2), standard(0xa8a29e), (left + right) / 2, 0.015, z, false).receiveShadow = true;
  // Control building with a flat roof, windows and a door.
  const bx = left + 6;
  put(group, box(7, 3, 5), walls, bx, 1.5, z);
  put(group, box(7.6, 0.35, 5.6), dark, bx, 3.17, z);
  put(group, box(1.2, 0.6, 1), steel, bx + 2, 3.65, z - 1);        // air-conditioning unit on the roof
  for (const wx of [-2.2, -0.6, 2.2]) put(group, box(1.1, 0.8, 0.05), standard(0x1e3a5f, { roughness: 0.3 }), bx + wx, 1.9, z + 2.52, false);
  put(group, box(1, 1.9, 0.05), dark, bx + 0.9, 0.95, z + 2.52, false);
  // Substation: low fence, two transformers, a gantry the wires arrive at.
  const sx = (left + right) / 2 + 4;
  const fence = standard(0x94a3b8, { transparent: true, opacity: 0.55 });
  for (const [w, d, fx, fz] of [[10, 0.05, 0, -3.5], [10, 0.05, 0, 3.5], [0.05, 7, -5, 0], [0.05, 7, 5, 0]]) put(group, box(w, 1.2, d), fence, sx + fx, 0.6, z + fz, false);
  for (const tx of [-2.2, 1.8]) {
    put(group, box(1.8, 1.7, 1.4), standard(0x475569, { metalness: 0.3 }), sx + tx, 0.85, z + 0.8);
    put(group, new THREE.CylinderGeometry(0.3, 0.3, 1.5, 12).rotateZ(Math.PI / 2), steel, sx + tx, 2, z + 0.8);
    for (const ix of [-0.5, 0, 0.5]) put(group, new THREE.CylinderGeometry(0.07, 0.1, 0.8, 8), standard(0xd6d3d1), sx + tx + ix, 2.1, z + 0.2);
  }
  const gantryTop = 4.5;
  for (const gx of [-3.5, 3.5]) put(group, box(0.25, gantryTop, 0.25), steel, sx + gx, gantryTop / 2, z - 2);
  put(group, box(7.4, 0.25, 0.25), steel, sx, gantryTop, z - 2);
  // Transmission tower: four tapered legs with rings and cross bracing, three cross-arms.
  const tx = right - 3, tz = z - 1;
  const corner = (level, sx2, sz2) => { const half = 1.8 - 1.35 * level; return new THREE.Vector3(tx + sx2 * half, level * TOWER_HEIGHT, tz + sz2 * half); };
  const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  const pairs = [];
  const levels = [0, 0.18, 0.36, 0.54, 0.7, 0.85, 1];
  for (let k = 0; k < levels.length - 1; k++) {
    corners.forEach(([ax, az], c) => {
      const [bx2, bz2] = corners[(c + 1) % 4];
      pairs.push([corner(levels[k], ax, az), corner(levels[k + 1], ax, az)]);       // leg
      pairs.push([corner(levels[k + 1], ax, az), corner(levels[k + 1], bx2, bz2)]);  // ring
      pairs.push([corner(levels[k], ax, az), corner(levels[k + 1], bx2, bz2)]);      // brace
    });
  }
  const arms = [0.62, 0.78, 0.94].map((level, i) => ({ y: level * TOWER_HEIGHT, reach: 3 - i * 0.6 }));
  for (const arm of arms) pairs.push([new THREE.Vector3(tx - arm.reach, arm.y, tz), new THREE.Vector3(tx + arm.reach, arm.y, tz)]);
  group.add(beams(pairs, 0.12, steel));
  // Wires: from the gantry up to the tower arms, and from the tower away to the grid (sagging curves).
  const wire = new THREE.LineBasicMaterial({ color: 0x64748b });
  const sag = (a, b, drop) => new THREE.QuadraticBezierCurve3(a, a.clone().lerp(b, 0.5).setY(Math.min(a.y, b.y) - drop), b).getPoints(16);
  arms.forEach((arm, i) => {
    const end = new THREE.Vector3(tx - arm.reach, arm.y, tz);
    const gantryPoint = new THREE.Vector3(sx - 2.5 + i * 2.5, gantryTop, z - 2);
    const away = new THREE.Vector3(tx + arm.reach + 14, arm.y - 3, tz - 10);
    for (const points of [sag(gantryPoint, end, 0.8), sag(new THREE.Vector3(tx + arm.reach, arm.y, tz), away, 1.5)]) {
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), wire));
    }
  });
}

/** Builds the whole plant for a list of inverter ids. Returns the group plus one entry per block. */
export function buildPlant(ids) {
  const group = new THREE.Group();
  const columns = Math.max(1, Math.ceil(Math.sqrt(ids.length * 1.6)));   // wider than deep, like a real plant
  const rows = Math.ceil(ids.length / columns);
  const gridW = columns * blockWidth + (columns - 1) * GAP;
  const gridD = rows * blockDepth + (rows - 1) * GAP;
  const centres = ids.map((_, i) => {
    const row = Math.floor(i / columns);
    const inRow = Math.min(columns, ids.length - row * columns);           // last row is centred
    return new THREE.Vector3((i % columns - (inRow - 1) / 2) * (blockWidth + GAP), 0, (row - (rows - 1) / 2) * (blockDepth + GAP));
  });

  // Ground: grass slab, gravel under the panels, glowing amber border (like a model on a display stand).
  const baseW = gridW + 2 * MARGIN, baseD = gridD + GAP + YARD_DEPTH + 2 * MARGIN;
  const baseZ = -(GAP + YARD_DEPTH) / 2;
  put(group, box(baseW, 0.8, baseD), standard(0x4b6b45), 0, -0.4, baseZ, false).receiveShadow = true;
  put(group, new THREE.PlaneGeometry(gridW + 2, gridD + 2).rotateX(-Math.PI / 2), standard(0x7c8574), 0, 0.01, 0, false).receiveShadow = true;
  const halo = 3;
  put(group, new THREE.PlaneGeometry(baseW + 2 * halo, baseD + 2 * halo).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({
    map: borderGlowTexture(baseW + 2 * halo, baseD + 2 * halo, halo), transparent: true, depthWrite: false,
    blending: THREE.AdditiveBlending, toneMapped: false }), 0, 0.03, baseZ, false);
  const edge = new THREE.MeshBasicMaterial({ color: AMBER, toneMapped: false });
  for (const [w, d, x, z] of [[baseW + 0.18, 0.18, 0, -baseD / 2], [baseW + 0.18, 0.18, 0, baseD / 2],
    [0.18, baseD, -baseW / 2, 0], [0.18, baseD, baseW / 2, 0]]) put(group, box(w, 0.18, d), edge, x, 0.02, baseZ + z, false);

  addPanelRows(group, centres);
  addYard(group, -gridW / 2, gridW / 2, -gridD / 2 - GAP - YARD_DEPTH / 2);

  // Per-status materials, shared by all blocks with that status.
  const materials = { cabinet: {}, glow: {} };
  for (const [status, color] of Object.entries(STATUS_COLORS)) {
    materials.cabinet[status] = standard(color, { emissive: color, emissiveIntensity: 0.35, roughness: 0.5 });
    materials.glow[status] = new THREE.MeshBasicMaterial({ color, map: glowTexture, transparent: true, opacity: GLOW_OPACITY[status], depthWrite: false, toneMapped: false });
  }
  const markerMaterial = standard(STATUS_COLORS.critical, { emissive: STATUS_COLORS.critical, emissiveIntensity: 0.8 });
  const glowGeometry = new THREE.PlaneGeometry(blockWidth + 2, blockDepth + 2).rotateX(-Math.PI / 2);
  const hitGeometry = box(blockWidth + GAP * 0.8, 3, blockDepth + GAP * 0.8);
  const hidden = new THREE.MeshBasicMaterial({ visible: false });   // invisible, but the mouse can still "hit" it
  const plinth = box(1.3, 0.12, 1.1), plinthMaterial = standard(0xd6d3d1), cabinetGeometry = box(0.9, 1.5, 0.8);
  const markerShape = new THREE.Group();                            // red "look here" pin: a ball on a cone
  put(markerShape, new THREE.ConeGeometry(0.5, 1.1, 16).rotateX(Math.PI), markerMaterial, 0, 0, 0);
  put(markerShape, new THREE.SphereGeometry(0.42, 16, 12), markerMaterial, 0, 0.9, 0);
  const blocks = ids.map((id, i) => {
    const { x, z } = centres[i];
    const cx = x + blockWidth / 2 - 0.7;
    put(group, plinth, plinthMaterial, cx, 0.06, z);                                       // concrete plinth
    const cabinet = put(group, cabinetGeometry, materials.cabinet.normal, cx, 0.87, z);
    const glow = put(group, glowGeometry, materials.glow.normal, x, 0.02 + i * 0.0005, z, false);
    const hit = put(group, hitGeometry, hidden, x, 1.5, z, false);
    hit.userData.id = id;
    const marker = markerShape.clone();
    marker.position.set(x - 0.8, 4.2, z);
    marker.visible = false;
    group.add(marker);
    return { id, centre: centres[i], cabinet, glow, hit, marker, status: "normal" };
  });
  const outline = new THREE.LineSegments(new THREE.EdgesGeometry(box(blockWidth + 0.6, 2.6, blockDepth + 0.6)),
    new THREE.LineBasicMaterial({ color: AMBER, toneMapped: false }));
  outline.visible = false;
  group.add(outline);

  group.position.z = -baseZ;   // centre the base on the turntable axis
  return { group, ids, blocks, materials, markerMaterial, outline, radius: Math.hypot(baseW, baseD) / 2 + 1, height: TOWER_HEIGHT };
}

/** Colours one block's cabinet and glow by status; only critical blocks show the red marker. */
export function paintBlock(plant, block, status) {
  block.status = status;
  block.cabinet.material = plant.materials.cabinet[status];
  block.glow.material = plant.materials.glow[status];
  block.marker.visible = status === "critical";
}

/** Frees GPU memory of a plant we no longer show (the shared panel and glow textures are kept). */
export function disposePlant(plant) {
  const keep = new Set([panelTexture, glowTexture]);
  plant.group.traverse((object) => {
    if (object.isInstancedMesh) object.dispose();
    if (object.geometry) object.geometry.dispose();
    for (const material of [].concat(object.material || [])) {
      if (material.map && !keep.has(material.map)) material.map.dispose();
      material.dispose();
    }
  });
  for (const material of [...Object.values(plant.materials.cabinet), ...Object.values(plant.materials.glow)]) material.dispose();
}
