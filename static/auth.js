class AuthManager {
    constructor() {
        this.baseURL = window.location.origin;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkExistingAuth();
    }

    setupEventListeners() {
        // Form toggle
        document.getElementById('showRegister').addEventListener('click', () => {
            this.toggleForm('register');
        });

        document.getElementById('showLogin').addEventListener('click', () => {
            this.toggleForm('login');
        });

        // Form submissions
        document.getElementById('loginSubmit').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.getElementById('registerSubmit').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });
    }

    toggleForm(formType) {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');

        if (formType === 'register') {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
        } else {
            registerForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
        }
    }

    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            this.showError('Please fill in all fields');
            return;
        }

        this.setLoading('login', true);

        try {
            const response = await fetch(`${this.baseURL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                // Store token
                localStorage.setItem('auth_token', data.access_token);
                localStorage.setItem('user_info', JSON.stringify(data.user));

                this.showSuccess('Login successful!');

                // Check container status and redirect
                setTimeout(() => {
                    this.checkContainerStatusAndRedirect();
                }, 1000);

            } else {
                this.showError(data.error || 'Login failed');
            }

        } catch (error) {
            console.error('Login error:', error);
            this.showError('Network error. Please try again.');
        } finally {
            this.setLoading('login', false);
        }
    }

    async handleRegister() {
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // Validation
        if (!username || !email || !password || !confirmPassword) {
            this.showError('Please fill in all fields');
            return;
        }

        if (username.length < 3) {
            this.showError('Username must be at least 3 characters');
            return;
        }

        if (password.length < 6) {
            this.showError('Password must be at least 6 characters');
            return;
        }

        if (password !== confirmPassword) {
            this.showError('Passwords do not match');
            return;
        }

        if (!this.isValidEmail(email)) {
            this.showError('Please enter a valid email address');
            return;
        }

        this.setLoading('register', true);

        try {
            const response = await fetch(`${this.baseURL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username.trim(),
                    email: email.trim().toLowerCase(),
                    password
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Store token
                localStorage.setItem('auth_token', data.access_token);
                localStorage.setItem('user_info', JSON.stringify(data.user));

                this.showSuccess('Account created successfully!');

                // Show container setup
                setTimeout(() => {
                    this.showContainerSetup();
                }, 1000);

            } else {
                this.showError(data.error || 'Registration failed');
            }

        } catch (error) {
            console.error('Registration error:', error);
            this.showError('Network error. Please try again.');
        } finally {
            this.setLoading('register', false);
        }
    }

    async checkContainerStatusAndRedirect() {
        const token = localStorage.getItem('auth_token');

        if (!token) {
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/auth/container-status`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();

            if (response.ok) {
                if (data.openapi_configured) {
                    // User is fully set up, go to dashboard
                    window.location.href = '/';
                } else {
                    // Show container setup
                    this.showContainerSetup();
                }
            } else {
                this.showError('Failed to check container status');
            }

        } catch (error) {
            console.error('Container status error:', error);
            // Continue to dashboard anyway
            window.location.href = '/';
        }
    }

    showContainerSetup() {
        const modal = document.getElementById('setupModal');
        modal.classList.remove('hidden');

        // Simulate container setup process
        this.simulateContainerSetup();
    }

    async simulateContainerSetup() {
        const statusElement = document.getElementById('setupStatus');
        const continueBtn = document.getElementById('continueToApp');

        const steps = [
            'Provisioning your container...',
            'Setting up OpenD environment...',
            'Configuring security settings...',
            'Initializing trading environment...',
            'Setup complete!'
        ];

        for (let i = 0; i < steps.length; i++) {
            statusElement.textContent = steps[i];
            await this.delay(2000); // 2 seconds per step
        }

        // Show continue button
        continueBtn.classList.remove('hidden');
    }

    checkExistingAuth() {
        const token = localStorage.getItem('auth_token');

        if (token) {
            // Check if token is still valid
            this.verifyToken(token);
        }
    }

    async verifyToken(token) {
        try {
            const response = await fetch(`${this.baseURL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                // Token is valid, redirect to dashboard
                window.location.href = '/';
            } else {
                // Token is invalid, clear it
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
            }
        } catch (error) {
            console.error('Token verification error:', error);
            // Clear invalid token
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
        }
    }

    setLoading(form, loading) {
        const btn = document.getElementById(`${form}Btn`);
        const btnText = document.getElementById(`${form}BtnText`);
        const spinner = document.getElementById(`${form}Spinner`);

        btn.disabled = loading;

        if (loading) {
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');
        } else {
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }

    showError(message) {
        const toast = document.getElementById('errorToast');
        const messageElement = document.getElementById('errorMessage');

        messageElement.textContent = message;
        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 5000);
    }

    showSuccess(message) {
        const toast = document.getElementById('successToast');
        const messageElement = document.getElementById('successMessage');

        messageElement.textContent = message;
        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

function goToDashboard() {
    window.location.href = '/';
}

// Initialize auth manager when page loads
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});