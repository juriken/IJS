/**
 * IdolJapan.store — High-Performance IndexedDB Storage Engine
 * File path: /db.js
 */

(function() {
  const DB_NAME = 'IdolJapanCatalogDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'products';

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
          store.createIndex('artist', 'artist', { unique: false });
          store.createIndex('category', 'category', { unique: false });
          store.createIndex('availability', 'availability', { unique: false });
        }
      };

      request.onsuccess = (event) => resolve(event.target.result);
      request.onerror = (event) => reject(event.target.error);
    });
  }

  window.IdolDB = {
    saveCatalog: async function(items) {
      if (!Array.isArray(items) || items.length === 0) return;
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.clear();

        for (const item of items) {
          store.put(item);
        }

        return new Promise((resolve) => {
          tx.oncomplete = () => resolve(true);
          tx.onerror = () => resolve(false);
        });
      } catch (e) {
        console.warn('IndexedDB write skipped:', e);
        return false;
      }
    },

    loadCatalog: async function() {
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.getAll();

        return new Promise((resolve) => {
          request.onsuccess = () => {
            const records = request.result;
            resolve(Array.isArray(records) && records.length > 0 ? records : null);
          };
          request.onerror = () => resolve(null);
        });
      } catch (e) {
        return null;
      }
    },

    clear: async function() {
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME).clear();
      } catch (e) {}
    }
  };
})();
