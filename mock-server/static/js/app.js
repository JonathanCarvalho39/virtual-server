let editor = null;
let currentFile = null;
let routesData = [];
let treeData = {};
let selectedRoute = null;
let selectedContextPath = null;
let contextPath = '';
let selectedFolderPath = null;
let expandedFolders = new Set();
let serverBaseUrl = 'http://localhost:8000';
let serverRunning = false;

const METHOD_ICONS = {
    GET: 'fa-arrow-down',
    POST: 'fa-arrow-up',
    PUT: 'fa-pen',
    PATCH: 'fa-pen',
    DELETE: 'fa-trash',
    HEAD: 'fa-headphones',
    OPTIONS: 'fa-circle-question',
};

function init() {
    setupTabs();
    setupButtons();
    setupModal();
    setupContextMenu();
    initMonaco();
    fetch('/admin/logs/clear', { method: 'POST' });
    loadRoutes();
    log('info', 'Interface inicializada');
}

function setupTabs() {
}

function switchTab(tab) {
    const editorTab = document.getElementById('editor-tab');
    const referenceTab = document.getElementById('reference-tab');
    const editorContainer = document.getElementById('editor-container');
    const referenceContainer = document.getElementById('reference-container');

    if (tab === 'editor') {
        editorTab.classList.add('active');
        referenceTab.classList.remove('active');
        editorContainer.classList.remove('hidden');
        referenceContainer.classList.add('hidden');
    } else {
        referenceTab.classList.add('active');
        editorTab.classList.remove('active');
        referenceContainer.classList.remove('hidden');
        editorContainer.classList.add('hidden');
    }
}

function setupButtons() {
    document.getElementById('btn-start').addEventListener('click', startServer);
    document.getElementById('btn-stop').addEventListener('click', stopServer);
    document.getElementById('btn-clear-logs').addEventListener('click', clearLogs);
    document.getElementById('btn-add-folder').addEventListener('click', () => showModal('folder'));
    document.getElementById('btn-add-method').addEventListener('click', () => showModal('method'));
    document.getElementById('btn-add-file').addEventListener('click', () => showModal('file'));
    document.getElementById('btn-save').addEventListener('click', saveCurrentFile);
    setupResizeHandles();
}

function setupResizeHandles() {
    document.querySelectorAll('.resize-handle').forEach(handle => {
        let startPos, startSize, target, isHorizontal;

        const onMouseDown = (e) => {
            e.preventDefault();
            isHorizontal = handle.classList.contains('resize-h');
            const targetId = handle.dataset.target;

            if (targetId === 'sidebar-width') {
                target = document.getElementById('sidebar');
                startPos = e.clientX;
                startSize = target.offsetWidth;
            } else if (targetId === 'routes-height') {
                target = document.getElementById('panel-routes');
                startPos = e.clientY;
                startSize = target.offsetHeight;
            } else if (targetId === 'logs-height') {
                target = document.getElementById('log-panel');
                startPos = e.clientY;
                startSize = target.offsetHeight;
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            document.body.style.cursor = isHorizontal ? 'col-resize' : 'row-resize';
            document.body.style.userSelect = 'none';
        };

        const onMouseMove = (e) => {
            if (!target) return;
            const delta = isHorizontal ? (e.clientX - startPos) : (startPos - e.clientY);
            const newSize = startSize + delta;
            if (isHorizontal) {
                target.style.width = Math.max(150, newSize) + 'px';
            } else {
                target.style.height = Math.max(80, newSize) + 'px';
            }
            if (window.editor) editor.layout();
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            target = null;
        };

        handle.addEventListener('mousedown', onMouseDown);
    });
}

function togglePanel(name) {
    const panels = {
        tree: { panel: document.getElementById('panel-tree'), icon: document.getElementById('icon-tree') },
        routes: { panel: document.getElementById('panel-routes'), icon: document.getElementById('icon-routes') },
        logs: { panel: document.getElementById('log-panel'), icon: document.getElementById('icon-logs') },
    };

    const p = panels[name];
    if (!p) return;

    const content = p.panel.querySelector('.panel-content') || p.panel.querySelector('.log-content');
    const isCollapsed = p.panel.classList.toggle('collapsed');
    const iconBtn = p.icon.parentElement;

    if (isCollapsed) {
        content.classList.add('hidden');
        iconBtn.classList.add('collapsed');
    } else {
        content.classList.remove('hidden');
        content.style.maxHeight = content.scrollHeight + 'px';
        requestAnimationFrame(() => {
            content.style.maxHeight = '';
        });
        iconBtn.classList.remove('collapsed');
    }

    const resizeHandle = name === 'logs'
        ? document.getElementById('resize-logs')
        : p.panel.nextElementSibling;

    if (resizeHandle && resizeHandle.classList.contains('resize-handle')) {
        resizeHandle.style.display = isCollapsed ? 'none' : '';
    }

    if (window.editor) {
        setTimeout(() => editor.layout(), 300);
    }
}

function setupModal() {
    const overlay = document.getElementById('modal-overlay');
    const closeBtn = document.getElementById('modal-close');
    const cancelBtn = document.getElementById('modal-cancel');
    const confirmBtn = document.getElementById('modal-confirm');

    closeBtn.addEventListener('click', hideModal);
    cancelBtn.addEventListener('click', hideModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) hideModal();
    });

    confirmBtn.addEventListener('click', handleModalConfirm);

    document.getElementById('modal-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleModalConfirm();
        if (e.key === 'Escape') hideModal();
    });
}

function setupContextMenu() {
    const ctxMenu = document.getElementById('context-menu');
    const ctxRename = document.getElementById('ctx-rename');
    const ctxDelete = document.getElementById('ctx-delete');
    const ctxCurl = document.getElementById('ctx-curl');

    document.addEventListener('click', () => hideContextMenu());

    ctxRename.addEventListener('click', () => {
        if (selectedContextPath) {
            showRenameModal(selectedContextPath);
        }
        hideContextMenu();
    });

    ctxDelete.addEventListener('click', async () => {
        if (selectedContextPath) {
            await deleteItem(selectedContextPath);
        }
        hideContextMenu();
    });

    ctxCurl.addEventListener('click', () => {
        if (window._curlMethod && window._curlPath) {
            copyCurl(window._curlMethod, window._curlPath, window._curlScenarioData);
        }
        hideContextMenu();
    });
}

function showModal(type, parentPath) {
    const overlay = document.getElementById('modal-overlay');
    const title = document.getElementById('modal-title');
    const label = document.getElementById('modal-label');
    const input = document.getElementById('modal-input');
    const hint = document.getElementById('modal-hint');
    const selectGroup = document.getElementById('modal-select-group');
    const confirmBtn = document.getElementById('modal-confirm');

    selectGroup.classList.add('hidden');
    input.value = '';
    contextPath = parentPath || contextPath || '';

    if (type === 'folder') {
        title.textContent = 'Nova Pasta';
        label.textContent = 'Nome da pasta:';
        input.placeholder = 'ex: v1';
        hint.textContent = contextPath ? `Dentro de: ${contextPath}` : 'Pasta raiz da API';
        confirmBtn.dataset.type = 'folder';
    } else if (type === 'method') {
        title.textContent = 'Novo Método HTTP';
        label.textContent = 'Criar método em:';
        input.value = contextPath || '/api';
        input.placeholder = '/api/v1/usuarios';
        hint.textContent = 'Caminho da pasta onde o método será criado';
        selectGroup.classList.remove('hidden');
        confirmBtn.dataset.type = 'method';
    } else if (type === 'file') {
        title.textContent = 'Novo Cenário';
        label.textContent = 'Nome do arquivo:';
        input.placeholder = 'sucesso.json';
        hint.textContent = contextPath ? `Dentro de: ${contextPath}` : 'Selecione uma pasta primeiro';
        confirmBtn.dataset.type = 'file';
    }

    overlay.classList.remove('hidden');
    input.focus();

    if (type !== 'method') {
        input.select();
    }
}

function hideModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
}

function showRenameModal(path) {
    const overlay = document.getElementById('modal-overlay');
    const title = document.getElementById('modal-title');
    const label = document.getElementById('modal-label');
    const input = document.getElementById('modal-input');
    const hint = document.getElementById('modal-hint');
    const selectGroup = document.getElementById('modal-select-group');
    const confirmBtn = document.getElementById('modal-confirm');

    title.textContent = 'Renomear';
    label.textContent = 'Novo nome:';
    selectGroup.classList.add('hidden');
    hint.textContent = '';

    const name = path.split('/').pop();
    input.value = name;
    contextPath = path;
    confirmBtn.dataset.type = 'rename';

    overlay.classList.remove('hidden');
    input.focus();
    input.select();
}

async function handleModalConfirm() {
    const confirmBtn = document.getElementById('modal-confirm');
    const type = confirmBtn.dataset.type;
    const input = document.getElementById('modal-input');
    const value = input.value.trim();

    if (!value) {
        log('error', 'Nome é obrigatório');
        return;
    }

    let result;
    let newPath = '';

    if (type === 'folder') {
        result = await createFolder(value, contextPath);
        if (result) {
            newPath = contextPath ? `${contextPath}/${value}` : `/api/${value}`;
        }
    } else if (type === 'method') {
        const select = document.getElementById('modal-select');
        result = await createMethod(select.value, value);
        if (result) {
            newPath = `${value}/${select.value}`;
        }
    } else if (type === 'file') {
        result = await createFile(value, contextPath);
        if (result) {
            newPath = `${contextPath}/${value}`;
        }
    } else if (type === 'rename') {
        result = await renameItem(contextPath, value);
    }

    if (result) {
        hideModal();
        await loadRoutes();

        if (newPath) {
            selectFolderByPath(newPath);
        }
    }
}

function selectFolderByPath(path) {
    const normalizedPath = path.replace(/^\/api/, '');
    const parts = normalizedPath.split('/').filter(Boolean);

    let current = '';
    for (const part of parts) {
        current = current ? `${current}/${part}` : part;
        expandedFolders.add(current);
    }

    selectedFolderPath = path;
    contextPath = path;

    renderFolderTree(treeData);
}

async function createFolder(name, parent) {
    try {
        const res = await fetch('/admin/create-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent }),
        });
        const data = await res.json();
        if (res.ok) {
            log('success', `Pasta criada: ${name}`);
            return true;
        } else {
            log('error', data.error);
            return false;
        }
    } catch (err) {
        log('error', `Erro ao criar pasta: ${err.message}`);
        return false;
    }
}

async function createMethod(method, parent) {
    try {
        const res = await fetch('/admin/create-method', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ method, parent }),
        });
        const data = await res.json();
        if (res.ok) {
            log('success', `Método ${method.toUpperCase()} criado em ${parent}`);
            return true;
        } else {
            log('error', data.error);
            return false;
        }
    } catch (err) {
        log('error', `Erro ao criar método: ${err.message}`);
        return false;
    }
}

async function createFile(name, parent) {
    const defaultContent = JSON.stringify({
        name: name.replace('.json', ''),
        request: {},
        response: {
            status: 200,
            headers: { "Content-Type": "application/json" },
            body: {}
        }
    }, null, 2);

    try {
        const res = await fetch('/admin/create-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent, content: defaultContent }),
        });
        const data = await res.json();
        if (res.ok) {
            log('success', `Cenário criado: ${name}`);
            return true;
        } else {
            log('error', data.error);
            return false;
        }
    } catch (err) {
        log('error', `Erro ao criar arquivo: ${err.message}`);
        return false;
    }
}

async function renameItem(path, newName) {
    try {
        const res = await fetch('/admin/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, new_name: newName }),
        });
        const data = await res.json();
        if (res.ok) {
            log('success', `Renomeado para: ${newName}`);
            return true;
        } else {
            log('error', data.error);
            return false;
        }
    } catch (err) {
        log('error', `Erro ao renomear: ${err.message}`);
        return false;
    }
}

async function deleteItem(path) {
    const name = path.split('/').pop();
    if (!confirm(`Deletar "${name}"?`)) return false;

    try {
        const res = await fetch('/admin/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        });
        const data = await res.json();
        if (res.ok) {
            log('success', `Deletado: ${name}`);
            await loadRoutes();
            return true;
        } else {
            log('error', data.error);
            return false;
        }
    } catch (err) {
        log('error', `Erro ao deletar: ${err.message}`);
        return false;
    }
}

function showContextMenu(e, path) {
    e.preventDefault();
    e.stopPropagation();
    selectedContextPath = path;

    const ctxMenu = document.getElementById('context-menu');
    ctxMenu.querySelector('#ctx-curl').style.display = 'none';
    ctxMenu.querySelector('#ctx-rename').style.display = 'flex';
    ctxMenu.querySelector('#ctx-delete').style.display = 'flex';
    ctxMenu.style.left = `${e.clientX}px`;
    ctxMenu.style.top = `${e.clientY}px`;
    ctxMenu.classList.remove('hidden');
}

function toggleFolder(el, path) {
    el.stopPropagation();

    if (expandedFolders.has(path)) {
        expandedFolders.delete(path);
    } else {
        expandedFolders.add(path);
    }

    renderFolderTree(treeData);
}

function selectFolder(el, path) {
    document.querySelectorAll('.route-item, .tree-item').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    selectedFolderPath = path;
    contextPath = path;
}

function toggleAndSelect(el, ctxPath, folderPath) {
    document.querySelectorAll('.route-item, .tree-item').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    selectedFolderPath = ctxPath;
    window.contextPath = ctxPath;

    if (expandedFolders.has(folderPath)) {
        expandedFolders.delete(folderPath);
        for (const p of [...expandedFolders]) {
            if (p.startsWith(folderPath + '/')) {
                expandedFolders.delete(p);
            }
        }
    } else {
        expandedFolders.add(folderPath);
    }

    renderFolderTree(treeData);
}

function openFile(el, filePath) {
    document.querySelectorAll('.route-item, .tree-item').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    contextPath = filePath;

    loadFileContent(filePath);
}

async function loadFileContent(filePath) {
    try {
        const apiBase = window.location.origin;
        const res = await fetch(`${apiBase}/admin/scenario?path=${encodeURIComponent(filePath)}`);
        if (res.ok) {
            const data = await res.json();
            currentFile = filePath;
            const content = JSON.stringify(data, null, 2);
            editor.setValue(content);
            editor.updateOptions({ readOnly: false });
            document.getElementById('btn-save').disabled = false;
            switchTab('editor');
        } else {
            log('error', `Erro ao carregar arquivo: ${res.statusText}`);
        }
    } catch (err) {
        log('error', `Erro ao carregar arquivo: ${err.message}`);
    }
}

function initMonaco() {
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
    require(['vs/editor/editor.main'], () => {
        editor = monaco.editor.create(document.getElementById('monaco-editor'), {
            value: `{
  "name": "Novo cenário",
  "request": {
    "headers": {},
    "query": {},
    "body": {}
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {}
  }
}`,
            language: 'json',
            theme: 'vs-dark',
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: "'Consolas', 'Fira Code', monospace",
            padding: { top: 12 },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true },
        });

        fetch('/static/docs/REFERENCE.md')
            .then(r => r.text())
            .then(md => {
                document.getElementById('reference-content').innerHTML = simpleMarkdown(md);
            })
            .catch(() => {});

        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            if (currentFile) saveCurrentFile();
        });

        log('success', 'Monaco Editor carregado');
    });
}

function simpleMarkdown(md) {
    let html = md
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        .replace(/<\/ul>\n<ul>/g, '\n');

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
    });

    const lines = html.split('\n');
    let inTable = false;
    const result = [];

    for (const line of lines) {
        if (line.trim().startsWith('|')) {
            if (!inTable) {
                result.push('<table>');
                inTable = true;
            }
            const cells = line.split('|').filter(c => c.trim() !== '');
            if (cells.every(c => c.trim().match(/^[-:]+$/))) continue;
            const tag = result.length > 0 && result[result.length - 1].startsWith('<tr>') ? 'td' : 'th';
            const row = cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('');
            result.push(`<tr>${row}</tr>`);
        } else {
            if (inTable) {
                result.push('</table>');
                inTable = false;
            }
            result.push(line);
        }
    }
    if (inTable) result.push('</table>');

    return result.join('\n')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(?!<[hluop])/gm, '')
        .replace(/<br>(<)/g, '$1');
}

async function saveCurrentFile() {
    if (!currentFile || !editor) return;

    const content = editor.getValue();
    try {
        JSON.parse(content);
    } catch (e) {
        return;
    }

    const loadingEl = document.getElementById('editor-loading');
    const saveStatusEl = document.getElementById('save-status');
    const saveBtn = document.getElementById('btn-save');

    loadingEl.classList.remove('hidden');
    saveStatusEl.textContent = 'Salvando...';
    saveStatusEl.className = 'save-status saving';
    saveBtn.disabled = true;

    try {
        const res = await fetch('/admin/scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: currentFile, content }),
        });
        if (res.ok) {
            await loadRoutes();
            saveStatusEl.textContent = 'Salvo';
            saveStatusEl.className = 'save-status saved';
            setTimeout(() => {
                saveStatusEl.textContent = '';
                saveStatusEl.className = 'save-status';
            }, 2000);
        } else {
            saveStatusEl.textContent = 'Erro ao salvar';
            saveStatusEl.className = 'save-status';
        }
    } catch (_) {
        saveStatusEl.textContent = 'Erro ao salvar';
        saveStatusEl.className = 'save-status';
    } finally {
        loadingEl.classList.add('hidden');
        saveBtn.disabled = false;
    }
}

async function loadRoutes() {
    try {
        const res = await fetch('/admin/routes');
        const data = await res.json();
        routesData = data.routes;

        await loadDirectoryTree();
        renderRouteList();
        fetchServerUrl();
    } catch (err) {
        log('error', `Erro ao carregar rotas: ${err.message}`);
    }
}

async function fetchServerUrl() {
    try {
        const res = await fetch('/admin/status');
        const data = await res.json();
        if (data.host && data.port) {
            const host = data.host === '0.0.0.0' ? 'localhost' : data.host;
            serverBaseUrl = `http://${host}:${data.port}`;
        }
        if (data.running !== undefined) {
            updateServerStatus(data.running);
        }
    } catch {
        // mantém o default
    }
}

async function loadDirectoryTree() {
    try {
        const res = await fetch('/admin/tree');
        const data = await res.json();
        treeData = data.tree || {};

        if (!treeData || Object.keys(treeData).length === 0) {
            renderFolderTree({});
            return;
        }

        renderFolderTree(treeData);
    } catch {
        treeData = {};
        renderFolderTree({});
    }
}

function renderFolderTree(tree) {
    const container = document.getElementById('folder-tree');

    if (!tree || Object.keys(tree).length === 0) {
        container.innerHTML = '<p class="empty-state">Nenhum diretório encontrado</p>';
        return;
    }

    container.innerHTML = renderTreeNode(tree, '');

    if (selectedFolderPath) {
        const item = container.querySelector(`.tree-item[data-context="${selectedFolderPath}"]`);
        if (item) item.classList.add('active');
    }

    container.querySelectorAll('.tree-item[data-context]').forEach(el => {
        el.addEventListener('contextmenu', (e) => {
            showContextMenu(e, el.dataset.context);
        });
    });
}

function renderTreeNode(node, parentPath) {
    let html = '';

    const dirs = [];
    const files = [];

    for (const [key, value] of Object.entries(node)) {
        if (value === null) {
            files.push(key);
        } else {
            dirs.push([key, value]);
        }
    }

    const METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];

    for (const [key, value] of dirs) {
        const path = parentPath ? `${parentPath}/${key}` : key;
        const isExpanded = expandedFolders.has(path);
        const hasChildren = value && Object.keys(value).length > 0;
        const dirIcon = isExpanded ? 'fa-folder-open' : 'fa-folder';
        const isMethod = METHODS.includes(key.toLowerCase());
        const routePath = isMethod ? `/api/${parentPath}` : null;
        const httpMethod = isMethod ? key.toUpperCase() : null;

        const contextAttr = isMethod
            ? `oncontextmenu="showMethodContextMenu(event, '${httpMethod}', '${routePath}')"`
            : `oncontextmenu="showContextMenu(event, '/api/${path}')"`;

        html += `
            <div class="tree-item tree-dir" data-context="/api/${path}" data-path="${path}" onclick="toggleAndSelect(this, '/api/${path}', '${path}')" ${contextAttr}>
                ${hasChildren ? `<span class="icon folder"><i class="fas ${dirIcon}"></i></span>` : '<span class="icon folder"><i class="fas fa-folder"></i></span>'}
                <span>/${key}</span>
            </div>`;

        if (isExpanded && hasChildren) {
            html += `<div style="padding-left: 16px;">${renderTreeNode(value, path)}</div>`;
        }
    }

    for (const key of files) {
        const name = key;
        const parts = parentPath.split('/');
        const lastPart = parts[parts.length - 1];
        const isMethodParent = METHODS.includes(lastPart.toLowerCase());
        const fileRoutePath = isMethodParent ? `/api/${parts.slice(0, -1).join('/')}` : `/api/${parentPath}`;
        const fileMethod = isMethodParent ? lastPart.toUpperCase() : null;

        const fileContext = fileMethod
            ? `oncontextmenu="showFileContextMenu(event, '${fileMethod}', '${fileRoutePath}', '${name}')"`
            : `oncontextmenu="showContextMenu(event, '/api/${parentPath}/${key}')"`;

        html += `
            <div class="tree-item tree-file" data-file="/api/${parentPath}/${key}" onclick="openFile(this, '/api/${parentPath}/${key}')" ${fileContext}>
                <span class="icon file-json"><i class="fas fa-file-code"></i></span>
                <span>${name}</span>
            </div>`;
    }

    return html;
}

function renderRouteList() {
    const container = document.getElementById('route-list');

    if (!routesData || routesData.length === 0) {
        container.innerHTML = '<p class="empty-state">Nenhuma rota encontrada</p>';
        return;
    }

    container.innerHTML = routesData.map(r => {
        const methodLower = r.method.toLowerCase();
        return `
            <div class="route-entry" data-method="${r.method}" data-path="${r.path}" oncontextmenu="showRouteContextMenu(event, '${r.method}', '${r.path}')">
                <span class="route-method ${methodLower}">${r.method}</span>
                <span class="route-path">${r.path}</span>
            </div>`;
    }).join('');
}

function showMethodContextMenu(e, method, path) {
    e.preventDefault();
    e.stopPropagation();
    selectedContextPath = null;

    const ctxMenu = document.getElementById('context-menu');
    ctxMenu.querySelector('#ctx-curl').style.display = 'flex';
    ctxMenu.querySelector('#ctx-rename').style.display = 'none';
    ctxMenu.querySelector('#ctx-delete').style.display = 'none';
    ctxMenu.style.left = `${e.clientX}px`;
    ctxMenu.style.top = `${e.clientY}px`;
    ctxMenu.classList.remove('hidden');

    window._curlMethod = method;
    window._curlPath = path;
}

async function showFileContextMenu(e, method, path, scenario) {
    e.preventDefault();
    e.stopPropagation();
    selectedContextPath = null;

    window._curlMethod = method;
    window._curlPath = path;
    window._curlScenarioData = null;

    const filePath = `${path}/${method.toLowerCase()}/${scenario}.json`;
    try {
        const res = await fetch(`/admin/scenario?path=${encodeURIComponent(filePath)}`);
        if (res.ok) {
            const data = await res.json();
            data.name = scenario;
            window._curlScenarioData = data;
        }
    } catch (_) {}

    const ctxMenu = document.getElementById('context-menu');
    ctxMenu.querySelector('#ctx-curl').style.display = 'flex';
    ctxMenu.querySelector('#ctx-rename').style.display = 'none';
    ctxMenu.querySelector('#ctx-delete').style.display = 'none';
    ctxMenu.style.left = `${e.clientX}px`;
    ctxMenu.style.top = `${e.clientY}px`;
    ctxMenu.classList.remove('hidden');
}

function showRouteContextMenu(e, method, path) {
    e.preventDefault();
    e.stopPropagation();
    selectedContextPath = null;

    const ctxMenu = document.getElementById('context-menu');
    ctxMenu.querySelector('#ctx-curl').style.display = 'flex';
    ctxMenu.querySelector('#ctx-rename').style.display = 'none';
    ctxMenu.querySelector('#ctx-delete').style.display = 'none';
    ctxMenu.style.left = `${e.clientX}px`;
    ctxMenu.style.top = `${e.clientY}px`;
    ctxMenu.classList.remove('hidden');

    window._curlMethod = method;
    window._curlPath = path;
}

function copyCurl(method, path, scenarioData) {
    let curl = `curl -X ${method} "${serverBaseUrl}${path}"`;

    if (scenarioData) {
        const req = scenarioData.request || {};
        const body = req.body;

        if (req.headers) {
            for (const [k, v] of Object.entries(req.headers)) {
                curl += ` \\\n  -H "${k}: ${v}"`;
            }
        }

        if (body && method !== 'GET' && method !== 'HEAD') {
            const bodyStr = JSON.stringify(body, null, 2);
            curl += ` \\\n  -d '${bodyStr}'`;
        }
    }

    const label = scenarioData ? scenarioData.name : path;
    navigator.clipboard.writeText(curl).then(() => {
        showToast(`Copiado: ${method} ${label}`);
    }).catch(() => {
        log('info', curl);
    });

    hideContextMenu();
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 2000);
}

function hideContextMenu() {
    document.getElementById('context-menu').classList.add('hidden');
    document.getElementById('context-menu').querySelector('#ctx-curl').style.display = '';
    document.getElementById('context-menu').querySelector('#ctx-rename').style.display = '';
    document.getElementById('context-menu').querySelector('#ctx-delete').style.display = '';
}

async function startServer() {
    log('info', 'Iniciando servidor mock...');

    try {
        const res = await fetch('/admin/start', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'running') {
            updateServerStatus(true);
            const host = data.host === '0.0.0.0' ? 'localhost' : data.host;
            log('success', `Servidor rodando em http://${host}:${data.port}`);
        }
    } catch (err) {
        log('error', `Erro ao iniciar servidor: ${err.message}`);
    }
}

async function stopServer() {
    log('info', 'Parando servidor mock...');

    try {
        const res = await fetch('/admin/stop', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'stopped') {
            updateServerStatus(false);
            log('warn', 'Servidor parado');
        }
    } catch (err) {
        log('error', `Erro ao parar servidor: ${err.message}`);
    }
}

function updateServerStatus(running) {
    serverRunning = running;
    const statusEl = document.getElementById('server-status');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');

    if (running) {
        statusEl.className = 'status-badge status-running';
        statusEl.innerHTML = '<i class="fas fa-circle"></i> Rodando';
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        statusEl.className = 'status-badge status-stopped';
        statusEl.innerHTML = '<i class="fas fa-circle"></i> Parado';
        btnStart.disabled = false;
        btnStop.disabled = true;
    }
}

function log(level, message) {
    const container = document.getElementById('log-content');
    const time = new Date().toLocaleTimeString('pt-BR');
    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;
    entry.innerHTML = `<span class="timestamp">[${time}]</span> ${message}`;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}

function clearLogs() {
    document.getElementById('log-content').innerHTML = '';
    lastLogCount = 0;
    fetch('/admin/logs/clear', { method: 'POST' });
}

let lastLogCount = 0;

async function pollLogs() {
    if (!serverRunning) return;

    try {
        const res = await fetch('/admin/logs');
        const data = await res.json();
        const logs = data.logs || [];

        if (logs.length > lastLogCount) {
            const container = document.getElementById('log-content');
            for (let i = lastLogCount; i < logs.length; i++) {
                const entry = logs[i];
                const level = entry.status >= 400 ? 'error' : 'info';
                const methodColor = {
                    GET: 'color: var(--accent-green)',
                    POST: 'color: var(--accent-blue)',
                    PUT: 'color: var(--accent-yellow)',
                    PATCH: 'color: var(--accent-purple)',
                    DELETE: 'color: var(--accent-red)',
                }[entry.method] || '';

                const el = document.createElement('div');
                el.className = `log-entry ${level}`;
                const time = new Date().toLocaleTimeString('pt-BR');
                el.innerHTML = `<span class="timestamp">[${time}]</span> <span style="${methodColor};font-weight:bold">${entry.method}</span> ${entry.path} → <strong>${entry.status}</strong> <span style="color:var(--text-muted)">${entry.detail || ''}</span>`;
                container.appendChild(el);
            }
            container.scrollTop = container.scrollHeight;
            lastLogCount = logs.length;
        }
    } catch {
        // ignora erros de polling
    }
}

document.addEventListener('DOMContentLoaded', init);
setInterval(pollLogs, 1000);
