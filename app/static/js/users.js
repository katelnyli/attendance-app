let token = null;
let users = [];
let roles = [];

window.onload = function() {
    token = localStorage.getItem('token');
    const email = localStorage.getItem('email');

    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    if (email) {
        document.getElementById('userEmail').textContent = email;
    }

    loadUsers();
};

function goBack() {
    window.location.href = '/';
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    window.location.href = '/login.html';
}

async function loadUsers() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('usersTable');
    const emptyState = document.getElementById('emptyState');
    const messageDiv = document.getElementById('message');

    loading.style.display = 'block';
    table.style.display = 'none';
    emptyState.style.display = 'none';
    messageDiv.innerHTML = '';

    try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/users', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return;
            }
            if (response.status === 403) {
                showError('You do not have permission to view users. Admin access required.');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        users = await response.json();

        // Extract unique roles from users
        const roleMap = new Map();
        users.forEach(user => {
            if (user.role_id && user.role_name) {
                roleMap.set(user.role_id, user.role_name);
            }
        });
        roles = Array.from(roleMap, ([id, name]) => ({ id, name }));

        if (users.length === 0) {
            emptyState.style.display = 'block';
        } else {
            displayUsers();
            table.style.display = 'table';
        }

    } catch (error) {
        console.error('Error loading users:', error);
        showError('Failed to load users: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

function displayUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    users.forEach(user => {
        const row = document.createElement('tr');

        // Email
        const emailCell = document.createElement('td');
        emailCell.textContent = user.user_email;
        row.appendChild(emailCell);

        // Name
        const nameCell = document.createElement('td');
        nameCell.textContent = user.user_name;
        row.appendChild(nameCell);

        // Current Role Badge
        const roleCell = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `badge badge-${user.role_name || 'viewer'}`;
        badge.textContent = user.role_name || 'No Role';
        roleCell.appendChild(badge);
        row.appendChild(roleCell);

        // Role Dropdown
        const actionCell = document.createElement('td');
        const select = document.createElement('select');
        select.id = `role-${user.user_id}`;

        roles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.name.charAt(0).toUpperCase() + role.name.slice(1);
            if (user.role_id === role.id) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        select.addEventListener('change', () => updateUserRole(user.user_id, select.value));
        actionCell.appendChild(select);
        row.appendChild(actionCell);

        tbody.appendChild(row);
    });
}

async function updateUserRole(userId, newRoleId) {
    const select = document.getElementById(`role-${userId}`);
    const originalValue = select.value;
    select.disabled = true;

    try {
        const response = await fetch(
            `http://127.0.0.1:8000/api/v1/users/${userId}/role?role_id=${newRoleId}`,
            {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return;
            }
            if (response.status === 403) {
                throw new Error('Permission denied. You cannot perform this action.');
            }
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update role');
        }

        const result = await response.json();
        showSuccess(`Successfully updated ${result.user_email} to ${result.new_role}`);

        // Reload users to get fresh data
        setTimeout(() => loadUsers(), 1500);

    } catch (error) {
        console.error('Error updating role:', error);
        showError('Failed to update role: ' + error.message);
        // Revert the select value
        select.value = originalValue;
    } finally {
        select.disabled = false;
    }
}

function showError(message) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `<div class="error">${message}</div>`;
    setTimeout(() => {
        messageDiv.innerHTML = '';
    }, 5000);
}

function showSuccess(message) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `<div class="success">${message}</div>`;
    setTimeout(() => {
        messageDiv.innerHTML = '';
    }, 3000);
}
