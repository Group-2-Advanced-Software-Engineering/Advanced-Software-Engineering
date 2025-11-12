const BOARD_WIDTH = 11;
const BOARD_HEIGHT = 5;
const DEFAULT_SAMPLE_LIMIT = 100;
const DEFAULT_SOLVE_TIME_SECONDS = 10;
const DEFAULT_SOLVE_TIME_MS = DEFAULT_SOLVE_TIME_SECONDS * 1000;

function getConfiguredBatchSize() {
    const sel = document.getElementById('batchSizeSelect');
    if (!sel) return DEFAULT_SAMPLE_LIMIT;
    const v = parseInt(sel.value, 10);
    if (!Number.isFinite(v) || v <= 0) return DEFAULT_SAMPLE_LIMIT;
    return v;
}
const USE_VIRTUAL_SCROLL = true;
const USE_CANVAS_RENDER = true;

let VIRTUAL_ITEM_HEIGHT = 160;
const VIRTUAL_BUFFER_ROWS = 6;

const solutionStore = [];
let virtualizationInitialized = false;
let solutionsVirtualContainer = null;
let lastVirtualRange = { start: 0, end: -1 };
let infiniteScrollArmed = true;
let lastScrollTopValue = 0;     
let lastScrollRatio = 0;      
let lastFetchTime = 0;          
let lastFetchCursor = 0;

const SOLUTION_CELL_SIZE = 20; 
const SOLUTION_FONT_RATIO = 0.55;
let virtualMeasured = false;

function createEmptyBoard() {
    return Array.from({ length: BOARD_HEIGHT }, () =>
        Array(BOARD_WIDTH).fill(0)
    );
}

function cloneBoardState(sourceBoard) {
    return sourceBoard.map(row => row.slice());
}

function getConfiguredTimeLimitMs() {
    const input = document.getElementById('solveTimeLimit');
    let seconds = Number.parseFloat(input ? input.value : '');
    if (!Number.isFinite(seconds) || seconds < 0) {
        seconds = DEFAULT_SOLVE_TIME_SECONDS;
    }
    if (seconds === 0) {
        return 0;
    }
    return Math.round(seconds * 1000);
}

let board = createEmptyBoard();
let selectedPiece = null;
let pieces = [];
let moveHistory = [];
let usedPieces = new Set();
let pieceColorMap = new Map();
let previewCells = [];
let lastHoverKey = null;
let activeSolveController = null;
let isSolving = false;

const solveState = {
    lastBoardSnapshot: null,
    solutionsReturned: 0,
    totalSolutions: 0,
    timedOut: false,
    exhausted: false,
    lastMaxTime: DEFAULT_SOLVE_TIME_MS,
    displayedCount: 0
};

document.addEventListener('DOMContentLoaded', () => {
    initializeBoard();
    loadPieces();
    const input = document.getElementById('solveTimeLimit');
    if (input) {
        input.value = DEFAULT_SOLVE_TIME_SECONDS;
    }
    solveState.lastMaxTime = getConfiguredTimeLimitMs();
    setupInfiniteScroll();
    if (USE_VIRTUAL_SCROLL) {
        initVirtualSolutions();
    }
});

function setupInfiniteScroll() {
    const container = document.getElementById('solutions');
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

    if (ratio < 0.5) {
        infiniteScrollArmed = true;
    }
    const crossedDownward = lastScrollRatio < 0.65 && ratio >= 0.65 && scrolledDown;
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

    if (!isSolving && ratio >= 0.85 && cooldownOk) {
        const currentCursor = solutionStore.length;
        if (currentCursor !== lastFetchCursor) {
            lastFetchTime = now;
            lastFetchCursor = currentCursor;
            window.loadMoreSolutions();
        }
    }
}

function initializeBoard() {
    const boardElement = document.getElementById('board');
    boardElement.innerHTML = '';

    for (let y = 0; y < BOARD_HEIGHT; y++) {
        for (let x = 0; x < BOARD_WIDTH; x++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.x = x;
            cell.dataset.y = y;
            cell.addEventListener('click', () => handleCellClick(x, y));
            cell.addEventListener('mouseenter', () => handleCellEnter(x, y));
            cell.addEventListener('mouseleave', () => handleCellLeave(x, y));
            boardElement.appendChild(cell);
        }
    }

    updateBoardDisplay();
}

function handleCellClick(x, y) {
    if (!selectedPiece) {
        showStatus('Select a piece before placing it on the board.', 'info');
        return;
    }

    if (canPlacePiece(x, y)) {
        placePiece(x, y);
    } else {
        showStatus('This piece cannot be placed there.', 'error');
    }
}

function handleCellEnter(x, y) {
    if (!selectedPiece) {
        clearPreview();
        return;
    }

    const key = `${x},${y}`;
    if (key === lastHoverKey && previewCells.length > 0) {
        return;
    }

    lastHoverKey = key;
    clearPreview(false);

    const preview = buildPreview(x, y);
    if (preview.cells.length === 0) {
        return;
    }

    const color = getColorForPieceId(selectedPiece.id);
    previewCells = preview.cells;

    preview.cells.forEach((cellData, index) => {
        const cellElement = getBoardCellElement(cellData.x, cellData.y);
        if (!cellElement) {
            return;
        }

        if (preview.valid) {
            cellElement.classList.add('preview-valid');
            cellElement.style.background = applyAlpha(color, index === 0 ? 0.9 : 0.65);
            cellElement.style.color = '#fff';
        } else {
            cellElement.classList.add('preview-invalid');
            cellElement.style.background = 'rgba(220, 53, 69, 0.35)';
            cellElement.style.color = '#dc3545';
        }

        if (index === 0) {
            cellElement.classList.add('preview-anchor');
        }
    });
}

function handleCellLeave() {
    clearPreview();
}

function clearPreview(refresh = true) {
    if (previewCells.length === 0 && !lastHoverKey) {
        return;
    }

    previewCells.forEach(({ x, y }) => {
        const cellElement = getBoardCellElement(x, y);
        if (!cellElement) {
            return;
        }
        cellElement.classList.remove('preview-valid', 'preview-invalid', 'preview-anchor');
    });

    previewCells = [];
    lastHoverKey = null;

    if (refresh) {
        updateBoardDisplay();
    }
}

function getBoardCellElement(x, y) {
    return document.querySelector(`.cell[data-x="${x}"][data-y="${y}"]`);
}

function buildPreview(x, y) {
    const cells = [];
    let valid = true;

    for (const [dx, dy] of selectedPiece.cells) {
        const nx = x + dx;
        const ny = y + dy;

        if (nx < 0 || nx >= BOARD_WIDTH || ny < 0 || ny >= BOARD_HEIGHT) {
            valid = false;
            continue;
        }

        if (board[ny][nx] !== 0) {
            valid = false;
        }

        cells.push({ x: nx, y: ny });
    }

    if (cells.length !== selectedPiece.cells.length) {
        valid = false;
    }

    return { cells, valid };
}

function canPlacePiece(x, y) {
    if (!selectedPiece) return false;

    for (const [dx, dy] of selectedPiece.cells) {
        const nx = x + dx;
        const ny = y + dy;

        if (nx < 0 || nx >= BOARD_WIDTH || ny < 0 || ny >= BOARD_HEIGHT) {
            return false;
        }

        if (board[ny][nx] !== 0) {
            return false;
        }
    }

    return true;
}

function placePiece(x, y) {
    if (!selectedPiece) return;

    clearPreview();

    const placedCells = selectedPiece.cells.map(([dx, dy]) => [x + dx, y + dy]);

    placedCells.forEach(([cx, cy]) => {
        board[cy][cx] = selectedPiece.id;
    });

    moveHistory.push({
        pieceId: selectedPiece.id,
        cells: placedCells
    });

    usedPieces.add(selectedPiece.id);
    const placedName = selectedPiece.name;
    selectedPiece = null;

    updateBoardDisplay();
    updatePiecesDisplay();
    updatePieceInfo();
    showStatus(`Placed ${placedName}.`, 'success');
}

function undoLastMove() {
    if (moveHistory.length === 0) {
        showStatus('No moves to undo.', 'info');
        return;
    }

    clearPreview();

    const lastMove = moveHistory.pop();

    lastMove.cells.forEach(([x, y]) => {
        board[y][x] = 0;
    });

    usedPieces.delete(lastMove.pieceId);

    updateBoardDisplay();
    updatePiecesDisplay();
    updatePieceInfo();

    const piece = getPieceById(lastMove.pieceId);
    const name = piece ? piece.name : `#${lastMove.pieceId}`;
    showStatus(`Undid placement of ${name}.`, 'info');
}

function updateBoardDisplay() {
    const cells = document.querySelectorAll('.cell');

    cells.forEach(cell => {
        const x = Number(cell.dataset.x);
        const y = Number(cell.dataset.y);
        const value = board[y][x];

        if (value === 0) {
            cell.textContent = '';
            cell.className = 'cell';
            cell.style.background = '#fff';
            cell.style.color = '#333';
        } else {
            cell.textContent = value;
            cell.className = 'cell occupied';
            const color = getColorForPieceId(value);
            cell.style.background = color;
            cell.style.color = '#fff';
        }
    });
}

window.loadPieces = function() {
    if (isSolving) {
        stopSolving();
    }

    fetch('/api/pieces')
        .then(response => response.json())
        .then(data => {
            pieces = data.pieces.map(piece => ({
                ...piece,
                cells: piece.shapeData.map(([x, y]) => [x, y])
            }));
            pieceColorMap = new Map(pieces.map(piece => [piece.id, piece.color]));
            selectedPiece = null;
            clearPreview(false);
            displayPieces();
            updatePiecesDisplay();
            updatePieceInfo();
        })
        .catch(error => {
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

        const preview = document.createElement('div');
        preview.className = 'piece-preview';

        const bounds = getPieceBounds(piece.cells);
        preview.style.gridTemplateColumns = `repeat(${bounds.width}, 12px)`;
        preview.style.gridTemplateRows = `repeat(${bounds.height}, 12px)`;

        const shape = new Set(piece.cells.map(([x, y]) => `${x},${y}`));

        for (let y = 0; y < bounds.height; y++) {
            for (let x = 0; x < bounds.width; x++) {
                const cell = document.createElement('div');
                cell.className = 'piece-cell';
                if (shape.has(`${x},${y}`)) {
                    cell.style.background = getColorValue(piece.color);
                }
                preview.appendChild(cell);
            }
        }

        pieceElement.innerHTML = `
            <div>${piece.name}</div>
            <div>ID: ${piece.id}</div>
        `;
        pieceElement.appendChild(preview);
        piecesElement.appendChild(pieceElement);
    });
}

function selectPiece(piece) {
    if (usedPieces.has(piece.id)) {
        showStatus('This piece has already been placed.', 'error');
        return;
    }

    selectedPiece = {
        id: piece.id,
        name: piece.name,
        color: piece.color,
        baseCells: piece.cells.map(([x, y]) => [x, y]),
        rotation: 0,
        flipped: false,
        cells: []
    };

    updateSelectedPieceCells();

    updatePiecesDisplay();
    updatePieceInfo();
    clearPreview();
    showStatus(`Selected ${piece.name}.`, 'info');
}

function updateSelectedPieceCells() {
    if (!selectedPiece) return;
    selectedPiece.cells = applyOrientation(
        selectedPiece.baseCells,
        selectedPiece.rotation,
        selectedPiece.flipped
    );
    renderSelectedPiecePreview(document.getElementById('selectedPiecePreview'));
}

window.rotateSelectedPiece = function() {
    if (!selectedPiece) {
        showStatus('No piece selected.', 'error');
        return;
    }

    clearPreview();
    selectedPiece.rotation = (selectedPiece.rotation + 90) % 360;
    updateSelectedPieceCells();
    updatePieceInfo();
    updatePiecesDisplay();
    showStatus(`Rotated ${selectedPiece.name} to ${selectedPiece.rotation} deg.`, 'info');
}

window.flipSelectedPiece = function() {
    if (!selectedPiece) {
        showStatus('No piece selected.', 'error');
        return;
    }

    clearPreview();
    selectedPiece.flipped = !selectedPiece.flipped;
    updateSelectedPieceCells();
    updatePieceInfo();
    updatePiecesDisplay();
    showStatus(`${selectedPiece.flipped ? 'Flipped' : 'Unflipped'} ${selectedPiece.name}.`, 'info');
}

function updatePieceInfo() {
    const pieceInfo = document.getElementById('pieceInfo');
    const pieceName = document.getElementById('pieceName');
    const pieceRotationSpan = document.getElementById('pieceRotation');
    const pieceFlippedSpan = document.getElementById('pieceFlipped');
    const preview = document.getElementById('selectedPiecePreview');

    if (selectedPiece) {
        pieceName.textContent = `${selectedPiece.name} (#${selectedPiece.id})`;
        pieceRotationSpan.textContent = `${selectedPiece.rotation} deg`;
        pieceFlippedSpan.textContent = selectedPiece.flipped ? 'Yes' : 'No';
        renderSelectedPiecePreview(preview);
        pieceInfo.style.display = 'block';
    } else {
        pieceInfo.style.display = 'none';
        if (preview) {
            preview.innerHTML = '';
        }
    }
}

function renderSelectedPiecePreview(previewElement) {
    if (!previewElement) return;
    previewElement.innerHTML = '';

    if (!selectedPiece) {
        return;
    }

    const bounds = getPieceBounds(selectedPiece.cells);
    previewElement.style.gridTemplateColumns = `repeat(${bounds.width}, 14px)`;
    previewElement.style.gridTemplateRows = `repeat(${bounds.height}, 14px)`;

    const cellSet = new Set(selectedPiece.cells.map(([x, y]) => `${x},${y}`));

    for (let y = 0; y < bounds.height; y++) {
        for (let x = 0; x < bounds.width; x++) {
            const cell = document.createElement('div');
            cell.className = 'piece-cell';
            if (cellSet.has(`${x},${y}`)) {
                cell.style.background = getColorForPieceId(selectedPiece.id);
            } else {
                cell.style.background = 'transparent';
            }
            previewElement.appendChild(cell);
        }
    }
}

function updatePiecesDisplay() {
    const pieceElements = document.querySelectorAll('.piece');

    pieceElements.forEach(element => {
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

window.solvePuzzle = function() {
    clearPreview();
    const maxTime = getConfiguredTimeLimitMs();
    solveState.lastMaxTime = maxTime;
    requestSolve({
        action: 'init',
        partialBoard: cloneBoardState(board),
        batchSize: getConfiguredBatchSize(),
        maxTime
    });
}

window.solveEmpty = function() {
    clearPreview();
    const maxTime = getConfiguredTimeLimitMs();
    solveState.lastMaxTime = maxTime;
    requestSolve({
        action: 'init',
        partialBoard: null,
        batchSize: getConfiguredBatchSize(),
        maxTime
    });
}

async function requestSolve({ action = 'init', partialBoard, batchSize = DEFAULT_SAMPLE_LIMIT, maxTime }) {
    if (isSolving && activeSolveController) {
        activeSolveController.abort();
    }

    if (action === 'init') {
        solveState.exhausted = false;
        solveState.timedOut = false;
        solveState.solutionsReturned = 0;
        solveState.totalSolutions = 0;
        solveState.displayedCount = 0;
        infiniteScrollArmed = true;
        lastScrollTopValue = 0;
    lastScrollRatio = 0;
    lastFetchTime = 0;
    lastFetchCursor = 0;
        if (USE_VIRTUAL_SCROLL) {
            ensureVirtualContainer();
            solutionStore.length = 0;
            lastVirtualRange = { start: 0, end: -1 };
            virtualMeasured = false;
            if (solutionsVirtualContainer) {
                solutionsVirtualContainer.innerHTML = '';
                solutionsVirtualContainer.style.height = '0px';
            }
        }
        const cont = document.getElementById('solutions');
        if (cont) cont.scrollTop = 0;
    }

    const controller = new AbortController();
    activeSolveController = controller;
    isSolving = true;
    showLoading(true);

    const solveUrl = `api/solve/${solveId}/`;

    try {
        const payload = {
            action,
            batchSize,
            maxTime: maxTime ?? DEFAULT_SOLVE_TIME_MS
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
                if(data.timedOut) {
                    showStatus('Search stopped due to time limit. Scroll the solutions list to load more.', 'info');
                } else if (data.solutionsReturned > 0) {
                    showStatus(data.message || 'Solution found!', 'success');
                } else {
                    showStatus(data.message || 'No solution found.', 'info');
                }
            } else {
                throw new Error(data.error || 'Solver request failed.');
            }
    } finally {
        if (activeSolveController === controller) {
            activeSolveController = null;
        }
        isSolving = false;
        showLoading(false);
        updateSolutionsSummary();
        const container = document.getElementById('solutions');
        if (container && !solveState.exhausted) {
            window.requestAnimationFrame(() => maybeTriggerLoadMore(container));
        }
    }
}

function handleSolveSuccess(data, payload) {
    const solutions = data.solutions || [];
    const isSameBoard = boardsEqual(payload.partialBoard ?? null, solveState.lastBoardSnapshot ?? null);
    const isInit = payload.action === 'init' || !isSameBoard;
    displaySolutions(solutions, { reset: isInit, startNumber: isInit ? 1 : (solveState.displayedCount + 1) });
    showStatus(data.message, 'success');

    solveState.lastBoardSnapshot = payload.partialBoard ? cloneBoardState(payload.partialBoard) : null;
    if (USE_VIRTUAL_SCROLL) {
        solveState.displayedCount = solutionStore.length;
        solveState.solutionsReturned = solutionStore.length;
    } else {
        solveState.displayedCount = (isInit ? 0 : solveState.displayedCount) + (data.solutionsReturned ?? solutions.length);
        solveState.solutionsReturned = solveState.displayedCount;
    }
    solveState.totalSolutions = data.solutionCount ?? solveState.totalSolutions;
    solveState.timedOut = Boolean(data.timedOut);
    solveState.exhausted = Boolean(data.exhausted);
    solveState.lastMaxTime = payload.maxTime;

    updateSolutionsSummary();
}

 function handleSolvePartial(data, payload) {
    const partial = data.partialResults || { solutions: [], totalSolutions: 0 };
    const isSameBoard = boardsEqual(payload.partialBoard ?? null, solveState.lastBoardSnapshot ?? null);
    displaySolutions(partial.solutions || [], { reset: !isSameBoard });

    solveState.lastBoardSnapshot = payload.partialBoard ? cloneBoardState(payload.partialBoard) : null;
    solveState.sampleLimit = payload.sampleLimit;
    solveState.solutionsReturned = partial.solutions ? partial.solutions.length : 0;
    solveState.totalSolutions = partial.totalSolutions || solveState.solutionsReturned;
    solveState.timedOut = true;
    solveState.limitReached = false;
    solveState.lastMaxTime = payload.maxTime;
    solveState.displayedCount = Math.max(solveState.displayedCount || 0, solveState.solutionsReturned);

    updateSolutionsSummary();
}

window.loadMoreSolutions = function() {
    if (isSolving) {
        showStatus('A search is already in progress. Please wait.', 'info');
        return;
    }

    const lastBoard = solveState.lastBoardSnapshot
        ? cloneBoardState(solveState.lastBoardSnapshot)
        : null;

    requestSolve({
        action: 'next',
        partialBoard: lastBoard,
        batchSize: getConfiguredBatchSize(),
        maxTime: solveState.lastMaxTime ?? DEFAULT_SOLVE_TIME_MS
    });

}

window.stopSolving = function() {
    if (activeSolveController) {
        activeSolveController.abort();
    }
}

window.clearBoard = function() {
    if (isSolving) {
        stopSolving();
    }
    board = createEmptyBoard();
    moveHistory = [];
    usedPieces.clear();
    selectedPiece = null;
    clearPreview(false);
    updateBoardDisplay();
    updatePiecesDisplay();
    updatePieceInfo();
    resetSolutionsView();
    showStatus('Board cleared.', 'info');
}

window.undoLastMove = undoLastMove;

function resetSolutionsView() {
    const solutionsElement = document.getElementById('solutions');
    const summaryElement = document.getElementById('solutionsSummary');

    if (USE_VIRTUAL_SCROLL) {
        ensureVirtualContainer();
        solutionStore.length = 0;
        lastVirtualRange = { start: 0, end: -1 };
        virtualMeasured = false;
        if (solutionsVirtualContainer) {
            solutionsVirtualContainer.innerHTML = '';
            solutionsVirtualContainer.style.height = '0px';
        }
    } else {
        solutionsElement.innerHTML = '';
    }
    summaryElement.style.display = 'none';

    solveState.lastBoardSnapshot = null;
    solveState.solutionsReturned = 0;
    solveState.totalSolutions = 0;
    solveState.timedOut = false;
    solveState.limitReached = false;
    solveState.lastMaxTime = getConfiguredTimeLimitMs();
    solveState.displayedCount = 0;
}

function displaySolutions(solutions, { reset = false, startNumber = 1 } = {}) {
    const solutionsElement = document.getElementById('solutions');
    if (!solutionsElement) return;
    if (USE_VIRTUAL_SCROLL) {
        if (reset) {
            solutionStore.length = 0;
            lastVirtualRange = { start: 0, end: -1 };
            ensureVirtualContainer();
            virtualMeasured = false;
        }
        for (const sol of solutions) {
            solutionStore.push(sol);
        }
        refreshVirtualSolutions();
        return;
    }

    if (reset) {
        solutionsElement.innerHTML = '';
        solveState.displayedCount = 0;
    }
    if (!solutions || solutions.length === 0) {
        if (solutionsElement.querySelectorAll('.solution').length === 0) {
            solutionsElement.innerHTML = '<p>No solutions found.</p>';
        }
        return;
    }
    const frag = document.createDocumentFragment();
    for (let i = 0; i < solutions.length; i++) {
        frag.appendChild(buildSolutionDom(solutions[i], startNumber + i));
    }
    solutionsElement.appendChild(frag);
}

function buildSolutionDom(solution, number) {
    const wrapper = document.createElement('div');
    wrapper.className = 'solution';
    const title = document.createElement('h4');
    title.textContent = `Solution ${number}`;
    wrapper.appendChild(title);
    if (USE_CANVAS_RENDER) {
        const canvas = document.createElement('canvas');
        canvas.className = 'solution-canvas';
        drawBoardToCanvas(canvas, solution.board);
        wrapper.appendChild(canvas);
        return wrapper;
    }
    const boardElement = document.createElement('div');
    boardElement.className = 'solution-board';
    for (let y = 0; y < BOARD_HEIGHT; y++) {
        for (let x = 0; x < BOARD_WIDTH; x++) {
            const cell = document.createElement('div');
            cell.className = 'solution-cell';
            const value = solution.board[y][x];
            if (value) {
                cell.textContent = value;
                const color = getColorForPieceId(value);
                cell.style.background = color;
                cell.style.color = '#fff';
            }
            boardElement.appendChild(cell);
        }
    }
    wrapper.appendChild(boardElement);
    return wrapper;
}

function drawBoardToCanvas(canvas, board, cellSize = SOLUTION_CELL_SIZE) {
    const rows = board.length;
    const cols = board[0].length;
    const dpr = window.devicePixelRatio || 1;
    const width = cols * cellSize;
    const height = rows * cellSize;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const v = board[y][x];
            if (!v) continue;
            const color = getColorForPieceId(v);
            ctx.fillStyle = color;
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
    }
    const fontPx = Math.max(10, Math.round(cellSize * SOLUTION_FONT_RATIO));
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `${fontPx}px Segoe UI, system-ui, -apple-system, sans-serif`;
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const v = board[y][x];
            if (!v) continue;
            const color = getColorForPieceId(v);
            const [r, g, b] = hexToRgb(color);
            const luminance = r === null ? 0 : (0.2126 * r + 0.7152 * g + 0.0722 * b);
            const lightBg = r === null ? false : luminance > 160;
            ctx.lineWidth = Math.max(1, Math.floor(fontPx / 10));
            ctx.strokeStyle = lightBg ? 'rgba(0,0,0,0.65)' : 'rgba(255,255,255,0.65)';
            ctx.fillStyle = lightBg ? '#000' : '#fff';
            const cx = x * cellSize + cellSize / 2;
            const cy = y * cellSize + cellSize / 2;
            const text = String(v);
            try { ctx.strokeText(text, cx, cy); } catch (_) {}
            ctx.fillText(text, cx, cy);
        }
    }
}

function hexToRgb(hex) {
    if (!hex || typeof hex !== 'string') return [null, null, null];
    if (!hex.startsWith('#')) {
        return [null, null, null];
    }
    const clean = hex.replace('#', '');
    const full = clean.length === 3
        ? clean.split('').map(c => c + c).join('')
        : clean;
    const num = parseInt(full, 16);
    const r = (num >> 16) & 255;
    const g = (num >> 8) & 255;
    const b = num & 255;
    return [r, g, b];
}

function initVirtualSolutions() {
    const container = document.getElementById('solutions');
    if (!container) return;
    container.style.position = 'relative';
    container.innerHTML = '';
    solutionsVirtualContainer = document.createElement('div');
    solutionsVirtualContainer.style.position = 'relative';
    solutionsVirtualContainer.style.width = '100%';
    container.appendChild(solutionsVirtualContainer);
    virtualizationInitialized = true;
    container.addEventListener('scroll', () => refreshVirtualSolutions(), { passive: true });
}

function ensureVirtualContainer() {
    const container = document.getElementById('solutions');
    if (!container) return false;
    container.style.position = 'relative';
    if (!solutionsVirtualContainer || solutionsVirtualContainer.parentElement !== container) {
        container.innerHTML = '';
        solutionsVirtualContainer = document.createElement('div');
        solutionsVirtualContainer.style.position = 'relative';
        solutionsVirtualContainer.style.width = '100%';
        container.appendChild(solutionsVirtualContainer);
    }
    virtualizationInitialized = true;
    return true;
}

function refreshVirtualSolutions() {
    if (!virtualizationInitialized) return;
    ensureVirtualContainer();
    const container = document.getElementById('solutions');
    if (!container) return;
    const total = solutionStore.length;
    if (total === 0) {
        solutionsVirtualContainer.innerHTML = '<p>No solutions yet.</p>';
        return;
    }
    if (!virtualMeasured) {
        const temp = buildSolutionDom(solutionStore[0], 1);
        temp.style.position = 'absolute';
        temp.style.visibility = 'hidden';
        temp.style.top = '0';
        solutionsVirtualContainer.appendChild(temp);
        requestAnimationFrame(() => {
            VIRTUAL_ITEM_HEIGHT = temp.getBoundingClientRect().height + 12;
            solutionsVirtualContainer.removeChild(temp);
            virtualMeasured = true;
            applyVirtualMetrics(total, container);
            renderVirtualWindow(container, total);
            maybeTriggerLoadMore(container);
        });
        return;
    }
    applyVirtualMetrics(total, container);
    renderVirtualWindow(container, total);
    if (solutionStore.length > 0 && solutionsVirtualContainer.children.length === 0) {
        console.warn('[VirtualSolutions] Empty window after render; falling back to non-virtual DOM rendering.');
        const limit = Math.min(solutionStore.length, 500);
        const frag = document.createDocumentFragment();
        for (let i = 0; i < limit; i++) {
            frag.appendChild(buildSolutionDom(solutionStore[i], i + 1));
        }
        solutionsVirtualContainer.appendChild(frag);
    }
}

function applyVirtualMetrics(total, container) {
    solutionsVirtualContainer.style.height = (total * VIRTUAL_ITEM_HEIGHT) + 'px';
}

function renderVirtualWindow(container, total) {
    const scrollTop = container.scrollTop;
    const viewHeight = container.clientHeight;
    const startIndex = Math.max(0, Math.floor(scrollTop / VIRTUAL_ITEM_HEIGHT) - VIRTUAL_BUFFER_ROWS);
    const endIndex = Math.min(total - 1, Math.ceil((scrollTop + viewHeight) / VIRTUAL_ITEM_HEIGHT) + VIRTUAL_BUFFER_ROWS);
    if (startIndex === lastVirtualRange.start && endIndex === lastVirtualRange.end) {
        return;
    }
    lastVirtualRange = { start: startIndex, end: endIndex };
    solutionsVirtualContainer.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (let i = startIndex; i <= endIndex; i++) {
        const sol = solutionStore[i];
        const node = buildSolutionDom(sol, i + 1);
        node.style.position = 'absolute';
        node.style.top = (i * VIRTUAL_ITEM_HEIGHT) + 'px';
        node.style.left = '0';
        node.style.right = '0';
        frag.appendChild(node);
    }
    solutionsVirtualContainer.appendChild(frag);
}

function boardsEqual(a, b) {
    if (a === b) return true;
    if (!a || !b) return false;
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    for (let y = 0; y < a.length; y++) {
        if (!Array.isArray(a[y]) || !Array.isArray(b[y]) || a[y].length !== b[y].length) {
            return false;
        }
        for (let x = 0; x < a[y].length; x++) {
            if (a[y][x] !== b[y][x]) return false;
        }
    }
    return true;
}

function updateSolutionsSummary(extraMessage) {
    const summaryElement = document.getElementById('solutionsSummary');

    if (solveState.solutionsReturned === 0 && solveState.totalSolutions === 0) {
        summaryElement.style.display = 'none';
        return;
    }

    const total = solveState.totalSolutions;
    const returned = solveState.solutionsReturned;
    const timedOut = solveState.timedOut;
    const exhausted = solveState.exhausted;

    summaryElement.style.display = 'block';
    summaryElement.className = `status ${timedOut ? 'error' : 'info'}`;

    let message = `Showing <strong>${returned}</strong> solutions.`;

    if (timedOut) {
        message += ' Search stopped due to time limit. Scroll inside the solutions list to continue the search.';
    } else if (exhausted) {
        message += ' All solutions found.';
    } else {
        message += ' More solutions available — scroll the solutions list to load more.';
    }

    if (extraMessage) {
        message += ` ${extraMessage}`;
    }

    summaryElement.innerHTML = message;
}

function showStatus(message, type) {
    const statusElement = document.getElementById('status');
    statusElement.innerHTML = `<div class="status ${type}">${message}</div>`;
}

function showLoading(show) {
    const loadingElement = document.getElementById('loading');
    const stopButton = document.getElementById('stopSolveButton');
    loadingElement.style.display = show ? 'block' : 'none';
    if (stopButton) {
        stopButton.style.display = show ? 'inline-block' : 'none';
        stopButton.disabled = !show;
    }
}

function normalizeCells(cells) {
    const minX = Math.min(...cells.map(([x]) => x));
    const minY = Math.min(...cells.map(([, y]) => y));
    return cells
        .map(([x, y]) => [x - minX, y - minY])
        .sort(([ax, ay], [bx, by]) => (ax - bx) || (ay - by));
}

function applyOrientation(baseCells, rotationDegrees, flipped) {
    const steps = ((rotationDegrees / 90) % 4 + 4) % 4;
    const transformed = baseCells.map(([x, y]) => {
        let tx = flipped ? -x : x;
        let ty = flipped ? y : y;
        for (let i = 0; i < steps; i++) {
            const nx = ty;
            const ny = -tx;
            tx = nx;
            ty = ny;
        }
        return [tx, ty];
    });
    return normalizeCells(transformed);
}

function getPieceBounds(cells) {
    const maxX = Math.max(...cells.map(([x]) => x));
    const maxY = Math.max(...cells.map(([, y]) => y));
    return {
        width: maxX + 1,
        height: maxY + 1
    };
}

function getPieceById(id) {
    return pieces.find(piece => piece.id === id);
}

function getColorForPieceId(pieceId) {
    const colorName = pieceColorMap.get(pieceId);
    return getColorValue(colorName);
}

function applyAlpha(color, alpha) {
    const baseColor = getColorValue(color);
    if (!baseColor.startsWith('#')) {
        return baseColor;
    }

    const hex = baseColor.replace('#', '');
    const bigint = parseInt(hex, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function getColorValue(colorName) {
    if (!colorName) {
        return '#4facfe';
    }

    const normalized = colorName.toString().toLowerCase().trim();
    if (normalized.startsWith('#')) {
        return normalized;
    }

    const palette = {
        red: '#ff595e',
        pink: '#ff85c2',
        lightpink: '#ffbfd3',
        blue: '#4361ee',
        yellow: '#ffd22b',
        purple: '#9b5de5',
        darkpurple: '#5a189a',
        lightgreen: '#70e000',
        orange: '#ff8f00',
        darkgreen: '#2b9348',
        lightblue: '#4cc9f0',

        crimson: '#ef476f',
        goldenrod: '#f9c74f',
        lightseagreen: '#06d6a0',
        royalblue: '#118ab2',
        mediumseagreen: '#43aa8b',
        deeppink: '#ff4d6d',
        teal: '#00b4d8',
        tomato: '#ff6f59',
        dodgerblue: '#3a86ff',
        sienna: '#bc6c25'
    };

    return palette[normalized] || colorName;
}