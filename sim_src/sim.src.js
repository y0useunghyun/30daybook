// 시뮬레이션: 처음 책을 읽은 강의실 + 문 뒤의 4호선 객차. 빛은 Blender에서 미리 구움(lightmap), 움직여도 안 변함
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Reflector } from 'three/addons/objects/Reflector.js';

const BASE = new URL('.', import.meta.url).href;
const EYE = 1.5, RADIUS = .2, WALK_SPEED = 1.5, TURN_PER_PX = .0032, WHEEL_STEP = .0025, TAP_SLOP_PX = 6;
const PITCH_MAX = 1.35;
const SPAWN = { x: 2.15, y: .95, yaw: 62 * Math.PI / 180, pitch: -.1 }; // 8번 사진 자리
const BOUNDS_Y0 = -2.85, MY_ROOM_Y0 = -7.05; // 객차 남쪽 끝, 내 방 창가
const SOUTH_AISLE_Y = .95, EAST_AISLE_X = 6.6;                          // 책상 줄을 건널 수 있는 통로
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

// 맨 앞줄 접이식 책상 중 가운데. 책상을 바꾸려면 x·y만 고치면 됨
const PILE = { x: 7.75, y: 4.6, z: .792, spread: .3, gap: .0014, sheetW: .2, reach: 2.4 };
const DOOR_OPEN_RAD = -95 * Math.PI / 180, DOOR_MS = 900, LEAF_SLIDE = .66, DOOR_REACH = 1.7, DOOR_STAND = .72;
const GANGWAY = { cols: 5, rowZ: [1.68, 1.36, 1.04], sheetW: .178, off: .03, reach: 1.5, color: 0xdedcd4 };
const MY_DOOR = { id: 'C', x0: 8.2, x1: 9.15, south: true, wallY: -3.05, stand: -2.3, leafX: 1.28 };
const VIEW = { width: 24, dist: 12, zc: 1.5, aspect: 580 / 900 };
const SWITCH = { reach: 1.7, tilt: .32, stand: .85, dimUnlit: .4, dimLed: 0x77797a, dimEnv: .25 };
const DESK_SHEET_W = .19, DESK_REACH = 1.5, DESK_STAND = { x: 9.05, y: -5.88 };
const LCD_MS = 6000, SETTLE_MS = 1500;
const STATIONS = '진접 오남 별내별가람 당고개 상계 노원 창동 쌍문 수유 미아 미아사거리 길음 성신여대입구 한성대입구 혜화 동대문 동대문역사문화공원 충무로 명동 회현 서울역 숙대입구 삼각지 신용산 이촌 동작 총신대입구 사당 남태령 선바위 경마공원 대공원 과천 정부과천청사 인덕원 평촌 범계 금정 산본 수리산 대야미 반월 상록수 한대앞 중앙 고잔 초지 안산 신길온천 정왕 오이도'.split(' ');

// Blender 좌표(x 동, y 북, z 위) → three (x, z, -y)
const toThree = (x, y, z) => new THREE.Vector3(x, z, -y);

let ui = null; // 한 번 지으면 재사용

// 통신이 잠깐 끊겨도 공간이 안 열리는 일이 없게 몇 번 다시 받음
const RETRIES = 3, RETRY_MS = 500;
async function retry(load) {
  for (let i = 0; ; i++) {
    try { return await load(); } catch (err) {
      if (i >= RETRIES) throw err;
      await new Promise(r => setTimeout(r, RETRY_MS * (i + 1)));
    }
  }
}
// 나중에 채워지는 질감도 실패하면 다시 받음
function loadTexture(loader, url, tries = RETRIES) {
  const tex = new THREE.Texture();
  const attempt = left => loader.load(url, t => { tex.image = t.image; tex.needsUpdate = true; }, undefined,
    () => { if (left > 0) setTimeout(() => attempt(left - 1), RETRY_MS); });
  attempt(tries);
  return tex;
}

function collide(p, rects) {
  let { x, y } = p;
  for (const [x0, y0, x1, y1] of rects) {
    const nx = Math.max(x0, Math.min(x, x1)), ny = Math.max(y0, Math.min(y, y1));
    const dx = x - nx, dy = y - ny, d = Math.hypot(dx, dy);
    if (d >= RADIUS) continue;
    if (d > 1e-5) { x = nx + dx / d * RADIUS; y = ny + dy / d * RADIUS; }
    else { // 안에 들어옴: 가까운 변으로
      const e = [[x - x0, -1, 0], [x1 - x, 1, 0], [y - y0, 0, -1], [y1 - y, 0, 1]].sort((a, b) => a[0] - b[0])[0];
      x += e[1] * (e[0] + RADIUS); y += e[2] * (e[0] + RADIUS);
    }
  }
  return { x, y };
}

// 한 공간 불러오기: glb + lightmap + env + 재질. dir 예: '' 또는 'subway/'
async function loadPart(dir, renderer, loader, extra = () => null) {
  const url = `${BASE}${dir}`;
  const [meta, gltf, lightMap, envRaw] = await Promise.all([
    retry(() => fetch(`${url}scene.json`).then(r => { if (!r.ok) throw new Error(`${dir}scene.json ${r.status}`); return r.json(); })),
    retry(() => new GLTFLoader().loadAsync(`${url}room.glb`)),
    retry(() => loader.loadAsync(`${url}lightmap.webp`)),
    retry(() => loader.loadAsync(`${url}env.jpg`)),
  ]);
  lightMap.colorSpace = THREE.SRGBColorSpace; lightMap.flipY = false; lightMap.channel = 1;
  lightMap.generateMipmaps = false; lightMap.minFilter = lightMap.magFilter = THREE.LinearFilter;
  envRaw.colorSpace = THREE.SRGBColorSpace; envRaw.mapping = THREE.EquirectangularReflectionMapping;
  const pm = new THREE.PMREMGenerator(renderer); const env = pm.fromEquirectangular(envRaw).texture; pm.dispose();
  const anisotropy = renderer.capabilities.getMaxAnisotropy();
  const tex = name => {
    const t = loadTexture(loader, `${url}tex/${name}.jpg`);
    t.colorSpace = THREE.SRGBColorSpace; t.flipY = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = anisotropy;
    return t;
  };
  const cache = {};
  const material = name => {
    if (cache[name]) return cache[name];
    const special = extra(name, tex, envRaw);
    if (special) return cache[name] = special;
    const d = meta.materials[name] || {};
    const map = d.map ? tex(d.map) : null;
    const color = d.map ? (d.tint || 0xffffff) : (d.color || '#ffffff');
    const lit = meta.lightmapScale * (d.gain ?? 1);
    let m;
    if (d.emit || d.unlit) { // 빛 계산 안 함: 형광등·블라인드·문짝·작은 종이
      m = new THREE.MeshBasicMaterial({ map, color });
      if (d.opacity) { m.transparent = true; m.opacity = d.opacity; m.depthWrite = false; m.side = THREE.DoubleSide; }
    }
    else if ((d.rough ?? .6) >= .7 && !d.metal) m = new THREE.MeshBasicMaterial({ map, color, lightMap, lightMapIntensity: lit });
    else m = new THREE.MeshStandardMaterial({
      map, color, roughness: d.rough ?? .6, metalness: d.metal ?? 0,
      lightMap, lightMapIntensity: lit * Math.PI, envMap: env, envMapIntensity: d.metal ? 1 : .35,
    });
    return cache[name] = m;
  };
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    const name = o.material.name;
    o.material = material(name); o.userData.mat = name;
    o.matrixAutoUpdate = false; o.frustumCulled = false;
  });
  // 불 켜기/끄기: 구운 빛 지도를 바꿔 끼움. 스스로 빛나는 것(블라인드·비상구)은 그대로
  const lightMapOff = meta.lightmapOff ? await retry(() => loader.loadAsync(`${url}lightmap_off.webp`)) : null;
  if (lightMapOff) { lightMapOff.colorSpace = THREE.SRGBColorSpace; lightMapOff.flipY = false; lightMapOff.channel = 1; lightMapOff.generateMipmaps = false; lightMapOff.minFilter = lightMapOff.magFilter = THREE.LinearFilter; }
  const setLights = on => {
    for (const [name, m] of Object.entries(cache)) {
      const d = meta.materials[name] || {};
      if (m.lightMap) m.lightMap = on ? lightMap : lightMapOff;
      if (m.envMap) m.envMapIntensity = (d.metal ? 1 : .35) * (on ? 1 : SWITCH.dimEnv);
      if (name === 'led') m.color.set(on ? 0xffffff : SWITCH.dimLed);
      else if (d.unlit && !d.emit) m.color.set(d.color || 0xffffff).multiplyScalar(on ? 1 : SWITCH.dimUnlit);
    }
  };
  return { meta, root: gltf.scene, setLights };
}

// 책상 위 30장. 누르면 위에서 한 장 집어 옆 더미로. 다 넘기면 방향만 바뀜
function makePile(scene, loader, sizes) {
  const maxW = Math.max(...sizes.map(s => s[0]));
  const maps = sizes.map((_, i) => {
    const map = loadTexture(loader, `${BASE}../pages/small/front${String(i + 1).padStart(2, '0')}.jpg`);
    map.colorSpace = THREE.SRGBColorSpace; map.anisotropy = 4;
    return map;
  });
  const sheets = sizes.map(([w, h], i) => {
    const map = maps[i];
    const sw = PILE.sheetW * w / maxW;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(sw, sw * h / w).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map, color: 0xf2f0e8 }));
    scene.add(mesh);
    return { mesh, day: i, tilt: (Math.random() - .5) * .3, dx: (Math.random() - .5) * .022, dy: (Math.random() - .5) * .022 };
  });
  const stacks = [[...sheets].reverse(), []]; // 배열 끝이 맨 위. 처음엔 1일차가 위
  let source = 0;
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 64;
  const g = canvas.getContext('2d'), grad = g.createRadialGradient(32, 32, 14, 32, 32, 32);
  grad.addColorStop(0, 'rgba(0,0,0,.3)'); grad.addColorStop(.6, 'rgba(0,0,0,.2)'); grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  const shadowMat = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false });
  const stackY = k => PILE.y + (k ? -PILE.spread : PILE.spread);
  const shadows = [0, 1].map(k => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(.235, .29).rotateX(-Math.PI / 2), shadowMat);
    m.position.copy(toThree(PILE.x + .004, stackY(k) - .004, PILE.z - .0006));
    scene.add(m); return m;
  });
  const layout = () => stacks.forEach((stack, k) => {
    shadows[k].visible = stack.length > 0;
    stack.forEach((s, j) => {
      s.mesh.position.copy(toThree(PILE.x + s.dx, stackY(k) + s.dy, PILE.z + (j + 1) * PILE.gap));
      s.mesh.rotation.y = -Math.PI / 2 + s.tilt; // 책상 서쪽에 선 사람이 바로 읽는 방향
    });
  });
  layout();
  const proxy = new THREE.Mesh(new THREE.BoxGeometry(.5, .08, .9));
  proxy.position.copy(toThree(PILE.x, PILE.y, PILE.z + .02)); proxy.visible = false; scene.add(proxy);
  return {
    proxy, maps,
    setLights(on) { sheets.forEach(s => s.mesh.material.color.set(0xf2f0e8).multiplyScalar(on ? 1 : SWITCH.dimUnlit)); },
    take() {
      if (!stacks[source].length) source = 1 - source;
      const sheet = stacks[source].pop();
      stacks[1 - source].push(sheet); layout();
      return sheet.day;
    },
  };
}

// 연결 통로: 양쪽 벽 눈높이에 30장을 붙임 (서서 읽는 자리). 1일차는 북쪽 벽 왼쪽 위부터
function makeGangwayPapers(scene, gw, maps, sizes) {
  const maxW = Math.max(...sizes.map(s => s[0]));
  const stepX = (gw.x1 - gw.x0 - .12) / GANGWAY.cols;
  const tape = new THREE.MeshBasicMaterial({ color: 0xe9e3c6 });
  const tapeGeo = new THREE.PlaneGeometry(.05, .016);
  const group = new THREE.Group(); group.visible = false; scene.add(group);
  const papers = sizes.map(([w, h], i) => {
    const perWall = GANGWAY.cols * GANGWAY.rowZ.length;
    const north = i < perWall, j = i % perWall;
    const col = j % GANGWAY.cols, row = Math.floor(j / GANGWAY.cols);
    const sw = GANGWAY.sheetW * w / maxW;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(sw, sw * h / w), new THREE.MeshBasicMaterial({ map: maps[i], color: GANGWAY.color }));
    // 객차에서 들어가며 볼 때 왼쪽→오른쪽 순서가 되게: 북쪽 벽은 x 증가, 남쪽 벽은 x 감소
    const x = north ? gw.x0 + .06 + stepX * (col + .5) : gw.x1 - .06 - stepX * (col + .5);
    const y = gw.yc + (north ? 1 : -1) * (gw.halfW - GANGWAY.off);
    mesh.position.copy(toThree(x, y, GANGWAY.rowZ[row] + (Math.random() - .5) * .018));
    mesh.rotation.set(0, north ? 0 : Math.PI, (Math.random() - .5) * .07);
    mesh.userData.day = i;
    const t = new THREE.Mesh(tapeGeo, tape); t.position.set(0, sw * h / w / 2, .001); t.rotation.z = (Math.random() - .5) * .3; mesh.add(t);
    group.add(mesh);
    return mesh;
  });
  return { group, papers };
}

// 똑딱이 스위치: 판은 굽힌 모델, 레버·글자는 여기서. x·z는 Blender 좌표, 남쪽 벽에 붙음
function makeSwitches(scene, list) {
  const label = text => {
    const c = document.createElement('canvas'); c.width = 128; c.height = 40;
    const g = c.getContext('2d'); g.fillStyle = '#e9e9e4'; g.fillRect(0, 0, 128, 40);
    g.font = '500 26px SUIT, sans-serif'; g.fillStyle = '#222'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 64, 22);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    return new THREE.MeshBasicMaterial({ map: t });
  };
  const leverMat = new THREE.MeshBasicMaterial({ color: 0xf4f4f0 });
  const baseMat = new THREE.MeshBasicMaterial({ color: 0xb6b6b0 });
  const labels = { light: label('전등'), ac: label('에어컨') };
  return list.map(sw => {
    const pos = toThree(sw.x, .012, sw.z);
    const base = new THREE.Mesh(new THREE.BoxGeometry(.034, .05, .004), baseMat); base.position.copy(pos); scene.add(base);
    const pivot = new THREE.Group(); pivot.position.copy(pos); scene.add(pivot);
    // 벽에서 방 쪽(three -z)으로 튀어나온 레버
    const lever = new THREE.Mesh(new THREE.BoxGeometry(.016, .012, .032), leverMat); lever.position.z = -.016; pivot.add(lever);
    const tag = new THREE.Mesh(new THREE.PlaneGeometry(.08, .025), labels[sw.kind]); tag.position.copy(toThree(sw.x, .0125, sw.z + .1)); tag.rotation.y = Math.PI; scene.add(tag);
    const proxy = new THREE.Mesh(new THREE.BoxGeometry(.14, .22, .1)); proxy.position.copy(pos); proxy.visible = false; scene.add(proxy);
    const set = up => { pivot.rotation.x = up ? -SWITCH.tilt : SWITCH.tilt; };
    return { ...sw, proxy, set };
  });
}

// 방 책상 위 30장: 누르면 맨 위를 크게 보고 맨 아래로 넣음
function makeDeskPile(group, desk, maps, sizes) {
  const maxW = Math.max(...sizes.map(s => s[0]));
  const order = sizes.map((_, i) => i);
  const meshes = sizes.map(([w, h], i) => {
    const sw = DESK_SHEET_W * w / maxW;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(sw, sw * h / w).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: maps[i], color: 0xf2f0e8 }));
    m.rotation.y = -Math.PI / 2 + (Math.random() - .5) * .3;
    m.userData.dx = (Math.random() - .5) * .018; m.userData.dy = (Math.random() - .5) * .018;
    group.add(m);
    return m;
  });
  const layout = () => order.forEach((day, j) => {
    const m = meshes[day], up = order.length - j;
    m.position.copy(toThree(desk.x + m.userData.dx, desk.y + m.userData.dy, desk.z + up * PILE.gap));
  });
  layout();
  const proxy = new THREE.Mesh(new THREE.BoxGeometry(.3, .07, .34)); proxy.position.copy(toThree(desk.x, desk.y, desk.z + .02)); proxy.visible = false; group.add(proxy);
  return { proxy, take() { const day = order.shift(); order.push(day); layout(); return day; } };
}

function makeLcd() {
  const canvas = document.createElement('canvas'); canvas.width = 840; canvas.height = 64;
  const g = canvas.getContext('2d');
  const map = new THREE.CanvasTexture(canvas); map.colorSpace = THREE.SRGBColorSpace; map.flipY = false;
  let i = 14; // 혜화부터
  const draw = () => {
    g.fillStyle = '#0b0a08'; g.fillRect(0, 0, 840, 64);
    g.font = '500 36px SUIT, sans-serif'; g.fillStyle = '#ff9d2e'; g.textBaseline = 'middle';
    g.fillText(`오이도 행   이번 역은 ${STATIONS[i]}`, 18, 34);
    map.needsUpdate = true;
  };
  draw();
  return { map, next() { i = (i + 1) % STATIONS.length; draw(); } };
}

// 바닥 위에 살짝 얹는 반사층 (광택 콘크리트). 흐리게 + 낮은 각도일수록 진하게
const REFLECT_SHADER = {
  name: 'FloorGloss',
  uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null } },
  vertexShader: `uniform mat4 textureMatrix; varying vec4 vUv; varying vec3 vP;
    void main(){ vUv = textureMatrix * vec4(position,1.); vec4 w = modelMatrix * vec4(position,1.); vP = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
  fragmentShader: `uniform sampler2D tDiffuse; varying vec4 vUv; varying vec3 vP;
    void main(){
      vec2 uv = vUv.xy / vUv.w; vec3 s = vec3(0.);
      for (int i = 0; i < 16; i++) { float a = float(i) * 2.399; float r = sqrt(float(i) / 16.) * .012;
        s += texture2D(tDiffuse, uv + vec2(cos(a), sin(a) * 1.8) * r).rgb; }
      s /= 16.;
      vec3 v = normalize(cameraPosition - vP);
      gl_FragColor = vec4(s, .05 + .5 * pow(1. - max(v.y, 0.), 4.));
      #include <colorspace_fragment>
    }`,
};

async function build(root, opts) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  const touch = matchMedia('(pointer: coarse)').matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, touch ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#dfe6ea');
  const camera = new THREE.PerspectiveCamera(58, 1, .08, 120);
  const loader = new THREE.TextureLoader();

  const room = await loadPart('', renderer, loader);
  root.append(renderer.domElement);
  scene.add(room.root);
  const [W, D] = room.meta.size;

  const pile = makePile(scene, loader, opts.sheets);

  let refl = null;
  if (!touch) { // 바닥 반사 (폰은 생략)
    refl = new Reflector(new THREE.PlaneGeometry(W, D), { textureWidth: 1024, textureHeight: 1024, clipBias: .001, shader: REFLECT_SHADER, multisample: 0 });
    refl.material.transparent = true; refl.material.depthWrite = false;
    refl.rotation.x = -Math.PI / 2; refl.position.copy(toThree(W / 2, D / 2, .002));
    scene.add(refl);
  }

  const switches = makeSwitches(scene, room.meta.switches);
  const sim = { lights: true, ac: true };
  const syncSwitches = () => switches.forEach(sw => sw.set(sw.kind === 'ac' ? sim.ac : sim.lights));
  syncSwitches();
  const setLights = on => {
    lastView = ''; sim.lights = on; room.setLights(on); pile.setLights(on); syncSwitches();
    const b = root.querySelector('.sim-light'); if (b) b.textContent = on ? '강의실 불 끄기' : '강의실 불 켜기';
  };
  const flip = sw => { if (sw.kind === 'ac') { lastView = ''; sim.ac = !sim.ac; syncSwitches(); } else setLights(!sim.lights); };

  // ── 문: 교실 문짝(경첩으로 돎)과 객차 문짝(옆으로 밀림)을 한 쌍으로
  const doors = room.meta.doors.map(d => {
    const hinge = toThree(d.x1, 0, 0), pivot = new THREE.Group(); pivot.position.copy(hinge); scene.add(pivot);
    const parts = [];
    room.root.traverse(o => { if (o.isMesh && [`door${d.id}`, `handle${d.id}`, `doorglass${d.id}`].includes(o.userData.mat)) parts.push(o); });
    parts.forEach(o => { o.matrixAutoUpdate = true; o.position.copy(hinge).negate(); pivot.add(o); }); // traverse 중에 옮기면 안 됨
    const proxy = new THREE.Mesh(new THREE.BoxGeometry(d.x1 - d.x0, 2.25, .4));
    proxy.position.copy(toThree((d.x0 + d.x1) / 2, -.15, 1.12)); proxy.visible = false; scene.add(proxy);
    return { ...d, mid: (d.x0 + d.x1) / 2, pivot, proxy, leaves: [], open: false, t: 0 };
  });
  { // 객차 반대편 문 → 내 방. 경첩 없이 객차 문만 밀림
    const proxy = new THREE.Mesh(new THREE.BoxGeometry(MY_DOOR.leafX, 2, .2)); proxy.position.copy(toThree((MY_DOOR.x0 + MY_DOOR.x1) / 2, MY_DOOR.wallY, 1)); proxy.visible = false; scene.add(proxy);
    // 어느 문인지 바로 보이게 「집」 표시 (열리면 사라짐)
    const c = document.createElement('canvas'); c.width = 256; c.height = 128;
    const g = c.getContext('2d'); g.fillStyle = '#f6f5f0'; g.fillRect(0, 0, 256, 128);
    g.font = '500 76px SUIT, sans-serif'; g.fillStyle = '#111'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('집', 128, 70);
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(.3, .15), new THREE.MeshBasicMaterial({ map: tex }));
    sign.position.copy(toThree((MY_DOOR.x0 + MY_DOOR.x1) / 2, MY_DOOR.wallY - .012, 1.72)); sign.rotation.y = Math.PI; sign.visible = false; scene.add(sign);
    doors.push({ ...MY_DOOR, mid: (MY_DOOR.x0 + MY_DOOR.x1) / 2, proxy, sign, leaves: [], open: false, t: 0 });
  }
  let subway = null, train = null, trainColliders = [], gangway = null, myColliders = [], myRoom = null, carClones = [], deskPile = null;
  // 내 방: 객차가 온 뒤 이어서 불러옴
  const myRoomReady = () => myRoomLoad ??= loadPart('myroom/', renderer, loader).then(part => {
    myRoom = new THREE.Group(); myRoom.visible = false; myRoom.add(part.root); scene.add(myRoom);
    part.root.traverse(o => { if (o.userData.mat === 'plug') o.visible = false; });
    myColliders = part.meta.colliders; rebuildColliders();
    const [wx0, wx1, wy] = part.meta.window;
    const map = loadTexture(loader, `${BASE}myroom/tex/view.jpg`); map.colorSpace = THREE.SRGBColorSpace;
    const view = new THREE.Mesh(new THREE.PlaneGeometry(VIEW.width, VIEW.width * VIEW.aspect), new THREE.MeshBasicMaterial({ map }));
    view.position.copy(toThree((wx0 + wx1) / 2, wy - VIEW.dist, VIEW.zc)); view.rotation.y = Math.PI; myRoom.add(view); // 앞면이 방을 보게
    deskPile = makeDeskPile(myRoom, part.meta.desk, pile.maps, opts.sheets);
    return part;
  });
  let myRoomLoad = null;
  const bounds = { x0: .2, x1: W - .2 };
  const lcd = makeLcd();
  const subwayReady = loadPart('subway/', renderer, loader, name => {
    if (name === 'lcd') return new THREE.MeshBasicMaterial({ map: lcd.map });
    return null;
  }).then(part => {
    subway = part;
    const P = part.meta.carPitch;
    // 앞뒤 칸은 같은 칸을 복제 (구운 빛·파일 재사용). 끝 막음 그림은 맨 끝 칸에서만
    const back = part.root.clone(true), front = part.root.clone(true);
    back.position.x = -P; front.position.x = P;
    const showEnds = (r, gang, gangW) => r.traverse(o => {
      if (o.userData.mat === 'gang') o.visible = gang;
      if (o.userData.mat === 'gangW') o.visible = gangW;
    });
    showEnds(part.root, false, false); showEnds(back, false, true); showEnds(front, true, false);
    train = new THREE.Group(); train.visible = false; train.add(part.root, back, front); scene.add(train);
    carClones = [back, front];
    part.root.traverse(o => {
      const m = o.userData.mat?.match(/^(?:leaf|glass)([ABC])([LR])$/);
      if (!m) return;
      o.matrixAutoUpdate = true;
      doors.find(d => d.id === m[1]).leaves.push({ mesh: o, dir: m[2] === 'L' ? -1 : 1 });
    });
    gangway = { ...part.meta.gangway, ...makeGangwayPapers(scene, part.meta.gangway, pile.maps, opts.sheets) };
    const shift = (c, dx) => [c[0] + dx, c[1], c[2] + dx, c[3]];
    const { carX0, carYN: yn, carYS: ys } = part.meta;
    const sd = part.meta.southDoor;
    const noHoles = dx => [...room.meta.doors.map(d => [d.x0 + dx, yn, d.x1 + dx, yn + .05]), [sd.x0 + dx, ys - .3, sd.x1 + dx, ys]]; // 앞뒤 칸 문은 안 열림
    const walkLimit = { x0: carX0 - P + RADIUS, x1: part.meta.gangway.x1 + P - RADIUS };
    trainColliders = [
      ...part.meta.colliders,
      ...[-P, P].flatMap(dx => [...part.meta.colliders.map(c => shift(c, dx)), ...noHoles(dx)]),
      [carX0 - P - 1, ys - 1, carX0 - P, yn + 1], [part.meta.gangway.x1 + P, ys - 1, part.meta.gangway.x1 + P + 1, yn + 1],
    ];
    Object.assign(bounds, walkLimit);
    rebuildColliders();
    myRoomReady().catch(console.error); // 문 누르면 바로 열리게 미리
    return part;
  });
  subwayReady.catch(console.error);

  const state = { x: SPAWN.x, y: SPAWN.y, yaw: SPAWN.yaw, pitch: SPAWN.pitch, goal: null, keys: new Set(), running: false, last: 0, lcdAt: 0 };
  let colliders = [];
  // 닫힌 문은 벽처럼 막음. 객차가 아직 안 왔으면 문은 안 열림
  function rebuildColliders() {
    colliders = [...room.meta.colliders, ...trainColliders, ...myColliders, ...doors.filter(d => !d.open).map(d => d.south ? [d.x0, -3.35, d.x1, d.wallY] : [d.x0, -.3, d.x1, 0])];
  }
  rebuildColliders();
  const applyDoor = d => {
    const e = d.t * d.t * (3 - 2 * d.t);
    if (d.pivot) d.pivot.rotation.y = DOOR_OPEN_RAD * e;
    d.leaves.forEach(l => { l.mesh.position.x = l.dir * LEAF_SLIDE * e; });
  };
  const openDoor = async d => {
    if (d.open) return;
    await subwayReady;
    if (d.south) { await myRoomReady(); myRoom.visible = true; }
    train.visible = true; gangway.group.visible = true; lastView = ''; invalidate();
    d.open = true; rebuildColliders();
    doors.forEach(v => { if (v.sign) v.sign.visible = !v.open; });
    if (reducedMotion) { d.t = 1; applyDoor(d); }
  };

  const applyCamera = () => {
    camera.position.copy(toThree(state.x, state.y, EYE));
    const c = Math.cos(state.pitch);
    camera.lookAt(camera.position.clone().add(toThree(Math.cos(state.yaw) * c, Math.sin(state.yaw) * c, Math.sin(state.pitch))));
  };
  const resize = () => {
    lastView = '';
    const w = root.clientWidth || innerWidth, h = root.clientHeight || innerHeight;
    camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h, false);
  };
  addEventListener('resize', resize);

  const moveBy = (dx, dy) => {
    const p = collide({ x: state.x + dx, y: state.y + dy }, colliders);
    state.x = p.x; state.y = p.y;
  };
  const hint = root.querySelector('.sim-hint');
  const interacted = () => hint?.classList.add('gone');

  // 경유지를 차례로 걷고 done 실행. 막혀도 다음으로 넘어감
  const walkRoute = (pts, done) => {
    const [first, ...rest] = pts;
    if (!first) { done?.(); return; }
    state.goal = { ...first, stuck: 0, then: () => walkRoute(rest, done) };
  };
  const inCar = () => state.y < -.15;
  const inMyRoom = () => state.y < -3.05;
  const leaveMyRoom = () => inMyRoom() ? [{ x: MY_DOOR.x0 + .475, y: MY_DOOR.stand }] : [];
  const openDoorNear = () => doors.filter(d => d.open && !d.south).sort((a, b) => Math.abs(a.mid - state.x) - Math.abs(b.mid - state.x))[0];

  const pickSheet = () => {
    // 집을 때 더미 쪽을 보게 (크게 보기가 바로 덮어서 안 튐)
    const dx = PILE.x - state.x, dy = PILE.y - state.y;
    state.yaw = Math.atan2(dy, dx); state.pitch = Math.atan2(PILE.z - EYE, Math.hypot(dx, dy));
    interacted();
    lastView = '';
    opts.openSheet(pile.take());
  };
  const reachPile = () => {
    interacted();
    if (Math.hypot(PILE.x - state.x, PILE.y - state.y) <= PILE.reach) return pickSheet();
    const fromCar = inCar() && openDoorNear();
    const toRoom = fromCar ? [{ x: fromCar.mid, y: -DOOR_STAND }, { x: fromCar.mid, y: DOOR_STAND }] : [];
    const startX = fromCar ? fromCar.mid : state.x;
    walkRoute([...leaveMyRoom(), ...toRoom, { x: startX, y: SOUTH_AISLE_Y }, { x: EAST_AISLE_X, y: SOUTH_AISLE_Y }, { x: EAST_AISLE_X, y: PILE.y }], pickSheet);
  };
  const readPaper = (day, x, y) => {
    interacted();
    const open = () => { state.yaw = Math.atan2(y - state.y, x - state.x); state.pitch = 0; opts.openSheet(day); };
    if (Math.hypot(x - state.x, y - state.y) <= GANGWAY.reach) return open();
    const door = !inCar() && openDoorNear();
    const toCar = door ? [{ x: door.mid, y: DOOR_STAND }, { x: door.mid, y: -DOOR_STAND }] : [];
    walkRoute([...leaveMyRoom(), ...toCar, { x: gangway.x0 - .4, y: gangway.yc }, { x: (gangway.x0 + gangway.x1) / 2, y: gangway.yc }], open);
  };
  const reachDesk = () => {
    interacted();
    const read = () => {
      const dx = DESK_STAND.x + .59 - state.x, dy = DESK_STAND.y - state.y;
      state.yaw = Math.atan2(dy, dx); state.pitch = Math.atan2(.74 - EYE, Math.hypot(dx, dy));
      lastView = ''; opts.openSheet(deskPile.take());
    };
    if (Math.hypot(DESK_STAND.x + .59 - state.x, DESK_STAND.y - state.y) <= DESK_REACH) return read();
    const way = inMyRoom() ? [] : [{ x: MY_DOOR.x0 + .475, y: MY_DOOR.stand }, { x: MY_DOOR.x0 + .475, y: -3.7 }];
    walkRoute([...way, DESK_STAND], read);
  };
  const reachSwitch = sw => {
    interacted();
    if (Math.hypot(sw.x - state.x, -state.y) <= SWITCH.reach) return flip(sw);
    if (inCar()) return; // 객차 안에선 교실 스위치에 안 감
    walkRoute([{ x: state.x, y: SOUTH_AISLE_Y }, { x: sw.x, y: SWITCH.stand }], () => flip(sw));
  };
  const reachDoor = d => {
    interacted();
    const wallY = d.south ? d.wallY : -.15;
    if (Math.hypot(d.mid - state.x, wallY - state.y) <= DOOR_REACH) { openDoor(d); return; }
    if (d.south) {
      const via = openDoorNear();
      const toCar = !inCar() && via ? [{ x: via.mid, y: DOOR_STAND }, { x: via.mid, y: -DOOR_STAND }] : [];
      walkRoute([...toCar, { x: d.mid, y: d.stand }], () => openDoor(d));
      return;
    }
    if (inCar()) { walkRoute([...leaveMyRoom(), { x: d.mid, y: -DOOR_STAND - .3 }], () => openDoor(d)); return; }
    walkRoute([{ x: state.x, y: SOUTH_AISLE_Y }, { x: d.mid, y: DOOR_STAND }], () => openDoor(d));
  };
  root.querySelector('.sim-take')?.addEventListener('click', pickSheet);
  root.querySelector('.sim-myroom')?.addEventListener('click', () => {
    const d = doors.find(v => v.south);
    state.x = d.mid; state.y = d.stand; state.yaw = -Math.PI / 2; state.pitch = 0;
    if (!doors.some(v => v.open)) openDoor(doors.find(v => !v.south && v.id === 'B'));
    openDoor(d);
  });
  root.querySelector('.sim-light')?.addEventListener('click', () => setLights(!sim.lights));
  root.querySelector('.sim-door')?.addEventListener('click', () => {
    const d = doors.find(v => !v.open && !v.south) ?? doors[0];
    state.x = d.mid; state.y = .72; state.yaw = -Math.PI / 2; state.pitch = 0;
    openDoor(d);
  });

  // 끌기 = 둘러보기. 누르기 = 종이·문이면 그쪽으로, 바닥이면 걷기
  const el = renderer.domElement; let drag = null;
  const ray = new THREE.Raycaster(); const floorPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0); const hit = new THREE.Vector3();
  const aim = e => {
    const r = el.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
  };
  const targetUnderRay = () => {
    const closed = doors.filter(d => !d.open);
    const papers = gangway?.group.visible ? gangway.papers : [];
    const deskHit = deskPile && myRoom.visible ? [deskPile.proxy] : [];
    const hits = ray.intersectObjects([pile.proxy, ...closed.map(d => d.proxy), ...papers, ...switches.map(v => v.proxy), ...deskHit], false);
    if (!hits.length) return null;
    const o = hits[0].object;
    if (o === pile.proxy) return { pile: true };
    if (deskPile && o === deskPile.proxy) return { desk: true };
    if (o.userData.day !== undefined) return { paper: o };
    const sw = switches.find(v => v.proxy === o);
    if (sw) return { sw };
    return { door: closed.find(d => d.proxy === o) };
  };
  el.addEventListener('pointerdown', e => {
    if (e.button) return;
    el.setPointerCapture(e.pointerId);
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: false };
  });
  el.addEventListener('pointermove', e => {
    if (!drag && e.pointerType === 'mouse') { aim(e); el.classList.toggle('over-paper', !!targetUnderRay()); }
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.moved && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) <= TAP_SLOP_PX) return;
    drag.moved = true; el.classList.add('dragging'); interacted(); state.goal = null;
    state.yaw += (e.clientX - drag.x) * TURN_PER_PX;
    state.pitch = Math.max(-PITCH_MAX, Math.min(PITCH_MAX, state.pitch + (e.clientY - drag.y) * TURN_PER_PX));
    drag.x = e.clientX; drag.y = e.clientY;
  });
  const endDrag = e => {
    if (!drag) return;
    const tap = !drag.moved && e.type === 'pointerup';
    drag = null; el.classList.remove('dragging');
    if (!tap) return;
    aim(e);
    const target = targetUnderRay();
    if (target?.pile) return reachPile();
    if (target?.desk) return reachDesk();
    if (target?.door) return reachDoor(target.door);
    if (target?.sw) return reachSwitch(target.sw);
    if (target?.paper) { const p = target.paper.position; return readPaper(target.paper.userData.day, p.x, -p.z); }
    if (ray.ray.intersectPlane(floorPlane, hit)) {
      state.goal = { x: Math.max(bounds.x0, Math.min(bounds.x1, hit.x)), y: Math.max(myRoom?.visible ? MY_ROOM_Y0 : BOUNDS_Y0, Math.min(D - .2, -hit.z)), stuck: 0 };
      interacted();
    }
  };
  el.addEventListener('pointerup', endDrag); el.addEventListener('pointercancel', endDrag);
  el.addEventListener('wheel', e => {
    interacted(); state.goal = null;
    const s = -e.deltaY * WHEEL_STEP;
    moveBy(Math.cos(state.yaw) * s, Math.sin(state.yaw) * s);
  }, { passive: true });
  // e.code: 글자가 아니라 키 위치. 한글 입력 상태에선 W가 'ㅈ'으로 들어와서 e.key로는 안 먹음
  const MOVE_KEYS = ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
  addEventListener('keydown', e => {
    const k = e.code;
    if (!state.running || opts.paused() || !MOVE_KEYS.includes(k) || e.metaKey || e.ctrlKey) return;
    e.preventDefault(); state.keys.add(k); state.goal = null; interacted();
  });
  addEventListener('keyup', e => state.keys.delete(e.code));
  addEventListener('blur', () => state.keys.clear());

  let lastView = '', redrawUntil = 0;
  const invalidate = () => { redrawUntil = performance.now() + SETTLE_MS; };
  THREE.DefaultLoadingManager.onProgress = invalidate; // 질감이 늦게 도착하면 다시 그림
  const has = (...k) => k.some(v => state.keys.has(v));
  const arrive = () => { const then = state.goal.then; state.goal = null; then?.(); };
  function step(t) {
    if (!state.running) return;
    const dt = Math.min((t - state.last) / 1000 || 0, .05); state.last = t;
    if (opts.paused()) state.keys.clear();
    const f = (has('KeyW', 'ArrowUp') ? 1 : 0) - (has('KeyS', 'ArrowDown') ? 1 : 0);
    const s = (has('KeyD') ? 1 : 0) - (has('KeyA') ? 1 : 0);
    state.yaw += ((has('ArrowLeft') ? 1 : 0) - (has('ArrowRight') ? 1 : 0)) * 1.4 * dt;
    if (f || s) {
      const v = WALK_SPEED * dt, c = Math.cos(state.yaw), n = Math.sin(state.yaw);
      moveBy((c * f + n * s) * v, (n * f - c * s) * v);
    } else if (state.goal) {
      const dx = state.goal.x - state.x, dy = state.goal.y - state.y, d = Math.hypot(dx, dy);
      if (d < .08) arrive();
      else {
        const v = Math.min(WALK_SPEED * dt * Math.min(1, d / .4 + .25), d);
        const bx = state.x, by = state.y;
        moveBy(dx / d * v, dy / d * v);
        // 막혀서 못 나아가면 다음으로
        state.goal.stuck = Math.hypot(state.x - bx, state.y - by) < v * .25 ? state.goal.stuck + 1 : 0;
        if (state.goal.stuck > 8) arrive();
      }
    }
    doors.forEach(d => { if (d.open && d.t < 1) { d.t = Math.min(1, d.t + dt * 1000 / DOOR_MS); applyDoor(d); } });
    if (t - state.lcdAt > LCD_MS) { state.lcdAt = t; lcd.next(); if (train?.visible) invalidate(); }
    // 움직임이 없으면 다시 그리지 않음 (렉·배터리)
    const view = `${state.x},${state.y},${state.yaw},${state.pitch},${camera.fov}`;
    if (view !== lastView || doors.some(d => d.open && d.t < 1) || t < redrawUntil) {
      lastView = view;
      if (refl) refl.visible = state.y > -.3; // 객차 안에선 교실 바닥 반사 끔
      carClones.forEach(c => { c.visible = state.y > -3.1; }); // 방 안에선 앞뒤 칸 안 그림
      applyCamera();
      renderer.render(scene, camera);
    }
    requestAnimationFrame(step);
  }
  return {
    start() { if (state.running) return; state.running = true; state.last = performance.now(); resize(); invalidate(); requestAnimationFrame(step); },
    stop() { state.running = false; state.keys.clear(); state.goal = null; },
    state, camera, doors, openDoor, subwayReady, sim,
  };
}

let pending = null;
export function open(root, opts) {
  pending ??= build(root, opts).then(s => (ui = s));
  pending.then(s => { root.classList.add('ready'); if (location.hash === '#sim') s.start(); },
    err => { console.error(err); root.classList.add('failed'); });
}
export function close() { ui?.stop(); }
// 사진과 비교·자동 점검에 쓰는 자리 지정 (시뮬레이션 동작엔 안 쓰임)
export const pose = (x, y, yawDeg, pitchDeg = 0, fov) => {
  if (!ui) return false;
  Object.assign(ui.state, { x, y, yaw: yawDeg * Math.PI / 180, pitch: pitchDeg * Math.PI / 180, goal: null });
  if (fov) { ui.camera.fov = fov; ui.camera.updateProjectionMatrix(); }
  return true;
};
export const where = () => ui && { x: ui.state.x, y: ui.state.y, doors: ui.doors.map(d => [d.id, d.open]), lights: ui.sim.lights, ac: ui.sim.ac, yaw: ui.state.yaw, pitch: ui.state.pitch };
export const openAllDoors = async () => { await ui.subwayReady; await Promise.all(ui.doors.map(ui.openDoor)); };
