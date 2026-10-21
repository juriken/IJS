/**
 * IdolJapan.store — Outbound Affiliate Telemetry & Conversion Engine
 * File path: /analytics.js
 */

(function() {
  const STORAGE_KEY = 'idoljapan_telemetry_events';
  const MAX_EVENTS = 250;

  function recordEvent(eventName, eventData = {}) {
    try {
      const payload = {
        event: eventName,
        data: eventData,
        timestamp: new Date().toISOString(),
        referrer: document.referrer || 'direct',
        viewport: window.innerWidth <= 768 ? 'mobile' : 'desktop'
      };

      const raw = localStorage.getItem(STORAGE_KEY);
      const list = raw ? JSON.parse(raw) : [];
      list.push(payload);

      if (list.length > MAX_EVENTS) {
        list.splice(0, list.length - MAX_EVENTS);
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));

      // Optional: Forward to GA4 if initialized on the page
      if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, eventData);
      }
    } catch (e) {
      console.warn('Telemetry event omitted:', e);
    }
  }

  // Global telemetry hooks accessible to index.html
  window.IdolAnalytics = {
    trackProductView: function(product) {
      if (!product) return;
      recordEvent('view_release_modal', {
        id: product.id,
        title: product.title,
        artist: product.artist,
        category: product.category,
        availability: product.availability || 'instock'
      });
    },

    trackAffiliateClick: function(product, triggerSource) {
      if (!product) return;
      recordEvent('affiliate_outbound_click', {
        id: product.id,
        title: product.title,
        artist: product.artist,
        category: product.category,
        price: product.price,
        source: triggerSource || 'direct'
      });
    },

    trackAudioSamplePlay: function(product) {
      if (!product) return;
      recordEvent('play_audio_sample', {
        id: product.id,
        title: product.title,
        artist: product.artist
      });
    },

    trackWishlistToggle: function(product, isAdded) {
      if (!product) return;
      recordEvent(isAdded ? 'add_to_wishlist' : 'remove_from_wishlist', {
        id: product.id,
        title: product.title,
        artist: product.artist
      });
    },

    getTelemetryReport: function() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (e) {
        return [];
      }
    },

    clearTelemetry: function() {
      localStorage.removeItem(STORAGE_KEY);
    }
  };
})();
