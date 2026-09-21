# Sale Single-Store Boundary Design

## Principle

`Sale = campaign-centric / single-store`

`New Release = item-centric / multi-store`

Every Sale campaign, article, image set, and X draft candidate belongs to exactly one store. A Sale consumer must never substitute another store's offer, price, affiliate URL, or cover. New Release keeps its existing Kindle + Kobo + DMM aggregation behavior and is outside this change.

## Scope

This change introduces a Sale-only canonical store policy, establishes explicit campaign store identity, rejects mismatched offers before snapshot creation, and revalidates every Sale snapshot consumer. It also adds store and series diagnostics and displays the campaign store once near the top of the WordPress body.

Post 3417 remains a draft. Its body is regenerated only after the fixed post, campaign, experiment, marker, status, and featured-media guards pass. OGP/X assets and X drafts are not regenerated for Post 3417 in this phase.

Post 3417 is a legacy identity compatibility exception. Its existing experiment ID, snapshot hash, Sale marker, experiment snapshot, and three X variant identities are preserved. Store validation for its content-only rendering receives a separately verified canonical store context instead of mutating or re-identifying the legacy snapshot.

The five-series threshold is diagnostic only. It does not block import, snapshot creation, WordPress draft regeneration, or any other automatic regeneration in this phase.

## Non-goals

- Do not change New Release store names, URL policies, aggregation, rendering, or tests except to run existing regression coverage.
- Do not merge, backfill, or substitute offers across stores.
- Do not infer campaign store from campaign title, campaign ID text, item majority, URL majority, or the only available offer.
- Do not publish WordPress posts or post to X.
- Do not regenerate or upload OGP/X assets for Post 3417.
- Do not enforce the five-distinct-series threshold yet.
- Do not change the database schema. Campaign store identity travels through projection data, persisted Sale offer JSON, and experiment snapshots.
- Do not mutate Post 3417's legacy experiment snapshot or preserve an old hash over changed snapshot content.

## Canonical Sale Store Model

Only these canonical values may exist after the Sale input boundary:

| Canonical value | Accepted input aliases | Public display name |
| --- | --- | --- |
| `rakuten_kobo` | `rakuten_kobo`, `rakuten`, `kobo` | 楽天Kobo |
| `dmm` | `dmm`, `dmm_books` | DMMブックス |
| `amazon` | `amazon`, `amazon_kindle`, `kindle` | Amazon Kindle |

Aliases are accepted only by the Sale store-policy input functions. Projection groups, persisted Sale offer JSON, snapshots, renderers, image generation, and X-copy generation receive canonical values only. New Release retains its current values and does not import or call this normalization policy.

Normalization trims surrounding whitespace and compares case-insensitively. Empty, unknown, Boolean, or non-string values do not resolve to a store.

Snapshot consumers do not call alias normalization. They require the exact canonical literals `rakuten_kobo`, `dmm`, or `amazon`. An alias such as `kobo`, `dmm_books`, or `amazon_kindle` after the input boundary is `NON_CANONICAL_SALE_STORE` and fails closed.

## Campaign Store Identity

Campaign store identity must come from explicit campaign-source or campaign-metadata evidence.

The Kobo official campaign collector writes `campaign_store: rakuten_kobo` into the evidence it creates. This is explicit source provenance because that producer is dedicated to the official Kobo campaign source; it is not an inference from campaign content.

The live campaign metadata reader normalizes an explicit `campaign_store` and carries it into each projection group. Future DMM and Amazon campaign producers must likewise emit an explicit store value or alias at their source boundary.

If explicit identity is absent or invalid, the campaign receives `SALE_STORE_REVIEW_REQUIRED`. It remains visible in diagnostics but is excluded from automatic Sale article, image, affiliate-link, and X-draft candidate generation. Other valid campaigns may continue safely.

The campaign store is copied into each persisted Sale offer JSON record during projection import. A current snapshot reconstructs the campaign identity only from that copied, canonical campaign value and requires it to be present and identical on every eligible offer. It never derives identity from `offer.store_name`.

New Sale experiments include canonical `campaign_store` in the snapshot before computing the snapshot digest, `snapshot_hash`, and experiment identity. Store identity is therefore part of every new experiment's immutable identity contract.

### Post 3417 legacy identity compatibility

Post 3417 predates the `campaign_store` snapshot field and remains bound to:

```ini
POST_ID=3417
CAMPAIGN_ID=rakuten-kobo-official-discount-341921-20261001
EXPERIMENT_ID=a028f0d31b6f7e1c895c4c140eba8008a98e9d2814d5e4a45902a5863771fcdf
FEATURED_MEDIA_ID=3418
```

Adding `campaign_store` directly to that stored snapshot would produce a different digest and break the identity relationship among the experiment, Sale marker, and existing X variants. The legacy record is therefore not migrated in place and is not recreated under a new identity.

Its content-only render uses this explicit compatibility flow:

```text
unchanged legacy experiment snapshot
+ externally verified canonical campaign_store=rakuten_kobo
→ strict Sale Store validation context
→ content-only render
```

The externally supplied store must be verified against the fixed campaign provenance and guarded Post 3417 identity before rendering. It is renderer/validation context only; it is not written into the legacy experiment snapshot or used to recompute its digest.

```ini
LEGACY_STORE_BOUNDARY_EXCEPTION_POST_ID=3417
LEGACY_EXPERIMENT_ID_PRESERVED=YES
LEGACY_SNAPSHOT_MUTATION=NO
LEGACY_MARKER_PRESERVED=YES
LEGACY_X_VARIANTS_PRESERVED=YES
NEW_EXPERIMENT_STORE_IDENTITY_REQUIRED=YES
```

This exception applies only to Post 3417 and is not the normal contract for new Sale experiments.

## Sale Store Policy Module

A new `app/services/sale_store_policy.py` owns all Sale-only store rules:

- `normalize_sale_store(value) -> str | None`
- `require_canonical_sale_store(value) -> str`
- `sale_store_display_name(canonical_store) -> str`
- `sale_store_gate_reasons(campaign_store, offer) -> list[str]`
- `validate_sale_snapshot_store(snapshot) -> str`
- `validate_sale_product_url(canonical_store, url)`
- `validate_sale_affiliate_url(canonical_store, url, evidence=None)`
- `validate_sale_cover_url(canonical_store, url)`
- store diagnostics shared by projection/import/runtime reporting

The policy does not import or mutate New Release services.

### URL-kind separation

The three URL purposes have separate allowlists and validators:

```text
allowed_product_hosts(store)
allowed_affiliate_hosts(store)
allowed_cover_hosts(store)
```

They are never combined into a single generic host list.

Initial explicit host contracts are:

| Store | Product hosts | Affiliate hosts | Cover hosts |
| --- | --- | --- | --- |
| `rakuten_kobo` | `books.rakuten.co.jp` | `hb.afl.rakuten.co.jp`, `a.r10.to` | `thumbnail.image.rakuten.co.jp` |
| `dmm` | `book.dmm.com` | `al.dmm.com` | `pics.dmm.com` |
| `amazon` | `amazon.co.jp`, `www.amazon.co.jp` | `amazon.co.jp`, `www.amazon.co.jp` | `m.media-amazon.com` |

All URLs must use HTTPS and must not contain embedded credentials or explicit ports. Product and affiliate validation reuses the existing `store_url_policy` behavior where available, while Sale cover validation remains a distinct policy. Unknown hosts fail closed.

### Affiliate redirect and short-link validation

Affiliate validation is not satisfied by the outer host alone. It evaluates, as applicable:

1. the outer affiliate host;
2. an embedded destination URL; and
3. trusted generation evidence for links whose destination cannot be established from the URL.

When an affiliate URL contains a destination parameter, such as Kobo's encoded `pc` value or DMM's encoded `lurl` value, the validator decodes the destination and passes the resulting URL through `validate_sale_product_url` for the same canonical store. Both the outer affiliate policy and embedded product policy must pass.

For example:

```text
campaign_store=rakuten_kobo
outer_host=hb.afl.rakuten.co.jp
embedded_destination_host=books.rakuten.co.jp
→ ALLOW

campaign_store=rakuten_kobo
outer_host=hb.afl.rakuten.co.jp
embedded_destination_host=amazon.co.jp
→ STORE URL POLICY VIOLATION
→ FAIL CLOSED
```

A short-link host such as `a.r10.to` is not automatically trusted merely because it appears in the affiliate host allowlist. A destination-less short link is accepted at the input gate only when structured evidence binds the exact URL to the canonical store through at least one of these sources:

- trusted affiliate-generation evidence;
- an existing `store_url_policy` verification result for that link and store; or
- a trusted producer dedicated to that same canonical store.

The evidence must identify the canonical store and producer or verification provenance; an unstructured truthy flag is insufficient. Without a verifiable destination or trusted provenance, the input gate records `SALE_STORE_REVIEW_REQUIRED`. If such a link reaches a snapshot consumer, the consumer fails closed.

## Gate and Consumer Responsibilities

### Import and projection boundary

Projection/import performs filtering and accounting:

1. Normalize explicit `campaign_store`.
2. Normalize each `offer.store_name` through the Sale-only alias map.
3. If campaign identity is missing, add `SALE_STORE_REVIEW_REQUIRED` and exclude every offer from automatic candidates.
4. If the normalized offer store differs from the campaign store, add `SALE_STORE_MISMATCH` to that offer.
5. Count the mismatch in diagnostics and continue processing matched offers.
6. Apply the existing Sale eligibility and scope gates independently.
7. Persist only canonical campaign store values into downstream Sale data.

`SALE_STORE_MISMATCH` is separate from `SALE_SCOPE_REVIEW_REQUIRED` and existing price, period, URL, and evidence failures. A mismatch does not abort processing of matched offers in the same campaign.

### Snapshot consumers

WordPress rendering, OGP/X image creation, and X draft creation validate the complete snapshot before producing output.

A consumer stops with a store-policy error when:

- `campaign_store` is missing or non-canonical;
- any item store is non-canonical or does not exactly equal `campaign_store`;
- any canonical item store differs from another item store;
- any product URL violates the campaign store's product policy;
- any affiliate URL violates the campaign store's affiliate policy; or
- any cover URL violates the campaign store's cover policy.

Consumers do not silently discard only the violating material and continue. Filtering belongs to the import/projection gate; a contaminated snapshot indicates an upstream contract failure and must fail closed.

Consumer validation performs exact canonical comparison and never reinterprets aliases. For example, `campaign_store=rakuten_kobo` with `item.store_name=rakuten_kobo` passes, while `item.store_name=kobo` fails as non-canonical and `item.store_name=amazon` fails as a store mismatch.

## WordPress Contract

The Sale WordPress renderer accepts canonical `campaign_store`, validates the full item list, and emits one store label near the top:

```html
<p class="sale-store">販売ストア：楽天Kobo</p>
```

It does not repeat the label on each series or volume card. Every rendered item, price, cover, and affiliate URL comes from an offer whose canonical store equals the campaign store.

Post 3417 is updated through the existing content-only path after verifying:

- post ID is `3417`;
- status is `draft`;
- campaign ID is `rakuten-kobo-official-discount-341921-20261001`;
- experiment ID and Sale marker match;
- featured media is `3418`; and
- Sale mode is `STOP`.

The guarded path supplies externally verified `campaign_store=rakuten_kobo` to the renderer without modifying the stored legacy snapshot, experiment ID, snapshot hash, marker, or X variants. The update payload contains `content` only. A readback must reconfirm the post ID, draft status, featured media, marker, store label, and absence of other-store items.

## OGP and X Image Contract

Image creation requires canonical `campaign_store` and validates all rows before selecting representative covers. Both OGP and X images use the same already-validated rows. A contaminated row stops both outputs; it is not skipped.

The image heading includes the public store name, for example:

```text
楽天Kobo
最大50%OFF
```

For Post 3417, this phase runs boundary tests only. It does not regenerate, upload, or replace the current OGP/X assets.

## X Draft Contract

X-copy generation validates the experiment snapshot before composing text and includes the public store name, for example:

```text
📚 楽天KoboでKADOKAWAセール
```

The process creates draft candidates only; it never posts to X. Existing Post 3417 X variants are not regenerated or modified in this phase.

## Diagnostics

Each campaign inspection reports:

```ini
CAMPAIGN_STORE=<canonical value or SALE_STORE_REVIEW_REQUIRED>
TOTAL_STORE_MATCHED_ITEMS=<count>
STORE_MISMATCH_COUNT=<count>
SCOPE_ALLOWED_ITEM_COUNT=<count>
DISTINCT_SERIES_COUNT=<count>
MIN_DISTINCT_SERIES_FOR_ROUNDUP=5
SERIES_THRESHOLD_STATUS=MET|BELOW_THRESHOLD
SALE_ROUNDUP_INSUFFICIENT_SERIES=DIAGNOSTIC_ONLY
AUTO_REGEN_BLOCKED=YES|NO
```

Definitions:

- `TOTAL_STORE_MATCHED_ITEMS`: offers whose normalized store equals the explicit canonical campaign store, before other eligibility failures.
- `STORE_MISMATCH_COUNT`: offers whose normalized store is absent, unknown, or different from the explicit campaign store.
- `SCOPE_ALLOWED_ITEM_COUNT`: store-matched offers that pass the independent Sale scope gate.
- `DISTINCT_SERIES_COUNT`: distinct normalized series among offers that pass store, scope, and existing Sale eligibility gates and are eligible for the snapshot.
- `AUTO_REGEN_BLOCKED`: `YES` when the campaign lacks an explicit store identity or has no eligible matched offer after mandatory gates; otherwise `NO`. A below-threshold series count alone never changes it to `YES` in this phase.

The series threshold is informational. `BELOW_THRESHOLD` does not add a block reason and does not prevent automatic regeneration in this phase.

## Expected Current Campaign Result

For the current five-item KADOKAWA canary:

```ini
CAMPAIGN_STORE=rakuten_kobo
TOTAL_STORE_MATCHED_ITEMS=5
STORE_MISMATCH_COUNT=0
SCOPE_ALLOWED_ITEM_COUNT=5
DISTINCT_SERIES_COUNT=1
MIN_DISTINCT_SERIES_FOR_ROUNDUP=5
SERIES_THRESHOLD_STATUS=BELOW_THRESHOLD
SALE_ROUNDUP_INSUFFICIENT_SERIES=DIAGNOSTIC_ONLY
AUTO_REGEN_BLOCKED=NO
```

After the guarded Post 3417 body update:

```ini
POST_ID=3417
STATUS=draft
FEATURED_MEDIA_ID=3418
BLOG_STORE_COUNT=1
BLOG_STORE=楽天Kobo
OTHER_STORE_ITEM_COUNT_IN_ARTICLE=0
OTHER_STORE_COVER_COUNT=0
OTHER_STORE_AFFILIATE_URL_COUNT=0
WORDPRESS_PUBLISH=NO
X_POST=NO
```

## Testing Strategy

Tests are written before implementation and cover:

1. Kobo campaign + Kobo alias offer allows and canonicalizes to `rakuten_kobo`.
2. Kobo campaign + Kindle offer receives `SALE_STORE_MISMATCH`.
3. Kobo campaign + DMM offer receives `SALE_STORE_MISMATCH`.
4. DMM campaign + DMM alias offer allows and canonicalizes to `dmm`.
5. Amazon campaign + Kindle alias offer allows and canonicalizes to `amazon`.
6. Missing or unknown campaign store receives `SALE_STORE_REVIEW_REQUIRED` without inference.
7. Projection/import excludes mismatches, counts them, and continues with matched offers.
8. A Sale snapshot cannot contain multiple stores.
9. WordPress content displays one store and contains no other-store item, cover, or affiliate URL.
10. OGP and X image generation both reject a contaminated snapshot before creating files.
11. X-copy generation rejects a contaminated snapshot and includes the store name for valid input.
12. Product, affiliate, and cover hosts are validated independently.
13. Below-five series produces diagnostics but does not block regeneration.
14. Existing New Release multi-store tests remain green without modifying New Release production code.
15. WordPress remains draft and no X post occurs.
16. Post 3417 retains featured media `3418` after its content-only update.
17. Legacy Post 3417 keeps its existing experiment ID, snapshot hash, Sale marker, and X variant identities.
18. Adding Sale store validation to Post 3417 does not mutate the legacy experiment snapshot.
19. New Sale experiments include canonical `campaign_store` inside snapshot identity and digest input.
20. A snapshot consumer rejects an alias such as `kobo` with `NON_CANONICAL_SALE_STORE` instead of normalizing it again.
21. A Rakuten affiliate redirect with outer host `hb.afl.rakuten.co.jp` and embedded destination host `books.rakuten.co.jp` passes.
22. A Rakuten affiliate redirect with outer host `hb.afl.rakuten.co.jp` and embedded destination host `amazon.co.jp` fails closed.
23. A short affiliate URL without a verifiable destination or trusted generation evidence is not silently accepted.
24. Existing New Release behavior remains unchanged, including its multi-store aggregation and store naming.

Only focused Sale tests, directly affected projection tests, and existing targeted New Release multi-store regression tests are run. The full test suite is not required for this change.

## Rollout and Failure Behavior

The policy is introduced fail-closed at snapshot consumers. Existing Sale fixtures and official Kobo evidence are upgraded to carry explicit `campaign_store`. Campaigns from sources that do not yet provide explicit identity remain review-required rather than being guessed.

Rollout separates the one legacy compatibility case from the new invariant:

```text
Existing legacy experiment: Post 3417
→ preserve existing experiment ID and snapshot hash
→ preserve Sale marker and X variant identities
→ do not rewrite or mutate the snapshot
→ supply verified campaign_store at the guarded render boundary

New Sale experiments
→ require canonical campaign_store
→ include campaign_store in the immutable snapshot
→ include campaign_store in snapshot digest and experiment identity
→ require consumers to compare canonical literals exactly
```

No general legacy fallback exists. A snapshot without canonical store identity is invalid for normal consumer use; only the fixed Post 3417 content-only path may use the explicit external validation context described above.

Store mismatches are expected diagnostic events, not pipeline crashes. A campaign may continue with its matched offers. A consumer validation failure is different: it indicates a contaminated snapshot and stops generation before any WordPress write, image output, affiliate-link use, or X draft mutation.

The next phase may expand the KADOKAWA campaign through read-only collection and reevaluate `DISTINCT_SERIES_COUNT`. Enforcement of `MIN_DISTINCT_SERIES_FOR_ROUNDUP=5` requires a separate approved change after campaign-wide acquisition is complete.
