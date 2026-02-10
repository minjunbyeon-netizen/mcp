// API Base URL
const API_BASE = '/api';

// ============================================================
// Step & Sub-tab Navigation
// ============================================================

const stepBtns = document.querySelectorAll('.step-btn');
const stepPanels = document.querySelectorAll('.step-panel');

// Step switching
stepBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const stepId = btn.dataset.step;

        stepBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        stepPanels.forEach(panel => {
            panel.classList.remove('active');
            if (panel.id === stepId) {
                panel.classList.add('active');
            }
        });
    });
});

// Sub-tab switching
document.querySelectorAll('.sub-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const subtabId = btn.dataset.subtab;
        const parentNav = btn.closest('.sub-tab-nav');
        const parentPanel = btn.closest('.step-panel');

        // Update buttons within the same nav
        parentNav.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update panels within the same step
        parentPanel.querySelectorAll('.sub-tab-panel').forEach(p => {
            p.classList.remove('active');
            if (p.id === subtabId) {
                p.classList.add('active');
            }
        });
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

        ['status-collection-select', 'biz-collection-select'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = defaultOpt + optionsHTML;
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
                <div style="background: rgba(248, 81, 73, 0.1); border: 1px solid var(--accent-danger); padding: 16px; border-radius: 8px;">
                    <h5 style="color: var(--accent-danger); margin-bottom: 8px;">금지 표현</h5>
                    <ul style="font-size: 0.9rem;">${(result.red_flags || []).map(r => `<li>${r}</li>`).join('')}</ul>
                </div>
                <div style="background: rgba(63, 185, 80, 0.1); border: 1px solid var(--accent-success); padding: 16px; border-radius: 8px;">
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

        const qualityScore = result.content_quality?.score || 0;
        const qualityColor = qualityScore >= 7 ? 'var(--accent-success)' : qualityScore >= 4 ? 'var(--accent-warning)' : 'var(--accent-danger)';

        const html = `
            <h3>블로그 상태 분석 리포트</h3>
            <p style="color: var(--text-muted); margin-bottom: 16px;">${result.blog_id} | 분석 글 수: ${result.post_count}개</p>
            
            <div style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <h4 style="margin-bottom: 8px;">블로그 개요</h4>
                <p>${result.blog_overview}</p>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">글쓰기 톤</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.writing_tone}</div>
                </div>
                <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px;">
                    <div style="color: var(--text-muted); font-size: 0.85rem;">게시 패턴</div>
                    <div style="font-weight: 500; margin-top: 4px;">${result.posting_pattern}</div>
                </div>
            </div>

            <div style="margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <h4>콘텐츠 품질</h4>
                    <span style="font-size: 1.2rem; font-weight: 700; color: ${qualityColor};">${qualityScore}/10</span>
                </div>
                <p style="font-size: 0.9rem;">${result.content_quality?.assessment || ''}</p>
            </div>

            <h4>주요 주제</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 16px;">
                ${(result.main_topics || []).map(t => `<span style="background: var(--accent-blue); color: white; padding: 4px 12px; border-radius: 16px; font-size: 0.85rem;">${t}</span>`).join('')}
            </div>

            <h4>키워드 전략</h4>
            <p style="font-size: 0.9rem; margin-bottom: 16px;">${result.keyword_strategy}</p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
                <div style="background: rgba(63, 185, 80, 0.1); border: 1px solid var(--accent-success); padding: 16px; border-radius: 8px;">
                    <h5 style="color: var(--accent-success); margin-bottom: 8px;">강점</h5>
                    <ul style="font-size: 0.9rem;">${(result.strengths || []).map(s => `<li>${s}</li>`).join('')}</ul>
                </div>
                <div style="background: rgba(248, 81, 73, 0.1); border: 1px solid var(--accent-danger); padding: 16px; border-radius: 8px;">
                    <h5 style="color: var(--accent-danger); margin-bottom: 8px;">약점/개선점</h5>
                    <ul style="font-size: 0.9rem;">${(result.weaknesses || []).map(w => `<li>${w}</li>`).join('')}</ul>
                </div>
            </div>

            <h4 style="margin-top: 20px;">추천 전략</h4>
            <ol style="font-size: 0.9rem;">${(result.recommendations || []).map(r => `<li>${r}</li>`).join('')}</ol>
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
            
            <div style="background: linear-gradient(135deg, rgba(102,126,234,0.15), rgba(118,75,162,0.15)); padding: 20px; border-radius: 12px; margin: 16px 0;">
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

            <div style="background: rgba(248, 81, 73, 0.1); border: 1px solid var(--accent-danger); padding: 16px; border-radius: 8px; margin-top: 16px;">
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

    if (hasFile) {
        formData.append('file', pressFileInput.files[0]);
    } else {
        formData.append('press_release', pressReleaseText);
    }

    setLoading(submitBtn, true);

    try {
        const result = await apiRequest('/blog/generate', 'POST', formData, true);

        const html = `
            <h3>블로그 글 생성 완료</h3>
            <div class="blog-preview">
                <h1>${result.title}</h1>
                <div class="content">${result.content.replace(/\n/g, '<br>')}</div>
                <div class="tags">
                    ${result.tags.map(tag => `<span class="tag">#${tag}</span>`).join('')}
                </div>
            </div>
            <div style="margin-top: 16px; color: var(--text-secondary);">
                <p><strong>저장 위치:</strong></p>
                <code>${result.md_path}</code><br>
                <code>${result.docx_path}</code>
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

// ============================================================
// Initialize
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadPersonas();
    loadCollections();
});
