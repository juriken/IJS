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

/* ==========================================================================
   IdolJapan.store — Search Engine & Autocomplete Logic
   Path: js/search.js
   ========================================================================== */

var searchIndex = null;
var searchCacheMap = new Map();
var MAX_SEARCH_CACHE_SIZE = 200;

var SEARCH_GROUP_ABBREVIATIONS = {
  'Morning Musume': ['mm', 'momusu', 'morning', 'モー娘', 'モーニング娘', 'モーニング娘。', 'モーニング', '早安少女組'],
  'Hello! Project & Up-Front': ['hp', 'h!p', 'hellopro', 'ハロプロ', 'ハロ', 'upfront', 'up-front'],
  'ANGERME': ['anju', 'angerme', 'アンジュ', 'アンジュルム', 'smileage', 'スマイレージ'],
  'Juice=Juice': ['jj', 'juice', 'ジュース', 'ジュースジュース', 'j=j'],
  'Tsubaki Factory': ['tsubaki', 'つばき', 'つばきファクトリー'],
  'BEYOOOOONDS': ['beyo', 'ビヨ', 'ビヨーンズ', 'chica#tetsu', 'ame no mori kawa umi', 'seasoningS'],
  'OCHA NORMA': ['ocha', 'オチャ', 'オチャノーマ'],
  'Rosy Chronicle': ['rosy', 'ロージー', 'ロージークロニクル'],
  'Berryz Kobo': ['berryz', 'ベリーズ', 'ベリーズ工房'],
  '℃-ute': ['cute', 'c-ute', 'キュート'],
  'Buono!': ['buono', 'ボーノ'],
  'AKB48 Group': ['akb', 'akb48', 'ske', 'ske48', 'nmb', 'nmb48', 'hkt', 'hkt48', 'ngt', 'ngt48', 'stu', 'stu48', '48g'],
  'Sakamichi Series': ['sakamichi', '坂道', '46g', 'nogi', 'nogizaka', '乃木坂', '乃木坂46', 'saku', 'sakurazaka', '櫻坂', '櫻坂46', 'keyaki', 'keyakizaka', '欅坂', '欅坂46', 'hinata', 'hinatazaka', '日向坂', '日向坂46', 'bokuao', '僕青'],
  'Stardust Planet': ['momoclo', 'mcz', 'ももクロ', 'ももいろクローバーz', 'ebichu', 'エビ中', '私立恵比寿中学', 'tokisen', 'とき宣', '超ときめき宣伝部', 'shachi', 'team shachi'],
  '=LOVE / Sister Groups': ['ikolove', 'イコラブ', '=love', 'equal love', 'noime', 'ノイミー', '≠me', 'not equal me', 'niajoy', 'ニアジョイ', '≒joy', 'nearly equal joy'],
  'KAWAII LAB.': ['fruits zipper', 'fz', 'ふるっぱー', 'candy tune', 'きゃんちゅー', 'sweet steady', 'すいすて', 'cutie street', 'きゅーすと'],
  'Modern & Alternative': ['babymetal', 'bm', 'ベビメタ', 'niziu', 'ニジュー', 'me:i', 'mei', 'ミーアイ', 'is:sue', 'issue', 'イッシュ', 'sakura gakuin', 'さくら学院']
};

var IDOL_NAME_VARIATIONS = {
  'Suzuki Airi': ['Airi Suzuki', '鈴木愛理', 'すずきあいり', 'あいりーん'],
  'Michishige Sayumi': ['Sayumi Michishige', '道重さゆみ', 'さゆみん'],
  'Miyamoto Karin': ['Karin Miyamoto', '宮本佳林', 'かりん'],
  'Sato Masaki': ['Masaki Sato', '佐藤優樹', 'まーちゃん'],
  'Sayashi Riho': ['Riho Sayashi', '鞘師里保', 'りほりほ'],
  'Inaba Manaka': ['Manaka Inaba', '稲場愛香', 'まなかん'],
  'Tanaka Reina': ['Reina Tanaka', '田中れいな'],
  'Takahashi Ai': ['Ai Takahashi', '高橋愛'],
  'Matsuura Aya': ['Aya Matsuura', '松浦亜弥', 'あやや'],
  'Goto Maki': ['Maki Goto', '後藤真希', 'ごっちん'],
  'Abe Natsumi': ['Natsumi Abe', '安倍なつみ', 'なっち'],
  'Tsukishima Kirari': ['Tsukishima Kirari (Kusumi Koharu)', 'Koharu Kusumi', 'Kusumi Koharu', '久住小春', '月島きらり'],
  'Makino Maria': ['Maria Makino', '牧野真莉愛'],
  'Ishida Ayumi': ['Ayumi Ishida', '石田亜佑美'],
  'Ikuta Erina': ['Erina Ikuta', '生田衣梨奈'],
  'Fukumura Mizuki': ['Mizuki Fukumura', '譜久村聖'],
  'Kudo Haruka': ['Haruka Kudo', '工藤遥'],
  'Sasaki Rikako': ['Rikako Sasaki', '佐々木莉佳子'],
  'Shiraishi Mai': ['Mai Shiraishi', '白石麻衣', 'まいやん'],
  'Nishino Nanase': ['Nanase Nishino', '西野七瀬', 'なぁちゃん'],
  'Ikuta Erika': ['Erika Ikuta', '生田絵梨花', 'いくちゃん'],
  'Saito Asuka': ['Asuka Saito', '齋藤飛鳥', 'あすか'],
  'Hirate Yurina': ['Yurina Hirate', '平手友梨奈', 'てち'],
  'Yamamoto Sayaka': ['Sayaka Yamamoto', '山本彩', 'さや姉'],
  'Maeda Atsuko': ['Atsuko Maeda', '前田敦子', 'あっちゃん'],
  'Oshima Yuko': ['Yuko Oshima', '大島優子'],
  'Watanabe Mayu': ['Mayu Watanabe', '渡辺麻友', 'まゆゆ'],
  'Kashiwagi Yuki': ['Yuki Kashiwagi', '柏木由紀', 'ゆきりん'],
  'Sashihara Rino': ['Rino Sashihara', '指原莉乃', 'さっしー']
};

function normalizeSearchString(str) {
  if (!str) return '';
  return String(str)
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[ōóòôõ]/g, 'o')
    .replace(/[ūúùû]/g, 'u')
    .replace(/[āáàâã]/g, 'a')
    .replace(/[ēéèê]/g, 'e')
    .replace(/[īíìî]/g, 'i')
    .replace(/ou/g, 'o')
    .replace(/oo/g, 'o')
    .replace(/uu/g, 'u')
    .replace(/kiku/g, 'kikka')
    .replace(/[\u30a1-\u30f6]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0x60));
}

function cleanAlphanumericOnly(str) {
  if (!str) return '';
  return String(str).toLowerCase().replace(/[^a-z0-9]/gi, '');
}

function computeLevenshteinDistance(a, b) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;

  const row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = i;
    for (let j = 1; j <= b.length; j++) {
      const val = (a[i - 1] === b[j - 1]) ? row[j - 1] : Math.min(row[j - 1] + 1, prev + 1, row[j] + 1);
      row[j - 1] = prev;
      prev = val;
    }
    row[b.length] = prev;
  }
  return row[b.length];
}

function isFuzzyTokenMatch(targetToken, queryToken) {
  if (!targetToken || !queryToken) return false;
  if (targetToken.includes(queryToken)) return true;
  if (queryToken.length >= 4 && queryToken.length <= 6) {
    return computeLevenshteinDistance(targetToken.slice(0, queryToken.length), queryToken) <= 1;
  }
  if (queryToken.length >= 7) {
    return computeLevenshteinDistance(targetToken.slice(0, queryToken.length), queryToken) <= 2;
  }
  return false;
}

function buildSearchCache(products) {
  const source = Array.isArray(products) ? products : (typeof allProducts !== 'undefined' ? allProducts : []);
  searchIndex = source.map((p, idx) => {
    const rawId = String(p.id || '').trim();
    const cleanId = cleanAlphanumericOnly(rawId);
    const rawArtist = String(p.artist || '').trim();
    const rawTitle = String(p.title || '').trim();
    const cleanTitle = (typeof stripTitlePrefixes === 'function') ? stripTitlePrefixes(rawTitle) : rawTitle;
    const rawCat = String(p.category || '').trim();
    const rawFmt = (typeof getItemFormatCategory === 'function') ? getItemFormatCategory(p) : 'Other';
    const isAvail = (typeof isOutOfPrint === 'function') ? !isOutOfPrint(p) : true;
    const isUpcoming = (typeof isPreOrder === 'function') ? isPreOrder(p) : false;

    const artistNorm = normalizeSearchString(rawArtist);
    const titleNorm = normalizeSearchString(cleanTitle);
    const descNorm = normalizeSearchString(p.description || '');

    const nameAliases = [artistNorm];
    if (IDOL_NAME_VARIATIONS[rawArtist]) {
      IDOL_NAME_VARIATIONS[rawArtist].forEach(alias => nameAliases.push(normalizeSearchString(alias)));
    }
    const parts = rawArtist.split(/\s+/);
    if (parts.length === 2) {
      nameAliases.push(normalizeSearchString(`${parts[1]} ${parts[0]}`));
    }

    return {
      index: idx,
      id: rawId,
      cleanId: cleanId,
      artist: rawArtist,
      artistNorm: artistNorm,
      artistAliases: nameAliases,
      title: rawTitle,
      cleanTitle: cleanTitle,
      titleNorm: titleNorm,
      category: rawCat,
      format: rawFmt,
      descNorm: descNorm,
      isAvailable: isAvail,
      isPreOrder: isUpcoming,
      price: p.price,
      image: p.image,
      ref: p
    };
  });
  searchCacheMap.clear();
}

function updateSearchCache(products) {
  buildSearchCache(products);
}

function calculateProductSearchScore(doc, queryNorm, queryClean, queryTokens) {
  let score = 0;

  if (queryClean.length >= 3) {
    if (doc.cleanId === queryClean) score += 15000;
    else if (doc.cleanId.startsWith(queryClean)) score += 12000;
    else if (doc.cleanId.includes(queryClean)) score += 9500;
  }
  if (doc.id.toLowerCase().includes(queryNorm)) {
    score = Math.max(score, 10000);
  }

  let groupMatch = false;
  for (const alias of doc.artistAliases) {
    if (alias === queryNorm) {
      score += 8500;
      groupMatch = true;
      break;
    } else if (alias.startsWith(queryNorm)) {
      score += 7800;
      groupMatch = true;
      break;
    } else if (alias.includes(queryNorm)) {
      score += 7000;
      groupMatch = true;
      break;
    }
  }

  if (!groupMatch) {
    for (const [canonicalGroup, abbreviations] of Object.entries(SEARCH_GROUP_ABBREVIATIONS)) {
      if (doc.artist === canonicalGroup || doc.category === canonicalGroup) {
        if (abbreviations.some(a => normalizeSearchString(a) === queryNorm || queryNorm.includes(normalizeSearchString(a)))) {
          score += 7500;
          groupMatch = true;
          break;
        }
      }
    }
  }

  if (!groupMatch) {
    for (const [memName, memAliases] of Object.entries(IDOL_NAME_VARIATIONS)) {
      if (doc.artistNorm.includes(normalizeSearchString(memName)) || doc.titleNorm.includes(normalizeSearchString(memName))) {
        if (memAliases.some(a => normalizeSearchString(a).includes(queryNorm) || queryNorm.includes(normalizeSearchString(a)))) {
          score += 6200;
          break;
        }
      }
    }
  }

  if (doc.titleNorm.startsWith(queryNorm)) score += 4800;
  else if (doc.titleNorm.includes(queryNorm)) score += 4000;

  if (queryTokens.length > 1) {
    let tokensMatched = 0;
    queryTokens.forEach(token => {
      if (doc.cleanId.includes(token) || doc.artistNorm.includes(token) || doc.titleNorm.includes(token) || isFuzzyTokenMatch(doc.titleNorm, token)) {
        tokensMatched++;
      }
    });
    if (tokensMatched === queryTokens.length) score += 3500;
    else if (tokensMatched > 0) score += (tokensMatched * 600);
  } else if (queryTokens.length === 1 && score === 0) {
    const singleToken = queryTokens[0];
    if (isFuzzyTokenMatch(doc.titleNorm, singleToken)) score += 2800;
    else if (isFuzzyTokenMatch(doc.artistNorm, singleToken)) score += 3200;
  }

  if (score === 0 && doc.descNorm && doc.descNorm.includes(queryNorm)) {
    score += 1500;
  }

  if (score > 0) {
    if (doc.isPreOrder) score += 50;
    else if (doc.isAvailable) score += 20;
    else score -= 4000;
  }

  return score;
}

function getMatchingProductIds(query) {
  if (!query) return null;
  const rawQ = String(query).trim();
  if (!rawQ) return null;

  const cacheKey = `ids_${rawQ.toLowerCase()}_${typeof activeFilter !== 'undefined' ? activeFilter : 'All'}`;
  if (searchCacheMap.has(cacheKey)) {
    return searchCacheMap.get(cacheKey);
  }

  if (!searchIndex || !searchIndex.length) {
    buildSearchCache(typeof allProducts !== 'undefined' ? allProducts : []);
  }

  const queryNorm = normalizeSearchString(rawQ);
  const queryClean = cleanAlphanumericOnly(rawQ);
  const queryTokens = queryNorm.split(/\s+/).filter(t => t.length > 0);

  const matchedIds = new Set();
  for (let i = 0; i < searchIndex.length; i++) {
    const doc = searchIndex[i];
    const score = calculateProductSearchScore(doc, queryNorm, queryClean, queryTokens);
    if (score > 1200) {
      matchedIds.add(doc.id);
    }
  }

  if (searchCacheMap.size >= MAX_SEARCH_CACHE_SIZE) {
    const firstKey = searchCacheMap.keys().next().value;
    searchCacheMap.delete(firstKey);
  }
  searchCacheMap.set(cacheKey, matchedIds);
  return matchedIds;
}

function matchesCatalogSearch(item, query) {
  if (!query) return true;
  if (!item) return false;
  const matchedSet = getMatchingProductIds(query);
  return matchedSet ? matchedSet.has(item.id) : true;
}

function matchesFuzzyQuery(text, query) {
  if (!text || !query) return false;
  const tNorm = normalizeSearchString(text);
  const qNorm = normalizeSearchString(query);
  if (tNorm.includes(qNorm)) return true;

  const tClean = cleanAlphanumericOnly(text);
  const qClean = cleanAlphanumericOnly(query);
  if (qClean.length >= 3 && tClean.includes(qClean)) return true;

  return isFuzzyTokenMatch(tNorm, qNorm);
}

function highlightQueryTokens(text, rawQuery) {
  if (!text) return '';
  const safeText = (typeof escapeHtml === 'function') ? escapeHtml(text) : text;
  if (!rawQuery) return safeText;

  const tokens = String(rawQuery)
    .trim()
    .split(/\s+/)
    .filter(t => t.length > 0)
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

  if (!tokens.length) return safeText;

  const regex = new RegExp(`(${tokens.join('|')})`, 'gi');
  return safeText.replace(regex, '<mark class="bg-rose-100 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 font-extrabold rounded-xs px-0.5">$1</mark>');
}

function showSearchSuggestions() {
  const box = document.getElementById('search-autocomplete-box');
  const input = document.getElementById('search-input');
  if (!box || !input) return;

  const rawQuery = (input.value || '').trim();
  if (!rawQuery) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }

  const queryNorm = normalizeSearchString(rawQuery);
  const queryClean = cleanAlphanumericOnly(rawQuery);
  const queryTokens = queryNorm.split(/\s+/).filter(t => t.length > 0);

  if (!searchIndex || !searchIndex.length) {
    buildSearchCache(typeof allProducts !== 'undefined' ? allProducts : []);
  }

  const franchiseDict = (typeof FRANCHISE_ARTISTS !== 'undefined' && FRANCHISE_ARTISTS) ? FRANCHISE_ARTISTS : {};
  const brandColors = (typeof ARTIST_BRAND_COLORS !== 'undefined' && ARTIST_BRAND_COLORS) ? ARTIST_BRAND_COLORS : {};

  const allKnownGroups = [
    'Morning Musume', 'ANGERME', 'Juice=Juice', 'Tsubaki Factory', 'BEYOOOOONDS',
    'OCHA NORMA', 'Rosy Chronicle', 'Berryz Kobo', '℃-ute', 'Buono!',
    'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48',
    'Nogizaka46', 'Sakurazaka46', 'Hinatazaka46', 'Boku ga Mitakatta Aozora',
    'Momoiro Clover Z', 'Shiritsu Ebisu Chugaku', 'Chou Tokimeki Sendenbu',
    '=LOVE', '≠ME', '≒JOY',
    'FRUITS ZIPPER', 'CANDY TUNE', 'SWEET STEADY', 'CUTIE STREET',
    'BABYMETAL', 'NiziU', 'ME:I', 'IS:SUE'
  ];

  let matchedGroup = null;
  for (const grp of allKnownGroups) {
    const grpNorm = normalizeSearchString(grp);
    if (grpNorm.includes(queryNorm) || queryNorm.includes(grpNorm)) {
      matchedGroup = grp;
      break;
    }
    const abbrs = SEARCH_GROUP_ABBREVIATIONS[grp] || [];
    if (abbrs.some(a => normalizeSearchString(a) === queryNorm || queryNorm.startsWith(normalizeSearchString(a)))) {
      matchedGroup = grp;
      break;
    }
  }

  let matchedMember = null;
  for (const [memName, memAliases] of Object.entries(IDOL_NAME_VARIATIONS)) {
    const memNorm = normalizeSearchString(memName);
    if (memNorm.includes(queryNorm) || memAliases.some(a => normalizeSearchString(a).includes(queryNorm))) {
      matchedMember = memName;
      break;
    }
  }

  const scoredReleases = [];
  for (let i = 0; i < searchIndex.length; i++) {
    const doc = searchIndex[i];
    if (!doc.isAvailable) continue;

    const score = calculateProductSearchScore(doc, queryNorm, queryClean, queryTokens);
    if (score > 1500) {
      scoredReleases.push({ doc, score });
    }
  }

  scoredReleases.sort((a, b) => b.score - a.score);

  const suggestions = [];

  if (matchedGroup) {
    suggestions.push({
      type: 'group',
      title: matchedGroup,
      badge: 'Group',
      badgeColor: brandColors[matchedGroup] || '#e11d48'
    });
  }

  if (matchedMember && (!matchedGroup || matchedMember !== matchedGroup)) {
    suggestions.push({
      type: 'member',
      title: matchedMember,
      badge: 'Soloist',
      badgeColor: brandColors[matchedMember] || '#a855f7'
    });
  }

  const releaseLimit = Math.max(2, 5 - suggestions.length);
  for (let i = 0; i < Math.min(scoredReleases.length, releaseLimit); i++) {
    const { doc } = scoredReleases[i];
    suggestions.push({
      type: 'product',
      id: doc.id,
      title: doc.cleanTitle,
      artist: doc.artist,
      price: doc.price,
      image: doc.image,
      isPreOrder: doc.isPreOrder
    });
  }

  const finalSuggestions = suggestions.slice(0, 5);

  if (!finalSuggestions.length) {
    const currentCat = (typeof activeFilter !== 'undefined') ? activeFilter : 'All';
    box.innerHTML = `
      <div class="p-3 text-center text-xs text-stone-500 dark:text-slate-400 space-y-2">
        <p>No active releases found for "<strong>${escapeHtml(rawQuery)}</strong>"</p>
        ${currentCat !== 'All' ? `
          <button onclick="setFilter('All'); triggerDebouncedSearch('${escapeHtml(rawQuery)}');" class="text-[11px] font-bold text-rose-600 dark:text-rose-400 hover:underline cursor-pointer">
            Search across All Groups →
          </button>
        ` : `
          <div class="pt-1 flex flex-wrap items-center justify-center gap-1">
            <span class="text-[10px] text-stone-400">Try:</span>
            <button onclick="selectSearchGroup('Morning Musume')" class="text-[10px] px-1.5 py-0.5 rounded bg-stone-100 dark:bg-slate-800 font-bold hover:text-rose-600">Morning Musume</button>
            <button onclick="selectSearchGroup('Nogizaka46')" class="text-[10px] px-1.5 py-0.5 rounded bg-stone-100 dark:bg-slate-800 font-bold hover:text-rose-600">Nogizaka46</button>
            <button onclick="selectSearchGroup('FRUITS ZIPPER')" class="text-[10px] px-1.5 py-0.5 rounded bg-stone-100 dark:bg-slate-800 font-bold hover:text-rose-600">FRUITS ZIPPER</button>
          </div>
        `}
      </div>
    `;
    box.classList.remove('hidden');
    return;
  }

  let html = `<div class="p-1 divide-y divide-stone-100 dark:divide-slate-800/80">`;

  finalSuggestions.forEach(item => {
    if (item.type === 'group') {
      const safeGroup = escapeHtml(item.title);
      const cleanJsArg = item.title.replace(/'/g, "\\'");
      html += `
        <button 
          type="button"
          onclick="selectSearchGroup('${cleanJsArg}')"
          class="autocomplete-item w-full text-left px-3 py-2 hover:bg-rose-50 dark:hover:bg-slate-800/90 transition flex items-center justify-between text-xs cursor-pointer rounded-lg group"
        >
          <div class="flex items-center gap-2 truncate">
            <span class="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs" style="background-color: ${item.badgeColor}"></span>
            <span class="font-bold text-stone-900 dark:text-stone-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 truncate">
              ${highlightQueryTokens(item.title, rawQuery)}
            </span>
          </div>
          <span class="text-[10px] font-black uppercase text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/80 px-2 py-0.5 rounded-full shrink-0 ml-2">Franchise</span>
        </button>
      `;
    } else if (item.type === 'member') {
      const safeMem = escapeHtml(item.title);
      const cleanJsArg = item.title.replace(/'/g, "\\'");
      html += `
        <button 
          type="button"
          onclick="selectSearchMember('${cleanJsArg}')"
          class="autocomplete-item w-full text-left px-3 py-2 hover:bg-purple-50 dark:hover:bg-slate-800/90 transition flex items-center justify-between text-xs cursor-pointer rounded-lg group"
        >
          <div class="flex items-center gap-2 truncate">
            <span class="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs" style="background-color: ${item.badgeColor}"></span>
            <span class="font-bold text-stone-900 dark:text-stone-100 group-hover:text-purple-600 dark:group-hover:text-purple-400 truncate">
              ${highlightQueryTokens(item.title, rawQuery)}
            </span>
          </div>
          <span class="text-[10px] font-black uppercase text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/80 px-2 py-0.5 rounded-full shrink-0 ml-2">Soloist</span>
        </button>
      `;
    } else {
      const safeId = escapeHtml(item.id);
      const cleanJsArg = item.id.replace(/'/g, "\\'");
      const priceFmt = (typeof formatDisplayPrice === 'function') ? formatDisplayPrice(item.price) : escapeHtml(item.price);
      const thumbUrl = (typeof getThumbnailUrl === 'function') ? getThumbnailUrl(item.image) : item.image;

      html += `
        <button 
          type="button"
          onclick="selectSearchProduct('${cleanJsArg}')"
          class="autocomplete-item w-full text-left px-3 py-1.5 hover:bg-stone-100 dark:hover:bg-slate-800/90 transition flex items-center gap-2.5 text-xs cursor-pointer rounded-lg group"
        >
          <img src="${thumbUrl}" class="w-8 h-8 object-contain rounded bg-stone-100 dark:bg-slate-800 shrink-0 border border-stone-200 dark:border-slate-700" onerror="if(typeof onImgLoadError==='function') onImgLoadError(this)" />
          <div class="flex-1 min-w-0">
            <div class="font-bold text-stone-900 dark:text-stone-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 truncate text-[11px]">
              ${highlightQueryTokens(item.title, rawQuery)}
            </div>
            <div class="text-[10px] text-stone-400 dark:text-slate-500 truncate flex items-center gap-1 font-mono">
              <span>${highlightQueryTokens(item.artist, rawQuery)}</span>
              <span>•</span>
              <span class="text-stone-600 dark:text-slate-300 font-bold">${highlightQueryTokens(item.id, rawQuery)}</span>
            </div>
          </div>
          <div class="text-right shrink-0">
            <div class="text-xs font-black text-rose-600 dark:text-rose-400 font-mono">${priceFmt}</div>
            ${item.isPreOrder ? '<span class="text-[8px] font-black text-rose-500 uppercase tracking-tighter">PRE-ORDER</span>' : ''}
          </div>
        </button>
      `;
    }
  });

  html += `</div>`;
  box.innerHTML = html;
  box.classList.remove('hidden');
}

function selectSearchGroup(groupName) {
  const box = document.getElementById('search-autocomplete-box');
  const input = document.getElementById('search-input');
  if (box) box.classList.add('hidden');
  if (input) input.value = groupName;
  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
  searchQuery = '';
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.classList.remove('hidden');
  activeFilter = 'All';
  if (typeof updateFilterButtonsUI === 'function') updateFilterButtonsUI();
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
  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
  searchQuery = '';
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.classList.remove('hidden');
  activeFilter = 'All';
  if (typeof updateFilterButtonsUI === 'function') updateFilterButtonsUI();
  if (typeof setSubArtist === 'function') setSubArtist(memberName);
  const target = document.getElementById('product-container');
  if (target) target.scrollIntoView({ behavior: 'smooth' });
}

function selectSearchProduct(productId) {
  const box = document.getElementById('search-autocomplete-box');
  if (box) box.classList.add('hidden');
  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
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
    if (query && String(query).trim().length > 0) clearBtn.classList.remove('hidden');
    else clearBtn.classList.add('hidden');
  }

  showSearchSuggestions();

  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    searchQuery = (query || '').toLowerCase().trim();
    currentPage = 1;
    if (typeof syncUrlParams === 'function') syncUrlParams();
    if (typeof render === 'function') render();
  }, 160);
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
      triggerDebouncedSearch(e.target.value);
    });

    sInput.addEventListener('keydown', (e) => {
      const box = document.getElementById('search-autocomplete-box');
      const items = box ? box.querySelectorAll('.autocomplete-item') : [];

      if (['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) {
        if (e.key === 'Enter') {
          if (activeSuggestionIndex >= 0 && activeSuggestionIndex < items.length) {
            e.preventDefault();
            items[activeSuggestionIndex].click();
          } else {
            e.preventDefault();
            if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
            searchQuery = (sInput.value || '').toLowerCase().trim();
            closeAutocomplete();
            currentPage = 1;
            if (typeof syncUrlParams === 'function') syncUrlParams();
            if (typeof render === 'function') render();
            sInput.blur();
          }
          return;
        }

        if (!box || box.classList.contains('hidden') || !items.length) return;

        if (e.key === 'ArrowDown') {
          e.preventDefault();
          activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
          highlightSuggestion(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
          highlightSuggestion(items);
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
      triggerDebouncedSearch(e.target.value);
    });

    sInput.addEventListener('click', () => {
      if ((sInput.value || '').trim()) {
        showSearchSuggestions();
      }
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