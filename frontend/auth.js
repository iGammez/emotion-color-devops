// auth.js - Sistema de autenticación para el frontend

const AUTH = {
    // Verificar si el usuario está autenticado
    isAuthenticated() {
        const token = localStorage.getItem('token');
        const user = localStorage.getItem('user');
        return token && user;
    },

    // Obtener token
    getToken() {
        return localStorage.getItem('token');
    },

    // Obtener usuario
    getUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    // Cerrar sesión
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    },

    // Verificar rol
    hasRole(role) {
        const user = this.getUser();
        return user && user.role === role;
    },

    // Verificar si es admin
    isAdmin() {
        return this.hasRole('admin');
    },

    // Obtener headers con autenticación
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.getToken()}`,
            'Content-Type': 'application/json'
        };
    },

    // Redirigir a login si no está autenticado
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }
};

// Verificar autenticación al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // Si estamos en una página que requiere auth (no login ni register)
    const publicPages = ['login.html', 'register.html'];
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    if (!publicPages.includes(currentPage)) {
        if (!AUTH.requireAuth()) {
            return;
        }
        
        // NO crear la barra de usuario aquí
        // La UI del usuario ahora está en el menú hamburguesa
    }
});

// Función para hacer peticiones autenticadas
async function authenticatedFetch(url, options = {}) {
    const token = AUTH.getToken();
    
    if (!token) {
        AUTH.logout();
        throw new Error('No autenticado');
    }

    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        }
    };

    const response = await fetch(url, { ...options, headers: defaultOptions.headers });

    // Si el token expiró o es inválido
    if (response.status === 401) {
        alert('Sesión expirada. Por favor, inicia sesión nuevamente.');
        AUTH.logout();
        throw new Error('Sesión expirada');
    }

    return response;
}

// Exportar para uso en otros scripts
window.AUTH = AUTH;
window.authenticatedFetch = authenticatedFetch;