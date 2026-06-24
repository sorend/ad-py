/* Photo table: scatter animation + drag-to-move + click-to-open */
(function () {
  'use strict';

  /* ── Dimensions (keep in sync with CSS --photo-width / --photo-img-h) ── */
  var PHOTO_W = 220;
  var PHOTO_H = 275; /* approx rendered card height (10+190+50+padding) */

  var maxZ = 100;
  var activeDrag = null; /* single active drag state */

  /* ── Global pointer tracking (one listener pair for the whole page) ───── */
  document.addEventListener('mousemove', function (e) {
    if (activeDrag) activeDrag.move(e.clientX, e.clientY);
  });
  document.addEventListener('mouseup', function (e) {
    if (activeDrag) { activeDrag.end(e.clientX, e.clientY); activeDrag = null; }
  });

  /* ── Scatter photos across the viewport with a "thrown" animation ─────── */
  function scatter() {
    var feed = document.getElementById('feed');
    if (!feed) return;

    var photos = Array.prototype.slice.call(feed.querySelectorAll('.photo'));
    if (!photos.length) return;

    var W  = window.innerWidth;
    var H  = window.innerHeight;
    var cx = W / 2 - PHOTO_W / 2;
    var cy = H / 2 - PHOTO_H / 2;

    /* Info-panel exclusion zone (bottom-right, roughly 210×230 px) */
    var excX = W  - 232;
    var excY = H  - 252;

    photos.forEach(function (photo, i) {
      /* Pick a random final position, avoiding the info-panel corner */
      var x, y, tries = 0;
      do {
        var margin = 28;
        x = margin + Math.random() * Math.max(0, W - PHOTO_W - margin * 2);
        y = margin + Math.random() * Math.max(0, H - PHOTO_H - margin * 2);
        tries++;
      } while (tries < 12 && x > excX && y > excY);

      var rot = (Math.random() - 0.5) * 22; /* –11° … +11° */

      /* Place card at centre, invisible & tiny – ready to "fly out" */
      photo.style.left      = cx + 'px';
      photo.style.top       = cy + 'px';
      photo.style.opacity   = '0';
      photo.style.transform = 'rotate(0deg) scale(0.35)';
      photo.style.zIndex    = String(photos.length - i);

      /* Staggered throw animation – oldest thrown first, newest lands on top */
      var delay = (photos.length - 1 - i) * 55 + 60;
      setTimeout(function () {
        photo.style.transition =
          'left 0.45s cubic-bezier(0.22, 1.18, 0.36, 1),' +
          'top  0.45s cubic-bezier(0.22, 1.18, 0.36, 1),' +
          'transform 0.45s cubic-bezier(0.22, 1.18, 0.36, 1),' +
          'opacity 0.22s ease';
        photo.style.left      = x + 'px';
        photo.style.top       = y + 'px';
        photo.style.transform = 'rotate(' + rot + 'deg) scale(1)';
        photo.style.opacity   = '1';

        /* After animation settles, keep only the shadow transition */
        setTimeout(function () {
          photo.style.transition = 'box-shadow 0.2s ease';
          photo.dataset.rot = String(rot);
        }, 460);
      }, delay);
    });

    makeDraggable(photos);
  }

  /* ── Wire up drag + click behaviour on a set of photo cards ──────────── */
  function makeDraggable(photos) {
    photos.forEach(function (photo) {
      /* Mouse */
      photo.addEventListener('mousedown', function (e) {
        if (e.button !== 0) return;
        e.preventDefault();
        activeDrag = createDragState(photo, e.clientX, e.clientY);
      });

      /* Touch */
      photo.addEventListener('touchstart', function (e) {
        var t = e.touches[0];
        activeDrag = createDragState(photo, t.clientX, t.clientY);
      }, { passive: true });

      photo.addEventListener('touchmove', function (e) {
        if (activeDrag && activeDrag.photo === photo) {
          e.preventDefault();
          var t = e.touches[0];
          activeDrag.move(t.clientX, t.clientY);
        }
      }, { passive: false });

      photo.addEventListener('touchend', function (e) {
        if (activeDrag && activeDrag.photo === photo) {
          var t = e.changedTouches[0];
          activeDrag.end(t.clientX, t.clientY);
          activeDrag = null;
        }
      });
    });
  }

  /* ── Create a drag-state object for one pointer interaction ────────────── */
  function createDragState(photo, clientX, clientY) {
    var rect   = photo.getBoundingClientRect();
    var ox     = clientX - rect.left;   /* offset within the card */
    var oy     = clientY - rect.top;
    var startX = clientX;
    var startY = clientY;
    var moved  = false;

    photo.style.zIndex     = String(++maxZ);
    photo.style.transition = 'none';
    photo.classList.add('is-dragging');

    var rot = parseFloat(photo.dataset.rot || '0');

    return {
      photo: photo,

      move: function (cx, cy) {
        var dx = cx - startX;
        var dy = cy - startY;
        if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        photo.style.left      = (cx - ox) + 'px';
        photo.style.top       = (cy - oy) + 'px';
        photo.style.transform = 'rotate(' + rot + 'deg)';
      },

      end: function (cx, cy) {
        photo.classList.remove('is-dragging');
        photo.style.transition = 'box-shadow 0.2s ease';
        /* Open link only on a genuine click (no significant movement) */
        if (!moved) {
          var href = photo.dataset.href;
          if (href) window.open(href, '_blank', 'noopener,noreferrer');
        }
      }
    };
  }

  /* ── Hook into htmx: scatter once the feed fragment is in the DOM ─────── */
  document.addEventListener('htmx:afterSwap', function (e) {
    var target = e.detail && e.detail.target;
    if (target && target.id === 'feed') {
      requestAnimationFrame(scatter);
    }
  });

}());
