// Job Hunt Tracker - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile menu
    initMobileMenu();

    // Initialize nav dropdowns
    initNavDropdowns();

    // Initialize sidebar profile menu
    initSidebarProfileMenu();

    // Initialize sidebar add menu
    initSidebarAddMenu();

    // Initialize header/dashboard add dropdowns
    initHeaderAddDropdowns();

    // Initialize calendar sync dropdowns
    initCalSyncDropdowns();

    // Initialize onboarding dismiss
    initOnboardingDismiss();

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

// === Calendar Sync Dropdowns ===

function initCalSyncDropdowns() {
    document.addEventListener('click', function(e) {
        var toggle = e.target.closest('.cal-sync-toggle');
        var wrap = toggle ? toggle.closest('.cal-sync-wrap') : null;

        // Close every open dropdown except the one being toggled
        document.querySelectorAll('.cal-sync-wrap.open').forEach(function(el) {
            if (el !== wrap) el.classList.remove('open');
        });

        // If we clicked a toggle, flip its state
        if (wrap) {
            wrap.classList.toggle('open');
        }
    });
}

// === Onboarding Dismiss ===

function initOnboardingDismiss() {
    var dismissBtn = document.getElementById('dismiss-onboarding');
    if (!dismissBtn) return;

    dismissBtn.addEventListener('click', function() {
        var card = document.querySelector('.onboarding-card');
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(-20px)';
            card.style.transition = 'all 0.3s ease';
            setTimeout(function() {
                card.remove();
            }, 300);
        }

        // Save dismissal to server
        fetch('/onboarding/dismiss', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    });
}

// === Mobile Menu ===

function initMobileMenu() {
    const navMenu = document.getElementById('nav-menu');
    if (!navMenu) return;

    // Close menu when clicking a nav link (page will reload, but close instantly)
    const navLinks = navMenu.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (typeof closeMobileMenu === 'function') closeMobileMenu();
        });
    });

    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            if (typeof closeMobileMenu === 'function') closeMobileMenu();
        }
    });

    // Handle window resize - close menu if resizing to desktop
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 768 && navMenu.classList.contains('active')) {
                if (typeof closeMobileMenu === 'function') closeMobileMenu();
            }
        }, 100);
    });
}

// === Sidebar Profile Menu ===

function initSidebarProfileMenu() {
    var sidebarProfile = document.getElementById('sidebarProfile');
    if (!sidebarProfile) return;

    var trigger = sidebarProfile.querySelector('.sidebar-profile-trigger');
    if (!trigger) return;

    trigger.addEventListener('click', function(e) {
        e.stopPropagation();
        var isOpen = sidebarProfile.classList.contains('open');
        sidebarProfile.classList.toggle('open');
        trigger.setAttribute('aria-expanded', String(!isOpen));

        // Close nav dropdowns and add menu when sidebar profile opens
        if (!isOpen) {
            document.querySelectorAll('.nav-dropdown.open, .nav-profile.open').forEach(function(d) {
                d.classList.remove('open');
                var t = d.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
                if (t) t.setAttribute('aria-expanded', 'false');
            });
            var sidebarAdd = document.getElementById('sidebarAdd');
            if (sidebarAdd) {
                sidebarAdd.classList.remove('open');
                var addTrigger = sidebarAdd.querySelector('.sidebar-cta');
                if (addTrigger) addTrigger.setAttribute('aria-expanded', 'false');
            }
        }
    });

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!sidebarProfile.contains(e.target)) {
            sidebarProfile.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebarProfile.classList.contains('open')) {
            sidebarProfile.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.focus();
        }
    });

    // Close after clicking any menu link
    sidebarProfile.querySelectorAll('.sidebar-menu-item').forEach(function(item) {
        if (item.tagName === 'A') {
            item.addEventListener('click', function() {
                sidebarProfile.classList.remove('open');
                trigger.setAttribute('aria-expanded', 'false');
            });
        }
    });

    // Set initial theme label
    var themeLabel = sidebarProfile.querySelector('.sidebar-theme-label');
    if (themeLabel) {
        themeLabel.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? 'Light Mode' : 'Dark Mode';
    }
}

// === Sidebar Add Menu ===

function initSidebarAddMenu() {
    var sidebarAdd = document.getElementById('sidebarAdd');
    if (!sidebarAdd) return;

    var trigger = sidebarAdd.querySelector('.sidebar-cta');
    if (!trigger) return;

    trigger.addEventListener('click', function(e) {
        e.stopPropagation();
        var isOpen = sidebarAdd.classList.contains('open');
        sidebarAdd.classList.toggle('open');
        trigger.setAttribute('aria-expanded', String(!isOpen));

        // Close profile menu when add menu opens
        if (!isOpen) {
            var sidebarProfile = document.getElementById('sidebarProfile');
            if (sidebarProfile) {
                sidebarProfile.classList.remove('open');
                var profileTrigger = sidebarProfile.querySelector('.sidebar-profile-trigger');
                if (profileTrigger) profileTrigger.setAttribute('aria-expanded', 'false');
            }
            // Close nav dropdowns
            document.querySelectorAll('.nav-dropdown.open, .nav-profile.open').forEach(function(d) {
                d.classList.remove('open');
                var t = d.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
                if (t) t.setAttribute('aria-expanded', 'false');
            });
        }
    });

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!sidebarAdd.contains(e.target)) {
            sidebarAdd.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebarAdd.classList.contains('open')) {
            sidebarAdd.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.focus();
        }
    });

    // Close after clicking any menu link
    sidebarAdd.querySelectorAll('.sidebar-menu-item').forEach(function(item) {
        if (item.tagName === 'A') {
            item.addEventListener('click', function() {
                sidebarAdd.classList.remove('open');
                trigger.setAttribute('aria-expanded', 'false');
            });
        }
    });
}

// === Header Add Dropdowns (Dashboard, Mobile Nav) ===

function initHeaderAddDropdowns() {
    var dropdowns = document.querySelectorAll('.header-add-dropdown, .mobile-add-dropdown');
    if (!dropdowns.length) return;

    dropdowns.forEach(function(dropdown) {
        var trigger = dropdown.querySelector('button');
        if (!trigger) return;

        trigger.addEventListener('click', function(e) {
            e.stopPropagation();
            var isOpen = dropdown.classList.contains('open');

            // Close all other header dropdowns
            dropdowns.forEach(function(other) {
                if (other !== dropdown) other.classList.remove('open');
            });

            dropdown.classList.toggle('open');
            trigger.setAttribute('aria-expanded', String(!isOpen));
        });
    });

    // Close on outside click
    document.addEventListener('click', function(e) {
        dropdowns.forEach(function(dropdown) {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
                var trigger = dropdown.querySelector('button');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            }
        });
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdowns.forEach(function(dropdown) {
                if (dropdown.classList.contains('open')) {
                    dropdown.classList.remove('open');
                    var trigger = dropdown.querySelector('button');
                    if (trigger) {
                        trigger.setAttribute('aria-expanded', 'false');
                        trigger.focus();
                    }
                }
            });
        }
    });
}

// === Nav Dropdowns (Network, Insights, Profile) ===

function initNavDropdowns() {
    var dropdowns = document.querySelectorAll('.nav-dropdown, .nav-profile');
    if (!dropdowns.length) return;

    dropdowns.forEach(function(dropdown) {
        var toggle = dropdown.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
        if (!toggle) return;

        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            var isOpen = dropdown.classList.contains('open');

            // Close all other dropdowns first
            dropdowns.forEach(function(other) {
                if (other !== dropdown) {
                    other.classList.remove('open');
                    var otherToggle = other.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
                    if (otherToggle) otherToggle.setAttribute('aria-expanded', 'false');
                }
            });

            // Close sidebar profile menu and add menu when nav dropdown opens
            var sidebarProfile = document.getElementById('sidebarProfile');
            if (sidebarProfile) {
                sidebarProfile.classList.remove('open');
                var sidebarTrigger = sidebarProfile.querySelector('.sidebar-profile-trigger');
                if (sidebarTrigger) sidebarTrigger.setAttribute('aria-expanded', 'false');
            }
            var sidebarAdd = document.getElementById('sidebarAdd');
            if (sidebarAdd) {
                sidebarAdd.classList.remove('open');
                var addTrigger = sidebarAdd.querySelector('.sidebar-cta');
                if (addTrigger) addTrigger.setAttribute('aria-expanded', 'false');
            }

            dropdown.classList.toggle('open');
            toggle.setAttribute('aria-expanded', String(!isOpen));
        });
    });

    // Close all on outside click
    document.addEventListener('click', function(e) {
        dropdowns.forEach(function(dropdown) {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
                var toggle = dropdown.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
                if (toggle) toggle.setAttribute('aria-expanded', 'false');
            }
        });
    });

    // Close all on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdowns.forEach(function(dropdown) {
                if (dropdown.classList.contains('open')) {
                    dropdown.classList.remove('open');
                    var toggle = dropdown.querySelector('.nav-dropdown-toggle, .nav-profile-toggle');
                    if (toggle) {
                        toggle.setAttribute('aria-expanded', 'false');
                        toggle.focus();
                    }
                }
            });
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

// === Form Validation Feedback ===

document.addEventListener('DOMContentLoaded', function() {
    // Add visual feedback for required fields
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('loading')) {
                // Don't add loading state for forms that might fail validation
                const requiredFields = form.querySelectorAll('[required]');
                let allValid = true;
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        allValid = false;
                        field.classList.add('invalid');
                    } else {
                        field.classList.remove('invalid');
                    }
                });
            }
        });
    });

    // Remove invalid class on input
    document.querySelectorAll('input, textarea, select').forEach(field => {
        field.addEventListener('input', function() {
            this.classList.remove('invalid');
        });
    });
});

// === Dropdown improvements for touch devices ===

if ('ontouchstart' in window) {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
            const menu = this.querySelector('.dropdown-menu');
            if (menu) {
                const isVisible = menu.style.display === 'block';
                // Close all other dropdowns
                document.querySelectorAll('.dropdown-menu').forEach(m => {
                    m.style.display = 'none';
                });
                menu.style.display = isVisible ? 'none' : 'block';
            }
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-menu').forEach(m => {
            m.style.display = 'none';
        });
    });
}
