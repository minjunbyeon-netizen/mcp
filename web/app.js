// API Base URL
const API_BASE = 'http://localhost:5000/api';

// DOM Elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

// ============================================================
// Authentication Status Check
// ============================================================

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();

        const loginSection = document.getElementById('login-section');
        const userSection = document.getElementById('user-section');
        const noSsoSection = document.getElementById('no-sso-section');

        if (!data.sso_enabled) {
            // SSO 미설정 - 모든 기능 사용 가능
            if (loginSection) loginSection.classList.add('hidden');
            if (userSection) userSection.classList.add('hidden');
            if (noSsoSection) noSsoSection.classList.remove('hidden');
        } else if (data.logged_in) {
            // 로그인됨
            if (loginSection) loginSection.classList.add('hidden');
            if (userSection) userSection.classList.remove('hidden');
            if (noSsoSection) noSsoSection.classList.add('hidden');

            // 사용자 정보 표시
            const userAvatar = document.getElementById('user-avatar');
            const userName = document.getElementById('user-name');

            if (userAvatar && data.user.picture) {
                userAvatar.src = data.user.picture;
            }
            if (userName) {
                userName.textContent = data.user.name || data.user.email;
            }
        } else {
            // 로그인 필요
            if (loginSection) loginSection.classList.remove('hidden');
            if (userSection) userSection.classList.add('hidden');
            if (noSsoSection) noSsoSection.classList.add('hidden');
        }

        console.log('Auth status:', data);
    } catch (error) {
        console.error('Auth check failed:', error);
    }
}

// Tab Switching
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;

        // Update buttons
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update panels
        tabPanels.forEach(panel => {
            panel.classList.remove('active');
            if (panel.id === tabId) {
                panel.classList.add('active');
            }
        });
    });
});

// Utility Functions
async function apiRequest(endpoint, method = 'GET', data = null, isFormData = false) {
    const options = {
        method,
    };

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
    // Click to select
    personaFileUploadArea.addEventListener('click', () => {
        personaFileInput.click();
    });

    // Drag and drop
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
        if (files.length > 0) {
            handlePersonaFileSelect(files[0]);
        }
    });

    // File input change
    personaFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handlePersonaFileSelect(e.target.files[0]);
        }
    });

    // Remove file
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

    // Update UI
    personaFileUploadArea.querySelector('.file-upload-content').classList.add('hidden');
    personaFileSelected.classList.remove('hidden');
    personaFileName.textContent = file.name;
    personaFileUploadArea.classList.add('has-file');

    // Auto-fill client name from filename
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
    pressFileUploadArea.addEventListener('click', () => {
        pressFileInput.click();
    });

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
        if (files.length > 0) {
            handlePressFileSelect(files[0]);
        }
    });

    pressFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handlePressFileSelect(e.target.files[0]);
        }
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

        const personaSelect = document.getElementById('persona-select');
        const matchPersonaSelect = document.getElementById('match-persona-select');

        const optionsHTML = personas.map(p =>
            `<option value="${p.client_id}">${p.client_name} (${p.organization}) - 격식도: ${p.formality}/10</option>`
        ).join('');

        if (personaSelect) {
            personaSelect.innerHTML = '<option value="">페르소나를 선택하세요</option>' + optionsHTML;
        }
        if (matchPersonaSelect) {
            matchPersonaSelect.innerHTML = '<option value="">페르소나를 선택하세요</option>' + optionsHTML;
        }

        console.log(`${personas.length}개 페르소나 로드됨`);
    } catch (error) {
        console.error('페르소나 로드 실패:', error);
    }
}

// ============================================================
// Persona Extractor Form (File Upload)
// ============================================================

document.getElementById('persona-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultBox = document.getElementById('persona-result');

    // Check if file is selected
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
            
            <!-- 성격 지표 -->
            <h4 style="margin-top: 16px; margin-bottom: 12px;">성격 지표</h4>
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">격식도</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.formality_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.formality_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">완벽주의</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.perfectionism_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.perfectionism_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">디테일 중시</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.detail_orientation_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.detail_orientation_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">긴급성 민감도</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.urgency_sensitivity_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.urgency_sensitivity_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">유연성</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.flexibility_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.flexibility_score}/10</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">직접성</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.directness_score * 10}%"></div>
                    </div>
                    <div class="score-item-value">${result.directness_score}/10</div>
                </div>
            </div>
            
            <!-- 커뮤니케이션 스타일 -->
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
            
            <!-- 페르소나 유형 -->
            <h4 style="margin-top: 24px;">페르소나 유형</h4>
            <p style="color: var(--accent-primary); font-size: 1.1rem;">${result.persona_type}</p>
            
            <!-- 콘텐츠 제작 난이도 -->
            <div style="margin-top: 16px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
                <div style="color: var(--text-muted); font-size: 0.85rem;">콘텐츠 제작 난이도: ${result.content_difficulty || 5}/10</div>
                <div style="margin-top: 8px; color: var(--accent-warning);">${result.primary_caution || ''}</div>
            </div>
            
            <!-- 핵심 특성 -->
            <h4 style="margin-top: 20px;">핵심 특성</h4>
            <ul>${(result.key_characteristics || []).map(c => `<li>${c}</li>`).join('')}</ul>
            
            <!-- 금기/권장 사항 -->
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
// Blog Generator Form (File Upload)
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
// Match Rate Tester Form
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
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.tone_match}%"></div>
                    </div>
                    <div class="score-item-value">${result.tone_match}%</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">문장 스타일</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.style_match}%"></div>
                    </div>
                    <div class="score-item-value">${result.style_match}%</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">어휘 선택</div>
                    <div class="score-item-bar">
                        <div class="score-item-fill" style="width: ${result.vocabulary_match}%"></div>
                    </div>
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
// Refresh Personas Button
// ============================================================

document.getElementById('refresh-personas')?.addEventListener('click', () => {
    loadPersonas();
});

// ============================================================
// Initialize
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadPersonas();
});
