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
        
        // Mostrar información del usuario
        displayUserInfo();
        
        // Agregar botón de logout si no existe
        addLogoutButton();
    }
});

// Mostrar información del usuario en la interfaz
function displayUserInfo() {
    const user = AUTH.getUser();
    if (!user) return;

    // Crear barra de usuario si no existe
    if (!document.getElementById('user-bar')) {
        const userBar = document.createElement('div');
        userBar.id = 'user-bar';
        userBar.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 15px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        `;

        // Icono de rol
        const roleIcon = user.role === 'admin' ? '🛡️' : '👤';
        const roleColor = user.role === 'admin' ? '#ff6b6b' : '#4ecdc4';
        const roleName = user.role === 'admin' ? 'Admin' : 'User';

        userBar.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1.2rem;
                ">
                    ${roleIcon}
                </div>
                <div>
                    <div style="font-weight: 600; color: #333; font-size: 0.9rem;">
                        ${user.full_name || user.username}
                    </div>
                    <div style="font-size: 0.75rem; color: ${roleColor}; font-weight: 600;">
                        ${roleName}
                    </div>
                </div>
            </div>
            <button id="logout-btn" style="
                background: linear-gradient(135deg, #667eea, #764ba2);
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 15px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                Cerrar Sesión
            </button>
        `;

        document.body.appendChild(userBar);

        // Agregar evento al botón de logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
                AUTH.logout();
            }
        });
    }
}

// Agregar botón de logout al header si existe
function addLogoutButton() {
    const controlsContainer = document.querySelector('.controls-container');
    if (controlsContainer && !document.getElementById('logout-btn-header')) {
        // Ya se agregó en displayUserInfo, no duplicar
    }
}

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