/* ==========================================================================
   IdolJapan.store — Search Engine & Autocomplete Logic
   Path: js/search.js
   ========================================================================== */

async function loadSearchAliases() {
  try {
    const res = await fetch('/search_aliases.json').catch(() => null);
    if (res && res.ok) {
      searchAliases = await res.json().catch(() => ({}));
    }
  } catch (e) {
    console.warn('Search aliases fallback activated');
  }
}

// Bilingual Alias Normalization & Multi-Field Fuzzy Matcher
function matchesFuzzyQuery(text, query) {
  if (!text || !query) return false;
  const t = text.toLowerCase();
  const q = query.toLowerCase();
  if (t.includes(q)) return true;

  for (const [canonical, aliases] of Object.entries(searchAliases)) {
    if (aliases.some(a => a.toLowerCase() === q)) {
      if (t.includes(canonical.toLowerCase())) return true;
    }
  }

  const normT = t.replace(/ou/g, 'o').replace(/oo/g, 'o').replace(/uu/g, 'u').replace(/kiku/g, 'kikka');
  const normQ = q.replace(/ou/g, 'o').replace(/oo/g, 'o').replace(/uu/g, 'u').replace(/kiku/g, 'kikka');
  return normT.includes(normQ);
}

function showSearchSuggestions() {
  const box = document.getElementById('search-autocomplete-box');
  const input = document.getElementById('search-input');
  if (!box || !input) return;

  if (!input.value.trim()) {
    box.innerHTML = `
      <div class="p-3 text-xs text-stone-500 dark:text-slate-400">
        <span class="block text-[10px] font-bold uppercase tracking-wider text-stone-400 mb-2">Trending Idol Searches:</span>
        <div class="flex flex-wrap gap-1.5">
          <button onclick="quickSearch('Morning Musume')" class="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-800 dark:text-stone-200 transition font-bold">🌸 Morning Musume</button>
          <button onclick="quickSearch('Masaki Sato')" class="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-800 dark:text-stone-200 transition font-bold">💚 Masaki Sato</button>
          <button onclick="quickSearch('Nogizaka46')" class="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-800 dark:text-stone-200 transition font-bold">💜 Nogizaka46</button>
          <button onclick="quickSearch('FRUITS ZIPPER')" class="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-800 dark:text-stone-200 transition font-bold">💖 FRUITS ZIPPER</button>
          <button onclick="quickSearch('BABYMETAL')" class="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-800 dark:text-stone-200 transition font-bold">🦊 BABYMETAL</button>
          <button onclick="toggleAvailabilityMode('preorder')" class="px-2.5 py-1 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 font-bold transition">💿 Pre-Orders</button>
        </div>
      </div>
    `;
    box.classList.remove('hidden');
  }
}

function quickSearch(val) {
  const input = document.getElementById('search-input');
  if (input) {
    input.value = val;
    searchQuery = val.toLowerCase();
    const clearBtn = document.getElementById('search-clear-btn');
    if (clearBtn) clearBtn.classList.remove('hidden');
    closeAutocomplete();
    currentPage = 1;
    if (typeof syncUrlParams === 'function') syncUrlParams();
    if (typeof render === 'function') render();
  }
}

function updateAutocomplete(val, token) {
  if (token !== currentSearchToken) return;
  const box = document.getElementById('search-autocomplete-box');
  if (!box) return;

  const hasCjk = /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]/.test(val);
  const minLength = hasCjk ? 1 : 2;

  if (!val || val.length < minLength) {
    showSearchSuggestions();
    return;
  }

  // Exact catalog SKU match prioritized to rank #1
  const exactSkuMatches = [];
  const standardMatches = [];

  allProducts.forEach(p => {
    const idLower = String(p.id || '').toLowerCase();
    if (idLower === val) {
      exactSkuMatches.push(p);
    } else if (
      idLower.includes(val) ||
      matchesFuzzyQuery(p.title, val) ||
      matchesFuzzyQuery(p.artist, val)
    ) {
      standardMatches.push(p);
    }
  });

  const matches = [...exactSkuMatches, ...standardMatches].slice(0, 6);

  if (!matches.length) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }

  box.innerHTML = '';
  activeSuggestionIndex = -1;

  matches.forEach((item, sIdx) => {
    const row = document.createElement('div');
    row.id = `search-suggest-${sIdx}`;
    row.className = "autocomplete-item p-2 hover:bg-stone-50 dark:hover:bg-slate-800/80 cursor-pointer flex items-center gap-2.5 transition";
    row.role = "option";
    row.onclick = () => {
      if (typeof openModal === 'function') openModal(item.id);
      closeAutocomplete();
    };

    const cleanT = typeof stripTitlePrefixes === 'function' ? stripTitlePrefixes(item.title) : item.title;
    row.innerHTML = `
      <img src="${typeof getThumbnailUrl === 'function' ? getThumbnailUrl(item.image) : item.image}" class="w-8 h-8 rounded object-cover shrink-0" onerror="onImgLoadError(this)" />
      <div class="flex-1 min-w-0 text-left">
        <p class="text-xs font-bold text-stone-800 dark:text-stone-100 truncate">${escapeHtml(cleanT)}</p>
        <p class="text-[10px] text-stone-400 dark:text-slate-400 truncate">${escapeHtml(item.artist)} • <span class="font-mono">${item.id}</span> • ${typeof formatDisplayPrice === 'function' ? formatDisplayPrice(item.price, item) : item.price}</p>
      </div>
      <i class="fa-solid fa-chevron-right text-[9px] text-stone-300 dark:text-slate-600"></i>
    `;
    box.appendChild(row);
  });

  box.classList.remove('hidden');
}

function closeAutocomplete() {
  const box = document.getElementById('search-autocomplete-box');
  if (box) box.classList.add('hidden');
  activeSuggestionIndex = -1;
}

function highlightSuggestion(items) {
  items.forEach((it, idx) => {
    if (idx === activeSuggestionIndex) {
      it.classList.add('active');
      it.scrollIntoView({ block: 'nearest' });
    } else {
      it.classList.remove('active');
    }
  });
}

function triggerDebouncedSearch(val) {
  currentSearchToken++;
  const thisToken = currentSearchToken;

  const sClear = document.getElementById('search-clear-btn');
  if (sClear) {
    if (val) sClear.classList.remove('hidden');
    else sClear.classList.add('hidden');
  }

  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);

  searchDebounceTimeout = setTimeout(() => {
    updateAutocomplete(val.toLowerCase(), thisToken);
    searchQuery = val.toLowerCase();
    currentPage = 1;
    if (typeof syncUrlParams === 'function') syncUrlParams();
    if (typeof render === 'function') render();
  }, 280);
}

function clearSearch() {
  const input = document.getElementById('search-input');
  if (input) {
    input.value = '';
    searchQuery = '';
    if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
    const clearBtn = document.getElementById('search-clear-btn');
    if (clearBtn) clearBtn.classList.add('hidden');
    closeAutocomplete();
    currentPage = 1;
    if (typeof syncUrlParams === 'function') syncUrlParams();
    if (typeof render === 'function') render();
  }
}

// Initialize Search Listeners & Key Traversal
document.addEventListener('DOMContentLoaded', () => {
  const sInput = document.getElementById('search-input');

  if (sInput) {
    sInput.addEventListener('compositionstart', () => {
      isComposing = true;
    });

    sInput.addEventListener('compositionend', (e) => {
      isComposing = false;
      triggerDebouncedSearch(e.target.value.trim());
    });

    sInput.addEventListener('keydown', (e) => {
      const box = document.getElementById('search-autocomplete-box');
      const items = box ? box.querySelectorAll('.autocomplete-item') : [];

      if (['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) {
        if (!box || box.classList.contains('hidden') || !items.length) return;

        if (e.key === 'ArrowDown') {
          e.preventDefault();
          activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
          highlightSuggestion(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
          highlightSuggestion(items);
        } else if (e.key === 'Enter') {
          if (activeSuggestionIndex >= 0 && activeSuggestionIndex < items.length) {
            e.preventDefault();
            items[activeSuggestionIndex].click();
          }
        }
        return;
      }

      if (e.key === 'Escape') {
        closeAutocomplete();
        return;
      }

      if (['Shift', 'Control', 'Alt', 'Meta', 'Tab'].includes(e.key)) {
        return;
      }
    });

    sInput.addEventListener('input', (e) => {
      if (isComposing) return;
      triggerDebouncedSearch(e.target.value.trim());
    });
  }

  document.addEventListener('click', (e) => {
    const searchBox = document.getElementById('search-autocomplete-box');
    const searchInputEl = document.getElementById('search-input');
    if (searchBox && searchInputEl && !searchBox.contains(e.target) && e.target !== searchInputEl) {
      closeAutocomplete();
    }
  });
});
