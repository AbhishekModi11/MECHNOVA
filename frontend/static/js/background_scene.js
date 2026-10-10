// Animated 3D Background with Wireframe Machined Parts & Toolpath Lines
(function () {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return; // Respect reduced motion preference
  }

  function initScene() {
    let container = document.getElementById('bg-canvas-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'bg-canvas-container';
      document.body.appendChild(container);
    } else {
      container.innerHTML = '';
    }

    if (typeof THREE === 'undefined') {
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 45;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    container.appendChild(renderer.domElement);

    // Fetch theme accent color
    function getAccentColor() {
      const col = getComputedStyle(document.documentElement).getPropertyValue('--accent-600').trim();
      return col ? col : '#1D7147';
    }

    let wireMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(getAccentColor()),
      wireframe: true,
      transparent: true,
      opacity: 0.18
    });

    // 1. Drilled Machined Plate (Box with cylinder cutout approximations)
    const plateGeom = new THREE.BoxGeometry(22, 14, 4, 6, 6, 2);
    const plateMesh = new THREE.Mesh(plateGeom, wireMaterial);
    plateMesh.position.set(-18, 8, -5);
    scene.add(plateMesh);

    // 2. Machined Gear/Cylinder
    const gearGeom = new THREE.CylinderGeometry(10, 10, 5, 24, 3, true);
    const gearMesh = new THREE.Mesh(gearGeom, wireMaterial);
    gearMesh.position.set(20, -6, -10);
    scene.add(gearMesh);

    // 3. Bracket Model
    const bracketGeom = new THREE.TorusGeometry(12, 3.5, 8, 32);
    const bracketMesh = new THREE.Mesh(bracketGeom, wireMaterial);
    bracketMesh.position.set(0, -14, -15);
    scene.add(bracketMesh);

    // 4. Drifting Toolpath Lines (Curved CNC paths)
    const curvePoints = [];
    for (let i = 0; i < 40; i++) {
      const t = i / 40;
      curvePoints.push(new THREE.Vector3(
        (t - 0.5) * 60,
        Math.sin(t * Math.PI * 4) * 10,
        Math.cos(t * Math.PI * 2) * 8
      ));
    }
    const curve = new THREE.CatmullRomCurve3(curvePoints);
    const lineGeom = new THREE.BufferGeometry().setFromPoints(curve.getPoints(120));
    const lineMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(getAccentColor()),
      transparent: true,
      opacity: 0.35,
      linewidth: 1.5
    });
    const toolpathLine = new THREE.Line(lineGeom, lineMaterial);
    scene.add(toolpathLine);

    // 5. Soft Particle Dust (floating metal shavings/chips)
    const particleCount = 120;
    const pGeom = new THREE.BufferGeometry();
    const pPositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      pPositions[i] = (Math.random() - 0.5) * 80;
      pPositions[i + 1] = (Math.random() - 0.5) * 60;
      pPositions[i + 2] = (Math.random() - 0.5) * 40;
    }
    pGeom.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
    const pMaterial = new THREE.PointsMaterial({
      color: new THREE.Color(getAccentColor()),
      size: 0.8,
      transparent: true,
      opacity: 0.25
    });
    const particles = new THREE.Points(pGeom, pMaterial);
    scene.add(particles);

    // Animation Loop
    let animId;
    let clock = new THREE.Clock();

    function animate() {
      if (document.hidden) {
        animId = requestAnimationFrame(animate);
        return;
      }

      const delta = clock.getDelta();
      plateMesh.rotation.x += delta * 0.12;
      plateMesh.rotation.y += delta * 0.18;

      gearMesh.rotation.y += delta * 0.25;
      gearMesh.rotation.z += delta * 0.1;

      bracketMesh.rotation.x += delta * 0.15;
      bracketMesh.rotation.z += delta * 0.12;

      toolpathLine.rotation.y += delta * 0.08;
      particles.rotation.y += delta * 0.04;

      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    }
    animate();

    // Theme update observer
    const observer = new MutationObserver(() => {
      const col = new THREE.Color(getAccentColor());
      wireMaterial.color = col;
      lineMaterial.color = col;
      pMaterial.color = col;
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-accent'] });

    // Window resize
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScene);
  } else {
    setTimeout(initScene, 100);
  }
})();
