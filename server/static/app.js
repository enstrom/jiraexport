/**
 * Jira Export Tool - Frontend Application
 */

// State
let credentials = null;
let issues = [];
let selectedFormat = 'pdf';

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const mainScreen = document.getElementById('mainScreen');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const logoutBtn = document.getElementById('logoutBtn');

const searchBtn = document.getElementById('searchBtn');
const issueKeysInput = document.getElementById('issueKeys');
const jqlQueryInput = document.getElementById('jqlQuery');
const maxResultsInput = document.getElementById('maxResults');

const resultsCard = document.getElementById('resultsCard');
const resultCount = document.getElementById('resultCount');
const issuesList = document.getElementById('issuesList');

const exportBtn = document.getElementById('exportBtn');
const formatOptions = document.querySelectorAll('.format-option');

const downloadsCard = document.getElementById('downloadsCard');
const downloadsList = document.getElementById('downloadsList');
const downloadAllBtn = document.getElementById('downloadAllBtn');

const toast = document.getElementById('toast');

// Tab handling
const tabBtns = document.querySelectorAll('.tab-btn');
const keysTab = document.getElementById('keysTab');
const jqlTab = document.getElementById('jqlTab');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check for saved credentials
    const saved = localStorage.getItem('jiraCredentials');
    if (saved) {
        credentials = JSON.parse(saved);
        showMainScreen();
    }
    
    setupEventListeners();
});

function setupEventListeners() {
    // Login form
    loginForm.addEventListener('submit', handleLogin);
    
    // Logout
    logoutBtn.addEventListener('click', handleLogout);
    
    // Tabs
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const tabId = btn.dataset.tab;
            keysTab.classList.toggle('active', tabId === 'keys');
            jqlTab.classList.toggle('active', tabId === 'jql');
        });
    });
    
    // Search
    searchBtn.addEventListener('click', handleSearch);
    
    // Format selection
    formatOptions.forEach(option => {
        option.addEventListener('click', () => {
            formatOptions.forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
            selectedFormat = option.dataset.format;
        });
    });
    
    // Export
    exportBtn.addEventListener('click', handleExport);
    
    // Download all
    downloadAllBtn.addEventListener('click', downloadAll);
}

// Login
async function handleLogin(e) {
    e.preventDefault();
    
    const jiraUrl = document.getElementById('jiraUrl').value.trim();
    const email = document.getElementById('email').value.trim();
    const apiToken = document.getElementById('apiToken').value;
    
    setButtonLoading(loginForm.querySelector('button'), true);
    hideError();
    
    try {
        // Test credentials by making a simple API call
        const response = await fetch('/api/test-credentials', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jira_url: jiraUrl, email, api_token: apiToken })
        });
        
        const data = await response.json();
        
        if (data.success) {
            credentials = { jira_url: jiraUrl, email, api_token: apiToken };
            localStorage.setItem('jiraCredentials', JSON.stringify(credentials));
            showMainScreen();
            showToast('success', `Ansluten till ${data.site_name || 'Jira'}`);
        } else {
            showError(data.error || 'Kunde inte ansluta till Jira');
        }
    } catch (error) {
        showError('Nätverksfel: ' + error.message);
    } finally {
        setButtonLoading(loginForm.querySelector('button'), false);
    }
}

function handleLogout() {
    credentials = null;
    localStorage.removeItem('jiraCredentials');
    issues = [];
    
    // Reset form
    document.getElementById('jiraUrl').value = '';
    document.getElementById('email').value = '';
    document.getElementById('apiToken').value = '';
    
    // Reset UI
    resultsCard.classList.add('hidden');
    downloadsCard.classList.add('hidden');
    issuesList.innerHTML = '';
    downloadsList.innerHTML = '';
    
    showLoginScreen();
}

// Screen transitions
function showLoginScreen() {
    loginScreen.classList.remove('hidden');
    mainScreen.classList.add('hidden');
    logoutBtn.classList.add('hidden');
}

function showMainScreen() {
    loginScreen.classList.add('hidden');
    mainScreen.classList.remove('hidden');
    logoutBtn.classList.remove('hidden');
}

// Search
async function handleSearch() {
    const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
    
    let searchParams = {};
    
    if (activeTab === 'keys') {
        const keys = issueKeysInput.value
            .split(/[,\s]+/)
            .map(k => k.trim().toUpperCase())
            .filter(k => k.length > 0 && k.includes('-'));
        
        if (keys.length === 0) {
            showToast('error', 'Ange minst en issue key');
            return;
        }
        
        searchParams = { issue_keys: keys };
    } else {
        const jql = jqlQueryInput.value.trim();
        if (!jql) {
            showToast('error', 'Ange en JQL-query');
            return;
        }
        
        searchParams = { 
            jql, 
            max_results: parseInt(maxResultsInput.value) || 50 
        };
    }
    
    setButtonLoading(searchBtn, true);
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...credentials, ...searchParams })
        });
        
        const data = await response.json();
        
        if (data.success) {
            issues = data.issues;
            renderIssues();
            resultsCard.classList.remove('hidden');
            downloadsCard.classList.add('hidden');
            downloadsList.innerHTML = '';
            showToast('success', `Hittade ${issues.length} issues`);
        } else {
            showToast('error', data.error || 'Sökningen misslyckades');
        }
    } catch (error) {
        showToast('error', 'Nätverksfel: ' + error.message);
    } finally {
        setButtonLoading(searchBtn, false);
    }
}

function renderIssues() {
    resultCount.textContent = `${issues.length} issues`;
    
    issuesList.innerHTML = issues.map(issue => `
        <div class="issue-item">
            <input type="checkbox" class="issue-checkbox" value="${issue.key}" checked>
            <span class="issue-type">${getIssueTypeIcon(issue.type)}</span>
            <span class="issue-key">${issue.key}</span>
            <span class="issue-summary">${escapeHtml(issue.summary)}</span>
        </div>
    `).join('');
}

function getIssueTypeIcon(type) {
    const icons = {
        'Story': '📗',
        'Bug': '🐛',
        'Task': '✅',
        'Epic': '🏔️',
        'Subtask': '📎',
        'Sub-task': '📎'
    };
    return icons[type] || '📄';
}

// Export
async function handleExport() {
    const selectedIssues = Array.from(document.querySelectorAll('.issue-checkbox:checked'))
        .map(cb => cb.value);
    
    if (selectedIssues.length === 0) {
        showToast('error', 'Välj minst en issue att exportera');
        return;
    }
    
    setButtonLoading(exportBtn, true);
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...credentials,
                issue_keys: selectedIssues,
                format: selectedFormat
            })
        });
        
        const data = await response.json();
        
        if (data.success || data.files) {
            renderDownloads(data.files || [], data.errors || []);
            downloadsCard.classList.remove('hidden');
            showToast('success', `Exporterade ${data.exported || data.files?.length || 0} filer`);
        } else {
            showToast('error', data.error || 'Export misslyckades');
        }
    } catch (error) {
        showToast('error', 'Nätverksfel: ' + error.message);
    } finally {
        setButtonLoading(exportBtn, false);
    }
}

function renderDownloads(files, errors) {
    let html = '';
    
    files.forEach(file => {
        html += `
            <div class="download-item" data-file='${JSON.stringify(file)}'>
                <span class="download-icon">✅</span>
                <div class="download-info">
                    <div class="download-name">${file.filename}</div>
                </div>
                <button class="download-btn" onclick="downloadFile(this)">Ladda ner</button>
            </div>
        `;
    });
    
    errors.forEach(err => {
        html += `
            <div class="download-item error">
                <span class="download-icon">❌</span>
                <div class="download-info">
                    <div class="download-name">${err.issue_key}</div>
                    <div class="download-size">${err.error}</div>
                </div>
            </div>
        `;
    });
    
    downloadsList.innerHTML = html;
}

function downloadFile(btn) {
    const item = btn.closest('.download-item');
    const file = JSON.parse(item.dataset.file);
    
    const base64 = file.file_base64 || file.pdf_base64;
    const mimeType = getMimeType(file.format || selectedFormat);
    
    const link = document.createElement('a');
    link.href = `data:${mimeType};base64,${base64}`;
    link.download = file.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function downloadAll() {
    const items = document.querySelectorAll('.download-item:not(.error)');
    
    items.forEach((item, index) => {
        setTimeout(() => {
            const file = JSON.parse(item.dataset.file);
            const base64 = file.file_base64 || file.pdf_base64;
            const mimeType = getMimeType(file.format || selectedFormat);
            
            const link = document.createElement('a');
            link.href = `data:${mimeType};base64,${base64}`;
            link.download = file.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }, index * 500);
    });
}

function getMimeType(format) {
    const types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'md': 'text/markdown',
        'png': 'image/png'
    };
    return types[format] || 'application/octet-stream';
}

// UI Helpers
function setButtonLoading(btn, loading) {
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loading');
    
    if (loading) {
        text.classList.add('hidden');
        loader.classList.remove('hidden');
        btn.disabled = true;
    } else {
        text.classList.remove('hidden');
        loader.classList.add('hidden');
        btn.disabled = false;
    }
}

function showError(message) {
    loginError.textContent = message;
    loginError.classList.remove('hidden');
}

function hideError() {
    loginError.classList.add('hidden');
}

function showToast(type, message) {
    toast.className = `toast ${type}`;
    toast.querySelector('.toast-icon').textContent = type === 'success' ? '✅' : '❌';
    toast.querySelector('.toast-message').textContent = message;
    
    // Force reflow
    toast.offsetHeight;
    
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
