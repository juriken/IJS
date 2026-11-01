/**
 * IdolJapan.store — Ambient Idol Audio Jukebox Engine
 * File path: /jukebox.js
 */

(function() {
  let isPlaying = false;
  let queue = [];
  let currentIndex = -1;
  const audioEl = document.getElementById('global-audio-player') || new Audio();
  audioEl.id = 'global-audio-player';
  if (!document.getElementById('global-audio-player')) {
    audioEl.className = 'hidden';
    document.body.appendChild(audioEl);
  }

  function shuffle(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function populateQueue() {
    if (window.allProducts && window.allProducts.length > 0) {
      const candidates = window.allProducts.filter(p => p.sample_audio || p.category === 'Hello! Project' || p.category === 'AKB48 Group');
      queue = shuffle(candidates);
    }
  }

  function updateWidgetUI(product) {
    const bar = document.getElementById('jukebox-bar');
    const title = document.getElementById('jukebox-title');
    const artist = document.getElementById('jukebox-artist');
    const img = document.getElementById('jukebox-img');
    const btn = document.getElementById('jukebox-play-btn');

    if (!bar) return;

    if (product) {
      bar.classList.remove('hidden');
      if (title) title.innerText = product.title || 'Official Sample';
      if (artist) artist.innerText = product.artist || 'Idol Artist';
      if (img) img.src = product.image || '';
      if (btn) btn.innerHTML = '<i class="fa-solid fa-pause"></i>';
    } else {
      if (btn) btn.innerHTML = '<i class="fa-solid fa-play"></i>';
    }
  }

  window.IdolJukebox = {
    start: function() {
      if (!queue.length) populateQueue();
      if (!queue.length) {
        if (typeof showToast === 'function') showToast("Loading releases for preview...", false);
        return;
      }

      currentIndex = (currentIndex + 1) % queue.length;
      const product = queue[currentIndex];
      const streamUrl = product.sample_audio || `https://www.neowing.co.jp/audio/${product.id}_01.mp3`;

      audioEl.src = streamUrl;
      audioEl.play().then(() => {
        isPlaying = true;
        updateWidgetUI(product);
        if (typeof showToast === 'function') showToast(`Playing sample: ${product.title}`);
        if (window.IdolAnalytics) window.IdolAnalytics.trackAudioSamplePlay(product);
      }).catch(() => {
        // Skip dead/missing samples automatically
        window.IdolJukebox.next();
      });
    },

    toggle: function() {
      if (isPlaying) {
        audioEl.pause();
        isPlaying = false;
        updateWidgetUI(null);
      } else {
        if (currentIndex === -1) {
          window.IdolJukebox.start();
        } else {
          audioEl.play().then(() => {
            isPlaying = true;
            updateWidgetUI(queue[currentIndex]);
          }).catch(() => window.IdolJukebox.next());
        }
      }
    },

    next: function() {
      window.IdolJukebox.start();
    },

    close: function() {
      audioEl.pause();
      isPlaying = false;
      const bar = document.getElementById('jukebox-bar');
      if (bar) bar.classList.add('hidden');
    }
  };

  audioEl.onended = () => {
    // Automatically advance to next preview
    window.IdolJukebox.next();
  };
})();
