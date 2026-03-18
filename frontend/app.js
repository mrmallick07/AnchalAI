/* ═══════════════════════════════════════════════════════════════
   AnchalAI — Application Logic
   SPA routing, data loading, charts, modals, and interactions
   ═══════════════════════════════════════════════════════════════ */

const API = "https://anchalai-backend-961197586142.asia-south1.run.app";
// const API = "https://anchalai-backend-961197586142.asia-south1.run.app";

let allWomen = [];
let filteredWomen = [];
let currentFilter = "All";
let currentProfile = null;
let currentLang = "Bengali";
let currentPage = 1;
const PER_PAGE = 15;
let searchQuery = "";
let analyticsData = null;
let contactsData = [];

// ── SPA Routing ─────────────────────────────────────────────────────────────
function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const el = document.getElementById(`page-${page}`);
    if (el) el.classList.add('active');

    const nav = document.querySelector(`[data-page="${page}"]`);
    if (nav) nav.classList.add('active');

    // Update topbar title
    const titles = {
        dashboard: 'Risk Dashboard',
        patients: 'All Patients',
        outreach: 'Outreach Log',
        analytics: 'Analytics'
    };
    document.getElementById('pageTitle').textContent = titles[page] || 'Dashboard';

    // Load page-specific data
    if (page === 'analytics') loadAnalytics();
    if (page === 'outreach') loadContacts();
    if (page === 'patients') { currentPage = 1; renderPatientList(); }

    // Close mobile sidebar
    closeSidebar();
    window.scrollTo(0, 0);
}

// ── Data Loading ────────────────────────────────────────────────────────────
async function loadDashboard() {
    try {
        const res = await fetch(`${API}/dashboard`);
        allWomen = await res.json();
        filteredWomen = [...allWomen];

        // Animate counters
        const high = allWomen.filter(w => w.risk_label === 'High').length;
        const med = allWomen.filter(w => w.risk_label === 'Medium').length;
        const low = allWomen.filter(w => w.risk_label === 'Low').length;

        animateCount('totalCount', allWomen.length);
        animateCount('highCount', high);
        animateCount('medCount', med);
        animateCount('lowCount', low);

        // Render dashboard list (top 10)
        renderDashboardList();

        // Render dashboard mini-chart
        renderRiskDonut('dashDonut', high, med, low);

        // Render village hotspots
        renderVillageHotspots();

        // Render activity feed
        renderActivityFeed();

    } catch (e) {
        document.getElementById('dashboardGrid').innerHTML =
            '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Cannot connect to AnchalAI backend.<br>Make sure the API is running.</p></div>';
    }
}

function animateCount(id, target) {
    let current = 0;
    const el = document.getElementById(id);
    if (!el) return;
    const inc = Math.max(target / 25, 1);
    const timer = setInterval(() => {
        current += inc;
        if (current >= target) {
            el.textContent = target;
            clearInterval(timer);
        } else {
            el.textContent = Math.floor(current);
        }
    }, 25);
}

// ── Dashboard Rendering ─────────────────────────────────────────────────────
function renderDashboardList() {
    const grid = document.getElementById('dashboardGrid');
    const top = allWomen.slice(0, 10);

    if (top.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>No patient data available.</p></div>';
        return;
    }

    grid.innerHTML = top.map((w, i) => makeWomanCard(w, i + 1)).join('');
}

function makeWomanCard(w, rank) {
    const initials = w.name ? w.name.split(' ').map(n => n[0]).join('') : '?';
    const missed = w.attended_last_visit === 0;
    return `
    <div class="woman-card ${w.risk_label}" onclick="openModal(${w.id})">
        <div class="woman-rank">${rank}</div>
        <div class="woman-avatar ${w.risk_label}">${initials}</div>
        <div class="woman-details">
            <div class="woman-name">${w.name || 'Patient #' + w.id}</div>
            <div class="woman-meta">
                <span class="meta-chip">Age ${w.age}</span>
                <span class="meta-chip">📍 ${w.distance_to_phc_km} km</span>
                <span class="meta-chip">${w.village || ''}</span>
                <span class="meta-chip" style="color:${missed ? 'var(--crimson)' : 'var(--green)'};background:${missed ? 'var(--crimson-pale)' : 'var(--green-pale)'}">
                    ${missed ? '✗ Missed visit' : '✓ Attended'}
                </span>
            </div>
        </div>
        <div class="risk-indicator">
            <div class="risk-percent ${w.risk_label}">${w.risk_percent}%</div>
            <span class="risk-badge ${w.risk_label}">${w.risk_label}</span>
        </div>
        <button class="reach-btn" onclick="event.stopPropagation(); openModal(${w.id})">Reach Out</button>
    </div>`;
}

// ── Risk Donut Chart (Canvas) ───────────────────────────────────────────────
function renderRiskDonut(canvasId, high, med, low) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Auto-scale for retina displays
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0) return; // Hidden
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const total = high + med + low || 1;
    const w = rect.width, h = rect.height;
    const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 20, inner = r * 0.58;

    ctx.clearRect(0, 0, w, h);

    const segments = [
        { val: high, color: '#C0392B', label: 'High' },
        { val: med, color: '#D4860A', label: 'Medium' },
        { val: low, color: '#1E8449', label: 'Low' },
    ];

    let startAngle = -Math.PI / 2;
    segments.forEach(seg => {
        const sliceAngle = (seg.val / total) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, r, startAngle, startAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = seg.color;
        ctx.fill();
        startAngle += sliceAngle;
    });

    // Inner circle (donut hole)
    ctx.beginPath();
    ctx.arc(cx, cy, inner, 0, Math.PI * 2);
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    ctx.fillStyle = isDark ? '#1C1A18' : '#FFFFFF';
    ctx.fill();

    // Center text
    ctx.fillStyle = isDark ? '#E8E4E0' : '#1C1C1E';
    ctx.font = 'bold 24px "Playfair Display", serif';
    ctx.textAlign = 'center';
    ctx.fillText(total, cx, cy + 2);
    ctx.fillStyle = isDark ? '#A09890' : '#6B6560';
    ctx.font = '10px "DM Sans", sans-serif';
    ctx.fillText('TOTAL', cx, cy + 16);

    // Legend
    let ly = h - 8;
    ctx.font = '11px "DM Sans", sans-serif';
    const legendX = [w * 0.15, w * 0.45, w * 0.75];
    segments.forEach((seg, i) => {
        ctx.fillStyle = seg.color;
        ctx.fillRect(legendX[i] - 6, ly - 8, 10, 10);
        ctx.fillStyle = isDark ? '#A09890' : '#6B6560';
        ctx.textAlign = 'left';
        ctx.fillText(`${seg.label}: ${seg.val}`, legendX[i] + 8, ly);
    });
}

// ── Village Hotspots ────────────────────────────────────────────────────────
function renderVillageHotspots() {
    const container = document.getElementById('villageHotspots');
    if (!container) return;

    const villageMap = {};
    allWomen.forEach(w => {
        if (!villageMap[w.village]) villageMap[w.village] = { total: 0, riskSum: 0, high: 0 };
        villageMap[w.village].total++;
        villageMap[w.village].riskSum += w.risk_percent;
        if (w.risk_label === 'High') villageMap[w.village].high++;
    });

    const sorted = Object.entries(villageMap)
        .map(([v, d]) => ({ village: v, ...d, avg: d.riskSum / d.total }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 8);

    container.innerHTML = `
    <table class="village-table">
        <thead><tr><th>Village</th><th>Women</th><th>Avg Risk</th><th>High Risk</th></tr></thead>
        <tbody>
            ${sorted.map(v => `
                <tr>
                    <td style="font-weight:600">${v.village}</td>
                    <td>${v.total}</td>
                    <td><span style="color:${v.avg > 50 ? 'var(--crimson)' : v.avg > 35 ? 'var(--gold)' : 'var(--green)'};font-weight:600">${v.avg.toFixed(1)}%</span></td>
                    <td>${v.high > 0 ? `<span style="color:var(--crimson);font-weight:600">${v.high}</span>` : '0'}</td>
                </tr>
            `).join('')}
        </tbody>
    </table>`;
}

// ── Activity Feed ───────────────────────────────────────────────────────────
function renderActivityFeed() {
    const container = document.getElementById('activityFeed');
    if (!container) return;

    // Show top 5 highest risk as recent alerts
    const top5 = allWomen.slice(0, 5);
    container.innerHTML = top5.map(w => `
        <div class="activity-item">
            <div class="activity-dot ${w.risk_label}"></div>
            <div class="activity-text"><strong>${w.name}</strong> flagged as ${w.risk_label} Risk (${w.risk_percent}%)</div>
            <div class="activity-time">${w.village}</div>
        </div>
    `).join('');
}

// ── Patients Page ───────────────────────────────────────────────────────────
function renderPatientList() {
    let list = [...allWomen];

    // Apply search
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        list = list.filter(w =>
            (w.name && w.name.toLowerCase().includes(q)) ||
            (w.village && w.village.toLowerCase().includes(q)) ||
            (w.risk_label && w.risk_label.toLowerCase().includes(q))
        );
    }

    // Apply filter
    if (currentFilter !== 'All') {
        list = list.filter(w => w.risk_label === currentFilter);
    }

    filteredWomen = list;
    const totalPages = Math.ceil(list.length / PER_PAGE);
    const start = (currentPage - 1) * PER_PAGE;
    const pageData = list.slice(start, start + PER_PAGE);

    const grid = document.getElementById('patientsGrid');
    if (pageData.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>No patients found matching your criteria.</p></div>';
    } else {
        grid.innerHTML = pageData.map((w, i) => makeWomanCard(w, start + i + 1)).join('');
    }

    // Pagination
    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const container = document.getElementById('pagination');
    if (!container) return;
    if (totalPages <= 1) { container.innerHTML = ''; return; }

    let html = `<button ${currentPage <= 1 ? 'disabled' : ''} onclick="goPage(${currentPage - 1})">← Prev</button>`;

    for (let i = 1; i <= totalPages; i++) {
        if (i <= 3 || i >= totalPages - 1 || Math.abs(i - currentPage) <= 1) {
            html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
        } else if (i === 4 || i === totalPages - 2) {
            html += '<span>…</span>';
        }
    }

    html += `<button ${currentPage >= totalPages ? 'disabled' : ''} onclick="goPage(${currentPage + 1})">Next →</button>`;
    container.innerHTML = html;
}

function goPage(p) {
    currentPage = p;
    renderPatientList();
    document.getElementById('page-patients').scrollTo(0, 0);
}

function filterPatients(label, btn) {
    currentFilter = label;
    currentPage = 1;
    document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Update for current page context
    const activePage = document.querySelector('.page.active');
    if (activePage && activePage.id === 'page-dashboard') {
        renderDashboardList();
    } else {
        renderPatientList();
    }
}

function onSearch(e) {
    searchQuery = e.target.value;
    currentPage = 1;
    renderPatientList();
}

// ── Modal ───────────────────────────────────────────────────────────────────
function openModal(patientId) {
    const w = allWomen.find(p => p.id === patientId);
    if (!w) return;
    currentProfile = w;
    currentLang = "Bengali";

    document.getElementById('modalName').textContent = w.name || 'Patient #' + w.id;
    document.getElementById('modalMeta').textContent =
        `Age ${w.age} · ${w.village || ''} · ${w.distance_to_phc_km} km from PHC`;
    document.getElementById('modalRiskNum').textContent = w.risk_percent + '%';

    // Reset language tabs
    document.querySelectorAll('.lang-tab').forEach((b, i) => b.classList.toggle('active', i === 0));

    // Show factors
    const chips = document.getElementById('factorChips');
    chips.innerHTML = (w.top_factors || []).map(f => `<span class="factor-chip">${f}</span>`).join('');

    // Show modal
    document.getElementById('modalOverlay').classList.add('active');
    document.getElementById('escalationBanner').innerHTML = '';

    // Generate message
    generateMessage();
}

async function generateMessage() {
    const box = document.getElementById('messageBox');
    box.className = 'message-box loading';
    box.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>&nbsp; Generating with Gemini...';

    try {
        const res = await fetch(`${API}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...currentProfile, language: currentLang })
        });
        const data = await res.json();

        box.className = 'message-box';
        box.textContent = data.message;

        // Update factors from response
        if (data.top_factors) {
            document.getElementById('factorChips').innerHTML =
                data.top_factors.map(f => `<span class="factor-chip">${f}</span>`).join('');
        }

        // Show escalation
        if (data.escalation) {
            const esc = data.escalation;
            const banner = document.getElementById('escalationBanner');
            banner.innerHTML = `
                <div class="escalation-banner ${esc.urgency || 'low'}">
                    <span>${esc.icon || '📋'}</span>
                    <span>${esc.action}</span>
                </div>`;
        }
    } catch (e) {
        box.className = 'message-box';
        box.textContent = 'Error generating message. Please check if the backend is running.';
    }
}

function switchLang(lang, btn) {
    currentLang = lang;
    document.querySelectorAll('.lang-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    generateMessage();
}

async function markContacted() {
    if (!currentProfile) return;

    const messageBox = document.getElementById('messageBox');
    const message = messageBox ? messageBox.textContent : '';

    try {
        await fetch(`${API}/contact`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_id: currentProfile.id,
                patient_name: currentProfile.name,
                village: currentProfile.village,
                language: currentLang,
                message: message,
                risk_percent: currentProfile.risk_percent,
                risk_label: currentProfile.risk_label,
            })
        });
        showToast(`✓ ${currentProfile.name} marked as contacted`);
    } catch (e) {
        showToast('⚠ Could not save contact — backend may be offline');
    }

    closeModal();
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
}

// ── Outreach Log Page ───────────────────────────────────────────────────────
async function loadContacts() {
    const container = document.getElementById('contactsList');
    container.innerHTML = '<div class="empty-state"><div class="loading-dots" style="justify-content:center"><span></span><span></span><span></span></div><p>Loading outreach history...</p></div>';

    try {
        const res = await fetch(`${API}/contacts`);
        contactsData = await res.json();
        renderContacts();
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Could not load outreach history.</p></div>';
    }
}

function renderContacts() {
    const container = document.getElementById('contactsList');

    // Stats
    const total = contactsData.length;
    const pending = contactsData.filter(c => c.follow_up_status === 'pending').length;

    document.getElementById('outreachTotal').textContent = total;
    document.getElementById('outreachPending').textContent = pending;

    if (total === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>No outreach contacts yet.<br>Start by clicking "Reach Out" on a patient.</p></div>';
        return;
    }

    container.innerHTML = contactsData.map(c => {
        const dt = c.timestamp ? new Date(c.timestamp) : null;
        const timeStr = dt ? dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
        return `
        <div class="contact-card">
            <div class="cc-icon">📞</div>
            <div class="cc-details">
                <div class="cc-name">${c.patient_name || 'Unknown'}</div>
                <div class="cc-meta">${c.village || ''} · ${c.language || ''} · <span class="risk-badge ${c.risk_label}" style="display:inline;padding:2px 8px;font-size:10px">${c.risk_label} ${c.risk_percent}%</span></div>
            </div>
            <div class="cc-time">${timeStr}</div>
        </div>`;
    }).join('');
}

// ── Analytics Page ──────────────────────────────────────────────────────────
async function loadAnalytics() {
    try {
        const res = await fetch(`${API}/analytics`);
        analyticsData = await res.json();
        renderAnalytics();
    } catch (e) {
        document.getElementById('page-analytics').innerHTML =
            '<div class="empty-state"><div class="empty-icon">📊</div><p>Could not load analytics data.</p></div>';
    }
}

function renderAnalytics() {
    if (!analyticsData) return;
    const d = analyticsData;

    // Key metrics
    document.getElementById('metricTotal').textContent = d.total_women || 0;
    document.getElementById('metricAvgRisk').textContent = (d.avg_risk_percent || 0) + '%';
    document.getElementById('metricContacts').textContent = d.outreach?.total_contacts || 0;

    // Risk donut
    const rd = d.risk_distribution || {};
    renderRiskDonut('analyticsDonut', rd.High || 0, rd.Medium || 0, rd.Low || 0);

    // Feature importance bar chart
    renderFeatureImportance(d.model_metrics?.feature_importance || {});

    // Village table
    renderAnalyticsVillageTable(d.village_stats || []);

    // Model metrics
    const mm = d.model_metrics || {};
    document.getElementById('modelAccuracy').textContent = mm.accuracy ? (mm.accuracy * 100).toFixed(1) + '%' : 'N/A';
    document.getElementById('modelAUC').textContent = mm.auc_roc ? mm.auc_roc.toFixed(3) : 'N/A';
    document.getElementById('modelF1').textContent = mm.f1_score ? mm.f1_score.toFixed(3) : 'N/A';
}

function renderFeatureImportance(features) {
    const canvas = document.getElementById('featureCanvas');
    if (!canvas || !features) return;
    const ctx = canvas.getContext('2d');
    
    // Auto-scale for retina displays
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0) return; // Hidden
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const sorted = Object.entries(features).sort((a, b) => b[1] - a[1]);
    const maxVal = sorted[0]?.[1] || 1;
    const barH = Math.min(24, (h - 20) / sorted.length - 4);
    const labelW = 160;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    sorted.forEach(([name, val], i) => {
        const y = 10 + i * (barH + 4);
        const barW = ((w - labelW - 20) * val) / maxVal;

        // Label
        ctx.fillStyle = isDark ? '#A09890' : '#6B6560';
        ctx.font = '11px "DM Sans", sans-serif';
        ctx.textAlign = 'right';
        const displayName = name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        ctx.fillText(displayName, labelW - 10, y + barH / 2 + 4);

        // Bar — use brand gradient
        const gradient = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
        gradient.addColorStop(0, '#2D7D8B');
        gradient.addColorStop(1, '#3A9E9E');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(labelW, y, barW, barH, 4);
        ctx.fill();

        // Value
        ctx.fillStyle = isDark ? '#E8E4E0' : '#2C2420';
        ctx.textAlign = 'left';
        ctx.fillText((val * 100).toFixed(1) + '%', labelW + barW + 6, y + barH / 2 + 4);
    });
}

function renderAnalyticsVillageTable(villages) {
    const container = document.getElementById('analyticsVillages');
    if (!container) return;

    container.innerHTML = `
    <table class="village-table">
        <thead><tr><th>Village</th><th>Women</th><th>Avg Risk</th><th>High Risk</th></tr></thead>
        <tbody>
            ${villages.map(v => `
                <tr>
                    <td style="font-weight:600">${v.village}</td>
                    <td>${v.count}</td>
                    <td><span style="color:${v.avg_risk > 50 ? 'var(--crimson)' : v.avg_risk > 35 ? 'var(--gold)' : 'var(--green)'};font-weight:600">${v.avg_risk}%</span></td>
                    <td>${v.high_risk_count > 0 ? `<span style="color:var(--crimson);font-weight:600">${v.high_risk_count}</span>` : '0'}</td>
                </tr>
            `).join('')}
        </tbody>
    </table>`;
}

// ── Theme Toggle ────────────────────────────────────────────────────────────
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('anchalai-theme', next);
    document.getElementById('themeBtn').textContent = next === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';

    const high = allWomen.filter(w => w.risk_label === 'High').length;
    const med = allWomen.filter(w => w.risk_label === 'Medium').length;
    const low = allWomen.filter(w => w.risk_label === 'Low').length;
    renderRiskDonut('dashDonut', high, med, low);
    if (analyticsData) {
        const rd = analyticsData.risk_distribution || {};
        renderRiskDonut('analyticsDonut', rd.High || 0, rd.Medium || 0, rd.Low || 0);
        renderFeatureImportance(analyticsData.model_metrics?.feature_importance || {});
    }
}

// ── Mobile Sidebar ──────────────────────────────────────────────────────────
function toggleSidebar() {
    document.querySelector('aside').classList.toggle('open');
    document.querySelector('.sidebar-overlay').classList.toggle('open');
}
function closeSidebar() {
    document.querySelector('aside').classList.remove('open');
    document.querySelector('.sidebar-overlay').classList.remove('open');
}

// ── Toast Notifications ─────────────────────────────────────────────────────
function showToast(msg) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ═══════════════════════════════════════════════════════════════════════════════
// GEMINI CHAT ASSISTANT — "Anchal Sahayak"
// ═══════════════════════════════════════════════════════════════════════════════
let chatOpen = false;
let chatMessages = [];

function toggleChat() {
    chatOpen = !chatOpen;
    document.getElementById('chatPanel').classList.toggle('active', chatOpen);
    document.getElementById('chatFab').classList.toggle('hidden', chatOpen);

    if (chatOpen && chatMessages.length === 0) {
        // Welcome message
        const lang = document.getElementById('chatLang') ? document.getElementById('chatLang').value : 'Hindi';
        let greeting = '';
        if (lang === 'Bengali') {
            greeting = 'নমস্কার! 🙏 আমি আঁচল সহায়ক — আপনার এআই সহকারী।\n\nআপনি আমাকে যেকোনো কিছু জিজ্ঞাসা করতে পারেন:\n• "সীতাকে তার পরবর্তী ভিজিট সম্পর্কে কী বলব?"\n• "হাই রিস্ক মানে কী?"\n• "তৃতীয় ত্রৈমাসিকে কী মনে রাখা উচিত?"';
        } else if (lang === 'English') {
            greeting = 'Hello! 🙏 I am Anchal Sahayak — your AI assistant.\n\nYou can ask me anything:\n• "What should I tell Sita about her next visit?"\n• "What does High Risk mean?"\n• "What to keep in mind during the 3rd trimester?"';
        } else {
            greeting = 'नमस्ते! 🙏 मैं आंचल सहायक हूँ — आपकी AI सहायिका।\n\nआप मुझसे कुछ भी पूछ सकती हैं:\n• "सीता को क्या बताऊं उनकी अगली विज़िट के बारे में?"\n• "हाई रिस्क का मतलब क्या है?"\n• "तीसरी तिमाही में क्या ध्यान रखें?"';
        }
        addChatMessage('bot', greeting);
    }

    setTimeout(() => document.getElementById('chatInput')?.focus(), 100);
}

function closeChat() {
    chatOpen = false;
    document.getElementById('chatPanel').classList.remove('active');
    document.getElementById('chatFab').classList.remove('hidden');
}

function updateChatPlaceholder() {
    const lang = document.getElementById('chatLang').value;
    const input = document.getElementById('chatInput');
    if (!input) return;
    if (lang === 'Bengali') input.placeholder = 'যেকোনো কিছু জিজ্ঞাসা করুন... (Ask anything)';
    else if (lang === 'English') input.placeholder = 'Ask anything...';
    else input.placeholder = 'कुछ भी पूछें... (Ask anything)';
}

function addChatMessage(type, text) {
    chatMessages.push({ type, text });
    renderChatMessages();
}

function renderChatMessages() {
    const container = document.getElementById('chatMessages');
    container.innerHTML = chatMessages.map(m => {
        const formatted = m.text.replace(/\n/g, '<br>');
        return `<div class="chat-msg ${m.type}">${formatted}</div>`;
    }).join('');
    container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    // Add user message
    addChatMessage('user', message);
    input.value = '';

    // Show typing indicator
    const typingId = Date.now();
    chatMessages.push({ type: 'typing', text: 'टाइप कर रही हूँ...', id: typingId });
    renderChatMessages();

    try {
        const chatLangStr = document.getElementById('chatLang') ? document.getElementById('chatLang').value : 'Hindi';
        const body = {
            message: message,
            language: chatLangStr,
        };
        // If a patient is currently selected in the modal, pass context
        if (currentProfile) {
            body.patient_id = currentProfile.id;
        }

        const res = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();

        // Remove typing indicator
        chatMessages = chatMessages.filter(m => m.id !== typingId);
        addChatMessage('bot', data.reply || 'कुछ गड़बड़ हो गई। फिर से कोशिश करें।');
    } catch (e) {
        chatMessages = chatMessages.filter(m => m.id !== typingId);
        addChatMessage('bot', '⚠️ सर्वर से कनेक्ट नहीं हो पा रहा। कृपया बाद में प्रयास करें।');
    }
}

function handleChatKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
}

// ── Initialization ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Restore theme
    const savedTheme = localStorage.getItem('anchalai-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('themeBtn').textContent = savedTheme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeChat();
        }
        if (e.key === '/' && !document.activeElement.closest('input')) {
            e.preventDefault();
            document.getElementById('globalSearch')?.focus();
        }
    });

    // Load data
    loadDashboard();
    navigate('dashboard');
});

