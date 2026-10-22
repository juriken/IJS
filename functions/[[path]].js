/**
 * Cloudflare Pages Functions: Dynamic Edge Open Graph & Metadata Injection
 * File path: /functions/[[path]].js
 */

const BOT_USER_AGENTS = [
  'twitterbot',
  'facebookexternalhit',
  'discordbot',
  'telegrambot',
  'whatsapp',
  'slackbot',
  'applebot',
  'baiduspider',
  'bingbot',
  'googlebot',
  'yandex'
];

function isSocialBot(userAgent) {
  if (!userAgent) return false;
  const ua = userAgent.toLowerCase();
  return BOT_USER_AGENTS.some(bot => ua.includes(bot));
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const userAgent = request.headers.get('user-agent') || '';
  const url = new URL(request.url);

  if (!isSocialBot(userAgent)) {
    return next();
  }

  let productId = url.searchParams.get('id');
  if (!productId) {
    const pathMatch = url.pathname.match(/\/product\/([A-Za-z0-9_\-\.]+)/);
    if (pathMatch) productId = pathMatch[1];
  }

  if (!productId) {
    return next();
  }

  const response = await next();

  let product = null;
  try {
    let catalogRes = await env.ASSETS.fetch(new URL('/catalog-index.json', url.origin).toString());
    if (catalogRes.ok) {
      const indexData = await catalogRes.json();
      product = indexData[productId] || null;
    }

    if (!product) {
      catalogRes = await env.ASSETS.fetch(new URL('/products.json', url.origin).toString());
      if (catalogRes.ok) {
        const fullData = await catalogRes.json();
        product = fullData[productId] || null;
      }
    }
  } catch (err) {
    return response;
  }

  if (!product) {
    return response;
  }

  const title = escapeHtml(`${product.title} — ${product.artist}`);
  const description = escapeHtml(
    `Official Japanese release by ${product.artist}. Catalog ID: ${product.id}. CDJapan Price: ${product.price || 'Official Retail'}. Street Date: ${product.release_date || 'Available Now'}. Directly fulfilled from Tokyo with Oricon chart eligibility.`
  );
  const imageUrl = product.image || `${url.origin}/favicon.ico`;
  const canonicalUrl = `${url.origin}/?id=${encodeURIComponent(product.id)}`;

  return new HTMLRewriter()
    .on('title', {
      element(e) {
        e.setInnerContent(`${title} | IdolJapan.store`);
      }
    })
    .on('meta[name="title"]', {
      element(e) {
        e.setAttribute('content', `${title} | IdolJapan.store`);
      }
    })
    .on('meta[name="description"]', {
      element(e) {
        e.setAttribute('content', description);
      }
    })
    .on('meta[property="og:title"]', {
      element(e) {
        e.setAttribute('content', title);
      }
    })
    .on('meta[property="og:description"]', {
      element(e) {
        e.setAttribute('content', description);
      }
    })
    .on('meta[property="og:image"]', {
      element(e) {
        e.setAttribute('content', imageUrl);
      }
    })
    .on('meta[property="og:url"]', {
      element(e) {
        e.setAttribute('content', canonicalUrl);
      }
    })
    .on('meta[name="twitter:title"]', {
      element(e) {
        e.setAttribute('content', title);
      }
    })
    .on('meta[name="twitter:description"]', {
      element(e) {
        e.setAttribute('content', description);
      }
    })
    .on('meta[name="twitter:image"]', {
      element(e) {
        e.setAttribute('content', imageUrl);
      }
    })
    .on('meta[name="twitter:url"]', {
      element(e) {
        e.setAttribute('content', canonicalUrl);
      }
    })
    .transform(response);
}
