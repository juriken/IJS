/* ==========================================================================
   IdolJapan.store — Global Configuration, Constants & Shared State
   Path: js/config.js
   ========================================================================== */

// LocalStorage Keys
var CURRENCY_STORAGE_KEY = 'idoljapan_selected_currency';
var RATES_STORAGE_KEY = 'idoljapan_all_exchange_rates';
var RATES_TIME_KEY = 'idoljapan_exchange_rates_time';
var WISHLIST_STORAGE_KEY = 'idoljapan_fan_wishlist_ids';
var VIEW_MODE_KEY = 'idoljapan_view_mode';
var TWENTY_FOUR_HOURS_MS = 24 * 60 * 60 * 1000;

// Shared Catalog & Filtering State
var allProducts = [];
var clusteredEntities = [];
var activeFilteredList = [];
var activeFilter = 'All';
var activeArtist = 'All';
var activeMobileArtists = [];
var activeEra = 'All';
var activeFormat = 'All';
var activeMerchSubgroup = 'All';
var selectedAvailabilities = new Set(['all']);

// UI Display & Navigation Preferences (Restores saved viewMode safely)
var viewMode = (function() {
  try {
    const saved = localStorage.getItem(VIEW_MODE_KEY);
    return (saved === 'list' || saved === 'grid') ? saved : 'grid';
  } catch (e) {
    return 'grid';
  }
})();

var searchAliases = {};
var currentHoverCat = null;
var megaMenuTimer = null;
var isMegaMenuPinned = false;
var hpSoloistSubfilter = 'all';
var hpGradViewMode = 'group';

// Search Engine State
var isComposing = false;
var currentSearchToken = 0;
var searchDebounceTimeout = null;
var activeSuggestionIndex = -1;
var searchQuery = '';

// Device Layout & Pagination State
function detectDeviceLayout() {
  try {
    const mqMatch = typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 768px)').matches;
    const uaMatch = typeof navigator !== 'undefined' && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || '');
    return (mqMatch || uaMatch) ? 'mobile' : 'desktop';
  } catch (e) {
    return 'desktop';
  }
}

var layoutMode = detectDeviceLayout();
var isClusteringEnabled = true;
var maxPriceLimit = 20000;
var currentSort = 'newest';
var currentCurrency = 'USD';
var exchangeRates = {
  USD: 1.0,
  JPY: 152.4,
  EUR: 0.92,
  GBP: 0.79,
  CAD: 1.38,
  AUD: 1.51,
  TWD: 32.1,
  HKD: 7.78,
  KRW: 1375.0,
  SGD: 1.32
};
var ZERO_DECIMAL_CURRENCIES = ['JPY', 'KRW', 'VND', 'IDR', 'CLP', 'HUF', 'TWD', 'ISK', 'PYG', 'UGX'];
var currentModalProduct = null;
var currentPage = 1;
var itemsPerPage = 48;

// Date Matching Helper Map
var EN_MONTHS = {
  jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
  jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12,
  january: 1, february: 2, march: 3, april: 4,
  june: 6, july: 7, august: 8, september: 9,
  october: 10, november: 11, december: 12
};

// Agency Brand Colors for Avatars & Release Indicators
var ARTIST_BRAND_COLORS = {
  'Morning Musume': '#e11d48',
  'ANGERME': '#3b82f6',
  'Juice=Juice': '#a855f7',
  'Tsubaki Factory': '#f43f5e',
  'BEYOOOOONDS': '#10b981',
  'OCHA NORMA': '#f97316',
  'Rosy Chronicle': '#ec4899',
  'Suzuki Airi': '#ec4899',
  'Sato Masaki': '#10b981',
  'Michishige Sayumi': '#f43f5e',
  'Sayashi Riho': '#e11d48',
  'Tsukishima Kirari (Kusumi Koharu)': '#38bdf8',
  'Tsukishima Kirari': '#38bdf8',
  'Nogizaka46': '#7e22ce',
  'Sakurazaka46': '#f43f5e',
  'Hinatazaka46': '#38bdf8',
  'AKB48': '#fb7185',
  '=LOVE': '#ec4899',
  '≠ME': '#38bdf8',
  '≒JOY': '#f59e0b',
  'FRUITS ZIPPER': '#f43f5e',
  'CANDY TUNE': '#f59e0b',
  'SWEET STEADY': '#a855f7',
  'CUTIE STREET': '#fb7185',
  'BABYMETAL': '#ef4444',
  'NiziU': '#06b6d4',
  'ME:I': '#f43f5e',
  'IS:SUE': '#6366f1'
};

// Complete 79+ Idol Taxonomy Registry
var FRANCHISE_ARTISTS = {
  'Hello! Project & Up-Front': [
    'Morning Musume', 'ANGERME', 'Juice=Juice', 'Tsubaki Factory',
    'BEYOOOOONDS', 'OCHA NORMA', 'Rosy Chronicle', 'Hello Pro Kenshuusei',
    'Berryz Kobo', '℃-ute', 'Buono!', 'Country Girls', 'Kobushi Factory',
    'Tanpopo', 'Minimoni', 'v-u-den', 'W', 'GAM', 'Melon Kinenbi',
    'Taiyo to Ciscomoon', 'LoVendoR', 'PINK CRES.',
    'Suzuki Airi', 'Michishige Sayumi', 'Miyamoto Karin', 'Sato Masaki',
    'Sayashi Riho', 'Inaba Manaka', 'Tanaka Reina', 'Takahashi Ai',
    'Matsuura Aya', 'Goto Maki', 'Abe Natsumi', 'Nakazawa Yuko',
    'Fujimoto Miki', 'Mano Erina', 'Tsukishima Kirari (Kusumi Koharu)', 'Kikkawa You',
    'Up Up Girls (Kari)', 'Up Up Girls (2)',
    'Makino Maria', 'Ishida Ayumi', 'Ikuta Erina', 'Fukumura Mizuki',
    'Kudo Haruka', 'Iikubo Haruna', 'Haga Akane', 'Iida Kaori',
    'Niigaki Risa', 'Tsuji Nozomi', 'Kago Ai', 'Ishikawa Rika',
    'Wada Ayaka', 'Sasaki Rikako', 'Tamura Meimi', 'Fukuda Kanon',
    'Murota Mizuki', 'Kawamura Ayano', 'Kasahara Momona',
    'Tsugunaga Momoko', 'Yajima Maimi', 'Natsuyaki Miyabi', 'Sugaya Risako',
    'Kumai Yurina', 'Morito Chisaki', 'Satoda Mai',
    'Kanazawa Tomoko', 'Uemura Akari', 'Miyazaki Yuka', 'Dambara Ruru',
    'Kishimoto Yumeno', 'Akiyama Mao', 'Yamazaki Yuhane', 'Hamaura Ayano',
    'Yanagawa Nanami', 'Tanimoto Ami', 'Ono Mizuho', 'Onoda Saori',
    'Saito Madoka', 'Nakayama Natsume', 'Ishiguri Kanami'
  ],
  'AKB48 Group': [
    'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48',
    'Not yet', 'no3b', 'French Kiss', 'Watarirouka Hashiritai',
    'Yamamoto Sayaka', 'Maeda Atsuko', 'Oshima Yuko', 'Watanabe Mayu',
    'Kashiwagi Yuki', 'Sashihara Rino', 'Itano Tomomi'
  ],
  'Sakamichi Series': [
    'Nogizaka46', 'Sakurazaka46', 'Hinatazaka46', '22/7', 'Boku ga Mitakatta Aozora',
    'Shiraishi Mai', 'Nishino Nanase', 'Ikuta Erika', 'Saito Asuka', 'Hirate Yurina'
  ],
   'Stardust Planet': [
    'Momoiro Clover Z', 'Shiritsu Ebisu Chugaku', 'Chou Tokimeki Sendenbu',
    'TEAM SHACHI', 'BATTEN GIRLS', 'ukka'
  ],
  '=LOVE / Sister Groups': ['=LOVE', '≠ME', '≒JOY'],
  'KAWAII LAB.': ['FRUITS ZIPPER', 'CANDY TUNE', 'SWEET STEADY', 'CUTIE STREET'],
  'Modern & Alternative': [
    'NiziU', 'ME:I', 'IS:SUE',
    'BABYMETAL', 'Sakura Gakuin'
  ]
};

/* File: js/config.js | Block/Target: Mega Menu Information Architecture (Last Name First Name Order) */
// Consolidated Mega Menu Information Architecture
var MEGA_MENU_CATEGORIES = {
  'Hello! Project & Up-Front': [
    {
      id: 'hp-active',
      title: "Active Groups & Units",
      icon: "fa-fire text-rose-500",
      units: ['Morning Musume', 'ANGERME', 'Juice=Juice', 'Tsubaki Factory', 'BEYOOOOONDS', 'OCHA NORMA', 'Rosy Chronicle', 'Hello Pro Kenshuusei']
    },
    {
      id: 'hp-classic',
      title: "Classic Subunits & Historic",
      icon: "fa-crown text-amber-500",
      units: ['Berryz Kobo', '℃-ute', 'Buono!', 'Country Girls', 'Kobushi Factory', 'Tanpopo', 'Minimoni', 'v-u-den', 'W', 'GAM', 'Melon Kinenbi', 'Taiyo to Ciscomoon', 'LoVendoR', 'PINK CRES.']
    },
    {
      id: 'hp-soloists',
      title: "Career Soloists & M-line",
      icon: "fa-microphone text-purple-500",
      isSoloistColumn: true,
      units: [
        'Suzuki Airi', 'Michishige Sayumi', 'Miyamoto Karin', 'Sato Masaki',
        'Sayashi Riho', 'Inaba Manaka', 'Tanaka Reina', 'Takahashi Ai',
        'Matsuura Aya', 'Goto Maki', 'Abe Natsumi', 'Nakazawa Yuko',
        'Fujimoto Miki', 'Mano Erina', 'Tsukishima Kirari (Kusumi Koharu)', 'Kikkawa You',
        'Up Up Girls (Kari)', 'Up Up Girls (2)'
      ]
    },
    {
      id: 'hp-graduates',
      title: "Group Graduates & Photobooks",
      icon: "fa-book-open text-emerald-500",
      isGraduateColumn: true,
      clusters: [
        {
          parent: "Morning Musume Alumni",
          era: "mixed",
          units: ['Makino Maria', 'Ishida Ayumi', 'Ikuta Erina', 'Fukumura Mizuki', 'Kudo Haruka', 'Iikubo Haruna', 'Haga Akane', 'Iida Kaori', 'Niigaki Risa', 'Tsuji Nozomi', 'Kago Ai', 'Ishikawa Rika']
        },
        {
          parent: "ANGERME / S/mileage Alumni",
          era: "expansion",
          units: ['Wada Ayaka', 'Sasaki Rikako', 'Tamura Meimi', 'Fukuda Kanon', 'Murota Mizuki', 'Kawamura Ayano', 'Kasahara Momona']
        },
        {
          parent: "Berryz / ℃-ute Alumni",
          era: "platinum",
          units: ['Tsugunaga Momoko', 'Yajima Maimi', 'Natsuyaki Miyabi', 'Sugaya Risako', 'Kumai Yurina', 'Morito Chisaki', 'Satoda Mai']
        },
        {
          parent: "Juice=Juice & Newer Alumni",
          era: "modern",
          units: ['Kanazawa Tomoko', 'Uemura Akari', 'Miyazaki Yuka', 'Dambara Ruru', 'Kishimoto Yumeno', 'Akiyama Mao', 'Yamazaki Yuhane', 'Hamaura Ayano', 'Yanagawa Nanami']
        }
      ]
    }
  ],
  'AKB48 Group': [
    {
      title: "Theater Flagships",
      icon: "fa-landmark text-rose-500",
      units: ['AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48']
    },
    {
      title: "Official Subunits",
      icon: "fa-star text-amber-500",
      units: ['Not yet', 'no3b', 'French Kiss', 'Watarirouka Hashiritai']
    },
    {
      title: "Legendary Graduates",
      icon: "fa-award text-purple-500",
      units: ['Yamamoto Sayaka', 'Maeda Atsuko', 'Oshima Yuko', 'Watanabe Mayu', 'Kashiwagi Yuki', 'Sashihara Rino', 'Itano Tomomi']
    }
  ],
  'Sakamichi Series': [
    {
      title: "Sakamichi 46 Series",
      icon: "fa-mountain text-sky-500",
      units: ['Nogizaka46', 'Sakurazaka46', 'Hinatazaka46']
    },
    {
      title: "Sakamichi 46 & Official Rivals / Digital",
      icon: "fa-shield-halved text-purple-500",
      units: ['22/7', 'Boku ga Mitakatta Aozora']
    },
    {
      title: "Graduate Soloists",
      icon: "fa-feather text-rose-500",
      units: ['Shiraishi Mai', 'Nishino Nanase', 'Ikuta Erika', 'Saito Asuka', 'Hirate Yurina']
    }
  ],
   'Stardust Planet': [
    {
      title: "Flagship Groups",
      icon: "fa-star text-amber-500",
      units: ['Momoiro Clover Z', 'Shiritsu Ebisu Chugaku', 'Chou Tokimeki Sendenbu']
    },
    {
      title: "Branch & Regional Units",
      icon: "fa-compass text-teal-500",
      units: ['TEAM SHACHI', 'BATTEN GIRLS', 'ukka']
    }
  ],
  '=LOVE / Sister Groups': [
    {
      title: "=LOVE (Equal Love)",
      icon: "fa-heart text-pink-500",
      units: ['=LOVE']
    },
    {
      title: "≠ME (Not Equal Me)",
      icon: "fa-sparkles text-sky-400",
      units: ['≠ME']
    },
    {
      title: "≒JOY (Nearly Equal Joy)",
      icon: "fa-wand-magic-sparkles text-amber-400",
      units: ['≒JOY']
    }
  ],
  'KAWAII LAB.': [
    {
      title: "KAWAII LAB. Units",
      icon: "fa-ribbon text-rose-400",
      units: ['FRUITS ZIPPER', 'CANDY TUNE', 'SWEET STEADY', 'CUTIE STREET']
    }
  ],
  'Modern & Alternative': [
    {
      title: "Produce 101 & Global Units",
      icon: "fa-bolt text-emerald-500",
      units: ['NiziU', 'ME:I', 'IS:SUE']
    },
    {
      title: "Alternative, Rock & Loud",
      icon: "fa-guitar text-stone-800 dark:text-stone-200",
      units: ['BABYMETAL', 'Sakura Gakuin']
    },
    {
      title: "Ecosystem Branches (Coming Soon)",
      icon: "fa-cubes text-stone-400",
      units: [],
      placeholderText: "WACK (BiSH/ExWHYZ), Chika / Live Idols & 2.5D Anime Idols (Love Live!) indexing currently in staging."
    }
  ]
};

var PLACEHOLDER_IMG = "data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 300 300'%3E%3Crect width='300' height='300' fill='%23f5f5f4'/%3E%3Ccircle cx='150' cy='150' r='70' fill='%23e7e5e4'/%3E%3Ccircle cx='150' cy='150' r='25' fill='%23f5f5f4'/%3E%3Ctext x='150' y='270' font-family='sans-serif' font-size='14' font-weight='bold' fill='%23a8a29e' text-anchor='middle'%3ECDJapan Release%3C/text%3E%3C/svg%3E";

var MEDIA_WEIGHTS_GRAMS = {
  'Single': 85,
  'Album': 130,
  'CD': 110,
  'Blu-ray': 180,
  'DVD': 140,
  'Book': 480,
  'Collectable': 160,
  'Other': 140
};

// Bidirectional Name Bridge (Resolves Last-First and First-Last dynamically)
var IDOL_NAME_ALIASES = {
  'Suzuki Airi': 'Airi Suzuki',
  'Michishige Sayumi': 'Sayumi Michishige',
  'Miyamoto Karin': 'Karin Miyamoto',
  'Sato Masaki': 'Masaki Sato',
  'Sayashi Riho': 'Riho Sayashi',
  'Inaba Manaka': 'Manaka Inaba',
  'Tanaka Reina': 'Reina Tanaka',
  'Takahashi Ai': 'Ai Takahashi',
  'Matsuura Aya': 'Aya Matsuura',
  'Goto Maki': 'Maki Goto',
  'Abe Natsumi': 'Natsumi Abe',
  'Nakazawa Yuko': 'Yuko Nakazawa',
  'Fujimoto Miki': 'Miki Fujimoto',
  'Mano Erina': 'Erina Mano',
  'Tsukishima Kirari (Kusumi Koharu)': 'Tsukishima Kirari',
  'Makino Maria': 'Maria Makino',
  'Ishida Ayumi': 'Ayumi Ishida',
  'Ikuta Erina': 'Erina Ikuta',
  'Fukumura Mizuki': 'Mizuki Fukumura',
  'Kudo Haruka': 'Haruka Kudo',
  'Iikubo Haruna': 'Haruna Iikubo',
  'Haga Akane': 'Akane Haga',
  'Iida Kaori': 'Kaori Iida',
  'Niigaki Risa': 'Risa Niigaki',
  'Tsuji Nozomi': 'Nozomi Tsuji',
  'Kago Ai': 'Ai Kago',
  'Ishikawa Rika': 'Rika Ishikawa',
  'Wada Ayaka': 'Ayaka Wada',
  'Sasaki Rikako': 'Rikako Sasaki',
  'Tamura Meimi': 'Meimi Tamura',
  'Fukuda Kanon': 'Kanon Fukuda',
  'Murota Mizuki': 'Mizuki Murota',
  'Kawamura Ayano': 'Ayano Kawamura',
  'Kasahara Momona': 'Momona Kasahara',
  'Tsugunaga Momoko': 'Momoko Tsugunaga',
  'Yajima Maimi': 'Maimi Yajima',
  'Natsuyaki Miyabi': 'Miyabi Natsuyaki',
  'Sugaya Risako': 'Risako Sugaya',
  'Kumai Yurina': 'Yurina Kumai',
  'Morito Chisaki': 'Chisaki Morito',
  'Satoda Mai': 'Mai Satoda',
  'Kanazawa Tomoko': 'Tomoko Kanazawa',
  'Uemura Akari': 'Akari Uemura',
  'Miyazaki Yuka': 'Yuka Miyazaki',
  'Dambara Ruru': 'Ruru Dambara',
  'Kishimoto Yumeno': 'Yumeno Kishimoto',
  'Akiyama Mao': 'Mao Akiyama',
  'Yamazaki Yuhane': 'Yuhane Yamazaki',
  'Hamaura Ayano': 'Ayano Hamaura',
  'Yanagawa Nanami': 'Nanami Yanagawa',
  'Tanimoto Ami': 'Ami Tanimoto',
  'Ono Mizuho': 'Mizuho Ono',
  'Onoda Saori': 'Saori Onoda',
  'Saito Madoka': 'Madoka Saito',
  'Nakayama Natsume': 'Natsume Nakayama',
  'Ishiguri Kanami': 'Kanami Ishiguri',
  'Yamamoto Sayaka': 'Sayaka Yamamoto',
  'Maeda Atsuko': 'Atsuko Maeda',
  'Oshima Yuko': 'Yuko Oshima',
  'Watanabe Mayu': 'Mayu Watanabe',
  'Kashiwagi Yuki': 'Yuki Kashiwagi',
  'Sashihara Rino': 'Rino Sashihara',
  'Itano Tomomi': 'Tomomi Itano',
  'Shiraishi Mai': 'Mai Shiraishi',
  'Nishino Nanase': 'Nanase Nishino',
  'Ikuta Erika': 'Erika Ikuta',
  'Saito Asuka': 'Asuka Saito',
  'Hirate Yurina': 'Yurina Hirate'
};

function matchesArtistName(productArtist, targetArtist) {
  if (!productArtist || !targetArtist) return false;
  if (productArtist === targetArtist) return true;
  if (IDOL_NAME_ALIASES[targetArtist] === productArtist) return true;
  if (IDOL_NAME_ALIASES[productArtist] === targetArtist) return true;
  if ((targetArtist === 'Tsukishima Kirari (Kusumi Koharu)' || targetArtist === 'Tsukishima Kirari') && (productArtist === 'Tsukishima Kirari' || productArtist.includes('Kirari'))) return true;
  if ((productArtist === 'Tsukishima Kirari (Kusumi Koharu)' || productArtist === 'Tsukishima Kirari') && (targetArtist === 'Tsukishima Kirari' || targetArtist.includes('Kirari'))) return true;
  return false;
}
