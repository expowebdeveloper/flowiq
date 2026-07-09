/**
 * FlowIQ - Main Application JavaScript
 * Handles global UI interactions, toast notifications, and shared utilities.
 */

// ─── Toast Notifications ──────────────────────────────────────────────────────

function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const icons = {
        success: 'fa-circle-check text-success',
        error: 'fa-circle-xmark text-danger',
        warning: 'fa-triangle-exclamation text-warning',
        info: 'fa-circle-info text-primary',
    };

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center border-0 shadow-sm show';
    toastEl.setAttribute('role', 'alert');
    toastEl.style.cssText = 'min-width:280px;';
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body d-flex align-items-center gap-2">
                <i class="fa-solid ${icons[type] || icons.info}"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;

    toastContainer.appendChild(toastEl);
    setTimeout(() => toastEl.remove(), 4000);
}


// ─── Sidebar Active Link ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar .nav-link[data-path]').forEach(function (link) {
        const dp = link.getAttribute('data-path');
        if (dp === '/' ? path === '/' : path.startsWith(dp)) {
            link.classList.add('active');
        }
    });
});


// ─── Confirm Delete Helper ────────────────────────────────────────────────────

function confirmDelete(message, onConfirm) {
    if (confirm(message || 'Are you sure you want to delete this item?')) {
        onConfirm();
    }
}


// ─── Generic API Fetch Helper ─────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await response.json();
            return { ok: response.ok, status: response.status, data };
        }
        const text = await response.text();
        return { ok: response.ok, status: response.status, data: text };
    } catch (err) {
        console.error('API Fetch error:', err);
        return { ok: false, status: 0, data: null, error: err.message };
    }
}


// ─── Company Actions ──────────────────────────────────────────────────────────

async function deleteCompany(id) {
    confirmDelete('Are you sure you want to delete this company? This cannot be undone.', async () => {
        const result = await apiFetch(`/companies/${id}/delete`, { method: 'POST' });
        if (result.ok) {
            showToast(result.data?.message || 'Company deleted.', 'success');
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(result.data?.message || 'Failed to delete company.', 'error');
        }
    });
}


// ─── Bank Actions ─────────────────────────────────────────────────────────────

function deleteBank(id) {
    confirmDelete('Are you sure you want to delete this bank and all its loan policies?', () => {
        window.location.href = `/banks/${id}/delete`;
    });
}
