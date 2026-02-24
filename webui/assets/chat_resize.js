/**
 * Chat drawer resize logic.
 *
 * Detects mousedown near the left edge of the #chat-drawer offcanvas and lets
 * the user drag to resize.  Width is persisted to localStorage and restored
 * each time the drawer opens.
 */
(function () {
    "use strict";

    var MIN_WIDTH  = 300;
    var MAX_RATIO  = 0.85;   // max 85 % of viewport
    var EDGE_ZONE  = 12;     // px from the left edge that counts as "grab zone"
    var dragging   = false;
    var startX     = 0;
    var startWidth = 0;

    /* ---------- DOM helpers ---------- */
    function drawer() {
        return document.getElementById("chat-drawer");
    }

    function isOpen(el) {
        return el && el.classList.contains("show");
    }

    function setWidth(el, px) {
        el.style.width = px + "px";
    }

    /* ---------- localStorage ---------- */
    function persist(px) {
        try { localStorage.setItem("chat-width-store", JSON.stringify({ width: px })); } catch (_) {}
    }
    function restore() {
        try {
            var d = JSON.parse(localStorage.getItem("chat-width-store"));
            return d && d.width ? d.width : null;
        } catch (_) { return null; }
    }

    /* ---------- Hit-test: is pointer in the grab zone? ---------- */
    function inGrabZone(el, clientX) {
        var rect = el.getBoundingClientRect();
        // The drawer is anchored to the right edge; its left boundary = rect.left
        return clientX >= rect.left - EDGE_ZONE && clientX <= rect.left + EDGE_ZONE;
    }

    /* ---------- Mouse handlers (capture phase) ---------- */
    document.addEventListener("mousedown", function (e) {
        var el = drawer();
        if (!el || !isOpen(el)) return;
        if (!inGrabZone(el, e.clientX)) return;

        e.preventDefault();
        e.stopPropagation();
        dragging   = true;
        startX     = e.clientX;
        startWidth = el.getBoundingClientRect().width;
        el.classList.add("chat-resizing");
        document.body.style.cursor     = "col-resize";
        document.body.style.userSelect = "none";
    }, true);

    document.addEventListener("mousemove", function (e) {
        if (!dragging) return;
        e.preventDefault();
        var el = drawer();
        if (!el) { dragging = false; return; }

        var delta    = startX - e.clientX;          // dragging left → positive delta → wider
        var maxW     = window.innerWidth * MAX_RATIO;
        var newWidth = Math.max(MIN_WIDTH, Math.min(maxW, startWidth + delta));
        setWidth(el, newWidth);
    }, true);

    document.addEventListener("mouseup", function () {
        if (!dragging) return;
        dragging = false;
        var el = drawer();
        document.body.style.cursor     = "";
        document.body.style.userSelect = "";
        if (el) {
            el.classList.remove("chat-resizing");
            persist(Math.round(el.getBoundingClientRect().width));
        }
    }, true);

    /* ---------- Touch handlers ---------- */
    document.addEventListener("touchstart", function (e) {
        var el = drawer();
        if (!el || !isOpen(el)) return;
        var t = e.touches[0];
        if (!inGrabZone(el, t.clientX)) return;

        e.preventDefault();
        dragging   = true;
        startX     = t.clientX;
        startWidth = el.getBoundingClientRect().width;
        el.classList.add("chat-resizing");
    }, { capture: true, passive: false });

    document.addEventListener("touchmove", function (e) {
        if (!dragging) return;
        var el = drawer();
        if (!el) { dragging = false; return; }
        var t        = e.touches[0];
        var delta    = startX - t.clientX;
        var maxW     = window.innerWidth * MAX_RATIO;
        var newWidth = Math.max(MIN_WIDTH, Math.min(maxW, startWidth + delta));
        setWidth(el, newWidth);
    }, { capture: true, passive: true });

    document.addEventListener("touchend", function () {
        if (!dragging) return;
        dragging = false;
        var el = drawer();
        if (el) {
            el.classList.remove("chat-resizing");
            persist(Math.round(el.getBoundingClientRect().width));
        }
    }, true);

    /* ---------- Disable Bootstrap focus trap so inputs outside the drawer work ---------- */
    function disableFocusTrap(el) {
        try {
            // Bootstrap 5 stores its instance on the element
            var bsInstance = bootstrap.Offcanvas.getInstance(el);
            if (bsInstance && bsInstance._focustrap) {
                bsInstance._focustrap.deactivate();
            }
        } catch (_) {}
    }

    /* ---------- Restore width when drawer becomes visible ---------- */
    function observe() {
        var el = drawer();
        if (!el) { setTimeout(observe, 500); return; }

        new MutationObserver(function () {
            if (isOpen(el)) {
                var saved = restore();
                if (saved) setWidth(el, saved);
                // Disable focus trap so other page inputs remain usable
                disableFocusTrap(el);
            }
        }).observe(el, { attributes: true, attributeFilter: ["class"] });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", observe);
    } else {
        observe();
    }

    /* ---------- Show col-resize cursor when hovering the grab zone ---------- */
    document.addEventListener("mousemove", function (e) {
        if (dragging) return;   // handled above during drag
        var el = drawer();
        if (!el || !isOpen(el)) return;
        if (inGrabZone(el, e.clientX)) {
            el.style.cursor = "col-resize";
        } else if (el.style.cursor === "col-resize") {
            el.style.cursor = "";
        }
    }, false);
})();
