// main.js
// Переключение темы
document.addEventListener('DOMContentLoaded', function() {
    // Тема
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            const icon = this.querySelector('i');
            if (newTheme === 'dark') {
                icon.className = 'bi bi-sun me-2';
                this.textContent = 'Светлая тема';
            } else {
                icon.className = 'bi bi-moon me-2';
                this.textContent = 'Темная тема';
            }
        });
        
        // Установка правильной иконки при загрузке
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const icon = themeToggle.querySelector('i');
        if (currentTheme === 'dark') {
            icon.className = 'bi bi-sun me-2';
            themeToggle.textContent = 'Светлая тема';
        }
    }
    
    // Управление уведомлениями
    const notificationToggle = document.getElementById('notificationToggle');
    const notificationDropdown = document.getElementById('notificationDropdown');
    
    if (notificationToggle && notificationDropdown) {
        notificationToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationDropdown.style.display = 
                notificationDropdown.style.display === 'block' ? 'none' : 'block';
        });
        
        // Закрытие при клике вне области
        document.addEventListener('click', function(e) {
            if (!notificationDropdown.contains(e.target) && !notificationToggle.contains(e.target)) {
                notificationDropdown.style.display = 'none';
            }
        });
    }
    
    // Автоматическое скрытие уведомлений
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            setTimeout(() => bsAlert.close(), 5000);
        });
    }, 3000);
    
    // Анимация загрузки контента
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 100}ms`;
        card.classList.add('animate__animated', 'animate__fadeInUp');
    });
    
    // Подтверждение действий
    const confirmForms = document.querySelectorAll('form[data-confirm]');
    confirmForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm(this.getAttribute('data-confirm') || 'Вы уверены?')) {
                e.preventDefault();
            }
        });
    });
    
    // Копирование текста
    window.copyToClipboard = async function(text, successMessage = 'Скопировано!') {
        try {
            await navigator.clipboard.writeText(text);
            
            // Показываем уведомление
            const toast = document.createElement('div');
            toast.className = 'position-fixed bottom-0 end-0 p-3';
            toast.innerHTML = `
                <div class="toast show" role="alert">
                    <div class="toast-body d-flex align-items-center">
                        <i class="bi bi-check-circle-fill text-success me-2"></i>
                        ${successMessage}
                    </div>
                </div>
            `;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.remove();
            }, 2000);
        } catch (err) {
            console.error('Ошибка копирования:', err);
            alert('Не удалось скопировать текст');
        }
    };
    
    // Валидация форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const inputs = form.querySelectorAll('[required]');
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('is-invalid');
                    
                    // Добавляем сообщение об ошибке
                    if (!input.nextElementSibling?.classList?.contains('invalid-feedback')) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'invalid-feedback';
                        errorDiv.textContent = 'Это поле обязательно для заполнения';
                        input.parentNode.appendChild(errorDiv);
                    }
                } else {
                    input.classList.remove('is-invalid');
                    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
                    if (errorDiv) errorDiv.remove();
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                // Анимация для неправильных полей
                const invalidInputs = form.querySelectorAll('.is-invalid');
                invalidInputs.forEach(input => {
                    input.classList.add('animate__animated', 'animate__shakeX');
                    setTimeout(() => {
                        input.classList.remove('animate__animated', 'animate__shakeX');
                    }, 1000);
                });
            }
        });
    });
    
    // Автоматическое обновление времени
    function updateRelativeTimes() {
        document.querySelectorAll('.relative-time').forEach(element => {
            const timestamp = element.getAttribute('data-timestamp');
            if (timestamp) {
                const time = new Date(timestamp);
                const now = new Date();
                const diff = Math.floor((now - time) / 1000);
                
                if (diff < 60) element.textContent = 'только что';
                else if (diff < 3600) element.textContent = `${Math.floor(diff / 60)} мин назад`;
                else if (diff < 86400) element.textContent = `${Math.floor(diff / 3600)} ч назад`;
                else element.textContent = `${Math.floor(diff / 86400)} дн назад`;
            }
        });
    }
    
    setInterval(updateRelativeTimes, 60000);
    updateRelativeTimes();
});