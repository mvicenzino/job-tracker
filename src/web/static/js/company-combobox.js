/**
 * Company Combobox Component
 * Searchable dropdown for selecting or creating companies
 */

class CompanyCombobox {
    constructor(inputElement, hiddenIdElement = null) {
        this.input = inputElement;
        this.hiddenId = hiddenIdElement; // Hidden input to store company_id
        this.results = [];
        this.selectedIndex = -1;
        this.dropdown = null;
        this.isOpen = false;

        this.init();
    }

    init() {
        // Create dropdown container
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'company-combobox-dropdown';
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
        
        if (query.length < 2) {
            this.close();
            // Clear hidden ID if text is cleared
            if (this.hiddenId && !query) {
                this.hiddenId.value = '';
            }
            return;
        }

        this.search(query);
    }

    async search(query) {
        try {
            const response = await fetch(`/api/companies/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.results = data.companies || [];
            this.selectedIndex = -1;
            this.render(query);
            this.open();
        } catch (error) {
            console.error('Company search failed:', error);
        }
    }

    render(query) {
        this.dropdown.innerHTML = '';

        // Existing companies
        this.results.forEach((company, index) => {
            const item = document.createElement('div');
            item.className = 'company-combobox-item';
            item.innerHTML = company.name;
            item.dataset.index = index;
            item.dataset.id = company.id;
            item.addEventListener('click', () => this.select(company, true));
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
            this.dropdown.appendChild(item);
        });

        // "Create new company" option
        const createItem = document.createElement('div');
        createItem.className = 'company-combobox-item company-combobox-create';
        createItem.innerHTML = `<strong>+ Create new company</strong> "${query}"`;
        createItem.dataset.index = this.results.length;
        createItem.addEventListener('click', () => this.createNew(query));
        createItem.addEventListener('mouseenter', () => {
            this.selectedIndex = this.results.length;
            this.updateSelection();
        });
        this.dropdown.appendChild(createItem);
    }

    updateSelection() {
        const items = this.dropdown.querySelectorAll('.company-combobox-item');
        items.forEach((item, idx) => {
            if (idx === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    onKeydown(e) {
        if (!this.isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(
                    this.selectedIndex + 1,
                    this.results.length // Include "create" option
                );
                this.updateSelection();
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;

            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex === -1) return;

                if (this.selectedIndex < this.results.length) {
                    // Select existing company
                    this.select(this.results[this.selectedIndex], true);
                } else {
                    // Create new company
                    this.createNew(this.input.value.trim());
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

    select(company, clearId = false) {
        this.input.value = company.name;
        if (this.hiddenId) {
            this.hiddenId.value = company.id;
        }
        this.close();
    }

    createNew(name) {
        this.input.value = name;
        if (this.hiddenId) {
            this.hiddenId.value = ''; // Clear ID to signal create new
        }
        this.close();
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
    const companyInputs = document.querySelectorAll('[data-combobox="company"]');
    companyInputs.forEach((input) => {
        const hiddenId = document.querySelector(`[data-combobox-id="${input.id}"]`);
        new CompanyCombobox(input, hiddenId);
    });
});
