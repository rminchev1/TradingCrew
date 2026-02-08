/**
 * Watchlist Drag & Drop functionality
 * Handles reordering of watchlist items via HTML5 drag and drop
 */
(function() {
    let draggedItem = null;
    let draggedSymbol = null;

    function initDragDrop() {
        const container = document.getElementById('watchlist-items-container');
        if (!container) {
            setTimeout(initDragDrop, 500);
            return;
        }

        container.addEventListener('dragstart', handleDragStart);
        container.addEventListener('dragend', handleDragEnd);
        container.addEventListener('dragover', handleDragOver);
        container.addEventListener('dragenter', handleDragEnter);
        container.addEventListener('dragleave', handleDragLeave);
        container.addEventListener('drop', handleDrop);
    }

    function handleDragStart(e) {
        const item = e.target.closest('.watchlist-item');
        if (!item) return;

        draggedItem = item;
        draggedSymbol = item.getAttribute('data-symbol');
        item.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', draggedSymbol);
    }

    function handleDragEnd(e) {
        const item = e.target.closest('.watchlist-item');
        if (item) item.classList.remove('dragging');

        document.querySelectorAll('.watchlist-item.drag-over').forEach(function(el) {
            el.classList.remove('drag-over');
        });

        draggedItem = null;
        draggedSymbol = null;
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDragEnter(e) {
        const item = e.target.closest('.watchlist-item');
        if (item && item !== draggedItem) {
            item.classList.add('drag-over');
        }
    }

    function handleDragLeave(e) {
        const item = e.target.closest('.watchlist-item');
        if (item) {
            const rect = item.getBoundingClientRect();
            if (e.clientX < rect.left || e.clientX > rect.right ||
                e.clientY < rect.top || e.clientY > rect.bottom) {
                item.classList.remove('drag-over');
            }
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        const targetItem = e.target.closest('.watchlist-item');
        if (!targetItem || !draggedItem || targetItem === draggedItem) return;

        targetItem.classList.remove('drag-over');

        const container = document.getElementById('watchlist-items-container');
        const items = Array.from(container.querySelectorAll('.watchlist-item'));

        const draggedIndex = items.indexOf(draggedItem);
        const targetIndex = items.indexOf(targetItem);

        if (draggedIndex === -1 || targetIndex === -1) return;

        const symbols = items.map(function(item) {
            return item.getAttribute('data-symbol');
        });

        symbols.splice(draggedIndex, 1);
        symbols.splice(targetIndex, 0, draggedSymbol);

        // Trigger Dash callback via hidden input
        const reorderInput = document.getElementById('watchlist-reorder-input');
        if (reorderInput) {
            reorderInput.value = symbols.join(',') + '|' + Date.now();

            var event = new Event('input', { bubbles: true });
            reorderInput.dispatchEvent(event);

            var changeEvent = new Event('change', { bubbles: true });
            reorderInput.dispatchEvent(changeEvent);
        }
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDragDrop);
    } else {
        initDragDrop();
    }

    // Re-initialize when DOM changes (for dynamic content)
    var observer = new MutationObserver(function(mutations) {
        var container = document.getElementById('watchlist-items-container');
        if (container) {
            initDragDrop();
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();
