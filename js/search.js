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

  const rawQuery = (input.value || '').trim();
  const q = rawQuery.toLowerCase();

  // If query is blank, close box or render initial quick-picks
  if (!q) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }

  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];
  const franchiseDict = (typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS) ? FRANCHISE_ARTISTS : {};
  const brandColors = (typeof ARTIST_BRAND_COLORS !== 'undefined' && ARTIST_BRAND_COLORS) ? ARTIST_BRAND_COLORS : {};

  // 1. KNOWN ENSEMBLE GROUPS (Excludes soloists and graduates)
  const ensembleGroupNames = [
    'Morning Musume', 'ANGERME', 'Juice=Juice', 'Tsubaki Factory', 'BEYOOOOONDS', 
    'OCHA NORMA', 'Rosy Chronicle', 'Hello Pro Kenshuusei', 'Berryz Kobo', '℃-ute', 
    'Buono!', 'Country Girls', 'Kobushi Factory', 'Minimoni', 'Tanpopo', 'v-u-den',
    'Nogizaka46', 'Sakurazaka46', 'Hinatazaka46', 'Yoshimotozaka46', 'Boku ga Mitakatta Aozora',
    'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48',
    'Momoiro Clover Z', 'Shiritsu Ebisu Chugaku', 'Chou Tokimeki Sendenbu', 'TEAM SHACHI', 'AMEFURASSHI',
    '=LOVE', '≠ME', '≒JOY',
    'FRUITS ZIPPER', 'CANDY TUNE', 'SWEET STEADY', 'CUTIE STREET', 'KAWAII LAB. MATES',
    'BABYMETAL', 'NiziU', 'ME:I', 'IS:SUE', 'Atarashii Gakko!'
  ];

  // Collect all distinct artists from data
  const allKnownArtists = Array.from(new Set([
    ...Object.values(franchiseDict).flat(),
    ...productList.map(p => p.artist).filter(Boolean)
  ]));

  // Match Groups
  const matchingGroups = ensembleGroupNames.filter(name => {
    return name.toLowerCase().includes(q) || (typeof matchesFuzzyQuery === 'function' && matchesFuzzyQuery(name, q));
  }).slice(0, 4);

  // Match Members / Soloists (Any artist not in ensembleGroupNames)
  const matchingMembers = allKnownArtists.filter(name => {
    if (ensembleGroupNames.includes(name)) return false;
    return name.toLowerCase().includes(q) || (typeof matchesFuzzyQuery === 'function' && matchesFuzzyQuery(name, q));
  }).slice(0, 4);

  // Match Items (Products by title or SKU, sorted newest release date first)
  const matchingItems = productList.filter(p => {
    const titleMatch = (p.title || '').toLowerCase().includes(q);
    const skuMatch = (p.id || '').toLowerCase().includes(q);
    return titleMatch || skuMatch;
  }).sort((a, b) => {
    const dateA = a.release_date || '0000/00/00';
    const dateB = b.release_date || '0000/00/00';
    return dateB.localeCompare(dateA);
  }).slice(0, 5);

  if (matchingGroups.length === 0 && matchingMembers.length === 0 && matchingItems.length === 0) {
    box.innerHTML = `
      <div class="p-3 text-center text-xs text-stone-400 dark:text-slate-500">
        No groups, members, or items matching "<strong>${q}</strong>"
      </div>
    `;
    box.classList.remove('hidden');
    return;
  }

  let html = '';

  // TIER 1: GROUPS
  if (matchingGroups.length > 0) {
    html += `
      <div class="p-1.5 bg-stone-50 dark:bg-slate-800/90 border-b border-stone-100 dark:border-slate-800">
        <span class="text-[10px] font-black uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1.5 px-2 py-0.5">
          <i class="fa-solid fa-users text-[9px]"></i> Groups &amp; Franchises
        </span>
      </div>
    `;
    matchingGroups.forEach(grp => {
      const count = productList.filter(p => p.artist === grp).length;
      const brandColor = brandColors[grp] || '#e11d48';
      html += `
        <button 
          type="button"
          onclick="selectSearchGroup('${grp.replace(/'/g, "\\'")}')"
          class="autocomplete-item w-full text-left px-3 py-2 hover:bg-rose-50 dark:hover:bg-slate-800 transition flex items-center justify-between text-xs cursor-pointer group"
        >
          <div class="flex items-center gap-2 truncate">
            <span class="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs" style="background-color: ${brandColor}"></span>
            <span class="font-bold text-stone-800 dark:text-stone-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 truncate">${grp}</span>
          </div>
          <span class="text-[10px] font-mono text-stone-400 dark:text-slate-500 shrink-0 ml-2">${count} releases →</span>
        </button>
      `;
    });
  }

  // TIER 2: MEMBERS
  if (matchingMembers.length > 0) {
    html += `
      <div class="p-1.5 bg-stone-50 dark:bg-slate-800/90 border-t border-b border-stone-100 dark:border-slate-800">
        <span class="text-[10px] font-black uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1.5 px-2 py-0.5">
          <i class="fa-solid fa-user text-[9px]"></i> Members &amp; Soloists
        </span>
      </div>
    `;
    matchingMembers.forEach(mem => {
      const count = productList.filter(p => p.artist === mem).length;
      const brandColor = brandColors[mem] || '#94a3b8';
      html += `
        <button 
          type="button"
          onclick="selectSearchMember('${mem.replace(/'/g, "\\'")}')"
          class="autocomplete-item w-full text-left px-3 py-2 hover:bg-purple-50 dark:hover:bg-slate-800 transition flex items-center justify-between text-xs cursor-pointer group"
        >
          <div class="flex items-center gap-2 truncate">
            <span class="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs" style="background-color: ${brandColor}"></span>
            <span class="font-bold text-stone-800 dark:text-stone-100 group-hover:text-purple-600 dark:group-hover:text-purple-400 truncate">${mem}</span>
          </div>
          <span class="text-[10px] font-mono text-stone-400 dark:text-slate-500 shrink-0 ml-2">${count} items →</span>
        </button>
      `;
    });
  }

  // TIER 3: ITEMS
  if (matchingItems.length > 0) {
    html += `
      <div class="p-1.5 bg-stone-50 dark:bg-slate-800/90 border-t border-b border-stone-100 dark:border-slate-800">
        <span class="text-[10px] font-black uppercase tracking-wider text-sky-600 dark:text-sky-400 flex items-center gap-1.5 px-2 py-0.5">
          <i class="fa-solid fa-compact-disc text-[9px]"></i> Release Items
        </span>
      </div>
    `;
    matchingItems.forEach(prod => {
      const cleanTitle = (prod.title || '').replace(/^\[[^\]]+\]\s*/, '');
      const priceText = (typeof formatDisplayPrice === 'function') 
        ? formatDisplayPrice(prod.price) 
        : `¥${(prod.price || 0).toLocaleString()}`;
      const imgUrl = (typeof getThumbnailUrl === 'function') ? getThumbnailUrl(prod.image) : prod.image;

      html += `
        <button 
          type="button"
          onclick="selectSearchProduct('${prod.id}')"
          class="autocomplete-item w-full text-left px-3 py-2 hover:bg-sky-50 dark:hover:bg-slate-800 transition flex items-center gap-2.5 text-xs cursor-pointer group"
        >
          <img src="${imgUrl}" class="w-7 h-7 object-contain rounded bg-stone-100 dark:bg-slate-700 shrink-0" onerror="if(typeof onImgLoadError==='function') onImgLoadError(this)" />
          <div class="flex-1 min-w-0">
            <div class="font-bold text-stone-800 dark:text-stone-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 truncate">${cleanTitle}</div>
            <div class="text-[10px] text-stone-400 dark:text-slate-500 truncate">${prod.artist} • <span class="font-mono">${prod.id}</span></div>
          </div>
          <span class="text-xs font-black text-rose-600 dark:text-rose-400 font-mono shrink-0">${priceText}</span>
        </button>
      `;
    });
  }

  box.innerHTML = html;
  box.classList.remove('hidden');
}

function selectSearchGroup(groupName) {
  const box = document.getElementById('search-autocomplete-box');
  const input = document.getElementById('search-input');
  if (box) box.classList.add('hidden');
  if (input) input.value = groupName;
  if (typeof setSubArtist === 'function') setSubArtist(groupName);
  else if (typeof setFilter === 'function') setFilter(groupName);
  const target = document.getElementById('product-container');
  if (target) target.scrollIntoView({ behavior: 'smooth' });
}

function selectSearchMember(memberName) {
  const box = document.getElementById('search-autocomplete-box');
  const input = document.getElementById('search-input');
  if (box) box.classList.add('hidden');
  if (input) input.value = memberName;
  if (typeof setSubArtist === 'function') setSubArtist(memberName);
  const target = document.getElementById('product-container');
  if (target) target.scrollIntoView({ behavior: 'smooth' });
}

function selectSearchProduct(productId) {
  const box = document.getElementById('search-autocomplete-box');
  if (box) box.classList.add('hidden');
  if (typeof openModal === 'function') openModal(productId);
}

function closeAutocomplete() {
  const box = document.getElementById('search-autocomplete-box');
  if (box) {
    box.classList.add('hidden');
    box.innerHTML = '';
  }
  activeSuggestionIndex = -1;
}

function highlightSuggestion(items) {
  if (!items || !items.length) return;
  items.forEach((item, idx) => {
    if (idx === activeSuggestionIndex) {
      item.classList.add('bg-rose-100', 'dark:bg-slate-700');
      item.focus();
      item.scrollIntoView({ block: 'nearest' });
    } else {
      item.classList.remove('bg-rose-100', 'dark:bg-slate-700');
    }
  });
}

function handleSearchInput(query) {
  triggerDebouncedSearch(query);
}

function triggerDebouncedSearch(query) {
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) {
    if (query) clearBtn.classList.remove('hidden');
    else clearBtn.classList.add('hidden');
  }

  showSearchSuggestions();

  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    searchQuery = (query || '').toLowerCase().trim();
    currentPage = 1;
    if (typeof syncUrlParams === 'function') syncUrlParams();
    if (typeof render === 'function') render();
  }, 250);
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
