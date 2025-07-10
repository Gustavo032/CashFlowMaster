// CashFlowMaster JavaScript Functions

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize auto-save functionality
    initializeAutoSave();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Initialize notification system
    initializeNotifications();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize form validation
function initializeFormValidation() {
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
}

// Initialize auto-save functionality
function initializeAutoSave() {
    const autoSaveInputs = document.querySelectorAll('[data-auto-save]');
    
    autoSaveInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            debounce(function() {
                saveFormData(input.closest('form'));
            }, 2000)();
        });
    });
}

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Save form data to localStorage
function saveFormData(form) {
    if (!form) return;
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    const formId = form.id || 'default_form';
    localStorage.setItem(`cashflow_${formId}`, JSON.stringify(data));
    
    showNotification('Dados salvos automaticamente', 'success');
}

// Load form data from localStorage
function loadFormData(formId) {
    const savedData = localStorage.getItem(`cashflow_${formId}`);
    
    if (savedData) {
        const data = JSON.parse(savedData);
        
        for (let [key, value] of Object.entries(data)) {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }
    }
}

// Initialize keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + S to save
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            const activeForm = document.querySelector('form:focus-within');
            if (activeForm) {
                activeForm.requestSubmit();
            }
        }
        
        // Ctrl/Cmd + N to create new
        if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
            event.preventDefault();
            const createButton = document.querySelector('[data-bs-toggle="modal"][data-bs-target*="create"]');
            if (createButton) {
                createButton.click();
            }
        }
        
        // Escape to close modals
        if (event.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modalInstance = bootstrap.Modal.getInstance(openModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }
        }
    });
}

// Initialize notification system
function initializeNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(function() {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// File upload handling
function handleFileUpload(input, callback) {
    const file = input.files[0];
    if (!file) return;
    
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'text/csv', 'application/vnd.ms-excel', 'text/plain'];
    
    if (file.size > maxSize) {
        showNotification('Arquivo muito grande. Tamanho máximo: 10MB', 'error');
        input.value = '';
        return;
    }
    
    if (!allowedTypes.includes(file.type)) {
        showNotification('Tipo de arquivo não suportado', 'error');
        input.value = '';
        return;
    }
    
    if (callback) {
        callback(file);
    }
}

// Format currency values
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Texto copiado para a área de transferência', 'success');
    }).catch(function() {
        showNotification('Erro ao copiar texto', 'error');
    });
}

// Confirm action
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Form validation helpers
function validateRequired(input) {
    const value = input.value.trim();
    if (!value) {
        showFieldError(input, 'Este campo é obrigatório');
        return false;
    }
    clearFieldError(input);
    return true;
}

function validateEmail(input) {
    const value = input.value.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (value && !emailRegex.test(value)) {
        showFieldError(input, 'Email inválido');
        return false;
    }
    clearFieldError(input);
    return true;
}

function validateCurrency(input) {
    const value = input.value.trim();
    const currencyRegex = /^-?\d+([.,]\d{2})?$/;
    
    if (value && !currencyRegex.test(value)) {
        showFieldError(input, 'Valor monetário inválido');
        return false;
    }
    clearFieldError(input);
    return true;
}

function showFieldError(input, message) {
    clearFieldError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    input.classList.add('is-invalid');
    input.parentNode.appendChild(errorDiv);
}

function clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Table utilities
function sortTable(table, columnIndex, ascending = true) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();
        
        if (ascending) {
            return aValue.localeCompare(bValue, 'pt-BR', { numeric: true });
        } else {
            return bValue.localeCompare(aValue, 'pt-BR', { numeric: true });
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

function filterTable(table, filterText, columnIndex = null) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        let showRow = false;
        
        if (columnIndex !== null) {
            const cellText = row.cells[columnIndex].textContent.toLowerCase();
            showRow = cellText.includes(filterText.toLowerCase());
        } else {
            const rowText = row.textContent.toLowerCase();
            showRow = rowText.includes(filterText.toLowerCase());
        }
        
        row.style.display = showRow ? '' : 'none';
    });
}

// Export utilities
function exportTableToCSV(table, filename = 'export.csv') {
    const rows = table.querySelectorAll('tr');
    const csvContent = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = Array.from(cols).map(col => {
            return '"' + col.textContent.replace(/"/g, '""') + '"';
        });
        csvContent.push(rowData.join(','));
    });
    
    const blob = new Blob([csvContent.join('\n')], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Loading states
function showLoading(element) {
    element.classList.add('loading');
    element.disabled = true;
}

function hideLoading(element) {
    element.classList.remove('loading');
    element.disabled = false;
}

// Utility functions for specific features
function formatAccountNumber(accountNumber) {
    return accountNumber.replace(/(\d{1,3})(\d{1,3})(\d{1,3})(\d{1,3})(\d{1,3})/g, '$1.$2.$3.$4.$5');
}

function normalizeText(text) {
    return text.toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^\w\s]/g, '')
        .trim();
}

// Global error handler
window.addEventListener('error', function(event) {
    console.error('JavaScript Error:', event.error);
    showNotification('Ocorreu um erro inesperado. Tente recarregar a página.', 'error');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled Promise Rejection:', event.reason);
    showNotification('Ocorreu um erro de conexão. Verifique sua internet.', 'error');
});

// Export functions for use in other scripts
window.CashFlowMaster = {
    showNotification,
    formatCurrency,
    formatDate,
    copyToClipboard,
    confirmAction,
    validateRequired,
    validateEmail,
    validateCurrency,
    sortTable,
    filterTable,
    exportTableToCSV,
    showLoading,
    hideLoading,
    formatAccountNumber,
    normalizeText
};
