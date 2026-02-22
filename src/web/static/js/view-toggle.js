/**
 * Shared list/tile view toggle + instant client-side filter.
 *
 * Usage:
 *   initListPage({
 *     pageKey: 'contacts',          // localStorage suffix
 *     listSelector: '.list-view-container',
 *     tileSelector: '.tile-view-container',
 *     itemSelector: '[data-filter-text]',
 *     searchSelector: '#pageFilterInput',
 *     toggleSelector: '.view-toggle'
 *   });
 */
function initListPage(cfg) {
    var storageKey = 'stride-view-' + cfg.pageKey;
    var listEl = document.querySelector(cfg.listSelector);
    var tileEl = document.querySelector(cfg.tileSelector);
    var searchEl = document.querySelector(cfg.searchSelector);
    var toggleEl = document.querySelector(cfg.toggleSelector);
    var noResults = document.querySelector('.no-filter-results');

    if (!listEl || !tileEl) return;

    // --- View toggle ---
    function setView(mode) {
        if (mode === 'tile') {
            listEl.style.display = 'none';
            tileEl.style.display = '';
            localStorage.setItem(storageKey, 'tile');
        } else {
            listEl.style.display = '';
            tileEl.style.display = 'none';
            localStorage.setItem(storageKey, 'list');
        }
        if (toggleEl) {
            var btns = toggleEl.querySelectorAll('.view-toggle-btn');
            btns.forEach(function(b) {
                b.classList.toggle('active', b.getAttribute('data-view') === mode);
            });
        }
    }

    // Restore saved preference (default: list)
    var saved = localStorage.getItem(storageKey) || 'list';
    setView(saved);

    // Button clicks
    if (toggleEl) {
        toggleEl.addEventListener('click', function(e) {
            var btn = e.target.closest('.view-toggle-btn');
            if (btn) setView(btn.getAttribute('data-view'));
        });
    }

    // --- Instant filter ---
    if (searchEl) {
        // Prevent form submit if wrapped in a form
        var parentForm = searchEl.closest('form');
        if (parentForm) {
            parentForm.addEventListener('submit', function(e) { e.preventDefault(); });
        }

        searchEl.addEventListener('input', function() {
            var query = searchEl.value.toLowerCase().trim();
            var items = document.querySelectorAll(cfg.itemSelector);
            var visibleCount = 0;

            items.forEach(function(item) {
                var text = (item.getAttribute('data-filter-text') || '').toLowerCase();
                var match = !query || text.indexOf(query) !== -1;
                item.style.display = match ? '' : 'none';
                if (match) visibleCount++;
            });

            if (noResults) {
                noResults.style.display = (visibleCount === 0 && query) ? 'block' : 'none';
            }
        });
    }

    // --- Mobile: hide toggle, default to tile ---
    function checkMobile() {
        if (!toggleEl) return;
        if (window.innerWidth < 768) {
            toggleEl.style.display = 'none';
            listEl.style.display = 'none';
            tileEl.style.display = '';
        } else {
            toggleEl.style.display = '';
            setView(localStorage.getItem(storageKey) || 'list');
        }
    }
    checkMobile();
    window.addEventListener('resize', checkMobile);
}
