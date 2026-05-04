/* UI Flags loader for fixed page (dry run extract) */
async function loadUiFlags() {
  try {
    const response = await fetch('data/campaign_items.json', { cache: 'no-store' });
    if (!response.ok) {
      console.warn('[ui_flags] campaign_items.json load failed:', response.status);
      return;
    }

    const items = await response.json();
    const itemMap = new Map(items.map((item) => [item.id, item]));

    document.querySelectorAll('.book-card[data-item-id]').forEach((card) => {
      const itemId = card.dataset.itemId;
      const item = itemMap.get(itemId);
      if (!item) return;
      applyUiFlagsToCard(card, item);
    });

    const htmlIds = new Set(Array.from(document.querySelectorAll('.book-card[data-item-id]')).map((el) => el.dataset.itemId));
    const jsonIds = new Set(items.map((item) => item.id));
    const missingInHtml = items.filter((item) => !htmlIds.has(item.id)).map((item) => item.id);
    const missingInJson = Array.from(htmlIds).filter((id) => !jsonIds.has(id));

    if (missingInHtml.length || missingInJson.length) {
      console.warn('[ui_flags] id mismatch', { missingInHtml, missingInJson });
    }

    console.log('[ui_flags] applied:', items.length);
  } catch (error) {
    console.warn('[ui_flags] apply failed:', error);
  }
}

function applyUiFlagsToCard(card, item) {
  const deadline = card.querySelector('.deadline');
  const flags = item.ui_flags || {};

  if (deadline) {
    deadline.classList.remove('is-urgent', 'is-blink');
  }
  card.classList.remove('is-ai-push', 'is-manual-push');

  if (!deadline) return;

  if (flags.urgent) deadline.classList.add('is-urgent');
  if (flags.blink) deadline.classList.add('is-blink');

  if (flags.source === 'manual_override') {
    card.classList.add('is-manual-push');
  } else if (flags.blink) {
    card.classList.add('is-ai-push');
  }
}

/* Execute after page load */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadUiFlags);
} else {
  loadUiFlags();
}
