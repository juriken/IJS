/* ==========================================================================
   IdolJapan.store — Redesigned Master-Detail & Visual Showcase Mega-Menu
   Path: js/mega-menu.js
   Architecture: Amazon/Newegg Two-Tier Master Rail + Visual Merchandising Card
   ========================================================================== */

// Use window fallbacks to prevent SyntaxError with variables already in config.js
window.activeRailIndex = window.activeRailIndex || 0;
if (typeof megaMenuTimer === 'undefined') window.megaMenuTimer = null;
if (typeof currentHoverCat === 'undefined') window.currentHoverCat = null;
if (typeof isMegaMenuPinned === 'undefined') window.isMegaMenuPinned = false;
if (typeof hpSoloistSubfilter === 'undefined') window.hpSoloistSubfilter = 'all';
if (typeof hpGradViewMode === 'undefined') window.hpGradViewMode = 'group';

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

/**
 * Handle hover on desktop Tier-1 tab bar
 */
function handleTopNavHover(cat) {
  if (isMegaMenuPinned) return;
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
 * In-flyout live search filter
 */
function filterMegaMenuLinks(query) {
  const q = (query || '').toLowerCase().trim();
  const links = document.querySelectorAll('.mega-menu-item-link');
  let visibleCount = 0;

  links.forEach(el => {
    const text = el.dataset.name || '';
    const aliases = el.dataset.aliases || '';
    const isMatch = !q || text.includes(q) || aliases.includes(q);
    if (isMatch) {
      el.classList.remove('hidden');
      visibleCount++;
    } else {
      el.classList.add('hidden');
    }
  });

  const emptyMsg = document.getElementById('mega-menu-filter-empty');
  if (emptyMsg) {
    if (q && visibleCount === 0) emptyMsg.classList.remove('hidden');
    else emptyMsg.classList.add('hidden');
  }
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

  // Resolve Featured Showcase Product
  let showcaseProduct = productList.find(p => {
    const matchesFranchise = (p.category === cat || (franchiseDict[cat] && franchiseDict[cat].includes(p.artist)));
    const matchesSection = (currentRail && currentRail.units && currentRail.units.length > 0) 
      ? currentRail.units.includes(p.artist) 
      : true;
    return matchesFranchise && matchesSection && typeof isPreOrder === 'function' && isPreOrder(p);
  });

  if (!showcaseProduct) {
    showcaseProduct = productList.find(p => {
      const matchesFranchise = (p.category === cat || (franchiseDict[cat] && franchiseDict[cat].includes(p.artist)));
      return matchesFranchise && typeof isPreOrder === 'function' && isPreOrder(p);
    });
  }

  if (!showcaseProduct) {
    showcaseProduct = productList.find(p => (p.category === cat || (franchiseDict[cat] && franchiseDict[cat].includes(p.artist))));
  }

  // ZONE 1: Left Master Sidebar Rail
  let railHtml = `
    <div class="w-full md:w-1/4 lg:w-[22%] bg-stone-50/80 dark:bg-slate-800/60 p-2.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col gap-1 shrink-0 max-h-[380px] overflow-y-auto">
      <div class="px-2 py-1 mb-1 border-b border-stone-200/60 dark:border-slate-700/60 flex items-center justify-between">
        <span class="text-[10px] font-black uppercase tracking-wider text-stone-500 dark:text-slate-400">Directory Index</span>
        <span class="text-[9px] font-mono text-stone-400 dark:text-slate-500 font-bold">${railItems.length} Sections</span>
      </div>
  `;

  railItems.forEach((item, idx) => {
    const isActive = (idx === window.activeRailIndex);
    const count = item.clusters 
      ? item.clusters.reduce((acc, c) => acc + (c.units ? c.units.length : 0), 0)
      : (item.units ? item.units.length : 0);

    railHtml += `
      <button 
        onclick="switchMegaMenuRail(${idx})" 
        class="w-full text-left px-2.5 py-2 rounded-xl transition flex items-center justify-between text-xs cursor-pointer ${
          isActive 
            ? 'bg-rose-600 text-white font-bold shadow-xs' 
            : 'text-stone-700 dark:text-stone-300 hover:bg-rose-50 dark:hover:bg-slate-700 hover:text-rose-600'
        }"
      >
        <div class="flex items-center gap-2 truncate">
          <i class="fa-solid ${item.icon} text-xs ${isActive ? 'text-white' : 'text-rose-500 dark:text-rose-400'}"></i>
          <span class="truncate text-[11px]">${safeEscapeHtml(item.title)}</span>
        </div>
        <span class="text-[10px] font-mono ml-1.5 px-1.5 py-0.2 rounded-full ${isActive ? 'bg-white/20 text-white' : 'bg-black/5 dark:bg-white/10 text-stone-400 dark:text-slate-400'}">
          ${count}
        </span>
      </button>
    `;
  });

  railHtml += `</div>`;

  // ZONE 2: Center Detail Link Canvas
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
    <div class="flex-1 min-w-0 bg-stone-50/40 dark:bg-slate-800/30 p-3.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col justify-between">
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

        <div id="mega-menu-matrix-scroll" class="max-h-[340px] overflow-y-auto pr-1.5">
  `;

  if (currentRail.clusters && currentRail.clusters.length > 0) {
    centerHtml += `<div class="space-y-3">`;
    currentRail.clusters.forEach(cluster => {
      centerHtml += `
        <div>
          <div class="text-[10px] font-extrabold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>${safeEscapeHtml(cluster.parent)}</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            ${(cluster.units || []).map(u => renderMegaMenuUnitRow(cat, u)).join('')}
          </div>
        </div>
      `;
    });
    centerHtml += `</div>`;
  } else {
    let unitsToRender = currentRail.units || [];
    if (currentRail.isSoloistColumn) {
      if (hpSoloistSubfilter === 'mline') {
        unitsToRender = ['Airi Suzuki', 'Sayumi Michishige', 'Karin Miyamoto', 'Masaki Sato', 'Riho Sayashi', 'Manaka Inaba', 'Reina Tanaka', 'Ai Takahashi'];
      } else if (hpSoloistSubfilter === 'classic') {
        unitsToRender = ['Aya Matsuura', 'Maki Goto', 'Natsumi Abe', 'Yuko Nakazawa', 'Miki Fujimoto', 'Erina Mano', 'Tsukishima Kirari'];
      }
    }

    centerHtml += `
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
        ${unitsToRender.map(u => renderMegaMenuUnitRow(cat, u)).join('')}
      </div>
    `;
  }

  centerHtml += `
          <div id="mega-menu-filter-empty" class="hidden py-8 text-center text-xs text-stone-400 dark:text-slate-500">
            <i class="fa-solid fa-magnifying-glass text-lg mb-1.5 opacity-60"></i>
            <p>No idols or subunits match your quick search.</p>
          </div>
        </div>
      </div>
    </div>
  `;

  // ZONE 3: Right Visual Merchandising Card
  let showcaseHtml = '';
  if (showcaseProduct) {
    const sTitle = safeEscapeHtml(safeStripPrefixes(showcaseProduct.title));
    const sArtist = safeEscapeHtml(showcaseProduct.artist);
    const sDate = showcaseProduct.release_date || 'Upcoming Street Date';
    const isUpcoming = typeof isPreOrder === 'function' && isPreOrder(showcaseProduct);
    const formattedPrice = safeFormatPrice(showcaseProduct.price);

    showcaseHtml = `
      <div class="w-full md:w-64 lg:w-72 bg-gradient-to-br from-rose-50/80 via-white to-pink-50/60 dark:from-slate-800/90 dark:via-slate-800/60 dark:to-slate-900 border border-rose-200/80 dark:border-slate-700/80 p-3.5 rounded-2xl flex flex-col justify-between shadow-2xs shrink-0">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-wider ${
              isUpcoming 
                ? 'bg-rose-600 text-white' 
                : 'bg-stone-800 text-amber-300'
            } px-2 py-0.5 rounded-full shadow-2xs">
              <i class="fa-solid ${isUpcoming ? 'fa-clock' : 'fa-star'} text-[8px]"></i>
              ${isUpcoming ? 'Featured Pre-Order' : 'Franchise Spotlight'}
            </span>
            <span class="text-[9px] font-mono text-stone-500 dark:text-slate-400 font-bold">${showcaseProduct.format || 'CD'}</span>
          </div>

          <div class="aspect-square bg-white dark:bg-slate-900 rounded-xl overflow-hidden mb-2.5 p-1.5 shadow-inner border border-stone-100 dark:border-slate-800 flex items-center justify-center">
            <img 
              src="${safeThumbnailUrl(showcaseProduct.image)}" 
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
          onclick="if(typeof triggerOutboundAffiliate==='function') triggerOutboundAffiliate(allProducts.find(x => x.id === '${showcaseProduct.id}'), 'megamenu_showcase');" 
          class="mt-3 w-full py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-center text-xs shadow-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <span>${isUpcoming ? 'Pre-Order on CDJapan' : 'Order on CDJapan'}</span>
          <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
        </button>
      </div>
    `;
  } else {
    showcaseHtml = `
      <div class="w-full md:w-64 lg:w-72 bg-stone-50 dark:bg-slate-800 p-4 rounded-2xl border border-stone-200 dark:border-slate-700 flex flex-col items-center justify-center text-center shrink-0">
        <i class="fa-solid fa-compact-disc text-3xl text-stone-300 dark:text-slate-600 mb-2"></i>
        <p class="text-xs font-bold text-stone-600 dark:text-slate-300">CDJapan Tokyo Partner</p>
        <p class="text-[10px] text-stone-400 dark:text-slate-500 mt-1">Official chart-reporting discography releases</p>
      </div>
    `;
  }

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
    footerFormatStrip += `
      <button 
        onclick="selectFranchiseFormat('${safeEscapeHtml(cat)}', '${f.fmt}')" 
        class="px-2 py-0.5 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-slate-700 text-stone-700 dark:text-stone-300 text-[10px] font-bold transition flex items-center gap-1 cursor-pointer border border-stone-200/50 dark:border-slate-700/50"
      >
        <i class="fa-solid ${f.icon} ${f.color} text-[9px]"></i>
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
}

/**
 * Render single artist row link in detail grid
 */
function renderMegaMenuUnitRow(cat, unitName) {
  const currentActiveArtist = (typeof activeArtist !== 'undefined') ? activeArtist : null;
  const isSelected = (currentActiveArtist === unitName);
  const productList = (typeof allProducts !== 'undefined' && Array.isArray(allProducts)) ? allProducts : [];
  const brandColors = (typeof ARTIST_BRAND_COLORS !== 'undefined' && ARTIST_BRAND_COLORS) ? ARTIST_BRAND_COLORS : {};

  const count = productList.filter(p => p.artist === unitName).length;
  const brandColor = brandColors[unitName] || '#94a3b8';
  const hasPreOrder = productList.some(p => p.artist === unitName && typeof isPreOrder === 'function' && isPreOrder(p));

  return `
    <button 
      onclick="selectSubArtistFromMegaMenu('${safeEscapeHtml(cat)}', '${safeEscapeHtml(unitName)}')" 
      data-name="${unitName.toLowerCase()}"
      class="mega-menu-item-link w-full text-left px-2 py-1.5 rounded-xl transition flex items-center justify-between text-xs cursor-pointer ${
        isSelected 
          ? 'bg-rose-600 text-white font-bold shadow-2xs' 
          : 'text-stone-700 dark:text-stone-300 hover:bg-rose-50 dark:hover:bg-slate-700 hover:text-rose-600'
      }"
    >
      <div class="flex items-center gap-2 truncate">
        <span class="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs" style="background-color: ${brandColor}"></span>
        <span class="truncate text-[11px]">${safeEscapeHtml(unitName)}</span>
        ${hasPreOrder ? '<span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" title="Active Pre-Orders Available"></span>' : ''}
      </div>
      <span class="text-[10px] ${isSelected ? 'text-white/80' : 'text-stone-400 dark:text-slate-500'} ml-1 font-mono">
        ${count}
      </span>
    </button>
  `;
}
