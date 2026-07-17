let token = null;

window.onload = function() {
    token = localStorage.getItem('token');
    const email = localStorage.getItem('email');
    const role = localStorage.getItem('role');

    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    if (email) {
        document.getElementById('userEmail').textContent = email;
    }

    if (role) {
        document.getElementById('userRole').textContent = role;
    }

    // Verify token and check permissions
    verifyToken();
    fetchMetadata();
};

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
        const permissions = data.permissions || [];

        // Check if user has write:attendance permission
        if (!permissions.includes('write:attendance')) {
            document.getElementById('error').textContent = 'You do not have permission to upload files. Only admin and HR can upload.';
            document.querySelector('.form-group').style.display = 'none';
            document.querySelector('.btn-primary').style.display = 'none';
        }
    } catch (err) {
        console.error('Token verification failed:', err);
    }
}

async function fetchMetadata() {
    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/attendance/metadata',
            {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            },
        );

        if (!res.ok) {
            console.error('Failed to fetch metadata');
            return;
        }

        const data = await res.json();
        const uploadedFiles = data.data;
        displayHistory(uploadedFiles);

    } catch (err) {
        console.error('Fetch metadata failed: ', err);
    }
}

async function displayHistory(files) {
    const container = document.getElementById('historyContainer');
    container.innerHTML = ''; // Clear existing content

    if (files.length === 0) {
        container.innerHTML = '<div class="no-files">No files uploaded yet</div>';
        return;
    }

    files.forEach(file => {
        const card = document.createElement('div');
        card.className = 'file-card';

        // Format date
        const uploadedDate = file.uploaded_at
            ? new Date(file.uploaded_at).toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            })
            : 'N/A';

        card.innerHTML = `
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">
                    <span class="file-meta-item"><strong>Uploaded by:</strong> ${file.uploaded_by}</span>
                    <span class="file-meta-item"><strong>Date:</strong> ${uploadedDate}</span>
                </div>
            </div>
            <div class="file-actions">
                <button class="btn-delete" onclick="deleteFile('${file.id}')">
                    Delete
                </button>
            </div>
        `;

        container.appendChild(card);
    });
}

async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file and all its attendance records?')) {
        return;
    }

    try {
        const res = await fetch(
            `http://127.0.0.1:8000/api/v1/attendance/${fileId}`,
            {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            },
        );

        if (res.status === 401) {
            alert('Session expired. Please login again.');
            logout();
            return;
        }

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || 'Delete failed');
            return;
        }

        // Show success and refresh
        alert(`Successfully deleted: ${data.filename}`);
        fetchMetadata(); // Refresh the list
    } catch (err) {
        alert('Failed to delete file');
        console.error(err);
    }
}

function goToHome() {
    window.location.href = '/index.html';
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    localStorage.removeItem('role');
    window.location.href = '/login.html';
}

async function uploadFile() {
    const fileInput = document.getElementById('file');
    const errorDiv = document.getElementById('error');
    const successDiv = document.getElementById('success');
    const loadingDiv = document.getElementById('loading');

    errorDiv.textContent = '';
    successDiv.style.display = 'none';

    if (!fileInput.files.length) {
        errorDiv.textContent = 'Please select a file.';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    loadingDiv.style.display = 'block';

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/attendance/upload',
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
            errorDiv.textContent = data.detail || 'Upload failed';
            return;
        }

        // Show success message
        successDiv.style.display = 'block';
        successDiv.innerHTML = `
            <strong>Success!</strong><br>
            File: ${data.filename}<br>
            Records created: ${data.records_created}<br>
            ${data.message}
        `;

        // Clear file input
        fileInput.value = '';

        // Refresh the upload history
        fetchMetadata();

        // Redirect to home after 3 seconds
        setTimeout(() => {
            window.location.href = '/index.html';
        }, 3000);
    } catch (err) {
        loadingDiv.style.display = 'none';
        errorDiv.textContent = 'Failed to connect to backend.';
        console.error(err);
    }
}
