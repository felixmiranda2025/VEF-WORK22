// dist/app.js

// Estado de la aplicación
let currentUser = null;
let currentSection = 'dashboard';

// Elementos del DOM
const loginContainer = document.getElementById('login-container');
const dashboardContainer = document.getElementById('dashboard-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const userInfo = document.getElementById('user-info');
const pageTitle = document.getElementById('page-title');

// ============================================
// FUNCIONES DE AUTENTICACIÓN
// ============================================

// Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/.netlify/functions/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            mostrarDashboard();
            cargarDatosIniciales();
        } else {
            loginError.textContent = 'Usuario o contraseña incorrectos';
        }
    } catch (error) {
        loginError.textContent = 'Error de conexión';
        console.error('Login error:', error);
    }
});

// Logout
function logout() {
    currentUser = null;
    dashboardContainer.style.display = 'none';
    loginContainer.style.display = 'flex';
    loginForm.reset();
}

// Mostrar dashboard
function mostrarDashboard() {
    loginContainer.style.display = 'none';
    dashboardContainer.style.display = 'block';
    userInfo.textContent = `${currentUser.nombre_completo} (${currentUser.rol})`;
    showSection('dashboard');
}

// ============================================
// NAVEGACIÓN ENTRE SECCIONES
// ============================================

function showSection(section) {
    // Ocultar todas las secciones
    document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
    
    // Mostrar la sección seleccionada
    const sectionElement = document.getElementById(`${section}-section`);
    if (sectionElement) {
        sectionElement.style.display = 'block';
    }
    
    // Actualizar menú activo
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.textContent.toLowerCase().includes(section)) {
            item.classList.add('active');
        }
    });
    
    // Actualizar título
    pageTitle.textContent = section.charAt(0).toUpperCase() + section.slice(1);
    currentSection = section;
    
    // Cargar datos según la sección
    switch(section) {
        case 'dashboard':
            cargarDashboard();
            break;
        case 'clientes':
            cargarClientes();
            break;
        case 'proveedores':
            cargarProveedores();
            break;
        case 'proyectos':
            cargarProyectos();
            break;
        case 'cotizaciones':
            cargarCotizaciones();
            break;
        case 'ordenes':
            cargarOrdenes();
            break;
    }
}

// ============================================
// FUNCIONES DEL DASHBOARD
// ============================================

async function cargarDashboard() {
    try {
        // Cargar contadores
        const [clientes, proyectos, cotizaciones, ordenes] = await Promise.all([
            fetch('/.netlify/functions/clientes/get-clientes-count').catch(() => ({ json: () => ({ count: 0 }) })),
            fetch('/.netlify/functions/proyectos/get-proyectos-count').catch(() => ({ json: () => ({ count: 0 }) })),
            fetch('/.netlify/functions/cotizaciones/get-cotizaciones-pendientes-count').catch(() => ({ json: () => ({ count: 0 }) })),
            fetch('/.netlify/functions/ordenes/get-ordenes-pendientes-count').catch(() => ({ json: () => ({ count: 0 }) }))
        ]);
        
        const clientesData = await clientes.json();
        const proyectosData = await proyectos.json();
        const cotizacionesData = await cotizaciones.json();
        const ordenesData = await ordenes.json();
        
        document.getElementById('clientes-count').textContent = clientesData.count || 0;
        document.getElementById('proyectos-count').textContent = proyectosData.count || 0;
        document.getElementById('cotizaciones-count').textContent = cotizacionesData.count || 0;
        document.getElementById('ordenes-count').textContent = ordenesData.count || 0;
        
        // Cargar últimas cotizaciones
        const response = await fetch('/.netlify/functions/cotizaciones/get-ultimas-cotizaciones');
        const data = await response.json();
        
        const tbody = document.querySelector('#ultimas-cotizaciones tbody');
        if (tbody) {
            if (data.success && data.cotizaciones && data.cotizaciones.length > 0) {
                tbody.innerHTML = data.cotizaciones.map(c => `
                    <tr>
                        <td>${c.folio || 'N/A'}</td>
                        <td>${c.cliente_nombre || 'N/A'}</td>
                        <td>${new Date(c.fecha).toLocaleDateString()}</td>
                        <td>$${c.total ? c.total.toFixed(2) : '0.00'}</td>
                        <td>
                            <span style="color: ${c.estatus === 'aprobada' ? 'green' : c.estatus === 'pendiente' ? 'orange' : 'red'}">
                                ${c.estatus || 'pendiente'}
                            </span>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No hay cotizaciones recientes</td></tr>';
            }
        }
    } catch (error) {
        console.error('Error cargando dashboard:', error);
    }
}

// ============================================
// FUNCIONES PARA CLIENTES
// ============================================

// Cargar lista de clientes
async function cargarClientes() {
    const tbody = document.querySelector('#clientes-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Cargando...</td></tr>';
    
    try {
        const response = await fetch('/.netlify/functions/clientes/get-clientes');
        const data = await response.json();
        
        if (data.success) {
            if (data.clientes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No hay clientes registrados</td></tr>';
            } else {
                tbody.innerHTML = data.clientes.map(cliente => `
                    <tr>
                        <td>${cliente.id}</td>
                        <td>${cliente.nombre}</td>
                        <td>${cliente.email || '-'}</td>
                        <td>${cliente.telefono || '-'}</td>
                        <td>${cliente.rfc || '-'}</td>
                        <td>
                            <button class="btn-icon" onclick="editarCliente(${cliente.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon" onclick="eliminarCliente(${cliente.id})" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando clientes:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error al cargar clientes</td></tr>';
    }
}

// Abrir modal para nuevo cliente
function abrirModalCliente(cliente = null) {
    const modal = document.getElementById('clienteModal');
    const titulo = document.getElementById('modal-titulo');
    const form = document.getElementById('cliente-form');
    
    if (!modal || !titulo || !form) return;
    
    if (cliente) {
        titulo.textContent = 'Editar Cliente';
        document.getElementById('cliente-id').value = cliente.id;
        document.getElementById('cliente-nombre').value = cliente.nombre;
        document.getElementById('cliente-email').value = cliente.email || '';
        document.getElementById('cliente-telefono').value = cliente.telefono || '';
        document.getElementById('cliente-direccion').value = cliente.direccion || '';
        document.getElementById('cliente-rfc').value = cliente.rfc || '';
    } else {
        titulo.textContent = 'Nuevo Cliente';
        form.reset();
        document.getElementById('cliente-id').value = '';
    }
    
    modal.style.display = 'block';
}

// Cerrar modal
function cerrarModalCliente() {
    const modal = document.getElementById('clienteModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Guardar cliente (nuevo o editado)
if (document.getElementById('cliente-form')) {
    document.getElementById('cliente-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const clienteData = {
            id: document.getElementById('cliente-id').value,
            nombre: document.getElementById('cliente-nombre').value,
            email: document.getElementById('cliente-email').value,
            telefono: document.getElementById('cliente-telefono').value,
            direccion: document.getElementById('cliente-direccion').value,
            rfc: document.getElementById('cliente-rfc').value
        };
        
        const endpoint = clienteData.id ? 'update-cliente' : 'create-cliente';
        const method = clienteData.id ? 'PUT' : 'POST';
        
        try {
            const response = await fetch(`/.netlify/functions/clientes/${endpoint}`, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(clienteData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                cerrarModalCliente();
                cargarClientes();
                alert(clienteData.id ? 'Cliente actualizado' : 'Cliente creado');
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error de conexión');
        }
    });
}

// Editar cliente
async function editarCliente(id) {
    try {
        const response = await fetch(`/.netlify/functions/clientes/get-cliente?id=${id}`);
        const data = await response.json();
        
        if (data.success) {
            abrirModalCliente(data.cliente);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar cliente');
    }
}

// Eliminar cliente
async function eliminarCliente(id) {
    if (!confirm('¿Estás seguro de eliminar este cliente?')) return;
    
    try {
        const response = await fetch(`/.netlify/functions/clientes/delete-cliente`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        
        const data = await response.json();
        
        if (data.success) {
            cargarClientes();
            alert('Cliente eliminado');
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión');
    }
}

// ============================================
// FUNCIONES PARA PROVEEDORES
// ============================================

async function cargarProveedores() {
    const tbody = document.querySelector('#proveedores-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Cargando...</td></tr>';
    
    try {
        const response = await fetch('/.netlify/functions/proveedores/get-proveedores');
        const data = await response.json();
        
        if (data.success) {
            if (data.proveedores.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No hay proveedores registrados</td></tr>';
            } else {
                tbody.innerHTML = data.proveedores.map(p => `
                    <tr>
                        <td>${p.id}</td>
                        <td>${p.nombre}</td>
                        <td>${p.contacto || '-'}</td>
                        <td>${p.email || '-'}</td>
                        <td>${p.telefono || '-'}</td>
                        <td>
                            <button class="btn-icon" onclick="editarProveedor(${p.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon" onclick="eliminarProveedor(${p.id})" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando proveedores:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error al cargar proveedores</td></tr>';
    }
}

// ============================================
// FUNCIONES PARA PROYECTOS
// ============================================

async function cargarProyectos() {
    const tbody = document.querySelector('#proyectos-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Cargando...</td></tr>';
    
    try {
        const response = await fetch('/.netlify/functions/proyectos/get-proyectos');
        const data = await response.json();
        
        if (data.success) {
            if (data.proyectos.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No hay proyectos registrados</td></tr>';
            } else {
                tbody.innerHTML = data.proyectos.map(p => `
                    <tr>
                        <td>${p.id}</td>
                        <td>${p.cliente_nombre || 'N/A'}</td>
                        <td>${p.nombre}</td>
                        <td>${p.fecha_inicio ? new Date(p.fecha_inicio).toLocaleDateString() : '-'}</td>
                        <td>${p.estatus || 'activo'}</td>
                        <td>$${p.monto_total ? p.monto_total.toFixed(2) : '0.00'}</td>
                        <td>
                            <button class="btn-icon" onclick="editarProyecto(${p.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon" onclick="eliminarProyecto(${p.id})" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando proyectos:', error);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: red;">Error al cargar proyectos</td></tr>';
    }
}

// ============================================
// FUNCIONES PARA COTIZACIONES
// ============================================

async function cargarCotizaciones() {
    const tbody = document.querySelector('#cotizaciones-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Cargando...</td></tr>';
    
    try {
        const response = await fetch('/.netlify/functions/cotizaciones/get-cotizaciones');
        const data = await response.json();
        
        if (data.success) {
            if (data.cotizaciones.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No hay cotizaciones</td></tr>';
            } else {
                tbody.innerHTML = data.cotizaciones.map(c => `
                    <tr>
                        <td>${c.folio || 'N/A'}</td>
                        <td>${c.cliente_nombre}</td>
                        <td>${new Date(c.fecha).toLocaleDateString()}</td>
                        <td>$${c.total ? c.total.toFixed(2) : '0.00'}</td>
                        <td>${c.estatus}</td>
                        <td>
                            <button class="btn-icon" onclick="verCotizacion(${c.id})" title="Ver">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn-icon" onclick="editarCotizacion(${c.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando cotizaciones:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error al cargar cotizaciones</td></tr>';
    }
}

// ============================================
// FUNCIONES PARA ÓRDENES
// ============================================

async function cargarOrdenes() {
    const tbody = document.querySelector('#ordenes-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Cargando...</td></tr>';
    
    try {
        const response = await fetch('/.netlify/functions/ordenes/get-ordenes');
        const data = await response.json();
        
        if (data.success) {
            if (data.ordenes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No hay órdenes</td></tr>';
            } else {
                tbody.innerHTML = data.ordenes.map(o => `
                    <tr>
                        <td>${o.folio || 'N/A'}</td>
                        <td>${o.cliente_nombre}</td>
                        <td>${new Date(o.fecha).toLocaleDateString()}</td>
                        <td>$${o.total ? o.total.toFixed(2) : '0.00'}</td>
                        <td>${o.estatus}</td>
                        <td>
                            <button class="btn-icon" onclick="verOrden(${o.id})" title="Ver">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando órdenes:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error al cargar órdenes</td></tr>';
    }
}

// ============================================
// FUNCIONES AUXILIARES
// ============================================

// Cerrar modal si se hace clic fuera
window.onclick = function(event) {
    const modal = document.getElementById('clienteModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// ============================================
// CARGA INICIAL
// ============================================

async function cargarDatosIniciales() {
    await cargarDashboard();
}

// Exportar funciones globales para los onclick
window.logout = logout;
window.showSection = showSection;
window.abrirModalCliente = abrirModalCliente;
window.cerrarModalCliente = cerrarModalCliente;
window.editarCliente = editarCliente;
window.eliminarCliente = eliminarCliente;
window.editarProveedor = editarProveedor;
window.eliminarProveedor = eliminarProveedor;
window.editarProyecto = editarProyecto;
window.eliminarProyecto = eliminarProyecto;
window.verCotizacion = verCotizacion;
window.editarCotizacion = editarCotizacion;
window.verOrden = verOrden;