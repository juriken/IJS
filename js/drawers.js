/* ==========================================================================
   IdolJapan.store — Drawers, Modals, Haul Shipping & Formatting Utilities
   Path: js/drawers.js
   ========================================================================== */

var toastTimeoutId = null;

function showToast(message, isSuccess = true) {
  const toast = document.getElementById('toast');
  const text = document.getElementById('toast-message');
  const icon = document.getElementById('toast-icon');
  if (!toast || !text) return;

  text.innerText = message;
  if (icon) {
    icon.className = isSuccess
      ? 'fa-solid fa-circle-check text-emerald-400'
      : 'fa-solid fa-circle-exclamation text-amber-400';
  }

  toast.classList.remove('opacity-0', 'pointer-events-none');
  if (toastTimeoutId) clearTimeout(toastTimeoutId);
  toastTimeoutId = setTimeout(() => {
    toast.classList.add('opacity-0', 'pointer-events-none');
    toastTimeoutId = null;
  }, 2600);
}

function copyToClipboard(text, successMessage) {
  if (!text) return;
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMessage || 'Copied to clipboard!');
    }).catch(() => {
      fallbackCopyToClipboard(text, successMessage);
    });
  } else {
    fallbackCopyToClipboard(text, successMessage);
  }
}

function fallbackCopyToClipboard(text, successMessage) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast(successMessage || 'Copied to clipboard!');
  } catch (err) {
    showToast('Unable to copy to clipboard', false);
  }
}

function dismissTrustNotice() {
  const banner = document.getElementById('trust-notice-banner');
  if (banner) banner.classList.add('hidden');
  try {
    localStorage.setItem('idoljapan_dismiss_trust', 'true');
  } catch (e) {}
}

function toggleQr(coinKey) {
  const el = document.getElementById(`qr-box-${coinKey}`);
  if (!el) return;
  el.classList.toggle('hidden');
}

function toggleAllQrs() {
  const boxes = document.querySelectorAll('.crypto-qr-box');
  const anyHidden = Array.from(boxes).some(b => b.classList.contains('hidden'));
  boxes.forEach(b => {
    if (anyHidden) b.classList.remove('hidden');
    else b.classList.add('hidden');
  });
  const btnText = document.getElementById('toggle-all-qr-text');
  if (btnText) {
    btnText.innerText = anyHidden ? 'Hide All QRs' : 'Show All QRs';
  }
}

function toggleCryptoModal() {
  const modal = document.getElementById('crypto-modal');
  if (!modal) return;
  if (modal.classList.contains('hidden')) {
    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  } else {
    modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }
}

function closeCryptoModalOnBackdrop(e) {
  if (e && e.target && e.target.id === 'crypto-modal') toggleCryptoModal();
}

function triggerOutboundAffiliate(product, subId = 'direct') {
  if (!product) return;
  if (window.IdolAnalytics && typeof window.IdolAnalytics.trackAffiliateClick === 'function') {
    window.IdolAnalytics.trackAffiliateClick(product, subId);
  }

  const baseUrl = product.affiliate_url || `https://www.cdjapan.co.jp/product/${encodeURIComponent(product.id)}?affi=A033398`;
  const sep = baseUrl.includes('?') ? '&' : '?';
  const finalUrl = `${baseUrl}${sep}sub_id=${encodeURIComponent(subId)}`;

  showToast("Redirecting to official retailer CDJapan (Tokyo)...");
  window.open(finalUrl, '_blank', 'noopener,noreferrer');
}

function stripTitlePrefixes(rawTitle) {
  if (!rawTitle) return '';
  return String(rawTitle)
    .replace(/^(?:Album\s+CD|Single\s+CD|Collectible|Blu-ray|DVD|BOOK|Album|Single|APPAREL)\s+/i, '')
    .trim();
}

function extractVariantLabel(vTitle, baseTitle) {
  if (!vTitle) return 'Standard Edition';
  const cleanV = stripTitlePrefixes(vTitle);
  const cleanBase = stripTitlePrefixes(baseTitle);

  const bracketMatches = cleanV.match(/\[(.*?)\]|\((.*?)\)|【(.*?)】/g);
  if (bracketMatches && bracketMatches.length > 0) {
    return bracketMatches.join(' ');
  }

  if (cleanBase && cleanV.toLowerCase().startsWith(cleanBase.toLowerCase())) {
    const diff = cleanV.slice(cleanBase.length).trim();
    if (diff) return diff;
  }

  return cleanV.length > 38 ? cleanV.slice(0, 38) + '...' : cleanV;
}

function getVariantSortScore(variant) {
  if (!variant) return 50;
  const title = String(variant.title || '').toLowerCase();
  let rank = 50;

  if (title.includes('limited') || title.includes('初回') || title.includes('ltd')) {
    rank = 10;
    const typeMatch = title.match(/type[\s-]*([a-z0-9]+)/i);
    if (typeMatch && typeMatch[1]) {
      rank += (typeMatch[1].toUpperCase().charCodeAt(0) - 64) * 0.1;
    }
  } else if (title.includes('regular') || title.includes('通常')) {
    rank = 30;
  } else if (title.includes('bundle') || title.includes('bonus') || title.includes('set')) {
    rank = 70;
  }

  return rank;
}

function extractEditionTags(title) {
  if (!title) return [];
  const tags = [];
  const lower = String(title).toLowerCase();

  if (/limited edition|初回生産限定盤|初回限定盤/i.test(lower)) {
    tags.push({ name: 'Limited', color: 'bg-amber-600' });
  }
  if (/regular edition|通常盤/i.test(lower)) {
    tags.push({ name: 'Regular', color: 'bg-stone-600' });
  }
  const typeMatch = String(title).match(/Type\s*([A-Za-z0-9]+)/i);
  if (typeMatch && typeMatch[1]) {
    tags.push({ name: `Type ${typeMatch[1].toUpperCase()}`, color: 'bg-rose-600' });
  }
  if (/w\/\s*blu-ray|blu-ray disc付|\+bd/i.test(lower)) {
    tags.push({ name: 'CD+BD', color: 'bg-sky-600' });
  }
  if (/w\/\s*dvd|dvd付/i.test(lower)) {
    tags.push({ name: 'CD+DVD', color: 'bg-purple-600' });
  }
  if (/tokuten|bonus|外付け特典/i.test(lower)) {
    tags.push({ name: 'Bonus Included', color: 'bg-emerald-600' });
  }
  return tags;
}

function getThumbnailUrl(rawUrl) {
  if (!rawUrl || String(rawUrl).startsWith('data:')) return PLACEHOLDER_IMG;
  return String(rawUrl).replace('/pictures/l/', '/pictures/m/');
}

function onImgLoadError(imgEl) {
  if (!imgEl) return;
  imgEl.onerror = null;
  if (imgEl.src !== PLACEHOLDER_IMG) {
    imgEl.src = PLACEHOLDER_IMG;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeIcsText(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n');
}

function exportAllPreOrdersIcs() {
  const preOrders = allProducts.filter(p => typeof isPreOrder === 'function' && isPreOrder(p));
  if (!preOrders.length) {
    showToast("No active pre-orders to export.", false);
    return;
  }

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//IdolJapan.store//Tokyo Street Dates//EN"
  ];

  preOrders.forEach(p => {
    const dVal = typeof getItemDateValue === 'function' ? getItemDateValue(p) : 0;
    if (dVal > 0) {
      const y = Math.floor(dVal / 10000);
      const m = String(Math.floor((dVal % 10000) / 100)).padStart(2, '0');
      const d = String(dVal % 100).padStart(2, '0');
      const dateStr = `${y}${m}${d}`;

      lines.push("BEGIN:VEVENT");
      lines.push(`UID:${p.id}@idoljapan.store`);
      lines.push(`DTSTAMP:${dateStr}T090000Z`);
      lines.push(`DTSTART;VALUE=DATE:${dateStr}`);
      lines.push(`SUMMARY:${escapeIcsText(`[Release] ${p.artist} - ${stripTitlePrefixes(p.title)}`)}`);
      lines.push(`DESCRIPTION:${escapeIcsText(`Official Tokyo Street Date for ${p.title} (${p.id}). CDJapan Order: ${p.affiliate_url || ''}`)}`);
      lines.push(`URL:https://idoljapan.store/?id=${encodeURIComponent(p.id)}`);
      lines.push("END:VEVENT");
    }
  });

  lines.push("END:VCALENDAR");
  const ics = lines.join("\r\n") + "\r\n";

  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `idoljapan_preorders_${Date.now()}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast("Pre-Order .ICS calendar exported!");
}

function calculateWishlistHaulMetrics() {
  const listIds = getWishlist();
  const items = allProducts.filter(p => listIds.includes(p.id));

  let totalWeightGrams = 0;
  let totalJpy = 0;

  items.forEach(it => {
    const fmt = typeof getItemFormatCategory === 'function' ? getItemFormatCategory(it) : 'Other';
    totalWeightGrams += MEDIA_WEIGHTS_GRAMS[fmt] || 140;
    totalJpy += typeof parseNumericPrice === 'function' ? parseNumericPrice(it.price, it) : 0;
  });

  let bracket = "≤ 500g (Minimum Tier)";
  let progressPct = Math.min(100, (totalWeightGrams / 500) * 100);

  if (totalWeightGrams > 2000) {
    bracket = "> 2,000g (Heavy Tier)";
    progressPct = 100;
  } else if (totalWeightGrams > 1000) {
    bracket = "1,001g – 2,000g Tier";
    progressPct = Math.min(100, ((totalWeightGrams - 1000) / 1000) * 100);
  } else if (totalWeightGrams > 500) {
    bracket = "501g – 1,000g Tier";
    progressPct = Math.min(100, ((totalWeightGrams - 500) / 500) * 100);
  }

  return { count: items.length, weight: totalWeightGrams, jpy: totalJpy, bracket, progressPct, items };
}

function toggleHaulDrawer() {
  const drawer = document.getElementById('haul-drawer');
  if (!drawer) return;
  const isHidden = drawer.classList.contains('hidden');

  if (isHidden) {
    populateHaulDrawer();
    drawer.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  } else {
    drawer.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }
}

function closeHaulDrawerOnBackdrop(e) {
  if (e && e.target && (e.target.id === 'haul-drawer' || e.target.classList.contains('backdrop-blur-xs'))) {
    toggleHaulDrawer();
  }
}

function populateHaulDrawer() {
  const container = document.getElementById('haul-drawer-list');
  const countEl = document.getElementById('haul-items-count');
  const weightEl = document.getElementById('haul-weight-total');
  const tierEl = document.getElementById('haul-bracket-tier');
  const progressEl = document.getElementById('haul-weight-progress');

  if (!container) return;
  const metrics = calculateWishlistHaulMetrics();

  if (countEl) countEl.innerText = `${metrics.count} releases`;
  if (weightEl) weightEl.innerText = `~${metrics.weight.toLocaleString()}g`;
  if (tierEl) tierEl.innerText = metrics.bracket;
  if (progressEl) progressEl.style.width = `${metrics.progressPct}%`;

  if (metrics.count === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-stone-400 dark:text-slate-500 space-y-2">
        <i class="fa-regular fa-heart text-4xl mb-1 text-rose-400/60"></i>
        <p class="font-bold text-sm text-stone-700 dark:text-stone-300">Your Wishlist is Empty</p>
        <p class="text-[11px]">Click the heart icon on any release to calculate consolidated shipping.</p>
      </div>
    `;
    return;
  }

  let html = '';
  metrics.items.forEach(it => {
    const fmt = typeof getItemFormatCategory === 'function' ? getItemFormatCategory(it) : 'Other';
    const weight = MEDIA_WEIGHTS_GRAMS[fmt] || 140;
    const cleanTitle = escapeHtml(stripTitlePrefixes(it.title));
    const safeId = escapeHtml(it.id);

    html += `
      <div class="pt-3 first:pt-0 flex items-center gap-3">
        <img src="${getThumbnailUrl(it.image)}" alt="${cleanTitle}" class="w-11 h-11 object-cover rounded-lg shrink-0 border border-stone-200 dark:border-slate-800" onerror="onImgLoadError(this)" />
        <div class="flex-1 min-w-0">
          <h4 class="font-bold text-stone-900 dark:text-white truncate text-xs" title="${cleanTitle}">${cleanTitle}</h4>
          <p class="text-[10px] text-stone-400 dark:text-slate-500 truncate">${escapeHtml(it.artist)} • ${fmt} (~${weight}g)</p>
          <div class="text-[11px] font-black text-rose-600 dark:text-rose-400 mt-0.5">${typeof formatDisplayPrice === 'function' ? formatDisplayPrice(it.price, it) : escapeHtml(it.price)}</div>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <button onclick="triggerOutboundAffiliate(allProducts.find(x => x.id === '${safeId}'), 'haul_drawer_buy')" title="Order on CDJapan" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg text-[10px] transition cursor-pointer">
            Order
          </button>
          <button onclick="toggleWishlist('${safeId}'); populateHaulDrawer();" title="Remove" class="w-7 h-7 rounded-lg text-stone-400 hover:text-rose-600 hover:bg-stone-100 dark:hover:bg-slate-800 flex items-center justify-center transition cursor-pointer">
            <i class="fa-solid fa-trash-can text-[11px]"></i>
          </button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function exportWishlistHaul() {
  const listIds = getWishlist();
  if (!listIds.length) {
    showToast("Wishlist is empty!", false);
    return;
  }

  const metrics = calculateWishlistHaulMetrics();
  let content = "========================================\n";
  content += "IDOLJAPAN.STORE — SAVED CDJAPAN HAUL\n";
  content += "Generated: " + new Date().toLocaleDateString() + "\n";
  content += `Total Items: ${metrics.count} | Est. Weight: ~${metrics.weight}g\n`;
  content += `Courier Shipping Bracket: ${metrics.bracket}\n`;
  content += `Estimated Value: ¥${metrics.jpy.toLocaleString()}\n`;
  content += "========================================\n\n";

  metrics.items.forEach((it, idx) => {
    const fmt = typeof getItemFormatCategory === 'function' ? getItemFormatCategory(it) : 'Other';
    const weight = MEDIA_WEIGHTS_GRAMS[fmt] || 140;
    content += `${idx + 1}. [${it.artist}] ${stripTitlePrefixes(it.title)}\n`;
    content += `   Catalog ID: ${it.id} | Format: ${fmt} (~${weight}g)\n`;
    content += `   Price: ${it.price}\n`;
    content += `   Direct Link: https://idoljapan.store/?id=${encodeURIComponent(it.id)}\n\n`;
  });

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `idoljapan_haul_${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast("Wishlist haul exported!");
}

async function shareProduct(product, e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  if (!product) return;

  const directUrl = `${window.location.origin}/?id=${encodeURIComponent(product.id)}`;
  const shareData = {
    title: `${stripTitlePrefixes(product.title)} — ${product.artist}`,
    text: `Check out ${stripTitlePrefixes(product.title)} on IdolJapan.store:`,
    url: directUrl
  };

  if (navigator.share) {
    try {
      await navigator.share(shareData);
      return;
    } catch (err) {
      if (err.name !== 'AbortError') console.warn('Native share failed:', err);
    }
  }

  copyToClipboard(directUrl, "Product link copied to clipboard!");
}

function getWishlist() {
  try {
    const raw = localStorage.getItem(WISHLIST_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    return [];
  }
}

function saveWishlist(list) {
  try {
    localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(list));
  } catch (e) {}
  updateWishlistBadge();
}

function toggleWishlist(productId, e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  let list = getWishlist();
  const idx = list.indexOf(productId);
  const isAdded = (idx === -1);

  if (!isAdded) {
    list.splice(idx, 1);
    showToast("Removed from wishlist");
  } else {
    list.push(productId);
    showToast("Saved to wishlist!");
  }
  saveWishlist(list);

  const p = allProducts.find(x => x.id === productId);
  if (p && window.IdolAnalytics && typeof window.IdolAnalytics.trackWishlistToggle === 'function') {
    window.IdolAnalytics.trackWishlistToggle(p, isAdded);
  }

  if (typeof render === 'function') render();
}

function updateWishlistBadge() {
  const list = getWishlist();
  const badge = document.getElementById('wishlist-count-badge');
  const mobileBadge = document.getElementById('mobile-bottom-wishlist-badge');
  if (badge) badge.innerText = list.length;
  if (mobileBadge) mobileBadge.innerText = list.length;
}

function shareWishlistUrl() {
  const listIds = getWishlist();
  if (!listIds.length) {
    showToast("Wishlist is empty!", false);
    return;
  }
  const shareUrl = `${window.location.origin}/?wishlist=${encodeURIComponent(listIds.join(','))}`;
  copyToClipboard(shareUrl, "Wishlist share link copied!");
}

function toggleMobileFilterDrawer() {
  const drawer = document.getElementById('mobile-filter-drawer');
  if (!drawer) return;
  const isHidden = drawer.classList.contains('hidden');
  if (isHidden) {
    updateMobileDrawerContent();
    drawer.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  } else {
    drawer.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }
}

function closeMobileFilterDrawerOnBackdrop(e) {
  if (e && e.target && (e.target.id === 'mobile-filter-drawer' || e.target.classList.contains('backdrop-blur-xs'))) {
    toggleMobileFilterDrawer();
  }
}

function mobileQuickSelect(artist) {
  activeMobileArtists = [artist];
  activeArtist = artist;
  activeFilter = 'All';
  updateMobileDrawerContent();
  currentPage = 1;
  if (typeof updateActiveArtistBanner === 'function') updateActiveArtistBanner();
  if (typeof syncUrlParams === 'function') syncUrlParams();
  if (typeof render === 'function') render();
  toggleMobileFilterDrawer();
}

function clearMobileSelectedArtists() {
  activeMobileArtists = [];
  activeArtist = 'All';
  updateMobileDrawerContent();
  currentPage = 1;
  if (typeof updateActiveArtistBanner === 'function') updateActiveArtistBanner();
  if (typeof syncUrlParams === 'function') syncUrlParams();
  if (typeof render === 'function') render();
}

function toggleMobileArtistCheckbox(artist) {
  const idx = activeMobileArtists.indexOf(artist);
  if (idx > -1) {
    activeMobileArtists.splice(idx, 1);
  } else {
    activeMobileArtists.push(artist);
  }
  activeArtist = activeMobileArtists.length === 1 ? activeMobileArtists[0] : 'All';
  updateMobileDrawerContent();
  currentPage = 1;
  if (typeof updateActiveArtistBanner === 'function') updateActiveArtistBanner();
  if (typeof syncUrlParams === 'function') syncUrlParams();
  if (typeof render === 'function') render();
}

function updateMobileDrawerContent() {
  const accordionContainer = document.getElementById('mobile-drawer-accordions');
  const fmtBox = document.getElementById('mobile-drawer-formats');
  const countEl = document.getElementById('mobile-selected-count');
  const filterBadge = document.getElementById('mobile-filter-count-badge');
  const mobPriceRange = document.getElementById('mobile-drawer-price-range');
  const mobPriceLabel = document.getElementById('mobile-drawer-price-label');

  if (countEl) {
    countEl.innerText = activeMobileArtists.length ? `${activeMobileArtists.length} group(s)` : 'All';
  }
  if (filterBadge) {
    filterBadge.innerText = activeMobileArtists.length ? `${activeMobileArtists.length} selected` : (activeFilter !== 'All' ? activeFilter : 'All');
  }
  if (mobPriceRange) {
    mobPriceRange.value = maxPriceLimit;
  }
  if (mobPriceLabel) {
    mobPriceLabel.innerText = maxPriceLimit >= 20000 ? 'Any' : `≤ ¥${maxPriceLimit.toLocaleString()}`;
  }

  if (accordionContainer) {
    const franchises = [
      'Hello! Project & Up-Front', 'AKB48 Group', 'Sakamichi Series',
      'Stardust Planet', '=LOVE / Sister Groups', 'KAWAII LAB.', 'Modern & Alternative'
    ];

    let accHtml = '';
    franchises.forEach((fr, fIdx) => {
      const units = FRANCHISE_ARTISTS[fr] || [];
      accHtml += `
        <div class="border border-stone-200 dark:border-slate-800 rounded-xl overflow-hidden bg-stone-50/50 dark:bg-slate-800/40">
          <button 
            onclick="document.getElementById('mob-acc-content-${fIdx}')?.classList.toggle('hidden'); document.getElementById('mob-acc-icon-${fIdx}')?.classList.toggle('rotate-180');" 
            class="w-full p-2.5 flex items-center justify-between text-left font-bold text-stone-800 dark:text-stone-200 text-xs cursor-pointer"
          >
            <span>${escapeHtml(fr)}</span>
            <i id="mob-acc-icon-${fIdx}" class="fa-solid fa-chevron-down text-[10px] text-stone-400 transition-transform duration-200"></i>
          </button>
          <div id="mob-acc-content-${fIdx}" class="hidden p-2.5 pt-0 border-t border-stone-100 dark:border-slate-800 space-y-1">
            ${units.map(u => {
              const isChecked = activeMobileArtists.includes(u);
              return `
                <label class="flex items-center gap-2 py-1 px-1.5 rounded hover:bg-stone-100 dark:hover:bg-slate-700 cursor-pointer">
                  <input 
                    type="checkbox" 
                    ${isChecked ? 'checked' : ''} 
                    onchange="toggleMobileArtistCheckbox('${escapeHtml(u)}')" 
                    class="accent-rose-600 rounded"
                  />
                  <span class="text-xs text-stone-700 dark:text-stone-300">${escapeHtml(u)}</span>
                </label>
              `;
            }).join('')}
          </div>
        </div>
      `;
    });
    accordionContainer.innerHTML = accHtml;
  }

  if (fmtBox) {
    const fmts = ['All', 'Single', 'Album', 'Blu-ray', 'DVD', 'Book', 'Collectable'];
    fmtBox.innerHTML = fmts.map(f => {
      const isAct = (activeFormat === f);
      return `<button onclick="setFormat('${f}')" class="px-2.5 py-1 rounded-xl text-xs font-bold transition cursor-pointer ${isAct ? 'bg-rose-600 text-white' : 'bg-stone-100 dark:bg-slate-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-slate-700'}">${f}</button>`;
    }).join('');
  }
}

function openSortMenuMobile() {
  const order = ['newest', 'oldest', 'price-asc', 'price-desc'];
  const nextSort = order[(order.indexOf(currentSort) + 1) % order.length];
  if (typeof changeSort === 'function') changeSort(nextSort);
  showToast(`Sorted: ${nextSort.replace('-', ' ')}`);
}

function toggleCalendarDrawer() {
  const drawer = document.getElementById('calendar-drawer');
  if (!drawer) return;
  const isHidden = drawer.classList.contains('hidden');

  if (isHidden) {
    populateCalendarDrawer();
    drawer.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  } else {
    drawer.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }
}

function closeCalendarOnBackdrop(e) {
  if (e && e.target && (e.target.id === 'calendar-drawer' || e.target.classList.contains('backdrop-blur-xs'))) {
    toggleCalendarDrawer();
  }
}

function populateCalendarDrawer() {
  const container = document.getElementById('calendar-drawer-list');
  if (!container) return;

  const preOrders = allProducts.filter(p => typeof isPreOrder === 'function' && isPreOrder(p));
  preOrders.sort((a, b) => (typeof getItemDateValue === 'function' ? getItemDateValue(a) - getItemDateValue(b) : 0));

  if (!preOrders.length) {
    container.innerHTML = `
      <div class="text-center py-10 text-stone-400">
        <i class="fa-regular fa-calendar-xmark text-3xl mb-2"></i>
        <p>No scheduled pre-orders found in active catalog.</p>
      </div>
    `;
    return;
  }

  const grouped = {};
  preOrders.forEach(p => {
    const d = p.release_date || 'Upcoming Street Date';
    if (!grouped[d]) grouped[d] = [];
    grouped[d].push(p);
  });

  let html = '';
  Object.entries(grouped).forEach(([dateStr, items]) => {
    html += `
      <div>
        <div class="sticky top-0 bg-stone-100 dark:bg-slate-800 py-1 px-2.5 rounded-md font-bold text-rose-600 dark:text-rose-400 flex items-center justify-between mb-2">
          <span><i class="fa-regular fa-clock mr-1"></i> ${escapeHtml(dateStr)}</span>
          <span class="text-[10px] text-stone-500 font-normal">${items.length} release${items.length > 1 ? 's' : ''}</span>
        </div>
        <div class="space-y-2">
    `;
    items.forEach(it => {
      const cleanTitle = escapeHtml(stripTitlePrefixes(it.title));
      const safeId = escapeHtml(it.id);
      html += `
        <div class="flex items-center gap-3 p-2 rounded-xl border border-stone-100 dark:border-slate-800 hover:bg-stone-50 dark:hover:bg-slate-800/50 transition">
          <img src="${getThumbnailUrl(it.image)}" alt="${cleanTitle}" class="w-10 h-10 object-cover rounded-lg shrink-0" onerror="onImgLoadError(this)" />
          <div class="flex-1 min-w-0">
            <p class="font-bold text-stone-800 dark:text-stone-100 truncate text-[11px]">${cleanTitle}</p>
            <p class="text-[10px] text-stone-400 truncate">${escapeHtml(it.artist)} • ${typeof formatDisplayPrice === 'function' ? formatDisplayPrice(it.price, it) : escapeHtml(it.price)}</p>
          </div>
          <button onclick="triggerOutboundAffiliate(allProducts.find(x => x.id === '${safeId}'), 'calendar_view')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-md text-[10px] whitespace-nowrap shadow-xs cursor-pointer">
            Pre-Order
          </button>
        </div>
      `;
    });
    html += `</div></div>`;
  });

  container.innerHTML = html;
}

function openModal(productId, e) {
  if (e) e.preventDefault();
  const p = allProducts.find(item => item.id === productId);
  if (!p) return;
  currentModalProduct = p;

  const modal = document.getElementById('product-modal');
  if (!modal) return;

  const params = new URLSearchParams(window.location.search);
  params.set('id', p.id);
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);

  const cleanTitle = stripTitlePrefixes(p.title);
  document.title = `${cleanTitle} — ${p.artist} | IdolJapan.store`;

  const img = document.getElementById('modal-img');
  const title = document.getElementById('modal-title');
  const artist = document.getElementById('modal-artist-badge');
  const cat = document.getElementById('modal-category');
  const cid = document.getElementById('modal-catalog-id');
  const relDate = document.getElementById('modal-release-date');
  const price = document.getElementById('modal-price');
  const fmt = document.getElementById('modal-format-badge');
  const preorder = document.getElementById('modal-preorder-badge');
  const oopBadge = document.getElementById('modal-oop-badge');
  const buyText = document.getElementById('modal-buy-btn-text');
  const editionBox = document.getElementById('modal-edition-tags');

  if (img) {
    img.src = p.image || PLACEHOLDER_IMG;
    img.alt = cleanTitle;
  }
  if (title) title.innerText = cleanTitle;
  if (artist) artist.innerText = p.artist || '';
  if (cat) cat.innerText = p.category || '';
  if (cid) cid.innerText = p.id || '';
  if (relDate) relDate.innerText = p.release_date || 'Available Now';
  if (price) price.innerHTML = typeof formatDisplayPrice === 'function' ? formatDisplayPrice(p.price, p) : escapeHtml(p.price);
  if (fmt) fmt.innerText = typeof getItemFormatCategory === 'function' ? getItemFormatCategory(p) : 'CD';

  if (editionBox) {
    editionBox.innerHTML = '';
    const tags = extractEditionTags(p.title);
    tags.forEach(t => {
      const pill = document.createElement('span');
      pill.className = `${t.color} text-white text-[9px] font-bold px-2 py-0.5 rounded shadow-xs`;
      pill.innerText = t.name;
      editionBox.appendChild(pill);
    });
  }

  const upcoming = typeof isPreOrder === 'function' && isPreOrder(p);
  const oop = typeof isOutOfPrint === 'function' && isOutOfPrint(p);

  if (upcoming) {
    if (preorder) preorder.classList.remove('hidden');
    if (oopBadge) oopBadge.classList.add('hidden');
    if (buyText) buyText.innerText = "Pre-Order on CDJapan";
  } else if (oop) {
    if (oopBadge) oopBadge.classList.remove('hidden');
    if (preorder) preorder.classList.add('hidden');
    if (buyText) buyText.innerText = "Check Archive Status on CDJapan";
  } else {
    if (preorder) preorder.classList.add('hidden');
    if (oopBadge) oopBadge.classList.add('hidden');
    if (buyText) buyText.innerText = "Order Securely on CDJapan";
  }

  modal.classList.remove('hidden');
  document.body.classList.add('overflow-hidden');

  if (window.IdolAnalytics && typeof window.IdolAnalytics.trackProductView === 'function') {
    window.IdolAnalytics.trackProductView(p);
  }
}

function navigateModalPrev() {
  if (!currentModalProduct || !activeFilteredList.length) return;
  const idx = activeFilteredList.findIndex(x => x.id === currentModalProduct.id);
  const prevIdx = idx > 0 ? idx - 1 : activeFilteredList.length - 1;
  if (activeFilteredList[prevIdx]) {
    openModal(activeFilteredList[prevIdx].id);
  }
}

function navigateModalNext() {
  if (!currentModalProduct || !activeFilteredList.length) return;
  const idx = activeFilteredList.findIndex(x => x.id === currentModalProduct.id);
  const nextIdx = idx < activeFilteredList.length - 1 ? idx + 1 : 0;
  if (activeFilteredList[nextIdx]) {
    openModal(activeFilteredList[nextIdx].id);
  }
}

function closeModal() {
  const modal = document.getElementById('product-modal');
  if (modal) modal.classList.add('hidden');
  document.body.classList.remove('overflow-hidden');
  currentModalProduct = null;

  const params = new URLSearchParams(window.location.search);
  if (params.has('id')) {
    params.delete('id');
    const rest = params.toString();
    window.history.replaceState({}, '', window.location.pathname + (rest ? `?${rest}` : ''));
  }
  if (typeof updatePageTitle === 'function') updatePageTitle();
}

function closeModalOnBackdrop(e) {
  if (e && e.target && e.target.id === 'product-modal') {
    closeModal();
  }
}
