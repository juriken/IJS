/* ==========================================================================
   IdolJapan.store — Master-Detail Mega-Menu Engine (Enhanced)
   Features: Master-Detail Rail, Contextual Showcase, Bottom Scroll Fade Mask,
             Smart Pre-Order Count Badges, Zero-Suppression & Global Debounce Guard
   Path: js/mega-menu.js
   ========================================================================== */

// Use window fallbacks to prevent SyntaxError collisions with js/config.js
window.activeRailIndex = window.activeRailIndex || 0;
if (typeof megaMenuTimer === 'undefined') window.megaMenuTimer = null;
if (typeof currentHoverCat === 'undefined') window.currentHoverCat = null;
if (typeof isMegaMenuPinned === 'undefined') window.isMegaMenuPinned = false;
if (typeof hpSoloistSubfilter === 'undefined') window.hpSoloistSubfilter = 'all';
if (typeof hpGradViewMode === 'undefined') window.hpGradViewMode = 'group';

// Diagonal hover-tunnel & preview delay timers
let railSwitchTimer = null;
let showcasePreviewTimer = null;

function scheduleMegaMenuRail(idx) {
  if (railSwitchTimer) clearTimeout(railSwitchTimer);
  railSwitchTimer = setTimeout(() => {
    switchMegaMenuRail(idx);
  }, 80);
}
function cancelMegaMenuRailSchedule() {
  if (railSwitchTimer) {
    clearTimeout(railSwitchTimer);
    railSwitchTimer = null;
  }
}

// Global keydown listener for Escape and Arrow/Enter navigation
if (!window._megaMenuKeydownBound) {
  window._megaMenuKeydownBound = true;
  document.addEventListener('keydown', (e) => {
    const flyout = document.getElementById('mega-menu-flyout');
    if (!flyout || flyout.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
      dismissMegaMenu();
      return;
    }

    if (['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) {
      const activeElement = document.activeElement;
      const matrixScroll = document.getElementById('mega-menu-matrix-scroll');
      if (!matrixScroll) return;

      const items = Array.from(matrixScroll.querySelectorAll('.mega-menu-item-link'));
      if (!items.length) return;

      let currentIndex = items.indexOf(activeElement);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = (currentIndex + 1) % items.length;
        items[nextIndex].focus();
        items[nextIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = (currentIndex <= 0) ? items.length - 1 : currentIndex - 1;
        items[prevIndex].focus();
        items[prevIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter' && currentIndex >= 0) {
        e.preventDefault();
        items[currentIndex].click();
      }
    }
  });
}

// Defensive helper wrappers
function safeEscapeHtml(str) {
  if (typeof escapeHtml === 'function') {
    try { return escapeHtml(str); } catch (e) {}
  }
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function safeThumbnailUrl(img) {
  if (typeof getThumbnailUrl === 'function') {
    try { return getThumbnailUrl(img); } catch (e) {}
  }
  return img || '';
}

function safeStripPrefixes(title) {
  if (typeof stripTitlePrefixes === 'function') {
    try { return stripTitlePrefixes(title); } catch (e) {}
  }
  return title || '';
}

function safeFormatPrice(price) {
  if (typeof formatDisplayPrice === 'function') {
    try { return formatDisplayPrice(price); } catch (e) {}
  }
  return price ? `¥${Number(price).toLocaleString()}` : '';
}

function handleTopNavHover(cat) {
  if (isMegaMenuPinned) return;
  if (document.documentElement.classList.contains('layout-mobile')) return;
  if (megaMenuTimer) {
    clearTimeout(megaMenuTimer);
    megaMenuTimer = null;
  }
   
  const franchiseDict = (typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS) ? FRANCHISE_ARTISTS : {};
  if (cat === 'All' || !franchiseDict[cat] || franchiseDict[cat].length === 0) {
    dismissMegaMenu();
    return;
  }
  if (currentHoverCat !== cat) {
    window.activeRailIndex = 0;
  }
  currentHoverCat = cat;
  renderMegaMenu(cat);
  openMegaMenu();
}

/**
 * Handle mouse leaving Tier-1 tab bar
 */
function handleTopNavLeave() {
  if (isMegaMenuPinned) return;
  if (megaMenuTimer) clearTimeout(megaMenuTimer);
  megaMenuTimer = setTimeout(() => {
    dismissMegaMenu();
  }, 180);
}

/**
 * Handle mouse entering flyout container
 */
function handleMegaMenuEnter() {
  if (megaMenuTimer) {
    clearTimeout(megaMenuTimer);
    megaMenuTimer = null;
  }
}

/**
 * Handle mouse leaving flyout container
 */
function handleMegaMenuLeave() {
  if (isMegaMenuPinned) return;
  if (megaMenuTimer) clearTimeout(megaMenuTimer);
  megaMenuTimer = setTimeout(() => {
    dismissMegaMenu();
  }, 180);
}

/**
 * Open flyout and show backdrop scrim
 */
function openMegaMenu() {
  const flyout = document.getElementById('mega-menu-flyout');
  const backdrop = document.getElementById('mega-menu-backdrop');
  if (flyout) flyout.classList.remove('hidden');
  if (backdrop) backdrop.classList.remove('hidden');
}

/**
 * Dismiss flyout and reset pin state
 */
function dismissMegaMenu() {
  const flyout = document.getElementById('mega-menu-flyout');
  const backdrop = document.getElementById('mega-menu-backdrop');
  if (flyout) flyout.classList.add('hidden');
  if (backdrop) backdrop.classList.add('hidden');
  currentHoverCat = null;
  isMegaMenuPinned = false;
  window.activeRailIndex = 0;
  updatePinnedBadge();
}

/**
 * Update pinned indicator badge state
 */
function updatePinnedBadge() {
  const pinnedTag = document.getElementById('mega-menu-pinned-tag');
  if (!pinnedTag) return;
  if (isMegaMenuPinned) pinnedTag.classList.remove('hidden');
  else pinnedTag.classList.add('hidden');
}

/**
 * Click handler for Tier-1 navigation tabs
 */
function onTier1Click(cat) {
  const currentActiveFilter = (typeof activeFilter !== 'undefined') ? activeFilter : 'All';
  if (cat === currentActiveFilter && isMegaMenuPinned) {
    dismissMegaMenu();
    return;
  }

  if (typeof setFilter === 'function') setFilter(cat);

  const franchiseDict = (typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS) ? FRANCHISE_ARTISTS : {};
  if (cat !== 'All' && franchiseDict[cat] && franchiseDict[cat].length > 0) {
    isMegaMenuPinned = true;
    currentHoverCat = cat;
    window.activeRailIndex = 0;
    renderMegaMenu(cat);
    openMegaMenu();
    updatePinnedBadge();
  } else {
    dismissMegaMenu();
  }
}

/**
 * Backward compatibility stub for frontend_context.md contract
 */
function filterMegaMenuLinks(query) {
  // Retained so inline triggers don't throw; search is now handled globally
}

/**
 * Switch Master Sidebar Rail sub-tier
 */
function switchMegaMenuRail(index) {
  window.activeRailIndex = index;
  const currentActiveFilter = (typeof activeFilter !== 'undefined') ? activeFilter : 'All';
  renderMegaMenu(currentHoverCat || (currentActiveFilter !== 'All' ? currentActiveFilter : 'Hello! Project & Up-Front'));
}

/**
 * Quick jump combining category and format filtering
 */
function selectFranchiseFormat(cat, fmt) {
  if (typeof setFilter === 'function') setFilter(cat);
  if (typeof setFormat === 'function') setFormat(fmt);
  dismissMegaMenu();
}

/**
 * Select specific unit and close flyout
 */
function selectSubArtistFromMegaMenu(cat, unit) {
  if (typeof activeFilter !== 'undefined') activeFilter = cat;
  if (typeof setSubArtist === 'function') setSubArtist(unit);
  if (typeof updateFilterButtonsUI === 'function') updateFilterButtonsUI();
  dismissMegaMenu();
}

/**
 * Soloist sub-filter toggles for Hello! Project
 */
function setHpSoloistSubfilter(mode) {
  hpSoloistSubfilter = mode;
  renderMegaMenu('Hello! Project & Up-Front');
}

/**
 * Graduate view mode toggles for Hello! Project
 */
function setHpGradViewMode(mode) {
  hpGradViewMode = mode;
  renderMegaMenu('Hello! Project & Up-Front');
}

/**
 * Dynamically adjust bottom gradient fade mask on scroll
 */
function updateMatrixScrollFade(el) {
  const mask = document.getElementById('mega-menu-scroll-mask');
  if (!mask || !el) return;
  const isNearBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) <= 15;
  if (isNearBottom) {
    mask.style.opacity = '0';
    mask.style.pointerEvents = 'none';
  } else {
    mask.style.opacity = '1';
  }
}

/**
 * Sort helper: purchasable releases first, zero-count items last
 */
function sortUnitsByRelevance(unitsList) {
  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];
  return [...unitsList].sort((a, b) => {
    const countA = productList.filter(p => (typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, a) : p.artist === a)).length;
    const countB = productList.filter(p => (typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, b) : p.artist === b)).length;
    if (countA === 0 && countB > 0) return 1;
    if (countB === 0 && countA > 0) return -1;
    return countB - countA;
  });
}

/**
 * Main Master-Detail Mega-Menu Render Engine
 */
function renderMegaMenu(cat) {
  const franchiseTitle = document.getElementById('mega-menu-franchise-title');
  const columnsContainer = document.getElementById('mega-menu-columns-container');
  const viewAllBtn = document.getElementById('mega-menu-view-all-btn');

  if (!columnsContainer || !franchiseTitle) return;

  franchiseTitle.innerText = `${cat} Directory`;
  if (viewAllBtn) {
    viewAllBtn.onclick = () => {
      if (typeof setFilter === 'function') setFilter(cat);
      dismissMegaMenu();
    };
  }

  const franchiseDict = (typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS) ? FRANCHISE_ARTISTS : {};
  const rawSections = (typeof MEGA_MENU_CATEGORIES !== 'undefined' && MEGA_MENU_CATEGORIES && Array.isArray(MEGA_MENU_CATEGORIES[cat])) 
    ? MEGA_MENU_CATEGORIES[cat] 
    : [];
  
  // Build a normalized list of rail items
  let railItems = rawSections.map((sec, idx) => ({
    id: idx,
    title: sec.title || 'General Units',
    icon: sec.icon || 'fa-layer-group',
    isSoloistColumn: !!sec.isSoloistColumn,
    isGraduateColumn: !!sec.isGraduateColumn,
    clusters: sec.clusters || null,
    units: sec.units || []
  }));

  // Append full alphabetical group roster option
  if (franchiseDict[cat] && franchiseDict[cat].length > 0) {
    const allAlphabetical = [...franchiseDict[cat]].sort((a, b) => a.localeCompare(b));
    railItems.push({
      id: railItems.length,
      title: 'All Franchise Units (A–Z)',
      icon: 'fa-arrow-down-a-z',
      isSoloistColumn: false,
      isGraduateColumn: false,
      clusters: null,
      units: allAlphabetical
    });
  }

  if (railItems.length === 0) {
    columnsContainer.innerHTML = `<div class="p-4 text-center text-xs text-stone-400">No units found for this category.</div>`;
    return;
  }

  // Safety guard for active rail selection
  if (window.activeRailIndex >= railItems.length) {
    window.activeRailIndex = 0;
  }
  const currentRail = railItems[window.activeRailIndex] || railItems[0];

  // Safe product catalogue list
  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];

  const checkFranchiseMatch = (p, targetCat) => {
    if (p.category === targetCat) return true;
    if (targetCat === 'Hello! Project & Up-Front' && (p.category === 'Hello! Project' || p.category === 'Up-Front Alumni')) return true;
    if (targetCat === 'Modern & Alternative' && (p.category === 'Modern Idols' || p.category === 'Babymetal')) return true;
    if (targetCat === 'Stardust Planet' && p.category === 'Momoiro Clover Z') return true;
    if (franchiseDict[targetCat]) {
      return franchiseDict[targetCat].some(u => typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, u) : p.artist === u);
    }
    return false;
  };

  const currentRailUnits = currentRail.clusters 
    ? currentRail.clusters.flatMap(c => c.units || []) 
    : (currentRail.units || []);

  // Resolve Featured Showcase Product
  let showcaseProduct = productList.find(p => {
    const matchesFranchise = checkFranchiseMatch(p, cat);
    const matchesSection = currentRailUnits.length > 0 
      ? currentRailUnits.some(u => typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, u) : p.artist === u)
      : true;
    return matchesFranchise && matchesSection && typeof isPreOrder === 'function' && isPreOrder(p);
  });

  if (!showcaseProduct) {
    showcaseProduct = productList.find(p => {
      const matchesFranchise = checkFranchiseMatch(p, cat);
      return matchesFranchise && typeof isPreOrder === 'function' && isPreOrder(p);
    });
  }

  if (!showcaseProduct) {
    showcaseProduct = productList.find(p => checkFranchiseMatch(p, cat));
  }

  // ZONE 1: Left Master Sidebar Rail
  let railHtml = `
    <div class="w-full md:w-1/4 lg:w-[22%] bg-stone-50/80 dark:bg-slate-800/60 p-2.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col gap-1 shrink-0 max-h-[380px] overflow-y-auto mega-menu-scrollbar">
      <div class="px-2 py-1 mb-1 border-b border-stone-200/60 dark:border-slate-700/60 flex items-center justify-between">
        <span class="text-[10px] font-black uppercase tracking-wider text-stone-500 dark:text-slate-400">Directory Index</span>
        <span class="text-[9px] font-mono text-stone-400 dark:text-slate-500 font-bold">${railItems.length} Sections</span>
      </div>
  `;

  /* File: js/mega-menu.js | Block/Target: Zone 1 Left Master Rail Loop */
  railItems.forEach((item, idx) => {
    const isActive = (idx === window.activeRailIndex);
    const itemUnits = item.clusters 
      ? item.clusters.flatMap(c => c.units || []) 
      : (item.units || []);
    const count = itemUnits.length;
    const hasRailPreOrders = itemUnits.some(u => 
      productList.some(p => p.artist === u && typeof isPreOrder === 'function' && isPreOrder(p))
    );

    railHtml += `
      <button 
        onclick="switchMegaMenuRail(${idx})" 
        onmouseenter="scheduleMegaMenuRail(${idx})"
        onmouseleave="cancelMegaMenuRailSchedule()"
        class="w-full text-left px-2.5 py-2 rounded-xl transition flex items-center justify-between text-xs cursor-pointer ${
          isActive 
            ? 'bg-rose-600 text-white font-bold shadow-xs' 
            : 'text-stone-700 dark:text-stone-300 hover:bg-rose-50 dark:hover:bg-slate-700 hover:text-rose-600'
        }"
      >
        <div class="flex items-center gap-2 truncate">
          <i class="fa-solid ${item.icon} text-xs ${isActive ? 'text-white' : 'text-rose-500 dark:text-rose-400'}"></i>
          <span class="truncate text-[11px]">${safeEscapeHtml(item.title)}</span>
          ${hasRailPreOrders ? '<span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping shrink-0 ml-0.5" title="Active Pre-Orders in this section"></span>' : ''}
        </div>
        <span class="text-[10px] font-mono ml-1.5 px-1.5 py-0.2 rounded-full ${isActive ? 'bg-white/20 text-white' : 'bg-black/5 dark:bg-white/10 text-stone-400 dark:text-slate-400'}">
          ${count}
        </span>
      </button>
    `;
  });

  railHtml += `</div>`;

  // ZONE 2: Center Detail Link Canvas (with Scroll Fade Mask)
  let canvasHeaderControls = '';
  if (currentRail && currentRail.isSoloistColumn) {
    canvasHeaderControls = `
      <div class="flex items-center gap-1 text-[10px] font-bold">
        <button onclick="setHpSoloistSubfilter('all')" class="px-2 py-0.5 rounded-lg transition ${hpSoloistSubfilter === 'all' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">All</button>
        <button onclick="setHpSoloistSubfilter('mline')" class="px-2 py-0.5 rounded-lg transition ${hpSoloistSubfilter === 'mline' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">M-Line Only</button>
        <button onclick="setHpSoloistSubfilter('classic')" class="px-2 py-0.5 rounded-lg transition ${hpSoloistSubfilter === 'classic' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">Classic OG</button>
      </div>
    `;
  } else if (currentRail && currentRail.isGraduateColumn) {
    canvasHeaderControls = `
      <div class="flex items-center gap-1 text-[10px] font-bold">
        <button onclick="setHpGradViewMode('group')" class="px-2 py-0.5 rounded-lg transition ${hpGradViewMode === 'group' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">By Parent Group</button>
        <button onclick="setHpGradViewMode('era')" class="px-2 py-0.5 rounded-lg transition ${hpGradViewMode === 'era' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">By Debut Era</button>
      </div>
    `;
  }

  let centerHtml = `
    <div class="flex-1 min-w-0 bg-stone-50/40 dark:bg-slate-800/30 p-3.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col justify-between relative overflow-hidden">
      <div>
        <div class="flex flex-wrap items-center justify-between pb-2 mb-2.5 border-b border-stone-200/60 dark:border-slate-700/60 gap-2">
          <div class="flex items-center gap-2">
            <h4 class="font-black text-stone-900 dark:text-white text-xs uppercase tracking-wide flex items-center gap-1.5">
              <i class="fa-solid ${currentRail.icon} text-rose-600 dark:text-rose-400"></i>
              <span>${safeEscapeHtml(currentRail.title)}</span>
            </h4>
          </div>
          ${canvasHeaderControls}
        </div>

        <div 
          id="mega-menu-matrix-scroll" 
          onscroll="updateMatrixScrollFade(this)" 
          class="max-h-[340px] overflow-y-auto mega-menu-scrollbar pr-1.5 pb-6"
        >
  `;

  if (currentRail.clusters && currentRail.clusters.length > 0) {
    centerHtml += `<div class="space-y-3">`;
    currentRail.clusters.forEach(cluster => {
      const sortedClusterUnits = sortUnitsByRelevance(cluster.units || []);
      centerHtml += `
        <div>
          <div class="text-[10px] font-extrabold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>${safeEscapeHtml(cluster.parent)}</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            ${sortedClusterUnits.map(u => renderMegaMenuUnitRow(cat, u)).join('')}
          </div>
        </div>
      `;
    });
    centerHtml += `</div>`;
  } else {
    let unitsToRender = currentRail.units || [];
    if (currentRail.isSoloistColumn) {
      if (hpSoloistSubfilter === 'mline') {
        unitsToRender = ['Suzuki Airi', 'Michishige Sayumi', 'Miyamoto Karin', 'Sato Masaki', 'Sayashi Riho', 'Inaba Manaka', 'Tanaka Reina', 'Takahashi Ai'];
      } else if (hpSoloistSubfilter === 'classic') {
        unitsToRender = ['Matsuura Aya', 'Goto Maki', 'Abe Natsumi', 'Nakazawa Yuko', 'Fujimoto Miki', 'Mano Erina', 'Tsukishima Kirari (Kusumi Koharu)'];
      }
    }

    const sortedUnits = sortUnitsByRelevance(unitsToRender);
    centerHtml += `
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
        ${sortedUnits.map(u => renderMegaMenuUnitRow(cat, u)).join('')}
      </div>
    `;
  }

  // Bottom scroll cue mask with dynamic fade
  centerHtml += `
        </div>
      </div>
      <div 
        id="mega-menu-scroll-mask" 
        class="pointer-events-none absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-white dark:from-slate-900 to-transparent transition-opacity duration-200 flex items-end justify-center pb-1"
      >
        <span class="text-[9px] font-bold text-rose-500/80 dark:text-rose-400/80 bg-white/90 dark:bg-slate-900/90 px-2 py-0.5 rounded-full border border-rose-200/50 dark:border-slate-700/60 shadow-2xs">
          Scroll for more idols ↓
        </span>
      </div>
    </div>
  `;

  // ZONE 3: Right Visual Merchandising Card (Wrapped in mount ID for hover-sync)
  let showcaseContent = '';
  if (showcaseProduct) {
    showcaseContent = renderMegaMenuCardMarkup(showcaseProduct, {
      isUpcoming: typeof isPreOrder === 'function' && isPreOrder(showcaseProduct),
      badgeText: (typeof isPreOrder === 'function' && isPreOrder(showcaseProduct)) ? 'Featured Pre-Order' : 'Franchise Spotlight',
      badgeIcon: (typeof isPreOrder === 'function' && isPreOrder(showcaseProduct)) ? 'fa-clock' : 'fa-star',
      sourceTag: 'megamenu_showcase'
    });
  } else {
    showcaseContent = `
      <div class="w-full h-full min-h-[300px] bg-stone-50 dark:bg-slate-800 p-4 rounded-2xl border border-stone-200 dark:border-slate-700 flex flex-col items-center justify-center text-center shrink-0">
        <i class="fa-solid fa-compact-disc text-3xl text-stone-300 dark:text-slate-600 mb-2"></i>
        <p class="text-xs font-bold text-stone-600 dark:text-slate-300">CDJapan Tokyo Partner</p>
        <p class="text-[10px] text-stone-400 dark:text-slate-500 mt-1">Official chart-reporting discography releases</p>
      </div>
    `;
  }
  window._defaultMegaMenuShowcaseHtml = showcaseContent;
  const showcaseHtml = `<div id="mega-menu-showcase-mount" class="w-full md:w-64 lg:w-72 shrink-0">${showcaseContent}</div>`;

  // ZONE 4: Bottom Quick Format Jump Strip
  const quickFormats = [
    { label: 'Singles', fmt: 'Single', icon: 'fa-music', color: 'text-rose-500' },
    { label: 'Albums', fmt: 'Album', icon: 'fa-record-vinyl', color: 'text-rose-600' },
    { label: 'Blu-rays', fmt: 'Blu-ray', icon: 'fa-film', color: 'text-sky-500' },
    { label: 'DVDs', fmt: 'DVD', icon: 'fa-video', color: 'text-amber-500' },
    { label: 'Photobooks', fmt: 'Book', icon: 'fa-book-open', color: 'text-emerald-500' },
    { label: 'Collectables', fmt: 'Collectable', icon: 'fa-gift', color: 'text-purple-500' }
  ];

  let footerFormatStrip = `
    <div class="mt-3 pt-2.5 border-t border-stone-100 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
      <div class="flex items-center gap-1 text-[11px] font-bold text-stone-400 dark:text-slate-500">
        <i class="fa-solid fa-bolt text-rose-500 text-[10px]"></i>
        <span>Instant Format Jump for ${safeEscapeHtml(cat)}:</span>
      </div>
      <div class="flex flex-wrap items-center gap-1">
  `;

  quickFormats.forEach(f => {
    const isFmtActive = (typeof activeFormat !== 'undefined' && activeFormat === f.fmt);
    footerFormatStrip += `
      <button 
        onclick="selectFranchiseFormat('${safeEscapeHtml(cat)}', '${f.fmt}')" 
        class="px-2 py-0.5 rounded-lg text-[10px] font-bold transition flex items-center gap-1 cursor-pointer border border-stone-200/50 dark:border-slate-700/50 ${
          isFmtActive
            ? 'bg-rose-600 text-white shadow-2xs font-black'
            : 'bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-700 dark:text-stone-300'
        }"
      >
        <i class="fa-solid ${f.icon} ${isFmtActive ? 'text-white' : f.color} text-[9px]"></i>
        <span>${f.label}</span>
      </button>
    `;
  });

  footerFormatStrip += `
      </div>
    </div>
  `;

  // Render combined 3-Zone Panel + Footer Strip
  columnsContainer.className = "flex flex-col gap-1";
  columnsContainer.innerHTML = `
    <div class="flex flex-col md:flex-row gap-3">
      ${railHtml}
      ${centerHtml}
      ${showcaseHtml}
    </div>
    ${footerFormatStrip}
  `;

  // Initialize scroll mask visibility check
  const scrollEl = document.getElementById('mega-menu-matrix-scroll');
  if (scrollEl) updateMatrixScrollFade(scrollEl);
}

/* File: js/mega-menu.js | Block/Target: Unit Row Avatar Badges, Micro-Debounce & Isolated Showcase */
/**
 * Render single artist row link with initials avatar pill, smart badge & zero-suppression
 */
function renderMegaMenuUnitRow(cat, unitName) {
  const currentActiveArtist = (typeof activeArtist !== 'undefined') ? activeArtist : null;
  const isSelected = (currentActiveArtist === unitName);
  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];
  const brandColors = (typeof ARTIST_BRAND_COLORS !== 'undefined' && ARTIST_BRAND_COLORS) ? ARTIST_BRAND_COLORS : {};

  const artistProducts = productList.filter(p => {
    if (typeof matchesArtistName === 'function') {
      return matchesArtistName(p.artist, unitName);
    }
    return p.artist === unitName;
  });

  const count = artistProducts.length;
  const brandColor = brandColors[unitName] || (unitName.includes('Tsukishima') ? '#38bdf8' : '#94a3b8');
  
  // Two-letter initials avatar for immediate visual recognition
  const initials = unitName
    .replace(/[^\w\s]/gi, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');

  // Exact count of active pre-orders for this specific unit
  const preOrderCount = artistProducts.filter(p => typeof isPreOrder === 'function' && isPreOrder(p)).length;
  const isZeroCount = (count === 0);

  // Badge HTML formatting (Smart Badge: Pre-Order Count + Total)
  let badgeHtml = '';
  if (preOrderCount > 0) {
    badgeHtml = `
      <div class="flex items-center gap-1 shrink-0 ml-1">
        <span class="inline-flex items-center gap-0.5 bg-rose-600 text-white text-[9px] font-black px-1.5 py-0.2 rounded-full shadow-2xs animate-pulse">
          <i class="fa-solid fa-clock text-[8px]"></i>
          <span>${preOrderCount}</span>
        </span>
        <span class="text-[10px] ${isSelected ? 'text-white/80' : 'text-stone-400 dark:text-slate-500'} font-mono">
          ${count}
        </span>
      </div>
    `;
  } else {
    badgeHtml = `
      <span class="text-[10px] ${isSelected ? 'text-white/80' : (isZeroCount ? 'text-stone-300 dark:text-slate-600' : 'text-stone-400 dark:text-slate-500')} ml-1 font-mono">
        ${count}
      </span>
    `;
  }

  return `
    <button 
      onclick="selectSubArtistFromMegaMenu('${safeEscapeHtml(cat)}', '${safeEscapeHtml(unitName)}')" 
      onmouseenter="scheduleShowcasePreview('${safeEscapeHtml(unitName)}', '${safeEscapeHtml(cat)}')"
      onmouseleave="cancelShowcasePreview('${safeEscapeHtml(cat)}')"
      data-name="${unitName.toLowerCase()}"
      tabindex="0"
      class="mega-menu-item-link w-full text-left px-2 py-1.5 rounded-xl transition flex items-center justify-between text-xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-rose-500 ${
        isSelected 
          ? 'bg-rose-600 text-white font-bold shadow-xs' 
          : 'text-stone-700 dark:text-stone-300 hover:bg-rose-50 dark:hover:bg-slate-700 hover:text-rose-600'
      }"
    >
      <div class="flex items-center gap-2 truncate">
        <span 
          class="w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[8px] font-black tracking-tight text-white shadow-2xs ${isZeroCount ? 'grayscale opacity-50' : ''}" 
          style="background-color: ${brandColor}"
        >
          ${initials || '•'}
        </span>
        <span class="truncate text-[11px]">${safeEscapeHtml(unitName)}</span>
      </div>
      ${badgeHtml}
    </button>
  `;
}

/**
 * Reusable HTML generator for Zone 3 spotlight product card
 */
function renderMegaMenuCardMarkup(prod, meta) {
  const sTitle = safeEscapeHtml(safeStripPrefixes(prod.title));
  const sArtist = safeEscapeHtml(prod.artist);
  const sDate = prod.release_date || 'Upcoming Street Date';
  const formattedPrice = safeFormatPrice(prod.price);
  const btnLabel = meta.isUpcoming ? 'Pre-Order on CDJapan' : 'Order on CDJapan';

  return `
    <div class="w-full bg-gradient-to-br from-rose-50/90 via-white to-pink-50/80 dark:from-slate-800/95 dark:via-slate-800/80 dark:to-slate-900 border border-rose-300/80 dark:border-slate-700/80 p-3.5 rounded-2xl flex flex-col justify-between shadow-2xs h-full">
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-wider ${
            meta.isUpcoming ? 'bg-rose-600 text-white' : 'bg-stone-800 text-amber-300'
          } px-2 py-0.5 rounded-full shadow-2xs">
            <i class="fa-solid ${meta.badgeIcon} text-[8px]"></i>
            ${meta.badgeText}
          </span>
          <span class="text-[9px] font-mono text-stone-500 dark:text-slate-400 font-bold">${prod.format || 'CD'}</span>
        </div>

        <div class="aspect-square bg-white dark:bg-slate-900 rounded-xl overflow-hidden mb-2.5 p-1.5 shadow-inner border border-stone-100 dark:border-slate-800 flex items-center justify-center">
          <img 
            src="${safeThumbnailUrl(prod.image)}" 
            alt="${sTitle}" 
            class="w-full h-full object-contain transition-transform duration-300 hover:scale-105" 
            onerror="if(typeof onImgLoadError==='function') onImgLoadError(this);" 
          />
        </div>

        <h5 class="font-extrabold text-xs text-stone-900 dark:text-white line-clamp-2 leading-snug" title="${sTitle}">
          ${sTitle}
        </h5>
        
        <div class="mt-1 flex items-center justify-between text-[11px]">
          <span class="font-bold text-rose-600 dark:text-rose-400 truncate">${sArtist}</span>
          <span class="text-xs font-black text-stone-900 dark:text-white font-mono">${formattedPrice}</span>
        </div>

        <p class="text-[10px] text-stone-500 dark:text-slate-400 mt-1 flex items-center gap-1">
          <i class="fa-regular fa-calendar text-[9px]"></i>
          <span>${sDate}</span>
        </p>
      </div>

      <button 
        onclick="if(typeof triggerOutboundAffiliate==='function') triggerOutboundAffiliate(allProducts.find(x => x.id === '${prod.id}'), '${meta.sourceTag}');" 
        class="mt-3 w-full py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-center text-xs shadow-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
      >
        <span>${btnLabel}</span>
        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
      </button>
    </div>
  `;
}

/**
 * 40ms micro-debounced hover scheduler for Zone 3 showcase
 */
function scheduleShowcasePreview(unitName, cat) {
  if (showcasePreviewTimer) clearTimeout(showcasePreviewTimer);
  showcasePreviewTimer = setTimeout(() => {
    previewUnitInShowcase(unitName, cat);
  }, 40);
}

function cancelShowcasePreview(cat) {
  if (showcasePreviewTimer) {
    clearTimeout(showcasePreviewTimer);
    showcasePreviewTimer = null;
  }
  restoreDefaultShowcase(cat);
}

/**
 * Preview specific hovered artist release inside Zone 3 showcase
 */
function previewUnitInShowcase(unitName, cat) {
  const mount = document.getElementById('mega-menu-showcase-mount');
  if (!mount) return;

  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];
  const unitProduct = productList.find(p => (typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, unitName) : p.artist === unitName) && typeof isPreOrder === 'function' && isPreOrder(p)) ||
                      productList.find(p => (typeof matchesArtistName === 'function' ? matchesArtistName(p.artist, unitName) : p.artist === unitName));

  if (!unitProduct) {
    restoreDefaultShowcase(cat);
    return;
  }

  const isUpcoming = typeof isPreOrder === 'function' && isPreOrder(unitProduct);
  mount.innerHTML = renderMegaMenuCardMarkup(unitProduct, {
    isUpcoming,
    badgeText: isUpcoming ? 'Artist Pre-Order' : 'Latest Release',
    badgeIcon: isUpcoming ? 'fa-clock' : 'fa-compact-disc',
    sourceTag: 'megamenu_hover_preview'
  });
}

/**
 * Restore default franchise spotlight without re-rendering directory columns
 */
function restoreDefaultShowcase(cat) {
  const mount = document.getElementById('mega-menu-showcase-mount');
  if (mount && window._defaultMegaMenuShowcaseHtml) {
    mount.innerHTML = window._defaultMegaMenuShowcaseHtml;
  }
}
