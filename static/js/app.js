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

async function apiGet(url) {
    const response = await fetch(url, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    });
    if (response.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Error en la solicitud');
    }
    // Handle null response
    const text = await response.text();
    if (!text || text === 'null') return null;
    return JSON.parse(text);
}

async function apiPost(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(data)
    });
    if (response.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Error en la solicitud');
    }
    return await response.json();
}

async function apiPut(url, data) {
    const response = await fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(data)
    });
    if (response.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Error en la solicitud');
    }
    return await response.json();
}

async function apiDelete(url) {
    const response = await fetch(url, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    });
    if (response.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Error en la solicitud');
    }
    return await response.json();
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
