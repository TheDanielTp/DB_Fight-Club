// Modern Fight Club Management System JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initNavbar();
    initAnimations();
    initParticles();
    initPageTransitions();
    initCounters();
    initFlashMessages();
    
    // Handle entity button clicks
    document.querySelectorAll('.entity-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!window.isLoggedIn) {
                e.preventDefault();
                const entity = this.dataset.entity;
                showLoginMessage(entity);
            }
        });
    });
    
    // Login button click
    const loginBtn = document.querySelector('.login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', function(e) {
            if (!window.isLoggedIn) {
                e.preventDefault();
                window.location.href = '/login';
            }
        });
    }
});

// Initialize navbar effects
function initNavbar() {
    const navbar = document.querySelector('.navbar');
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll <= 0) {
            navbar.style.transform = 'translateY(0)';
            return;
        }
        
        if (currentScroll > lastScroll && currentScroll > 100) {
            // Scroll down
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // Scroll up
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScroll = currentScroll;
    });
}

// Initialize animations
function initAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements
    document.querySelectorAll('.stat-card, .feature-card').forEach(el => {
        observer.observe(el);
    });
    
    // Add animation classes
    const style = document.createElement('style');
    style.textContent = `
        .stat-card, .feature-card {
            opacity: 0;
            transform: translateY(30px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }
        
        .stat-card.animate-in, .feature-card.animate-in {
            opacity: 1;
            transform: translateY(0);
        }
        
        .stat-card:nth-child(1) { transition-delay: 0.1s; }
        .stat-card:nth-child(2) { transition-delay: 0.2s; }
        .stat-card:nth-child(3) { transition-delay: 0.3s; }
        .stat-card:nth-child(4) { transition-delay: 0.4s; }
        
        .feature-card:nth-child(1) { transition-delay: 0.1s; }
        .feature-card:nth-child(2) { transition-delay: 0.2s; }
        .feature-card:nth-child(3) { transition-delay: 0.3s; }
        .feature-card:nth-child(4) { transition-delay: 0.4s; }
    `;
    document.head.appendChild(style);
}

// Initialize particle background
function initParticles() {
    const container = document.querySelector('.particles');
    if (!container) return;
    
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        createParticle(container);
    }
}

function createParticle(container) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    // Random properties
    const size = Math.random() * 5 + 2;
    const posX = Math.random() * 100;
    const posY = Math.random() * 100;
    const delay = Math.random() * 5;
    const duration = Math.random() * 10 + 10;
    const opacity = Math.random() * 0.3 + 0.1;
    
    // Apply styles
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${posX}%`;
    particle.style.top = `${posY}%`;
    particle.style.opacity = opacity;
    particle.style.animationDelay = `${delay}s`;
    particle.style.animationDuration = `${duration}s`;
    
    // Random color gradient
    const colors = ['#e74a8f', '#efa9c6', '#c42a7a'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    particle.style.background = color;
    
    container.appendChild(particle);
    
    // Remove and recreate particle after animation
    setTimeout(() => {
        particle.remove();
        createParticle(container);
    }, duration * 1000);
}

// Initialize page transitions
function initPageTransitions() {
    const transition = document.createElement('div');
    transition.className = 'page-transition';
    transition.innerHTML = `
        <div class="loading-spinner"></div>
    `;
    document.body.appendChild(transition);
    
    // Handle link clicks
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (link && link.href && link.href.startsWith(window.location.origin)) {
            e.preventDefault();
            
            transition.classList.add('active');
            
            setTimeout(() => {
                window.location.href = link.href;
            }, 300);
        }
    });
}

// Initialize counter animations
function initCounters() {
    const counters = document.querySelectorAll('.stat-number');
    const speed = 200;
    
    counters.forEach(counter => {
        const updateCount = () => {
            const target = parseInt(counter.getAttribute('data-count') || counter.textContent);
            const count = parseInt(counter.textContent.replace(/\D/g, ''));
            const increment = target / speed;
            
            if (count < target) {
                counter.textContent = Math.ceil(count + increment).toLocaleString();
                setTimeout(updateCount, 1);
            } else {
                counter.textContent = target.toLocaleString();
            }
        };
        
        // Start counting when element is in view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCount();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        observer.observe(counter);
    });
}

// Initialize flash messages
function initFlashMessages() {
    const messages = document.querySelectorAll('.flash-message');
    
    messages.forEach(message => {
        // Auto-remove after 5 seconds
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
        
        // Close button functionality
        const closeBtn = message.querySelector('.close-flash');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                message.style.opacity = '0';
                message.style.transform = 'translateX(100%)';
                
                setTimeout(() => {
                    message.remove();
                }, 300);
            });
        }
    });
}

// Show login required message
function showLoginMessage(entity) {
    // Create flash message
    const flashContainer = document.querySelector('.flash-messages');
    if (!flashContainer) {
        const container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    const message = document.createElement('div');
    message.className = 'flash-message warning';
    message.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <span>Please login first to access ${entity} management.</span>
        <button class="close-flash" style="margin-left: auto; background: none; border: none; color: white; cursor: pointer;">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    flashContainer.appendChild(message);
    
    // Add close functionality
    message.querySelector('.close-flash').addEventListener('click', () => {
        message.style.opacity = '0';
        message.style.transform = 'translateX(100%)';
        
        setTimeout(() => {
            message.remove();
        }, 300);
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (message.parentNode) {
            message.style.opacity = '0';
            message.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                message.remove();
            }, 300);
        }
    }, 5000);
}

// API functions
async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching stats:', error);
        return null;
    }
}

// Update stats on page load
window.addEventListener('load', async () => {
    const stats = await fetchStats();
    if (stats) {
        // Update counter elements with real data
        document.querySelectorAll('[data-stat]').forEach(el => {
            const stat = el.getAttribute('data-stat');
            if (stats[stat]) {
                el.setAttribute('data-count', stats[stat]);
                if (el.textContent === '∞') {
                    el.textContent = '0';
                }
            }
        });
        
        // Restart counters
        initCounters();
    }
});

// Utility function for smooth scrolling
function smoothScroll(target, duration = 1000) {
    const targetElement = document.querySelector(target);
    if (!targetElement) return;
    
    const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset;
    const startPosition = window.pageYOffset;
    const distance = targetPosition - startPosition;
    let startTime = null;
    
    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const run = ease(timeElapsed, startPosition, distance, duration);
        window.scrollTo(0, run);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }
    
    function ease(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
    }
    
    requestAnimationFrame(animation);
}

// Add smooth scroll to anchor links
document.addEventListener('click', function(e) {
    if (e.target.matches('a[href^="#"]')) {
        e.preventDefault();
        const target = e.target.getAttribute('href');
        smoothScroll(target);
    }
});

// Global variables
window.isLoggedIn = false; // Will be set by backend template