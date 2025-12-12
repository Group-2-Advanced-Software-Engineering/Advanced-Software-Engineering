const SPHERE_RADIUS = 0.4;
const SPHERE_SPACING = 1.0;
const DEFAULT_SOLVE_TIME_SECONDS = 120;
const DEFAULT_BATCH_SIZE = 100;
const DEFAULT_PYRAMID_SIZE = 5;
const PREVIEW_SEGMENTS = 32;

let pyramidLevels = typeof initialPyramidLevels !== 'undefined' ? initialPyramidLevels : DEFAULT_PYRAMID_SIZE;
let scene, camera, renderer, controls;
let pyramidGroup, pieceGroup, previewGroup, levelHighlightGroup;
let pieces = [];
let selectedPiece = null;
let pyramidState = {};
let usedPieces = new Set();
let moveHistory = [];
let pieceColorMap = new Map();
let hoveredPosition = null;

let isSolving = false;
let activeSolveController = null;
let solutionStore = [];

let infiniteScrollArmed = true;
let lastScrollTopValue = 0;
let lastScrollRatio = 0;
let lastFetchTime = 0;
let lastFetchCursor = 0;

let sharedSolutionRenderer = null;

const solveState = {
    lastBoardSnapshot: null,
    solutionsReturned: 0,
    totalSolutions: 0,
    timedOut: false,
    exhausted: false,
    lastMaxTime: DEFAULT_SOLVE_TIME_SECONDS,
    displayedCount: 0
};

function initScene() {
    const container = document.getElementById('pyramid-canvas-container');
    const canvas = document.getElementById('pyramid-canvas');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    camera = new THREE.PerspectiveCamera(
        60,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
    );
    camera.position.set(6, 12, 10);
    camera.lookAt(3, 2, 3);

    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    scene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-10, 10, -10);
    scene.add(directionalLight2);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 5;
    controls.maxDistance = 30;

    pyramidGroup = new THREE.Group();
    scene.add(pyramidGroup);

    pieceGroup = new THREE.Group();
    scene.add(pieceGroup);

    previewGroup = new THREE.Group();
    scene.add(previewGroup);

    levelHighlightGroup = new THREE.Group();
    scene.add(levelHighlightGroup);

    buildPyramidStructure();

    setupRaycasting();

    window.addEventListener('resize', onWindowResize);

    animate();
}

function onWindowResize() {
    const container = document.getElementById('pyramid-canvas-container');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}
function updatePyramidSize(newLevels) {
    pyramidLevels = newLevels;

    clearPyramid();

    buildPyramidStructure();

    const cameraDistance = pyramidLevels * 2 + 6;
    camera.position.set(cameraDistance, cameraDistance * 2, cameraDistance);
    camera.lookAt(pyramidLevels / 2, pyramidLevels / 2, pyramidLevels / 2);

    showStatus(`Pyramid resized to ${newLevels} levels`, 'info');
}
function buildPyramidStructure() {
    pyramidGroup.clear();

    for (let z = 0; z < pyramidLevels; z++) {
        const gridSize = pyramidLevels - z;

        const minXY = z;
        const maxXY = (pyramidLevels * 2 - 1) - z;
        const odd = z & 1;

        for (let latticeX = minXY; latticeX <= maxXY; latticeX += 2) {
            if ((latticeX & 1) !== odd) continue;

            for (let latticeY = minXY; latticeY <= maxXY; latticeY += 2) {
                if ((latticeY & 1) !== odd) continue;

                // Convert lattice to grid for display
                const gridX = (latticeX - z) / 2;
                const gridY = (latticeY - z) / 2;
                const gridZ = z;

                const posKey = `${gridX},${gridY},${gridZ}`;

                // Calculate world position
                const worldX = gridX * SPHERE_SPACING + (z * SPHERE_SPACING / 2);
                const layerY = z * SPHERE_SPACING * 0.866;
                const worldZ = gridY * SPHERE_SPACING + (z * SPHERE_SPACING / 2);

                const geometry = new THREE.SphereGeometry(SPHERE_RADIUS * 0.9, 32, 32);
                const material = new THREE.MeshPhongMaterial({
                    color: 0x4a5568,
                    transparent: true,
                    opacity: 0.2,
                    emissive: 0x2d3748,
                    emissiveIntensity: 0.4,
                    shininess: 60
                });
                const sphere = new THREE.Mesh(geometry, material);
                sphere.position.set(worldX, layerY, worldZ);
                sphere.userData = { posKey, x: gridX, y: gridY, z: gridZ };
                pyramidGroup.add(sphere);

                const wireGeometry = new THREE.SphereGeometry(SPHERE_RADIUS * 0.92, 12, 12);
                const wireMaterial = new THREE.MeshBasicMaterial({
                    color: 0x718096,
                    wireframe: true,
                    transparent: true,
                    opacity: 0.3
                });
                const wireframe = new THREE.Mesh(wireGeometry, wireMaterial);
                wireframe.position.set(worldX, layerY, worldZ);
                pyramidGroup.add(wireframe);
            }
        }

        // Grid lines
        const gridHelper = new THREE.Group();
        const lineColor = new THREE.Color().setHSL(0.6, 0.7, 0.5 + z * 0.1);
        const lineMaterial = new THREE.LineBasicMaterial({
            color: lineColor,
            transparent: true,
            opacity: 0.4
        });

        const offset = z * SPHERE_SPACING / 2;
        const layerY = z * SPHERE_SPACING * 0.866;

        for (let i = 0; i <= gridSize; i++) {
            const points = [];
            points.push(new THREE.Vector3(offset + i * SPHERE_SPACING, layerY, offset));
            points.push(new THREE.Vector3(
                offset + i * SPHERE_SPACING,
                layerY,
                offset + (gridSize - 1) * SPHERE_SPACING
            ));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMaterial);
            gridHelper.add(line);
        }

        for (let i = 0; i <= gridSize; i++) {
            const points = [];
            points.push(new THREE.Vector3(offset, layerY, offset + i * SPHERE_SPACING));
            points.push(new THREE.Vector3(
                offset + (gridSize - 1) * SPHERE_SPACING,
                layerY,
                offset + i * SPHERE_SPACING
            ));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMaterial);
            gridHelper.add(line);
}

pyramidGroup.add(gridHelper);

        // Level label
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 128;
        canvas.height = 64;
        context.fillStyle = '#4facfe';
        context.font = 'bold 48px Arial';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(`L${z}`, 64, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            opacity: 0.7
        });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.position.set(offset - 0.8, layerY, offset - 0.8);
        sprite.scale.set(0.8, 0.4, 1);
        pyramidGroup.add(sprite);
    }
}


function getPyramidPosition(x, y, z) {
    const offset = z * SPHERE_SPACING / 2;
    return {
        x: x * SPHERE_SPACING + offset,
        y: z * SPHERE_SPACING * 0.866,
        z: y * SPHERE_SPACING + offset
    };}

let raycaster, mouse;

function setupRaycasting() {
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    const canvas = document.getElementById('pyramid-canvas');
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('click', onCanvasClick);
}

function onMouseMove(event) {
    if (!selectedPiece) {
        clearPreview();
        clearLevelHighlight();
        return;
    }

    const canvas = event.target;
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pyramidGroup.children, true);

    if (intersects.length > 0) {
        let obj = null;
        for (const intersect of intersects) {
            if (intersect.object.userData && intersect.object.userData.posKey) {
                obj = intersect.object;
                break;
            }
        }

        if (obj) {
            const { x, y, z } = obj.userData;
            hoveredPosition = { x, y, z };
            highlightLevel(z);
            showPiecePreview(x, y, z);
        }
    } else {
        hoveredPosition = null;
        clearPreview();
        clearLevelHighlight();
    }
}

function onCanvasClick(event) {
    if (!selectedPiece || !hoveredPosition) return;

    const { x, y, z } = hoveredPosition;
    if (canPlacePiece(x, y, z)) {
        placePiece(x, y, z);
    } else {
        showStatus('Cannot place piece at this position', 'error');
    }
}

function showPiecePreview(x, y, z) {
    clearPreview();

    if (!selectedPiece || !selectedPiece.cells) return;

    const canPlace = canPlacePiece(x, y, z);
    const pieceColor = selectedPiece.color || '#4facfe';

    for (const [dx, dy, dz] of selectedPiece.cells) {
        const nx = x + dx;
        const ny = y + dy;
        const nz = z + dz;

        if (!isValidPosition(nx, ny, nz)) continue;

        const pos = getPyramidPosition(nx, ny, nz);

        const geometry = new THREE.SphereGeometry(SPHERE_RADIUS, PREVIEW_SEGMENTS, PREVIEW_SEGMENTS);
        const material = new THREE.MeshPhongMaterial({
            color: canPlace ? pieceColor : 0xff0000,
            transparent: true,
            opacity: canPlace ? 0.7 : 0.4,
            emissive: canPlace ? pieceColor : 0xff0000,
            emissiveIntensity: 0.3,
            shininess: 60
        });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(pos.x, pos.y, pos.z);
        previewGroup.add(sphere);

        const outlineGeometry = new THREE.SphereGeometry(SPHERE_RADIUS * 1.1, PREVIEW_SEGMENTS, PREVIEW_SEGMENTS);
        const outlineMaterial = new THREE.MeshBasicMaterial({
            color: canPlace ? 0xffffff : 0xff0000,
            transparent: true,
            opacity: 0.2,
            side: THREE.BackSide
        });
        const outline = new THREE.Mesh(outlineGeometry, outlineMaterial);
        outline.position.set(pos.x, pos.y, pos.z);
        previewGroup.add(outline);
    }

    const anchorPos = getPyramidPosition(x, y, z);
    const anchorGeometry = new THREE.SphereGeometry(SPHERE_RADIUS * 0.5, 16, 16);
    const anchorMaterial = new THREE.MeshBasicMaterial({
        color: 0xffff00,
        transparent: true,
        opacity: 0.8
    });
    const anchorSphere = new THREE.Mesh(anchorGeometry, anchorMaterial);
    anchorSphere.position.set(anchorPos.x, anchorPos.y, anchorPos.z);
    previewGroup.add(anchorSphere);
}

function clearPreview() {
    previewGroup.clear();
}

function highlightLevel(z) {
    clearLevelHighlight();

    const gridSize = pyramidLevels - z;
    const offset = z * SPHERE_SPACING / 2;
    const levelY = z * SPHERE_SPACING * 0.866;

    const planeSize = (gridSize - 1) * SPHERE_SPACING + SPHERE_SPACING * 0.5;
    const planeGeometry = new THREE.PlaneGeometry(planeSize, planeSize);
    const planeMaterial = new THREE.MeshBasicMaterial({
        color: 0x4facfe,
        transparent: true,
        opacity: 0.15,
        side: THREE.DoubleSide
    });
    const plane = new THREE.Mesh(planeGeometry, planeMaterial);
    plane.rotation.x = -Math.PI / 2;
    plane.position.set(
        offset + (gridSize - 1) * SPHERE_SPACING / 2,
        levelY,
        offset + (gridSize - 1) * SPHERE_SPACING / 2
    );
    levelHighlightGroup.add(plane);

    const edgesGeometry = new THREE.EdgesGeometry(planeGeometry);
    const edgesMaterial = new THREE.LineBasicMaterial({ color: 0x00f2fe, linewidth: 2 });
    const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
    edges.rotation.x = -Math.PI / 2;
    edges.position.copy(plane.position);
    levelHighlightGroup.add(edges);
}

function clearLevelHighlight() {
    levelHighlightGroup.clear();
}

function isValidPosition(x, y, z) {
    if (z < 0 || z >= pyramidLevels) return false;
    const gridSize = pyramidLevels - z;
    return x >= 0 && x < gridSize && y >= 0 && y < gridSize;
}

function canPlacePiece(x, y, z) {
    if (!selectedPiece || !selectedPiece.cells) return false;

    for (const [dx, dy, dz] of selectedPiece.cells) {
        const nx = x + dx;
        const ny = y + dy;
        const nz = z + dz;

        if (!isValidPosition(nx, ny, nz)) return false;

        const posKey = `${nx},${ny},${nz}`;
        if (pyramidState[posKey]) return false;
    }

    return true;
}

function placePiece(x, y, z) {
    if (!selectedPiece) return;

    const placedCells = [];
    const color = getColorForPieceId(selectedPiece.id);

    for (const [dx, dy, dz] of selectedPiece.cells) {
        const nx = x + dx;
        const ny = y + dy;
        const nz = z + dz;

        const posKey = `${nx},${ny},${nz}`;
        pyramidState[posKey] = selectedPiece.id;
        placedCells.push([nx, ny, nz]);

        const pos = getPyramidPosition(nx, ny, nz);
        const geometry = new THREE.SphereGeometry(SPHERE_RADIUS, PREVIEW_SEGMENTS, PREVIEW_SEGMENTS);
        const material = new THREE.MeshPhongMaterial({
            color: color,
            shininess: 60,
            specular: 0x444444
        });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(pos.x, pos.y, pos.z);
        sphere.userData = { pieceId: selectedPiece.id, posKey };
        pieceGroup.add(sphere);
    }

    moveHistory.push({
        pieceId: selectedPiece.id,
        cells: placedCells
    });

    usedPieces.add(selectedPiece.id);
    const placedName = selectedPiece.name;
    selectedPiece = null;

    clearPreview();
    updatePiecesDisplay();
    updatePieceInfo();
    showStatus(`Placed ${placedName}`, 'success');
}

function undoLastMove() {
    if (moveHistory.length === 0) {
        showStatus('No moves to undo', 'info');
        return;
    }

    const lastMove = moveHistory.pop();

    for (const [x, y, z] of lastMove.cells) {
        const posKey = `${x},${y},${z}`;
        delete pyramidState[posKey];
    }

    const toRemove = [];
    pieceGroup.children.forEach(child => {
        if (child.userData.pieceId === lastMove.pieceId) {
            toRemove.push(child);
        }
    });
    toRemove.forEach(obj => pieceGroup.remove(obj));

    usedPieces.delete(lastMove.pieceId);

    clearPreview();
    updatePiecesDisplay();
    updatePieceInfo();

    const piece = getPieceById(lastMove.pieceId);
    const name = piece ? piece.name : `#${lastMove.pieceId}`;
    showStatus(`Undid placement of ${name}`, 'info');
}

function clearPyramid() {
    // Stop any active solving first
    if (isSolving) {
        stopSolving();
    }
    
    // Force isSolving to false to prevent race conditions
    isSolving = false;

    pyramidState = {};
    moveHistory = [];
    usedPieces.clear();
    selectedPiece = null;
    pieceGroup.clear();
    clearPreview();
    updatePiecesDisplay();
    updatePieceInfo();
    resetSolutionsView();
    showStatus('Pyramid cleared', 'info');
}

function setupInfiniteScroll() {
    const container = document.querySelector('.pieces-section');
    if (!container) return;

    let ticking = false;

    const onScroll = () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(() => {
            try {
                maybeTriggerLoadMore(container);
            } finally {
                ticking = false;
            }
        });
    };

    container.addEventListener('scroll', onScroll, { passive: true });
}

function maybeTriggerLoadMore(container) {
    if (isSolving) return;

    const moreAvailable = !solveState.exhausted;
    if (!moreAvailable) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const maxScroll = Math.max(1, scrollHeight - clientHeight);
    const ratio = scrollTop / maxScroll;

    const scrolledDown = scrollTop > lastScrollTopValue;
    lastScrollTopValue = scrollTop;

    // Reset armed flag when scrolled back up
    if (ratio < 0.4) {
        infiniteScrollArmed = true;
    }
    
    // Trigger at 60% scroll threshold
    const crossedDownward = lastScrollRatio < 0.60 && ratio >= 0.60 && scrolledDown;
    lastScrollRatio = ratio;

    const now = Date.now();
    const cooldownOk = (now - lastFetchTime) > 600;

    if (infiniteScrollArmed && crossedDownward && cooldownOk) {
        infiniteScrollArmed = false;
        lastFetchTime = now;

        const currentCursor = solutionStore.length;
        if (currentCursor !== lastFetchCursor) {
            lastFetchCursor = currentCursor;
            window.loadMoreSolutions();
        }
    }

    // Also trigger near bottom (80%) as backup
    if (!isSolving && ratio >= 0.80 && cooldownOk) {
        const currentCursor = solutionStore.length;
        if (currentCursor !== lastFetchCursor) {
            lastFetchTime = now;
            lastFetchCursor = currentCursor;
            window.loadMoreSolutions();
        }
    }
}

function loadSolutionToPyramid(boardState) {
    pyramidState = {};
    moveHistory = [];
    usedPieces.clear();
    selectedPiece = null;
    clearPreview();

    pieceGroup.children.forEach(child => {
        if (child.children) {
            child.children.forEach(subChild => {
                if (subChild.geometry) subChild.geometry.dispose();
                if (subChild.material) subChild.material.dispose();
            });
        }
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
    });
    pieceGroup.clear();

    for (const [key, pieceId] of Object.entries(boardState)) {
        if (!pieceId) continue;

        let x, y, z;
        if (key.includes('(')) {
            const cleanKey = key.replace(/[()]/g, '');
            const parts = cleanKey.split(',').map(p => parseInt(p.trim()));
            [x, y, z] = parts;
        } else {
            const parts = key.split(',').map(p => parseInt(p.trim()));
            [x, y, z] = parts;
        }

        if (isNaN(x) || isNaN(y) || isNaN(z)) continue;

        const invertedZ = pyramidLevels - 1 - z;

        pyramidState[`${x},${y},${invertedZ}`] = pieceId;
        usedPieces.add(pieceId);
    }

    renderPyramidPieces();
    updatePiecesDisplay();
    updatePieceInfo();
}

function renderPyramidPieces() {
    pieceGroup.children.forEach(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
        if (child.children) {
            child.children.forEach(subChild => {
                if (subChild.geometry) subChild.geometry.dispose();
                if (subChild.material) subChild.material.dispose();
            });
        }
    });
    pieceGroup.clear();

    const piecePositions = {};
    for (const [key, pieceId] of Object.entries(pyramidState)) {
        if (!piecePositions[pieceId]) {
            piecePositions[pieceId] = [];
        }
        const [x, y, z] = key.split(',').map(Number);
        piecePositions[pieceId].push({ x, y, z });
    }

    for (const [pieceId, positions] of Object.entries(piecePositions)) {
        const color = getColorForPieceId(parseInt(pieceId));

        positions.forEach((coord, index) => {
            const pos = getPyramidPosition(coord.x, coord.y, coord.z);

            const geometry = new THREE.SphereGeometry(SPHERE_RADIUS, PREVIEW_SEGMENTS, PREVIEW_SEGMENTS);
            const material = new THREE.MeshPhongMaterial({ color: color });
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.set(pos.x, pos.y, pos.z);

            if (index === 0) {
                const anchorGeo = new THREE.SphereGeometry(SPHERE_RADIUS * 0.3, 8, 8);
                const anchorMat = new THREE.MeshBasicMaterial({ color: 0xffff00 });
                const anchor = new THREE.Mesh(anchorGeo, anchorMat);
                anchor.position.set(0, 0, 0);
                sphere.add(anchor);
            }

            pieceGroup.add(sphere);
        });
    }
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function loadPieces() {
    fetch('/api/pieces?type=3d')
        .then(response => response.json())
        .then(data => {
            pieces = data.pieces
                .filter(p => p.id <= 12)
                .map(piece => ({
                    ...piece,
                    cells: piece.shapeData.map(c => c.length === 3 ? c : [c[0], c[1], 0])
                }));

            pieceColorMap = new Map(pieces.map(p => [p.id, p.color]));
            displayPieces();
            updatePiecesDisplay();
        })
        .catch(error => {
            console.error('Error loading pieces:', error);
            showStatus('Failed to load pieces: ' + error.message, 'error');
        });
}

function displayPieces() {
    const piecesElement = document.getElementById('pieces');
    piecesElement.innerHTML = '';

    pieces.forEach(piece => {
        const pieceElement = document.createElement('div');
        pieceElement.className = 'piece';
        pieceElement.dataset.pieceId = piece.id;
        pieceElement.addEventListener('click', () => selectPiece(piece));

        if (usedPieces.has(piece.id)) {
            pieceElement.classList.add('used');
        }

        const nameDiv = document.createElement('div');
        nameDiv.style.fontWeight = 'bold';
        nameDiv.textContent = piece.name;
        pieceElement.appendChild(nameDiv);

        const previewCanvas = document.createElement('canvas');
        previewCanvas.width = 80;
        previewCanvas.height = 80;
        previewCanvas.className = 'piece-preview-canvas';

        renderPiecePreview(previewCanvas, piece);
        pieceElement.appendChild(previewCanvas);

        const idDiv = document.createElement('div');
        idDiv.style.fontSize = '0.75em';
        idDiv.style.color = '#666';
        idDiv.textContent = `ID: ${piece.id}`;
        pieceElement.appendChild(idDiv);

        piecesElement.appendChild(pieceElement);
    });
}

function renderPiecePreview(canvas, piece) {
    const miniScene = new THREE.Scene();
    miniScene.background = new THREE.Color(0xf8f9fa);

    const miniCamera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
    miniCamera.position.set(3, 3, 3);
    miniCamera.lookAt(0, 0, 0);

    const miniRenderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: true
    });
    miniRenderer.setSize(canvas.width, canvas.height);
    miniRenderer.setPixelRatio(window.devicePixelRatio);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    miniScene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
    directionalLight.position.set(2, 3, 2);
    miniScene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
    directionalLight2.position.set(-2, 1, -2);
    miniScene.add(directionalLight2);

    const color = piece.color || '#4facfe';

    const coords = piece.cells.map(c => [...c]);
    const minX = Math.min(...coords.map(c => c[0]));
    const minY = Math.min(...coords.map(c => c[1]));
    const minZ = Math.min(...coords.map(c => c[2]));
    const maxX = Math.max(...coords.map(c => c[0]));
    const maxY = Math.max(...coords.map(c => c[1]));
    const maxZ = Math.max(...coords.map(c => c[2]));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;

    coords.forEach(([x, y, z]) => {
        const geometry = new THREE.SphereGeometry(0.35, 24, 24);
        const material = new THREE.MeshPhongMaterial({
            color: color,
            shininess: 60,
            specular: 0x333333
        });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(
            (x - centerX) * 0.8,
            (y - centerY) * 0.8,
            (z - centerZ) * 0.8
        );
        miniScene.add(sphere);
    });

    miniRenderer.render(miniScene, miniCamera);
}

function selectPiece(piece) {
    if (usedPieces.has(piece.id)) {
        showStatus('This piece has already been placed', 'error');
        return;
    }

    selectedPiece = {
        id: piece.id,
        name: piece.name,
        color: piece.color,
        baseCells: piece.cells.map(c => [...c]),
        rotationX: 0,
        rotationY: 0,
        rotationZ: 0,
        flipped: false,
        cells: []
    };

    updateSelectedPieceCells();
    updatePiecesDisplay();
    updatePieceInfo();
    showStatus(`Selected ${piece.name}`, 'info');
}

function updatePiecesDisplay() {
    document.querySelectorAll('.piece').forEach(element => {
        const pieceId = Number(element.dataset.pieceId);

        if (usedPieces.has(pieceId)) {
            element.classList.add('used');
        } else {
            element.classList.remove('used');
        }

        if (selectedPiece && selectedPiece.id === pieceId) {
            element.classList.add('selected');
        } else {
            element.classList.remove('selected');
        }
    });
}

function updatePieceInfo() {
    const pieceInfo = document.getElementById('pieceInfo');
    const pieceName = document.getElementById('pieceName');
    const pieceRotationSpan = document.getElementById('pieceRotation');
    const pieceFlipped = document.getElementById('pieceFlipped');
    const previewDiv = document.getElementById('selectedPiecePreview');

    if (selectedPiece) {
        pieceName.textContent = `${selectedPiece.name}`;
        pieceRotationSpan.textContent = `${selectedPiece.rotationX} deg`;
        pieceFlipped.textContent = selectedPiece.flipped ? 'Yes' : 'No';
        pieceInfo.style.display = 'block';

        if (previewDiv) {
            renderSelectedPiecePreview2D(previewDiv);
        }
    } else {
        pieceInfo.style.display = 'none';
        if (previewDiv) {
            previewDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">💡 Click on a piece above to see its 3D structure and rotations</div>';
        }
    }
}

function renderSelectedPiecePreview2D(previewDiv) {
    if (!selectedPiece || !selectedPiece.cells) {
        previewDiv.innerHTML = '';
        return;
    }

    const cells = selectedPiece.cells;
    const color = selectedPiece.color || '#4facfe';

    const minX = Math.min(...cells.map(c => c[0]));
    const maxX = Math.max(...cells.map(c => c[0]));
    const minY = Math.min(...cells.map(c => c[1]));
    const maxY = Math.max(...cells.map(c => c[1]));
    const minZ = Math.min(...cells.map(c => c[2]));
    const maxZ = Math.max(...cells.map(c => c[2]));

    const width = maxX - minX + 1;
    const height = maxY - minY + 1;
    const depth = maxZ - minZ + 1;

    let html = '<div style="display: flex; gap: 15px; align-items: flex-start; justify-content: center;">';

    html += '<div style="text-align: center;">';
    html += '<div style="font-size: 11px; color: #666; margin-bottom: 5px; font-weight: bold;">Complete Piece</div>';
    html += '<div style="display: grid; grid-template-columns: repeat(' + width + ', 22px); grid-template-rows: repeat(' + height + ', 22px); gap: 2px;">';

    for (let y = minY; y <= maxY; y++) {
        for (let x = minX; x <= maxX; x++) {
            const hasCell = cells.some(c => c[0] === x && c[1] === y);
            if (hasCell) {
                const maxZAtPos = Math.max(...cells.filter(c => c[0] === x && c[1] === y).map(c => c[2]));
                const opacity = 0.5 + (maxZAtPos - minZ) / Math.max(1, depth) * 0.5;
                html += `<div style="width: 22px; height: 22px; background: ${color}; opacity: ${opacity}; border: 1px solid #333; border-radius: 3px;"></div>`;
            } else {
                html += '<div style="width: 22px; height: 22px;"></div>';
            }
        }
    }
    html += '</div></div>';

    if (depth > 1) {
        html += '<div style="text-align: center;">';
        html += '<div style="font-size: 11px; color: #666; margin-bottom: 5px; font-weight: bold;">By Level</div>';

        for (let z = maxZ; z >= minZ; z--) {
            html += `<div style="font-size: 9px; color: #999; margin-top: ${z === maxZ ? 0 : 8}px; margin-bottom: 2px;">Z=${z}</div>`;
            html += '<div style="display: grid; grid-template-columns: repeat(' + width + ', 18px); grid-template-rows: repeat(' + height + ', 18px); gap: 1px; margin-bottom: 3px;">';

            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    const hasCell = cells.some(c => c[0] === x && c[1] === y && c[2] === z);
                    if (hasCell) {
                        html += `<div style="width: 18px; height: 18px; background: ${color}; border: 1px solid #333; border-radius: 2px;"></div>`;
                    } else {
                        html += '<div style="width: 18px; height: 18px;"></div>';
                    }
                }
            }
            html += '</div>';
        }
        html += '</div>';
    }

    html += '</div>';
    previewDiv.innerHTML = html;
}

function renderSelectedPiecePreview(canvas) {
    if (!selectedPiece || !selectedPiece.cells) return;

    try {
        const miniScene = new THREE.Scene();
        miniScene.background = new THREE.Color(0xf8f9fa);

        const miniCamera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
        miniCamera.position.set(4, 4, 4);
        miniCamera.lookAt(0, 0, 0);

        const miniRenderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            alpha: true
        });
        miniRenderer.setSize(canvas.width, canvas.height);
        miniRenderer.setPixelRatio(window.devicePixelRatio);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        miniScene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
        directionalLight.position.set(3, 4, 3);
        miniScene.add(directionalLight);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        directionalLight2.position.set(-2, 1, -2);
        miniScene.add(directionalLight2);

        const color = selectedPiece.color || '#4facfe';

        const coords = selectedPiece.cells.map(c => [...c]);
        const minX = Math.min(...coords.map(c => c[0]));
        const minY = Math.min(...coords.map(c => c[1]));
        const minZ = Math.min(...coords.map(c => c[2]));
        const maxX = Math.max(...coords.map(c => c[0]));
        const maxY = Math.max(...coords.map(c => c[1]));
        const maxZ = Math.max(...coords.map(c => c[2]));

        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const centerZ = (minZ + maxZ) / 2;

        coords.forEach(([x, y, z]) => {
            const geometry = new THREE.SphereGeometry(0.4, 32, 32);
            const material = new THREE.MeshPhongMaterial({
                color: color,
                shininess: 60,
                specular: 0x444444
            });
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.set(
                (x - centerX) * 0.9,
                (y - centerY) * 0.9,
                (z - centerZ) * 0.9
            );
            miniScene.add(sphere);
        });

        miniRenderer.render(miniScene, miniCamera);
    } catch (error) {
        console.error('Error rendering piece preview:', error);
    }
}


function normalize3DCoords(coords) {
    if (!coords || coords.length === 0) return [];

    const minX = Math.min(...coords.map(c => c[0]));
    const minY = Math.min(...coords.map(c => c[1]));
    const minZ = Math.min(...coords.map(c => c[2]));

    return coords.map(([x, y, z]) => [x - minX, y - minY, z - minZ])
                 .sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
}

function rotate3DX(coords) {
    return normalize3DCoords(coords.map(([x, y, z]) => [x, -z, y]));
}

function rotate3DY(coords) {
    return normalize3DCoords(coords.map(([x, y, z]) => [z, y, -x]));
}

function rotate3DZ(coords) {
    return normalize3DCoords(coords.map(([x, y, z]) => [-y, x, z]));
}

function reflect3DXY(coords) {
    return normalize3DCoords(coords.map(([x, y, z]) => [x, y, -z]));
}

function clamp3DCoord(val, max) {
    const n = Number.parseInt(val, 10);
    if (!Number.isFinite(n)) return 0;
    return Math.min(Math.max(n, 0), max);
}

function getCoordInputs3D() {
    const xInput = document.getElementById('coordX3D');
    const yInput = document.getElementById('coordY3D');
    const zInput = document.getElementById('coordZ3D');
    const z = clamp3DCoord(zInput ? zInput.value : 0, pyramidLevels - 1);
    const maxXY = pyramidLevels - z - 1;
    return {
        x: clamp3DCoord(xInput ? xInput.value : 0, maxXY),
        y: clamp3DCoord(yInput ? yInput.value : 0, maxXY),
        z
    };
}

function setCoordInputs3D(x, y, z) {
    const zClamped = clamp3DCoord(z, pyramidLevels - 1);
    const maxXY = pyramidLevels - zClamped - 1;
    const xClamped = clamp3DCoord(x, maxXY);
    const yClamped = clamp3DCoord(y, maxXY);
    const xInput = document.getElementById('coordX3D');
    const yInput = document.getElementById('coordY3D');
    const zInput = document.getElementById('coordZ3D');
    if (xInput) xInput.value = xClamped;
    if (yInput) yInput.value = yClamped;
    if (zInput) zInput.value = zClamped;
}

window.nudgeCoords3D = function nudgeCoords3D(dx, dy, dz) {
    const { x, y, z } = getCoordInputs3D();
    setCoordInputs3D(x + dx, y + dy, z + dz);
    const coords = getCoordInputs3D();
    if (selectedPiece) {
        showPiecePreview(coords.x, coords.y, coords.z);
    }
};

window.placeSelectedFromPanel3D = function placeSelectedFromPanel3D() {
    if (!selectedPiece) {
        showStatus('Select a piece first.', 'info');
        return;
    }
    const { x, y, z } = getCoordInputs3D();
    if (canPlacePiece(x, y, z)) {
        placePiece(x, y, z);
        showStatus(`Placed at (${x}, ${y}, ${z}).`, 'success');
    } else {
        showStatus(`Cannot place at (${x}, ${y}, ${z}).`, 'error');
    }
};

function setupKeyboardShortcuts3D() {
    document.addEventListener('keydown', (evt) => {
        const active = document.activeElement;
        if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {
            return;
        }
        if (evt.key === 'r' || evt.key === 'R') {
            console.log('[Shortcut][3D] Rotate (R)');
            rotatePiece();
            evt.preventDefault();
        } else if (evt.key === 'f' || evt.key === 'F') {
            console.log('[Shortcut][3D] Flip (F)');
            flipPiece();
            evt.preventDefault();
        } else if (evt.key === 'Backspace') {
            console.log('[Shortcut][3D] Undo (Backspace)');
            undoLastMove();
            evt.preventDefault();
        } else if (evt.key === 'c' || evt.key === 'C') {
            console.log('[Shortcut][3D] Clear (C)');
            clearPyramid();
            evt.preventDefault();
        }
    });
}

function rotatePiece() {
    if (!selectedPiece) {
        showStatus('No piece selected', 'error');
        return;
    }
    clearPreview();
    selectedPiece.rotationX = (selectedPiece.rotationX + 90) % 360;
    updateSelectedPieceCells();
    updatePieceInfo();
    updatePiecesDisplay();
}

function rotatePieceX() {
    if (!selectedPiece) {
        showStatus('No piece selected', 'error');
        return;
    }
    selectedPiece.rotationX = (selectedPiece.rotationX + 90) % 360;
    updateSelectedPieceCells();
    updatePieceInfo();
    clearPreview();
}

function rotatePieceY() {
    if (!selectedPiece) {
        showStatus('No piece selected', 'error');
        return;
    }
    selectedPiece.rotationY = (selectedPiece.rotationY + 90) % 360;
    updateSelectedPieceCells();
    updatePieceInfo();
    clearPreview();
}

function rotatePieceZ() {
    if (!selectedPiece) {
        showStatus('No piece selected', 'error');
        return;
    }
    selectedPiece.rotationZ = (selectedPiece.rotationZ + 90) % 360;
    updateSelectedPieceCells();
    updatePieceInfo();
    clearPreview();
}

function flipPiece() {
    if (!selectedPiece) {
        showStatus('No piece selected', 'error');
        return;
    }
    clearPreview();
    selectedPiece.flipped = !selectedPiece.flipped;
    updateSelectedPieceCells();
    updatePieceInfo();
    updatePiecesDisplay();
}

function updateSelectedPieceCells() {
    if (!selectedPiece) return;

    let coords = selectedPiece.baseCells.map(c => [...c]);

    const stepsX = (selectedPiece.rotationX / 90) % 4;
    for (let i = 0; i < stepsX; i++) {
        coords = rotate3DX(coords);
    }

    const stepsY = (selectedPiece.rotationY / 90) % 4;
    for (let i = 0; i < stepsY; i++) {
        coords = rotate3DY(coords);
    }

    const stepsZ = (selectedPiece.rotationZ / 90) % 4;
    for (let i = 0; i < stepsZ; i++) {
        coords = rotate3DZ(coords);
    }

    if (selectedPiece.flipped) {
        coords = reflect3DXY(coords);
    }

    selectedPiece.cells = normalize3DCoords(coords);
}

function getConfiguredTimeLimitMs() {
    const input = document.getElementById('solveTimeLimit');
    let seconds = Number.parseFloat(input ? input.value : '');
    if (!Number.isFinite(seconds) || seconds < 0) {
        seconds = DEFAULT_SOLVE_TIME_SECONDS;
    }
    return seconds === 0 ? 0 : Math.round(seconds * 1000);
}

function getConfiguredBatchSize() {
    const sel = document.getElementById('batchSizeSelect');
    if (!sel) return DEFAULT_BATCH_SIZE;
    const v = parseInt(sel.value, 10);
    return Number.isFinite(v) && v > 0 ? v : DEFAULT_BATCH_SIZE;
}
//Function added to get the Pyramid size, added to solvePyramid, solveEmpty, and loadMoreSolutions
//Might not be required in loadMoreSolutions
function getConfiguredPyramidSize() {
    const sel = document.getElementById('levels');
    if (!sel) return DEFAULT_PYRAMID_SIZE;
    const v = parseInt(sel.value, 5);
    return Number.isFinite(v) && v > 0 ? v : DEFAULT_PYRAMID_SIZE;
}

function solvePyramid() {
    const maxTime = getConfiguredTimeLimitMs();
    solveState.lastMaxTime = maxTime;
    requestSolve({
        action: 'init',
        partialBoard: { ...pyramidState },
        batchSize: getConfiguredBatchSize(),
        levels: getConfiguredPyramidSize(),
        maxTime
    });
}

function solveEmpty() {
    const maxTime = getConfiguredTimeLimitMs();
    solveState.lastMaxTime = maxTime;
    requestSolve({
        action: 'init',
        partialBoard: {},
        batchSize: getConfiguredBatchSize(),
        levels: getConfiguredPyramidSize(),
        maxTime
    });
}

window.loadMoreSolutions = function() {
    if (isSolving) return;
    if (solveState.exhausted) return;
    
    // Don't load more if there's no active solve session
    if (!solveState.lastBoardSnapshot && solutionStore.length === 0) {
        return;
    }

    requestSolve({
        action: 'next',
        partialBoard: solveState.lastBoardSnapshot || {},
        batchSize: getConfiguredBatchSize(),
        levels: getConfiguredPyramidSize(),
        maxTime: solveState.lastMaxTime,
        offset: solutionStore.length  // Tell backend where to start
    });
};

async function requestSolve({ action = 'init', partialBoard, batchSize, maxTime, offset = 0 }) {
    if (isSolving && activeSolveController) {
        activeSolveController.abort();
    }

    if (action === 'init') {
        solveState.exhausted = false;
        solveState.timedOut = false;
        solveState.solutionsReturned = 0;
        solveState.totalSolutions = 0;
        solveState.displayedCount = 0;
        solutionStore.length = 0;
        const cont = document.getElementById('solutions');
        if (cont) cont.innerHTML = '';
    }

    const controller = new AbortController();
    activeSolveController = controller;
    isSolving = true;
    showLoading(true);

    const solveUrl = `/api/solve/${solveId}/`;

    try {
        const payload = {
            action: action,  // Include action for handleSolveSuccess
            levels: getConfiguredPyramidSize(),
            batchSize,
            maxTime: maxTime ?? solveState.lastMaxTime,
            offset: offset  // Include offset in request
        };

        if (partialBoard !== undefined) {
            payload.partialBoard = partialBoard;
        }

        const response = await fetch(solveUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
        });

        const data = await response.json();

        if (response.ok && data.success) {
            handleSolveSuccess(data, { ...payload });
            showStatus(data.message || 'Solutions found!', 'success');
        } else {
            throw new Error(data.error || 'Solver request failed');
        }
    } catch (error) {
        if (error.name !== 'AbortError') {
            showStatus('Solve error: ' + error.message, 'error');
        }
    } finally {
        if (activeSolveController === controller) {
            activeSolveController = null;
        }
        isSolving = false;
        showLoading(false);
        updateSolutionsSummary();
    }
}

function handleSolveSuccess(data, payload) {
    const solutions = data.solutions || [];
    const isInit = payload.action === 'init';

    if (isInit) {
        solutionStore.length = 0;
        scrollToSolutions();
    }

    for (const sol of solutions) {
        solutionStore.push(sol);
    }

    displaySolutions(solutions, { reset: isInit });

    solveState.lastBoardSnapshot = payload.partialBoard;
    solveState.displayedCount = solutionStore.length;
    solveState.solutionsReturned = solutionStore.length;
    solveState.totalSolutions = data.solutionCount ?? solveState.totalSolutions;
    solveState.timedOut = Boolean(data.timedOut);
    solveState.exhausted = Boolean(data.exhausted);

    // If backend is still computing, start polling for more solutions
    if (data.computing && !data.exhausted) {
        startPollingForSolutions();
    }

    updateSolutionsSummary();
}

function scrollToSolutions() {
    setTimeout(() => {
        const solutionsElement = document.getElementById('solutions');
        if (solutionsElement) {
            const piecesSection = document.querySelector('.pieces-section');
            if (piecesSection) {
                solutionsElement.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'nearest',
                    inline: 'start'
                });
                
                const solutionsTop = solutionsElement.offsetTop;
                piecesSection.scrollTo({
                    top: solutionsTop - 50,
                    behavior: 'smooth'
                });
            } else {
                solutionsElement.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
        }
    }, 300);
}

// Polling mechanism to check for new solutions while background computes
let pollingInterval = null;
function startPollingForSolutions() {
    // Clear any existing polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    // Poll every 2 seconds
    pollingInterval = setInterval(() => {
        // Stop if exhausted, solving, or no active session
        if (solveState.exhausted || isSolving || !solveState.lastBoardSnapshot) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            return;
        }
        
        // Request next batch
        window.loadMoreSolutions();
    }, 2000);
}

function displaySolutions(solutions, { reset = false } = {}) {
    const solutionsElement = document.getElementById('solutions');
    if (!solutionsElement) return;

    if (reset) {
        solutionsElement.innerHTML = '';
    }

    if (!solutions || solutions.length === 0) {
        if (reset) {
            // Create a prominent "no solutions" message
            const noSolutionsDiv = document.createElement('div');
            noSolutionsDiv.className = 'no-solutions-message';
            noSolutionsDiv.style.cssText = `
                padding: 40px 20px;
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                color: white;
                margin: 20px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                animation: fadeIn 0.5s ease-in;
            `;
            noSolutionsDiv.innerHTML = `
                <div style="font-size: 48px; margin-bottom: 10px;">🔍</div>
                <h3 style="margin: 0 0 10px 0; font-size: 24px;">No Solutions Found</h3>
                <p style="margin: 0; font-size: 16px; opacity: 0.9;">
                    The current piece configuration cannot be completed.<br>
                    Try removing some pieces or starting fresh!
                </p>
            `;
            solutionsElement.appendChild(noSolutionsDiv);
            
            // Scroll to show the message
            setTimeout(() => scrollToSolutions(), 100);
        }
        return;
    }

    const startNumber = reset ? 1 : (solutionsElement.querySelectorAll('.solution').length + 1);

    const frag = document.createDocumentFragment();
    for (let i = 0; i < solutions.length; i++) {
        frag.appendChild(buildSolutionDom(solutions[i], startNumber + i));
    }
    solutionsElement.appendChild(frag);
}

function buildSolutionDom(solution, number) {
    const wrapper = document.createElement('div');
    wrapper.className = 'solution';
    wrapper.style.cursor = 'pointer';

    const title = document.createElement('h4');
    title.textContent = `Solution ${number}`;
    wrapper.appendChild(title);

    const canvas = document.createElement('canvas');
    canvas.className = 'solution-canvas';
    canvas.width = 600;
    canvas.height = 220;
    wrapper.appendChild(canvas);

    // Backend now returns complete board including pre-placed pieces
    renderSolutionTo3D(canvas, solution.board);

    wrapper.addEventListener('click', () => {
        loadSolutionToPyramid(solution.board);
        showStatus(`Loaded Solution ${number}`, 'success');
    });

    return wrapper;
}

function renderSolutionTo3D(canvas, boardState) {
    if (!sharedSolutionRenderer) {
        const offscreenCanvas = document.createElement('canvas');
        sharedSolutionRenderer = new THREE.WebGLRenderer({
            canvas: offscreenCanvas,
            antialias: true,
            preserveDrawingBuffer: true
        });
    }

    const miniScene = new THREE.Scene();
    miniScene.background = new THREE.Color(0x1a1a2e);

    const miniCamera = new THREE.PerspectiveCamera(50, canvas.width / canvas.height, 0.1, 100);
    miniCamera.position.set(6, 10, 8);
    miniCamera.lookAt(2, 2, 2);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    miniScene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight.position.set(5, 10, 5);
    miniScene.add(directionalLight);

    for (const [key, pieceId] of Object.entries(boardState)) {
        if (!pieceId) continue;

        const parts = key.split(',').map(p => parseInt(p.trim()));
        if (parts.length !== 3) continue;
        const [x, y, z] = parts;

        const invertedZ = pyramidLevels - 1 - z;

        const pos = getPyramidPosition(x, y, invertedZ);
        const color = getColorForPieceId(pieceId);

        const geometry = new THREE.SphereGeometry(SPHERE_RADIUS * 0.85, 12, 12);
        const material = new THREE.MeshPhongMaterial({ color: color });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(pos.x, pos.y, pos.z);
        miniScene.add(sphere);
    }

    sharedSolutionRenderer.setSize(canvas.width, canvas.height);
    sharedSolutionRenderer.render(miniScene, miniCamera);

    const ctx = canvas.getContext('2d');
    ctx.drawImage(sharedSolutionRenderer.domElement, 0, 0);

    miniScene.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) {
            if (Array.isArray(object.material)) {
                object.material.forEach(material => material.dispose());
            } else {
                object.material.dispose();
            }
        }
    });
}

function updateSolutionsSummary() {
    const summaryElement = document.getElementById('solutionsSummary');
    const hintElement = document.getElementById('solutionsHint');

    if (solveState.solutionsReturned === 0 && solveState.totalSolutions === 0) {
        summaryElement.style.display = 'none';
        if (hintElement) hintElement.style.display = 'none';
        return;
    }

    summaryElement.style.display = 'block';
    if (hintElement) hintElement.style.display = 'block';
    summaryElement.className = `status ${solveState.timedOut ? 'error' : 'info'}`;

    let message = `<strong>${solveState.solutionsReturned} solutions</strong> shown.`;

    if (solveState.exhausted) {
        message += ' All solutions found.';
    } else if (solveState.timedOut) {
        message += ' Search stopped due to time limit. <strong>Scroll down to load more.</strong>';
    } else if (solveState.solutionsReturned > 0) {
        message += ' <strong>Scroll down (60%) to load more.</strong>';
    }

    summaryElement.innerHTML = message;
}

function resetSolutionsView() {
    const solutionsElement = document.getElementById('solutions');
    const summaryElement = document.getElementById('solutionsSummary');
    const hintElement = document.getElementById('solutionsHint');

    solutionStore.length = 0;
    if (solutionsElement) solutionsElement.innerHTML = '';
    if (summaryElement) summaryElement.style.display = 'none';
    if (hintElement) hintElement.style.display = 'none';

    solveState.lastBoardSnapshot = null;
    solveState.solutionsReturned = 0;
    solveState.totalSolutions = 0;
    solveState.timedOut = false;
    solveState.exhausted = false;
    solveState.displayedCount = 0;
    
    // Clear polling interval if active
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function stopSolving() {
    if (activeSolveController) {
        activeSolveController.abort();
    }
    // Stop the auto-polling interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function getPieceById(id) {
    return pieces.find(p => p.id === id);
}

function getColorForPieceId(pieceId) {
    const colorName = pieceColorMap.get(pieceId);
    return colorName || '#4facfe';
}

function showStatus(message, type) {
    const statusElement = document.getElementById('status');
    statusElement.innerHTML = `<div class="status ${type}">${message}</div>`;
    setTimeout(() => {
        statusElement.innerHTML = '';
    }, 5000);
}

function showLoading(show) {
    const loadingElement = document.getElementById('loading');
    const stopButton = document.getElementById('stopSolveButton');
    loadingElement.style.display = show ? 'block' : 'none';
    if (stopButton) {
        stopButton.style.display = show ? 'inline-block' : 'none';
    }
}

function stopSolving() {
    if (activeSolveController) {
        activeSolveController.abort();
    }
    isSolving = false;
    showLoading(false);
    showStatus('Solving cancelled', 'info');
}

document.addEventListener('DOMContentLoaded', () => {
    initScene();
    loadPieces();
    setupInfiniteScroll();
    setupKeyboardShortcuts3D();

    const input = document.getElementById('solveTimeLimit');
    if (input) {
        input.value = DEFAULT_SOLVE_TIME_SECONDS;
    }
    setCoordInputs3D(0, 0, 0);

    const levelsSelect = document.getElementById('levels');
    if (levelsSelect) {
        levelsSelect.addEventListener('change', (e) => {
            const newLevels = parseInt(e.target.value, 10);
            updatePyramidSize(newLevels);
        });
    }
});
