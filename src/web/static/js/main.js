// Job Hunt Tracker - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile menu
    initMobileMenu();

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Set default date to today for date inputs
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(input => {
        if (!input.value) {
            input.value = today;
        }
    });

    // Set default time to next hour for time inputs
    const timeInputs = document.querySelectorAll('input[type="time"]');
    timeInputs.forEach(input => {
        if (!input.value) {
            const now = new Date();
            now.setHours(now.getHours() + 1);
            now.setMinutes(0);
            input.value = now.toTimeString().slice(0, 5);
        }
    });

    // Initialize drag and drop for pipeline board
    initPipelineDragDrop();
});

// === Mobile Menu ===

function initMobileMenu() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');

    if (!hamburger || !navMenu) return;

    // Toggle menu on hamburger click
    hamburger.addEventListener('click', function(e) {
        e.stopPropagation();
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
    });

    // Close menu when clicking a link
    const navLinks = navMenu.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (navMenu.classList.contains('active') &&
            !navMenu.contains(e.target) &&
            !hamburger.contains(e.target)) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}

// === Drag and Drop for Pipeline Board ===

function initPipelineDragDrop() {
    const cards = document.querySelectorAll('.pipeline-card');
    const columns = document.querySelectorAll('.column-body');

    if (!cards.length || !columns.length) return;

    // Make cards draggable
    cards.forEach(card => {
        card.setAttribute('draggable', 'true');

        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });

    // Make columns drop targets
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('dragenter', handleDragEnter);
        column.addEventListener('dragleave', handleDragLeave);
        column.addEventListener('drop', handleDrop);
    });
}

let draggedCard = null;

function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');

    // Set drag data
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.appId);

    // Add slight delay for visual feedback
    setTimeout(() => {
        this.style.opacity = '0.5';
    }, 0);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    this.style.opacity = '1';

    // Remove all drag-over states
    document.querySelectorAll('.column-body').forEach(col => {
        col.classList.remove('drag-over');
    });

    draggedCard = null;
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    // Find the card we're hovering over (for insertion point)
    const afterElement = getDragAfterElement(this, e.clientY);
    const dragging = document.querySelector('.dragging');

    if (dragging) {
        if (afterElement == null) {
            this.appendChild(dragging);
        } else {
            this.insertBefore(dragging, afterElement);
        }
    }
}

function handleDragEnter(e) {
    e.preventDefault();
    this.classList.add('drag-over');
}

function handleDragLeave(e) {
    // Only remove if we're actually leaving the column
    if (!this.contains(e.relatedTarget)) {
        this.classList.remove('drag-over');
    }
}

async function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');

    const appId = e.dataTransfer.getData('text/plain');
    const newStatus = this.closest('.pipeline-column').dataset.status;

    if (!appId || !newStatus) return;

    try {
        // Update status via API
        await updateApplicationStatus(appId, newStatus);

        // Update the column count badges
        updateColumnCounts();

        // Show success feedback
        showToast('Status updated!', 'success');
    } catch (error) {
        // Revert on error - reload page to restore correct state
        showToast('Failed to update status', 'error');
        setTimeout(() => location.reload(), 1000);
    }
}

// Get the element after which we should insert the dragged card
function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.pipeline-card:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;

        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Update the count badges in column headers
function updateColumnCounts() {
    document.querySelectorAll('.pipeline-column').forEach(column => {
        const count = column.querySelectorAll('.pipeline-card').length;
        const badge = column.querySelector('.column-count');
        if (badge) {
            badge.textContent = count;
        }
    });
}

// === API Helper ===

async function updateApplicationStatus(appId, newStatus) {
    const response = await fetch(`/api/applications/${appId}/status`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
    });

    if (!response.ok) {
        throw new Error('Failed to update status');
    }

    return await response.json();
}

// === Toast Notifications ===

function showToast(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto dismiss
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// === Utility ===

function confirmAction(message) {
    return confirm(message);
}
