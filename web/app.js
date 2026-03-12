/* =========================================================
   auto-blog app.js
   패널 1: 블로그 수집 | 패널 2: 블로그 글 작성 | 패널 3: 스타일 업데이트
   ========================================================= */

const API = '';

// ── 전역 상태 ──────────────────────────────────────────────
let _collectResult = null;
let _selectedDNA   = null;
let _activeTags    = [];
let _styleCurrentDNA = null;


// ── 초기화 ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initNav();
    initCollectPanel();
    initWritePanel();
    initStylePanel();
    initDBPanel();
    initModal();
});


// ═══════════════════════════════════════════════════════════
// 1. AUTH
// ═══════════════════════════════════════════════════════════
async function initAuth() {
    try {
        const res = await fetch(`${API}/api/auth/status`);
        const data = await res.json();

        // SSO 미설정(로컬 개발) 또는 로그인 완료 → 앱 바로 진입
        if (data.logged_in || !data.sso_enabled) {
            document.getElementById('login-gate').classList.add('hidden');
            document.getElementById('app-content').classList.remove('hidden');
            document.getElementById('sb-logged-out').classList.add('hidden');

            if (data.logged_in && data.user) {
                document.getElementById('sb-logged-in').classList.remove('hidden');
                const el = document.getElementById('sb-username');
                if (el) el.textContent = data.user.name || data.user.email || '';
                const av = document.getElementById('sb-avatar');
                if (av && data.user.picture) av.src = data.user.picture;
            } else {
                // SSO 미설정 → 로그인 영역 숨김
                document.getElementById('sb-logged-in').classList.add('hidden');
                document.getElementById('sb-logged-out').classList.add('hidden');
            }

            loadCollectHistory();
            loadDNAList();
        } else {
            document.getElementById('login-gate').classList.remove('hidden');
            document.getElementById('app-content').classList.add('hidden');
        }
    } catch {
        // 연결 실패 시에도 앱 진입 허용 (로컬 개발 편의)
        document.getElementById('login-gate').classList.add('hidden');
        document.getElementById('app-content').classList.remove('hidden');
        loadCollectHistory();
        loadDNAList();
    }
}


// ═══════════════════════════════════════════════════════════
// 2. NAVIGATION
// ═══════════════════════════════════════════════════════════
function initNav() {
    document.querySelectorAll('.nav-item[data-panel]').forEach(btn => {
        btn.addEventListener('click', () => {
            const panelId = btn.dataset.panel;
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
            const target = document.getElementById(`panel-${panelId}`);
            if (target) target.classList.remove('hidden');
        });
    });
}

function goToPanel(panelId) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById(`panel-${panelId}`);
    if (target) target.classList.remove('hidden');
}


// ═══════════════════════════════════════════════════════════
// 3. PANEL 1 — 블로그 수집
// ═══════════════════════════════════════════════════════════
function initCollectPanel() {
    initBlogSearch();

    const form = document.getElementById('collect-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const blogInput = document.getElementById('collect-url').value.trim();
        const count = document.getElementById('collect-count').value;
        if (!blogInput) return;

        setFormLoading(form, true);
        document.getElementById('collect-result').classList.add('hidden');
        document.getElementById('collect-dna-result').classList.add('hidden');

        try {
            const res = await fetch(`${API}/api/blog/collect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ blog_id: blogInput, count: parseInt(count) })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || '수집 실패');
            _collectResult = data;
            renderCollectResult(data);
            loadCollectHistory();
        } catch (err) {
            alert(err.message);
        } finally {
            setFormLoading(form, false);
        }
    });

    document.getElementById('btn-analyze-dna').addEventListener('click', () => {
        if (_collectResult) analyzeDNA(_collectResult.blog_id);
    });

    document.getElementById('btn-go-write').addEventListener('click', () => {
        goToPanel('write');
        loadDNAList();
    });
}

// ── 블로그 검색 자동완성 ─────────────────────────────────
function initBlogSearch() {
    const input = document.getElementById('collect-url');
    const dropdown = document.getElementById('collect-search-dropdown');
    let _timer = null;

    input.addEventListener('input', () => {
        clearTimeout(_timer);
        const q = input.value.trim();

        // URL이나 정확한 ID 형태면 검색 스킵
        if (!q || q.length < 2 || q.startsWith('http') || /^[A-Za-z0-9_]{4,}$/.test(q) && !q.includes(' ')) {
            dropdown.classList.add('hidden');
            return;
        }
        _timer = setTimeout(() => fetchBlogSearch(q), 400);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') dropdown.classList.add('hidden');
        if (e.key === 'ArrowDown') {
            const first = dropdown.querySelector('.search-item');
            if (first) first.focus();
        }
    });

    // 외부 클릭 시 닫기
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-input-wrap')) {
            dropdown.classList.add('hidden');
        }
    });
}

async function fetchBlogSearch(query) {
    const dropdown = document.getElementById('collect-search-dropdown');
    dropdown.innerHTML = `<div class="search-item-loading">검색 중...</div>`;
    dropdown.classList.remove('hidden');

    try {
        const res = await fetch(`${API}/api/blog/search-users?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        const results = data.results || [];

        if (!results.length) {
            dropdown.innerHTML = `<div class="search-item-empty">검색 결과가 없습니다</div>`;
            return;
        }

        dropdown.innerHTML = results.map(r => `
            <button class="search-item" type="button"
                    data-blog-id="${r.blog_id}"
                    onclick="selectBlogResult('${r.blog_id}')">
                <span class="search-item-id">${r.blog_id}</span>
                ${r.name ? `<span class="search-item-name">${r.name}</span>` : ''}
                <span class="search-item-url">blog.naver.com/${r.blog_id}</span>
            </button>`).join('');

        // 키보드 탐색
        dropdown.querySelectorAll('.search-item').forEach((el, i, arr) => {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowDown') arr[i + 1]?.focus();
                if (e.key === 'ArrowUp') { if (i === 0) document.getElementById('collect-url').focus(); else arr[i - 1]?.focus(); }
                if (e.key === 'Escape') document.getElementById('collect-search-dropdown').classList.add('hidden');
            });
        });
    } catch {
        dropdown.classList.add('hidden');
    }
}

function selectBlogResult(blogId) {
    document.getElementById('collect-url').value = blogId;
    document.getElementById('collect-search-dropdown').classList.add('hidden');
    document.getElementById('collect-url').focus();
}

function renderCollectResult(data) {
    document.getElementById('collect-summary').innerHTML = `
        <div class="result-card">
            <div class="result-card-row"><span class="result-label">블로그 ID</span><span class="result-value">${data.blog_id}</span></div>
            <div class="result-card-row"><span class="result-label">수집 글 수</span><span class="result-value">${data.post_count}개</span></div>
            <div class="result-card-row"><span class="result-label">총 글자 수</span><span class="result-value">${(data.total_chars || 0).toLocaleString()}자</span></div>
        </div>`;

    const posts = data.posts || [];
    document.getElementById('collect-posts-preview').innerHTML =
        posts.slice(0, 5).map(p => `
            <div class="post-preview-item">
                <span class="post-title">${p.title || '제목 없음'}</span>
                <span class="post-date">${(p.date || '').slice(0, 10)}</span>
            </div>`).join('') +
        (posts.length > 5 ? `<div class="post-preview-more">외 ${posts.length - 5}개</div>` : '');

    document.getElementById('collect-result').classList.remove('hidden');
}

async function analyzeDNA(blogId) {
    const btn = document.getElementById('btn-analyze-dna');
    btn.disabled = true;
    btn.textContent = 'DNA 분석 중...';

    try {
        const res = await fetch(`${API}/api/blog/analyze-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blog_id: blogId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '분석 실패');
        renderDNAResult(data, document.getElementById('collect-dna-content'));
        document.getElementById('collect-dna-result').classList.remove('hidden');
        loadCollectHistory();
        loadDNAList();
    } catch (err) {
        alert(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '이 블로그 DNA 분석하기';
    }
}

function renderDNAResult(dna, container) {
    const categories = [
        { key: 'c1_tone', label: '말투/톤' },
        { key: 'c2_structure', label: '구조' },
        { key: 'c3_content', label: '콘텐츠' },
        { key: 'c4_emotional', label: '감성' },
        { key: 'c5_expression', label: '표현' },
        { key: 'c6_sentence_patterns', label: '문장 패턴' },
        { key: 'c7_vocabulary', label: '어휘' },
        { key: 'c8_paragraph_composition', label: '단락 구성' },
        { key: 'c9_opening_closing', label: '도입/마무리' },
        { key: 'c10_visual_formatting', label: '시각 포맷' },
    ];

    let html = `<div class="dna-result">
        <div class="dna-result-header"><strong>${dna.blog_id || ''}</strong> DNA 분석 완료</div>
        <div class="dna-cats">`;

    categories.forEach(cat => {
        const d = dna[cat.key];
        if (!d) return;
        const items = Object.entries(d)
            .filter(([k]) => !['title','examples','opening_examples','closing_examples'].includes(k))
            .map(([, v]) => Array.isArray(v) ? v.slice(0, 2).join(', ') : String(v))
            .filter(v => v && v.length < 80)
            .slice(0, 3);
        if (!items.length) return;
        html += `<div class="dna-cat">
            <div class="dna-cat-label">${cat.label}</div>
            <div class="dna-cat-value">${items.join(' · ')}</div>
        </div>`;
    });

    html += `</div></div>`;
    container.innerHTML = html;
}

async function loadCollectHistory() {
    try {
        const res = await fetch(`${API}/api/blog/collections`);
        const data = await res.json();
        const items = data.items || data.collections || [];
        const tbody = document.getElementById('collections-tbody');
        if (!items.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">수집된 블로그가 없습니다</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr>
                <td>${item.blog_id || ''}</td>
                <td>${item.post_count || 0}개</td>
                <td>${(item.collected_at || item.updated_at || '').slice(0, 16).replace('T', ' ')}</td>
                <td>${item.has_dna ? '<span class="badge-yes">완료</span>' : `<button class="btn-link" onclick="analyzeDNA('${item.blog_id}')">분석</button>`}</td>
                <td><button class="btn-link" onclick="collectAndAnalyze('${item.blog_id}')">재수집</button></td>
            </tr>`).join('');
    } catch { /* ignore */ }
}

function collectAndAnalyze(blogId) {
    document.getElementById('collect-url').value = blogId;
    goToPanel('collect');
    document.getElementById('collect-form').requestSubmit();
}


// ═══════════════════════════════════════════════════════════
// 4. PANEL 2 — 블로그 글 작성
// ═══════════════════════════════════════════════════════════
function initWritePanel() {
    const dropArea = document.getElementById('write-drop-area');
    const fileInput = document.getElementById('write-files');

    dropArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => updateSelectedFiles(fileInput.files));
    dropArea.addEventListener('dragover', e => { e.preventDefault(); dropArea.classList.add('drag-over'); });
    dropArea.addEventListener('dragleave', () => dropArea.classList.remove('drag-over'));
    dropArea.addEventListener('drop', e => {
        e.preventDefault();
        dropArea.classList.remove('drag-over');
        updateSelectedFiles(e.dataTransfer.files);
    });

    document.getElementById('write-dna-select').addEventListener('change', onDNASelect);
    document.getElementById('write-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await generateBlog();
    });
}

function updateSelectedFiles(fileList) {
    const files = Array.from(fileList);
    const selectedEl = document.getElementById('write-files-selected');
    const innerEl = document.getElementById('write-drop-inner');
    if (!files.length) {
        selectedEl.classList.add('hidden');
        innerEl.classList.remove('hidden');
        return;
    }
    innerEl.classList.add('hidden');
    selectedEl.classList.remove('hidden');
    selectedEl.innerHTML = files.map(f => `
        <div class="selected-file">
            <span class="selected-file-name">${f.name}</span>
            <span class="selected-file-size">${formatBytes(f.size)}</span>
        </div>`).join('');
}

async function onDNASelect() {
    const dnaId = document.getElementById('write-dna-select').value;
    const tagsEl = document.getElementById('write-dna-tags');
    if (!dnaId) {
        _selectedDNA = null;
        _activeTags = [];
        tagsEl.classList.add('hidden');
        return;
    }
    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}`);
        const dna = await res.json();
        _selectedDNA = dna;
        _activeTags = dna.active_tags || [];
        renderWriteTags(dna);
    } catch {
        tagsEl.classList.add('hidden');
    }
}

function renderWriteTags(dna) {
    const tagsEl = document.getElementById('write-dna-tags');
    const allTags = extractPersonaTags(dna);
    if (!allTags.length) { tagsEl.classList.add('hidden'); return; }

    const activeIds = new Set((_activeTags || []).map(t => t.id));
    tagsEl.innerHTML = `
        <div class="tags-title">활성 스타일 태그 <span style="color:var(--text-muted);font-weight:400;font-size:0.8rem">(클릭으로 ON/OFF)</span></div>
        <div class="tags-wrap">
            ${allTags.map(t => `
                <span class="tag ${activeIds.has(t.id) ? 'tag-on' : ''}"
                      data-tag-id="${t.id}"
                      data-tag-label="${encodeURIComponent(t.label)}"
                      data-tag-cat="${t.cat}">${t.label}</span>`).join('')}
        </div>`;
    tagsEl.classList.remove('hidden');

    tagsEl.querySelectorAll('.tag').forEach(el => {
        el.addEventListener('click', () => {
            el.classList.toggle('tag-on');
            _activeTags = Array.from(tagsEl.querySelectorAll('.tag.tag-on')).map(t => ({
                id: t.dataset.tagId,
                label: decodeURIComponent(t.dataset.tagLabel),
                cat: t.dataset.tagCat
            }));
        });
    });
}

async function generateBlog() {
    const form = document.getElementById('write-form');
    const dnaId = document.getElementById('write-dna-select').value;
    const files = document.getElementById('write-files').files;
    const url = document.getElementById('write-url').value.trim();
    const text = document.getElementById('write-text').value.trim();

    if (!files.length && !url && !text) {
        alert('보도자료를 입력하거나 파일을 업로드하세요.');
        return;
    }

    setFormLoading(form, true);
    showLoadingModal();
    document.getElementById('write-preview-empty').classList.add('hidden');
    document.getElementById('write-preview-result').classList.add('hidden');

    const fd = new FormData();
    fd.append('style_template_id', 'informational');
    fd.append('blog_dna_id', dnaId);
    fd.append('target_audience', document.getElementById('write-audience').value);
    fd.append('content_angle', document.getElementById('write-angle').value);
    fd.append('keywords', document.getElementById('write-keywords').value.trim());
    fd.append('press_url', url);
    fd.append('press_release', text);
    fd.append('active_tags', JSON.stringify(_activeTags));
    Array.from(files).forEach(f => fd.append('files', f));

    try {
        const res = await fetch(`${API}/api/blog/generate`, { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '생성 실패');
        renderWriteResult(data, dnaId);
    } catch (err) {
        alert(err.message);
        document.getElementById('write-preview-empty').classList.remove('hidden');
    } finally {
        hideLoadingModal();
        setFormLoading(form, false);
    }
}

function renderWriteResult(data, dnaId) {
    const versions = data.versions || [];
    window._lastVersions = versions;
    window._lastDNAId = dnaId;

    document.getElementById('write-versions').innerHTML = versions.map((v, i) => `
        <div class="version-block">
            <div class="version-header">
                <span class="version-label">버전 ${i + 1}</span>
                ${v.title ? `<span class="version-title-text">${v.title}</span>` : ''}
                <div class="version-actions">
                    <button class="btn btn-secondary btn-sm" onclick="copyVersion(${i})">복사</button>
                    <button class="btn btn-primary btn-sm" onclick="saveVersion(${i})">저장</button>
                </div>
            </div>
            <div class="version-content">${formatBlogContent(v.content || '')}</div>
        </div>`).join('');

    document.getElementById('write-preview-result').classList.remove('hidden');
}

function formatBlogContent(text) {
    return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .split('\n').map(l => `<p>${l || '&nbsp;'}</p>`).join('');
}

function copyVersion(idx) {
    const v = (window._lastVersions || [])[idx];
    if (!v) return;
    navigator.clipboard.writeText((v.title ? v.title + '\n\n' : '') + (v.content || ''))
        .then(() => alert('복사되었습니다.'));
}

async function saveVersion(idx) {
    const v = (window._lastVersions || [])[idx];
    if (!v) return;
    try {
        const res = await fetch(`${API}/api/blog/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: v.title || '',
                content: v.content || '',
                style_template_id: 'informational',
                blog_dna_id: window._lastDNAId || '',
                version_index: idx
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '저장 실패');
        alert('저장되었습니다.');
    } catch (err) {
        alert(err.message);
    }
}

async function loadDNAList() {
    try {
        const res = await fetch(`${API}/api/mypage/dna`);
        const data = await res.json();
        const items = data.items || [];
        const sel = document.getElementById('write-dna-select');
        const current = sel.value;
        sel.innerHTML = `<option value="">DNA 미적용 (기본 스타일)</option>`;
        items.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.id;
            opt.textContent = `${item.blog_id} (${(item.created_at || '').slice(0, 10)})`;
            sel.appendChild(opt);
        });
        if (current) sel.value = current;
        renderStyleDNAList(items);
    } catch { /* ignore */ }
}


// ═══════════════════════════════════════════════════════════
// 5. PANEL 3 — 블로그 스타일 업데이트
// ═══════════════════════════════════════════════════════════
function initStylePanel() {
    document.querySelector('.nav-item[data-panel="style"]').addEventListener('click', loadDNAList);
}

function renderStyleDNAList(items) {
    const listEl = document.getElementById('style-dna-list');
    if (!items || !items.length) {
        listEl.innerHTML = `<div class="empty-hint">수집된 DNA가 없습니다.<br>먼저 블로그를 수집하고 DNA 분석을 실행하세요.</div>`;
        return;
    }
    listEl.innerHTML = items.map(item => `
        <div class="dna-card" data-dna-id="${item.id}" onclick="loadStyleDetail('${item.id}')">
            <div class="dna-card-id">${item.blog_id || ''}</div>
            <div class="dna-card-meta">${item.post_count || 0}개 분석 · ${(item.created_at || '').slice(0, 10)}</div>
        </div>`).join('');
}

async function loadStyleDetail(dnaId) {
    document.querySelectorAll('.dna-card').forEach(c => c.classList.remove('selected'));
    const card = document.querySelector(`.dna-card[data-dna-id="${dnaId}"]`);
    if (card) card.classList.add('selected');

    const detailEl = document.getElementById('style-detail');
    detailEl.innerHTML = `<div class="loading-hint">불러오는 중...</div>`;

    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}`);
        const dna = await res.json();
        _styleCurrentDNA = dna;
        renderStyleDetail(dna);
    } catch (err) {
        detailEl.innerHTML = `<div class="error-hint">로드 실패: ${err.message}</div>`;
    }
}

function renderStyleDetail(dna) {
    const detailEl = document.getElementById('style-detail');
    const allTags = extractPersonaTags(dna);
    const activeIds = new Set((dna.active_tags || []).map(t => t.id));

    const groups = {};
    allTags.forEach(t => {
        if (!groups[t.cat]) groups[t.cat] = [];
        groups[t.cat].push(t);
    });

    let html = `
        <div class="style-detail-header">
            <div class="style-detail-title">${dna.blog_id || ''}</div>
            <div class="style-detail-meta">${dna.post_count || 0}개 분석 · ${(dna.created_at || '').slice(0, 10)}</div>
        </div>
        <p class="style-detail-desc">태그를 켜면 글 생성 시 해당 스타일 특징이 강조 반영됩니다.</p>`;

    Object.entries(groups).forEach(([cat, tags]) => {
        html += `<div class="tag-group">
            <div class="tag-group-label">${cat}</div>
            <div class="tags-wrap">
                ${tags.map(t => `
                    <span class="tag ${activeIds.has(t.id) ? 'tag-on' : ''}"
                          data-tag-id="${t.id}"
                          data-tag-label="${encodeURIComponent(t.label)}"
                          data-tag-cat="${t.cat}">${t.label}</span>`).join('')}
            </div>
        </div>`;
    });

    const dnaFileId = dna.dna_id || dna.id || '';
    html += `<div class="style-detail-actions">
        <button class="btn btn-primary" onclick="saveStyleTags('${dnaFileId}')">태그 저장</button>
    </div>`;

    detailEl.innerHTML = html;
    detailEl.querySelectorAll('.tag').forEach(el => {
        el.addEventListener('click', () => el.classList.toggle('tag-on'));
    });
}

async function saveStyleTags(dnaId) {
    const detailEl = document.getElementById('style-detail');
    const activeTags = Array.from(detailEl.querySelectorAll('.tag.tag-on')).map(el => ({
        id: el.dataset.tagId,
        label: decodeURIComponent(el.dataset.tagLabel),
        cat: el.dataset.tagCat
    }));
    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}/tags`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active_tags: activeTags })
        });
        if (!res.ok) throw new Error('저장 실패');
        alert(`태그 ${activeTags.length}개가 저장되었습니다.`);
    } catch (err) {
        alert(err.message);
    }
}


// ═══════════════════════════════════════════════════════════
// 6. PANEL 4 — DB 관리
// ═══════════════════════════════════════════════════════════
function initDBPanel() {
    document.querySelector('.nav-item[data-panel="db"]').addEventListener('click', loadDBPanel);
}

async function loadDBPanel() {
    const listEl = document.getElementById('db-list');
    listEl.innerHTML = `<div class="loading-hint">불러오는 중...</div>`;

    try {
        const [colRes, dnaRes, blogRes] = await Promise.all([
            fetch(`${API}/api/blog/collections`),
            fetch(`${API}/api/mypage/dna`),
            fetch(`${API}/api/mypage/blogs`)
        ]);
        const colData  = await colRes.json();
        const dnaData  = await dnaRes.json();
        const blogData = await blogRes.json();

        // blog_id 기준으로 그룹화
        const groups = {};

        // 수집 데이터
        const collections = colData.collections || colData.items || [];
        collections.forEach(c => {
            const id = c.blog_id;
            if (!groups[id]) groups[id] = { blog_id: id, collections: [], dnas: [], blogs: [] };
            groups[id].collections.push(c);
        });

        // DNA 데이터
        (dnaData.items || []).forEach(d => {
            const id = d.blog_id;
            if (!groups[id]) groups[id] = { blog_id: id, collections: [], dnas: [], blogs: [] };
            groups[id].dnas.push(d);
        });

        // 생성된 블로그 글
        (blogData.items || []).forEach(b => {
            const id = b.blog_dna_id || b.blog_id || '';
            // blog_dna_id는 DNA_blogid_... 형태이므로 blog_id 추출
            const match = id.match(/DNA_([^_]+)_/);
            const blogId = match ? match[1] : id;
            if (blogId && groups[blogId]) {
                groups[blogId].blogs.push(b);
            }
        });

        const groupArr = Object.values(groups).sort((a, b) =>
            (b.collections[0]?.last_collected_at || '').localeCompare(a.collections[0]?.last_collected_at || '')
        );

        if (!groupArr.length) {
            listEl.innerHTML = `<div class="empty-hint">수집된 블로그가 없습니다</div>`;
            return;
        }

        listEl.innerHTML = groupArr.map(g => renderDBCard(g)).join('');

        // 토글 이벤트
        listEl.querySelectorAll('.db-card-header').forEach(el => {
            el.addEventListener('click', () => {
                const card = el.closest('.db-card');
                card.classList.toggle('open');
            });
        });

    } catch (err) {
        listEl.innerHTML = `<div class="error-hint">로드 실패: ${err.message}</div>`;
    }
}

function renderDBCard(g) {
    const col = g.collections[0] || {};
    const dnaCount = g.dnas.length;
    const blogCount = g.blogs.length;
    const postCount = col.post_count || 0;
    const lastDate = (col.last_collected_at || '').slice(0, 10);

    const dnaRows = g.dnas.map(d => `
        <div class="db-sub-row">
            <span class="db-sub-icon">DNA</span>
            <span class="db-sub-label">${d.id || ''}</span>
            <span class="db-sub-meta">${d.post_count || 0}개 분석 · ${(d.created_at || '').slice(0, 10)}</span>
            <div class="db-row-actions">
                <button class="btn-link" onclick="dbViewDNA('${d.id}')">상세</button>
                <button class="btn-link" onclick="loadStyleDetail('${d.id}');goToPanel('style')">편집</button>
                <button class="btn-link btn-link-danger" onclick="dbDelete('dna','${d.id}',this)">삭제</button>
            </div>
        </div>`).join('');

    const blogRows = g.blogs.slice(0, 5).map(b => `
        <div class="db-sub-row">
            <span class="db-sub-icon">글</span>
            <span class="db-sub-label">${b.title || '제목 없음'}</span>
            <span class="db-sub-meta">${(b.created_at || '').slice(0, 10)}</span>
            <div class="db-row-actions">
                <button class="btn-link" onclick="dbViewBlog('${b.id}')">상세</button>
                <button class="btn-link btn-link-danger" onclick="dbDelete('blogs','${b.id}',this)">삭제</button>
            </div>
        </div>`).join('');

    return `
        <div class="db-card">
            <div class="db-card-header">
                <div class="db-card-main">
                    <span class="db-blog-id">${g.blog_id}</span>
                    <div class="db-card-badges">
                        <span class="db-badge">수집 ${postCount}개</span>
                        <span class="db-badge">DNA ${dnaCount}개</span>
                        <span class="db-badge">생성 ${blogCount}개</span>
                    </div>
                </div>
                <div class="db-card-right">
                    <span class="db-card-date">${lastDate}</span>
                    <span class="db-card-toggle">▼</span>
                </div>
            </div>
            <div class="db-card-body">
                ${dnaCount ? `<div class="db-sub-section"><div class="db-sub-title">DNA 분석</div>${dnaRows}</div>` : ''}
                ${blogCount ? `<div class="db-sub-section"><div class="db-sub-title">생성된 글 (최근 5개)</div>${blogRows}</div>` : ''}
                ${!dnaCount && !blogCount ? `<div class="db-empty-body">수집만 완료. DNA 분석 후 글 작성이 가능합니다.</div>` : ''}
                <div class="db-card-actions">
                    <button class="btn btn-secondary btn-sm" onclick="goToPanel('collect');document.getElementById('collect-url').value='${g.blog_id}'">재수집</button>
                    <button class="btn btn-primary btn-sm" onclick="analyzeDNA('${g.blog_id}')">DNA 분석</button>
                </div>
            </div>
        </div>`;
}


async function dbViewDNA(dnaId) {
    openModal('DNA 분석 상세', '<div class="loading-hint">불러오는 중...</div>');
    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}`);
        const dna = await res.json();
        // DNA 키는 분석 시기에 따라 c1_tone 또는 c1_template_structure 등 다를 수 있음
        const cats = Object.keys(dna).filter(k => /^c\d+_/.test(k)).sort();
        const labels = cats.map(k => k.replace(/^c\d+_/, '').replace(/_/g, ' '));

        let html = `<div style="margin-bottom:16px">
            <strong>${dna.blog_id || ''}</strong>
            <span style="color:var(--text-muted);font-size:13px;margin-left:8px">${dna.post_count || 0}개 분석 · ${(dna.created_at || '').slice(0,10)}</span>
        </div>`;

        cats.forEach((key, i) => {
            const d = dna[key];
            if (!d) return;
            const title = d.title || labels[i];
            const entries = Object.entries(d)
                .filter(([k]) => !['title','examples','opening_examples','closing_examples'].includes(k))
                .map(([k, v]) => {
                    const val = Array.isArray(v) ? v.slice(0,4).join(', ') : String(v);
                    return val ? `<div class="dna-detail-row"><span class="dna-detail-key">${k}</span><span class="dna-detail-val">${val}</span></div>` : '';
                }).join('');
            if (!entries) return;
            html += `<div class="dna-detail-section">
                <div class="dna-detail-title">${title}</div>
                ${entries}
            </div>`;
        });

        document.getElementById('detail-modal-body').innerHTML = html;
    } catch (err) {
        document.getElementById('detail-modal-body').innerHTML = `<div class="error-hint">${err.message}</div>`;
    }
}

async function dbViewBlog(blogId) {
    openModal('블로그 글 상세', '<div class="loading-hint">불러오는 중...</div>');
    try {
        const res = await fetch(`${API}/api/mypage/blogs/${blogId}`);
        const data = await res.json();
        const versions = data.versions || [];
        let html = `<div style="margin-bottom:16px">
            <strong>${data.title || '제목 없음'}</strong>
            <span style="color:var(--text-muted);font-size:13px;margin-left:8px">${(data.created_at || '').slice(0,16).replace('T',' ')}</span>
        </div>`;
        if (versions.length) {
            html += versions.map((v, i) => `
                <div style="margin-bottom:24px">
                    <div style="font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;margin-bottom:8px">버전 ${i+1}</div>
                    <div style="font-size:14px;line-height:1.8;color:var(--text-secondary);white-space:pre-wrap">${(v.content || '').replace(/</g,'&lt;')}</div>
                </div>`).join('');
        } else if (data.content) {
            html += `<div style="font-size:14px;line-height:1.8;color:var(--text-secondary);white-space:pre-wrap">${data.content.replace(/</g,'&lt;')}</div>`;
        }
        document.getElementById('detail-modal-body').innerHTML = html;
    } catch (err) {
        document.getElementById('detail-modal-body').innerHTML = `<div class="error-hint">${err.message}</div>`;
    }
}

async function dbDelete(type, id, btn) {
    if (!confirm('삭제하시겠습니까? 복구할 수 없습니다.')) return;
    try {
        const res = await fetch(`${API}/api/mypage/${type}/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '삭제 실패');
        // 해당 행 제거
        btn.closest('.db-sub-row').remove();
    } catch (err) {
        alert(err.message);
    }
}


// ═══════════════════════════════════════════════════════════
// 7. 블로그 생성 로딩 모달
// ═══════════════════════════════════════════════════════════
const LOADING_EMOJIS = ['✍️','📝','💭','✨','📖','🎨','💡','🖊️','🌟','📋'];
const LOADING_STEPS  = [
    '자료를 분석하고 있어요',
    '블로그 스타일을 파악하고 있어요',
    'AI가 글을 구성하고 있어요',
    '문장을 다듬고 있어요',
    '마지막으로 검토하고 있어요',
    '거의 다 됐어요!',
];

let _loadingEmojiTimer = null;
let _loadingStepTimer  = null;
let _loadingBarTimer   = null;
let _loadingEmojiIdx   = 0;
let _loadingStepIdx    = 0;
let _loadingProgress   = 0;

function showLoadingModal() {
    const modal = document.getElementById('loading-modal');
    modal.classList.remove('hidden');
    _loadingEmojiIdx = 0;
    _loadingStepIdx  = 0;
    _loadingProgress = 0;

    document.getElementById('loading-emoji').textContent   = LOADING_EMOJIS[0];
    document.getElementById('loading-step').textContent    = LOADING_STEPS[0];
    document.getElementById('loading-bar').style.width     = '0%';

    // 이모지 순환 (700ms)
    _loadingEmojiTimer = setInterval(() => {
        _loadingEmojiIdx = (_loadingEmojiIdx + 1) % LOADING_EMOJIS.length;
        const el = document.getElementById('loading-emoji');
        el.classList.add('emoji-pop');
        el.textContent = LOADING_EMOJIS[_loadingEmojiIdx];
        setTimeout(() => el.classList.remove('emoji-pop'), 300);
    }, 700);

    // 단계 메시지 순환 (4s)
    _loadingStepTimer = setInterval(() => {
        _loadingStepIdx = Math.min(_loadingStepIdx + 1, LOADING_STEPS.length - 1);
        document.getElementById('loading-step').textContent = LOADING_STEPS[_loadingStepIdx];
    }, 4000);

    // 진행 바 (전체 ~30s 예상, 95%까지만 자동)
    _loadingBarTimer = setInterval(() => {
        if (_loadingProgress < 92) {
            _loadingProgress += _loadingProgress < 50 ? 2.5 : 0.8;
            document.getElementById('loading-bar').style.width = _loadingProgress + '%';
        }
    }, 600);
}

function hideLoadingModal() {
    clearInterval(_loadingEmojiTimer);
    clearInterval(_loadingStepTimer);
    clearInterval(_loadingBarTimer);

    const bar = document.getElementById('loading-bar');
    if (bar) bar.style.width = '100%';

    setTimeout(() => {
        document.getElementById('loading-modal').classList.add('hidden');
        if (bar) bar.style.width = '0%';
    }, 400);
}


// ═══════════════════════════════════════════════════════════
// 9. 상세보기 모달
// ═══════════════════════════════════════════════════════════
function initModal() {
    document.getElementById('detail-modal-close').addEventListener('click', closeModal);
    document.getElementById('detail-modal-overlay').addEventListener('click', closeModal);
}

function openModal(title, bodyHtml) {
    document.getElementById('detail-modal-title').textContent = title;
    document.getElementById('detail-modal-body').innerHTML = bodyHtml;
    document.getElementById('detail-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('detail-modal').classList.add('hidden');
}


// ═══════════════════════════════════════════════════════════
// 7. 페르소나 태그 추출
// ═══════════════════════════════════════════════════════════
function extractPersonaTags(dna) {
    const tags = [];
    const add = (id, label, cat) => {
        const s = String(label || '').trim();
        if (s && s.length < 60) tags.push({ id, label: s, cat });
    };

    const t = dna.c1_tone || {};
    if (t.tone) add('c1_tone', t.tone, '말투');
    if (t.formality) add('c1_formality', t.formality, '말투');
    if (t.relationship) add('c1_relationship', t.relationship, '말투');

    const s = dna.c2_structure || {};
    if (s.intro_style) add('c2_intro', `도입: ${s.intro_style}`, '구조');
    if (s.body_style) add('c2_body', `본문: ${s.body_style}`, '구조');
    if (s.conclusion_style) add('c2_conclusion', `마무리: ${s.conclusion_style}`, '구조');

    const c = dna.c3_content || {};
    if (c.depth) add('c3_depth', c.depth, '콘텐츠');
    (c.topics || []).slice(0, 3).forEach((v, i) => add(`c3_topic_${i}`, v, '주제'));

    const em = dna.c4_emotional || {};
    if (em.engagement_level) add('c4_engage', `참여도 ${em.engagement_level}/10`, '감성');
    if (em.humor_level) add('c4_humor', `유머 ${em.humor_level}/10`, '감성');
    if (em.emotional_style) add('c4_style', em.emotional_style, '감성');

    const ex = dna.c5_expression || {};
    (ex.signature_phrases || []).slice(0, 5).forEach((v, i) => add(`c5_sig_${i}`, v, '시그니처'));
    (ex.transition_words || []).slice(0, 3).forEach((v, i) => add(`c5_trans_${i}`, v, '전환어'));

    const sp = dna.c6_sentence_patterns || {};
    if (sp.avg_length) add('c6_length', `문장: ${sp.avg_length}`, '문장');
    if (sp.complexity) add('c6_complexity', sp.complexity, '문장');
    if (sp.rhythm) add('c6_rhythm', sp.rhythm, '문장');

    const v = dna.c7_vocabulary || {};
    if (v.level) add('c7_level', `어휘: ${v.level}`, '어휘');
    if (v.style) add('c7_style', v.style, '어휘');
    (v.characteristic_words || []).slice(0, 4).forEach((w, i) => add(`c7_word_${i}`, w, '특징어'));

    const p = dna.c8_paragraph_composition || {};
    if (p.whitespace_usage) add('c8_space', p.whitespace_usage, '단락');
    if (p.content_density) add('c8_density', p.content_density, '단락');
    if (p.avg_paragraph_length) add('c8_para_len', `단락: ${p.avg_paragraph_length}`, '단락');

    const oc = dna.c9_opening_closing || {};
    (oc.opening_types || []).slice(0, 2).forEach((v, i) => add(`c9_open_${i}`, `도입: ${v}`, '도입'));
    (oc.closing_types || []).slice(0, 2).forEach((v, i) => add(`c9_close_${i}`, `마무리: ${v}`, '마무리'));

    const vf = dna.c10_visual_formatting || {};
    if (vf.emoji_usage) add('c10_emoji_level', `이모지 ${vf.emoji_usage}/10`, '시각');
    if (vf.center_align) add('c10_center', vf.center_align, '시각');
    if (vf.bold_pattern) add('c10_bold', vf.bold_pattern, '시각');
    (vf.emoji_types || []).slice(0, 5).forEach((v, i) => add(`c10_emo_${i}`, v, '이모지'));
    (vf.special_symbols || []).slice(0, 5).forEach((v, i) => add(`c10_sym_${i}`, v, '기호'));
    if (vf.writing_guide) add('c10_guide', (vf.writing_guide || '').slice(0, 55), '작성 가이드');

    return tags;
}


// ═══════════════════════════════════════════════════════════
// 유틸
// ═══════════════════════════════════════════════════════════
function setFormLoading(form, isLoading) {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn) return;
    const textEl = btn.querySelector('.btn-text');
    const loadEl = btn.querySelector('.btn-loading');
    btn.disabled = isLoading;
    if (textEl) textEl.classList.toggle('hidden', isLoading);
    if (loadEl) loadEl.classList.toggle('hidden', !isLoading);
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
    return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
}
