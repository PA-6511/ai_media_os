"use strict";

const FIELD_LABELS = {
  volume_label: "巻数",
  author_name: "作者",
  publisher_name: "出版社",
};

const REASON_LABELS = {
  VERIFIED_SOURCE_NOT_FOUND: "検証済みの基本情報候補がありません",
  HUMAN_REVIEW_HISTORY: "人間入力によって保護されています",
  AUTHOR_CONFLICT: "作者の候補が競合しています",
  PUBLISHER_CONFLICT: "出版社の候補が競合しています",
  VOLUME_CONFLICT: "巻数の候補が競合しています",
  REVIEW_STATUS_PROTECTED: "基本情報を更新すると再審査が必要になるため、この画面からは更新できません",
  PUBLISH_READY_PROTECTED: "公開準備済みのため、この画面からは更新できません",
  WORDPRESS_DRAFT_EXISTS: "WordPress下書きが存在するため、先に投稿との整合処理が必要です",
};

const GREEN_STATES = new Set(["READY", "APPLIED", "METADATA_AUTOFILL_APPLIED"]);
const YELLOW_STATES = new Set(["METADATA_PARTIALLY_APPLIED"]);
const ORANGE_STATES = new Set([
  "METADATA_REVIEW_REQUIRED",
  "CONFLICT",
  "AUTHOR_CONFLICT",
  "PUBLISHER_CONFLICT",
  "HUMAN_REVIEW_PROTECTED",
  "WORKFLOW_STATE_PROTECTED",
]);
const GRAY_STATES = new Set([
  "SOURCE_NOT_FOUND",
  "ALREADY_MATCHED",
  "EXISTING_VALUE_PRESERVED",
  "METADATA_ALREADY_COMPLETE",
  "METADATA_SOURCE_NOT_FOUND",
]);

const ROMAN_VOLUME_VALUES = {
  I: 1,
  V: 5,
  X: 10,
  L: 50,
  C: 100,
  D: 500,
  M: 1000,
};
const KANJI_VOLUME_DIGITS = {
  "〇": 0,
  "零": 0,
  "一": 1,
  "二": 2,
  "三": 3,
  "四": 4,
  "五": 5,
  "六": 6,
  "七": 7,
  "八": 8,
  "九": 9,
};
const KANJI_VOLUME_UNITS = {"十": 10, "百": 100, "千": 1000};

function romanVolumeNumber(value) {
  const token = value.toUpperCase();
  const validRoman = /^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$/;
  if (!token || !validRoman.test(token)) return null;
  let total = 0;
  for (let index = 0; index < token.length; index += 1) {
    const current = ROMAN_VOLUME_VALUES[token[index]];
    const following = ROMAN_VOLUME_VALUES[token[index + 1]] || 0;
    total += current < following ? -current : current;
  }
  return total > 0 ? total : null;
}

function kanjiVolumeNumber(value) {
  const characters = Array.from(value);
  if (characters.length && characters.every((character) => Object.hasOwn(KANJI_VOLUME_DIGITS, character))) {
    const number = Number(characters.map((character) => KANJI_VOLUME_DIGITS[character]).join(""));
    return number > 0 ? number : null;
  }
  if (!characters.length || characters.some((character) => (
    !Object.hasOwn(KANJI_VOLUME_DIGITS, character)
    && !Object.hasOwn(KANJI_VOLUME_UNITS, character)
  ))) return null;
  let total = 0;
  let pendingDigit = null;
  let previousUnit = 10000;
  for (const character of characters) {
    if (Object.hasOwn(KANJI_VOLUME_DIGITS, character)) {
      if (pendingDigit !== null) return null;
      pendingDigit = KANJI_VOLUME_DIGITS[character];
      continue;
    }
    const unit = KANJI_VOLUME_UNITS[character];
    if (unit >= previousUnit) return null;
    total += (pendingDigit === null ? 1 : pendingDigit) * unit;
    pendingDigit = null;
    previousUnit = unit;
  }
  total += pendingDigit || 0;
  return total > 0 ? total : null;
}

function normalizeVolumeLabel(value) {
  const normalized = String(value || "").normalize("NFKC");
  const numeric = normalized.match(/^\s*(?:第\s*)?([0-9]{1,4})\s*(?:巻)?\s*$/);
  if (numeric) {
    const number = Number(numeric[1]);
    return number > 0 ? `第${number}巻` : null;
  }
  const wrapped = normalized.match(/^\s*(?:第\s*)?([^\s]+?)\s*(?:巻)?\s*$/);
  if (!wrapped) return null;
  const number = romanVolumeNumber(wrapped[1]) ?? kanjiVolumeNumber(wrapped[1]);
  return number === null ? null : `第${number}巻`;
}

function normalizeCatalogVolumeInput(input) {
  const normalized = normalizeVolumeLabel(input.value);
  if (normalized !== null) input.value = normalized;
}

if (document.documentElement.dataset.volumeLabelNormalizerBound !== "true") {
  document.documentElement.dataset.volumeLabelNormalizerBound = "true";
  document.addEventListener("blur", (event) => {
    const input = event.target;
    if (input?.matches?.('.catalog-edit-form input[name="volume_label"]')) {
      normalizeCatalogVolumeInput(input);
    }
  }, true);
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form?.matches?.(".catalog-edit-form")) return;
    const input = form.elements.namedItem("volume_label");
    if (input) normalizeCatalogVolumeInput(input);
  });
}

function stateClass(status) {
  if (GREEN_STATES.has(status)) return "metadata-state-green";
  if (YELLOW_STATES.has(status)) return "metadata-state-yellow";
  if (ORANGE_STATES.has(status)) return "metadata-state-orange";
  if (GRAY_STATES.has(status)) return "metadata-state-gray";
  return "metadata-state-red";
}

function textElement(tagName, text, className = "") {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function reasonText(result) {
  if (result.reason && REASON_LABELS[result.reason]) {
    return REASON_LABELS[result.reason];
  }
  if (result.status === "ALREADY_MATCHED") return "既に基本情報が入力されています";
  if (result.status === "EXISTING_VALUE_PRESERVED") return "既存値を保護しています";
  return result.reason || "-";
}

function unavailableReason(payload) {
  if ((payload.protection_reasons || []).length) {
    return payload.protection_reasons.map((reason) => REASON_LABELS[reason] || reason).join(" / ");
  }
  const results = payload.field_results || [];
  const protectedResult = results.find((result) => result.status === "HUMAN_REVIEW_PROTECTED");
  if (protectedResult) return "人間入力によって保護されています";
  const conflict = results.find((result) => result.status === "CONFLICT");
  if (conflict) return reasonText(conflict);
  if (results.every((result) => ["ALREADY_MATCHED", "EXISTING_VALUE_PRESERVED"].includes(result.status))) {
    return "既に基本情報が入力されています";
  }
  return "検証済みの基本情報候補がありません";
}

function previewPrefillValues(payload) {
  const values = {};
  for (const result of payload.field_results || []) {
    if (!["volume_label", "author_name", "publisher_name"].includes(result.field_name)) continue;
    if (["ALREADY_MATCHED", "EXISTING_VALUE_PRESERVED"].includes(result.status) && result.before) {
      values[result.field_name] = result.before;
    } else if (["CANDIDATE_AVAILABLE", "READY"].includes(result.status) && result.candidate) {
      values[result.field_name] = result.candidate;
    }
  }
  return values;
}

function formHasUnsavedChanges(form) {
  return Array.from(form.elements).some((element) => (
    element.name && element.value !== element.defaultValue
  ));
}

function prefillCatalogEditForm(container, payload) {
  const form = container.closest("tr")?.querySelector(".catalog-edit-form");
  if (!form) return;
  const targetId = form.elements.namedItem("ebook_item_id");
  if (!targetId || targetId.value !== payload.ebook_item_id) return;
  if (formHasUnsavedChanges(form) && !window.confirm("現在の未保存内容をプレビュー値で置き換えますか？")) return;

  const values = previewPrefillValues(payload);
  const inputNames = {
    volume_label: "volume_label",
    author_name: "authors",
    publisher_name: "publisher",
  };
  for (const [fieldName, value] of Object.entries(values)) {
    form.elements.namedItem(inputNames[fieldName]).value = value;
  }
  const details = form.closest("details");
  if (details) details.open = true;
  const notice = form.querySelector(".catalog-edit-prefill-notice");
  notice.textContent = "メタデータ補完プレビューから入力しました。まだDBには保存されていません。";
  notice.hidden = false;
  form.elements.namedItem("volume_label").focus();
}

function renderResult(container, panel, payload, onApply) {
  panel.replaceChildren();
  panel.className = `metadata-autofill-panel ${stateClass(payload.metadata_status)}`;
  panel.append(textElement("h3", `作品: ${payload.title || payload.ebook_item_id}`));
  panel.append(textElement("p", `全体状態: ${payload.metadata_status}`));
  for (const reason of payload.protection_reasons || []) {
    panel.append(textElement("p", REASON_LABELS[reason] || reason));
  }

  for (const result of payload.field_results || []) {
    const field = document.createElement("div");
    field.className = `metadata-field ${stateClass(result.status)}`;
    field.append(textElement("strong", `${FIELD_LABELS[result.field_name] || result.field_name}: ${result.status}`));
    field.append(textElement("p", `現在値: ${result.before || "空欄"}`));
    field.append(textElement("p", `候補値: ${result.candidate || "候補なし"}`));
    field.append(textElement("p", `情報源: ${(result.source_types || []).join(" / ") || result.source_type || "-"}`));
    field.append(textElement("p", `信頼度: ${result.confidence || "-"}`));
    field.append(textElement("p", `理由: ${reasonText(result)}`));
    if ((result.conflict_values || []).length) {
      field.append(textElement("p", `競合候補: ${result.conflict_values.join(" / ")}`));
    }
    panel.append(field);
  }

  panel.append(textElement("p", `証跡: ${payload.evidence_path || "-"}`));
  panel.append(textElement("p", `DB更新試行: ${String(payload.database_update_attempted)}`));
  panel.append(textElement("p", `DB更新成功: ${String(payload.database_update_succeeded)}`));

  const actions = document.createElement("div");
  actions.className = "metadata-autofill-actions";
  const cancel = textElement("button", "キャンセル");
  cancel.type = "button";
  cancel.addEventListener("click", () => { panel.hidden = true; });
  actions.append(cancel);

  if (payload.operation === "PREVIEW") {
    const edit = textElement("button", "基本情報を編集へ反映", "workflow-action-button");
    edit.type = "button";
    edit.addEventListener("click", () => prefillCatalogEditForm(container, payload));
    actions.append(edit);
  }

  if (payload.operation === "PREVIEW") {
    const apply = textElement("button", "SQLへ反映", "workflow-action-button metadata-apply-button");
    apply.type = "button";
    apply.disabled = !payload.apply_possible;
    apply.addEventListener("click", onApply);
    actions.append(apply);
    if (!payload.apply_possible) {
      actions.append(textElement("span", unavailableReason(payload)));
    }
  }
  panel.append(actions);
  panel.hidden = false;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error?.message || "基本情報更新に失敗しました");
  }
  return payload;
}

for (const container of document.querySelectorAll(".metadata-autofill")) {
  const button = container.querySelector(".metadata-autofill-button");
  const panel = container.querySelector(".metadata-autofill-panel");
  const ebookItemId = container.dataset.ebookItemId;
  const csrfToken = button.dataset.csrfToken;

  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "読み込み中";
    panel.hidden = false;
    panel.replaceChildren(textElement("p", "基本情報候補を確認しています。"));
    try {
      const preview = await postJson(`/api/ebooks/${encodeURIComponent(ebookItemId)}/metadata/preview`, {
        csrf_token: csrfToken,
      });
      renderResult(container, panel, preview, async (event) => {
        const applyButton = event.currentTarget;
        applyButton.disabled = true;
        applyButton.textContent = "処理中";
        try {
          const result = await postJson(`/api/ebooks/${encodeURIComponent(ebookItemId)}/metadata/apply`, {
            csrf_token: csrfToken,
            confirmed_fingerprint: preview.fingerprint,
            confirm_ebook_item_id: ebookItemId,
          });
          renderResult(container, panel, result, () => {});
        } catch (error) {
          panel.className = "metadata-autofill-panel metadata-state-red";
          panel.append(textElement("p", error.message, "metadata-autofill-error"));
          applyButton.disabled = false;
          applyButton.textContent = "SQLへ反映";
        }
      });
    } catch (error) {
      panel.className = "metadata-autofill-panel metadata-state-red";
      panel.replaceChildren(textElement("p", error.message, "metadata-autofill-error"));
    } finally {
      button.disabled = false;
      button.textContent = "基本情報更新";
    }
  });
}
