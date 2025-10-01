/**
 * Digital Gods - Enhanced Animations and Interactions
 * KidsKlassiks Platform
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // === SCROLL ANIMATIONS ===
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const fadeObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                entry.target.style.animationDelay = Math.random() * 0.3 + 's';
            }
        });
    }, observerOptions);
    
    // Observe only scroll-fade-in elements (not feature cards or stats)
    document.querySelectorAll('.scroll-fade-in').forEach(function(element) {
        fadeObserver.observe(element);
    });
    
    
    // === DIGITAL GODS LOGO INTERACTIONS ===
    document.querySelectorAll('.digital-gods-logo').forEach(function(logo) {
        let isAnimating = false;
        
        logo.addEventListener('mouseenter', function() {
            if (!isAnimating) {
                isAnimating = true;
                this.style.transition = 'all 0.3s ease-out';
                this.style.transform = 'scale(1.02) rotate(1deg)';
                this.style.filter = 'drop-shadow(0 0 6px rgba(230, 194, 0, 0.2))';
                
                setTimeout(() => {
                    isAnimating = false;
                }, 300);
            }
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1) rotate(0deg)';
            this.style.filter = 'drop-shadow(0 0 2px rgba(230, 194, 0, 0.2))';
        });
        
        // Random gentle pulse every few seconds
        setInterval(() => {
            if (!isAnimating && Math.random() > 0.7) {
                logo.style.animation = 'digitalPulse 2s ease-in-out';
                setTimeout(() => {
                    logo.style.animation = '';
                }, 2000);
            }
        }, 5000);
    });
    
    
    // === ENHANCED BUTTON INTERACTIONS ===
    document.querySelectorAll('.btn-digital-primary, .btn-digital-secondary').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            // Ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    
    // === NAVBAR SCROLL EFFECTS ===
    let lastScrollY = window.scrollY;
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > 100) {
            navbar.style.background = 'rgba(26, 26, 26, 0.98)';
            navbar.style.backdropFilter = 'blur(20px)';
            navbar.style.borderBottom = '1px solid rgba(255, 215, 0, 0.3)';
        } else {
            navbar.style.background = 'rgba(26, 26, 26, 0.95)';
            navbar.style.backdropFilter = 'blur(15px)';
            navbar.style.borderBottom = '1px solid rgba(255, 215, 0, 0.2)';
        }
        
        // Hide/show navbar on scroll
        if (currentScrollY > lastScrollY && currentScrollY > 200) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollY = currentScrollY;
    });
    
    
    // === PARALLAX EFFECTS DISABLED ===
    // Removed all parallax and transform effects to prevent sliding panels
    
    
    // === DYNAMIC STATS COUNTER ===
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(function() {
            current += increment;
            element.textContent = Math.floor(current);
            
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            }
        }, 16);
    }
    
    // Animate stats when they come into view
    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                const statsNumber = entry.target.querySelector('.stats-number');
                if (statsNumber && !statsNumber.dataset.animated) {
                    const target = parseInt(statsNumber.textContent) || Math.floor(Math.random() * 50) + 1;
                    statsNumber.dataset.animated = 'true';
                    animateCounter(statsNumber, target);
                }
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('.stats-card').forEach(function(card) {
        statsObserver.observe(card);
    });
    
    
    // === INTERACTIVE FEATURE CARDS ===
    document.querySelectorAll('.feature-card').forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-15px) scale(1.02) rotateX(5deg)';
            this.style.transition = 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1) rotateX(0deg)';
        });
    });
    
    
    // === LOADING STATES ===
    function showLoading(button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<div class="loading-spinner me-2"></div>Processing...';
        button.disabled = true;
        button.dataset.originalText = originalText;
    }
    
    function hideLoading(button) {
        button.innerHTML = button.dataset.originalText;
        button.disabled = false;
    }
    
    // Auto-apply loading to certain buttons
    document.querySelectorAll('[href="/books/import"], [href*="process"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            showLoading(this);
            // Hide loading after navigation or timeout
            setTimeout(() => hideLoading(this), 3000);
        });
    });
    
    
    // === THEME INTEGRATION ===
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            // Add rotation animation when theme changes
            this.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                this.style.transform = 'rotate(0deg)';
            }, 300);
        });
    }
    
    
    // === KEYBOARD SHORTCUTS ===
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for quick search (if implemented)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            // Trigger search modal or focus search input
            console.log('Quick search shortcut triggered');
        }
        
        // Ctrl/Cmd + N for new book import
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/books/import';
        }
    });
    
    
    // === PERFORMANCE OPTIMIZATION ===
    // Debounce scroll events
    let scrollTimeout;
    const originalScrollHandler = window.onscroll;
    
    window.addEventListener('scroll', function() {
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
        }
        scrollTimeout = setTimeout(originalScrollHandler, 10);
    });
    
    
    // === ACCESSIBILITY ENHANCEMENTS ===
    // Add focus indicators for keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-focus');
        }
    });
    
    document.addEventListener('mousedown', function() {
        document.body.classList.remove('keyboard-focus');
    });
    
    
    // === CONSOLE BRANDING ===
    console.log(`
    ╔══════════════════════════════════════╗
    ║           DIGITAL GODS               ║
    ║         KidsKlassiks Platform        ║
    ║                                      ║
    ║    🤖 AI-Powered Story Transform     ║
    ║    🎨 Character-Consistent Art       ║
    ║    📚 Classic Literature Adaptation  ║
    ║                                      ║
    ║      Powered by Advanced AI          ║
    ╚══════════════════════════════════════╝
    `);
    
});

// === CSS INJECTION FOR RIPPLE ANIMATION ===
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    .keyboard-focus *:focus {
        outline: 2px solid var(--dg-primary) !important;
        outline-offset: 2px !important;
    }
`;
document.head.appendChild(style);