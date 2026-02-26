// API Base URL
const API_BASE = '/api';

// ============================================================
// Sidebar Navigation
// ============================================================

const navItems = document.querySelectorAll('.nav-item');
const contentPanels = document.querySelectorAll('.content-panel');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const panelId = item.dataset.panel;

        navItems.forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        contentPanels.forEach(panel => {
            panel.classList.remove('active');
            if (panel.id === panelId) {
                panel.classList.add('active');
            }
        });

        // 마이페이지 패널 진입시 데이터 로드
        if (panelId === 'my-personas') loadMyPersonas();
        if (panelId === 'my-blogs') loadMyBlogs();
        if (panelId === 'my-dna') loadMyDna();
        if (panelId === 'my-business') loadMyBusiness();
        // 블로그 작성 패널 진입시 최근 작성 글 로드
        if (panelId === 's2-blog-write') loadRecentBlogs();
    });
});

// ============================================================
// Authentication Status Check
// ============================================================

async function checkAuthStatus() {
    const loginGate = document.getElementById('login-gate');
    const appContent = document.getElementById('app-content');
    const userSection = document.getElementById('user-section');

    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();

        if (!data.sso_enabled) {
            if (loginGate) loginGate.classList.add('hidden');
            if (appContent) appContent.classList.remove('hidden');
        } else if (data.logged_in) {
            if (loginGate) loginGate.classList.add('hidden');
            if (appContent) appContent.classList.remove('hidden');
            if (userSection) userSection.classList.remove('hidden');

            const userAvatar = document.getElementById('user-avatar');
            const userName = document.getElementById('user-name');

            if (userAvatar && data.user.picture) {
                userAvatar.src = data.user.picture;
            }
            if (userName) {
                userName.textContent = data.user.name || data.user.email;
            }
        } else {
            if (loginGate) loginGate.classList.remove('hidden');
            if (appContent) appContent.classList.add('hidden');
        }

        console.log('Auth status:', data);
    } catch (error) {
        console.error('Auth check failed:', error);
        if (loginGate) loginGate.classList.remove('hidden');
        if (appContent) appContent.classList.add('hidden');
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

    const response = await fetch(`${API_BASE}${endpoint}`, options);

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'API 요청 실패');
    }

    return response.json();
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
        if (files.length > 0) handlePressFileSelect(files[0]);
    });

    pressFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handlePressFileSelect(e.target.files[0]);
    });

    pressFileRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        clearPressFile();
    });
}

function handlePressFileSelect(file) {
    const validExtensions = ['.txt', '.pdf', '.hwp'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
        alert('지원되지 않는 파일 형식입니다. TXT, PDF 또는 HWP 파일을 선택해주세요.');
        return;
    }

    pressFileUploadArea.querySelector('.file-upload-content').classList.add('hidden');
    pressFileSelected.classList.remove('hidden');
    pressFileName.textContent = file.name;
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
// Load Personas for Dropdowns
// ============================================================

async function loadPersonas() {
    try {
        const data = await apiRequest('/persona/list');
        const personas = data.personas || [];

        const optionsHTML = personas.map(p =>
            `<option value="${p.client_id}">${p.client_name} (${p.organization}) - 격식도: ${p.formality}/10</option>`
        ).join('');

        const defaultOpt = '<option value="">페르소나를 선택하세요</option>';

        // Populate all persona select elements
        ['persona-select', 'match-persona-select', 'biz-persona-select'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = defaultOpt + optionsHTML;
        });

        console.log(`${personas.length}개 페르소나 로드됨`);
    } catch (error) {
        console.error('페르소나 로드 실패:', error);
    }
}

// ============================================================
// Load Blog Collections for Dropdowns
// ============================================================

async function loadCollections() {
    try {
        const data = await apiRequest('/blog/collections');
        const collections = data.collections || [];

        // Populate select dropdowns
        const optionsHTML = collections.map(c =>
            `<option value="${c.folder}">${c.blog_id} (${c.post_count}개, ${(c.total_chars / 1000).toFixed(1)}K자)</option>`
        ).join('');

        const defaultOpt = '<option value="">컬렉션을 선택하세요</option>';

        ['status-collection-select', 'biz-collection-select', 'blog-dna-select'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const defOpt = id === 'blog-dna-select'
                    ? '<option value="">DNA 미적용</option>'
                    : defaultOpt;
                el.innerHTML = defOpt + optionsHTML;
            }
        });

        // Populate collection list in 1-2 tab
        const listEl = document.getElementById('blog-collections-list');
        if (listEl) {
            if (collections.length === 0) {
                listEl.innerHTML = '<p class="text-muted">수집된 블로그가 없습니다.</p>';
            } else {
                listEl.innerHTML = collections.map(c => `
                    <div class="collection-item">
                        <div class="collection-info">
                            <span class="collection-name">${c.blog_id}</span>
                            <span class="collection-meta">${c.post_count}개 글 | ${(c.total_chars / 1000).toFixed(1)}K자 | ${c.collected_at || c.folder}</span>
                        </div>
                    </div>
                `).join('');
            }
        }

        console.log(`${collections.length}개 컬렉션 로드됨`);
    } catch (error) {
        console.error('컬렉션 로드 실패:', error);
        const listEl = document.getElementById('blog-collections-list');
        if (listEl) listEl.innerHTML = '<p class="text-muted">컬렉션 로드 실패</p>';
    }
}

// ============================================================
// 1-1: Persona Extractor Form
// ============================================================

document.getElementById('persona-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('persona-result');

    if (!personaFileInput.files.length) {
        showError(resultBox, '파일을 선택해주세요.');
        return;
    }

    const formData = new FormData();
    formData.append('file', personaFileInput.files[0]);
    formData.append('client_name', document.getElementById('client-name').value);
    formData.append('organization', document.getElementById('organization').value);
    formData.append('category', document.getElementById('category').value);

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/persona/extract', 'POST', formData, true);

        const html = `
            <h3>페르소나 심층 분석 완료</h3>
            
            <h4 style="margin-top: 16px; margin-bottom: 12px;">성격 지표</h4>
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">격식도</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.formality_score * 10}%"></div></div>
                    <div class="score-item-value">${result.formality_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">완벽주의</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.perfectionism_score * 10}%"></div></div>
                    <div class="score-item-value">${result.perfectionism_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">디테일 중시</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.detail_orientation_score * 10}%"></div></div>
                    <div class="score-item-value">${result.detail_orientation_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">긴급성 민감도</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.urgency_sensitivity_score * 10}%"></div></div>
                    <div class="score-item-value">${result.urgency_sensitivity_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">유연성</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.flexibility_score * 10}%"></div></div>
                    <div class="score-item-value">${result.flexibility_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">직접성</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.directness_score * 10}%"></div></div>
                    <div class="score-item-value">${result.directness_score}/10</div>
                </div>
            </div>
            
            <h4 style="margin-top: 24px; margin-bottom: 12px;">커뮤니케이션 스타일</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">의사결정 유형</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.decision_making_type || '숙고형'}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">감정 표현</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.emotional_expression || '중립'}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">문장 길이</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.sentence_length || 'medium'}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">어휘 스타일</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.vocabulary_style || '혼용'}</div>
                </div>
            </div>
            
            <h4 style="margin-top: 24px;">페르소나 유형</h4>
            <p style="color: var(--accent-primary); font-size: 1.1rem;">${result.persona_type}</p>
            
            <div style="margin-top: 16px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
                <div style="color: var(--text-muted); font-size: 0.85rem;">콘텐츠 제작 난이도: ${result.content_difficulty || 5}/10</div>
                <div style="margin-top: 8px; color: var(--accent-warning);">${result.primary_caution || ''}</div>
            </div>
            
            <h4 style="margin-top: 20px;">핵심 특성</h4>
            <ul>${(result.key_characteristics || []).map(c => `<li>${c}</li>`).join('')}</ul>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px;">
                <div style="background: rgba(198, 40, 40, 0.06); border: 1px solid var(--accent-danger); padding: 16px; border-radius: 8px;">
                    <h5 style="color: var(--accent-danger); margin-bottom: 8px;">금지 표현</h5>
                    <ul style="font-size: 0.9rem;">${(result.red_flags || []).map(r => `<li>${r}</li>`).join('')}</ul>
                </div>
                <div style="background: rgba(46, 125, 50, 0.06); border: 1px solid var(--accent-success); padding: 16px; border-radius: 8px;">
                    <h5 style="color: var(--accent-success); margin-bottom: 8px;">권장 표현</h5>
                    <ul style="font-size: 0.9rem;">${(result.green_flags || []).map(g => `<li>${g}</li>`).join('')}</ul>
                </div>
            </div>
            
            <h4 style="margin-top: 20px;">저장 위치</h4>
            <code>${result.save_path}</code>
        `;

        showResult(resultBox, html);
        loadPersonas();

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

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

    const folder = document.getElementById('status-collection-select').value;
    if (!folder) {
        showError(resultBox, '분석할 컬렉션을 선택해주세요.');
        return;
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/blog/analyze-status', 'POST', { folder });

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
            return `<div style="background: var(--bg-tertiary); padding: 16px; border-radius: 10px; margin-bottom: 12px;">
                <h4 style="color: var(--accent-primary); margin-bottom: 10px; font-size: 1rem;">${cat.title || ''}</h4>
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

        const html = `
            <h3>블로그 글쓰기 DNA 분석 리포트</h3>
            <p style="color: var(--text-muted); margin-bottom: 20px;">${result.blog_id} | 분석 글 수: ${result.post_count}개 | 10가지 카테고리</p>
            ${categories.map((cat, i) => renderCategory(cat)).join('')}
        `;

        showResult(resultBox, html);

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

// ============================================================
// 1-4: Business Personality Analysis Form
// ============================================================

document.getElementById('business-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('business-result');

    const clientId = document.getElementById('biz-persona-select').value;
    const folder = document.getElementById('biz-collection-select').value;

    if (!clientId || !folder) {
        showError(resultBox, '페르소나와 블로그 컬렉션을 모두 선택해주세요.');
        return;
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/persona/business-analysis', 'POST', {
            client_id: clientId,
            folder: folder
        });

        const bp = result.business_personality || {};
        const cs = result.communication_style || {};
        const cp = result.content_preferences || {};
        const wa = result.work_approach || {};

        const html = `
            <h3>업무적 성격 분석 리포트</h3>
            
            <div style="background: rgba(0,0,0,0.03); border: 1px solid var(--border-color); padding: 20px; border-radius: 12px; margin: 16px 0;">
                <div style="font-size: 1.3rem; font-weight: 700; color: var(--accent-primary);">${bp.type || ''}</div>
                <p style="margin-top: 8px; line-height: 1.6;">${bp.description || ''}</p>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px;">
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">커뮤니케이션 방식</div>
                    <div style="font-weight: 500; margin-top: 4px;">${cs.preferred || ''}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">응답 속도</div>
                    <div style="font-weight: 500; margin-top: 4px;">${cs.response_speed || ''}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">디테일 수준</div>
                    <div style="font-weight: 500; margin-top: 4px;">${cs.detail_level || ''}</div>
                </div>
            </div>

            <h4>콘텐츠 선호도</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 8px 0 20px;">
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">선호 톤</div>
                    <div style="font-weight: 500; margin-top: 4px;">${cp.tone || ''}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">콘텐츠 스타일</div>
                    <div style="font-weight: 500; margin-top: 4px;">${cp.style || ''}</div>
                </div>
            </div>

            <h4>업무 접근 방식</h4>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 20px;">
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">의사결정</div>
                    <div style="font-weight: 500; margin-top: 4px;">${wa.decision_style || ''}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">피드백 패턴</div>
                    <div style="font-weight: 500; margin-top: 4px;">${wa.feedback_pattern || ''}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">우선 관심사</div>
                    <div style="font-weight: 500; margin-top: 4px;">${wa.priority_focus || ''}</div>
                </div>
            </div>

            <h4>에이전시 대응 전략</h4>
            <ol style="font-size: 0.9rem;">${(result.agency_recommendations || []).map(r => `<li style="margin-bottom: 6px;">${r}</li>`).join('')}</ol>

            <div style="background: rgba(198, 40, 40, 0.06); border: 1px solid var(--accent-danger); padding: 16px; border-radius: 8px; margin-top: 16px;">
                <h5 style="color: var(--accent-danger); margin-bottom: 8px;">주의 사항</h5>
                <ul style="font-size: 0.9rem;">${(result.risk_factors || []).map(r => `<li>${r}</li>`).join('')}</ul>
            </div>

            <div style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; margin-top: 16px;">
                <h5 style="margin-bottom: 8px;">핵심 요약</h5>
                <p style="line-height: 1.6;">${result.summary || ''}</p>
            </div>
        `;

        showResult(resultBox, html);

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

// ============================================================
// 2-1: Blog Generator Form (File Upload)
// ============================================================

document.getElementById('blog-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('blog-result');

    const personaId = document.getElementById('persona-select').value;
    if (!personaId) {
        showError(resultBox, '페르소나를 선택해주세요.');
        return;
    }

    const pressReleaseText = document.getElementById('press-release').value;
    const hasFile = pressFileInput.files.length > 0;

    if (!hasFile && !pressReleaseText.trim()) {
        showError(resultBox, '보도자료 파일을 업로드하거나 내용을 입력해주세요.');
        return;
    }

    const formData = new FormData();
    formData.append('client_id', personaId);
    formData.append('keywords', document.getElementById('keywords').value);
    formData.append('target_audience', document.getElementById('target-audience').value);
    formData.append('content_angle', document.getElementById('content-angle').value);

    // 블로그 DNA 선택 (선택사항)
    const blogDnaFolder = document.getElementById('blog-dna-select')?.value;
    if (blogDnaFolder) {
        formData.append('blog_dna_folder', blogDnaFolder);
    }

    if (hasFile) {
        formData.append('file', pressFileInput.files[0]);
    } else {
        formData.append('press_release', pressReleaseText);
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

        // 각 버전 컨텐츠
        const contentsHTML = versions.map((v, i) => {
            const paragraphs = v.content.split('\n').filter(p => p.trim() !== '');
            const contentHTML = paragraphs.map(p => `<p>${p}</p>`).join('');

            return `
                <div class="version-content ${i === 0 ? 'active' : ''}" data-version-idx="${i}">
                    <div class="blog-preview">
                        <h1>${v.title}</h1>
                        <div class="content">${contentHTML}</div>
                        <div class="tags">
                            ${(v.tags || []).map(tag => `<span class="tag">#${tag}</span>`).join('')}
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

        const html = `
            <h3>블로그 3가지 버전 생성 완료</h3>
            <p style="color: var(--text-muted); margin-bottom: 16px;">동일한 내용을 3가지 톤으로 작성했습니다. 탭을 클릭하여 비교해보세요.</p>
            <div class="version-tabs">${tabsHTML}</div>
            <div class="version-panels">${contentsHTML}</div>
            ${imageGenHTML}
            <div style="margin-top: 16px; color: var(--text-secondary);">
                <p><strong>저장 위치:</strong> <code>${result.output_dir}</code></p>
            </div>
        `;

        showResult(resultBox, html);

        // 탭 클릭 이벤트
        resultBox.querySelectorAll('.version-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const idx = tab.dataset.versionIdx;
                resultBox.querySelectorAll('.version-tab').forEach(t => t.classList.remove('active'));
                resultBox.querySelectorAll('.version-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                resultBox.querySelector(`.version-content[data-version-idx="${idx}"]`).classList.add('active');
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
// 2-2: Match Rate Tester Form
// ============================================================

document.getElementById('match-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('match-result');

    const data = {
        client_id: document.getElementById('match-persona-select').value,
        content: document.getElementById('test-content').value
    };

    if (!data.client_id) {
        showError(resultBox, '페르소나를 선택해주세요.');
        return;
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/match-test', 'POST', data);

        const html = `
            <h3>일치율 분석 결과</h3>
            <div class="score-display">
                <div class="score-circle" style="--score: ${result.overall_score}">
                    <span class="score-value">${result.overall_score}%</span>
                </div>
                <div class="score-label">전체 일치율</div>
            </div>
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">톤 & 격식</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.tone_match}%"></div></div>
                    <div class="score-item-value">${result.tone_match}%</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">문장 스타일</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.style_match}%"></div></div>
                    <div class="score-item-value">${result.style_match}%</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">어휘 선택</div>
                    <div class="score-item-bar"><div class="score-item-fill" style="width: ${result.vocabulary_match}%"></div></div>
                    <div class="score-item-value">${result.vocabulary_match}%</div>
                </div>
            </div>
            <h4 style="margin-top: 24px;">개선 제안</h4>
            <ul>${result.suggestions.map(s => `<li>${s}</li>`).join('')}</ul>
        `;

        showResult(resultBox, html);

    } catch (error) {
        showError(resultBox, error.message);
    } finally {
        setLoading(submitBtn, false);
    }
});

// ============================================================
// Refresh Buttons
// ============================================================

document.getElementById('refresh-personas')?.addEventListener('click', () => loadPersonas());
document.getElementById('refresh-biz-personas')?.addEventListener('click', () => loadPersonas());
document.getElementById('refresh-collections-status')?.addEventListener('click', () => loadCollections());
document.getElementById('refresh-biz-collections')?.addEventListener('click', () => loadCollections());
document.getElementById('refresh-blog-dna')?.addEventListener('click', () => loadCollections());

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

// --- 페르소나 관리 ---
async function loadMyPersonas() {
    try {
        const res = await fetch(`${API_BASE}/mypage/personas`);
        const data = await res.json();
        const tbody = document.querySelector('#my-personas-table tbody');
        const empty = document.getElementById('my-personas-empty');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            document.getElementById('my-personas-table').style.display = 'none';
            empty.style.display = 'block';
            return;
        }
        document.getElementById('my-personas-table').style.display = 'table';
        empty.style.display = 'none';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.client_name || item.id}</td>
                <td>${item.organization || '-'}</td>
                <td>${formatDate(item.created_at)}</td>
                <td class="td-actions">
                    <button class="btn-view" onclick="viewDetail('personas','${item.id}','페르소나 상세')">상세</button>
                    <button class="btn-delete" onclick="deleteItem('personas','${item.id}',this)">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('페르소나 목록 로드 실패:', e); }
}

// --- 블로그 글 관리 ---
async function loadMyBlogs() {
    try {
        const res = await fetch(`${API_BASE}/mypage/blogs`);
        const data = await res.json();
        const tbody = document.querySelector('#my-blogs-table tbody');
        const empty = document.getElementById('my-blogs-empty');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            document.getElementById('my-blogs-table').style.display = 'none';
            empty.style.display = 'block';
            return;
        }
        document.getElementById('my-blogs-table').style.display = 'table';
        empty.style.display = 'none';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.title || '(제목없음)'}</td>
                <td>${item.client_id || '-'}</td>
                <td>${item.version_count || 0}개</td>
                <td>${formatDate(item.created_at)}</td>
                <td class="td-actions">
                    <button class="btn-view" onclick="viewDetail('blogs','${item.id}','블로그 상세')">상세</button>
                    <button class="btn-view" onclick="exportToGoogleDocs('blogs','${item.id}')" style="background:rgba(52,168,83,0.15);color:#34a853;">Docs</button>
                    <button class="btn-delete" onclick="deleteItem('blogs','${item.id}',this)">삭제</button>
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
        const tbody = document.querySelector('#my-dna-table tbody');
        const empty = document.getElementById('my-dna-empty');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            document.getElementById('my-dna-table').style.display = 'none';
            empty.style.display = 'block';
            return;
        }
        document.getElementById('my-dna-table').style.display = 'table';
        empty.style.display = 'none';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.blog_id || '-'}</td>
                <td>${item.folder || '-'}</td>
                <td>${item.post_count || 0}개</td>
                <td>${formatDate(item.created_at)}</td>
                <td class="td-actions">
                    <button class="btn-view" onclick="viewDetail('dna','${item.id}','DNA 분석 상세')">상세</button>
                    <button class="btn-delete" onclick="deleteItem('dna','${item.id}',this)">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('DNA 목록 로드 실패:', e); }
}

// --- 업무적 성격 관리 ---
async function loadMyBusiness() {
    try {
        const res = await fetch(`${API_BASE}/mypage/business`);
        const data = await res.json();
        const tbody = document.querySelector('#my-business-table tbody');
        const empty = document.getElementById('my-business-empty');
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            document.getElementById('my-business-table').style.display = 'none';
            empty.style.display = 'block';
            return;
        }
        document.getElementById('my-business-table').style.display = 'table';
        empty.style.display = 'none';
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.type || '-'}</td>
                <td>${item.client_id || '-'}</td>
                <td>${item.blog_folder || '-'}</td>
                <td>${formatDate(item.created_at)}</td>
                <td class="td-actions">
                    <button class="btn-view" onclick="viewDetail('business','${item.id}','업무적 성격 상세')">상세</button>
                    <button class="btn-delete" onclick="deleteItem('business','${item.id}',this)">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('업무적 성격 목록 로드 실패:', e); }
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
            if (type === 'personas') loadMyPersonas();
            else if (type === 'blogs') loadMyBlogs();
            else if (type === 'dna') loadMyDna();
            else if (type === 'business') loadMyBusiness();
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
        const tbody = document.querySelector('#recent-blogs-table tbody');
        const empty = document.getElementById('recent-blogs-empty');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!data.items || data.items.length === 0) {
            document.getElementById('recent-blogs-table').style.display = 'none';
            empty.style.display = 'block';
            return;
        }
        document.getElementById('recent-blogs-table').style.display = 'table';
        empty.style.display = 'none';
        // 최근 10건만 표시
        const items = data.items.slice(0, 10);
        items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.title || '(제목없음)'}</td>
                <td>${item.client_id || '-'}</td>
                <td>${item.version_count || 0}개</td>
                <td>${formatDate(item.created_at)}</td>
                <td class="td-actions">
                    <button class="btn-view" onclick="viewDetail('blogs','${item.id}','블로그 상세')">상세</button>
                    <button class="btn-view" onclick="exportToGoogleDocs('blogs','${item.id}')" style="background:rgba(52,168,83,0.15);color:#34a853;">Docs</button>
                    <button class="btn-delete" onclick="deleteItem('blogs','${item.id}',this); setTimeout(loadRecentBlogs,300);">삭제</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error('최근 블로그 로드 실패:', e); }
}


// ============================================================
// Initialize
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadPersonas();
    loadCollections();
});
