async function register(event) {
    event.preventDefault();

    const fullName = document.getElementById('fullName').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('registerError');
    const successDiv = document.getElementById('registerSuccess');

    errorDiv.textContent = '';
    successDiv.textContent = '';

    // Validate passwords match
    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        return;
    }

    try {
        const res = await fetch(
            'http://127.0.0.1:8000/api/v1/auth/register',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password, full_name: fullName }),
            },
        );

        const data = await res.json();

        if (!res.ok) {
            errorDiv.textContent = data.detail || 'Registration failed';
            return;
        }

        successDiv.textContent = 'Registration successful! Redirecting to login...';

        // Redirect to login page after 2 seconds
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 2000);
    } catch (err) {
        errorDiv.textContent = 'Failed to connect to server';
        console.error(err);
    }
}
