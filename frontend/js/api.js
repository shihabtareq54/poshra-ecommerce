const API_BASE = 'https://poshra-ecommerce.onrender.com/api';
const FALLBACK_IMG = 'https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=600&q=80';

function getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

function escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag]));
}

function requireAuth() {
    if (!localStorage.getItem('auth_token')) {
        window.location.href = 'auth.html';
        return false;
    }
    return true;
}

async function initSharedLayout(activeCategoryId = '') {
    const headerSlot = document.getElementById('shared-header');
    const footerSlot = document.getElementById('shared-footer');

    const token = localStorage.getItem('auth_token');
    const username = localStorage.getItem('username');
    const isStaff = localStorage.getItem('is_staff') === 'true';
    const currentSearch = getQueryParam('search') || '';

    if (headerSlot) {
        headerSlot.innerHTML = `
            <header class="main-header">
                <div class="container header-inner">
                    <a href="index.html" class="brand-logo">
                        <svg width="34" height="34" viewBox="0 0 40 40" fill="none">
                            <path d="M11 34V8H23C28.5228 8 33 12.4772 33 18C33 23.5228 28.5228 28 23 28H16" stroke="#ef4a23" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M16 14H22C24.2091 14 26 15.7909 26 18C26 20.2091 24.2091 22 22 22H16" stroke="#ef4a23" stroke-width="2.5" stroke-linecap="round"/>
                            <circle cx="11" cy="34" r="3" fill="#ef4a23"/>
                            <circle cx="11" cy="8" r="2.5" fill="#ffffff"/>
                            <circle cx="29" cy="12" r="2.2" fill="#ffffff"/>
                            <circle cx="16" cy="28" r="2.2" fill="#ffffff"/>
                        </svg>
                        <span>POSHRA</span>
                    </a>

                    <form class="search-box" id="global-search-form">
                        <input type="text" id="global-search-input" value="${escapeHTML(currentSearch)}" placeholder="Search laptops, mice, brands...">
                        <button type="submit">🔍</button>
                    </form>

                    <div class="header-actions">
                        ${isStaff ? `<a href="admin-dashboard.html" class="nav-link-btn" style="border-color:#ef4a23; color:#fca5a5;">⚙️ Store Admin</a>` : ''}
                        ${token && username ? `<a href="orders.html" class="nav-link-btn">📦 My Orders</a>` : ''}
                        <a href="cart.html" class="nav-link-btn">
                            🛒 Cart <span class="cart-badge" id="global-cart-count">0</span>
                        </a>
                        ${token && username ? `
                            <span style="font-size:13px; color:#38bdf8; font-weight:600;">@${escapeHTML(username)}</span>
                            <button class="btn-signin" id="global-logout-btn" style="background:#334155;">Logout</button>
                        ` : `
                            <a href="auth.html" class="btn-signin">Sign In</a>
                        `}
                    </div>
                </div>
            </header>

            <nav class="category-navbar">
                <div class="container category-nav-list" id="global-category-list">
                    <a href="index.html" class="cat-tab ${!activeCategoryId ? 'active' : ''}">All Products</a>
                </div>
            </nav>
        `;

        document.getElementById('global-search-form').onsubmit = (e) => {
            e.preventDefault();
            const q = document.getElementById('global-search-input').value.trim();
            window.location.href = q ? `products.html?search=${encodeURIComponent(q)}` : 'products.html';
        };

        const logoutBtn = document.getElementById('global-logout-btn');
        if (logoutBtn) {
            logoutBtn.onclick = async () => {
                try {
                    await fetch(`${API_BASE}/auth/logout/`, {
                        method: 'POST',
                        headers: { 'Authorization': `Token ${token}` }
                    });
                } catch {}
                localStorage.clear();
                window.location.href = 'index.html';
            };
        }

        loadGlobalCategoriesWithBrands(activeCategoryId);
    }

    if (footerSlot) {
        footerSlot.innerHTML = `
            <footer class="site-footer">
                <div class="container">
                    <p>© 2026 পসরা (Poshra) • Trusted Tech & Gadget Store in Bangladesh • Secured by SSLCommerz</p>
                </div>
            </footer>
        `;
    }

    if (token) updateCartBadge();
}

// প্রতিটি ক্যাটাগরি ট্যাবে হোভার করলে সেই ক্যাটাগরির ব্র্যান্ড ড্রপডাউন মেনু দেখাবে!
async function loadGlobalCategoriesWithBrands(activeCategoryId) {
    const catList = document.getElementById('global-category-list');
    if (!catList) return;

    try {
        const res = await fetch(`${API_BASE}/categories/`);
        const categories = await res.json();

        for (const cat of categories) {
            const isActive = String(cat.id) === String(activeCategoryId);
            const wrapper = document.createElement('div');
            wrapper.className = 'cat-dropdown';

            // ক্যাটাগরির ভেতরে থাকা ব্র্যান্ডগুলো আনা
            const bRes = await fetch(`${API_BASE}/brands/?category=${cat.id}`);
            const brands = await bRes.json();

            wrapper.innerHTML = `
                <a href="products.html?category=${cat.id}&name=${encodeURIComponent(cat.name)}" class="cat-tab ${isActive ? 'active' : ''}">
                    ${escapeHTML(cat.name)} ${brands.length ? '▾' : ''}
                </a>
                ${brands.length ? `
                    <div class="cat-dropdown-menu">
                        <a href="products.html?category=${cat.id}&name=${encodeURIComponent(cat.name)}" class="dropdown-item"><strong>All ${escapeHTML(cat.name)}</strong></a>
                        ${brands.map(b => `
                            <a href="products.html?category=${cat.id}&name=${encodeURIComponent(cat.name)}&brand=${encodeURIComponent(b)}" class="dropdown-item">${escapeHTML(b)}</a>
                        `).join('')}
                    </div>
                ` : ''}
            `;
            catList.appendChild(wrapper);
        }
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

async function updateCartBadge() {
    const token = localStorage.getItem('auth_token');
    const badge = document.getElementById('global-cart-count');
    if (!token || !badge) return;

    try {
        const res = await fetch(`${API_BASE}/cart/`, { headers: { 'Authorization': `Token ${token}` } });
        if (res.ok) {
            const cart = await res.json();
            badge.innerText = (cart.items || []).reduce((sum, i) => sum + i.quantity, 0);
        }
    } catch {}
}

async function addToCartAPI(productId, quantity = 1, goToCheckout = false) {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        alert('Please Sign In first to add items to your cart.');
        window.location.href = 'auth.html';
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/cart/items/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Token ${token}` },
            body: JSON.stringify({ product: productId, quantity })
        });
        const data = await res.json();

        if (res.status === 401) {
            localStorage.clear();
            alert('Session expired. Please Sign In again.');
            window.location.href = 'auth.html';
            return;
        }

        if (res.ok) {
            await updateCartBadge();
            if (goToCheckout) window.location.href = 'checkout.html';
            else alert('Product added to your cart!');
        } else {
            alert(data.error || data.detail || 'Could not add product to cart.');
        }
    } catch {
        alert('Network error. Make sure Django server is running.');
    }
}

function buildProductCardHTML(p) {
    return `
        <article class="product-card">
            <div class="badge-row">
                <span class="stock-badge ${p.in_stock ? 'in-stock' : 'out-stock'}">
                    ${p.in_stock ? 'In Stock' : 'Out of Stock'}
                </span>
                <span class="brand-tag">${escapeHTML(p.brand)}</span>
            </div>
            <a href="product-detail.html?id=${p.id}" class="product-thumb">
                <img src="${p.image || FALLBACK_IMG}" alt="${escapeHTML(p.name)}">
            </a>
            <a href="product-detail.html?id=${p.id}" class="product-title">${escapeHTML(p.name)}</a>
            <div class="product-price">৳ ${Number(p.price).toLocaleString()}</div>
            <button class="btn-outline-blue" ${!p.in_stock ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : ''} onclick="addToCartAPI(${p.id}, 1, false)">
                ${p.in_stock ? 'Add to Cart' : 'Out of Stock'}
            </button>
        </article>
    `;
}