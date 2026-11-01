# IdolJapan.store Frontend UI/DOM Contract

Target Environment: Cloudflare Pages | HTML5 | Tailwind CSS CDN (sakura palette) | Vanilla ES6

## 1. Global JS Event Handlers Called by index.html
Do not remove or rename these inline function calls when modifying the DOM:
- Navigation & Megamenu: onTier1Click(cat), handleTopNavHover(cat), handleTopNavLeave(), handleMegaMenuEnter(), handleMegaMenuLeave(), filterMegaMenuLinks(val), dismissMegaMenu(), setFilter(cat), resetAllFilters()
- Formats & Filtering: setFormat(fmt), toggleAvailabilityMode(mode), setEraFilter(era), onMaxPriceChange(price), setMerchSubgroup(sub), toggleClustering(checked)
- Search: showSearchSuggestions(), clearSearch()
- Drawers: toggleHaulDrawer(), closeHaulDrawerOnBackdrop(e), toggleCalendarDrawer(), closeCalendarOnBackdrop(e), toggleMobileFilterDrawer(), closeMobileFilterDrawerOnBackdrop(e), openSortMenuMobile(), mobileQuickSelect(group), clearMobileSelectedArtists()
- Modals: closeModal(), closeModalOnBackdrop(e), navigateModalPrev(), navigateModalNext(), triggerOutboundAffiliate(prod, src), shareProduct(prod), toggleCryptoModal(), closeCryptoModalOnBackdrop(e), toggleQr(coin), toggleAllQrs()
- UI Utilities: toggleTheme(), onCurrencyChange(val), setViewMode(mode), goToPage(page), changePerPage(val), changeSort(val), copyToClipboard(text, msg), shareWishlistUrl(), exportWishlistHaul(), exportAllPreOrdersIcs(), dismissTrustNotice(), onImgLoadError(img)

## 2. Protected Container IDs (Populated Dynamically via JS)
These containers must exist as empty target tags in index.html; scripts render inner HTML:
- #product-container (Grid/list product card mount)
- #empty-state (Toggled hidden/block when 0 items match)
- #search-autocomplete-box (Dropdown items)
- #mega-menu-columns-container (Rendered franchise links)
- #active-artist-label (Active filter chips container)
- #haul-drawer-list (Wishlist item cards)
- #calendar-drawer-list (Pre-order schedule entries)
- #mobile-drawer-accordions & #mobile-drawer-formats (Mobile filter controls)
- #pagination-bottom (Dynamic page buttons)
- #all-currencies-group (Dynamic currency options)

## 3. Dynamic Badges & Stat IDs (Text & Counts Injected via JS)
- Catalog & Stats: #stats, #page-range-info, #direct-page-total-label, #empty-state-message
- Category Badges: #badge-cat-All, #badge-cat-Hello! Project & Up-Front, #badge-cat-AKB48 Group, #badge-cat-Sakamichi Series, #badge-cat-Stardust Planet, #badge-cat-=LOVE / Sister Groups, #badge-cat-KAWAII LAB., #badge-cat-Modern & Alternative
- Format Badges: #badge-fmt-All, #badge-fmt-Single, #badge-fmt-Album, #badge-fmt-Blu-ray, #badge-fmt-DVD, #badge-fmt-Book, #badge-fmt-Collectable
- Drawer Badges: #wishlist-count-badge, #mobile-bottom-wishlist-badge, #mobile-filter-count-badge, #mobile-selected-count
- Haul Metrics: #haul-items-count, #haul-weight-total, #haul-bracket-tier, #haul-weight-progress
- Modal Details: #modal-img, #modal-format-badge, #modal-preorder-badge, #modal-oop-badge, #modal-artist-badge, #modal-title, #modal-edition-tags, #modal-release-date, #modal-catalog-id, #modal-category, #modal-price, #modal-buy-btn, #modal-buy-btn-text

## 4. Input Elements Checked by JS
- Inputs: #search-input, #price-range, #direct-page-input, #mobile-drawer-price-range, #mega-menu-filter-input
- Selects: #currency-select, #era-select, #sort-select, #per-page-select
- Toggles: #cluster-toggle, #theme-toggle, #theme-icon, #view-mode-grid, #view-mode-list

## 5. CSS Classes & Selectors Targeted by JS
- .tab-btn (Category tabs)
- .fmt-btn (Media format buttons)
- .merch-sub-btn (Merch sub-category pills)
- .desktop-only-header-btn (Hidden on mobile)
- .crypto-qr-box (Toggled hidden for cryptocurrency QR codes)
- .layout-mobile / .layout-desktop (Applied to <html> by inline viewport script)
