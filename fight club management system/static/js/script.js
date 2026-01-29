document.addEventListener('DOMContentLoaded', function() {
    // Modal functionality
    const modals = document.querySelectorAll('.modal');
    const closeButtons = document.querySelectorAll('.close-btn');
    
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    window.addEventListener('click', function(event) {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Item card click handlers
    document.querySelectorAll('.item-card').forEach(card => {
        card.addEventListener('click', function() {
            const entityType = this.dataset.entityType;
            const entityId = this.dataset.entityId;
            loadEntityDetails(entityType, entityId);
        });
    });
    
    // Search form submission
    const searchForms = document.querySelectorAll('form[role="search"]');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchInput = this.querySelector('input[type="search"]');
            const searchTerm = searchInput.value;
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('search', searchTerm);
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        });
    });
    
    // Login/Signup form switching
    const loginContainer = document.querySelector('.login-container');
    if (loginContainer) {
        const switchTexts = document.querySelectorAll('.switch-text');
        switchTexts.forEach(text => {
            text.addEventListener('click', function() {
                loginContainer.classList.toggle('show-signup');
            });
        });
    }
    
    // Form validation
    const forms = document.querySelectorAll('form:not([role="search"])');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredInputs = this.querySelectorAll('[required]');
            let isValid = true;
            
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#f44336';
                    showFlashMessage('Please fill in all required fields', 'error');
                } else {
                    input.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // Initialize tooltips
    initTooltips();
    
    // Auto-hide flash messages
    autoHideFlashMessages();
});

function loadEntityDetails(entityType, entityId) {
    const modal = document.getElementById('viewModal');
    const modalContent = modal.querySelector('.modal-content');
    
    modalContent.innerHTML = `
        <div class="loading"></div>
    `;
    modal.style.display = 'block';
    
    fetch(`/view/${entityType}/${entityId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            modalContent.innerHTML = html;
            attachModalEventListeners();
        })
        .catch(error => {
            console.error('Error loading entity details:', error);
            modalContent.innerHTML = `
                <span class="close-btn">&times;</span>
                <div class="error-message">
                    <h2>Error</h2>
                    <p>Failed to load details. Please try again.</p>
                </div>
            `;
        });
}

function attachModalEventListeners() {
    // Re-attach close button listener
    const closeBtn = document.querySelector('.close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    }
    
    // Attach edit form submission handlers
    const editForms = document.querySelectorAll('.edit-form');
    editForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            submitEditForm(this);
        });
    });
    
    // Attach delete button handlers
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const entityType = this.dataset.entityType;
            const entityId = this.dataset.entityId;
            confirmDelete(entityType, entityId);
        });
    });
    
    // Attach relationship action buttons
    const actionButtons = document.querySelectorAll('.action-btn[data-action]');
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.action;
            const entityId = this.dataset.entityId;
            const targetId = this.dataset.targetId;
            performAction(action, entityId, targetId);
        });
    });
}

function submitEditForm(form) {
    const formData = new FormData(form);
    const entityType = form.dataset.entityType;
    const entityId = form.dataset.entityId;
    
    fetch(`/api/update/${entityType}/${entityId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showFlashMessage('Update successful!', 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showFlashMessage(data.error || 'Update failed', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showFlashMessage('An error occurred', 'error');
    });
}

function confirmDelete(entityType, entityId) {
    if (confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
        fetch(`/api/delete/${entityType}/${entityId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showFlashMessage('Deleted successfully!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showFlashMessage(data.error || 'Delete failed', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showFlashMessage('An error occurred', 'error');
        });
    }
}

function performAction(action, entityId, targetId) {
    let url = '';
    const formData = new FormData();
    
    switch(action) {
        case 'add_trainer_to_fighter':
            url = '/api/fighter/add_trainer';
            formData.append('fighter_id', entityId);
            formData.append('trainer_id', targetId);
            break;
        case 'remove_trainer_from_fighter':
            url = '/api/fighter/remove_trainer';
            formData.append('fighter_id', entityId);
            formData.append('trainer_id', targetId);
            break;
        case 'add_fighter_to_gym':
            url = '/api/gym/add_fighter';
            formData.append('gym_id', entityId);
            formData.append('fighter_id', targetId);
            break;
        case 'add_trainer_to_gym':
            url = '/api/gym/add_trainer';
            formData.append('gym_id', entityId);
            formData.append('trainer_id', targetId);
            break;
        case 'remove_fighter_from_gym':
            url = '/api/gym/remove_fighter';
            formData.append('fighter_id', targetId);
            break;
        case 'remove_trainer_from_gym':
            url = '/api/gym/remove_trainer';
            formData.append('trainer_id', targetId);
            break;
        case 'add_fighter_to_trainer':
            url = '/api/trainer/add_fighter';
            formData.append('trainer_id', entityId);
            formData.append('fighter_id', targetId);
            break;
        case 'remove_fighter_from_trainer':
            url = '/api/trainer/remove_fighter';
            formData.append('trainer_id', entityId);
            formData.append('fighter_id', targetId);
            break;
        case 'change_fighter_gym':
            url = `/api/update/fighter/${entityId}`;
            formData.append('field', 'gym_id');
            formData.append('value', targetId);
            break;
        case 'change_trainer_gym':
            url = `/api/update/trainer/${entityId}`;
            formData.append('field', 'gym_id');
            formData.append('value', targetId);
            break;
    }
    
    if (url) {
        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showFlashMessage('Action successful!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showFlashMessage(data.error || 'Action failed', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showFlashMessage('An error occurred', 'error');
        });
    }
}

function showFlashMessage(message, type = 'info') {
    const flashContainer = document.querySelector('.flash-messages');
    if (!flashContainer) {
        const newContainer = document.createElement('div');
        newContainer.className = 'flash-messages';
        document.body.appendChild(newContainer);
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `flash-message ${type}`;
    messageDiv.textContent = message;
    
    document.querySelector('.flash-messages').appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.dataset.tooltip;
            tooltip.style.position = 'absolute';
            tooltip.style.background = 'var(--dark-red)';
            tooltip.style.color = 'var(--paper)';
            tooltip.style.padding = '0.5rem';
            tooltip.style.borderRadius = '4px';
            tooltip.style.zIndex = '10000';
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = (rect.top - 40) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2) + 'px';
            tooltip.style.transform = 'translateX(-50%)';
            
            document.body.appendChild(tooltip);
            
            this.tooltipElement = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this.tooltipElement) {
                this.tooltipElement.remove();
            }
        });
    });
}

function autoHideFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease';
            setTimeout(() => message.remove(), 500);
        }, 3000);
    });
}

// Utility function for making API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Debounce function for search inputs
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