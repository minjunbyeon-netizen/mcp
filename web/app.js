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
    initModal();
});


// ═══════════════════════════════════════════════════════════
// 1. AUTH
// ═══════════════════════════════════════════════════════════
async function initAuth() {
    try {
        const res = await fetch(`${API}/api/auth/status`);
        const data = await res.json();
        if (data.logged_in) {
            document.getElementById('login-gate').classList.add('hidden');
            document.getElementById('app-content').classList.remove('hidden');
            document.getElementById('sb-logged-out').classList.add('hidden');
            document.getElementById('sb-logged-in').classList.remove('hidden');
            if (data.user) {
                const el = document.getElementById('sb-username');
                if (el) el.textContent = data.user.name || data.user.email || '';
                const av = document.getElementById('sb-avatar');
                if (av && data.user.picture) av.src = data.user.picture;
            }
            loadCollectHistory();
            loadDNAList();
        } else {
            document.getElementById('login-gate').classList.remove('hidden');
            document.getElementById('app-content').classList.add('hidden');
        }
    } catch {
        document.getElementById('login-gate').classList.remove('hidden');
        document.getElementById('app-content').classList.add('hidden');
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
// 6. 모달
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
