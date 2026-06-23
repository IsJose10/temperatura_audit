/* ===================== */
/* RANSA - Frontend JavaScript */
/* Common utilities & API helpers */
/* ===================== */

// ============================
// Auth Helpers
// ============================

function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = '/';
        return false;
    }
    return true;
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

// ============================
// API Helpers
// ============================

const API_TIMEOUT_MS = 30000; // 30 segundos timeout
const API_MAX_RETRIES = 2;    // reintentos para GET

function _createAbortController() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
    return { signal: controller.signal, timeoutId };
}

function _clearTimeout(timeoutId) {
    clearTimeout(timeoutId);
}

async function _handleResponse(response) {
    if (response.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        const detail = err.detail || `Error del servidor (${response.status})`;
        throw new Error(detail);
    }
}

function _handleFetchError(error) {
    if (error.name === 'AbortError') {
        throw new Error('La solicitud tardó demasiado. Verifica tu conexión e intenta de nuevo.');
    }
    if (!navigator.onLine) {
        throw new Error('Sin conexión a internet. Verifica tu red e intenta de nuevo.');
    }
    throw error;
}

async function apiGet(url) {
    let lastError;
    for (let attempt = 0; attempt <= API_MAX_RETRIES; attempt++) {
        const { signal, timeoutId } = _createAbortController();
        try {
            if (attempt > 0) {
                // Backoff exponencial: 1s, 2s
                await new Promise(r => setTimeout(r, 1000 * attempt));
            }
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${getToken()}` },
                signal
            });
            _clearTimeout(timeoutId);
            await _handleResponse(response);
            const text = await response.text();
            if (!text || text === 'null') return null;
            return JSON.parse(text);
        } catch (error) {
            _clearTimeout(timeoutId);
            lastError = error;
            // No reintentar errores de autenticación o del servidor (4xx)
            if (error.message === 'Sesión expirada' || error.message.includes('Error del servidor (4')) {
                throw error;
            }
            if (attempt === API_MAX_RETRIES) {
                _handleFetchError(error);
            }
        }
    }
    throw lastError;
}

async function apiPost(url, data) {
    const { signal, timeoutId } = _createAbortController();
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(data),
            signal
        });
        _clearTimeout(timeoutId);
        await _handleResponse(response);
        return await response.json();
    } catch (error) {
        _clearTimeout(timeoutId);
        _handleFetchError(error);
    }
}

async function apiPut(url, data) {
    const { signal, timeoutId } = _createAbortController();
    try {
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(data),
            signal
        });
        _clearTimeout(timeoutId);
        await _handleResponse(response);
        return await response.json();
    } catch (error) {
        _clearTimeout(timeoutId);
        _handleFetchError(error);
    }
}

async function apiDelete(url) {
    const { signal, timeoutId } = _createAbortController();
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            signal
        });
        _clearTimeout(timeoutId);
        await _handleResponse(response);
        return await response.json();
    } catch (error) {
        _clearTimeout(timeoutId);
        _handleFetchError(error);
    }
}

// ============================
// UI Helpers
// ============================

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
    document.body.style.overflow = '';
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// ============================
// Date Formatting
// ============================

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-CO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateShort(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-CO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}
