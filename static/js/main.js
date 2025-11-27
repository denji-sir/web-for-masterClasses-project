// Портал мастер-классов - Основной JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех компонентов
    initToasts();
    initFormValidation();
    initConfirmDialogs();
    initAutoHideAlerts();
    initLoadingSpinner();
    initDynamicSearch();
    initSearchAutocomplete();
    initInfiniteScroll();
});

/**
 * Инициализация toast уведомлений
 */
function initToasts() {
    const toastElList = document.querySelectorAll('.toast');
    toastElList.forEach(function(toastEl) {
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
    });
}

/**
 * Автоматическое скрытие алертов через 5 секунд
 */
function initAutoHideAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}


function initFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
   
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validateEmail(input);
        });
    });
    

    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validatePhone(input);
        });
    });
}

/**
 * Валидация email адреса
 */
function validateEmail(input) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const isValid = emailRegex.test(input.value);
    
    if (input.value && !isValid) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        showFieldError(input, 'Введите корректный email адрес');
    } else if (input.value) {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
        hideFieldError(input);
    }
    
    return isValid;
}

/**
 * Валидация номера телефона
 */
function validatePhone(input) {
    const phoneRegex = /^[\d\s\+\-\(\)]+$/;
    const isValid = phoneRegex.test(input.value);
    
    if (input.value && !isValid) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        showFieldError(input, 'Введите корректный номер телефона');
    } else if (input.value) {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
        hideFieldError(input);
    }
    
    return isValid;
}

/**
 * Показать ошибку поля
 */
function showFieldError(input, message) {
    let feedback = input.parentElement.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        input.parentElement.appendChild(feedback);
    }
    feedback.textContent = message;
}

/**
 * Скрыть ошибку поля
 */
function hideFieldError(input) {
    const feedback = input.parentElement.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.textContent = '';
    }
}

/**
 * Диалоги подтверждения для опасных действий
 */
function initConfirmDialogs() {
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const message = button.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
}

/**
 * Индикатор загрузки
 */
function initLoadingSpinner() {
    // Создаем overlay для загрузки
    const spinnerHTML = `
        <div id="loadingSpinner" class="spinner-overlay hidden">
            <div class="spinner-border text-light" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">Загрузка...</span>
            </div>
        </div>
    `;
    
    if (!document.getElementById('loadingSpinner')) {
        document.body.insertAdjacentHTML('beforeend', spinnerHTML);
    }
}

/**
 * Показать индикатор загрузки
 */
function showLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.remove('hidden');
    }
}

/**
 * Скрыть индикатор загрузки
 */
function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.add('hidden');
    }
}

/**
 * Показать toast уведомление
 */
function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    // Удаляем элемент после скрытия
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Получить или создать контейнер для toast
 */
function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    return container;
}

/**
 * Форматирование даты
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('ru-RU', options);
}

/**
 * Дебаунс функция для оптимизации поиска
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Плавная прокрутка к элементу
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

/**
 * Копирование текста в буфер обмена
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Скопировано в буфер обмена', 'success');
        }).catch(function(err) {
            console.error('Ошибка копирования:', err);
            showToast('Не удалось скопировать', 'error');
        });
    } else {
        // Fallback для старых браузеров
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('Скопировано в буфер обмена', 'success');
        } catch (err) {
            console.error('Ошибка копирования:', err);
            showToast('Не удалось скопировать', 'error');
        }
        document.body.removeChild(textarea);
    }
}

/**
 * Динамическая фильтрация без перезагрузки страницы
 * Требование: 8.1
 */
function initDynamicSearch() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) return;
    
    const filterInputs = searchForm.querySelectorAll('select, input[type="date"], input[type="number"]');
    const searchQuery = document.getElementById('searchQuery');
    
    // Дебаунс для текстового поиска
    if (searchQuery) {
        const debouncedSearch = debounce(function() {
            performDynamicSearch();
        }, 500);
        
        searchQuery.addEventListener('input', debouncedSearch);
    }
    
    // Мгновенная фильтрация для селектов и других полей
    filterInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            performDynamicSearch();
        });
    });
}

/**
 * Выполнить динамический поиск через AJAX
 */
function performDynamicSearch() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) return;
    
    const formData = new FormData(searchForm);
    const params = new URLSearchParams(formData);
    
    // Добавляем параметр для AJAX запроса
    params.append('ajax', '1');
    
    showLoading();
    
    fetch('/search?' + params.toString(), {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        updateSearchResults(data);
        hideLoading();
        
        // Обновляем URL без перезагрузки страницы
        const newUrl = '/search?' + params.toString().replace('ajax=1&', '').replace('&ajax=1', '').replace('ajax=1', '');
        if (newUrl !== window.location.pathname + window.location.search) {
            window.history.pushState({}, '', newUrl);
        }
    })
    .catch(error => {
        console.error('Ошибка поиска:', error);
        hideLoading();
        showToast('Ошибка при выполнении поиска', 'error');
    });
}

/**
 * Обновить результаты поиска на странице
 */
function updateSearchResults(data) {
    const resultsContainer = document.querySelector('.row.row-cols-1.row-cols-md-2.row-cols-lg-3');
    if (!resultsContainer) return;
    
    if (data.masterclasses && data.masterclasses.length > 0) {
        let html = '';
        data.masterclasses.forEach(function(mc) {
            html += createMasterclassCard(mc);
        });
        resultsContainer.innerHTML = html;
        
        // Обновляем счетчик результатов
        updateResultsCount(data.masterclasses.length);
    } else {
        resultsContainer.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 
                    По вашему запросу ничего не найдено. Попробуйте изменить параметры поиска.
                </div>
            </div>
        `;
        updateResultsCount(0);
    }
}

/**
 * Создать HTML карточки мастер-класса
 */
function createMasterclassCard(mc) {
    const availableSpots = mc.max_participants - mc.current_participants;
    const isFull = availableSpots <= 0;
    
    let spotsText = '';
    if (availableSpots === 1) spotsText = 'место';
    else if (availableSpots < 5) spotsText = 'места';
    else spotsText = 'мест';
    
    let ratingHtml = '';
    if (mc.rating && mc.rating > 0) {
        const stars = '⭐'.repeat(Math.round(mc.rating));
        let reviewText = 'отзывов';
        if (mc.review_count === 1) reviewText = 'отзыв';
        else if (mc.review_count < 5) reviewText = 'отзыва';
        
        ratingHtml = `
            <div class="mb-2">
                <span class="text-warning">${stars}</span>
                <small class="text-muted">${mc.rating} (${mc.review_count} ${reviewText})</small>
            </div>
        `;
    }
    
    const description = mc.description && mc.description.length > 150 
        ? mc.description.substring(0, 150) + '...' 
        : mc.description || '';
    
    return `
        <div class="col">
            <div class="card h-100 shadow-sm hover-shadow">
                <div class="card-body">
                    <h5 class="card-title">${mc.title}</h5>
                    <p class="card-text text-muted">${description}</p>
                    
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="bi bi-calendar-event"></i> ${mc.date_time}
                        </small>
                    </div>
                    
                    ${mc.category ? `<div class="mb-2"><span class="badge bg-secondary">${mc.category}</span></div>` : ''}
                    
                    ${ratingHtml}
                    
                    <div class="mb-2">
                        ${mc.price ? `<strong class="text-primary">${mc.price} ₽</strong>` : '<strong class="text-success">Бесплатно</strong>'}
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="bi bi-people"></i> ${mc.current_participants}/${mc.max_participants} участников
                        </small>
                    </div>
                    
                    <div class="mb-3">
                        ${isFull 
                            ? '<span class="badge bg-danger">Мест нет</span>' 
                            : `<span class="badge bg-success">Осталось ${availableSpots} ${spotsText}</span>`
                        }
                    </div>
                </div>
                
                <div class="card-footer bg-transparent">
                    <a href="/masterclass/${mc.id}" class="btn btn-primary w-100">Подробнее</a>
                </div>
            </div>
        </div>
    `;
}

/**
 * Обновить счетчик результатов
 */
function updateResultsCount(count) {
    const countElement = document.querySelector('h3.mb-0');
    if (!countElement) return;
    
    let text = '';
    if (count === 0) {
        text = 'Мастер-классы не найдены';
    } else {
        let word = 'мастер-классов';
        if (count === 1) word = 'мастер-класс';
        else if (count < 5) word = 'мастер-класса';
        text = `Найдено: ${count} ${word}`;
    }
    
    countElement.textContent = text;
}

/**
 * Автодополнение в поиске
 * Требование: 8.5
 */
function initSearchAutocomplete() {
    const searchQuery = document.getElementById('searchQuery');
    if (!searchQuery) return;
    
    let autocompleteList = null;
    
    const debouncedAutocomplete = debounce(function() {
        const query = searchQuery.value.trim();
        
        if (query.length < 2) {
            hideAutocomplete();
            return;
        }
        
        fetch('/api/autocomplete?q=' + encodeURIComponent(query))
            .then(response => response.json())
            .then(data => {
                showAutocomplete(data.suggestions);
            })
            .catch(error => {
                console.error('Ошибка автодополнения:', error);
            });
    }, 300);
    
    searchQuery.addEventListener('input', debouncedAutocomplete);
    
    searchQuery.addEventListener('focus', function() {
        if (searchQuery.value.trim().length >= 2) {
            debouncedAutocomplete();
        }
    });
    
    // Скрыть автодополнение при клике вне поля
    document.addEventListener('click', function(e) {
        if (e.target !== searchQuery && !e.target.closest('.autocomplete-list')) {
            hideAutocomplete();
        }
    });
    
    // Навигация клавиатурой
    searchQuery.addEventListener('keydown', function(e) {
        if (!autocompleteList) return;
        
        const items = autocompleteList.querySelectorAll('.autocomplete-item');
        let currentFocus = -1;
        
        for (let i = 0; i < items.length; i++) {
            if (items[i].classList.contains('autocomplete-active')) {
                currentFocus = i;
                break;
            }
        }
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentFocus++;
            addActive(items, currentFocus);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentFocus--;
            addActive(items, currentFocus);
        } else if (e.key === 'Enter') {
            if (currentFocus > -1 && items[currentFocus]) {
                e.preventDefault();
                items[currentFocus].click();
            }
        } else if (e.key === 'Escape') {
            hideAutocomplete();
        }
    });
    
    function showAutocomplete(suggestions) {
        hideAutocomplete();
        
        if (!suggestions || suggestions.length === 0) return;
        
        autocompleteList = document.createElement('div');
        autocompleteList.className = 'autocomplete-list';
        autocompleteList.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            z-index: 1000;
            width: ${searchQuery.offsetWidth}px;
            max-height: 300px;
            overflow-y: auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        
        suggestions.forEach(function(suggestion) {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
            `;
            item.textContent = suggestion;
            
            item.addEventListener('mouseenter', function() {
                removeActive(autocompleteList.querySelectorAll('.autocomplete-item'));
                item.classList.add('autocomplete-active');
            });
            
            item.addEventListener('click', function() {
                searchQuery.value = suggestion;
                hideAutocomplete();
                performDynamicSearch();
            });
            
            autocompleteList.appendChild(item);
        });
        
        searchQuery.parentNode.style.position = 'relative';
        searchQuery.parentNode.appendChild(autocompleteList);
    }
    
    function hideAutocomplete() {
        if (autocompleteList) {
            autocompleteList.remove();
            autocompleteList = null;
        }
    }
    
    function addActive(items, index) {
        if (!items || items.length === 0) return;
        removeActive(items);
        
        if (index >= items.length) index = 0;
        if (index < 0) index = items.length - 1;
        
        items[index].classList.add('autocomplete-active');
        items[index].style.backgroundColor = '#e9ecef';
    }
    
    function removeActive(items) {
        items.forEach(function(item) {
            item.classList.remove('autocomplete-active');
            item.style.backgroundColor = '';
        });
    }
}

/**
 * Бесконечная прокрутка результатов поиска
 * Требование: 8.1
 */
function initInfiniteScroll() {
    const resultsContainer = document.querySelector('.row.row-cols-1.row-cols-md-2.row-cols-lg-3');
    if (!resultsContainer) return;
    
    let page = 1;
    let loading = false;
    let hasMore = true;
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting && !loading && hasMore) {
                loadMoreResults();
            }
        });
    }, {
        rootMargin: '100px'
    });
    
    // Создаем sentinel элемент для отслеживания
    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    sentinel.style.height = '1px';
    
    if (resultsContainer.parentNode) {
        resultsContainer.parentNode.appendChild(sentinel);
        observer.observe(sentinel);
    }
    
    function loadMoreResults() {
        if (loading || !hasMore) return;
        
        loading = true;
        page++;
        
        const searchForm = document.getElementById('searchForm');
        if (!searchForm) return;
        
        const formData = new FormData(searchForm);
        const params = new URLSearchParams(formData);
        params.append('page', page);
        params.append('ajax', '1');
        
        // Показываем индикатор загрузки
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'col-12 text-center my-4';
        loadingIndicator.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
        `;
        resultsContainer.appendChild(loadingIndicator);
        
        fetch('/search?' + params.toString(), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.remove();
            
            if (data.masterclasses && data.masterclasses.length > 0) {
                data.masterclasses.forEach(function(mc) {
                    resultsContainer.insertAdjacentHTML('beforeend', createMasterclassCard(mc));
                });
            } else {
                hasMore = false;
                observer.disconnect();
            }
            
            loading = false;
        })
        .catch(error => {
            console.error('Ошибка загрузки:', error);
            loadingIndicator.remove();
            loading = false;
            showToast('Ошибка при загрузке результатов', 'error');
        });
    }
}

// Экспорт функций для использования в других скриптах
window.MasterclassPortal = {
    showLoading,
    hideLoading,
    showToast,
    validateEmail,
    validatePhone,
    formatDate,
    debounce,
    scrollToElement,
    copyToClipboard,
    performDynamicSearch,
    createMasterclassCard
};
