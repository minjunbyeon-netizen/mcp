/* =========================================================
   auto-blog app.js
   패널 1: 블로그 수집 | 패널 2: 블로그 글 작성 | 패널 3: 스타일 업데이트
   ========================================================= */

// 서브패스 자동 감지: /mcp/ 에서도 /mcp/api/... 로 올바르게 요청
const API = window.location.pathname.replace(/\/[^/]*$/, '').replace(/\/$/, '');

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
    initAdminPanel();
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
            // ── 로그인 상태 → 앱 표시 ──────────────────────────
            document.getElementById('login-gate').classList.add('hidden');
            document.getElementById('app-content').classList.remove('hidden');
            document.getElementById('sb-logged-out').classList.add('hidden');
            document.getElementById('sb-logged-in').classList.remove('hidden');

            const u = data.user || {};
            const el = document.getElementById('sb-username');
            if (el) el.textContent = u.name || u.email || '';
            const av = document.getElementById('sb-avatar');
            if (av && u.picture) av.src = u.picture;

            // topbar
            const tbUser = document.getElementById('topbar-user');
            if (tbUser) tbUser.classList.remove('hidden');
            const tbName = document.getElementById('topbar-name');
            if (tbName) tbName.textContent = u.name || u.email || '';
            const tbAv = document.getElementById('topbar-avatar');
            if (tbAv) { if (u.picture) tbAv.src = u.picture; else tbAv.style.display = 'none'; }

            loadCollectHistory();
            loadDNAList();
        } else {
            // ── 비로그인 → 로그인 화면 ─────────────────────────
            document.getElementById('login-gate').classList.remove('hidden');
            document.getElementById('app-content').classList.add('hidden');
        }
    } catch {
        // 서버 응답 실패 → 로그인 화면 표시
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
        { key: 'c1_template_structure', label: '글 구조' },
        { key: 'c2_tone_mood', label: '톤/분위기' },
        { key: 'c3_speech_endings', label: '종결어미' },
        { key: 'c4_sentence_structure', label: '문장 구조' },
        { key: 'c5_paragraph_composition', label: '단락 구성' },
        { key: 'c6_signature_expressions', label: '시그니처 표현' },
        { key: 'c7_vocabulary_style', label: '어휘 스타일' },
        { key: 'c8_emoji_symbols', label: '이모지/기호' },
        { key: 'c9_opening_patterns', label: '도입부' },
        { key: 'c10_closing_patterns', label: '마무리' },
        { key: 'c11_visual_symbols', label: '시각 서식' },
        { key: 'c12_typography', label: '타이포그래피' },
        { key: 'c13_special_symbols', label: '특수 기호' },
        { key: 'c14_title_patterns', label: '제목 패턴' },
        { key: 'c15_post_length', label: '글 분량' },
        { key: 'c16_image_usage', label: '이미지 활용' },
        { key: 'c17_cta_patterns', label: 'CTA 패턴' },
        { key: 'c18_keyword_seo', label: 'SEO/키워드' },
        { key: 'c19_reader_engagement', label: '독자 참여' },
        { key: 'c20_interjections_fillers', label: '감탄사/추임새' },
        { key: 'c21_inline_formatting', label: '인라인 서식(SE3)' },
        { key: 'c22_content_patterns', label: '콘텐츠 패턴' },
    ];

    const hasC21 = !!dna['c21_inline_formatting'];
    const hasC22 = !!dna['c22_content_patterns'];
    const componentCount = categories.filter(c => !!dna[c.key]).length;

    let html = `<div class="dna-result">
        <div class="dna-result-header">
            <strong>${dna.blog_id || ''}</strong> DNA 분석 완료
            <span style="font-size:12px;font-weight:400;color:#6e6e73;margin-left:8px">${componentCount}/22 컴포넌트${!hasC21 || !hasC22 ? ' · <span style="color:#ff3b30">c21/c22 없음 — 재분석 권장</span>' : ''}</span>
        </div>
        <div class="dna-cats">`;

    categories.forEach(cat => {
        const d = dna[cat.key];
        if (!d) return;
        const items = Object.entries(d)
            .filter(([k]) => !['title','examples','opening_examples','closing_examples','font_switch_examples','size_switch_examples','color_switch_examples','combined_format_examples'].includes(k))
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
    const activeTags = allTags.filter(t => activeIds.has(t.id));
    const activeCount = activeTags.length;
    const preview = activeTags.slice(0, 5);
    const moreCount = activeCount - preview.length;
    const dnaId = dna.dna_id || dna.id || '';

    tagsEl.innerHTML = `
        <div class="write-dna-summary">
            <div class="write-dna-summary-top">
                <span class="write-dna-active-count">${activeCount}<span class="write-dna-total">/${allTags.length}</span></span>
                <span class="write-dna-count-label">스타일 적용 중</span>
                <button class="btn-link write-dna-edit-btn" onclick="loadStyleDetail('${dnaId}');goToPanel('style')">편집</button>
            </div>
            ${activeCount > 0 ? `
            <div class="tags-wrap write-tags-preview">
                ${preview.map(t => `<span class="tag tag-on">${t.label}</span>`).join('')}
                ${moreCount > 0 ? `<span class="tag-more">+${moreCount}개</span>` : ''}
            </div>` : `<div class="write-dna-no-tags">활성 태그 없음 — <button class="btn-link" onclick="loadStyleDetail('${dnaId}');goToPanel('style')">스타일 편집</button>에서 설정하세요</div>`}
        </div>`;
    tagsEl.classList.remove('hidden');
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
    window._lastImages = (data.images || []).map(url => `${API}${url}`);
    window._lastHtmlStyle = data.html_style || null;

    const vTypeLabel = { empathy: '독자공감형', info: '핵심정보형', story: '스토리텔링형',
                          formal: '포멀', balanced: '밸런스', casual: '캐주얼' };

    const container = document.getElementById('write-versions');
    container.innerHTML = '';

    versions.forEach((v, i) => {
        const typeLabel = v.version_label || vTypeLabel[v.version_type] || `버전 ${i + 1}`;

        const block = document.createElement('div');
        block.className = 'version-block';

        // 헤더
        const header = document.createElement('div');
        header.className = 'version-header';
        header.innerHTML = `
            <div class="version-label-row">
                <span class="version-badge">${typeLabel}</span>
            </div>
            <div class="version-actions">
                <button class="btn btn-secondary btn-sm" onclick="copyVersion(${i})">네이버 복사</button>
                <button class="btn btn-primary btn-sm" onclick="saveVersion(${i})">저장</button>
            </div>`;

        // 미리보기: blogToNaverHTML 렌더링 (DNA 스타일 + 이미지 위치 포함)
        const preview = document.createElement('div');
        preview.className = 'version-preview';
        preview.id = `preview-${i}`;
        preview.style.cssText = 'padding:24px;background:#fff;border-radius:8px;overflow:auto;max-height:800px;';
        preview.innerHTML = blogToNaverHTML(v.title || '', v.content || '', window._lastImages);

        block.appendChild(header);
        block.appendChild(preview);
        container.appendChild(block);
    });

    document.getElementById('write-preview-result').classList.remove('hidden');
}

function formatBlogContent(text) {
    const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const mdInline = s => s
        .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
        .replace(/__(.+?)__/g, '<b>$1</b>');
    return text.split('\n').map(line => {
        const t = line.trim();
        if (!t) return '<p style="margin:0;min-height:1.2em">&nbsp;</p>';
        if (/^##\s/.test(t))
            return `<p style="font-weight:bold;font-size:1.05em;margin:10px 0 3px">${mdInline(esc(t.replace(/^##\s+/,'')))}</p>`;
        if (/^#\s/.test(t))
            return `<p style="font-weight:bold;font-size:1.15em;margin:14px 0 5px">${mdInline(esc(t.replace(/^#\s+/,'')))}</p>`;
        if (/^[-*•]\s/.test(t) || /^\d+\.\s/.test(t))
            return `<p style="margin:0 0 3px;padding-left:14px">• ${mdInline(esc(t.replace(/^[-*•]\s|^\d+\.\s/,'')))}</p>`;
        return `<p style="margin:0 0 6px">${mdInline(esc(t))}</p>`;
    }).join('');
}

async function copyVersion(idx) {
    const previewEl = document.getElementById(`preview-${idx}`);
    const btn = document.querySelectorAll('.version-block')[idx]?.querySelector('.btn-secondary');

    // 렌더링된 미리보기 div를 직접 선택 → execCommand('copy')
    // → 태그 없이 실제 DOM 서식 그대로 clipboard에 올라감
    try {
        if (!previewEl) throw new Error('no preview');
        const range = document.createRange();
        range.selectNodeContents(previewEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        const ok = document.execCommand('copy');
        sel.removeAllRanges();
        if (!ok) throw new Error('execCommand failed');
    } catch {
        // fallback: ClipboardItem
        const v = (window._lastVersions || [])[idx];
        if (v) {
            const htmlStr = blogToNaverHTML(v.title || '', v.content || '', window._lastImages || []);
            try {
                const full = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${htmlStr}</body></html>`;
                await navigator.clipboard.write([new ClipboardItem({
                    'text/html' : new Blob([full],          { type: 'text/html'  }),
                    'text/plain': new Blob([v.content || ''], { type: 'text/plain' })
                })]);
            } catch {
                await navigator.clipboard.writeText((v.title ? v.title + '\n\n' : '') + (v.content || ''));
            }
        }
    }
    if (btn) { const orig = btn.textContent; btn.textContent = '복사 완료'; setTimeout(() => btn.textContent = orig, 1500); }
}

// ── Naver Blog 서식 HTML 변환 (Naver Smart Editor 3 호환) ──────────────────────────────
function blogToNaverHTML(title, content, images = []) {
    // ── DNA 기반 스타일 전체 적용 ───────────────────────────
    const st   = window._lastHtmlStyle || {};
    const ff   = st.font_family         || "'NanumGothic','나눔고딕','Malgun Gothic',sans-serif";
    const hff  = st.heading_font_family || ff;           // 소제목용 폰트 (두 번째 DNA 폰트)
    const fs   = st.base_font_size      || "15px";
    const hfs  = st.heading_font_size   || (parseInt(fs) + 2) + "px";
    const sfs  = st.small_font_size     || "13px";       // 작은 글씨 크기
    const lfs  = (parseInt(fs) + 4) + "px";             // [크게] 마커용 크기
    const lh   = st.line_height         || "2.2";
    const col  = "#333333";
    const accentCol        = st.accent_color       || "";
    const inlineAccentCol  = st.inline_accent_color || accentCol;
    const hlCol            = st.highlight_color    || "";
    const boldAllowed      = st.bold_allowed !== false;
    const centerHeadings   = !!st.center_headings;
    const inlineFontSwitch = !!st.inline_font_switch;  // c21: 인라인 폰트 전환 여부

    const esc = s => String(s)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    // ── 네이버 SE3 폰트 매핑 (한국어 이름 + 내부 ID 모두 지원) ────────────────
    const NAVER_FONTS = {
        // 한국어 이름
        '나눔고딕':       "'NanumGothic','나눔고딕',sans-serif",
        '나눔명조':       "'NanumMyeongjo','나눔명조',serif",
        '나눔스퀘어':     "'NanumSquare','나눔스퀘어',sans-serif",
        '나눔바른히피':   "'nanumbareunhipi','나눔바른히피',cursive",
        '나눔바른고딕':   "'NanumBarunGothic','나눔바른고딕',sans-serif",
        '맑은고딕':       "'Malgun Gothic','맑은 고딕',sans-serif",
        '돋움':           "'Dotum','돋움',sans-serif",
        '굴림':           "'Gulim','굴림',sans-serif",
        '바탕':           "'Batang','바탕',serif",
        // 네이버 SE3 내부 폰트 ID
        'nanumgothic':         "'NanumGothic','나눔고딕',sans-serif",
        'nanummyeongjo':       "'NanumMyeongjo','나눔명조',serif",
        'nanumsquare':         "'NanumSquare','나눔스퀘어',sans-serif",
        'nanumbareunhipi':     "'nanumbareunhipi','나눔바른히피',cursive",
        'nanumbarungothic':    "'NanumBarunGothic','나눔바른고딕',sans-serif",
        'nanumdasisijaghae':   "'nanumdasisijaghae','나눔다시시작해',cursive",
        'nanumbrush':          "'NanumBrush','나눔손글씨',cursive",
        'nanumpen':            "'NanumPen','나눔펜',cursive",
        'malgun':              "'Malgun Gothic','맑은 고딕',sans-serif",
        'dotum':               "'Dotum','돋움',sans-serif",
        'gulim':               "'Gulim','굴림',sans-serif",
        'batang':              "'Batang','바탕',serif",
        '강조':                hff,  // DNA 두 번째 폰트 (fallback)
    };

    const mdInline = raw => {
        let s = raw;

        // ─── 1. 볼드 (**text** / __text__) ───────────────────
        if (boldAllowed) {
            s = s.replace(/\*\*(.+?)\*\*/g, `<span style="font-weight:bold;">$1</span>`);
            s = s.replace(/__(.*?)__/g,      `<span style="font-weight:bold;">$1</span>`);
        } else {
            s = s.replace(/\*\*(.+?)\*\*/g, '$1').replace(/__(.*?)__/g, '$1');
        }

        // ─── 2. 기울임 (*text* / _text_) ──────────────────────
        s = s.replace(/\*([^*\n]+?)\*/g, `<span style="font-style:italic;">$1</span>`);
        s = s.replace(/_([^_\n]+?)_/g,   `<span style="font-style:italic;">$1</span>`);

        // ─── 3. 취소선 (~~text~~) ─────────────────────────────
        s = s.replace(/~~(.+?)~~/g, `<span style="text-decoration:line-through;color:#888;">$1</span>`);

        // ─── 4. 형광펜 (==text==) ─────────────────────────────
        const hlColor = hlCol || '#fff9a0';
        s = s.replace(/==(.+?)==/g,
            `<span style="background-color:${hlColor};padding:0 2px;">$1</span>`);

        // ─── 5. 액센트 색상 ({{text}}) ────────────────────────
        if (accentCol) {
            s = s.replace(/\{\{(.+?)\}\}/g,
                `<span style="color:${accentCol};">$1</span>`);
        }

        // ─── 6. esc() 이후 패턴 ───────────────────────────────
        const acCol = accentCol || '#0078cb';

        // 꺽쇠 &lt; 텍스트 &gt;
        s = s.replace(/&lt; ([^&<>]+?) &gt;/g,
            `<span style="color:${acCol};font-weight:bold;">&lt; $1 &gt;</span>`);
        s = s.replace(/&lt;([\uAC00-\uD7A3a-zA-Z0-9\s·]{2,25})&gt;/g,
            `<span style="color:${acCol};font-weight:bold;">&lt;$1&gt;</span>`);

        // 《》 한국어 꺽쇠
        s = s.replace(/《([^》]+)》/g,
            `<span style="color:${acCol};font-weight:bold;">《$1》</span>`);
        // 【】 대괄호
        s = s.replace(/【([^】]+)】/g,
            `<span style="font-weight:bold;">【$1】</span>`);
        // 「」 홑꺽쇠
        s = s.replace(/「([^」]+)」/g,
            `<span style="color:#555;">「$1」</span>`);
        // ≪≫ 이중 꺽쇠
        s = s.replace(/≪([^≫]+)≫/g,
            `<span style="color:${acCol};font-weight:bold;">≪$1≫</span>`);

        // 유니코드 큰따옴표 " "
        s = s.replace(/\u201c([^\u201d]+)\u201d/g,
            `<span style="color:#555;">\u201c$1\u201d</span>`);
        // 유니코드 작은따옴표 ' '
        s = s.replace(/\u2018([^\u2019]+)\u2019/g,
            `<span style="color:#555;">\u2018$1\u2019</span>`);

        // ─── 7. 브라켓 마커 ([ ]/[/ ] 형식) ──────────────────

        // 글꼴 크기 — 네이버 SE3 fs 단위
        s = s.replace(/\[fs(\d+)\]([\s\S]+?)\[\/fs\1\]/g,
            (_, n, t) => `<span style="font-size:${n}px;">${t}</span>`);
        // 또는 [크기:N] 형식
        s = s.replace(/\[크기:(\d+)\]([\s\S]+?)\[\/크기\]/g,
            (_, n, t) => `<span style="font-size:${n}px;">${t}</span>`);

        // [작게] / [크게] 단축어
        s = s.replace(/\[작게\]([\s\S]+?)\[\/작게\]/g,
            `<span style="font-size:${sfs};color:#666;">$1</span>`);
        s = s.replace(/\[크게\]([\s\S]+?)\[\/크게\]/g,
            `<span style="font-size:${lfs};font-weight:bold;">$1</span>`);
        // [매우크게] → fs28
        s = s.replace(/\[매우크게\]([\s\S]+?)\[\/매우크게\]/g,
            `<span style="font-size:28px;font-weight:bold;">$1</span>`);
        // [아주작게] → fs11
        s = s.replace(/\[아주작게\]([\s\S]+?)\[\/아주작게\]/g,
            `<span style="font-size:11px;color:#999;">$1</span>`);

        // [진하게]...[/진하게] → 굵게 (bold)
        s = s.replace(/\[진하게\]([\s\S]+?)\[\/진하게\]/g,
            `<span style="font-weight:bold;">$1</span>`);

        // 기울임 마커
        s = s.replace(/\[기울임\]([\s\S]+?)\[\/기울임\]/g,
            `<span style="font-style:italic;">$1</span>`);

        // 밑줄 마커
        s = s.replace(/\[밑줄\]([\s\S]+?)\[\/밑줄\]/g,
            `<span style="text-decoration:underline;">$1</span>`);

        // 취소선 마커
        s = s.replace(/\[취소선\]([\s\S]+?)\[\/취소선\]/g,
            `<span style="text-decoration:line-through;color:#888;">$1</span>`);

        // 색상 마커
        s = s.replace(/\[색상:(#[0-9a-fA-F]{3,6})\]([\s\S]+?)\[\/색상\]/g,
            `<span style="color:$1;">$2</span>`);

        // 배경색 마커
        s = s.replace(/\[배경:(#[0-9a-fA-F]{3,6})\]([\s\S]+?)\[\/배경\]/g,
            `<span style="background-color:$1;padding:0 2px;">$2</span>`);
        // [형광펜] 단축어 (DNA highlight_color 사용)
        s = s.replace(/\[형광펜\]([\s\S]+?)\[\/형광펜\]/g,
            `<span style="background-color:${hlColor};padding:0 2px;">$1</span>`);

        // 폰트 마커 [폰트:나눔고딕]...[/폰트:나눔고딕] 또는 [폰트:강조]...[/폰트]
        s = s.replace(/\[폰트:([^\]]+)\]([\s\S]+?)\[\/폰트(?::[^\]]+)?\]/g, (_, name, text) => {
            const fontCss = NAVER_FONTS[name] || hff;
            return `<span style="font-family:${fontCss};">${text}</span>`;
        });

        // ─── 8. 복합 서식 ─────────────────────────────────────

        // [강조] → bold + accent color (가장 많이 쓰는 복합 서식)
        s = s.replace(/\[강조\]([\s\S]+?)\[\/강조\]/g,
            `<span style="color:${acCol};font-weight:bold;">$1</span>`);

        // [볼드밑줄]
        s = s.replace(/\[볼드밑줄\]([\s\S]+?)\[\/볼드밑줄\]/g,
            `<span style="font-weight:bold;text-decoration:underline;">$1</span>`);

        // [기울임색상:#hex]
        s = s.replace(/\[기울임색상:(#[0-9a-fA-F]{3,6})\]([\s\S]+?)\[\/기울임색상\]/g,
            `<span style="font-style:italic;color:$1;">$2</span>`);

        // [크게색상:#hex]
        s = s.replace(/\[크게색상:(#[0-9a-fA-F]{3,6})\]([\s\S]+?)\[\/크게색상\]/g,
            `<span style="font-size:${lfs};font-weight:bold;color:$1;">$2</span>`);

        // [인라인강조] → inline_accent_color + bold
        s = s.replace(/\[인라인강조\]([\s\S]+?)\[\/인라인강조\]/g,
            `<span style="color:${inlineAccentCol || acCol};font-weight:bold;">$1</span>`);

        // ─── 9. 기타 특수 마커 ────────────────────────────────

        // [첨자위:text] → 위 첨자
        s = s.replace(/\[첨자위:([^\]]+)\]/g,
            `<sup style="font-size:0.75em;">$1</sup>`);
        // [첨자아래:text] → 아래 첨자
        s = s.replace(/\[첨자아래:([^\]]+)\]/g,
            `<sub style="font-size:0.75em;">$1</sub>`);

        // ─── 10. 추가 6가지 ────────────────────────────────────

        // [링크:url]text[/링크] → 하이퍼링크
        s = s.replace(/\[링크:([^\]]+)\]([\s\S]+?)\[\/링크\]/g,
            `<a href="$1" style="color:${acCol};text-decoration:underline;">$2</a>`);

        // [뱃지]text[/뱃지] → 인라인 필 배지 (강조 태그)
        s = s.replace(/\[뱃지\]([\s\S]+?)\[\/뱃지\]/g,
            `<span style="display:inline-block;background:${acCol};color:#fff;` +
            `font-size:11px;font-weight:bold;padding:1px 8px;border-radius:980px;` +
            `line-height:1.6;vertical-align:middle;">$1</span>`);

        // [밑줄색상:#hex]text[/밑줄색상] → 색상 밑줄 (border-bottom)
        s = s.replace(/\[밑줄색상:(#[0-9a-fA-F]{3,6})\]([\s\S]+?)\[\/밑줄색상\]/g,
            `<span style="border-bottom:2px solid $1;padding-bottom:1px;">$2</span>`);

        // [자간:N]text[/자간] → letter-spacing (단위: px)
        s = s.replace(/\[자간:(\d+(?:\.\d+)?)\]([\s\S]+?)\[\/자간\]/g,
            (_, n, t) => `<span style="letter-spacing:${n}px;">${t}</span>`);

        // [회색]text[/회색] → 흐린 회색 텍스트 단축어
        s = s.replace(/\[회색\]([\s\S]+?)\[\/회색\]/g,
            `<span style="color:#888;">$1</span>`);

        // [흰글자]text[/흰글자] → 흰색 텍스트 (배경색 조합용)
        s = s.replace(/\[흰글자\]([\s\S]+?)\[\/흰글자\]/g,
            `<span style="color:#ffffff;">$1</span>`);

        return s;
    };

    // 기본 p 태그 생성
    const p = (extra, inner) =>
        `<p style="font-family:${ff};font-size:${fs};line-height:${lh};`+
        `color:${col};margin:0;${extra}">${inner}</p>`;

    // ── 문단 블록 파싱 (멀티라인 블록 마커 지원) ──────────────
    const blocks = [];
    const lines = content.split('\n');
    let i = 0;

    // 멀티라인 블록 누적 헬퍼
    const collectUntil = (closeRe) => {
        const acc = [];
        while (i < lines.length) {
            const t = lines[i].trim();
            if (closeRe.test(t)) { i++; break; }
            acc.push(t);
            i++;
        }
        return acc.join('\n');
    };

    while (i < lines.length) {
        const t = lines[i].trim();
        i++;

        if (!t) {
            if (!blocks.length || blocks[blocks.length-1].type !== 'gap')
                blocks.push({ type: 'gap' });
            continue;
        }

        // ── 헤딩 / 리스트 ────────────────────────────────────
        if (/^##\s/.test(t)) {
            blocks.push({ type: 'h2', text: t.replace(/^##\s+/, '') });
        } else if (/^#\s/.test(t)) {
            blocks.push({ type: 'h1', text: t.replace(/^#\s+/, '') });
        } else if (/^[-*•]\s/.test(t) || /^\d+\.\s/.test(t)) {
            blocks.push({ type: 'li', text: t.replace(/^[-*•]\s|^\d+\.\s/, '') });

        // ── 구분선 ───────────────────────────────────────────
        } else if (/^\[구분선\]$/.test(t)) {
            blocks.push({ type: 'hr' });

        // ── 박스배경 (단일/멀티라인) ──────────────────────────
        } else if (/^\[박스배경:(#[0-9a-fA-F]{3,6})\]/.test(t)) {
            const mSingle = t.match(/^\[박스배경:(#[0-9a-fA-F]{3,6})\](.+)\[\/박스배경\]$/);
            if (mSingle) {
                blocks.push({ type: 'boxbg', text: mSingle[2], bgColor: mSingle[1] });
            } else {
                const bgColor = t.match(/^\[박스배경:(#[0-9a-fA-F]{3,6})\]/)[1];
                const inner   = t.replace(/^\[박스배경:#[0-9a-fA-F]{3,6}\]/, '');
                const rest    = collectUntil(/^\[\/박스배경\]$/);
                blocks.push({ type: 'boxbg', text: (inner + '\n' + rest).trim(), bgColor });
            }

        // ── 박스 (단일/멀티라인) ──────────────────────────────
        } else if (/^\[박스\]/.test(t)) {
            const mSingle = t.match(/^\[박스\](.+)\[\/박스\]$/);
            if (mSingle) {
                blocks.push({ type: 'box', text: mSingle[1] });
            } else {
                const inner = t.replace(/^\[박스\]/, '');
                const rest  = collectUntil(/^\[\/박스\]$/);
                blocks.push({ type: 'box', text: (inner + '\n' + rest).trim() });
            }

        // ── 중앙 정렬 (단일/멀티라인) ────────────────────────
        } else if (/^\[중앙\]/.test(t)) {
            const mSingle = t.match(/^\[중앙\](.+)\[\/중앙\]$/);
            if (mSingle) {
                blocks.push({ type: 'p', text: mSingle[1], align: 'center' });
            } else {
                const inner = t.replace(/^\[중앙\]/, '');
                const rest  = collectUntil(/^\[\/중앙\]$/);
                blocks.push({ type: 'p', text: (inner + '\n' + rest).trim(), align: 'center' });
            }

        // ── 우측 정렬 (단일/멀티라인) ────────────────────────
        } else if (/^\[우측\]/.test(t)) {
            const mSingle = t.match(/^\[우측\](.+)\[\/우측\]$/);
            if (mSingle) {
                blocks.push({ type: 'p', text: mSingle[1], align: 'right' });
            } else {
                const inner = t.replace(/^\[우측\]/, '');
                const rest  = collectUntil(/^\[\/우측\]$/);
                blocks.push({ type: 'p', text: (inner + '\n' + rest).trim(), align: 'right' });
            }

        // ── 들여쓰기 (단일/멀티라인) ─────────────────────────
        } else if (/^\[들여쓰기\]/.test(t)) {
            const mSingle = t.match(/^\[들여쓰기\](.+)\[\/들여쓰기\]$/);
            if (mSingle) {
                blocks.push({ type: 'p', text: mSingle[1], indent: true });
            } else {
                const inner = t.replace(/^\[들여쓰기\]/, '');
                const rest  = collectUntil(/^\[\/들여쓰기\]$/);
                blocks.push({ type: 'p', text: (inner + '\n' + rest).trim(), indent: true });
            }

        } else {
            blocks.push({ type: 'p', text: t });
        }
    }

    // ── 이미지 삽입 위치 결정 ──────────────────────────────
    const imgInsertAt = new Set();
    if (images.length > 0) {
        const gapAfterH = [], plainGap = [];
        for (let i = 0; i < blocks.length; i++) {
            if (blocks[i].type === 'gap') {
                const prev = i > 0 ? blocks[i-1].type : '';
                (prev === 'h1' || prev === 'h2' ? gapAfterH : plainGap).push(i);
            }
        }
        const cands = [...gapAfterH, ...plainGap];
        if (cands.length >= images.length) {
            const step = cands.length / images.length;
            for (let k = 0; k < images.length; k++)
                imgInsertAt.add(cands[Math.min(Math.round(k * step), cands.length-1)]);
        } else {
            cands.forEach(c => imgInsertAt.add(c));
            const rem = images.length - imgInsertAt.size;
            const step = Math.floor(blocks.length / (rem + 1));
            for (let k = 1; k <= rem; k++)
                imgInsertAt.add(Math.min(k * step, blocks.length - 1));
        }
    }

    const imgHtml = url =>
        `<p style="text-align:center;margin:16px 0;line-height:1;">` +
        `<img src="${url}" style="max-width:100%;height:auto;" /></p>`;

    // ── HTML 조립 ──────────────────────────────────────────
    let html = '';

    if (title) {
        const tfs = (parseInt(fs) + 6) + 'px';
        const tAlign = centerHeadings ? 'text-align:center;' : '';
        html += `<p style="font-family:${ff};font-size:${tfs};font-weight:bold;`+
                `line-height:1.5;color:#1a1a1a;margin:0 0 18px 0;${tAlign}">${esc(title)}</p>`;
    }

    let imgIdx = 0;
    for (let i = 0; i < blocks.length; i++) {
        if (imgInsertAt.has(i) && imgIdx < images.length)
            html += imgHtml(images[imgIdx++]);

        const b = blocks[i];
        if (b.type === 'gap') {
            html += `<p style="font-family:${ff};font-size:4px;line-height:1;margin:0;">&nbsp;</p>`;

        } else if (b.type === 'h2') {
            const hCol   = accentCol || '#1a1a1a';
            const hAlign = centerHeadings ? 'text-align:center;' : '';
            html += `<p style="font-family:${hff};font-size:${hfs};font-weight:bold;`+
                    `line-height:1.8;color:${hCol};margin:14px 0 4px 0;${hAlign}">`+
                    `${mdInline(esc(b.text))}</p>`;

        } else if (b.type === 'h1') {
            const h1fs   = (parseInt(hfs) + 2) + 'px';
            const hCol   = accentCol || '#1a1a1a';
            const hAlign = centerHeadings ? 'text-align:center;' : '';
            html += `<p style="font-family:${hff};font-size:${h1fs};font-weight:bold;`+
                    `line-height:1.6;color:${hCol};margin:20px 0 6px 0;${hAlign}">`+
                    `${mdInline(esc(b.text))}</p>`;

        } else if (b.type === 'li') {
            html += p('padding-left:18px;', `• ${mdInline(esc(b.text))}`);

        } else if (b.type === 'box') {
            // [박스] — 인용구 스타일 박스 (멀티라인 지원)
            const innerHtml = b.text.split('\n').map(l => l.trim())
                .filter(l => l).map(l => mdInline(esc(l))).join('<br>');
            html += `<p style="font-family:${ff};font-size:${fs};line-height:${lh};color:${col};`+
                    `margin:8px 0;padding:12px 16px;`+
                    `background:#f8f8f8;border-left:3px solid ${accentCol||'#ccc'};">`+
                    `${innerHtml}</p>`;

        } else if (b.type === 'boxbg') {
            // [박스배경:#hex] — 배경색 박스 (멀티라인 지원)
            const innerHtml = b.text.split('\n').map(l => l.trim())
                .filter(l => l).map(l => mdInline(esc(l))).join('<br>');
            html += `<p style="font-family:${ff};font-size:${fs};line-height:${lh};color:${col};`+
                    `margin:8px 0;padding:12px 16px;background:${b.bgColor};">`+
                    `${innerHtml}</p>`;

        } else if (b.type === 'hr') {
            // [구분선] — 얇은 구분선
            html += `<p style="border-top:1px solid #e0e0e0;margin:12px 0;line-height:0;">&nbsp;</p>`;

        } else {
            // 일반 p — 정렬/들여쓰기 옵션 처리 (멀티라인 내용은 <br> 연결)
            const alignStyle  = b.align  ? `text-align:${b.align};`   : '';
            const indentStyle = b.indent ? 'padding-left:24px;'        : '';
            const innerLines  = b.text.includes('\n')
                ? b.text.split('\n').map(l => l.trim()).filter(l => l).map(l => mdInline(esc(l))).join('<br>')
                : mdInline(esc(b.text));
            html += p(`${alignStyle}${indentStyle}`, innerLines);
        }
    }
    while (imgIdx < images.length) html += imgHtml(images[imgIdx++]);

    return html;
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

        // 블로그별 최신 DNA만 유지
        const blogMap = {};
        items.forEach(item => {
            if (!blogMap[item.blog_id] || (item.created_at || '') > (blogMap[item.blog_id].created_at || '')) {
                blogMap[item.blog_id] = item;
            }
        });
        const latest = Object.values(blogMap).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

        const sel = document.getElementById('write-dna-select');
        const current = sel.value;
        sel.innerHTML = `<option value="">스타일 미적용</option>`;
        latest.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.id;
            opt.textContent = item.blog_id;
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
    // 블로그별 최신 DNA만 표시
    const blogMap = {};
    items.forEach(item => {
        if (!blogMap[item.blog_id] || (item.created_at || '') > (blogMap[item.blog_id].created_at || '')) {
            blogMap[item.blog_id] = item;
        }
    });
    const latest = Object.values(blogMap).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    listEl.innerHTML = latest.map(item => {
        const needsUpgrade = !item.has_c21;
        return `
        <div class="dna-card" data-dna-id="${item.id}" onclick="loadStyleDetail('${item.id}')">
            <div class="dna-card-id">${item.blog_id || ''}${needsUpgrade ? ' <span style="font-size:10px;color:#ff3b30;font-weight:400">업그레이드 필요</span>' : ''}</div>
            <div class="dna-card-meta">${item.post_count || 0}개 분석 · ${(item.created_at || '').slice(0, 10)}</div>
        </div>`;
    }).join('');
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

const STYLE_SECTIONS = [
    { name: '글쓰기 스타일', cats: ['말투', '구조', '콘텐츠', '감성'] },
    { name: '어휘 & 표현', cats: ['시그니처', '전환어', '어휘', '특징어', '감탄사', '추임새'] },
    { name: '문장 & 단락', cats: ['문장', '단락', '글자수', '분량 지침'] },
    { name: '도입 & 마무리', cats: ['도입', '마무리'] },
    { name: '시각 포맷', cats: ['시각', '이모지', '기호', '폰트', '글꼴', '글꼴 지침', '작성 가이드'] },
    { name: '특수 기호', cats: ['꺽쇠', '괄호', '인용부호', '문장부호', '숫자 표현'] },
    { name: '제목', cats: ['제목', '제목 키워드'] },
    { name: '독자 소통', cats: ['독자 참여', '이미지'] },
];

function renderStyleDetail(dna) {
    const detailEl = document.getElementById('style-detail');
    const allTags = extractPersonaTags(dna);
    const activeIds = new Set((dna.active_tags || []).map(t => t.id));
    const activeCount = allTags.filter(t => activeIds.has(t.id)).length;

    // 카테고리별 그룹핑
    const catGroups = {};
    allTags.forEach(t => {
        if (!catGroups[t.cat]) catGroups[t.cat] = [];
        catGroups[t.cat].push(t);
    });

    // 섹션에 배정된 카테고리 추적
    const assignedCats = new Set(STYLE_SECTIONS.flatMap(s => s.cats));
    const remainingCats = Object.keys(catGroups).filter(c => !assignedCats.has(c));
    const sections = remainingCats.length
        ? [...STYLE_SECTIONS, { name: '기타', cats: remainingCats }]
        : STYLE_SECTIONS;

    const dnaFileId = dna.dna_id || dna.id || '';

    let html = `
        <div class="style-panel-header">
            <div class="style-panel-info">
                <div class="style-panel-blogid">${dna.blog_id || ''}</div>
                <div class="style-panel-meta">${dna.post_count || 0}개 분석 · ${(dna.created_at || '').slice(0, 10)}</div>
            </div>
            <div class="style-panel-counter">
                <span id="style-active-count">${activeCount}</span>
                <span class="style-counter-label">/ ${allTags.length}개 활성</span>
            </div>
        </div>
        <div class="style-panel-actions">
            <button class="btn-link" onclick="styleToggleAll(true)">전체 켜기</button>
            <button class="btn-link" onclick="styleToggleAll(false)">전체 끄기</button>
        </div>`;

    sections.forEach(sec => {
        const sectionTags = sec.cats.flatMap(cat => catGroups[cat] || []);
        if (!sectionTags.length) return;
        const secActive = sectionTags.filter(t => activeIds.has(t.id)).length;

        html += `
        <div class="style-section">
            <div class="style-section-head">
                <span class="style-section-name">${sec.name}</span>
                <span class="style-section-badge">${secActive}/${sectionTags.length}</span>
            </div>
            <div class="tags-wrap">
                ${sectionTags.map(t => `
                    <span class="tag ${activeIds.has(t.id) ? 'tag-on' : ''}"
                          data-tag-id="${t.id}"
                          data-tag-label="${encodeURIComponent(t.label)}"
                          data-tag-cat="${t.cat}">${t.label}</span>`).join('')}
            </div>
        </div>`;
    });

    const hasNew = !!(dna['c21_inline_formatting'] && dna['c22_content_patterns']);
    html += `
        <div class="style-save-bar">
            <button class="btn btn-primary" id="style-save-btn" onclick="saveStyleTags('${dnaFileId}')">저장</button>
            <button class="btn" style="border:1px solid #000;background:#fff;color:#000;border-radius:980px" onclick="reanalyzeDNA('${dna.blog_id || ''}')" title="${hasNew ? 'DNA 재분석 (22 컴포넌트)' : 'c21/c22 없음 — 재분석 필요'}">
                ${hasNew ? 'DNA 재분석' : 'DNA 업그레이드 (c21/c22 없음)'}
            </button>
        </div>`;

    detailEl.innerHTML = html;
    detailEl.querySelectorAll('.tag').forEach(el => {
        el.addEventListener('click', () => {
            el.classList.toggle('tag-on');
            updateStyleActiveCount();
        });
    });
}

function updateStyleActiveCount() {
    const all = document.querySelectorAll('#style-detail .tag').length;
    const active = document.querySelectorAll('#style-detail .tag.tag-on').length;
    const el = document.getElementById('style-active-count');
    if (el) el.textContent = active;
    // Update section badges
    document.querySelectorAll('.style-section').forEach(sec => {
        const badge = sec.querySelector('.style-section-badge');
        if (!badge) return;
        const total = sec.querySelectorAll('.tag').length;
        const on = sec.querySelectorAll('.tag.tag-on').length;
        badge.textContent = `${on}/${total}`;
    });
}

function styleToggleAll(on) {
    document.querySelectorAll('#style-detail .tag').forEach(t => t.classList.toggle('tag-on', on));
    updateStyleActiveCount();
}

async function saveStyleTags(dnaId) {
    const detailEl = document.getElementById('style-detail');
    const activeTags = Array.from(detailEl.querySelectorAll('.tag.tag-on')).map(el => ({
        id: el.dataset.tagId,
        label: decodeURIComponent(el.dataset.tagLabel),
        cat: el.dataset.tagCat
    }));
    const btn = document.getElementById('style-save-btn');
    try {
        if (btn) { btn.disabled = true; btn.textContent = '저장 중...'; }
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}/tags`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active_tags: activeTags })
        });
        if (!res.ok) throw new Error('저장 실패');
        if (btn) {
            btn.textContent = '저장됨';
            btn.style.background = '#1a8a1a';
            setTimeout(() => {
                btn.textContent = '저장';
                btn.style.background = '';
                btn.disabled = false;
            }, 1500);
        }
    } catch (err) {
        if (btn) { btn.textContent = '저장'; btn.disabled = false; }
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
    // 가장 최근 DNA (created_at 기준)
    const latestDna = g.dnas.slice().sort((a,b) =>
        (b.created_at || '').localeCompare(a.created_at || ''))[0];

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
                    ${latestDna ? `<button class="btn btn-secondary btn-sm" onclick="dbViewFinalStyle('${latestDna.id}')">최종 스타일</button>` : ''}
                    <button class="btn btn-primary btn-sm" onclick="analyzeDNAFromDB('${g.blog_id}')">DNA 분석</button>
                </div>
            </div>
        </div>`;
}


async function dbViewDNA(dnaId) {
    // 와이드 모달로 열기
    const modalContent = document.getElementById('detail-modal-content');
    modalContent.style.maxWidth = '860px';

    openModal('스타일 편집', '<div class="loading-hint">불러오는 중...</div>');

    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}`);
        const dna = await res.json();

        const allTags = extractPersonaTags(dna);
        const activeIds = new Set((dna.active_tags || []).map(t => t.id));
        const groups = {};
        allTags.forEach(t => {
            if (!groups[t.cat]) groups[t.cat] = [];
            groups[t.cat].push(t);
        });

        // 분석 상세 섹션
        const cats = Object.keys(dna).filter(k => /^c\d+_/.test(k)).sort();

        const html = `
            <div class="dna-modal-header">
                <span class="dna-modal-blogid">${dna.blog_id || ''}</span>
                <span class="dna-modal-meta">${dna.post_count || 0}개 분석 · ${(dna.created_at || '').slice(0,10)}</span>
            </div>

            <!-- 탭 -->
            <div class="tab-bar">
                <button class="tab-btn active" data-tab="tags">스타일 태그 편집</button>
                <button class="tab-btn" data-tab="detail">분석 상세</button>
            </div>

            <!-- 탭 1: 스타일 태그 편집 -->
            <div class="tab-pane active" id="tab-tags">
                <p class="tab-desc">태그를 켜면 글 생성 시 해당 스타일 특징이 강조 반영됩니다. 태그를 선택적으로 조합해 원하는 글쓰기 스타일을 세밀하게 조정하세요.</p>
                ${Object.entries(groups).map(([cat, tags]) => `
                    <div class="tag-group">
                        <div class="tag-group-label">${cat}</div>
                        <div class="tags-wrap">
                            ${tags.map(t => `
                                <span class="tag ${activeIds.has(t.id) ? 'tag-on' : ''}"
                                      data-tag-id="${t.id}"
                                      data-tag-label="${encodeURIComponent(t.label)}"
                                      data-tag-cat="${t.cat}">${t.label}</span>`).join('')}
                        </div>
                    </div>`).join('')}
                <div class="tab-pane-actions">
                    <span class="tag-count-hint" id="tag-count-hint">${activeIds.size}개 태그 활성</span>
                    <button class="btn btn-secondary btn-sm" onclick="clearAllTags()">전체 해제</button>
                    <button class="btn btn-primary btn-sm" onclick="dbSaveTagsFromModal('${dnaId}')">태그 저장</button>
                </div>
            </div>

            <!-- 탭 2: 분석 상세 -->
            <div class="tab-pane" id="tab-detail">
                ${cats.map(key => {
                    const d = dna[key];
                    if (!d || typeof d !== 'object') return '';
                    const label = (d.title || key.replace(/^c\d+_/, '').replace(/_/g, ' ')).toUpperCase();
                    const rows = Object.entries(d)
                        .filter(([k]) => !['title'].includes(k))
                        .map(([k, v]) => {
                            const isExample = ['examples','opening_examples','closing_examples'].includes(k);
                            const val = Array.isArray(v)
                                ? (isExample ? v.slice(0,2).map(s => `<div class="example-item">"${s}"</div>`).join('') : v.slice(0,5).join(' · '))
                                : String(v);
                            if (!val || val === 'undefined') return '';
                            return `<div class="dna-detail-row ${isExample ? 'dna-detail-example' : ''}">
                                <span class="dna-detail-key">${k}</span>
                                <span class="dna-detail-val">${val}</span>
                            </div>`;
                        }).join('');
                    if (!rows) return '';
                    return `<div class="dna-detail-section">
                        <div class="dna-detail-title">${label}</div>
                        ${rows}
                    </div>`;
                }).join('')}
            </div>`;

        document.getElementById('detail-modal-title').textContent = `${dna.blog_id} 스타일 편집`;
        document.getElementById('detail-modal-body').innerHTML = html;

        // 탭 전환
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
            });
        });

        // 태그 토글 + 카운트 업데이트
        document.querySelectorAll('#tab-tags .tag').forEach(el => {
            el.addEventListener('click', () => {
                el.classList.toggle('tag-on');
                updateTagCount();
            });
        });

    } catch (err) {
        document.getElementById('detail-modal-body').innerHTML = `<div class="error-hint">${err.message}</div>`;
    }
}

function updateTagCount() {
    const count = document.querySelectorAll('#tab-tags .tag.tag-on').length;
    const el = document.getElementById('tag-count-hint');
    if (el) el.textContent = `${count}개 태그 활성`;
}

function clearAllTags() {
    document.querySelectorAll('#tab-tags .tag').forEach(t => t.classList.remove('tag-on'));
    updateTagCount();
}

async function dbSaveTagsFromModal(dnaId) {
    const activeTags = Array.from(document.querySelectorAll('#tab-tags .tag.tag-on')).map(el => ({
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
        updateTagCount();
        // 저장 버튼 피드백
        const btn = document.querySelector('[onclick*="dbSaveTagsFromModal"]');
        if (btn) { btn.textContent = '저장 완료'; setTimeout(() => { btn.textContent = '태그 저장'; }, 1500); }
    } catch (err) {
        alert(err.message);
    }
}

async function dbViewFinalStyle(dnaId) {
    const modalContent = document.getElementById('detail-modal-content');
    modalContent.style.maxWidth = '720px';
    openModal('적용 스타일 최종본', '<div class="loading-hint">불러오는 중...</div>');

    try {
        const res = await fetch(`${API}/api/mypage/dna/${dnaId}`);
        const dna = await res.json();

        const allTags = extractPersonaTags(dna);
        const activeIds = new Set((dna.active_tags || []).map(t => t.id));
        const totalActive = activeIds.size;
        const totalAll = allTags.length;

        // 활성 태그 카테고리별 그룹
        const activeGroups = {};
        allTags.filter(t => activeIds.has(t.id)).forEach(t => {
            if (!activeGroups[t.cat]) activeGroups[t.cat] = [];
            activeGroups[t.cat].push(t);
        });

        // 비활성 태그
        const inactiveGroups = {};
        allTags.filter(t => !activeIds.has(t.id)).forEach(t => {
            if (!inactiveGroups[t.cat]) inactiveGroups[t.cat] = [];
            inactiveGroups[t.cat].push(t);
        });

        let activeSectionHtml;
        if (Object.keys(activeGroups).length === 0) {
            activeSectionHtml = `<div class="empty-hint" style="padding:24px 0">활성화된 태그가 없습니다. 태그 편집에서 스타일을 선택하세요.</div>`;
        } else {
            activeSectionHtml = Object.entries(activeGroups).map(([cat, tags]) => `
                <div class="final-style-row">
                    <span class="final-style-cat">${cat}</span>
                    <span class="final-style-tags">${tags.map(t => `<span class="tag tag-on">${t.label}</span>`).join('')}</span>
                </div>`).join('');
        }

        const inactiveSectionHtml = Object.keys(inactiveGroups).length ? `
            <div class="final-style-inactive">
                <div class="final-style-inactive-title">비활성 스타일 (현재 미적용)</div>
                ${Object.entries(inactiveGroups).map(([cat, tags]) => `
                    <div class="final-style-row">
                        <span class="final-style-cat muted">${cat}</span>
                        <span class="final-style-tags">${tags.map(t => `<span class="tag">${t.label}</span>`).join('')}</span>
                    </div>`).join('')}
            </div>` : '';

        const html = `
            <div class="final-style-header">
                <div class="final-style-blogid">${dna.blog_id || ''}</div>
                <div class="final-style-meta">${dna.post_count || 0}개 분석 · ${(dna.created_at || '').slice(0,10)} · 활성 태그 ${totalActive}/${totalAll}개</div>
            </div>
            <div class="final-style-desc">현재 설정 그대로 블로그 글을 생성하면 아래 스타일이 AI에게 전달됩니다. 원하는 스타일이 아니면 태그를 수정하세요.</div>
            <div class="final-style-body">${activeSectionHtml}</div>
            ${inactiveSectionHtml}
            <div class="final-style-footer">
                <button class="btn btn-secondary btn-sm" onclick="closeModal();setTimeout(()=>dbViewDNA('${dnaId}'),50)">태그 편집하기</button>
            </div>`;

        document.getElementById('detail-modal-title').textContent = `${dna.blog_id} 최종 스타일`;
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

async function reanalyzeDNA(blogId) {
    if (!blogId) return alert('blog_id를 찾을 수 없습니다.');
    if (!confirm(`${blogId} 블로그를 22컴포넌트 DNA로 재분석합니다.\n기존 DNA는 유지되고 새 DNA가 추가됩니다. 계속하시겠습니까?`)) return;
    await analyzeDNAFromDB(blogId);
}

async function analyzeDNAFromDB(blogId) {
    openModal('DNA 분석', `
        <div style="padding:32px 0;text-align:center">
            <div style="font-size:32px;margin-bottom:16px">분석 중</div>
            <div style="font-size:14px;color:var(--text-muted);margin-bottom:8px"><strong>${blogId}</strong> 블로그를 분석하고 있어요</div>
            <div style="font-size:13px;color:var(--text-muted)">30~60초 정도 소요됩니다</div>
        </div>`);
    try {
        const res = await fetch(`${API}/api/blog/analyze-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blog_id: blogId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '분석 실패');
        const container = document.getElementById('detail-modal-body');
        renderDNAResult(data, container);
        // 상단에 완료 메시지 추가
        container.insertAdjacentHTML('afterbegin', `
            <div style="margin-bottom:20px;padding:12px 16px;background:var(--bg-secondary);border-radius:var(--radius);display:flex;align-items:center;gap:12px">
                <span style="font-size:20px">완료</span>
                <div>
                    <div style="font-weight:700;font-size:14px">${data.blog_id} DNA 분석 완료</div>
                    <div style="font-size:12px;color:var(--text-muted)">${data.post_count || 0}개 글 · DNA ID: ${data.dna_id || ''}</div>
                </div>
            </div>`);
        loadDNAList();
        loadDBPanel();
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
// 9. 접근 관리 패널
// ═══════════════════════════════════════════════════════════
function initAdminPanel() {
    document.querySelector('.nav-item[data-panel="admin"]')
        .addEventListener('click', loadAdminEmails);
}

async function loadAdminEmails() {
    const el = document.getElementById('admin-email-list');
    el.innerHTML = `<div class="loading-hint">불러오는 중...</div>`;
    try {
        const res = await fetch(`${API}/api/admin/allowed-emails`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '조회 실패');
        renderAdminEmailList(data.emails || []);
    } catch (err) {
        el.innerHTML = `<div class="error-hint">${err.message}</div>`;
    }
}

function renderAdminEmailList(emails) {
    const el = document.getElementById('admin-email-list');
    if (!emails.length) {
        el.innerHTML = `<div class="empty-hint">등록된 이메일이 없습니다.<br>이메일을 추가하면 해당 구글 계정만 로그인할 수 있습니다.<br><small style="color:#999">목록이 비어있으면 누구나 로그인 가능합니다.</small></div>`;
        return;
    }
    el.innerHTML = `
        <div class="admin-count">${emails.length}개 계정 등록됨</div>
        ${emails.map(email => `
        <div class="admin-email-row">
            <span class="admin-email-addr">${email}</span>
            <button class="btn-link btn-danger" onclick="adminDeleteEmail('${email}', this)">제거</button>
        </div>`).join('')}`;
}

async function adminAddEmail() {
    const input = document.getElementById('admin-email-input');
    const email = input.value.trim();
    if (!email) return;
    try {
        const res = await fetch(`${API}/api/admin/allowed-emails`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '추가 실패');
        input.value = '';
        renderAdminEmailList(data.emails || []);
    } catch (err) {
        alert(err.message);
    }
}

async function adminDeleteEmail(email, btn) {
    if (!confirm(`${email} 을(를) 접근 목록에서 제거하시겠습니까?`)) return;
    btn.disabled = true;
    try {
        const res = await fetch(`${API}/api/admin/allowed-emails/${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '제거 실패');
        renderAdminEmailList(data.emails || []);
    } catch (err) {
        alert(err.message);
        btn.disabled = false;
    }
}


// ═══════════════════════════════════════════════════════════
// 10. 상세보기 모달
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
    // 와이드 모달 초기화
    const mc = document.getElementById('detail-modal-content');
    if (mc) mc.style.maxWidth = '';
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
    if (vf.separator_style) add('c10_sep', `구분선: ${vf.separator_style}`, '시각');
    (vf.emoji_types || []).slice(0, 5).forEach((v, i) => add(`c10_emo_${i}`, v, '이모지'));
    (vf.special_symbols || []).slice(0, 5).forEach((v, i) => add(`c10_sym_${i}`, v, '기호'));
    if (vf.writing_guide) add('c10_guide', (vf.writing_guide || '').slice(0, 55), '작성 가이드');

    // c11 — 글자수/분량
    const ls = dna.c11_length_stats || {};
    if (ls.avg_chars_per_post) add('c11_chars', ls.avg_chars_per_post, '글자수');
    if (ls.avg_sentences_per_post) add('c11_sentences', ls.avg_sentences_per_post, '글자수');
    if (ls.avg_chars_per_sentence) add('c11_sent_len', ls.avg_chars_per_sentence, '글자수');
    if (ls.content_ratio) add('c11_ratio', `비율: ${ls.content_ratio}`, '글자수');
    if (ls.writing_density_guide) add('c11_density', (ls.writing_density_guide || '').slice(0, 55), '분량 지침');

    // c12 — 폰트/글꼴
    const ty = dna.c12_typography || {};
    (ty.font_families || []).slice(0, 3).forEach((f, i) => add(`c12_font_${i}`, f, '폰트'));
    if (ty.base_font_size) add('c12_base_size', `본문: ${ty.base_font_size}`, '폰트');
    if (ty.heading_font_size) add('c12_head_size', `소제목: ${ty.heading_font_size}`, '폰트');
    if (ty.bold_frequency) add('c12_bold_freq', `볼드 ${ty.bold_frequency}/10`, '글꼴');
    if (ty.bold_purpose) add('c12_bold_purpose', ty.bold_purpose, '글꼴');
    if (ty.italic_usage) add('c12_italic', ty.italic_usage, '글꼴');
    if (ty.underline_usage) add('c12_underline', ty.underline_usage, '글꼴');
    if (ty.font_guide) add('c12_guide', (ty.font_guide || '').slice(0, 55), '글꼴 지침');

    // c13 — 꺽쇠/괄호
    const bq = dna.c13_brackets_quotes || {};
    (bq.angle_bracket_types || []).slice(0, 4).forEach((v, i) => add(`c13_angle_${i}`, v, '꺽쇠'));
    if (bq.angle_bracket_purpose) add('c13_angle_purpose', bq.angle_bracket_purpose, '꺽쇠');
    if (bq.angle_bracket_frequency) add('c13_angle_freq', `꺽쇠 빈도: ${bq.angle_bracket_frequency}`, '꺽쇠');
    (bq.square_bracket_types || []).slice(0, 3).forEach((v, i) => add(`c13_square_${i}`, v, '괄호'));
    if (bq.round_bracket_usage) add('c13_round', bq.round_bracket_usage, '괄호');
    if (bq.quotation_mark_style) add('c13_quote', bq.quotation_mark_style, '인용부호');

    // c14 — 제목 패턴
    const tp = dna.c14_title_patterns || {};
    if (tp.avg_title_length) add('c14_title_len', tp.avg_title_length, '제목');
    if (tp.title_structure) add('c14_title_struct', tp.title_structure, '제목');
    if (tp.number_usage) add('c14_number', tp.number_usage, '제목');
    if (tp.emotion_hook) add('c14_emotion', tp.emotion_hook, '제목');
    (tp.title_keywords || []).slice(0, 4).forEach((k, i) => add(`c14_kw_${i}`, k, '제목 키워드'));

    // c15 또는 c16 — 이미지/미디어
    const im = dna.c16_image_media || dna.c15_image_media || {};
    if (im.avg_images_per_post || im.avg_images) add('c15_img_count', im.avg_images_per_post || im.avg_images, '이미지');
    if (im.image_placement || im.image_position) add('c15_img_pos', im.image_placement || im.image_position, '이미지');
    if (im.caption_style || im.image_caption_style) add('c15_caption', im.caption_style || im.image_caption_style, '이미지');
    if (im.media_density) add('c15_density', im.media_density, '이미지');

    // c17 — 문장부호/구두점
    const pu = dna.c17_punctuation || {};
    if (pu.period_style) add('c17_period', pu.period_style, '문장부호');
    if (pu.comma_frequency) add('c17_comma', `쉼표 ${pu.comma_frequency}/10`, '문장부호');
    if (pu.exclamation_frequency) add('c17_exclaim', `느낌표 ${pu.exclamation_frequency}/10`, '문장부호');
    if (pu.exclamation_style) add('c17_exclaim_style', pu.exclamation_style, '문장부호');
    if (pu.tilde_usage) add('c17_tilde', `물결표: ${pu.tilde_usage}`, '문장부호');
    if (pu.ellipsis_usage) add('c17_ellipsis', `말줄임표: ${pu.ellipsis_usage}`, '문장부호');
    if (pu.multiple_punct_usage) add('c17_multi_punct', pu.multiple_punct_usage, '문장부호');
    if (pu.period_omission_ratio) add('c17_period_omit', `마침표 생략: ${pu.period_omission_ratio}`, '문장부호');

    // c18 — 숫자/데이터
    const nd = dna.c18_numbers_data || {};
    if (nd.numeral_preference) add('c18_numeral', nd.numeral_preference, '숫자 표현');
    if (nd.price_format) add('c18_price', `가격: ${nd.price_format}`, '숫자 표현');
    if (nd.date_format) add('c18_date', `날짜: ${nd.date_format}`, '숫자 표현');
    if (nd.unit_style) add('c18_unit', nd.unit_style, '숫자 표현');
    if (nd.ranking_format) add('c18_rank', `순위: ${nd.ranking_format}`, '숫자 표현');
    if (nd.approximation_style) add('c18_approx', `어림수: ${nd.approximation_style}`, '숫자 표현');

    // c19 — 독자 상호작용
    const re = dna.c19_reader_engagement || {};
    if (re.direct_question_frequency) add('c19_q_freq', `독자질문 ${re.direct_question_frequency}/10`, '독자 참여');
    (re.empathy_phrases || []).slice(0, 4).forEach((v, i) => add(`c19_empathy_${i}`, v, '독자 참여'));
    if (re.recommendation_strength) add('c19_rec_strength', `추천: ${re.recommendation_strength}`, '독자 참여');
    (re.recommendation_expressions || []).slice(0, 3).forEach((v, i) => add(`c19_rec_${i}`, v, '독자 참여'));
    (re.urgency_patterns || []).slice(0, 3).forEach((v, i) => add(`c19_urgency_${i}`, v, '독자 참여'));

    // c20 — 감탄사/추임새
    const fi = dna.c20_interjections_fillers || {};
    (fi.interjections || []).slice(0, 8).forEach((v, i) => add(`c20_interj_${i}`, v, '감탄사'));
    (fi.filler_starters || []).slice(0, 5).forEach((v, i) => add(`c20_filler_${i}`, v, '추임새'));
    (fi.affirmations || []).slice(0, 4).forEach((v, i) => add(`c20_affirm_${i}`, v, '추임새'));
    (fi.excitement_expressions || []).slice(0, 4).forEach((v, i) => add(`c20_excite_${i}`, v, '감탄사'));
    if (fi.frequency) add('c20_freq', `추임새 ${fi.frequency}/10`, '감탄사');

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
