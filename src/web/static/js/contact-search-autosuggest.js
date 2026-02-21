/**
 * Contact Search Autosuggest Component
 * Real-time search and jump to contact
 */

class ContactSearchAutosuggest {
    constructor(inputElement, formElement) {
        this.input = inputElement;
        this.form = formElement;
        this.results = [];
        this.selectedIndex = -1;
        this.dropdown = null;
        this.isOpen = false;
        this.debounceTimer = null;

        this.init();
    }

    init() {
        // Create dropdown container
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'contact-search-dropdown';
        this.dropdown.style.display = 'none';
        this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);

        // Event listeners
        this.input.addEventListener('input', (e) => this.onInput(e));
        this.input.addEventListener('keydown', (e) => this.onKeydown(e));
        this.input.addEventListener('focus', (e) => this.onFocus(e));
        document.addEventListener('click', (e) => this.onClickOutside(e));
    }

    onInput(e) {
        const query = e.target.value.trim();
        
        // Clear timer
        clearTimeout(this.debounceTimer);

        if (query.length < 2) {
            this.close();
            return;
        }

        // Debounce search
        this.debounceTimer = setTimeout(() => this.search(query), 150);
    }

    async search(query) {
        try {
            const response = await fetch(`/api/contacts/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.results = data.contacts || [];
            this.selectedIndex = -1;
            this.render();
            if (this.results.length > 0) {
                this.open();
            } else {
                this.close();
            }
        } catch (error) {
            console.error('Contact search failed:', error);
        }
    }

    render() {
        this.dropdown.innerHTML = '';

        this.results.forEach((contact, index) => {
            const item = document.createElement('div');
            item.className = 'contact-search-item';
            
            let html = `<strong>${contact.name}</strong>`;
            if (contact.companyName) {
                html += ` <span class="contact-company">${contact.companyName}</span>`;
            }
            item.innerHTML = html;
            
            item.dataset.index = index;
            item.dataset.id = contact.id;
            item.addEventListener('click', () => this.selectContact(contact.id));
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
            this.dropdown.appendChild(item);
        });
    }

    updateSelection() {
        const items = this.dropdown.querySelectorAll('.contact-search-item');
        items.forEach((item, idx) => {
            if (idx === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    onKeydown(e) {
        if (!this.isOpen || this.results.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
                this.updateSelection();
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;

            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.selectedIndex < this.results.length) {
                    this.selectContact(this.results[this.selectedIndex].id);
                }
                break;

            case 'Escape':
                e.preventDefault();
                this.close();
                break;
        }
    }

    onFocus(e) {
        const query = e.target.value.trim();
        if (query.length >= 2 && this.results.length > 0) {
            this.open();
        }
    }

    onClickOutside(e) {
        if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.close();
        }
    }

    selectContact(contactId) {
        // Navigate to contact edit page
        window.location.href = `/contacts/${contactId}/edit`;
    }

    open() {
        this.dropdown.style.display = 'block';
        this.isOpen = true;
    }

    close() {
        this.dropdown.style.display = 'none';
        this.isOpen = false;
        this.selectedIndex = -1;
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('[data-autosuggest="contact-search"]');
    const searchForm = searchInput?.closest('form');
    if (searchInput && searchForm) {
        new ContactSearchAutosuggest(searchInput, searchForm);
    }
});
