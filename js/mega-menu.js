/* File: js/mega-menu.js | Block/Target: Full File (Redesigned Master-Detail Mega-Menu Engine) */

/* ==========================================================================
   IdolJapan.store — Redesigned Master-Detail & Visual Showcase Mega-Menu
   Path: js/mega-menu.js
   Architecture: Amazon/Newegg Two-Tier Master Rail + Visual Merchandising Card
   ========================================================================== */

let megaMenuTimer = null;
let currentHoverCat = null;
let isMegaMenuPinned = false;
let activeRailIndex = 0;
let hpSoloistSubfilter = 'all';
let hpGradViewMode = 'group';

/**
 * Handle hover on desktop Tier-1 tab bar
 */
function handleTopNavHover(cat) {
  if (isMegaMenuPinned) return;
  if (megaMenuTimer) {
    clearTimeout(megaMenuTimer);
    megaMenuTimer = null;
  }
  if (cat === 'All' || !FRANCHISE_ARTISTS[cat] || FRANCHISE_ARTISTS[cat].length === 0) {
    dismissMegaMenu();
    return;
  }
  if (currentHoverCat !== cat) {
    activeRailIndex = 0;
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
  activeRailIndex = 0;
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
  if (cat === activeFilter && isMegaMenuPinned) {
    dismissMegaMenu();
    return;
  }

  if (typeof setFilter === 'function') setFilter(cat);

  if (cat !== 'All' && FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].length > 0) {
    isMegaMenuPinned = true;
    currentHoverCat = cat;
    activeRailIndex = 0;
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
  activeRailIndex = index;
  renderMegaMenu(currentHoverCat || activeFilter);
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
  activeFilter = cat;
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

  // Retrieve or synthesize master categories
  const rawSections = (MEGA_MENU_CATEGORIES && MEGA_MENU_CATEGORIES[cat]) ? [...MEGA_MENU_CATEGORIES[cat]] : [];
  
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
  if (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].length > 0) {
    const allAlphabetical = [...FRANCHISE_ARTISTS[cat]].sort((a, b) => a.localeCompare(b));
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

  // Safety guard for active rail selection
  if (activeRailIndex >= railItems.length) {
    activeRailIndex = 0;
  }
  const currentRail = railItems[activeRailIndex] || railItems[0];

  // Resolve Featured Showcase Product
  let showcaseProduct = allProducts.find(p => {
    const matchesFranchise = (p.category === cat || (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].includes(p.artist)));
    const matchesSection = currentRail ? currentRail.units.includes(p.artist) : true;
    return matchesFranchise && matchesSection && typeof isPreOrder === 'function' && isPreOrder(p);
  });

  if (!showcaseProduct) {
    showcaseProduct = allProducts.find(p => {
      const matchesFranchise = (p.category === cat || (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].includes(p.artist)));
      return matchesFranchise && typeof isPreOrder === 'function' && isPreOrder(p);
    });
  }

  if (!showcaseProduct) {
    showcaseProduct = allProducts.find(p => (p.category === cat || (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].includes(p.artist))));
  }

  // ZONE 1: Left Master Sidebar Rail
  let railHtml = `
    <div class="w-full md:w-1/4 lg:w-[22%] bg-stone-50/80 dark:bg-slate-800/60 p-2.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col gap-1 shrink-0">
      <div class="px-2 py-1 mb-1 border-b border-stone-200/60 dark:border-slate-700/60 flex items-center justify-between">
        <span class="text-[10px] font-black uppercase tracking-wider text-stone-500 dark:text-slate-400">Directory Index</span>
        <span class="text-[9px] font-mono text-stone-400 dark
