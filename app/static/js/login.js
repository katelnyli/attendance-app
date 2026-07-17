// Check if already logged in
window.onload = function() {
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = '/index.html';
    }
};

async function login(event) {
    event.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');

    errorDiv.textContent = '';

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/auth/login',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            },
        );

        const data = await res.json();

        if (!res.ok) {
            errorDiv.textContent = data.detail || 'Login failed';
            return;
        }

        // Save token to localStorage
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('email', email);

        // Redirect to home page
        window.location.href = '/index.html';
    } catch (err) {
        errorDiv.textContent = 'Failed to connect to server';
        console.error(err);
    }
}
