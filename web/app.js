// API Base URL
const API_BASE = '/api';

// ============================================================
// Sidebar Navigation
// ============================================================

const navItems = document.querySelectorAll('.nav-item');
const contentPanels = document.querySelectorAll('.content-panel');

function navigateTo(panelId) {
    navItems.forEach(n => {
        n.classList.toggle('active', n.dataset.panel === panelId);
    });
    contentPanels.forEach(panel => {
        panel.classList.toggle('active', panel.id === panelId);
    });
    if (panelId === 'my-blogs') loadMyBlogs();
    if (panelId === 'my-dna') loadMyDna();
    if (panelId === 'my-calibrations') loadMyCalibrations();
    if (panelId === 'quick-compare') { populateQcStyleSelect(); loadQcHistory(); }
    if (panelId === 's2-blog-write') loadRecentBlogs();
    if (panelId === 's1-blog-status') loadCollections();
}

navItems.forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.panel));
});


// ============================================================
// Authentication Status Check
// ============================================================

async function checkAuthStatus() {
    const loginGate    = document.getElementById('login-gate');
    const appContent   = document.getElementById('app-content');
    const userSection  = document.getElementById('user-section');
    const loginSection = document.getElementById('topbar-login-section');
    const sidebarLoggedIn  = document.getElementById('sidebar-logged-in');
    const sidebarLoggedOut = document.getElementById('sidebar-logged-out');

    function showApp()   { if (appContent) appContent.classList.remove('hidden'); if (loginGate) loginGate.classList.add('hidden'); }
    function showGate()  { if (loginGate) loginGate.classList.remove('hidden');  if (appContent) appContent.classList.add('hidden'); }

    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();

        if (data.logged_in) {
            // 로그인 완료
            showApp();
            if (userSection)  userSection.style.display  = 'flex';
            if (loginSection) loginSection.style.display = 'none';

            const avatar = document.getElementById('user-avatar');
            const name   = document.getElementById('user-name');
            if (avatar && data.user?.picture) avatar.src = data.user.picture;
            if (name)   name.textContent = data.user?.name || data.user?.email || '';

            if (sidebarLoggedIn)  sidebarLoggedIn.classList.remove('hidden');
            if (sidebarLoggedOut) sidebarLoggedOut.classList.add('hidden');
            const sidebarAvatar   = document.getElementById('sidebar-avatar');
            const sidebarUsername = document.getElementById('sidebar-username');
            if (sidebarAvatar && data.user?.picture) sidebarAvatar.src = data.user.picture;
            if (sidebarUsername) sidebarUsername.textContent = data.user?.name || data.user?.email || '';

        } else if (data.sso_enabled) {
            // SSO 활성화 + 미로그인 → 전체 화면 로그인 게이트
            showGate();
            if (userSection)  userSection.style.display  = 'none';
            if (loginSection) loginSection.style.display = 'block';
            if (sidebarLoggedIn)  sidebarLoggedIn.classList.add('hidden');
            if (sidebarLoggedOut) sidebarLoggedOut.classList.remove('hidden');

        } else {
            // SSO 미설정 — 로그인 없이 전체 사용, 버튼 숨김
            showApp();
            if (userSection)  userSection.style.display  = 'none';
            if (loginSection) loginSection.style.display = 'none';
            if (sidebarLoggedIn)  sidebarLoggedIn.classList.add('hidden');
            if (sidebarLoggedOut) sidebarLoggedOut.classList.add('hidden');
        }

    } catch (error) {
        console.error('Auth check failed:', error);
        showGate();
        if (userSection)  userSection.style.display  = 'none';
        if (loginSection) loginSection.style.display = 'block';
    }
}

// ============================================================
// Utility Functions
// ============================================================

async function apiRequest(endpoint, method = 'GET', data = null, isFormData = false) {
    const options = { method };

    if (data) {
        if (isFormData) {
            options.body = data;
        } else {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(data);
        }
    }

    const url = `${API_BASE}${endpoint}`;
    let response;
    try {
        response = await fetch(url, options);
    } catch (networkErr) {
        console.error(`[API] 네트워크 오류 ${method} ${url}:`, networkErr);
        throw new Error('네트워크 오류 — 서버에 연결할 수 없습니다.');
    }

    if (!response.ok) {
        const rawText = await response.text();
        console.error(`[API] ${method} ${url} → ${response.status}\n응답:`, rawText.slice(0, 500));
        if (rawText.trim().startsWith('<')) {
            throw new Error(`서버 오류 (${response.status}) — 콘솔에서 상세 내용을 확인하세요.`);
        }
        try {
            const errJson = JSON.parse(rawText);
            throw new Error(errJson.error || `API 오류 (${response.status})`);
        } catch (e) {
            if (e.message.startsWith('API') || e.message.startsWith('서버')) throw e;
            throw new Error(`API 오류 (${response.status}): ${rawText.slice(0, 100)}`);
        }
    }

    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch (e) {
        console.error(`[API] ${method} ${url} → 200이지만 JSON 아님:`, text.slice(0, 500));
        throw new Error(`서버 응답 파싱 오류 — 콘솔을 확인하세요.`);
    }
}

function setLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

function showResult(resultBox, content) {
    resultBox.innerHTML = content;
    resultBox.classList.remove('hidden');
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(resultBox, message) {
    resultBox.innerHTML = `<div class="error-message">${message}</div>`;
    resultBox.classList.remove('hidden');
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatMultilineText(value) {
    return escapeHtml(value).replace(/\n/g, '<br>');
}

// ============================================================
// File Upload Handlers
// ============================================================

// Persona File Upload
const personaFileInput = document.getElementById('persona-file');
const personaFileUploadArea = document.getElementById('file-upload-area');
const personaFileSelected = document.getElementById('file-selected');
const personaFileName = document.getElementById('file-name');
const personaFileRemove = document.getElementById('file-remove');
const clientNameInput = document.getElementById('client-name');

if (personaFileUploadArea) {
    personaFileUploadArea.addEventListener('click', () => { personaFileInput.click(); });

    personaFileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        personaFileUploadArea.classList.add('dragover');
    });

    personaFileUploadArea.addEventListener('dragleave', () => {
        personaFileUploadArea.classList.remove('dragover');
    });

    personaFileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        personaFileUploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) handlePersonaFileSelect(files[0]);
    });

    personaFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handlePersonaFileSelect(e.target.files[0]);
    });

    personaFileRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        clearPersonaFile();
    });
}

function handlePersonaFileSelect(file) {
    const validExtensions = ['.txt', '.pdf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
        alert('지원되지 않는 파일 형식입니다. TXT 또는 PDF 파일을 선택해주세요.');
        return;
    }

    personaFileUploadArea.querySelector('.file-upload-content').classList.add('hidden');
    personaFileSelected.classList.remove('hidden');
    personaFileName.textContent = file.name;
    personaFileUploadArea.classList.add('has-file');

    const filename = file.name.replace(/\.[^/.]+$/, '');
    const nameParts = filename.split('_');
    if (nameParts.length > 1) {
        clientNameInput.value = nameParts[nameParts.length - 1];
    } else {
        clientNameInput.value = filename;
    }
}

function clearPersonaFile() {
    personaFileInput.value = '';
    personaFileUploadArea.querySelector('.file-upload-content').classList.remove('hidden');
    personaFileSelected.classList.add('hidden');
    personaFileName.textContent = '';
    personaFileUploadArea.classList.remove('has-file');
    clientNameInput.value = '';
}

// Press Release File Upload
const pressFileInput = document.getElementById('press-file');
const pressFileUploadArea = document.getElementById('press-file-upload-area');
const pressFileSelected = document.getElementById('press-file-selected');
const pressFileName = document.getElementById('press-file-name');
const pressFileRemove = document.getElementById('press-file-remove');

if (pressFileUploadArea) {
    pressFileUploadArea.addEventListener('click', () => { pressFileInput.click(); });

    pressFileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        pressFileUploadArea.classList.add('dragover');
    });

    pressFileUploadArea.addEventListener('dragleave', () => {
        pressFileUploadArea.classList.remove('dragover');
    });

    pressFileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        pressFileUploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) handlePressFileSelect(files);
    });

    pressFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handlePressFileSelect(e.target.files);
    });

    pressFileRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        clearPressFile();
    });
}

function handlePressFileSelect(fileList) {
    const validExtensions = ['.txt', '.pdf', '.hwp', '.docx', '.jpg', '.jpeg', '.png'];
    const files = Array.from(fileList);

    if (files.some(file => !validExtensions.includes('.' + file.name.split('.').pop().toLowerCase()))) {
        alert('지원되지 않는 파일 형식입니다. TXT, PDF, HWP, DOCX, JPG, PNG 파일을 선택해주세요.');
        return;
    }

    pressFileUploadArea.querySelector('.file-upload-content').classList.add('hidden');
    pressFileSelected.classList.remove('hidden');
    pressFileName.textContent = files.length === 1
        ? files[0].name
        : `${files.length}개 파일 선택: ${files.map(file => file.name).join(', ')}`;
    pressFileUploadArea.classList.add('has-file');
}

function clearPressFile() {
    pressFileInput.value = '';
    pressFileUploadArea.querySelector('.file-upload-content').classList.remove('hidden');
    pressFileSelected.classList.add('hidden');
    pressFileName.textContent = '';
    pressFileUploadArea.classList.remove('has-file');
}

// ============================================================
// Load Blog Collections for Dropdowns
// ============================================================

async function loadCollections() {
    try {
        const data = await apiRequest('/blog/collections');
        const collections = data.collections || [];

        // Populate select dropdowns (Aggregated by blog_id)
        const optionsHTML = collections.map(c =>
            `<option value="${c.blog_id}">${c.blog_id} (${c.post_count}개, ${(c.total_chars / 1000).toFixed(1)}K자)</option>`
        ).join('');

        const defaultOpt = '<option value="">컬렉션을 선택하세요</option>';

        ['status-collection-select', 'biz-collection-select'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = defaultOpt + optionsHTML;
        });

        // Populate collection list in 1-2 tab (Table View)
        const listBody = document.getElementById('blog-collections-body');
        if (listBody) {
            if (collections.length === 0) {
                listBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">수집된 블로그가 없습니다. 블로그 주소를 입력해 수집을 시작하세요.</td></tr>';
            } else {
                listBody.innerHTML = collections.map(c => `
                    <tr>
                        <td class="font-medium">${c.blog_id}</td>
                        <td>${c.post_count}개</td>
                        <td>${(c.total_chars / 1000).toFixed(1)}K자</td>
                        <td class="text-muted" style="font-size: 0.85rem;">${c.last_collected_at}</td>
                        <td>
                            <button class="btn btn-sm" style="padding:4px 10px;font-size:0.8rem;"
                                onclick="goToDnaAnalysis('${c.blog_id}')">DNA 분석</button>
                        </td>
                    </tr>
                `).join('');
            }
        }

        // DNA 선택 드롭다운이 비어있으면 힌트 표시
        const dnaSelect = document.getElementById('blog-dna-select');
        const dnaHint = document.getElementById('dna-empty-hint');
        if (dnaSelect && dnaHint) {
            const hasOptions = collections.length > 0;
            dnaHint.style.display = hasOptions ? 'none' : 'block';
            dnaSelect.innerHTML = (hasOptions ? '<option value="">DNA 미적용 (기본 스타일)</option>' : '<option value="">수집된 블로그 없음</option>')
                + collections.map(c => `<option value="${c.blog_id}">${c.blog_id} (${c.post_count}개)</option>`).join('');
        }

        console.log(`${collections.length}개 컬렉션 로드됨`);
    } catch (error) {
        console.error('컬렉션 로드 실패:', error);
        const listEl = document.getElementById('blog-collections-list');
        if (listEl) listEl.innerHTML = '<p class="text-muted">컬렉션 로드 실패</p>';
    }
}


// ============================================================
// 1-2: Blog Collection Form
// ============================================================

document.getElementById('blog-collect-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('blog-collect-result');

    const blogId = document.getElementById('blog-id-input').value.trim();
    const count = document.getElementById('blog-count').value;

    if (!blogId) {
        showError(resultBox, '블로그 주소 또는 ID를 입력해주세요.');
        return;
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/blog/collect', 'POST', {
            blog_id: blogId,
            count: parseInt(count)
        });

        const postsHTML = result.posts.map(p => `
            <div style="padding: 10px 0; border-bottom: 1px solid var(--border-color);">
                <div style="font-weight: 500;">${p.title}</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">${p.date} | ${p.content_length.toLocaleString()}자</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">${p.content_preview}...</div>
            </div>
        `).join('');

        const html = `
            <h3>블로그 수집 완료</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0;">
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">블로그 ID</div>
                    <div style="font-weight: 600; margin-top: 4px;">${result.blog_id}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">수집 글 수</div>
                    <div style="font-weight: 600; margin-top: 4px;">${result.post_count}개</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">총 글자수</div>
                    <div style="font-weight: 600; margin-top: 4px;">${(result.total_chars / 1000).toFixed(1)}K자</div>
                </div>
            </div>
            <h4>수집된 글 목록</h4>
            ${postsHTML}
        `;

        showResult(resultBox, html);
        loadCollections(); // Refresh collections list

        // 다음 단계 배너 표시
        const nextBanner = document.getElementById('collect-next-step');
        if (nextBanner) {
            nextBanner.classList.remove('hidden');
            // DNA 선택 드롭다운에 방금 수집한 블로그 자동 선택 준비
            nextBanner.dataset.blogId = result.blog_id;
        }

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

// ============================================================
// 1-3: Blog Status Analysis Form
// ============================================================

document.getElementById('blog-status-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('blog-status-result');
    const errorBox = document.getElementById('blog-status-error');

    const blog_id = document.getElementById('status-collection-select').value;
    if (!blog_id) {
        errorBox.textContent = '분석할 블로그를 선택해주세요.';
        errorBox.classList.remove('hidden');
        return;
    }
    errorBox.classList.add('hidden');

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/blog/analyze-status', 'POST', { blog_id });

        // Chart.js Radar Chart
        const ctx = document.getElementById('dna-radar-chart');
        if (ctx) {
            if (window.dnaChart) window.dnaChart.destroy();
            window.dnaChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['격식도', '친밀감', '유머/위트', '비유/수사', '이모지 활용'],
                    datasets: [{
                        label: '블로그 DNA 지표',
                        data: [
                            result.c2_tone_mood?.formality_level || 5,
                            result.c2_tone_mood?.warmth_level || 5,
                            result.c4_rhetoric?.humor_usage || 5,
                            result.c4_rhetoric?.metaphor_usage || 5,
                            result.c10_visual_formatting?.emoji_usage || 5
                        ],
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                        borderColor: '#000000',
                        pointBackgroundColor: '#000000',
                        borderWidth: 2
                    }]
                },
                options: {
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 10,
                            ticks: { stepSize: 2, display: false },
                            grid: { color: 'rgba(0,0,0,0.05)' },
                            angleLines: { color: 'rgba(0,0,0,0.05)' },
                            pointLabels: { font: { size: 11, weight: '600' } }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        // 10가지 카테고리 렌더링 헬퍼
        function renderCategory(cat) {
            if (!cat) return '';
            const entries = Object.entries(cat).filter(([k]) => k !== 'title');
            const itemsHTML = entries.map(([key, val]) => {
                const label = key.replace(/_/g, ' ');
                if (Array.isArray(val)) {
                    if (key === 'examples' || key.endsWith('_examples')) {
                        return `<div style="margin-top: 8px;"><div style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 4px;">${label}</div>${val.map(v => `<div style="background: var(--bg-primary); padding: 8px 12px; border-left: 3px solid var(--accent-primary); margin: 4px 0; font-size: 0.85rem; font-style: italic;">"${v}"</div>`).join('')}</div>`;
                    }
                    return `<div style="margin-top: 6px;"><div style="color: var(--text-muted); font-size: 0.8rem;">${label}</div><div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px;">${val.map(v => `<span style="background: var(--bg-primary); padding: 3px 10px; border-radius: 12px; font-size: 0.82rem; border: 1px solid var(--border-color);">${v}</span>`).join('')}</div></div>`;
                }
                return `<div style="margin-top: 6px;"><span style="color: var(--text-muted); font-size: 0.8rem;">${label}: </span><span style="font-size: 0.9rem;">${val}</span></div>`;
            }).join('');
            return `<div class="dna-cat-card">
                <h4 class="dna-cat-title">${cat.title || ''}</h4>
                ${itemsHTML}
            </div>`;
        }

        const categories = [
            result.c1_template_structure,
            result.c2_tone_mood,
            result.c3_speech_style,
            result.c4_rhetoric,
            result.c5_frequent_expressions,
            result.c6_sentence_patterns,
            result.c7_vocabulary,
            result.c8_paragraph_composition,
            result.c9_opening_closing,
            result.c10_visual_formatting
        ];

        resultBox.classList.remove('hidden');
        const detailsContent = document.getElementById('dna-details-content');
        if (detailsContent) {
            detailsContent.innerHTML = `
                <div class="dna-details-grid">
                    ${categories.map((cat, i) => renderCategory(cat)).join('')}
                </div>
            `;
        }

        // DNA 분석 완료 → blog-dna-select 자동 선택 + 글 작성 이동 버튼
        const dnaSelect = document.getElementById('blog-dna-select');
        if (dnaSelect) {
            // blog_id 옵션이 있으면 선택
            const opt = Array.from(dnaSelect.options).find(o => o.value === blog_id);
            if (opt) {
                dnaSelect.value = blog_id;
                dnaSelect.dispatchEvent(new Event('change'));
            }
        }

        // 분석 완료 후 글 작성 이동 버튼 추가 (없으면)
        const resultBoxEl = document.getElementById('dna-result-box') || resultBox;
        if (resultBoxEl && !resultBoxEl.querySelector('.dna-goto-write')) {
            const gotoBtn = document.createElement('button');
            gotoBtn.className = 'btn-primary dna-goto-write';
            gotoBtn.style.cssText = 'margin-top:20px;width:100%;padding:13px;border-radius:980px;font-size:14px;font-weight:700';
            gotoBtn.textContent = '이 DNA로 글 쓰러 가기';
            gotoBtn.onclick = () => {
                navigateTo('s2-blog-write');
                // DNA select 다시 확인
                const sel = document.getElementById('blog-dna-select');
                if (sel) { sel.value = blog_id; sel.dispatchEvent(new Event('change')); }
            };
            resultBoxEl.appendChild(gotoBtn);
        }

    } catch (error) {
        errorBox.textContent = `분석 실패: ${error.message}`;
        errorBox.classList.remove('hidden');
    } finally {
        setLoading(submitBtn, false);
    }
});


// ============================================================
// Style Templates
// ============================================================

async function loadStyleTemplates() {
    const grid = document.getElementById('style-template-grid');
    if (!grid) return;

    try {
        const result = await apiRequest('/style-templates');
        const templates = result.templates || [];
        const currentVal = document.getElementById('style-template-id')?.value || 'informational';

        grid.innerHTML = templates.map(t => `
            <div class="style-template-card ${t.id === currentVal ? 'selected' : ''}"
                 data-template-id="${t.id}"
                 onclick="selectStyleTemplate('${t.id}', this)">
                <div class="style-template-name">${t.name}</div>
                <div class="style-template-desc">${t.description}</div>
            </div>
        `).join('');

        // 보정 후 이동 시 pending 스타일 자동 선택
        if (window._pendingStyleId) {
            const pendingCard = document.querySelector(`.style-template-card[data-template-id="${window._pendingStyleId}"]`);
            if (pendingCard) {
                selectStyleTemplate(window._pendingStyleId, pendingCard);
                pendingCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            window._pendingStyleId = null;
        }
    } catch (err) {
        console.error('스타일 템플릿 로드 실패:', err);
    }
}

// 생성된 버전을 빠른 비교 패널로 바로 전달
function goToQuickCompareWithVersion(versionIdx) {
    const versions = window._blogVersions;
    if (!versions || !versions[versionIdx]) { alert('생성된 글이 없습니다.'); return; }

    const activeEl = document.querySelectorAll('.version-content')[versionIdx];
    const title   = activeEl?.querySelector('[data-field="title"]')?.innerText?.trim()
                 || versions[versionIdx].title || '';
    const content = activeEl?.querySelector('[data-field="content"]')?.innerText?.trim()
                 || versions[versionIdx].content || '';

    navigateTo('quick-compare');
    document.getElementById('qc-ai-title').value   = title;
    document.getElementById('qc-ai-content').value = content;

    // 스타일도 동기화
    const styleId = document.getElementById('style-template-id')?.value;
    const qcSel   = document.getElementById('qc-style-select');
    if (qcSel && styleId) qcSel.value = styleId;

    // URL 필드 포커스
    document.getElementById('qc-approved-url')?.focus();
}

// 보정 후 글 작성 패널로 이동 + 스타일 자동 선택
function goToWriteWithStyle(styleId) {
    navigateTo('s2-blog-write');
    if (!styleId) return;
    // 카드가 이미 렌더링 됐으면 바로 선택
    const card = document.querySelector(`.style-template-card[data-template-id="${styleId}"]`);
    if (card) {
        selectStyleTemplate(styleId, card);
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
        // 아직 로딩 중이면 렌더 완료 후 선택
        window._pendingStyleId = styleId;
    }
}

function selectStyleTemplate(id, el) {
    document.querySelectorAll('.style-template-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    const hidden = document.getElementById('style-template-id');
    if (hidden) hidden.value = id;
}

// ============================================================
// 2-1: Blog Generator Form (File Upload)
// ============================================================

document.getElementById('blog-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('blog-result');

    const styleTemplateId = document.getElementById('style-template-id')?.value || 'informational';

    const pressReleaseText = document.getElementById('press-release').value;
    const pressUrl = document.getElementById('press-url')?.value?.trim() || '';
    const referenceBlogUrl = document.getElementById('reference-blog-url')?.value?.trim() || '';
    const hasFile = pressFileInput.files.length > 0;

    if (!hasFile && !pressReleaseText.trim() && !pressUrl) {
        showError(resultBox, '보도자료 파일, URL, 또는 내용을 입력해주세요.');
        return;
    }

    const formData = new FormData();
    formData.append('style_template_id', styleTemplateId);
    formData.append('keywords', document.getElementById('keywords').value);
    formData.append('target_audience', document.getElementById('target-audience').value);
    formData.append('content_angle', document.getElementById('content-angle').value);

    // 블로그 DNA 선택 (선택사항 - 통합 블로그 ID 사용)
    const blogDnaId = document.getElementById('blog-dna-select')?.value;
    if (blogDnaId) {
        formData.append('blog_dna_id', blogDnaId);
    }

    if (hasFile) {
        Array.from(pressFileInput.files).forEach(file => formData.append('files', file));
    }
    if (pressUrl) {
        formData.append('press_url', pressUrl);
    }
    if (pressReleaseText.trim()) {
        formData.append('press_release', pressReleaseText);
    }
    if (referenceBlogUrl) {
        formData.append('reference_blog_url', referenceBlogUrl);
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/blog/generate', 'POST', formData, true);

        const versions = result.versions || [];
        if (versions.length === 0) {
            showError(resultBox, 'AI가 버전을 생성하지 못했습니다.');
            return;
        }

        // 버전별 색상/아이콘
        const versionStyles = {
            formal: { color: '#1a1a1a', icon: '', bg: 'rgba(0,0,0,0.05)' },
            balanced: { color: '#555555', icon: '', bg: 'rgba(0,0,0,0.03)' },
            casual: { color: '#777777', icon: '', bg: 'rgba(0,0,0,0.02)' }
        };

        // 탭 버튼 생성
        const tabsHTML = versions.map((v, i) => {
            const style = versionStyles[v.version_type] || versionStyles.balanced;
            return `<button class="version-tab ${i === 0 ? 'active' : ''}" data-version-idx="${i}" 
                style="--tab-color: ${style.color}; --tab-bg: ${style.bg}">
                <span class="version-tab-icon">${style.icon}</span>
                <span class="version-tab-label">${v.version_label}</span>
            </button>`;
        }).join('');

        // 각 버전 컨텐츠 (편집 가능)
        const contentsHTML = versions.map((v, i) => {
            const paragraphs = v.content.split('\n').filter(p => p.trim() !== '');
            const contentHTML = paragraphs.map(p => `<p>${p}</p>`).join('');

            return `
                <div class="version-content ${i === 0 ? 'active' : ''}" data-version-idx="${i}">
                    <div class="blog-preview editable-preview">
                        <h1 contenteditable="true" class="editable-field" data-field="title">${v.title}</h1>
                        <div class="content editable-field" contenteditable="true" data-field="content">${contentHTML}</div>
                        <div class="tags">
                            ${(v.tags || []).map(tag => `<span class="tag">#${tag}</span>`).join('')}
                        </div>
                    </div>
                    <div class="blog-action-toolbar">
                        <div class="toolbar-hint">클릭하여 직접 수정할 수 있습니다</div>
                        <div class="toolbar-actions">
                            <button type="button" class="btn btn-save-blog" onclick="saveBlogVersion(${i})">
                                <span class="btn-text">💾 저장</span>
                                <span class="btn-loading">저장 중...</span>
                            </button>
                            <button type="button" class="btn btn-naver-copy" onclick="copyAsNaverHTML(${i})" title="네이버 스마트에디터에 붙여넣으면 글꼴/색상/정렬이 적용됩니다">
                                <span class="btn-text">N 네이버 붙여넣기용 복사</span>
                            </button>
                            <button type="button" class="btn btn-export-docs" onclick="exportBlogDocs(${i})">
                                <span class="btn-text">📄 DOCX 내보내기</span>
                                <span class="btn-loading">내보내기 중...</span>
                            </button>
                            <button type="button" class="btn btn-calibrate" onclick="openCalibrationModal(${i})" title="실제 검수 통과된 글을 등록해 AI 스타일을 보정합니다">
                                <span class="btn-text">보정 등록</span>
                            </button>
                            <button type="button" class="btn" style="background:#f5f5f7;border:1px solid #d0d0d0;color:#1d1d1f"
                                onclick="goToQuickCompareWithVersion(${i})" title="빠른 비교 테스트 패널에서 즉시 비교">
                                <span class="btn-text">즉시 비교</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // AI 이미지 생성 버튼 (블로그 결과 하단)
        const imageGenHTML = `
            <div id="image-gen-section" style="margin-top: 24px; padding: 20px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <h4 style="margin: 0;">AI 이미지 생성</h4>
                        <p style="color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0;">Google Imagen으로 본문에 맞는 이미지를 생성합니다</p>
                    </div>
                    <button id="btn-generate-images" class="btn btn-primary" style="padding: 10px 24px; font-size: 0.9rem;" onclick="generateBlogImages()">
                        <span class="btn-text">이미지 생성</span>
                        <span class="btn-loading">이미지 생성 중...</span>
                    </button>
                </div>
                <div id="generated-images-area"></div>
            </div>
        `;

        const sourceSummary = result.source_bundle?.sources?.length
            ? `<div style="margin-top: 16px; color: var(--text-secondary);">
                    <p><strong>입력 자료:</strong> ${result.source_bundle.sources.map(source => `${source.name} (${source.char_count}자)`).join(', ')}</p>
                    ${(result.source_bundle.warnings || []).length ? `<p><strong>추출 참고:</strong> ${result.source_bundle.warnings.join(' / ')}</p>` : ''}
               </div>`
            : '';

        const html = `
            <div style="margin-bottom: 20px;">
                <h3>블로그 3가지 버전 생성 완료</h3>
                <p style="color: var(--text-muted);">동일한 내용을 3가지 톤으로 작성했습니다. 탭을 클릭하여 비교해보세요.</p>
                <p style="color: var(--text-muted);">생성 방식: ${result.generation_mode === 'ai' ? 'AI 생성' : '오프라인 초안 엔진'}</p>
            </div>
            <div class="version-tabs">${tabsHTML}</div>
            <div class="version-panels">${contentsHTML}</div>
            ${imageGenHTML}
            <div style="margin-top: 16px; color: var(--text-secondary);">
                <p><strong>저장 위치:</strong> <code>${result.output_dir}</code></p>
            </div>
            ${sourceSummary}
        `;

        // Store versions data for save/export
        window._blogVersions = versions;
        window._blogOutputDir = result.output_dir;
        window._blogOutputId = result.output_id;

        // Update the versions area and mobile preview
        const versionsArea = document.getElementById('blog-versions-area');
        const mobilePreview = document.getElementById('mobile-preview-content');
        if (versionsArea) versionsArea.innerHTML = html;
        if (mobilePreview) {
            mobilePreview.innerHTML = `<h1>${versions[0].title}</h1>` +
                versions[0].content.split('\n').map(p => p.trim() ? `<p>${p}</p>` : '').join('');
        }

        resultBox.classList.remove('hidden');
        resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // 탭 클릭 이벤트
        resultBox.querySelectorAll('.version-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const idx = tab.dataset.versionIdx;
                resultBox.querySelectorAll('.version-tab').forEach(t => t.classList.remove('active'));
                resultBox.querySelectorAll('.version-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                resultBox.querySelector(`.version-content[data-version-idx="${idx}"]`).classList.add('active');

                // Update mobile preview with current editable content
                syncMobilePreview(resultBox, idx);
            });
        });

        // Sync edits to mobile preview in real-time
        resultBox.querySelectorAll('.editable-field').forEach(field => {
            field.addEventListener('input', () => {
                const versionContent = field.closest('.version-content');
                if (versionContent && versionContent.classList.contains('active')) {
                    const idx = versionContent.dataset.versionIdx;
                    syncMobilePreview(resultBox, idx);
                }
            });
        });

        // 최근 작성한 글 목록 갱신
        loadRecentBlogs();

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

// ============================================================
// 2-1-A: Blog Edit / Save / Export Helpers
// ============================================================

function syncMobilePreview(resultBox, idx) {
    const mobilePreview = document.getElementById('mobile-preview-content');
    const versionEl = resultBox.querySelector(`.version-content[data-version-idx="${idx}"]`);
    if (!mobilePreview || !versionEl) return;

    const titleEl = versionEl.querySelector('[data-field="title"]');
    const contentEl = versionEl.querySelector('[data-field="content"]');
    mobilePreview.innerHTML = `<h1>${titleEl?.innerHTML || ''}</h1>${contentEl?.innerHTML || ''}`;
}

// ============================================================
// 네이버 블로그 HTML 붙여넣기용 복사
// ============================================================

async function copyAsNaverHTML(idx) {
    const versionEl = document.querySelector(`.version-content[data-version-idx="${idx}"]`);
    if (!versionEl) return;

    const btn = versionEl.querySelector('.btn-naver-copy');
    const titleEl = versionEl.querySelector('[data-field="title"]');
    const contentEl = versionEl.querySelector('[data-field="content"]');

    const titleText = titleEl?.innerText?.trim() || '';
    const contentText = contentEl?.innerText?.trim() || '';

    const styles = window._dnaStyles || {};
    const fontFamily = styles.font_family || "'맑은 고딕', MalgunGothic, sans-serif";
    const centerRatio = styles.center_align_ratio || 0;
    const accentColor = styles.accent_color || '#333333';
    const highlightColor = styles.highlight_color || '';
    const bodySz = styles.font_size_body || '11pt';
    const headSz = styles.font_size_heading || '14pt';

    // 단락 분리
    const lines = contentText.split('\n');

    // 각 단락을 Naver 호환 HTML로 변환
    function lineToHtml(line, lineIdx) {
        if (!line.trim()) return '<p><br></p>';

        const isShortLine = line.trim().length <= 30;
        // 중앙정렬: 짧은 줄은 DNA center ratio에 따라, 긴 줄은 낮은 확률로
        const useCenter = isShortLine
            ? centerRatio > 0.2
            : (lineIdx % 10 < Math.round(centerRatio * 5));

        const align = useCenter ? 'center' : 'left';

        let spanStyle = `font-family:${fontFamily};font-size:${bodySz};`;
        let pStyle = `text-align:${align};margin:0;padding:2px 0;`;

        // 짧은 줄 = 소제목처럼 강조
        if (isShortLine && accentColor) {
            spanStyle += `font-size:${headSz};color:${accentColor};font-weight:bold;`;
        }
        // 하이라이트 색상 (DNA에서 추출한 배경색) → 첫 번째 문장에만 적용
        if (lineIdx === 0 && highlightColor) {
            spanStyle += `background-color:${highlightColor};`;
        }

        const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `<p style="${pStyle}"><span style="${spanStyle}">${escaped}</span></p>`;
    }

    const titleHtml = `<p style="text-align:center;margin:0 0 16px;"><span style="font-family:${fontFamily};font-size:18pt;font-weight:bold;color:${accentColor || '#111111'};">${titleText.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</span></p>`;
    const bodyHtml = lines.map((line, i) => lineToHtml(line, i)).join('\n');
    const fullHtml = `<div>${titleHtml}${bodyHtml}</div>`;

    try {
        await navigator.clipboard.write([
            new ClipboardItem({
                'text/html': new Blob([fullHtml], { type: 'text/html' }),
                'text/plain': new Blob([titleText + '\n\n' + contentText], { type: 'text/plain' }),
            })
        ]);
        const btnText = btn.querySelector('.btn-text');
        const orig = btnText.textContent;
        btnText.textContent = '복사 완료! 네이버에 붙여넣기 하세요';
        btn.style.background = '#1a1a1a';
        btn.style.color = '#fff';
        setTimeout(() => {
            btnText.textContent = orig;
            btn.style.background = '';
            btn.style.color = '';
        }, 3000);
    } catch (err) {
        alert('클립보드 복사 실패: ' + err.message + '\n\n브라우저 권한을 확인하거나 HTTPS 환경에서 시도해주세요.');
    }
}

async function saveBlogVersion(idx) {
    const versionEl = document.querySelector(`.version-content[data-version-idx="${idx}"]`);
    if (!versionEl) return;

    const btn = versionEl.querySelector('.btn-save-blog');
    const titleEl = versionEl.querySelector('[data-field="title"]');
    const contentEl = versionEl.querySelector('[data-field="content"]');

    const title = titleEl?.innerText?.trim() || '';
    const content = contentEl?.innerText?.trim() || '';
    const versionData = window._blogVersions?.[idx] || {};

    setLoading(btn, true);
    try {
        const result = await apiRequest('/blog/save', 'POST', {
            title: title,
            content: content,
            version_type: versionData.version_type || 'unknown',
            version_label: versionData.version_label || `Version ${idx + 1}`,
            tags: versionData.tags || [],
            output_id: window._blogOutputId || '',
            output_dir: window._blogOutputDir || ''
        });

        // 저장된 blog_id 기록 (보정 비교에 사용)
        window._lastSavedBlogId = result.blog_id || window._blogOutputId || '';

        // Show success feedback
        btn.classList.add('save-success');
        const btnText = btn.querySelector('.btn-text');
        const origText = btnText.textContent;
        btnText.textContent = '저장 완료';
        setTimeout(() => {
            btnText.textContent = origText;
            btn.classList.remove('save-success');
        }, 2000);

    } catch (error) {
        alert('저장 실패: ' + error.message);
    } finally {
        setLoading(btn, false);
    }
}

async function exportBlogDocs(idx) {
    const versionEl = document.querySelector(`.version-content[data-version-idx="${idx}"]`);
    if (!versionEl) return;

    const btn = versionEl.querySelector('.btn-export-docs');
    const titleEl = versionEl.querySelector('[data-field="title"]');
    const contentEl = versionEl.querySelector('[data-field="content"]');

    const title = titleEl?.innerText?.trim() || '';
    const content = contentEl?.innerText?.trim() || '';
    const versionData = window._blogVersions?.[idx] || {};

    setLoading(btn, true);
    try {
        const response = await fetch(`${API_BASE}/blog/export-docs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                content: content,
                version_type: versionData.version_type || 'unknown',
                version_label: versionData.version_label || `Version ${idx + 1}`,
                tags: versionData.tags || []
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'DOCX 내보내기 실패');
        }

        // Download the DOCX file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/[^가-힣a-zA-Z0-9\s]/g, '').trim() || 'blog'}_${versionData.version_type || 'v'}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        // Success feedback
        const btnText = btn.querySelector('.btn-text');
        const origText = btnText.textContent;
        btnText.textContent = '✅ 다운로드 완료!';
        setTimeout(() => { btnText.textContent = origText; }, 2000);

    } catch (error) {
        alert('내보내기 실패: ' + error.message);
    } finally {
        setLoading(btn, false);
    }
}

// ============================================================
// 2-1-B: Blog Image Generation (On-Demand)
// ============================================================

// 생성된 블로그 본문을 저장 (이미지 생성 시 사용)
let lastBlogContent = '';

// 블로그 생성 성공 시 본문 저장 hook
const origShowResult = window.showResult || function () { };

async function generateBlogImages() {
    const btn = document.getElementById('btn-generate-images');
    const area = document.getElementById('generated-images-area');

    if (!btn || !area) return;

    // 현재 활성된 버전의 본문 가져오기
    const activeContent = document.querySelector('.version-content.active .blog-preview .content');
    if (!activeContent) {
        area.innerHTML = '<p style="color: var(--accent-danger); margin-top: 12px;">블로그 본문을 찾을 수 없습니다.</p>';
        return;
    }

    const blogText = activeContent.innerText || activeContent.textContent;
    if (!blogText.trim()) {
        area.innerHTML = '<p style="color: var(--accent-danger); margin-top: 12px;">블로그 본문이 비어있습니다.</p>';
        return;
    }

    // 단계 1: 이미지 프롬프트 제안받기
    setLoading(btn, true);
    area.innerHTML = `
        <div style="text-align: center; padding: 20px; color: var(--text-muted);">
            <p>본문을 분석하여 이미지 프롬프트를 생성 중입니다...</p>
        </div>
    `;

    try {
        const targetAudience = document.getElementById('target-audience')?.value || '일반 시민';
        const contentAngle = document.getElementById('content-angle')?.value || '정보전달형';

        const result = await apiRequest('/blog/suggest-prompts', 'POST', {
            content: blogText,
            target_audience: targetAudience,
            content_angle: contentAngle
        });

        const prompts = result.prompts || [];
        if (prompts.length === 0) {
            area.innerHTML = '<p style="color: var(--accent-warning); margin-top: 12px;">프롬프트를 생성하지 못했습니다. 직접 입력하시겠습니까?</p>';
            prompts.push(""); // 빈 프롬프트 하나 추가
        }

        // 프롬프트 편집 UI 렌더링
        area.innerHTML = `
            <div style="margin-top: 20px; padding: 16px; background: var(--bg-secondary); border-radius: 10px; border: 1px solid var(--border-color);">
                <h5 style="margin-bottom: 12px;">이미지 생성 프롬프트 확인/수정</h5>
                <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">AI가 추천한 영문 프롬프트입니다. 자유롭게 수정 후 생성하세요.</p>
                
                <div id="prompt-list" style="display: flex; flex-direction: column; gap: 12px;">
                    ${prompts.map((p, i) => `
                        <div style="display: flex; gap: 10px; align-items: flex-start;">
                            <textarea id="prompt-input-${i}" class="form-control" style="flex: 1; height: 80px; font-size: 0.85rem; padding: 10px;" placeholder="영문 프롬프트를 입력하세요...">${p}</textarea>
                            <button class="btn btn-primary" style="padding: 8px 16px; font-size: 0.82rem; min-width: 100px;" onclick="generateSingleImage(${i})">
                                <span class="btn-text">이걸로 생성</span>
                                <span class="btn-loading">...</span>
                            </button>
                        </div>
                    `).join('')}
                </div>
                
                <div style="margin-top: 16px; border-top: 1px solid var(--border-color); padding-top: 16px; display: flex; justify-content: space-between; align-items: center;">
                    <button class="btn" style="background: rgba(0,0,0,0.05); font-size: 0.82rem;" onclick="addPromptInput()">+ 프롬프트 추가</button>
                    <button id="btn-generate-all" class="btn btn-primary" style="padding: 10px 24px; font-weight: 600;" onclick="generateAllImages()">전체 생성하기</button>
                </div>
            </div>
            <div id="final-images-area"></div>
        `;

        window._suggestedPrompts = prompts;

    } catch (error) {
        area.innerHTML = `<p style="color: var(--accent-danger); margin-top: 12px;">프롬프트 추천 실패: ${error.message}</p>`;
    } finally {
        setLoading(btn, false);
    }
}

// 프롬프트 입력창 추가
function addPromptInput() {
    const list = document.getElementById('prompt-list');
    const idx = list.querySelectorAll('textarea').length;
    const div = document.createElement('div');
    div.style.cssText = 'display: flex; gap: 10px; align-items: flex-start;';
    div.innerHTML = `
        <textarea id="prompt-input-${idx}" class="form-control" style="flex: 1; height: 80px; font-size: 0.85rem; padding: 10px;" placeholder="영문 프롬프트를 입력하세요..."></textarea>
        <button class="btn btn-primary" style="padding: 8px 16px; font-size: 0.82rem; min-width: 100px;" onclick="generateSingleImage(${idx})">
            <span class="btn-text">이걸로 생성</span>
            <span class="btn-loading">...</span>
        </button>
    `;
    list.appendChild(div);
}

// 특정 프롬프트 하나로 이미지 생성
async function generateSingleImage(idx) {
    const textarea = document.getElementById(`prompt-input-${idx}`);
    const prompt = textarea.value.trim();
    if (!prompt) {
        alert('프롬프트를 입력해주세요.');
        return;
    }

    const btn = textarea.nextElementSibling;
    const finalArea = document.getElementById('final-images-area');

    setLoading(btn, true);

    try {
        const targetAudience = document.getElementById('target-audience')?.value || '일반 시민';
        const contentAngle = document.getElementById('content-angle')?.value || '정보전달형';

        const result = await apiRequest('/blog/generate-images', 'POST', {
            prompts: [prompt],
            target_audience: targetAudience,
            content_angle: contentAngle
        });

        renderGeneratedImages(result.images, true);
    } catch (e) {
        alert('이미지 생성 실패: ' + e.message);
    } finally {
        setLoading(btn, false);
    }
}

// 모든 프롬프트로 이미지 생성
async function generateAllImages() {
    const textareas = document.querySelectorAll('#prompt-list textarea');
    const prompts = Array.from(textareas).map(t => t.value.trim()).filter(p => p !== "");

    if (prompts.length === 0) {
        alert('생성할 프롬프트가 없습니다.');
        return;
    }

    const btn = document.getElementById('btn-generate-all');
    const finalArea = document.getElementById('final-images-area');

    setLoading(btn, true);
    finalArea.innerHTML = '<div style="text-align: center; padding: 20px;">전체 이미지 생성 중... (잠시만 기다려주세요)</div>';

    try {
        const targetAudience = document.getElementById('target-audience')?.value || '일반 시민';
        const contentAngle = document.getElementById('content-angle')?.value || '정보전달형';

        const result = await apiRequest('/blog/generate-images', 'POST', {
            prompts: prompts,
            target_audience: targetAudience,
            content_angle: contentAngle
        });

        renderGeneratedImages(result.images);
    } catch (e) {
        finalArea.innerHTML = `<p style="color: var(--accent-danger);">이미지 생성 실패: ${e.message}</p>`;
    } finally {
        setLoading(btn, false);
    }
}

// 생성된 이미지 렌더링
function renderGeneratedImages(images, append = false) {
    const area = document.getElementById('final-images-area');
    if (!area) return;

    if (!window._allImages) window._allImages = [];

    // 중복 제거 및 병합
    if (append) {
        window._allImages = [...window._allImages, ...images];
    } else {
        window._allImages = images;
    }

    area.innerHTML = `
        <div style="margin-top: 24px;">
            <h4 style="margin-bottom: 12px;">생성된 이미지 (${window._allImages.length}장)</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
                ${window._allImages.map((img, idx) => `
                    <div class="image-card" style="border-radius: 10px; overflow: hidden; border: 1px solid var(--border-color); background: white;">
                        <img src="${img.data_uri}" alt="AI Generated ${idx + 1}" 
                             style="width: 100%; height: 180px; object-fit: cover; display: block; cursor: pointer;"
                             onclick="window.open(this.src, '_blank')" />
                        <div style="padding: 10px; background: var(--bg-secondary);">
                            <div style="font-size: 0.72rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; font-family: monospace;">
                                ${img.prompt || ''}
                            </div>
                            <button onclick="insertImageToBlog('${img.data_uri.substring(0, 50)}...', ${idx})"
                                    style="width: 100%; padding: 6px 12px; background: var(--gradient-primary); color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 500; cursor: pointer; transition: var(--transition);"
                                    id="insert-btn-${idx}">
                                본문에 삽입
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    // 이미지 data_uri 정보 갱신
    window._generatedImages = window._allImages;
}

// 삽입된 이미지 수 카운터 (문단별 분산 삽입용)
if (!window._insertedImageCount) window._insertedImageCount = 0;

function insertImageToBlog(_, imgIdx) {
    const images = window._generatedImages || [];
    if (imgIdx >= images.length) return;

    const img = images[imgIdx];
    const contents = document.querySelectorAll('.version-content .blog-preview .content');

    if (contents.length === 0) {
        alert('삽입할 블로그 본문을 찾을 수 없습니다.');
        return;
    }

    contents.forEach((activeContent, vIdx) => {
        // 문단(p, div, br 등) 요소들 수집
        const paragraphs = Array.from(activeContent.children).filter(
            el => !el.classList.contains('inserted-image')
        );

        // 이미지 요소 생성 (중앙 정렬 스타일 포함)
        const imgElement = document.createElement('div');
        imgElement.className = 'inserted-image';
        imgElement.style.cssText = 'text-align: center; margin: 24px 0;';
        imgElement.innerHTML = `
            <img src="${img.data_uri}" alt="AI Generated" 
                 style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); display: block; margin: 0 auto;" />
        `;

        // 문단 사이에 분산 삽입: 전체 문단을 균등 분할하여 배치
        const totalImages = images.length;
        const currentBatchIdx = window._generatedImagesMap ? (window._generatedImagesMap[imgIdx] || 0) : 0;

        // 각 버전별로 동일한 상대적 위치에 삽입되도록 함
        const step = Math.max(1, Math.floor(paragraphs.length / (totalImages + 1)));
        const targetIdx = Math.min(step * (window._insertedImageCount + 1), paragraphs.length) - 1;

        if (targetIdx >= 0 && paragraphs[targetIdx]) {
            // 해당 문단 뒤에 삽입
            paragraphs[targetIdx].after(imgElement);
        } else {
            // fallback: 마지막에 추가
            activeContent.appendChild(imgElement);
        }
    });

    window._insertedImageCount++;

    // 삽입 완료 표시
    const btn = document.getElementById(`insert-btn-${imgIdx}`);
    if (btn) {
        btn.textContent = '모든 버전에 삽입됨';
        btn.disabled = true;
        btn.style.background = 'var(--accent-success)';
        btn.style.opacity = '0.7';
    }
}


// ============================================================
// Refresh Buttons
// ============================================================

document.getElementById('refresh-collections-status')?.addEventListener('click', () => loadCollections());
document.getElementById('refresh-biz-collections')?.addEventListener('click', () => loadCollections());
document.getElementById('refresh-blog-dna')?.addEventListener('click', () => loadCollections());

// ============================================================
// DNA 스타일 미리보기
// ============================================================

document.getElementById('blog-dna-select')?.addEventListener('change', async (e) => {
    const blogId = e.target.value;
    const panel = document.getElementById('dna-preview-panel');
    const body = document.getElementById('dna-preview-body');
    const content = document.getElementById('dna-preview-content');
    const arrow = document.getElementById('dna-preview-arrow');
    if (!panel || !body || !content) return;

    if (!blogId) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';
    body.style.display = 'block';
    if (arrow) arrow.textContent = '▲ 접기';
    content.textContent = '불러오는 중...';

    try {
        const result = await apiRequest(`/blog/dna-preview?blog_id=${encodeURIComponent(blogId)}`);
        content.textContent = result.preview_text || '미리보기 없음';
        // 네이버 HTML 변환에 쓸 스타일 데이터 저장
        window._dnaStyles = result.dna_styles || null;
    } catch (err) {
        content.textContent = err.message || 'DNA 미리보기 로드 실패. 먼저 글쓰기 DNA 분석을 실행하세요.';
    }
});

document.getElementById('dna-preview-toggle')?.addEventListener('click', () => {
    const body = document.getElementById('dna-preview-body');
    const arrow = document.getElementById('dna-preview-arrow');
    if (!body) return;
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    if (arrow) arrow.textContent = isOpen ? '▼ 펼치기' : '▲ 접기';
});

// ============================================================
// My Page: Data Management
// ============================================================

function formatDate(isoStr) {
    if (!isoStr) return '-';
    try {
        const d = new Date(isoStr);
        return d.toLocaleDateString('ko-KR') + ' ' + d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    } catch { return isoStr; }
}

// --- 블로그 글 관리 ---
async function loadMyBlogs() {
    try {
        const res = await fetch(`${API_BASE}/mypage/blogs`);
        const data = await res.json();
        const table = document.getElementById('my-blogs-grid');
        const empty = document.getElementById('my-blogs-empty');
        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            empty.style.display = 'block'; table.style.display = 'none'; return;
        }
        empty.style.display = 'none'; table.style.display = 'table';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="lt-title">${item.title || '(제목없음)'}</td>
                <td class="lt-meta">${item.style_template_id || item.client_id || '-'}</td>
                <td class="lt-meta">${item.version_count || 0}개</td>
                <td class="lt-date">${formatDate(item.created_at)}</td>
                <td class="lt-actions">
                    <button class="lt-btn" onclick="viewDetail('blogs','${item.id}','블로그 상세')">상세</button>
                    <button class="lt-btn lt-btn-docs" onclick="exportToGoogleDocs('blogs','${item.id}')">Docs</button>
                    <button class="lt-btn lt-btn-del" onclick="deleteItem('blogs','${item.id}',this)">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('블로그 목록 로드 실패:', e); }
}

// --- DNA 관리 ---
async function loadMyDna() {
    try {
        const res = await fetch(`${API_BASE}/mypage/dna`);
        const data = await res.json();
        const table = document.getElementById('my-dna-grid');
        const empty = document.getElementById('my-dna-empty');
        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            empty.style.display = 'block'; table.style.display = 'none'; return;
        }
        empty.style.display = 'none'; table.style.display = 'table';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="lt-title">${item.blog_id || '-'}</td>
                <td class="lt-meta">${item.post_count || 0}개</td>
                <td class="lt-date">${formatDate(item.created_at)}</td>
                <td class="lt-actions">
                    <button class="lt-btn" onclick="viewDetail('dna','${item.id}','DNA 분석 상세')">상세</button>
                    <button class="lt-btn lt-btn-del" onclick="deleteItem('dna','${item.id}',this)">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('DNA 목록 로드 실패:', e); }
}

// --- 상세 보기 모달 ---
let _currentDetailType = '';
let _currentDetailId = '';

async function viewDetail(type, id, title) {
    const modal = document.getElementById('detail-modal');
    const modalTitle = document.getElementById('detail-modal-title');
    const modalBody = document.getElementById('detail-modal-body');

    _currentDetailType = type;
    _currentDetailId = id;
    modalTitle.textContent = title;
    modalBody.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">로딩 중...</div>';
    modal.classList.remove('hidden');

    // Google Docs 내보내기 버튼 표시
    const exportBtn = document.getElementById('detail-modal-export');
    if (exportBtn) exportBtn.style.display = 'inline-flex';

    try {
        const res = await fetch(`${API_BASE}/mypage/${type}/${id}`);
        const data = await res.json();
        modalBody.innerHTML = renderDetailContent(type, data);
    } catch (e) {
        modalBody.innerHTML = `<div class="error-message">데이터 로드 실패: ${e.message}</div>`;
    }
}

function renderDetailContent(type, data) {
    if (type === 'personas') {
        const pa = data.persona_analysis || {};
        let html = `<div class="detail-section">
            <div class="detail-section-title">기본 정보</div>
            <div class="detail-field"><span class="detail-field-label">이름</span><span class="detail-field-value">${data.client_name || data.client_id}</span></div>
            <div class="detail-field"><span class="detail-field-label">소속</span><span class="detail-field-value">${data.organization || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">생성일</span><span class="detail-field-value">${formatDate(data.created_at)}</span></div>
        </div>`;
        html += `<div class="detail-section">
            <div class="detail-section-title">페르소나 분석 결과</div>
            <div class="detail-text-block">${JSON.stringify(pa, null, 2)}</div>
        </div>`;
        return html;
    }
    if (type === 'blogs') {
        const versions = data.versions || [];
        let html = `<div class="detail-section">
            <div class="detail-section-title">기본 정보</div>
            <div class="detail-field"><span class="detail-field-label">출력 ID</span><span class="detail-field-value">${data.output_id || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">페르소나</span><span class="detail-field-value">${data.client_id || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">생성일</span><span class="detail-field-value">${formatDate(data.created_at)}</span></div>
        </div>`;
        versions.forEach(ver => {
            html += `<div class="detail-section">
                <div class="detail-section-title">${ver.version_label || ver.version_type} 버전</div>
                <div class="detail-field"><span class="detail-field-label">제목</span><span class="detail-field-value">${ver.title || ''}</span></div>
                <div class="detail-field"><span class="detail-field-label">태그</span><span class="detail-field-value"><span class="detail-tags">${(ver.tags || []).map(t => `<span class="detail-tag">${t}</span>`).join('')}</span></span></div>
                <div class="detail-text-block">${ver.content || ''}</div>
            </div>`;
        });
        return html;
    }
    if (type === 'dna') {
        let html = `<div class="detail-section">
            <div class="detail-section-title">분석 정보</div>
            <div class="detail-field"><span class="detail-field-label">블로그 ID</span><span class="detail-field-value">${data.blog_id || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">컬렉션</span><span class="detail-field-value">${data.folder || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">분석글수</span><span class="detail-field-value">${data.post_count || 0}개</span></div>
            <div class="detail-field"><span class="detail-field-label">생성일</span><span class="detail-field-value">${formatDate(data.created_at)}</span></div>
        </div>`;
        // DNA 카테고리별 표시
        const categories = Object.keys(data).filter(k => k.startsWith('c'));
        categories.forEach(key => {
            const cat = data[key];
            if (cat && typeof cat === 'object' && cat.title) {
                html += `<div class="detail-section">
                    <div class="detail-section-title">${cat.title}</div>
                    <div class="detail-text-block">${JSON.stringify(cat, null, 2)}</div>
                </div>`;
            }
        });
        return html;
    }
    if (type === 'business') {
        const bp = data.business_personality || {};
        const cs = data.communication_style || {};
        const cp = data.content_preferences || {};
        const wa = data.work_approach || {};
        let html = `<div class="detail-section">
            <div class="detail-section-title">업무적 성격</div>
            <div class="detail-field"><span class="detail-field-label">유형</span><span class="detail-field-value">${bp.type || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">설명</span><span class="detail-field-value">${bp.description || '-'}</span></div>
        </div>`;
        html += `<div class="detail-section">
            <div class="detail-section-title">커뮤니케이션 스타일</div>
            <div class="detail-field"><span class="detail-field-label">선호 방식</span><span class="detail-field-value">${cs.preferred || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">응답 속도</span><span class="detail-field-value">${cs.response_speed || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">디테일</span><span class="detail-field-value">${cs.detail_level || '-'}</span></div>
        </div>`;
        html += `<div class="detail-section">
            <div class="detail-section-title">콘텐츠 선호</div>
            <div class="detail-field"><span class="detail-field-label">톤</span><span class="detail-field-value">${cp.tone || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">스타일</span><span class="detail-field-value">${cp.style || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">관심 토픽</span><span class="detail-field-value">${(cp.topics || []).join(', ')}</span></div>
        </div>`;
        html += `<div class="detail-section">
            <div class="detail-section-title">업무 접근 방식</div>
            <div class="detail-field"><span class="detail-field-label">의사결정</span><span class="detail-field-value">${wa.decision_style || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">피드백 패턴</span><span class="detail-field-value">${wa.feedback_pattern || '-'}</span></div>
            <div class="detail-field"><span class="detail-field-label">우선시</span><span class="detail-field-value">${wa.priority_focus || '-'}</span></div>
        </div>`;
        if (data.agency_recommendations) {
            html += `<div class="detail-section">
                <div class="detail-section-title">대응 전략</div>
                ${data.agency_recommendations.map(r => `<div style="padding:4px 0;">• ${r}</div>`).join('')}
            </div>`;
        }
        if (data.summary) {
            html += `<div class="detail-section">
                <div class="detail-section-title">요약</div>
                <div>${data.summary}</div>
            </div>`;
        }
        return html;
    }
    if (type === 'blogs') {
        const versions = Array.isArray(data.versions) ? data.versions : [];
        const sourceBundle = data.source_bundle || {};
        const sourceNames = Array.isArray(sourceBundle.sources)
            ? sourceBundle.sources.map(source => `${source.name} (${source.char_count || 0}자)`)
            : [];

        let html = `<div class="detail-section">
            <div class="detail-section-title">기본 정보</div>
            <div class="detail-field"><span class="detail-field-label">제목</span><span class="detail-field-value">${escapeHtml(data.title || versions[0]?.title || '(제목없음)')}</span></div>
            <div class="detail-field"><span class="detail-field-label">클라이언트</span><span class="detail-field-value">${escapeHtml(data.client_id || '-')}</span></div>
            <div class="detail-field"><span class="detail-field-label">생성일</span><span class="detail-field-value">${escapeHtml(formatDate(data.created_at))}</span></div>
            <div class="detail-field"><span class="detail-field-label">생성 방식</span><span class="detail-field-value">${escapeHtml(data.generation_mode === 'ai' ? 'AI 생성' : '오프라인 초안 엔진')}</span></div>
        </div>`;

        if (sourceNames.length > 0 || (sourceBundle.warnings || []).length > 0) {
            html += `<div class="detail-section">
                <div class="detail-section-title">입력 자료</div>
                ${sourceNames.length > 0 ? `<div class="detail-text-block">${formatMultilineText(sourceNames.join('\n'))}</div>` : ''}
                ${(sourceBundle.warnings || []).length > 0 ? `<div class="detail-text-block" style="margin-top:12px;">${formatMultilineText(sourceBundle.warnings.join('\n'))}</div>` : ''}
            </div>`;
        }

        versions.forEach(version => {
            const tags = Array.isArray(version.tags) ? version.tags : [];
            html += `<div class="detail-section">
                <div class="detail-section-title">${escapeHtml(version.version_label || version.version_type || '버전')}</div>
                <div class="detail-field"><span class="detail-field-label">제목</span><span class="detail-field-value">${escapeHtml(version.title || '(제목없음)')}</span></div>
                ${tags.length > 0 ? `<div class="detail-tags">${tags.map(tag => `<span class="detail-tag">#${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
                <div class="detail-text-block">${formatMultilineText(version.content || '')}</div>
            </div>`;
        });

        return html;
    }
    return `<div class="detail-text-block">${JSON.stringify(data, null, 2)}</div>`;
}

// --- 항목 삭제 ---
async function deleteItem(type, id, btnEl) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`${API_BASE}/mypage/${type}/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            // 해당 탭 리로드
            if (type === 'blogs') loadMyBlogs();
            else if (type === 'dna') loadMyDna();
        } else {
            alert(data.error || '삭제 실패');
        }
    } catch (e) { alert('삭제 실패: ' + e.message); }
}

// --- 모달 닫기 ---
document.getElementById('detail-modal-close')?.addEventListener('click', () => {
    document.getElementById('detail-modal').classList.add('hidden');
});
document.querySelector('.detail-modal-overlay')?.addEventListener('click', () => {
    document.getElementById('detail-modal').classList.add('hidden');
});

// --- Google Docs 내보내기 ---
async function exportToGoogleDocs(type, id) {
    const btn = event?.target;
    const origText = btn ? btn.textContent : '';
    if (btn) { btn.textContent = '내보내는 중...'; btn.disabled = true; }

    try {
        const res = await fetch(`${API_BASE}/export/google-docs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, id })
        });
        const data = await res.json();

        if (data.success) {
            window.open(data.doc_url, '_blank');
            if (btn) btn.textContent = '완료!';
            setTimeout(() => { if (btn) { btn.textContent = origText; btn.disabled = false; } }, 2000);
        } else {
            alert(data.error || 'Google Docs 내보내기 실패');
            if (btn) { btn.textContent = origText; btn.disabled = false; }
        }
    } catch (e) {
        alert('Google Docs 내보내기 실패: ' + e.message);
        if (btn) { btn.textContent = origText; btn.disabled = false; }
    }
}

// --- 모달 내 Google Docs 내보내기 버튼 ---
document.getElementById('detail-modal-export')?.addEventListener('click', () => {
    exportToGoogleDocs(_currentDetailType, _currentDetailId);
});

// --- 최근 작성한 글 (블로그 작성 패널 내) ---
async function loadRecentBlogs() {
    try {
        const res = await fetch(`${API_BASE}/mypage/blogs`);
        const data = await res.json();
        const table = document.getElementById('recent-blogs-grid');
        const empty = document.getElementById('recent-blogs-empty');
        if (!table) return;
        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            empty.style.display = 'block'; table.style.display = 'none'; return;
        }
        empty.style.display = 'none'; table.style.display = 'table';
        data.items.slice(0, 10).forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="lt-title">${item.title || '(제목없음)'}</td>
                <td class="lt-meta">${item.style_template_id || item.client_id || '-'}</td>
                <td class="lt-meta">${item.version_count || 0}개</td>
                <td class="lt-date">${formatDate(item.created_at)}</td>
                <td class="lt-actions">
                    <button class="lt-btn" onclick="viewDetail('blogs','${item.id}','블로그 상세')">상세</button>
                    <button class="lt-btn lt-btn-docs" onclick="exportToGoogleDocs('blogs','${item.id}')">Docs</button>
                    <button class="lt-btn lt-btn-calibrate" onclick="openCalibrationFromBlog('${item.id}','${item.title?.replace(/'/g,'') || ''}','${item.style_template_id || ''}')">비교</button>
                    <button class="lt-btn lt-btn-del" onclick="deleteItem('blogs','${item.id}',this); setTimeout(loadRecentBlogs,300);">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('최근 블로그 로드 실패:', e); }
}


// ============================================================
// Initialize
// ============================================================

// ============================================================
// 보정 루프 — openCalibrationModal / 모달 핸들러 / loadMyCalibrations
// ============================================================

// 최근 글 테이블의 "비교" 버튼에서 호출
function openCalibrationFromBlog(blogId, blogTitle, styleTemplateId) {
    const modal = document.getElementById('calibration-modal');
    modal.dataset.blogId = blogId;
    modal.dataset.styleTemplateId = styleTemplateId;

    document.getElementById('cal-ai-title-preview').textContent = blogTitle || blogId;
    document.getElementById('cal-approved-url').value = '';
    document.getElementById('cal-result').classList.add('hidden');
    document.getElementById('cal-result').innerHTML = '';

    modal.classList.remove('hidden');
}

// 생성 직후 버전 탭의 "보정 등록" 버튼 — 저장 없이 바로 비교
function openCalibrationModal(versionIdx) {
    const versionEl = document.querySelector(`.version-content[data-version-idx="${versionIdx}"]`);
    if (!versionEl) return;
    const title   = versionEl.querySelector('[data-field="title"]')?.innerText?.trim() || '';
    const content = versionEl.querySelector('[data-field="content"]')?.innerText?.trim() || '';
    const styleId = document.getElementById('style-template-id')?.value || '';

    const modal = document.getElementById('calibration-modal');
    // ai_title/ai_content 직접 저장 (blog_id 불필요)
    modal.dataset.blogId = window._lastSavedBlogId || '';
    modal.dataset.aiTitle = title;
    modal.dataset.aiContent = content;
    modal.dataset.styleTemplateId = styleId;

    document.getElementById('cal-ai-title-preview').textContent = title || '(현재 생성된 글)';
    document.getElementById('cal-approved-url').value = '';
    document.getElementById('cal-result').classList.add('hidden');
    document.getElementById('cal-result').innerHTML = '';

    modal.classList.remove('hidden');
}

function closeCalibrationModal() {
    document.getElementById('calibration-modal').classList.add('hidden');
}

document.getElementById('cal-modal-close')?.addEventListener('click', closeCalibrationModal);
document.getElementById('cal-modal-cancel')?.addEventListener('click', closeCalibrationModal);
document.getElementById('cal-modal-overlay')?.addEventListener('click', closeCalibrationModal);

document.getElementById('cal-modal-submit')?.addEventListener('click', async () => {
    const modal = document.getElementById('calibration-modal');
    const approvedUrl = document.getElementById('cal-approved-url').value.trim();

    if (!approvedUrl) {
        alert('실제 게시된 블로그 URL을 입력해주세요.');
        return;
    }
    if (!approvedUrl.startsWith('http')) {
        alert('올바른 URL을 입력해주세요. (https://... 형식)');
        return;
    }

    const btn = document.getElementById('cal-modal-submit');
    setLoading(btn, true);

    const styleId = modal.dataset.styleTemplateId || document.getElementById('style-template-id')?.value || '';
    const dnaId   = document.getElementById('blog-dna-select')?.value || '';
    try {
        const result = await apiRequest('/blog/calibrate-from-url', 'POST', {
            blog_id:          modal.dataset.blogId || '',
            ai_title:         modal.dataset.aiTitle || '',
            ai_content:       modal.dataset.aiContent || '',
            approved_url:     approvedUrl,
            style_template_id: styleId,
            blog_dna_id:      dnaId
        });
        const meta = result.meta || {
            blog_id:          modal.dataset.blogId || '',
            ai_title:         modal.dataset.aiTitle || '',
            approved_url:     approvedUrl,
            style_template_id: styleId,
            blog_dna_id:      dnaId
        };
        renderCalibrationChecklist(result.analysis || {}, 'cal-result', meta);
    } catch (e) {
        alert('비교 분석 실패: ' + e.message);
    } finally {
        setLoading(btn, false);
    }
});

// 보정 기록 패널
async function loadMyCalibrations() {
    try {
        const data = await apiRequest('/blog/calibrations');
        const cals = data.calibrations || [];
        const grid = document.querySelector('#my-calibrations-grid tbody');
        const empty = document.getElementById('my-calibrations-empty');

        if (!cals.length) {
            if (empty) empty.style.display = 'block';
            if (grid) grid.innerHTML = '';
            return;
        }
        if (empty) empty.style.display = 'none';
        if (grid) {
            grid.innerHTML = cals.map(c => {
                const score = c.similarity_score ?? '?';
                const scoreColor = score >= 80 ? 'var(--accent-success)' : score >= 60 ? 'var(--accent-warning)' : 'var(--accent-danger)';
                const urlShort = c.approved_url ? c.approved_url.replace(/^https?:\/\//, '').substring(0, 30) + '...' : '—';
                return `
                <tr>
                    <td style="font-size:0.85rem">${c.style_template_id || '—'}</td>
                    <td style="font-size:0.82rem;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${c.ai_title}">${c.ai_title || '—'}</td>
                    <td style="font-size:0.9rem;font-weight:700;color:${scoreColor};text-align:center">${score}%</td>
                    <td style="font-size:0.82rem;color:var(--text-muted);max-width:220px">${c.tone_shift || c.calibration_prompt || '—'}</td>
                    <td style="font-size:0.82rem;color:var(--text-muted)">${c.created_at || '—'}</td>
                    <td><button class="btn-view" style="font-size:0.78rem;color:var(--accent-danger)"
                        onclick="deleteCalibration('${c.calibration_id}')">삭제</button></td>
                </tr>`;
            }).join('');
        }
    } catch (e) {
        console.error('보정 기록 로드 실패:', e);
    }
}

async function deleteCalibration(calId) {
    if (!confirm('이 보정 기록을 삭제하시겠습니까?')) return;
    try {
        await apiRequest(`/blog/calibration/${calId}`, 'DELETE');
        loadMyCalibrations();
    } catch (e) {
        alert('삭제 실패: ' + e.message);
    }
}

// ============================================================
// 빠른 비교 테스트 패널
// ============================================================

// 전체 선택/해제 토글
function toggleAllCalItems(checked, containerId) {
    document.getElementById(containerId)
        .querySelectorAll('.cal-item-check')
        .forEach(cb => { cb.checked = checked; });
}

// 선택 항목 저장
async function saveSelectedCalibration(containerId) {
    const container = document.getElementById(containerId);
    const a     = container._calAnalysis;
    const meta  = container._calMeta;
    const items = container._calItems;

    const checks = container.querySelectorAll('.cal-item-check');
    const selected = [];
    checks.forEach((cb, i) => { if (cb.checked) selected.push(items[i]); });

    if (!selected.length) { alert('최소 1개 항목을 선택해주세요.'); return; }

    // 선택 항목 기반 calibration_prompt 구성
    const doMore  = selected.filter(i => i.category === '더 활용').map(i => i.text);
    const doLess  = selected.filter(i => i.category === '줄일 것').map(i => i.text);
    const singles = selected.filter(i => i.category !== '더 활용' && i.category !== '줄일 것');
    const parts = [];
    if (doMore.length)  parts.push(`더 활용할 것: ${doMore.join(', ')}`);
    if (doLess.length)  parts.push(`줄일 것: ${doLess.join(', ')}`);
    singles.forEach(i => parts.push(`${i.category}: ${i.text}`));
    const customPrompt = parts.join('. ');

    const btn = document.getElementById(`${containerId}-save-btn`);
    btn.disabled = true;
    btn.textContent = '등록 중...';

    try {
        await apiRequest('/blog/calibration/save', 'POST', {
            analysis: a,
            selected_items: selected,
            calibration_prompt: customPrompt,
            meta: meta
        });
        btn.textContent = '등록 완료';
        loadQcHistory?.();
        loadMyCalibrations?.();

        // 저장 완료 영역: 안내 + 바로 글 쓰기 버튼
        const saveResult = document.getElementById(`${containerId}-save-result`);
        if (saveResult) {
            const styleId = meta.style_template_id || '';
            saveResult.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
                    <span>보정 등록 완료 — 다음 생성부터 반영됩니다.</span>
                    <button class="btn-primary" style="padding:8px 18px;font-size:13px;border-radius:980px;white-space:nowrap"
                        onclick="goToWriteWithStyle('${styleId}')">바로 글 쓰기</button>
                </div>`;
            saveResult.style.display = 'block';
        }
    } catch (e) {
        alert('저장 실패: ' + e.message);
        btn.disabled = false;
        btn.textContent = '선택한 항목 보정 등록';
    }
}

// 분석 결과를 번호 체크리스트로 렌더링
function renderCalibrationChecklist(a, containerId, meta) {
    const items = [];
    let n = 1;
    (a.do_more     || []).forEach(s => items.push({ n: n++, category: '더 활용',  text: s }));
    (a.do_less     || []).forEach(s => items.push({ n: n++, category: '줄일 것',  text: s }));
    if (a.tone_shift)    items.push({ n: n++, category: '톤 변화',  text: a.tone_shift });
    if (a.structure_diff)items.push({ n: n++, category: '구조',     text: a.structure_diff });
    if (a.length_diff)   items.push({ n: n++, category: '분량',     text: a.length_diff });
    (a.key_phrases || []).forEach(s => items.push({ n: n++, category: '특징 표현', text: s }));

    const score = a.similarity_score ?? '?';
    const scoreColor = score >= 80 ? 'var(--accent-success)' : score >= 60 ? 'var(--accent-warning)' : 'var(--accent-danger)';

    const CATEGORY_COLORS = {
        '더 활용':  '#0071E3',
        '줄일 것':  '#FF3B30',
        '톤 변화':  '#888',
        '구조':     '#888',
        '분량':     '#888',
        '특징 표현':'#555',
    };

    const rows = items.map(item => `
        <label class="cal-item-row">
            <input type="checkbox" class="cal-item-check" checked>
            <span class="cal-item-num">${item.n}</span>
            <span class="cal-item-badge" style="background:${CATEGORY_COLORS[item.category] || '#888'}20;color:${CATEGORY_COLORS[item.category] || '#888'}">${item.category}</span>
            <span class="cal-item-text">${escapeHtml(item.text)}</span>
        </label>`).join('');

    const container = document.getElementById(containerId);
    container.innerHTML = `
        <div class="cal-score-row">
            <div class="cal-score-num" style="color:${scoreColor}">${score}<span class="cal-score-unit">%</span></div>
            <div class="cal-score-label">현재 일치율</div>
        </div>
        <div class="cal-checklist-header">
            <span style="font-size:13px;color:#555">반영할 항목을 선택하세요</span>
            <div style="display:flex;gap:6px">
                <button class="cal-toggle-btn" onclick="toggleAllCalItems(true,'${containerId}')">전체 선택</button>
                <button class="cal-toggle-btn" onclick="toggleAllCalItems(false,'${containerId}')">전체 해제</button>
            </div>
        </div>
        <div class="cal-checklist">${rows}</div>
        <button id="${containerId}-save-btn" class="btn-primary cal-save-btn"
            onclick="saveSelectedCalibration('${containerId}')">선택한 항목 보정 등록</button>
        <div id="${containerId}-save-result" class="cal-save-done" style="display:none">보정 등록 완료 — 다음 생성부터 반영됩니다.</div>`;

    container._calAnalysis = a;
    container._calMeta     = meta;
    container._calItems    = items;
    container.classList.remove('hidden');
}

// 이전 코드와의 호환 — renderCalibrationResult 를 체크리스트로 대체
function renderCalibrationResult(a, containerId, meta) {
    renderCalibrationChecklist(a, containerId, meta || {});
}

// 최근 생성 글 불러오기
document.getElementById('qc-load-latest')?.addEventListener('click', async () => {
    // 1) 현재 세션 버전이 있으면 그걸 우선 사용
    const versions = window._blogVersions;
    if (versions && versions.length) {
        const activeEl = document.querySelector('.version-content.active');
        const title   = activeEl?.querySelector('[data-field="title"]')?.innerText?.trim()
                     || versions[0].title || '';
        const content = activeEl?.querySelector('[data-field="content"]')?.innerText?.trim()
                     || versions[0].content || '';
        document.getElementById('qc-ai-title').value   = title;
        document.getElementById('qc-ai-content').value = content;
        return;
    }

    // 2) 저장된 블로그 목록에서 선택
    const btn = document.getElementById('qc-load-latest');
    btn.disabled = true;
    btn.textContent = '불러오는 중...';
    try {
        const res = await fetch('/api/mypage/blogs');
        const data = await res.json();
        const items = (data.items || []).slice(0, 20);
        if (!items.length) { alert('저장된 블로그가 없습니다.'); return; }

        let existingPicker = document.getElementById('qc-blog-picker');
        if (existingPicker) existingPicker.remove();

        const picker = document.createElement('div');
        picker.id = 'qc-blog-picker';
        picker.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;z-index:9999;width:480px;max-height:60vh;overflow-y:auto;box-shadow:0 4px 24px rgba(0,0,0,0.12)';
        picker.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <strong style="font-size:15px">불러올 블로그 선택</strong>
                <button onclick="document.getElementById('qc-blog-picker').remove();document.getElementById('qc-backdrop').remove()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#666">&times;</button>
            </div>
            <div id="qc-picker-list" style="display:flex;flex-direction:column;gap:8px"></div>`;
        document.body.appendChild(picker);

        const listEl = picker.querySelector('#qc-picker-list');
        items.forEach(item => {
            const row = document.createElement('button');
            row.style.cssText = 'text-align:left;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;width:100%';
            row.innerHTML = `<div style="font-weight:700;margin-bottom:2px">${escapeHtml(item.title || '(제목 없음)')}</div><div style="color:#888;font-size:12px">${item.created_at ? item.created_at.slice(0,16).replace('T',' ') : ''}</div>`;
            row.onmouseenter = () => row.style.background = '#f5f5f7';
            row.onmouseleave = () => row.style.background = '#fff';
            row.addEventListener('click', async () => {
                document.getElementById('qc-blog-picker')?.remove();
                document.getElementById('qc-backdrop')?.remove();
                try {
                    const detailRes = await fetch(`/api/mypage/blogs/${item.id}`);
                    const detail = await detailRes.json();
                    const vs = detail.versions || [];
                    const v = vs[0] || {};
                    document.getElementById('qc-ai-title').value   = v.title || item.title || '';
                    document.getElementById('qc-ai-content').value = v.content || '';
                } catch(e) {
                    alert('블로그 상세를 불러오지 못했습니다.');
                }
            });
            listEl.appendChild(row);
        });

        const backdrop = document.createElement('div');
        backdrop.id = 'qc-backdrop';
        backdrop.style.cssText = 'position:fixed;inset:0;z-index:9998';
        backdrop.onclick = () => { picker.remove(); backdrop.remove(); };
        document.body.insertBefore(backdrop, picker);

    } catch(e) {
        alert('블로그 목록을 불러오지 못했습니다.');
    } finally {
        btn.disabled = false;
        btn.textContent = '최근 생성 글 불러오기';
    }
});

// 빠른 비교 스타일 셀렉트 채우기
function populateQcStyleSelect() {
    const sel = document.getElementById('qc-style-select');
    if (!sel) return;
    const currentStyleId = document.getElementById('style-template-id')?.value || '';
    // style-template-grid의 카드에서 추출
    const cards = document.querySelectorAll('.style-template-card');
    if (cards.length) {
        sel.innerHTML = '<option value="">스타일 선택 (선택사항)</option>'
            + Array.from(cards).map(c => {
                const id = c.dataset.templateId;
                const name = c.querySelector('.style-template-name')?.textContent || id;
                return `<option value="${id}" ${id === currentStyleId ? 'selected' : ''}>${name}</option>`;
            }).join('');
    }
}

document.getElementById('qc-submit')?.addEventListener('click', async () => {
    const aiTitle   = document.getElementById('qc-ai-title').value.trim();
    const aiContent = document.getElementById('qc-ai-content').value.trim();
    const url       = document.getElementById('qc-approved-url').value.trim();
    const styleId   = document.getElementById('qc-style-select').value;

    if (!aiContent) { alert('AI 생성 글 본문을 입력해주세요.'); return; }
    if (!url || !url.startsWith('http')) { alert('실제 게시된 블로그 URL을 입력해주세요.'); return; }

    const btn = document.getElementById('qc-submit');
    setLoading(btn, true);
    document.getElementById('qc-result').classList.add('hidden');

    const dnaId = document.getElementById('blog-dna-select')?.value || '';
    try {
        const result = await apiRequest('/blog/calibrate-from-url', 'POST', {
            ai_title: aiTitle,
            ai_content: aiContent,
            approved_url: url,
            style_template_id: styleId,
            blog_dna_id: dnaId
        });
        const meta = result.meta || {
            ai_title: aiTitle,
            approved_url: url,
            style_template_id: styleId,
            blog_dna_id: dnaId
        };
        renderCalibrationChecklist(result.analysis || {}, 'qc-result', meta);
    } catch (e) {
        alert('분석 실패: ' + e.message);
    } finally {
        setLoading(btn, false);
    }
});

async function loadQcHistory() {
    try {
        const data = await apiRequest('/blog/calibrations');
        const cals = (data.calibrations || []).slice(0, 10);
        const el = document.getElementById('qc-history');
        if (!el) return;
        if (!cals.length) {
            el.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem">아직 보정 기록이 없습니다.</p>';
            return;
        }
        el.innerHTML = `<table class="list-table" style="font-size:0.83rem">
            <thead><tr><th>날짜</th><th>스타일</th><th>일치율</th><th>보정 요약</th><th></th></tr></thead>
            <tbody>${cals.map(c => {
                const score = c.similarity_score ?? '?';
                const sc = score >= 80 ? 'var(--accent-success)' : score >= 60 ? 'var(--accent-warning)' : 'var(--accent-danger)';
                const date = (c.created_at || '').slice(0, 16).replace('T', ' ');
                return `<tr>
                    <td style="color:var(--text-muted);white-space:nowrap">${date}</td>
                    <td>${c.style_template_id || '—'}</td>
                    <td style="font-weight:700;color:${sc};text-align:center">${score}%</td>
                    <td style="color:var(--text-muted);max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        title="${escapeHtml(c.tone_shift || c.calibration_prompt || '')}">${escapeHtml(c.tone_shift || c.calibration_prompt || '—')}</td>
                    <td style="white-space:nowrap">
                        <button onclick="deleteQcCal('${c.calibration_id}')"
                            style="background:none;border:none;cursor:pointer;color:var(--accent-danger);font-size:13px;padding:2px 6px"
                            title="삭제">&#10005;</button>
                    </td>
                </tr>`;
            }).join('')}</tbody>
        </table>`;
    } catch (e) { console.error(e); }
}

async function deleteQcCal(calId) {
    if (!confirm('이 보정 기록을 삭제하시겠습니까?')) return;
    try {
        await apiRequest(`/blog/calibration/${calId}`, 'DELETE');
        loadQcHistory();
        loadMyCalibrations?.();
    } catch (e) {
        alert('삭제 실패: ' + e.message);
    }
}

document.getElementById('qc-refresh-history')?.addEventListener('click', loadQcHistory);

// ── 흐름 버튼 핸들러 ──────────────────────────────────────────

// 수집 패널: "DNA 분석하기" 버튼
document.getElementById('btn-go-dna-from-collect')?.addEventListener('click', () => {
    const banner = document.getElementById('collect-next-step');
    const blogId = banner?.dataset.blogId;
    navigateTo('s1-blog-status');
    // 방금 수집한 블로그 자동 선택
    if (blogId) {
        setTimeout(() => {
            const sel = document.getElementById('status-collection-select');
            if (sel) sel.value = blogId;
        }, 200);
    }
});

// DNA 분석 패널: "글 작성하기" 버튼
document.getElementById('btn-go-write-from-dna')?.addEventListener('click', () => {
    navigateTo('s2-blog-write');
});

// 글 작성 패널: "블로그 수집 → DNA 분석" 링크
document.getElementById('btn-go-collect-from-write')?.addEventListener('click', () => {
    navigateTo('s1-blog-collect');
});

// 수집 이력 테이블: DNA 분석 바로가기
function goToDnaAnalysis(blogId) {
    navigateTo('s1-blog-status');
    setTimeout(() => {
        const sel = document.getElementById('status-collection-select');
        if (sel) sel.value = blogId;
    }, 200);
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadStyleTemplates();
    loadCollections();
});
