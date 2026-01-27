// Configuration
const CONFIG = {
    apiBase: '/repo/api',
    selectorsApiBase: '/repos',
    maxRecentFiles: 5,
    searchDebounceMs: 300,
    modeMap: {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'javascript',
        'html': 'htmlmixed',
        'css': 'css',
        'json': 'javascript',
        'yaml': 'yaml',
        'markdown': 'markdown',
        'shell': 'shell'
    }
};

// State
let state = {
    currentRepo: null,
    currentFile: null,
    treeData: null,
    editor: null,
    expandedFolders: new Set(),
    selectedElement: null,
    searchTimeout: null
};

// =====================================
// Initialization
// =====================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Multi-Repo Browser...');
    
    // Initialize tree
    initTree();
    
    // Setup event listeners
    setupEventListeners();
    
    console.log('Initialization complete');
});

function setupEventListeners() {
    // Search
    const searchInput = document.getElementById('global-search');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearchInput);
        searchInput.addEventListener('keydown', handleSearchKeydown);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput?.focus();
        }
    });
    
    // Add repo button
    const addRepoBtn = document.getElementById('add-repo-btn');
    if (addRepoBtn) {
        addRepoBtn.addEventListener('click', openRepoSelector);
    }
    
    // Sync all button
    const syncAllBtn = document.getElementById('sync-all-btn');
    if (syncAllBtn) {
        syncAllBtn.addEventListener('click', syncAllRepos);
    }
    
    // Modal close
    const modalClose = document.querySelector('.modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeRepoSelector);
    }
    
    // Add repo submit
    const addRepoSubmit = document.getElementById('add-repo-submit');
    if (addRepoSubmit) {
        addRepoSubmit.addEventListener('click', addRepo);
    }
    
    // Click outside dropdown to close
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('search-results-dropdown');
        const searchBox = document.querySelector('.search-container');
        if (dropdown && !searchBox.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}

// =====================================
// Tree Management
// =====================================

async function initTree() {
    const treeContainer = document.getElementById('file-tree');
    if (!treeContainer) return;
    
    try {
        let url = `${CONFIG.apiBase}/tree`;
        
        // If repo is selected, show its tree
        if (state.currentRepo) {
            url += `?repo=${encodeURIComponent(state.currentRepo)}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        state.treeData = data;
        renderTree(treeContainer, data);
        
    } catch (error) {
        console.error('Failed to load tree:', error);
        treeContainer.innerHTML = '<p style="padding: 1rem;">שגיאה בטעינת עץ הקבצים</p>';
    }
}

function renderTree(container, items) {
    container.innerHTML = '';
    
    if (!items || items.length === 0) {
        container.innerHTML = '<p style="padding: 1rem;">אין קבצים להצגה</p>';
        return;
    }
    
    items.forEach(item => {
        const node = createTreeNode(item, 0);
        container.appendChild(node);
    });
}

function createTreeNode(item, level) {
    const node = document.createElement('div');
    node.className = 'tree-node';
    node.dataset.path = item.path;
    node.dataset.type = item.type;
    
    const itemEl = document.createElement('div');
    itemEl.className = 'tree-item';
    itemEl.style.paddingRight = `${8 + level * 16}px`;
    
    // Icon
    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    if (item.is_repo_root) {
        icon.innerHTML = '<i class="bi bi-folder"></i>';
        node.classList.add('repo-root');
    } else if (item.type === 'directory') {
        icon.innerHTML = '<i class="bi bi-folder"></i>';
    } else {
        icon.innerHTML = '<i class="bi bi-file-code"></i>';
    }
    
    // Name
    const name = document.createElement('span');
    name.className = 'tree-name';
    name.textContent = item.name;
    
    // Sync status badge
    if (item.is_repo_root && item.sync_status) {
        const badge = document.createElement('span');
        badge.className = `sync-badge ${item.sync_status}`;
        badge.textContent = item.sync_status === 'synced' ? '✓' : '?';
        name.appendChild(badge);
    }
    
    itemEl.appendChild(icon);
    itemEl.appendChild(name);
    node.appendChild(itemEl);
    
    // Click handler
    if (item.is_repo_root) {
        itemEl.addEventListener('click', (e) => {
            e.stopPropagation();
            selectRepo(item.name);
        });
    } else if (item.type === 'file') {
        itemEl.addEventListener('click', (e) => {
            e.stopPropagation();
            selectFile(state.currentRepo, item.path, itemEl);
        });
    }
    
    return node;
}

function selectRepo(repoName) {
    state.currentRepo = repoName;
    
    // Update UI
    document.querySelectorAll('.repo-root').forEach(el => {
        el.querySelector('.tree-item').classList.remove('selected');
    });
    
    const selectedNode = document.querySelector(`[data-path="${repoName}"]`);
    if (selectedNode) {
        selectedNode.querySelector('.tree-item').classList.add('selected');
    }
    
    // Reload tree
    initTree();
    
    // Update search placeholder
    const searchInput = document.getElementById('global-search');
    if (searchInput) {
        searchInput.placeholder = `חפש ב-${repoName}... (Ctrl+K)`;
    }
    
    showToast(`נבחר ריפו: ${repoName}`, 'success');
}

// =====================================
// File Viewer
// =====================================

async function selectFile(repoName, path, element) {
    if (!repoName || !path) return;
    
    // Update selected state
    if (state.selectedElement) {
        state.selectedElement.classList.remove('selected');
    }
    state.selectedElement = element;
    element.classList.add('selected');
    
    state.currentFile = { repo: repoName, path };
    
    // Update header
    const pathDisplay = document.getElementById('file-path-display');
    if (pathDisplay) {
        pathDisplay.innerHTML = `
            <i class="bi bi-file-code"></i>
            <span>${repoName}/${path}</span>
        `;
    }
    
    // Show loading
    const container = document.getElementById('code-viewer-container');
    container.innerHTML = '<div style="padding: 2rem; text-align: center;">טוען...</div>';
    
    try {
        const response = await fetch(
            `${CONFIG.apiBase}/file/${encodeURIComponent(repoName)}/${encodeURIComponent(path)}`
        );
        
        if (!response.ok) {
            throw new Error('Failed to load file');
        }
        
        const data = await response.json();
        displayFile(data);
        
    } catch (error) {
        console.error('Failed to load file:', error);
        container.innerHTML = '<div style="padding: 2rem; text-align: center; color: red;">שגיאה בטעינת הקובץ</div>';
    }
}

function displayFile(data) {
    const container = document.getElementById('code-viewer-container');
    container.innerHTML = '';
    
    // Create CodeMirror editor
    if (state.editor) {
        state.editor.toTextArea();
    }
    
    const textarea = document.createElement('textarea');
    textarea.value = data.content || '';
    container.appendChild(textarea);
    
    const mode = CONFIG.modeMap[data.language] || 'text/plain';
    
    state.editor = CodeMirror.fromTextArea(textarea, {
        mode: mode,
        theme: 'monokai',
        lineNumbers: true,
        readOnly: true,
        lineWrapping: false
    });
}

// =====================================
// Search
// =====================================

function handleSearchInput(e) {
    const query = e.target.value;
    
    clearTimeout(state.searchTimeout);
    
    if (query.length < 2) {
        hideSearchResults();
        return;
    }
    
    state.searchTimeout = setTimeout(() => {
        performSearch(query);
    }, CONFIG.searchDebounceMs);
}

function handleSearchKeydown(e) {
    const dropdown = document.getElementById('search-results-dropdown');
    if (!dropdown || dropdown.classList.contains('hidden')) return;
    
    if (e.key === 'Escape') {
        hideSearchResults();
        e.target.blur();
    }
}

async function performSearch(query) {
    const dropdown = document.getElementById('search-results-dropdown');
    const resultsList = dropdown.querySelector('.search-results-list');
    
    dropdown.classList.remove('hidden');
    resultsList.innerHTML = '<p style="padding: 1rem;">מחפש...</p>';
    
    try {
        let url = `${CONFIG.apiBase}/search?q=${encodeURIComponent(query)}&type=content`;
        
        if (state.currentRepo) {
            url += `&repo=${encodeURIComponent(state.currentRepo)}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        renderSearchResults(resultsList, data.results || [], query, !state.currentRepo);
        
    } catch (error) {
        console.error('Search failed:', error);
        resultsList.innerHTML = '<p style="padding: 1rem;">שגיאה בחיפוש</p>';
    }
}

function renderSearchResults(container, results, query, showRepo = false) {
    if (results.length === 0) {
        container.innerHTML = '<p style="padding: 1rem;">לא נמצאו תוצאות</p>';
        return;
    }
    
    container.innerHTML = results.slice(0, 50).map(result => {
        const repoDisplay = showRepo && result.repo ? `${escapeHtml(result.repo)}/` : '';
        return `
            <div class="search-result-item" onclick="handleSearchResultClick('${escapeHtml(result.repo || state.currentRepo)}', '${escapeHtml(result.path)}')">
                <div class="search-result-path">
                    ${repoDisplay}${escapeHtml(result.path)}
                    ${result.line ? `<span style="color: #888;"> : L${result.line}</span>` : ''}
                </div>
                ${result.content ? `<div class="search-result-content">${escapeHtml(result.content)}</div>` : ''}
            </div>
        `;
    }).join('');
}

function handleSearchResultClick(repo, path) {
    selectFile(repo, path, null);
    hideSearchResults();
}

function hideSearchResults() {
    const dropdown = document.getElementById('search-results-dropdown');
    if (dropdown) {
        dropdown.classList.add('hidden');
    }
}

// =====================================
// Repo Management
// =====================================

function openRepoSelector() {
    const modal = document.getElementById('repo-selector-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadRepoList();
    }
}

function closeRepoSelector() {
    const modal = document.getElementById('repo-selector-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

async function loadRepoList() {
    const container = document.getElementById('repo-list');
    if (!container) return;
    
    container.innerHTML = '<p>טוען...</p>';
    
    try {
        const response = await fetch(`${CONFIG.selectorsApiBase}/`);
        const repos = await response.json();
        
        if (repos.length === 0) {
            container.innerHTML = '<p>אין ריפוים. הוסף ריפו ראשון!</p>';
            return;
        }
        
        container.innerHTML = repos.map(repo => `
            <div class="repo-item" data-name="${escapeHtml(repo.name)}">
                <div class="repo-info">
                    <h4>${escapeHtml(repo.name)}</h4>
                    <div class="repo-meta">
                        ${repo.size_mb || 0} MB | ${repo.sync_status}
                    </div>
                </div>
                <div class="repo-actions">
                    <button class="btn-icon" onclick="syncRepo('${escapeHtml(repo.name)}')" title="סנכרן">
                        <i class="bi bi-arrow-repeat"></i>
                    </button>
                    <button class="btn-icon" onclick="removeRepo('${escapeHtml(repo.name)}')" title="מחק">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load repos:', error);
        container.innerHTML = '<p>שגיאה בטעינת ריפוים</p>';
    }
}

async function addRepo() {
    const urlInput = document.getElementById('new-repo-url');
    const nameInput = document.getElementById('new-repo-name');
    
    const url = urlInput?.value.trim();
    const name = nameInput?.value.trim() || null;
    
    if (!url) {
        showToast('יש להזין URL', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${CONFIG.selectorsApiBase}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, name })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('הריפו נוסף בהצלחה!', 'success');
            urlInput.value = '';
            nameInput.value = '';
            loadRepoList();
            initTree();
        } else {
            showToast(result.error || 'שגיאה בהוספת ריפו', 'error');
        }
        
    } catch (error) {
        showToast('שגיאה בהוספת ריפו', 'error');
    }
}

async function removeRepo(name) {
    if (!confirm(`האם למחוק את הריפו ${name}?`)) return;
    
    try {
        const response = await fetch(`${CONFIG.selectorsApiBase}/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('הריפו נמחק', 'success');
            
            if (state.currentRepo === name) {
                state.currentRepo = null;
            }
            
            loadRepoList();
            initTree();
        }
    } catch (error) {
        showToast('שגיאה במחיקת ריפו', 'error');
    }
}

async function syncRepo(name) {
    const repoItem = document.querySelector(`.repo-item[data-name="${name}"]`);
    const syncBtn = repoItem?.querySelector('.bi-arrow-repeat');
    
    if (syncBtn) {
        syncBtn.parentElement.classList.add('spinning');
    }
    
    try {
        const response = await fetch(`${CONFIG.selectorsApiBase}/${encodeURIComponent(name)}/sync`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('הסנכרון הושלם', 'success');
        } else {
            showToast(result.error || 'שגיאה בסנכרון', 'error');
        }
        
        loadRepoList();
        
    } catch (error) {
        showToast('שגיאה בסנכרון', 'error');
    } finally {
        if (syncBtn) {
            syncBtn.parentElement.classList.remove('spinning');
        }
    }
}

async function syncAllRepos() {
    showToast('מסנכרן את כל הריפוים...', 'success');
    
    try {
        const response = await fetch(`${CONFIG.selectorsApiBase}/sync-all`, {
            method: 'POST'
        });
        
        const result = await response.json();
        showToast('הסנכרון הושלם', 'success');
        
    } catch (error) {
        showToast('שגיאה בסנכרון', 'error');
    }
}

// =====================================
// Utilities
// =====================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}
