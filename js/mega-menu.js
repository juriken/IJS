/* ==========================================================================
   IdolJapan.store — Mega-Menu Desktop Interaction & IA Physics
   Path: js/mega-menu.js
   ========================================================================== */

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
  currentHoverCat = cat;
  renderMegaMenu(cat);
  openMegaMenu();
}

function handleTopNavLeave() {
  if (isMegaMenuPinned) return;
  if (megaMenuTimer) clearTimeout(megaMenuTimer);
  megaMenuTimer = setTimeout(() => {
    dismissMegaMenu();
  }, 180);
}

function handleMegaMenuEnter() {
  if (megaMenuTimer) {
    clearTimeout(megaMenuTimer);
    megaMenuTimer = null;
  }
}

function handleMegaMenuLeave() {
  if (isMegaMenuPinned) return;
  if (megaMenuTimer) clearTimeout(megaMenuTimer);
  megaMenuTimer = setTimeout(() => {
    dismissMegaMenu();
  }, 180);
}

function openMegaMenu() {
  const flyout = document.getElementById('mega-menu-flyout');
  const backdrop = document.getElementById('mega-menu-backdrop');
  if (flyout) flyout.classList.remove('hidden');
  if (backdrop) backdrop.classList.remove('hidden');
}

function dismissMegaMenu() {
  const flyout = document.getElementById('mega-menu-flyout');
  const backdrop = document.getElementById('mega-menu-backdrop');
  if (flyout) flyout.classList.add('hidden');
  if (backdrop) backdrop.classList.add('hidden');
  currentHoverCat = null;
  isMegaMenuPinned = false;
  updatePinnedBadge();
}

function updatePinnedBadge() {
  const pinnedTag = document.getElementById('mega-menu-pinned-tag');
  if (!pinnedTag) return;
  if (isMegaMenuPinned) pinnedTag.classList.remove('hidden');
  else pinnedTag.classList.add('hidden');
}

function onTier1Click(cat) {
  if (cat === activeFilter && isMegaMenuPinned) {
    dismissMegaMenu();
    return;
  }

  if (typeof setFilter === 'function') setFilter(cat);

  if (cat !== 'All' && FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].length > 0) {
    isMegaMenuPinned = true;
    currentHoverCat = cat;
    renderMegaMenu(cat);
    openMegaMenu();
    updatePinnedBadge();
  } else {
    dismissMegaMenu();
  }
}

function filterMegaMenuLinks(query) {
  const q = (query || '').toLowerCase().trim();
  const links = document.querySelectorAll('.mega-menu-item-link');
  links.forEach(el => {
    const text = el.dataset.name || '';
    if (!q || text.includes(q)) {
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  });
}

function selectSubArtistFromMegaMenu(cat, unit) {
  activeFilter = cat;
  if (typeof setSubArtist === 'function') setSubArtist(unit);
  if (typeof updateFilterButtonsUI === 'function') updateFilterButtonsUI();
  dismissMegaMenu();
}

function setHpSoloistSubfilter(mode) {
  hpSoloistSubfilter = mode;
  renderMegaMenu('Hello! Project & Up-Front');
}

function setHpGradViewMode(mode) {
  hpGradViewMode = mode;
  renderMegaMenu('Hello! Project & Up-Front');
}

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

  const categories = MEGA_MENU_CATEGORIES[cat];
  const needsSpotlight = ['=LOVE / Sister Groups', 'KAWAII LAB.', 'Stardust Planet'].includes(cat);

  // 4-Column Hello! Project & Up-Front Architecture
  if (cat === 'Hello! Project & Up-Front') {
    columnsContainer.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 text-xs";
    let html = '';

    categories.forEach(col => {
      let extraHeaderControls = '';

      if (col.isSoloistColumn) {
        extraHeaderControls = `
          <div class="flex items-center gap-1 mt-1 text-[9px] font-bold">
            <button onclick="setHpSoloistSubfilter('all')" class="px-1.5 py-0.5 rounded ${hpSoloistSubfilter === 'all' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">All</button>
            <button onclick="setHpSoloistSubfilter('mline')" class="px-1.5 py-0.5 rounded ${hpSoloistSubfilter === 'mline' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">M-line</button>
            <button onclick="setHpSoloistSubfilter('classic')" class="px-1.5 py-0.5 rounded ${hpSoloistSubfilter === 'classic' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">Classic</button>
          </div>
        `;
      } else if (col.isGraduateColumn) {
        extraHeaderControls = `
          <div class="flex items-center gap-1 mt-1 text-[9px] font-bold">
            <button onclick="setHpGradViewMode('group')" class="px-1.5 py-0.5 rounded ${hpGradViewMode === 'group' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">Group View</button>
            <button onclick="setHpGradViewMode('era')" class="px-1.5 py-0.5 rounded ${hpGradViewMode === 'era' ? 'bg-rose-600 text-white' : 'bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-300'}">Era View</button>
          </div>
        `;
      }

      html += `
        <div class="bg-stone-50/70 dark:bg-slate-800/50 p-3 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col max-h-[420px] overflow-y-auto no-scrollbar">
          <div class="sticky top-0 bg-stone-50/95 dark:bg-slate-800/95 backdrop-blur-xs pb-1 mb-2 border-b border-stone-200/50 dark:border-slate-700/60 z-10">
            <h4 class="font-black text-stone-800 dark:text-stone-200 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
              <i class="fa-solid ${col.icon}"></i> ${escapeHtml(col.title)}
            </h4>
            ${extraHeaderControls}
          </div>
          <div class="space-y-1">
      `;

      if (col.isGraduateColumn) {
        col.clusters.forEach(clust => {
          html += `<div class="pt-1.5 pb-0.5 text-[10px] font-bold uppercase text-stone-400 dark:text-slate-400 border-t border-stone-200/40 dark:border-slate-700/40 first:border-0">${clust.parent}</div>`;
          clust.units.forEach(u => {
            html += renderMegaMenuUnitRow(cat, u);
          });
        });
      } else {
        let filteredUnits = col.units;
        if (col.isSoloistColumn) {
          if (hpSoloistSubfilter === 'mline') {
            filteredUnits = ['Airi Suzuki', 'Sayumi Michishige', 'Karin Miyamoto', 'Masaki Sato', 'Riho Sayashi', 'Manaka Inaba', 'Reina Tanaka', 'Ai Takahashi'];
          } else if (hpSoloistSubfilter === 'classic') {
            filteredUnits = ['Aya Matsuura', 'Maki Goto', 'Natsumi Abe', 'Yuko Nakazawa', 'Miki Fujimoto', 'Erina Mano', 'Tsukishima Kirari'];
          }
        }
        filteredUnits.forEach(u => {
          html += renderMegaMenuUnitRow(cat, u);
        });
      }

      html += `</div></div>`;
    });

    columnsContainer.innerHTML = html;
    return;
  }

  // Compact Layouts with Featured Pre-Order Spotlight Card
  if (needsSpotlight) {
    columnsContainer.className = "grid grid-cols-1 lg:grid-cols-4 gap-4 text-xs";
    
    const franchisePreOrder = allProducts.find(p => {
      const matchFr = (p.category === cat || (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].includes(p.artist)));
      return matchFr && typeof isPreOrder === 'function' && isPreOrder(p);
    }) || allProducts.find(p => (FRANCHISE_ARTISTS[cat] && FRANCHISE_ARTISTS[cat].includes(p.artist)));

    let leftColsHtml = '<div class="lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">';
    categories.forEach(sec => {
      leftColsHtml += `
        <div class="bg-stone-50/70 dark:bg-slate-800/50 p-3 rounded-2xl border border-stone-200/60 dark:border-slate-800 max-h-[380px] overflow-y-auto no-scrollbar">
          <h4 class="font-black text-stone-800 dark:text-stone-200 text-[11px] uppercase tracking-wider mb-2 pb-1 border-b border-stone-200/50 dark:border-slate-700/60 flex items-center gap-1.5">
            <i class="fa-solid ${sec.icon}"></i> ${escapeHtml(sec.title)}
          </h4>
          <div class="space-y-1">
            ${sec.units.map(u => renderMegaMenuUnitRow(cat, u)).join('')}
          </div>
        </div>
      `;
    });
    leftColsHtml += '</div>';

    // Right 25% Spotlight Card
    let spotlightHtml = '';
    if (franchisePreOrder) {
      const sTitle = escapeHtml(stripTitlePrefixes(franchisePreOrder.title));
      spotlightHtml = `
        <div class="bg-gradient-to-br from-rose-50 to-pink-50 dark:from-slate-800 dark:to-slate-800/80 border border-rose-200 dark:border-slate-700 p-3.5 rounded-2xl flex flex-col justify-between">
          <div>
            <span class="inline-block text-[9px] font-black uppercase tracking-wider bg-rose-600 text-white px-2 py-0.5 rounded-full mb-2">
              Featured Pre-Order
            </span>
            <div class="aspect-square bg-white dark:bg-slate-900 rounded-xl overflow-hidden mb-2.5 p-2 shadow-2xs flex items-center justify-center">
              <img src="${getThumbnailUrl(franchisePreOrder.image)}" class="w-full h-full object-contain" onerror="onImgLoadError(this)" />
            </div>
            <h4 class="font-bold text-xs text-stone-900 dark:text-white line-clamp-2">${sTitle}</h4>
            <p class="text-[10px] text-rose-600 dark:text-rose-400 font-bold mt-1">${escapeHtml(franchisePreOrder.artist)}</p>
            <p class="text-[10px] text-stone-500 dark:text-slate-400"><i class="fa-regular fa-clock mr-1"></i>${franchisePreOrder.release_date || 'Upcoming Street Date'}</p>
          </div>
          <button onclick="triggerOutboundAffiliate(allProducts.find(x => x.id === '${franchisePreOrder.id}'), 'spotlight_card')" class="mt-3 w-full py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-center text-xs shadow-xs cursor-pointer">
            Pre-Order on CDJapan →
          </button>
        </div>
      `;
    } else {
      spotlightHtml = `<div class="bg-stone-50 dark:bg-slate-800 p-3 rounded-2xl border border-stone-200 dark:border-slate-700 flex items-center justify-center text-stone-400 text-xs">Direct CDJapan Partner Inventory</div>`;
    }

    columnsContainer.innerHTML = leftColsHtml + spotlightHtml;
    return;
  }

  // Default Standard Grid
  columnsContainer.className = "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5 text-xs";
  let html = '';
  categories.forEach(sec => {
    html += `
      <div class="bg-stone-50/70 dark:bg-slate-800/50 p-3.5 rounded-2xl border border-stone-200/60 dark:border-slate-800 flex flex-col max-h-[380px] overflow-y-auto no-scrollbar">
        <h4 class="font-black text-stone-800 dark:text-stone-200 text-[11px] uppercase tracking-wider mb-2 pb-1 border-b border-stone-200/40 dark:border-slate-700/50 flex items-center gap-1.5">
          <i class="fa-solid ${sec.icon}"></i> ${escapeHtml(sec.title)}
        </h4>
        <div class="space-y-1">
    `;

    if (sec.units && sec.units.length > 0) {
      sec.units.forEach(u => {
        html += renderMegaMenuUnitRow(cat, u);
      });
    } else if (sec.placeholderText) {
      html += `<p class="text-[11px] text-stone-400 dark:text-slate-500 leading-relaxed py-2">${escapeHtml(sec.placeholderText)}</p>`;
    }

    html += `</div></div>`;
  });

  columnsContainer.innerHTML = html;
}

function renderMegaMenuUnitRow(cat, unitName) {
  const isSelected = (activeArtist === unitName);
  const count = allProducts.filter(p => p.artist === unitName).length;
  const brandColor = ARTIST_BRAND_COLORS[unitName] || '#94a3b8';
  const hasPreOrder = allProducts.some(p => p.artist === unitName && typeof isPreOrder === 'function' && isPreOrder(p));

  return `
    <button 
      onclick="selectSubArtistFromMegaMenu('${cat}', '${escapeHtml(unitName)}')" 
      data-name="${unitName.toLowerCase()}"
      class="mega-menu-item-link w-full text-left px-2 py-1 rounded-lg transition flex items-center justify-between text-xs cursor-pointer ${isSelected ? 'bg-rose-600 text-white font-bold shadow-2xs' : 'text-stone-700 dark:text-stone-300 hover:bg-rose-50 dark:hover:bg-slate-700 hover:text-rose-600'}"
    >
      <div class="flex items-center gap-2 truncate">
        <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background-color: ${brandColor}"></span>
        <span class="truncate">${escapeHtml(unitName)}</span>
        ${hasPreOrder ? '<span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" title="Active Pre-Orders Available"></span>' : ''}
      </div>
      <span class="text-[10px] ${isSelected ? 'text-white/80' : 'text-stone-400 dark:text-slate-500'} ml-1 font-mono">${count}</span>
    </button>
  `;
}
