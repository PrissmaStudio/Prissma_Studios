(function () {
    var ua = navigator.userAgent || '';
    var touchCapable = navigator.maxTouchPoints > 0 || 'ontouchstart' in window;
    var mobileUA = /Android|iPhone|iPod|Mobile|IEMobile|Opera Mini/i.test(ua);
    var tabletUA = /iPad|Tablet|Nexus 7|Nexus 10|SM-T|Tab/i.test(ua) || (touchCapable && window.innerWidth >= 768 && window.innerWidth <= 1366);

    var root = document.documentElement;
    var body = document.body;

    function applyFlags() {
        if (!body) return;
        if (mobileUA) {
            root.classList.add('is-mobile-device');
            body.classList.add('is-mobile-device');
            body.setAttribute('data-device', 'mobile');
        } else if (tabletUA) {
            root.classList.add('is-tablet-device');
            body.classList.add('is-tablet-device');
            body.setAttribute('data-device', 'tablet');
        } else {
            body.setAttribute('data-device', 'desktop');
        }

        if (touchCapable) {
            root.classList.add('is-touch');
            body.classList.add('is-touch');
        }
    }

    function setViewportHeightVar() {
        var vh = window.innerHeight * 0.01;
        root.style.setProperty('--app-vh', vh + 'px');
    }

    function initAdminMobileActions() {
        if (!body || !body.classList.contains('admin-page')) return;
        if (window.innerWidth > 900) return;

        var adminHeader = document.querySelector('.admin-header');
        var headerNav = document.querySelector('.admin-header .header-nav');
        if (!adminHeader || !headerNav) return;
        if (document.querySelector('.admin-mobile-menu-toggle')) return;

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'admin-mobile-menu-toggle';
        toggle.setAttribute('aria-label', 'Open admin menu');
        toggle.textContent = '☰';

        var quickBack = null;
        var firstNavLink = headerNav.querySelector('a');
        if (firstNavLink) {
            quickBack = firstNavLink.cloneNode(true);
            quickBack.classList.add('admin-mobile-quick-back');
            quickBack.removeAttribute('style');
        }

        var overlay = document.createElement('div');
        overlay.className = 'admin-mobile-drawer-overlay';

        var drawer = document.createElement('aside');
        drawer.className = 'admin-mobile-drawer';

        var linksSection = document.createElement('div');
        linksSection.className = 'admin-mobile-drawer-section';

        var extraSection = document.createElement('div');
        extraSection.className = 'admin-mobile-drawer-section';

        Array.prototype.forEach.call(headerNav.querySelectorAll('a,button'), function (item) {
            var clone = item.cloneNode(true);
            clone.classList.add('header-capsule');
            clone.addEventListener('click', closeAdminMobileMenu);
            linksSection.appendChild(clone);
        });

        var rightBlock = document.querySelector('.admin-header .header-right-block');
        if (rightBlock) {
            Array.prototype.forEach.call(rightBlock.querySelectorAll('a,button'), function (item) {
                var clone = item.cloneNode(true);
                clone.classList.add('header-capsule');
                clone.addEventListener('click', closeAdminMobileMenu);
                extraSection.appendChild(clone);
            });
        }

        drawer.appendChild(linksSection);
        if (extraSection.children.length) drawer.appendChild(extraSection);

        function openAdminMobileMenu() {
            drawer.classList.add('open');
            overlay.classList.add('open');
            body.style.overflow = 'hidden';
        }

        function closeAdminMobileMenu() {
            drawer.classList.remove('open');
            overlay.classList.remove('open');
            body.style.overflow = 'auto';
        }

        toggle.addEventListener('click', function (event) {
            event.stopPropagation();
            if (drawer.classList.contains('open')) {
                closeAdminMobileMenu();
            } else {
                openAdminMobileMenu();
            }
        });

        overlay.addEventListener('click', closeAdminMobileMenu);
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') closeAdminMobileMenu();
        });
        document.addEventListener('click', function (event) {
            if (!drawer.classList.contains('open')) return;
            if (!drawer.contains(event.target) && !toggle.contains(event.target)) {
                closeAdminMobileMenu();
            }
        });

        if (quickBack) {
            adminHeader.appendChild(quickBack);
        }
        adminHeader.appendChild(toggle);
        body.appendChild(overlay);
        body.appendChild(drawer);
    }

    function init() {
        applyFlags();
        setViewportHeightVar();
        initAdminMobileActions();
        window.addEventListener('resize', setViewportHeightVar, { passive: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
