import * as THREE from 'three';
import { OrbitControls } from 'https://unpkg.com/three@0.128.0/examples/jsm/controls/OrbitControls.js';

// Инициализация сцены
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a1030);
scene.fog = new THREE.FogExp2(0x0a1030, 0.008);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(15, 8, 15);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

// Освещение (как в Lineage)
const ambientLight = new THREE.AmbientLight(0x404060);
scene.add(ambientLight);

const mainLight = new THREE.DirectionalLight(0xfff5e6, 1.2);
mainLight.position.set(10, 20, 5);
mainLight.castShadow = true;
mainLight.receiveShadow = true;
mainLight.shadow.mapSize.width = 1024;
mainLight.shadow.mapSize.height = 1024;
scene.add(mainLight);

const fillLight = new THREE.PointLight(0x4466cc, 0.5);
fillLight.position.set(-5, 5, 10);
scene.add(fillLight);

const backLight = new THREE.PointLight(0xffaa66, 0.3);
backLight.position.set(0, 5, -8);
scene.add(backLight);

// Пол (с текстурой как в Lineage)
const groundGeometry = new THREE.PlaneGeometry(40, 40);
const groundMaterial = new THREE.MeshStandardMaterial({ color: 0x3a6b3a, roughness: 0.8, metalness: 0.1 });
const ground = new THREE.Mesh(groundGeometry, groundMaterial);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.5;
ground.receiveShadow = true;
scene.add(ground);

// Сетка для визуального ориентира
const gridHelper = new THREE.GridHelper(40, 20, 0x88aa88, 0x446644);
gridHelper.position.y = -0.4;
scene.add(gridHelper);

// Игрок (рыцарь в простой геометрии)
const playerGroup = new THREE.Group();
const bodyGeo = new THREE.BoxGeometry(0.8, 1.2, 0.6);
const bodyMat = new THREE.MeshStandardMaterial({ color: 0xcc8844, metalness: 0.7, roughness: 0.3 });
const body = new THREE.Mesh(bodyGeo, bodyMat);
body.castShadow = true;
body.receiveShadow = true;
body.position.y = 0.6;
playerGroup.add(body);

const headGeo = new THREE.SphereGeometry(0.45, 24, 24);
const headMat = new THREE.MeshStandardMaterial({ color: 0xddbb99 });
const head = new THREE.Mesh(headGeo, headMat);
head.castShadow = true;
head.position.y = 1.2;
playerGroup.add(head);

const helmetGeo = new THREE.CylinderGeometry(0.5, 0.55, 0.3, 8);
const helmetMat = new THREE.MeshStandardMaterial({ color: 0xccaa77, metalness: 0.8 });
const helmet = new THREE.Mesh(helmetGeo, helmetMat);
helmet.position.y = 1.45;
helmet.castShadow = true;
playerGroup.add(helmet);

const swordGeo = new THREE.BoxGeometry(0.15, 1.0, 0.15);
const swordMat = new THREE.MeshStandardMaterial({ color: 0x88aaff, metalness: 0.9 });
const sword = new THREE.Mesh(swordGeo, swordMat);
sword.position.set(0.5, 0.9, 0);
sword.castShadow = true;
playerGroup.add(sword);

playerGroup.position.set(0, -0.2, 0);
scene.add(playerGroup);

// Монстры (простые, но с aura эффектом)
const monsters = [];
const monsterColors = [0xaa3333, 0x44aa44, 0xaa44aa, 0x33aacc, 0xcc8833];

for (let i = 0; i < 8; i++) {
    const monsterGroup = new THREE.Group();
    const bodyGeo = new THREE.SphereGeometry(0.5, 16, 16);
    const bodyMat = new THREE.MeshStandardMaterial({ color: monsterColors[i % monsterColors.length], emissive: 0x331100 });
    const monsterBody = new THREE.Mesh(bodyGeo, bodyMat);
    monsterBody.castShadow = true;
    monsterGroup.add(monsterBody);
    
    const eyeGeo = new THREE.SphereGeometry(0.12, 8, 8);
    const eyeMat = new THREE.MeshStandardMaterial({ color: 0xff3333, emissive: 0x550000 });
    const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
    leftEye.position.set(-0.2, 0.2, 0.45);
    const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
    rightEye.position.set(0.2, 0.2, 0.45);
    monsterGroup.add(leftEye);
    monsterGroup.add(rightEye);
    
    const angle = (i / 8) * Math.PI * 2;
    const radius = 8;
    monsterGroup.position.set(Math.cos(angle) * radius, -0.3, Math.sin(angle) * radius);
    
    scene.add(monsterGroup);
    monsters.push(monsterGroup);
}

// Эффекты частиц для баффов
const particleSystem = new THREE.BufferGeometry();
const particleCount = 500;
const particlePositions = new Float32Array(particleCount * 3);
for (let i = 0; i < particleCount; i++) {
    particlePositions[i*3] = (Math.random() - 0.5) * 20;
    particlePositions[i*3+1] = Math.random() * 5;
    particlePositions[i*3+2] = (Math.random() - 0.5) * 20;
}
particleSystem.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
const particleMat = new THREE.PointsMaterial({ color: 0xffaa66, size: 0.08 });
const particles = new THREE.Points(particleSystem, particleMat);
scene.add(particles);

// Анимация и эффекты
let time = 0;
let buffEffectActive = false;
let buffEffectTime = 0;

window.threeRenderer = {
    addBuffEffect: () => {
        buffEffectActive = true;
        buffEffectTime = 2.0;
        
        // Временное усиление свечения вокруг игрока
        const glowGeo = new THREE.SphereGeometry(1.2, 16, 16);
        const glowMat = new THREE.MeshBasicMaterial({ color: 0xff6600, transparent: true, opacity: 0.5 });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        playerGroup.add(glow);
        setTimeout(() => playerGroup.remove(glow), 500);
    }
};

// Орбитальный контроль камеры
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = false;
controls.enableZoom = true;
controls.zoomSpeed = 1.2;
controls.target.set(0, 1, 0);

// Анимация
function animate() {
    requestAnimationFrame(animate);
    time += 0.016;
    
    // Анимация монстров (покачивание)
    monsters.forEach((monster, idx) => {
        monster.position.y = -0.3 + Math.sin(time * 2 + idx) * 0.05;
        monster.rotation.y = time * 0.5;
    });
    
    // Анимация частиц
    particles.rotation.y = time * 0.1;
    particles.rotation.x = Math.sin(time * 0.2) * 0.1;
    
    // Эффект баффа
    if (buffEffectActive) {
        buffEffectTime -= 0.016;
        if (buffEffectTime <= 0) buffEffectActive = false;
        const intensity = 0.5 + Math.sin(time * 20) * 0.3;
        mainLight.intensity = 1.2 + intensity * 0.5;
    } else {
        mainLight.intensity = 1.2;
    }
    
    controls.update();
    renderer.render(scene, camera);
}

animate();

// Ресайз окна
window.addEventListener('resize', onWindowResize, false);
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

console.log("✅ Three.js рендерер загружен! 3D сцена готова.");