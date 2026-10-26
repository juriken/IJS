/* ==========================================================================
   IdolJapan.store — Core Application Runtime, Catalog Engine & View Pipeline
   Path: js/app.js
   ========================================================================== */

function parseNumericPrice(priceStr, item) {
  if (item && item.price_num) return item.price_num;
  if (!priceStr) return 0;
  const clean = String(priceStr).replace(/[^0-9]/g, '');
  return parseInt(clean, 10) || 0;
}

function formatDisplayPrice(priceStr, item) {
  const jpyAmount = parseNumericPrice(priceStr, item);
  if (jpyAmount === 0) return 'Check CDJapan';

  if (currentCurrency === 'JPY') {
    return `¥${jpyAmount.toLocaleString()}`;
  }

  const usdPerJpy = (exchangeRates['JPY'] && exchangeRates['JPY'] > 0) ? (1 / exchangeRates['JPY']) : (1 / 152.4);
  const targetRate = exchangeRates[currentCurrency] || 1.0;
  const convertedVal = jpyAmount * usdPerJpy * targetRate;

  const zeroDecimalCurrencies = ['KRW', 'VND', 'IDR', 'CLP', 'HUF', 'TWD'];
  const fractionDigits = zeroDecimalCurrencies.includes(currentCurrency) ? 0 : 2;

  let formattedConverted = '';
  try {
    formattedConverted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currentCurrency,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits
    }).format(convertedVal);
  } catch (e) {
    formattedConverted = `${currentCurrency} ${convertedVal.toFixed(fractionDigits)}`;
  }

  return `${formattedConverted} <span class="text-[9px] text-stone-400 dark:text-slate-500 font-normal">(¥${jpyAmount.toLocaleString()})</span>`;
}

function getItemDateValue(item) {
  if (!item) return 0;
  const dStr = String(item.release_date || '').trim();
  if (!dStr || dStr.toLowerCase().includes('available now')) return 0;

  const m = dStr.match(/\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b/);
  if (m) {
    const y = parseInt(m[1], 10);
    const mon = parseInt(m[2], 10);
    const day = parseInt(m[3], 10);
    if (day <= 31 && mon <= 12) return (y * 10000) + (mon * 100) + day;
  }

  const en = dStr.match(/\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b/);
  if (en) {
    const monKey = en[1].toLowerCase();
    if (EN_MONTHS[monKey]) {
      const mon = EN_MONTHS[monKey];
      const day = parseInt(en[2], 10);
      const y = parseInt(en[3], 10);
      return (y * 10000) + (mon * 100) + day;
    }
  }

  const ym = dStr.match(/\b(19\d\d|20\d\d)[./-](\d{1,2})\b/);
  if (ym) {
    const y = parseInt(ym[1], 10);
    const mon = parseInt(ym[2], 10);
    return (y * 10000) + (mon * 100) + 1;
  }

  return 0;
}

function getClusterEffectiveDateValue(cluster) {
  if (!cluster) return 0;
  const variants = cluster._activeVariants || cluster.variants || (cluster._primary ? [cluster._primary] : []);
  if (!variants.length) return 0;
  let maxVal = 0;
  for (const v of variants) {
    const val = getItemDateValue(v);
    if (val > maxVal) maxVal = val;
  }
  return maxVal;
}

function getItemYear(item) {
  const val = getItemDateValue(item);
  if (val === 0) return 0;
  return Math.floor(val / 10000);
}

function isOutOfPrint(item) {
  if (!item) return false;
  if (item.availability === 'oop') return true;
  const priceStr = String(item.price || '').toLowerCase();
  const titleStr = String(item.title || '').toLowerCase();
  return (
    priceStr.includes('no longer available') ||
    priceStr.includes('out of print') ||
    priceStr.includes('discontinued') ||
    priceStr.includes('sold out') ||
    priceStr.includes('廃盤') ||
    priceStr.includes('取扱終了') ||
    titleStr.includes('secondhand') ||
    titleStr.includes('used [') ||
    (item.price_num === 0 && !priceStr.includes('check cdjapan'))
  );
}

function isPreOrder(item) {
  if (!item || isOutOfPrint(item)) return false;
  if (item.availability === 'preorder') return true;
  const val = getItemDateValue(item);
  if (val === 0) return false;

  const today = new Date();
  const todayVal = (today.getFullYear() * 10000) + ((today.getMonth() + 1) * 100) + today.getDate();
  return val > todayVal;
}

function isInStock(item) {
  return !isOutOfPrint(item) && !isPreOrder(item);
}

function getCleanBaseTitle(title) {
  if (!title) return '';
  let clean = stripTitlePrefixes(title);
  clean = clean.replace(/\s*w\/\s*(?:7net|Amazon|Asmart|Tower Records|Rakuten Books|AKB48 Official Shop|[A-Za-z0-9\s]+Bonus|Tokuten).*$/i, '');
  clean = clean.replace(/\[Bundled Set.*?\]/gi, '');
  clean = clean.replace(/\s*DAY\s*\d+/gi, '');
  clean = clean.replace(/\[.*?Edition.*?\]/gi, '');
  clean = clean.replace(/\[.*?ver\..*?\]/gi, '');
  clean = clean.replace(/\[.*?盤.*?\]/gi, '');
  clean = clean.replace(/\[(?:Cardboard Sleeve|Blu-ray|DVD|CD|First Press|Limited|Regular|Special).*?\]/gi, '');
  clean = clean.replace(/\((?:Type\s*[A-Z0-9]+|w\/\s*[A-Za-z0-9\s]+|Regular Edition|Limited Edition|CD\s*\+\s*Blu-ray|CD\s*\+\s*DVD)\)/gi, '');
  clean = clean.replace(/【.*?】/g, '');
  clean = clean.replace(/(?:\s*[\(\[【]?\s*(?:¥\s*[\d,]+|[\d,]+\s*(?:yen|JPY))\s*(?:\([^)]*\)|（[^）]*）|tax\s*(?:incl|included|\.|\s*in)?|税込)?\s*[\)\]】]?)+$/gi, '');
  return clean.replace(/\s+/g, ' ').trim();
}

function buildClusteredEntities() {
  const clusters = {};
  allProducts.forEach(item => {
    const cleanTitle = getCleanBaseTitle(item.title).toLowerCase();
    const baseKey = `${item.artist || ''}__${cleanTitle}`;
    if (!clusters[baseKey]) {
      clusters[baseKey] = {
        id: item.id,
        canonicalItem: item,
        variants: [item]
      };
    } else {
      clusters[baseKey].variants.push(item);
    }
  });
  clusteredEntities = Object.values(clusters);
}

function getItemFormatCategory(item) {
  if (!item) return 'Other';
  const pid = String(item.id || '').toUpperCase();
  const title = String(item.title || '').toLowerCase();

  if (
    pid.startsWith('NEOBK-') ||
    title.includes('photobook') ||
    title.includes('photo book') ||
    title.includes('visual book') ||
    title.includes('magazine') ||
    title.includes('official book') ||
    title.includes('mook') ||
    title.includes('score') ||
    title.includes('写真集') ||
    title.includes('ムック')
  ) {
    return 'Book';
  }

  if (
    pid.startsWith('SRXL') ||
    pid.startsWith('SRXW') ||
    pid.startsWith('EPXE') ||
    pid.startsWith('KIXM') ||
    pid.startsWith('TFXQ') ||
    pid.startsWith('UMXK') ||
    pid.startsWith('VVXL') ||
    pid.startsWith('HKXN') ||
    pid.startsWith('AVXD') ||
    pid.startsWith('VPXF') ||
    pid.startsWith('UFXW') ||
    pid.startsWith('TGXF') ||
    pid.startsWith('BMWR-1008') ||
    pid.startsWith('BMWR-1009') ||
    (title.includes('blu-ray') && !title.includes('cd +') && !title.includes('w/ blu-ray'))
  ) {
    return 'Blu-ray';
  }

  if (
    pid.startsWith('SRBL') ||
    pid.startsWith('EPBE') ||
    pid.startsWith('KIBM') ||
    pid.startsWith('TFBQ') ||
    pid.startsWith('UMBK') ||
    pid.startsWith('VVBL') ||
    pid.startsWith('HKBN') ||
    pid.startsWith('AVBD') ||
    pid.startsWith('VPBF') ||
    pid.startsWith('PKBP') ||
    pid.startsWith('UFBW') ||
    pid.startsWith('TGBS') ||
    pid.startsWith('BMWR-1010') ||
    (title.includes('dvd') && !title.includes('cd +') && !title.includes('w/ dvd'))
  ) {
    return 'DVD';
  }

  if (
    title.startsWith('album cd') ||
    title.startsWith('cd album') ||
    title.includes('album [') ||
    title.includes('best album') ||
    title.includes('original album') ||
    title.includes('mini album') ||
    title.includes('アルバム')
  ) {
    return 'Album';
  }

  if (
    title.startsWith('single cd') ||
    title.startsWith('cd single') ||
    title.includes('single [') ||
    title.includes('maxi single') ||
    title.includes('シングル')
  ) {
    return 'Single';
  }

  if (
    pid.startsWith('NEODAI-') ||
    pid.startsWith('NEOODY-') ||
    pid.startsWith('NEOGDS-') ||
    pid.startsWith('DCFGDS-') ||
    pid.startsWith('DAKUFBW-') ||
    pid.includes('CL-') ||
    pid.endsWith('-A') ||
    title.includes('apparel') ||
    title.includes('collectible') ||
    title.includes('t-shirt') ||
    title.includes('shirt') ||
    title.includes('calendar') ||
    title.includes('acrylic') ||
    title.includes('keychain') ||
    title.includes('stand') ||
    title.includes('goods') ||
    title.includes('towel') ||
    title.includes('badge') ||
    title.includes('plate') ||
    title.includes('sticker') ||
    title.includes('pouch')
  ) {
    return 'Collectable';
  }

  if (
    pid.startsWith('SRCL') || pid.startsWith('EPCE') || pid.startsWith('HKCN') ||
    pid.startsWith('UPCH') || pid.startsWith('KICS') || pid.startsWith('KICM') ||
    pid.startsWith('AVCD') || pid.startsWith('TFCC') || pid.startsWith('VVCL') ||
    pid.startsWith('YRCS') || pid.startsWith('PKCP') || pid.startsWith('AICL') ||
    pid.startsWith('KLC-') || pid.startsWith('NEOIKT-')
  ) {
    return 'Single';
  }

  return 'Other';
}

function getMerchSubgroupType(item) {
  const title = String(item.title || '').toLowerCase();
  if (title.includes('acrylic') || title.includes('stand') || title.includes('アクスタ') || title.includes('アクリル')) return 'acrylic';
  if (title.includes('shirt') || title.includes('apparel') || title.includes('parka') || title.includes('tシャツ')) return 'apparel';
  if (title.includes('keychain') || title.includes('strap') || title.includes('holder') || title.includes('キーホルダー')) return 'keychain';
  if (title.includes('badge') || title.includes('pin') || title.includes('缶バッジ')) return 'badge';
  if (title.includes('towel') || title.includes('penlight') || title.includes('blade') || title.includes('タオル') || title.includes('ペンライト')) return 'towel';
  if (title.includes('sticker') || title.includes('poster') || title.includes('plate') || title.includes('file') || title.includes('folder')) return 'stationery';
  return 'other';
}

function setMerchSubgroup(subgroup) {
  activeMerchSubgroup = subgroup;
  currentPage = 1;
  document.querySelectorAll('.merch-sub-btn').forEach(btn => {
    if (btn.dataset.sub === subgroup) {
      btn.className = "merch-sub-btn px-2 py-0.5 rounded-md transition bg-purple-600 text-white cursor-pointer";
    } else {
      btn.className = "merch-sub-btn px-2 py-0.5 rounded-md transition bg-stone-100 dark:bg-slate-800 text-stone-700 dark:text-stone-300 hover:bg-purple-50 cursor-pointer";
    }
  });
  render();
}

function updateDynamicCounts() {
  const catCounts = {
    'All': allProducts.length,
    'Hello! Project & Up-Front': 0,
    'AKB48 Group': 0,
    'Sakamichi Series': 0,
    'Stardust Planet': 0,
    '=LOVE / Sister Groups': 0,
    'KAWAII LAB.': 0,
    'Modern & Alternative': 0
  };

  const fmtCounts = {
    'All': allProducts.length,
    'Single': 0,
    'Album': 0,
    'Blu-ray': 0,
    'DVD': 0,
    'Book': 0,
    'Collectable': 0
  };

  allProducts.forEach(item => {
    const cat = item.category || '';
    const art = item.artist || '';

    /* File: js/app.js | Block/Target: updateDynamicCounts Hello! Project variations */
    if (cat === 'Hello! Project & Up-Front' || cat === 'Hello! Project' || cat === 'Up-Front Alumni') {
      catCounts['Hello! Project & Up-Front']++;
    } else if (cat === 'AKB48 Group') {
      catCounts['AKB48 Group']++;
    } else if (cat === 'Sakamichi Series') {
      catCounts['Sakamichi Series']++;
    } else if (cat === 'Stardust Planet' || cat === 'Momoiro Clover Z') {
      catCounts['Stardust Planet']++;
    } else if (cat === '=LOVE / Sister Groups') {
      catCounts['=LOVE / Sister Groups']++;
    } else if (cat === 'KAWAII LAB.') {
      catCounts['KAWAII LAB.']++;
    } else if (
      /* File: js/app.js | Block/Target: updateDynamicCounts Modern & Alternative String Match */
      cat === 'Modern & Alternative' || cat === 'Modern Idols' || cat === 'Babymetal' ||
      art === 'BABYMETAL' || art === 'Sakura Gakuin' ||
      art === 'NiziU' || art === 'ME:I' || art === 'IS:SUE'
    ) {
      catCounts['Modern & Alternative']++;
    }

    const fmt = getItemFormatCategory(item);
    if (fmtCounts[fmt] !== undefined) fmtCounts[fmt]++;
  });

  Object.entries(catCounts).forEach(([catKey, count]) => {
    const badge = document.getElementById(`badge-cat-${catKey}`);
    if (badge) badge.innerText = count.toLocaleString();
  });

  Object.entries(fmtCounts).forEach(([fmt, count]) => {
    const badge = document.getElementById(`badge-fmt-${fmt}`);
    if (badge) badge.innerText = `(${count.toLocaleString()})`;
  });
}

function changeSort(sortVal) {
  currentSort = sortVal;
  const dSelect = document.getElementById('sort-select');
  if (dSelect) dSelect.value = sortVal;
  currentPage = 1;
  syncUrlParams();
  render();
}

function changePerPage(countVal) {
  itemsPerPage = parseInt(countVal, 10) || 48;
  currentPage = 1;
  render();
}

function goToPage(pageNumber) {
  const totalPages = Math.max(1, Math.ceil(activeFilteredList.length / itemsPerPage));
  const targetPage = Math.max(1, Math.min(pageNumber || 1, totalPages));
  currentPage = targetPage;

  const pageInput = document.getElementById('direct-page-input');
  if (pageInput) pageInput.value = currentPage;

  syncUrlParams();
  render();
  const anchor = document.getElementById('pagination-top-anchor');
  if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setFilter(cat) {
  activeFilter = cat;
  activeArtist = 'All';
  activeMobileArtists = [];
  activeEra = 'All';
  currentPage = 1;
  updateFilterButtonsUI();
  updateActiveArtistBanner();
  updateMobileDrawerContent();
  syncUrlParams();
  render();
}

function setSubArtist(artist) {
  activeArtist = artist;
  activeMobileArtists = [artist];
  activeEra = 'All';
  currentPage = 1;

  if (artist !== 'All' && selectedAvailabilities.has('instock') && selectedAvailabilities.size === 1) {
    const inStockCount = allProducts.filter(p => p.artist === artist && !isOutOfPrint(p)).length;
    if (inStockCount === 0) {
      selectedAvailabilities = new Set(['all']);
      updateAvailabilityPillsUI();
      showToast(`Showing complete discography archive for ${artist}`);
    }
  }

  updateActiveArtistBanner();
  updateMobileDrawerContent();
  syncUrlParams();
  render();
}

function setFormat(fmt) {
  activeFormat = fmt;
  activeMerchSubgroup = 'All';
  currentPage = 1;

  const merchBar = document.getElementById('merch-subgroup-bar');
  if (merchBar) {
    if (fmt === 'Collectable') merchBar.classList.remove('hidden');
    else merchBar.classList.add('hidden');
  }

  updateFilterButtonsUI();
  updateMobileDrawerContent();
  syncUrlParams();
  render();
}

function toggleAvailabilityMode(status) {
  if (status === 'all') {
    selectedAvailabilities = new Set(['all']);
  } else {
    selectedAvailabilities.delete('all');
    if (selectedAvailabilities.has(status)) {
      selectedAvailabilities.delete(status);
    } else {
      selectedAvailabilities.add(status);
    }
    if (selectedAvailabilities.size === 0) {
      selectedAvailabilities.add('all');
    }
  }
  currentPage = 1;
  updateAvailabilityPillsUI();
  syncUrlParams();
  render();
}

function updateAvailabilityPillsUI() {
  const activeClass = "px-2 py-0.5 rounded-md transition bg-white dark:bg-slate-700 text-rose-600 dark:text-white shadow-2xs font-bold cursor-pointer";
  const inactiveClass = "px-2 py-0.5 rounded-md transition hover:text-rose-600 dark:hover:text-white font-semibold cursor-pointer";

  const pills = {
    'all': document.getElementById('avail-pill-all'),
    'instock': document.getElementById('avail-pill-instock'),
    'preorder': document.getElementById('avail-pill-preorder'),
    'oop': document.getElementById('avail-pill-oop')
  };

  Object.entries(pills).forEach(([key, el]) => {
    if (!el) return;
    el.className = selectedAvailabilities.has(key) ? activeClass : inactiveClass;
  });
}

function updateFilterButtonsUI() {
  document.querySelectorAll('#filter-bar .tab-btn').forEach(btn => {
    const isSelected = btn.dataset.cat === activeFilter;
    btn.setAttribute('aria-expanded', isSelected ? 'true' : 'false');
    if (isSelected) {
      btn.className = "tab-btn px-2 py-1.5 rounded-xl text-xs font-bold transition bg-rose-600 text-white shadow-xs flex items-center justify-between cursor-pointer focus-visible:ring-2 focus-visible:ring-rose-400";
    } else {
      btn.className = "tab-btn px-2 py-1.5 rounded-xl text-xs font-bold transition bg-stone-100 dark:bg-slate-800 text-stone-700 dark:text-slate-300 hover:bg-rose-50 dark:hover:bg-slate-700 flex items-center justify-between cursor-pointer border border-stone-200/50 dark:border-slate-700/50 focus-visible:ring-2 focus-visible:ring-rose-400";
    }
  });

  document.querySelectorAll('#format-filter-bar .fmt-btn').forEach(btn => {
    if (btn.dataset.fmt === activeFormat) {
      btn.className = "fmt-btn px-2 py-0.5 rounded-md transition bg-rose-600 text-white font-bold shadow-2xs shrink-0 cursor-pointer";
    } else {
      btn.className = "fmt-btn px-2 py-0.5 rounded-md transition bg-white dark:bg-slate-800 text-stone-600 dark:text-slate-300 hover:bg-rose-50 dark:hover:bg-slate-700 border border-stone-200 dark:border-slate-700 shrink-0 cursor-pointer";
    }
  });
}

function updateActiveArtistBanner() {
  const banner = document.getElementById('active-artist-banner');
  const label = document.getElementById('active-artist-label');
  if (!banner || !label) return;

  const hasArtist = (activeArtist !== 'All' || activeMobileArtists.length > 0);
  const hasEra = (activeEra !== 'All');

  if (hasArtist || hasEra) {
    let html = '';
    if (hasArtist) {
      const displayTxt = activeArtist !== 'All' ? activeArtist : `${activeMobileArtists.length} Selected Groups`;
      html += `
        <span class="bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 px-2.5 py-0.5 rounded-full font-bold text-xs flex items-center gap-1.5 shadow-2xs">
          <span>${escapeHtml(displayTxt)}</span>
          <button onclick="setSubArtist('All'); clearMobileSelectedArtists();" title="Clear artist filter" class="hover:text-rose-950 dark:hover:text-white cursor-pointer ml-1">
            <i class="fa-solid fa-xmark text-[10px]"></i>
          </button>
        </span>
      `;
    }
    if (hasEra) {
      html += `
        <span class="bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 px-2.5 py-0.5 rounded-full font-bold text-xs flex items-center gap-1.5 shadow-2xs">
          <span>Era: ${escapeHtml(activeEra)}</span>
          <button onclick="setEraFilter('All')" title="Clear era filter" class="hover:text-amber-950 dark:hover:text-white cursor-pointer ml-1">
            <i class="fa-solid fa-xmark text-[10px]"></i>
          </button>
        </span>
      `;
    }
    label.innerHTML = html;
    banner.classList.remove('hidden');
  } else {
    banner.classList.add('hidden');
  }
}

function resetAllFilters() {
  activeFilter = 'All';
  activeArtist = 'All';
  activeMobileArtists = [];
  activeEra = 'All';
  activeFormat = 'All';
  activeMerchSubgroup = 'All';
  selectedAvailabilities = new Set(['all']);
  maxPriceLimit = 20000;
  searchQuery = '';
  currentPage = 1;

  const pRange = document.getElementById('price-range');
  if (pRange) pRange.value = 20000;
  const pLabel = document.getElementById('price-range-label');
  if (pLabel) pLabel.innerText = 'Any';

  const eraSelect = document.getElementById('era-select');
  if (eraSelect) eraSelect.value = 'All';

  const merchBar = document.getElementById('merch-subgroup-bar');
  if (merchBar) merchBar.classList.add('hidden');

  const input = document.getElementById('search-input');
  if (input) input.value = '';
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.classList.add('hidden');
  closeAutocomplete();

  dismissMegaMenu();
  updateFilterButtonsUI();
  updateAvailabilityPillsUI();
  updateActiveArtistBanner();
  updateWishlistBadge();
  updateMobileDrawerContent();
  syncUrlParams();
  render();
}

function setEraFilter(eraVal) {
  activeEra = eraVal;
  currentPage = 1;
  const select = document.getElementById('era-select');
  if (select) select.value = eraVal;
  updateActiveArtistBanner();
  syncUrlParams();
  render();
}

function syncUrlParams() {
  const params = new URLSearchParams();
  if (activeFilter !== 'All') params.set('cat', activeFilter);
  if (activeArtist !== 'All') params.set('artist', activeArtist);
  if (activeEra !== 'All') params.set('era', activeEra);
  if (activeFormat !== 'All') params.set('fmt', activeFormat);
  if (selectedAvailabilities.size > 0 && !selectedAvailabilities.has('all')) {
    params.set('status', Array.from(selectedAvailabilities).join(','));
  }
  if (searchQuery) params.set('q', searchQuery);
  if (currentSort !== 'newest') params.set('sort', currentSort);
  if (currentPage > 1) params.set('page', currentPage);

  const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', newUrl);
  updatePageTitle();
}

function updatePageTitle() {
  let baseTitle = "IdolJapan.store — Official Japanese Idol Discography";
  if (activeFilter !== 'All') {
    baseTitle = `${activeFilter} Discography — IdolJapan.store`;
  }
  if (activeArtist !== 'All') {
    baseTitle = `${activeArtist} CDJapan Releases — IdolJapan.store`;
  }
  document.title = baseTitle;
}

function readUrlParams() {
  const params = new URLSearchParams(window.location.search);
  if (params.has('cat')) activeFilter = params.get('cat');
  if (params.has('artist')) activeArtist = params.get('artist');
  if (params.has('era')) activeEra = params.get('era');
  if (params.has('fmt')) activeFormat = params.get('fmt');
  if (params.has('status')) {
    const statuses = params.get('status').split(',').map(s => s.trim().toLowerCase());
    selectedAvailabilities = new Set(statuses);
  }
  if (params.has('q')) {
    searchQuery = params.get('q').toLowerCase();
    const input = document.getElementById('search-input');
    if (input) input.value = params.get('q');
  }
  if (params.has('sort')) currentSort = params.get('sort');
  if (params.has('page')) currentPage = parseInt(params.get('page'), 10) || 1;

  if (params.has('id')) {
    const targetId = params.get('id');
    setTimeout(() => openModal(targetId), 250);
  }
  updatePageTitle();
}

function applyLayoutModeToDom() {
  layoutMode = detectDeviceLayout();
  const isMobile = (layoutMode === 'mobile');
  const viewportMeta = document.getElementById('dynamic-viewport');
  const htmlEl = document.documentElement;

  const mobileBar = document.getElementById('mobile-filter-bar');
  const mobileNav = document.getElementById('mobile-bottom-nav');
  const desktopTier1 = document.getElementById('desktop-nav-tier1');
  const desktopTier2 = document.getElementById('desktop-nav-tier2');

  if (isMobile) {
    if (viewportMeta) viewportMeta.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0';
    htmlEl.classList.remove('layout-desktop');
    htmlEl.classList.add('layout-mobile');

    if (mobileBar) mobileBar.classList.remove('hidden');
    if (mobileNav) mobileNav.classList.remove('hidden');
    if (desktopTier1) desktopTier1.classList.add('hidden');
    if (desktopTier2) desktopTier2.classList.add('hidden');
  } else {
    if (viewportMeta) viewportMeta.content = 'width=1280, initial-scale=0.3, maximum-scale=3.0, user-scalable=yes';
    htmlEl.classList.add('layout-desktop');
    htmlEl.classList.remove('layout-mobile');

    if (mobileBar) mobileBar.classList.add('hidden');
    if (mobileNav) mobileNav.classList.add('hidden');
    if (desktopTier1) desktopTier1.classList.remove('hidden');
    if (desktopTier2) desktopTier2.classList.remove('hidden');
  }

  updateMobileDrawerContent();
}

function setViewMode(mode) {
  viewMode = mode;
  localStorage.setItem(VIEW_MODE_KEY, mode);
  updateViewModeUI();
  render();
}

function updateViewModeUI() {
  const gBtn = document.getElementById('view-mode-grid');
  const lBtn = document.getElementById('view-mode-list');
  const activeClass = "px-1.5 py-0.5 rounded-md transition text-xs bg-white dark:bg-slate-700 text-rose-600 dark:text-white shadow-2xs cursor-pointer";
  const inactiveClass = "px-1.5 py-0.5 rounded-md transition text-xs text-stone-500 hover:text-stone-800 dark:hover:text-stone-200 cursor-pointer";

  if (gBtn && lBtn) {
    gBtn.className = viewMode === 'grid' ? activeClass : inactiveClass;
    lBtn.className = viewMode === 'list' ? activeClass : inactiveClass;
  }
}

function toggleClustering(checked) {
  isClusteringEnabled = checked;
  currentPage = 1;
  render();
}

function updateThemeIcon() {
  const isDark = document.documentElement.classList.contains('dark');
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.className = isDark ? 'fa-solid fa-sun text-amber-200 text-xs' : 'fa-solid fa-moon text-rose-100 text-xs';
  }
}

function toggleTheme() {
  if (document.documentElement.classList.contains('dark')) {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  } else {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  }
  updateThemeIcon();
}

async function initExchangeRates() {
  try {
    const savedCurrency = localStorage.getItem(CURRENCY_STORAGE_KEY) || (window.IdolGeo ? window.IdolGeo.applyAutoCurrency() : 'USD');
    currentCurrency = savedCurrency;

    const selectEl = document.getElementById('currency-select');
    if (selectEl) selectEl.value = currentCurrency;

    const localRes = await fetch('/rates.json').catch(() => null);
    if (localRes && localRes.ok) {
      const localData = await localRes.json().catch(() => null);
      if (localData && localData.rates) {
        exchangeRates = localData.rates;
        populateCurrencyOptions(exchangeRates);
      }
    }

    const cachedRates = localStorage.getItem(RATES_STORAGE_KEY);
    const cachedTime = localStorage.getItem(RATES_TIME_KEY);
    const now = Date.now();

    if (cachedRates && cachedTime && (now - parseInt(cachedTime, 10) < TWENTY_FOUR_HOURS_MS)) {
      exchangeRates = JSON.parse(cachedRates);
      populateCurrencyOptions(exchangeRates);
      return;
    }

    const res = await fetch('https://open.er-api.com/v6/latest/USD').catch(() => null);
    if (res && res.ok) {
      const data = await res.json().catch(() => null);
      if (data && data.rates) {
        exchangeRates = data.rates;
        localStorage.setItem(RATES_STORAGE_KEY, JSON.stringify(exchangeRates));
        localStorage.setItem(RATES_TIME_KEY, now.toString());
        populateCurrencyOptions(exchangeRates);
      }
    }
  } catch (err) {
    console.warn('Currency init completed with fallback:', err);
  }
}

function populateCurrencyOptions(rates) {
  const optGroup = document.getElementById('all-currencies-group');
  if (!optGroup || !rates) return;

  const popular = ['USD', 'JPY', 'EUR', 'GBP', 'CAD', 'AUD', 'TWD', 'HKD', 'KRW', 'SGD'];
  const allCodes = Object.keys(rates).sort();

  optGroup.innerHTML = '';
  allCodes.forEach(code => {
    if (!popular.includes(code)) {
      const opt = document.createElement('option');
      opt.value = code;
      opt.innerText = code;
      opt.className = 'text-slate-900 bg-white';
      optGroup.appendChild(opt);
    }
  });

  const selectEl = document.getElementById('currency-select');
  if (selectEl) selectEl.value = currentCurrency;
}

function onCurrencyChange(selectedCode) {
  currentCurrency = selectedCode;
  localStorage.setItem(CURRENCY_STORAGE_KEY, selectedCode);
  render();
}

function onMaxPriceChange(val) {
  const num = parseInt(val, 10);
  maxPriceLimit = num;
  const label = document.getElementById('price-range-label');
  if (label) {
    label.innerText = num >= 20000 ? 'Any' : `≤ ¥${num.toLocaleString()}`;
  }
  currentPage = 1;
  render();
}

function switchClusteredEdition(clusterIndex, newProductId, event) {
  if (event) event.stopPropagation();
  const variant = allProducts.find(x => x.id === newProductId);
  if (!variant) return;

  const card = document.getElementById(`cluster-card-${clusterIndex}`);
  if (!card) return;

  const imgEl = card.querySelector('.cluster-img');
  const imgContainer = card.querySelector('.cluster-img-container');
  const titleEl = card.querySelector('.cluster-title');
  const priceEl = card.querySelector('.cluster-price');
  const dateEl = card.querySelector('.cluster-date');
  const buyBtn = card.querySelector('.cluster-buy-btn');
  const favBtn = card.querySelector('.cluster-fav-btn');
  const shareBtn = card.querySelector('.cluster-share-btn');

  const cleanTitle = stripTitlePrefixes(variant.title);
  if (imgEl) imgEl.src = getThumbnailUrl(variant.image);
  if (imgContainer) imgContainer.setAttribute('onclick', `openModal('${variant.id}', event)`);
  if (titleEl) {
    titleEl.innerText = cleanTitle;
    titleEl.setAttribute('title', cleanTitle);
    titleEl.setAttribute('onclick', `openModal('${variant.id}', event)`);
  }
  if (priceEl) priceEl.innerHTML = formatDisplayPrice(variant.price, variant);
  if (dateEl) dateEl.innerHTML = `<i class="fa-regular fa-calendar text-[10px]"></i> ${variant.release_date || 'Available Now'}`;
  
  const isFav = getWishlist().includes(variant.id);
  if (favBtn) {
    favBtn.setAttribute('onclick', `toggleWishlist('${variant.id}', event)`);
    favBtn.setAttribute('title', isFav ? 'Remove from Wishlist' : 'Add to Wishlist');
    favBtn.className = `w-7 h-7 sm:w-6 sm:h-6 rounded-full ${isFav ? 'bg-rose-600 text-white' : 'bg-stone-900/60 text-white hover:bg-rose-600'} backdrop-blur-md flex items-center justify-center transition shadow-2xs cursor-pointer cluster-fav-btn`;
    favBtn.innerHTML = `<i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart text-[10px]"></i>`;
  }
  if (shareBtn) {
    shareBtn.setAttribute('onclick', `shareProduct(allProducts.find(x => x.id === '${variant.id}'), event)`);
  }
  if (buyBtn) {
    const upcoming = isPreOrder(variant);
    const oop = isOutOfPrint(variant);
    buyBtn.innerHTML = `${upcoming ? 'Pre-Order' : oop ? 'Archive' : 'Buy'} <i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>`;
    buyBtn.setAttribute('onclick', `triggerOutboundAffiliate(allProducts.find(x => x.id === '${variant.id}'), 'grid_cluster_btn')`);
  }
}

function renderPaginationControls(totalPages, totalItems, startIndex, endIndex) {
  const rangeEl = document.getElementById('page-range-info');
  const navEl = document.getElementById('pagination-bottom');
  const pageInput = document.getElementById('direct-page-input');
  const totalLabel = document.getElementById('direct-page-total-label');
  if (!rangeEl || !navEl) return;

  if (pageInput) {
    pageInput.max = totalPages;
    pageInput.value = currentPage;
  }
  if (totalLabel) {
    totalLabel.innerText = `of ${totalPages}`;
  }

  if (totalItems === 0) {
    rangeEl.innerText = "0 releases found";
    navEl.innerHTML = '';
    return;
  }

  rangeEl.innerHTML = `Showing <strong class="text-rose-600 dark:text-rose-400 font-bold">${startIndex + 1}–${Math.min(endIndex, totalItems)}</strong> of <strong>${totalItems.toLocaleString()}</strong> releases (Page <strong>${currentPage}</strong> of <strong>${totalPages}</strong>)`;

  if (totalPages <= 1) {
    navEl.innerHTML = '';
    return;
  }

  let navHtml = '';
  const prevDisabled = currentPage === 1;
  navHtml += `
    <button onclick="goToPage(1)" ${prevDisabled ? 'disabled' : ''} class="px-2 py-1 rounded-md border border-stone-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-stone-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-rose-50 dark:hover:bg-slate-800 transition cursor-pointer">« First</button>
    <button onclick="goToPage(${currentPage - 1})" ${prevDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded-md border border-stone-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-stone-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-rose-50 dark:hover:bg-slate-800 transition cursor-pointer">‹ Prev</button>
  `;

  let startP = Math.max(1, currentPage - 2);
  let endP = Math.min(totalPages, currentPage + 2);
  if (currentPage <= 3) endP = Math.min(totalPages, 5);
  else if (currentPage >= totalPages - 2) startP = Math.max(1, totalPages - 4);

  if (startP > 1) navHtml += `<span class="px-1.5 text-stone-400 dark:text-slate-500">...</span>`;

  for (let p = startP; p <= endP; p++) {
    if (p === currentPage) {
      navHtml += `<button class="px-3 py-1 rounded-md bg-rose-600 text-white font-bold shadow-2xs cursor-default">${p}</button>`;
    } else {
      navHtml += `<button onclick="goToPage(${p})" class="px-3 py-1 rounded-md border border-stone-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-stone-700 dark:text-slate-200 hover:bg-rose-50 dark:hover:bg-slate-800 transition cursor-pointer">${p}</button>`;
    }
  }

  if (endP < totalPages) navHtml += `<span class="px-1.5 text-stone-400 dark:text-slate-500">...</span>`;

  const nextDisabled = currentPage === totalPages;
  navHtml += `
    <button onclick="goToPage(${currentPage + 1})" ${nextDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded-md border border-stone-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-stone-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-rose-50 dark:hover:bg-slate-800 transition cursor-pointer">Next ›</button>
    <button onclick="goToPage(${totalPages})" ${nextDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded-md border border-stone-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-stone-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-rose-50 dark:hover:bg-slate-800 transition cursor-pointer">Last »</button>
  `;

  navEl.innerHTML = navHtml;
}

function render() {
  const container = document.getElementById('product-container');
  const empty = document.getElementById('empty-state');
  const emptyMsg = document.getElementById('empty-state-message');
  const emptyButtons = document.getElementById('empty-state-buttons');
  const rangeEl = document.getElementById('page-range-info');
  if (!container) return;
  container.innerHTML = '';

  const wishlistIds = getWishlist();

  const filterItem = (item) => {
    if (!item) return false;

    /* File: js/app.js | Block/Target: Tsukishima Kirari Verification Alignment */
    if (item.artist === 'Tsukishima Kirari' || (item.title && item.title.toLowerCase().includes('tsukishima kirari'))) {
      const pidUpper = String(item.id || '').toUpperCase();
      const tLower = (item.title || '').toLowerCase();
      const hasKusumi = tLower.includes('kusumi koharu') || tLower.includes('koharu kusumi') || tLower.includes('久住小春');
      const isUpFront = pidUpper.startsWith('EPCE') || pidUpper.startsWith('EPBE') || pidUpper.startsWith('EPDE');
      if (!hasKusumi && !isUpFront && item.artist !== 'Tsukishima Kirari') return false;
    }

    const priceNum = parseNumericPrice(item.price, item);
    if (maxPriceLimit < 20000 && priceNum > 0 && priceNum > maxPriceLimit) return false;

    const upcoming = isPreOrder(item);
    const oop = isOutOfPrint(item);
    const inStock = isInStock(item);

    if (!selectedAvailabilities.has('all')) {
      let matchAvail = false;
      if (selectedAvailabilities.has('instock') && inStock) matchAvail = true;
      if (selectedAvailabilities.has('preorder') && upcoming) matchAvail = true;
      if (selectedAvailabilities.has('oop') && oop) matchAvail = true;
      if (!matchAvail) return false;
    }

    const cat = item.category || '';
    const art = item.artist || '';
    let matchesCat = false;
    if (activeFilter === 'All') {
      matchesCat = true;
    /* File: js/app.js | Block/Target: filterItem Hello! Project variations */
    } else if (activeFilter === 'Hello! Project & Up-Front') {
      matchesCat = (cat === 'Hello! Project & Up-Front' || cat === 'Hello! Project' || cat === 'Up-Front Alumni');
   } else if (activeFilter === 'Modern & Alternative') {
      matchesCat = (
        cat === 'Modern & Alternative' || cat === 'Modern Idols' || cat === 'Babymetal' ||
        art === 'BABYMETAL' || art === 'Sakura Gakuin' ||
        art === 'NiziU' || art === 'ME:I' || art === 'IS:SUE'
      );
    } else if (activeFilter === 'Stardust Planet') {
      matchesCat = (cat === 'Stardust Planet' || cat === 'Momoiro Clover Z');
    } else {
      matchesCat = (cat === activeFilter);
    }

    if (activeEra !== 'All') {
      const yr = getItemYear(item);
      if (activeEra === 'upcoming' && !(yr >= 2026 && yr <= 2027)) return false;
      if (activeEra === 'modern' && !(yr >= 2020 && yr <= 2025)) return false;
      if (activeEra === 'expansion' && !(yr >= 2010 && yr <= 2019)) return false;
      if (activeEra === 'vintage' && !(yr >= 1998 && yr <= 2009)) return false;
    }

   /* File: js/app.js | Approx. Lines: 430-445 | Block/Target: filterItem Artist Matching Fallback */
    let matchesArtist = true;
    if (activeMobileArtists.length > 0) {
      matchesArtist = activeMobileArtists.includes(item.artist);
    } else if (activeArtist !== 'All') {
      matchesArtist = (item.artist === activeArtist);
      // Fallback: If filtering by parent group, also match known member releases containing the group name
      if (!matchesArtist && typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS[activeFilter]) {
        const isMemberOfGroup = (item.title || '').toLowerCase().includes(activeArtist.toLowerCase());
        if (isMemberOfGroup) matchesArtist = true;
      }
    }

    const itemFmt = getItemFormatCategory(item);
    const matchesFmt = (activeFormat === 'All' || itemFmt === activeFormat);

    let matchesMerchSub = true;
    if (activeFormat === 'Collectable' && activeMerchSubgroup !== 'All') {
      matchesMerchSub = (getMerchSubgroupType(item) === activeMerchSubgroup);
    }

    const cleanT = stripTitlePrefixes(item.title);
    const matchesSearch = !searchQuery || 
      matchesFuzzyQuery(item.title, searchQuery) || 
      matchesFuzzyQuery(cleanT, searchQuery) || 
      matchesFuzzyQuery(item.artist, searchQuery) ||
      (item.id && String(item.id).toLowerCase().includes(searchQuery));

    return matchesCat && matchesArtist && matchesFmt && matchesMerchSub && matchesSearch;
  };

  activeFilteredList = allProducts.filter(filterItem);

  let displayEntities = [];

  if (isClusteringEnabled) {
    displayEntities = clusteredEntities.filter(cluster => {
      const matchingVariants = (cluster.variants || []).filter(filterItem);
      if (!matchingVariants.length) return false;
      
      matchingVariants.sort((a, b) => {
        const scoreA = getVariantSortScore(a);
        const scoreB = getVariantSortScore(b);
        if (scoreA !== scoreB) return scoreA - scoreB;
        return String(a.title || '').localeCompare(String(b.title || ''));
      });

      cluster._activeVariants = matchingVariants;
      cluster._primary = matchingVariants[0];
      return true;
    });
  } else {
    displayEntities = activeFilteredList.map(p => ({
      id: p.id,
      _primary: p,
      _activeVariants: [p]
    }));
  }

  displayEntities.sort((entA, entB) => {
    const a = entA._primary || {};
    const b = entB._primary || {};
    const dateA = isClusteringEnabled ? getClusterEffectiveDateValue(entA) : getItemDateValue(a);
    const dateB = isClusteringEnabled ? getClusterEffectiveDateValue(entB) : getItemDateValue(b);

    if (currentSort === 'newest') {
      if (dateA > 0 && dateB === 0) return -1;
      if (dateB > 0 && dateA === 0) return 1;
      if (dateB !== dateA) return dateB - dateA;
      return (b._catalogIndex || 0) - (a._catalogIndex || 0);
    } else if (currentSort === 'oldest') {
      if (dateA > 0 && dateB === 0) return -1;
      if (dateB > 0 && dateA === 0) return 1;
      if (dateA !== dateB) return dateA - dateB;
      return (a._catalogIndex || 0) - (b._catalogIndex || 0);
    } else if (currentSort === 'price-asc') {
      const priceA = parseNumericPrice(a.price, a);
      const priceB = parseNumericPrice(b.price, b);
      if (priceA !== priceB) return priceA - priceB;
      return String(a.title || '').localeCompare(String(b.title || ''));
    } else if (currentSort === 'price-desc') {
      const priceA = parseNumericPrice(a.price, a);
      const priceB = parseNumericPrice(b.price, b);
      if (priceB !== priceA) return priceB - priceA;
      return String(a.title || '').localeCompare(String(b.title || ''));
    }
    return 0;
  });

  const totalItems = displayEntities.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
  if (currentPage > totalPages) currentPage = 1;

  if (totalItems === 0) {
    if (empty) {
      empty.classList.remove('hidden');
      if (emptyMsg) {
        emptyMsg.innerText = "No idol releases match your specific combination of filters.";
      }
      if (emptyButtons) {
        let btnsHtml = `<button onclick="resetAllFilters()" class="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-full transition cursor-pointer">Reset All Filters</button>`;
        if (activeFormat !== 'All') {
          btnsHtml += `<button onclick="setFormat('All')" class="px-3.5 py-1.5 bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-200 hover:bg-stone-300 text-xs font-bold rounded-full transition cursor-pointer">Clear Format (${activeFormat})</button>`;
        }
        if (activeEra !== 'All') {
          btnsHtml += `<button onclick="setEraFilter('All')" class="px-3.5 py-1.5 bg-stone-200 dark:bg-slate-700 text-stone-700 dark:text-stone-200 hover:bg-stone-300 text-xs font-bold rounded-full transition cursor-pointer">Clear Era (${activeEra})</button>`;
        }
        emptyButtons.innerHTML = btnsHtml;
      }
    }
    if (rangeEl) rangeEl.innerText = "0 releases found";
    renderPaginationControls(0, 0, 0, 0);
    return;
  }
  if (empty) empty.classList.add('hidden');

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedEntities = displayEntities.slice(startIndex, endIndex);

  if (layoutMode === 'mobile') {
    container.className = "grid grid-cols-2 gap-3";
  } else if (viewMode === 'grid') {
    container.className = "grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5";
  } else {
    container.className = "flex flex-col space-y-2";
  }

  paginatedEntities.forEach((entity, idx) => {
    const p = entity._primary || {};
    const variants = entity._activeVariants || [p];
    const displayImg = getThumbnailUrl(p.image);
    const upcoming = isPreOrder(p);
    const oop = isOutOfPrint(p);
    const itemFmt = getItemFormatCategory(p);
    const cleanTitle = stripTitlePrefixes(p.title);
    const safeTitle = escapeHtml(cleanTitle);
    const safeArtist = escapeHtml(p.artist);
    const isFav = wishlistIds.includes(p.id);

    let fmtBadgeBg = 'bg-stone-800/80';
    if (itemFmt === 'Single') fmtBadgeBg = 'bg-rose-600/85';
    else if (itemFmt === 'Album') fmtBadgeBg = 'bg-rose-700/85';
    else if (itemFmt === 'Blu-ray') fmtBadgeBg = 'bg-sky-700/85';
    else if (itemFmt === 'DVD') fmtBadgeBg = 'bg-amber-700/85';
    else if (itemFmt === 'Book') fmtBadgeBg = 'bg-emerald-700/85';
    else if (itemFmt === 'Collectable') fmtBadgeBg = 'bg-purple-700/85';

    const isVerticalItem = (itemFmt === 'Book' || itemFmt === 'Collectable');
    const imgFitClass = isVerticalItem ? 'object-contain p-1.5' : 'object-cover';

    let editionSelectorHtml = '';
    if (variants.length > 1) {
      editionSelectorHtml = `
        <div class="mt-1" onclick="event.stopPropagation()">
          <select onchange="switchClusteredEdition(${startIndex + idx}, this.value, event)" class="w-full bg-stone-100 dark:bg-slate-800 text-stone-700 dark:text-slate-200 py-1 px-1.5 rounded text-[10px] font-bold border border-stone-200 dark:border-slate-700 focus:outline-none cursor-pointer">
            ${variants.map(v => {
              const variantLabel = extractVariantLabel(v.title, p.title);
              return `<option value="${escapeHtml(v.id)}">${escapeHtml(variantLabel)} — ${escapeHtml(v.price || '')}</option>`;
            }).join('')}
          </select>
        </div>
      `;
    }

    const card = document.createElement('div');
    card.id = `cluster-card-${startIndex + idx}`;
    card.className = "catalog-card-item";

    if (layoutMode === 'mobile' || viewMode === 'grid') {
      card.innerHTML = `
        <div class="bg-white dark:bg-slate-900 border border-stone-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs hover:shadow-md transition flex flex-col group relative h-full">
          <div class="cluster-img-container aspect-square bg-stone-100 dark:bg-slate-800 relative overflow-hidden cursor-pointer flex items-center justify-center" onclick="openModal('${p.id}', event)">
            <img 
              src="${displayImg}" 
              alt="${safeTitle}" 
              loading="lazy" 
              referrerpolicy="no-referrer" 
              onload="this.classList.add('img-fade-in')" 
              onerror="onImgLoadError(this)" 
              class="cluster-img w-full h-full ${imgFitClass} group-hover:scale-105 transition duration-300"
            />
            
            <span class="absolute top-1.5 left-1.5 bg-stone-900/75 backdrop-blur-md text-white text-[9px] font-semibold px-1.5 py-0.2 rounded">
              ${safeArtist}
            </span>

            <div class="absolute bottom-1.5 right-1.5 flex items-center gap-1">
              <button 
                onclick="shareProduct(allProducts.find(x => x.id === '${p.id}'), event)" 
                aria-label="Share Link" 
                title="Share link" 
                class="cluster-share-btn w-7 h-7 sm:w-6 sm:h-6 rounded-full bg-stone-900/60 hover:bg-stone-900 text-white backdrop-blur-md flex items-center justify-center transition shadow-2xs cursor-pointer"
              >
                <i class="fa-solid fa-share-nodes text-[10px]"></i>
              </button>
              
              <button 
                onclick="toggleWishlist('${p.id}', event)" 
                aria-label="Save to Wishlist" 
                title="${isFav ? 'Remove from Wishlist' : 'Add to Wishlist'}" 
                class="cluster-fav-btn w-7 h-7 sm:w-6 sm:h-6 rounded-full ${isFav ? 'bg-rose-600 text-white' : 'bg-stone-900/60 text-white hover:bg-rose-600'} backdrop-blur-md flex items-center justify-center transition shadow-2xs cursor-pointer"
              >
                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart text-[10px]"></i>
              </button>
            </div>

            <span class="absolute bottom-1.5 left-1.5 ${fmtBadgeBg} backdrop-blur-md text-white text-[8px] font-bold px-1.5 py-0.2 rounded shadow-2xs">
              ${itemFmt}
            </span>

            ${upcoming ? `
              <span class="absolute top-1.5 right-1.5 bg-rose-600 text-white text-[9px] font-black px-1.5 py-0.2 rounded shadow-xs uppercase tracking-wide flex items-center gap-1 border border-rose-300/40">
                <i class="fa-solid fa-clock text-[8px]"></i> PRE-ORDER
              </span>
            ` : oop ? `
              <span class="absolute top-1.5 right-1.5 bg-stone-800 text-amber-300 text-[9px] font-black px-1.5 py-0.2 rounded shadow-xs uppercase tracking-wide flex items-center gap-1 border border-amber-300/40">
                <i class="fa-solid fa-box-archive text-[8px]"></i> OOP
              </span>
            ` : ''}
          </div>

          <div class="p-2.5 flex-1 flex flex-col justify-between">
            <div>
              <h2 class="cluster-title text-xs font-bold text-stone-800 dark:text-stone-100 line-clamp-2 cursor-pointer hover:text-rose-600 dark:hover:text-rose-400 transition" onclick="openModal('${p.id}', event)" title="${safeTitle}">
                ${safeTitle}
              </h2>
              <p class="cluster-date text-[10px] ${upcoming ? 'text-rose-600 dark:text-rose-400 font-semibold' : 'text-stone-500 dark:text-slate-400'} mt-1 flex items-center gap-1">
                <i class="fa-regular fa-calendar text-[9px]"></i> ${p.release_date || 'Available Now'}
              </p>
              ${editionSelectorHtml}
            </div>
            
            <div class="mt-2.5 pt-1.5 border-t border-stone-100 dark:border-slate-800 flex items-center justify-between">
              <div>
                <span class="cluster-price text-xs font-black text-rose-600 dark:text-rose-400">
                  ${formatDisplayPrice(p.price, p)}
                </span>
                <span class="block text-[8px] text-stone-400 dark:text-slate-500 font-medium">CDJapan Tokyo Direct</span>
              </div>
              <button 
                onclick="triggerOutboundAffiliate(allProducts.find(x => x.id === '${p.id}'), 'grid_btn')" 
                title="View and order securely on CDJapan" 
                class="cluster-buy-btn bg-rose-600 hover:bg-rose-700 text-white text-[10px] font-bold px-2.5 py-1.5 rounded-lg transition flex items-center gap-1 shadow-2xs whitespace-nowrap cursor-pointer"
              >
                ${upcoming ? 'Pre-Order' : oop ? 'Archive' : 'Buy'} <i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
              </button>
            </div>
          </div>
        </div>
      `;
    } else {
      card.innerHTML = `
        <div class="bg-white dark:bg-slate-900 border border-stone-200 dark:border-slate-800 rounded-xl p-2.5 shadow-2xs hover:shadow-xs transition flex flex-col sm:flex-row items-center gap-3 group">
          <div class="cluster-img-container w-12 h-12 bg-stone-100 dark:bg-slate-800 rounded-lg overflow-hidden shrink-0 cursor-pointer relative flex items-center justify-center" onclick="openModal('${p.id}', event)">
            <img src="${displayImg}" alt="${safeTitle}" class="cluster-img w-full h-full ${imgFitClass}" onerror="onImgLoadError(this)" />
            <span class="absolute bottom-0.5 left-0.5 ${fmtBadgeBg} text-white text-[8px] font-bold px-1 rounded">${itemFmt}</span>
          </div>

          <div class="flex-1 min-w-0 text-center sm:text-left">
            <div class="flex flex-wrap items-center justify-center sm:justify-start gap-1.5 mb-0.5">
              <span class="text-[10px] font-black text-rose-600 dark:text-rose-400 uppercase">${safeArtist}</span>
              <span class="text-[10px] font-mono text-stone-400 dark:text-slate-500">• ${p.id}</span>
              ${upcoming ? '<span class="bg-rose-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">Pre-Order</span>' : ''}
            </div>
            <h2 class="cluster-title text-xs font-bold text-stone-800 dark:text-stone-100 truncate cursor-pointer hover:text-rose-600" onclick="openModal('${p.id}', event)">
              ${safeTitle}
            </h2>
            <div class="flex items-center justify-center sm:justify-start gap-3 text-[10px] text-stone-500 dark:text-slate-400 mt-0.5">
              <span><i class="fa-regular fa-calendar text-[9px]"></i> ${p.release_date || 'Available Now'}</span>
              ${editionSelectorHtml}
            </div>
          </div>

          <div class="flex items-center gap-2.5 shrink-0">
            <div class="text-right">
              <div class="cluster-price text-xs font-black text-rose-600 dark:text-rose-400">
                ${formatDisplayPrice(p.price, p)}
              </div>
            </div>

            <div class="flex items-center gap-1">
              <button onclick="shareProduct(allProducts.find(x => x.id === '${p.id}'), event)" title="Share" class="cluster-share-btn w-7 h-7 rounded-lg bg-stone-100 dark:bg-slate-800 hover:bg-stone-200 dark:hover:bg-slate-700 text-stone-700 dark:text-stone-200 flex items-center justify-center text-xs transition cursor-pointer">
                <i class="fa-solid fa-share-nodes text-[10px]"></i>
              </button>
              <button onclick="toggleWishlist('${p.id}', event)" title="Wishlist" class="cluster-fav-btn w-7 h-7 rounded-lg ${isFav ? 'bg-rose-600 text-white' : 'bg-stone-100 dark:bg-slate-800 hover:bg-stone-200 dark:hover:bg-slate-700 text-stone-700 dark:text-stone-200'} flex items-center justify-center text-xs transition cursor-pointer">
                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart text-[10px]"></i>
              </button>
              <button onclick="triggerOutboundAffiliate(allProducts.find(x => x.id === '${p.id}'), 'list_btn')" class="cluster-buy-btn bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold px-2.5 py-1 rounded-lg transition flex items-center gap-1 shadow-2xs cursor-pointer whitespace-nowrap">
                ${upcoming ? 'Pre-Order' : oop ? 'Archive' : 'Buy'} <i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
              </button>
            </div>
          </div>
        </div>
      `;
    }

    container.appendChild(card);
  });

  renderPaginationControls(totalPages, totalItems, startIndex, endIndex);
}

async function loadCatalog() {
  const statsEl = document.getElementById('stats');
  let data = null;

  try {
    if (window.IdolDB) {
      const cachedDb = await window.IdolDB.loadCatalog().catch(() => null);
      if (cachedDb && Array.isArray(cachedDb) && cachedDb.length > 0) {
        allProducts = cachedDb.map((item, idx) => ({
          ...item,
          id: String(item.id || `sku-${idx}`),
          title: String(item.title || 'Untitled Release'),
          artist: (item.artist === 'Keyakizaka46' || item.artist === '欅坂46') ? 'Sakurazaka46' : String(item.artist || 'Idol Artist'),
          category: String(item.category || 'Hello! Project'),
          price: String(item.price || 'Check CDJapan'),
          _catalogIndex: idx
        }));
        
        if (statsEl) statsEl.innerText = `${allProducts.length.toLocaleString()} Items Live (Instant DB)`;
        try {
          readUrlParams();
          buildClusteredEntities();
          updateDynamicCounts();
          updateActiveArtistBanner();
          updateFilterButtonsUI();
          updateAvailabilityPillsUI();
          updateWishlistBadge();
          applyLayoutModeToDom();
        } catch (err) {}
        render();
      }
    }
  } catch (err) {
    console.warn('IndexedDB retrieval bypassed:', err);
  }

  const cacheBuster = Date.now();
  const candidatePaths = [
    `catalog-index.json?v=${cacheBuster}`,
    `./catalog-index.json?v=${cacheBuster}`,
    `/catalog-index.json?v=${cacheBuster}`,
    `products.json?v=${cacheBuster}`
  ];

  for (const p of candidatePaths) {
    try {
      const res = await fetch(p);
      if (res && res.ok) {
        const parsed = await res.json();
        if (parsed && typeof parsed === 'object' && Object.keys(parsed).length > 0) {
          data = parsed;
          break;
        }
      }
    } catch (e) {}
  }

  if (data && typeof data === 'object') {
    const parsedItems = Object.values(data)
      .filter(item => item && (item.id || item.title))
      .map((item, idx) => {
        let art = String(item.artist || 'Idol Artist');
        if (art === 'Keyakizaka46' || art === '欅坂46') {
          art = 'Sakurazaka46';
        }
        return {
          ...item,
          id: String(item.id || `sku-${idx}`),
          title: String(item.title || 'Untitled Release'),
          artist: art,
          category: String(item.category || 'Hello! Project'),
          price: String(item.price || 'Check CDJapan'),
          _catalogIndex: idx
        };
      });

    if (parsedItems.length > 0) {
      allProducts = parsedItems;
      if (statsEl) statsEl.innerText = `${allProducts.length.toLocaleString()} Items Live`;
      
      if (window.IdolDB) {
        window.IdolDB.saveCatalog(parsedItems).catch(() => {});
      }
    }
  }

  try {
    readUrlParams();
    buildClusteredEntities();
    updateDynamicCounts();
    updateActiveArtistBanner();
    updateFilterButtonsUI();
    updateAvailabilityPillsUI();
    updateWishlistBadge();
    applyLayoutModeToDom();
  } catch (prepErr) {
    console.error('Error preparing catalog state:', prepErr);
  } finally {
    render();
  }
}

// Global Browser Window & Keyboard Event Bindings
window.addEventListener('resize', () => {
  const newLayout = detectDeviceLayout();
  if (newLayout !== layoutMode) {
    layoutMode = newLayout;
    applyLayoutModeToDom();
    render();
  }
});

window.addEventListener('scroll', () => {
  const btn = document.getElementById('scroll-to-top');
  if (!btn) return;
  if (window.scrollY > 400) {
    btn.classList.remove('opacity-0', 'pointer-events-none');
  } else {
    btn.classList.add('opacity-0', 'pointer-events-none');
  }
});

window.addEventListener('keydown', (e) => {
  const modal = document.getElementById('product-modal');
  const cryptoModal = document.getElementById('crypto-modal');
  const haulDrawer = document.getElementById('haul-drawer');
  const isModalOpen = modal && !modal.classList.contains('hidden');
  const isInputActive = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);

  if (e.key === 'Escape') {
    dismissMegaMenu();
    closeModal();
    closeAutocomplete();
    if (cryptoModal && !cryptoModal.classList.contains('hidden')) toggleCryptoModal();
    const drawer = document.getElementById('calendar-drawer');
    if (drawer && !drawer.classList.contains('hidden')) toggleCalendarDrawer();
    if (haulDrawer && !haulDrawer.classList.contains('hidden')) toggleHaulDrawer();
    const mobileDrawer = document.getElementById('mobile-filter-drawer');
    if (mobileDrawer && !mobileDrawer.classList.contains('hidden')) toggleMobileFilterDrawer();
  } else if (isModalOpen && e.key === 'ArrowLeft') {
    navigateModalPrev();
  } else if (isModalOpen && e.key === 'ArrowRight') {
    navigateModalNext();
  } else if (!isInputActive && !isModalOpen) {
    if (e.key === 'End') {
      e.preventDefault();
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
    } else if (e.key === 'Home') {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  updateThemeIcon();
  applyLayoutModeToDom();
  updateAvailabilityPillsUI();
  if (localStorage.getItem('idoljapan_dismiss_trust') === 'true') {
    const banner = document.getElementById('trust-notice-banner');
    if (banner) banner.classList.add('hidden');
  }
  loadCatalog();
  Promise.allSettled([
    initExchangeRates(),
    loadSearchAliases()
  ]).then(() => {
    render();
  });
});
