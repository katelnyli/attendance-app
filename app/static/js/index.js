let token = null;
let userPermissions = [];
let userFullName = '';
let userRole = '';
let currentNames = [];

// Check authentication on page load
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

    const cachedRole = localStorage.getItem('role');
    if (cachedRole) {
        userRole = cachedRole;
        document.getElementById('userRole').textContent = userRole;
        if (userRole === 'admin') {
            document.getElementById('manageUsersBtn').style.display = 'inline-block';
        }
    }

    verifyToken();
};

function goToUsers() {
    window.location.href = '/users.html';
}

function goToUpload() {
    window.location.href = '/upload.html';
}

async function verifyToken() {
    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/auth/me',
            {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            },
        );

        if (!res.ok) {
            localStorage.removeItem('token');
            localStorage.removeItem('email');
            window.location.href = '/login.html';
            return;
        }

        const data = await res.json();
        document.getElementById('userEmail').textContent = data.email;
        localStorage.setItem('email', data.email);

        userPermissions = data.permissions || [];
        userFullName = data.full_name || '';
        userRole = data.role || '';

        if (userRole) {
            localStorage.setItem('role', userRole);
            document.getElementById('userRole').textContent = userRole;
        }

        if (userRole === 'admin') {
            document.getElementById('manageUsersBtn').style.display = 'inline-block';
        }

        // Show appropriate UI based on permissions
        const hasReadAll = userPermissions.includes('read:attendance');
        const hasWriteAttendance = userPermissions.includes('write:attendance');
        const hasReadSelf = userPermissions.includes('read:attendance:self');

        if (hasReadAll) {
            // Admin/HR - show full form
            document.getElementById('adminForm').style.display = 'block';
            if (hasWriteAttendance) {
                document.getElementById('uploadBtn').style.display = 'inline-block';
            }
        } else if (hasReadSelf) {
            // Regular user - show "View My Attendance" button
            document.getElementById('viewMyAttendanceBtn').style.display = 'inline-block';
        } else {
            // No permissions
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = 'You do not have permission to view attendance. Please contact your administrator.';
            errorDiv.style.background = '#fff3cd';
            errorDiv.style.padding = '15px';
            errorDiv.style.borderRadius = '4px';
            errorDiv.style.border = '1px solid #ffc107';
        }
    } catch (err) {
        console.error('Token verification failed:', err);
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    localStorage.removeItem('role');
    window.location.href = '/login.html';
}

async function viewMyAttendance() {
    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');
    const table = document.getElementById('resultsTable');
    const tbody = table.querySelector('tbody');

    errorDiv.textContent = '';
    table.style.display = 'none';
    tbody.innerHTML = '';
    loadingDiv.style.display = 'block';

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/attendance/me',
            {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            },
        );

        loadingDiv.style.display = 'none';

        if (res.status === 401) {
            alert('Session expired. Please login again.');
            logout();
            return;
        }

        const data = await res.json();

        if (!res.ok) {
            errorDiv.textContent = data.detail || 'Server error';
            return;
        }

        if (data.data && data.data.length > 0) {
            table.style.display = '';
            data.data.forEach((row) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.name}</td>
                    <td>${row.total_hours.toFixed(2)}</td>
                    <td>${row.date ? new Date(row.date).toLocaleDateString('zh-CN') : 'N/A'}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            errorDiv.textContent = 'No attendance records found for you.';
        }
    } catch (err) {
        loadingDiv.style.display = 'none';
        errorDiv.textContent = 'Failed to connect to backend.';
        console.error(err);
    }
}

async function submitForm() {
    const namesInput = document.getElementById('namesInput');
    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');
    const table = document.getElementById('resultsTable');
    const tbody = table.querySelector('tbody');

    errorDiv.textContent = '';
    table.style.display = 'none';
    tbody.innerHTML = '';
    document.getElementById('exportBtn').style.display = 'none';

    const names = namesInput.value
        .split(/[,，、]/)
        .map((n) => n.trim())
        .filter((n) => n.length > 0);

    if (names.length === 0) {
        errorDiv.textContent = 'Please enter at least one name.';
        return;
    }

    currentNames = names;

    const formData = new FormData();
    names.forEach((name) => formData.append('names', name));

    loadingDiv.style.display = 'block';

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/attendance/',
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            },
        );

        loadingDiv.style.display = 'none';

        if (res.status === 401) {
            alert('Session expired. Please login again.');
            logout();
            return;
        }

        const data = await res.json();

        if (!res.ok) {
            errorDiv.textContent = data.detail || 'Server error';
            return;
        }

        if (data.data && data.data.length > 0) {
            table.style.display = '';
            data.data.forEach((row) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.name}</td>
                    <td>${row.total_hours.toFixed(2)}</td>
                    <td>${row.date ? new Date(row.date).toLocaleDateString('zh-CN') : 'N/A'}</td>
                `;
                tbody.appendChild(tr);
            });

            // Show export button if user has export permission
            if (userPermissions.includes('export:attendance')) {
                document.getElementById('exportBtn').style.display = 'inline-block';
            }
        } else {
            errorDiv.textContent = 'No records found for the specified names.';
        }
    } catch (err) {
        loadingDiv.style.display = 'none';
        errorDiv.textContent = 'Failed to connect to backend.';
        console.error(err);
    }
}

async function exportExcel() {
    if (currentNames.length === 0) {
        alert('Please search for names first');
        return;
    }

    const formData = new FormData();
    currentNames.forEach((name) => formData.append('names', name));

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/attendance/export',
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            },
        );

        if (res.status === 401) {
            alert('Session expired. Please login again.');
            logout();
            return;
        }

        if (!res.ok) {
            alert('Export failed');
            return;
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'attendance_export.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert('Export failed');
        console.error(err);
    }
}
