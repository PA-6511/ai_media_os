<?php

declare(strict_types=1);

require "/var/www/wordpress/wp-load.php";

$planPath = (string)getenv("XNR_PLAN_FILE");
$targetDate = (string)getenv("TARGET_DATE");
$plan = json_decode((string)file_get_contents($planPath), true);
if (!is_array($plan)) {
    echo "WORDPRESS_APPLY=BLOCKED CODE=PLAN_READ_FAILED\n";
    exit(40);
}

$title = trim((string)($plan["title"] ?? ""));
$content = (string)($plan["wordpress_html"] ?? "");
$expectedCount = intval($plan["wordpress_item_count"] ?? 0);
$sourceDigest = trim((string)($plan["source_digest"] ?? ""));
$cardCount = substr_count($content, 'class="ai-nr-roundup__item"');
if (
    $targetDate === ""
    || $title === ""
    || $expectedCount < 1
    || $expectedCount > 200
    || $cardCount !== $expectedCount
    || $sourceDigest === ""
) {
    echo "WORDPRESS_APPLY=BLOCKED CODE=INVALID_PLAN\n";
    exit(40);
}

$lockName = "ai_media_os_xnr_" . $targetDate;
$lockAcquired = intval($wpdb->get_var($wpdb->prepare("SELECT GET_LOCK(%s, 0)", $lockName)));
if ($lockAcquired !== 1) {
    echo "WORDPRESS_APPLY=BLOCKED CODE=LOCK_UNAVAILABLE\n";
    exit(40);
}

try {
    $existing = get_posts([
        "post_type" => "post",
        "post_status" => ["draft", "pending", "future", "publish", "private"],
        "posts_per_page" => 2,
        "meta_key" => "_ai_media_os_daily_new_release_roundup_date",
        "meta_value" => $targetDate,
        "orderby" => "ID",
        "order" => "DESC",
    ]);
    if (count($existing) > 1) {
        echo "WORDPRESS_APPLY=BLOCKED CODE=DUPLICATE_POSTS\n";
        exit(40);
    }

    // XNR_PUBLISHED_IDEMPOTENCE_V1
    $reusePublished = false;
    $reuseFuture = false;
    $action = "CREATED";

    if ($existing) {
        $expectedPostId = intval($existing[0]->ID);
        $expectedStatus = (string)$existing[0]->post_status;

        if ($expectedStatus === "publish") {
            $existingItemCount = intval(
                get_post_meta(
                    $expectedPostId,
                    "_ai_media_os_roundup_item_count",
                    true
                )
            );
            $existingSourceDigest = (string)get_post_meta(
                $expectedPostId,
                "_ai_media_os_roundup_source_digest",
                true
            );

            if (
                $existingItemCount !== $expectedCount
            ) {
                echo "WORDPRESS_APPLY=BLOCKED CODE=PUBLISHED_ITEM_COUNT_MISMATCH\n";
                echo "POST_ID=" . $expectedPostId . "\n";
                echo "POST_STATUS=" . $expectedStatus . "\n";
                exit(40);
            }

            /*
             * XNR_PUBLISHED_SEMANTIC_DRIFT_V1
             *
             * Published WordPress content is immutable.
             *
             * Store/affiliate URLs may legitimately become
             * better canonical URLs after publication.
             *
             * Never rewrite the published post here.
             * When source_digest changed, allow permalink
             * finalization only if the user-visible semantic
             * identity is still exactly equivalent:
             *
             *   - same item count
             *   - same titles
             *   - same authors
             *   - same displayed prices
             *
             * Any semantic change still fails closed.
             */
            $publishedSourceDrift = false;

            if (
                $existingSourceDigest !== $sourceDigest
            ) {
                $currentPublished = get_post(
                    $expectedPostId
                );

                if (
                    !$currentPublished
                    || intval(
                        $currentPublished->ID
                    ) !== $expectedPostId
                    || (string)$currentPublished->post_status
                        !== "publish"
                ) {
                    echo "WORDPRESS_APPLY=BLOCKED CODE=POST_CAS_DRIFT\n";
                    exit(40);
                }

                $normalizeText = static function (
                    string $value
                ): string {
                    $value = html_entity_decode(
                        wp_strip_all_tags($value),
                        ENT_QUOTES | ENT_HTML5,
                        "UTF-8"
                    );

                    $value = preg_replace(
                        "/\\s+/u",
                        " ",
                        $value
                    );

                    return trim(
                        (string)$value
                    );
                };

                $extractValues = static function (
                    string $html,
                    string $className
                ) use (
                    $normalizeText
                ): array {
                    $quotedClass = preg_quote(
                        $className,
                        "~"
                    );

                    $pattern = (
                        '~<(?P<tag>h2|p|div)'
                        . '[^>]*class="[^"]*'
                        . $quotedClass
                        . '[^"]*"[^>]*>'
                        . '(?P<value>.*?)'
                        . '</(?P=tag)>~si'
                    );

                    $matches = [];

                    if (
                        preg_match_all(
                            $pattern,
                            $html,
                            $matches
                        ) === false
                    ) {
                        return [];
                    }

                    return array_map(
                        $normalizeText,
                        $matches["value"] ?? []
                    );
                };

                $publishedHtml = (
                    (string)$currentPublished->post_content
                );

                $publishedTitles = $extractValues(
                    $publishedHtml,
                    "ai-nr-roundup__title"
                );

                $plannedTitles = $extractValues(
                    $content,
                    "ai-nr-roundup__title"
                );

                $publishedAuthors = $extractValues(
                    $publishedHtml,
                    "ai-nr-roundup__author"
                );

                $plannedAuthors = $extractValues(
                    $content,
                    "ai-nr-roundup__author"
                );

                $publishedPrices = $extractValues(
                    $publishedHtml,
                    "ai-nr-roundup__price"
                );

                $plannedPrices = $extractValues(
                    $content,
                    "ai-nr-roundup__price"
                );

                if (
                    count($publishedTitles)
                        !== $expectedCount
                    || count($plannedTitles)
                        !== $expectedCount
                    || $publishedTitles
                        !== $plannedTitles
                    || $publishedAuthors
                        !== $plannedAuthors
                    || $publishedPrices
                        !== $plannedPrices
                ) {
                    echo "WORDPRESS_APPLY=BLOCKED CODE=PUBLISHED_CONTENT_MISMATCH\n";
                    echo "POST_ID=" . $expectedPostId . "\n";
                    echo "POST_STATUS=" . $expectedStatus . "\n";
                    echo "SEMANTIC_EQUIVALENCE=FAIL\n";
                    exit(40);
                }

                $publishedSourceDrift = true;

                echo "PUBLISHED_SOURCE_DRIFT=ACCEPTED_NO_WRITE\n";
                echo "SEMANTIC_EQUIVALENCE=PASS\n";
                echo "PUBLISHED_SOURCE_DIGEST="
                    . $existingSourceDigest
                    . "\n";
                echo "CURRENT_SOURCE_DIGEST="
                    . $sourceDigest
                    . "\n";
            }

            $postId = $expectedPostId;
            $action = (
                $publishedSourceDrift
                ? "ALREADY_PUBLISHED_SOURCE_DRIFT"
                : "ALREADY_PUBLISHED"
            );
            $reusePublished = true;

            // Published posts are immutable in this path.
            // Skip every WordPress mutation and continue at readback.
            goto xnr_verify_existing_roundup;
        }

        // XNR_SCHEDULED_IDEMPOTENCE_V1
        //
        // A scheduled roundup is already a valid state.
        // Reuse it only if its authorization binding still
        // exactly matches this roundup plan.
        if ($expectedStatus === "future") {
            $existingItemCount = intval(
                get_post_meta(
                    $expectedPostId,
                    "_ai_media_os_roundup_item_count",
                    true
                )
            );

            $existingSourceDigest = (string)get_post_meta(
                $expectedPostId,
                "_ai_media_os_roundup_source_digest",
                true
            );

            if (
                $existingItemCount !== $expectedCount
                || $existingSourceDigest !== $sourceDigest
            ) {
                echo "WORDPRESS_APPLY=BLOCKED CODE=SCHEDULED_CONTENT_MISMATCH\n";
                echo "POST_ID=" . $expectedPostId . "\n";
                echo "POST_STATUS=" . $expectedStatus . "\n";
                exit(40);
            }

            $postId = $expectedPostId;
            $action = "ALREADY_SCHEDULED";
            $reuseFuture = true;

            // Do not downgrade or rewrite a scheduled post.
            goto xnr_verify_existing_roundup;
        }

        if ($expectedStatus !== "draft") {
            echo "WORDPRESS_APPLY=BLOCKED CODE=EXISTING_NON_DRAFT\n";
            echo "POST_ID=" . $expectedPostId . "\n";
            echo "POST_STATUS=" . $expectedStatus . "\n";
            exit(40);
        }

        $current = get_post($expectedPostId);
        if (
            !$current
            || intval($current->ID) !== $expectedPostId
            || (string)$current->post_status !== $expectedStatus
        ) {
            echo "WORDPRESS_APPLY=BLOCKED CODE=POST_CAS_DRIFT\n";
            exit(40);
        }

        $postId = wp_update_post([
            "ID" => $expectedPostId,
            "post_type" => "post",
            "post_status" => "draft",
            "post_title" => $title,
            "post_content" => $content,
        ], true);
        $action = "UPDATED";
    } else {
        $postId = wp_insert_post([
            "post_type" => "post",
            "post_status" => "draft",
            "post_title" => $title,
            "post_name" => "daily-new-releases-" . $targetDate,
            "post_content" => $content,
        ], true);
    }

    if (is_wp_error($postId)) {
        echo "WORDPRESS_APPLY=BLOCKED CODE=WRITE_FAILED\n";
        echo "ERROR=" . $postId->get_error_message() . "\n";
        exit(40);
    }
    $postId = intval($postId);
    update_post_meta($postId, "_ai_media_os_daily_new_release_roundup", "1");
    update_post_meta($postId, "_ai_media_os_daily_new_release_roundup_date", $targetDate);
    update_post_meta($postId, "_ai_media_os_roundup_item_count", (string)$expectedCount);
    update_post_meta($postId, "_ai_media_os_roundup_source_digest", $sourceDigest);
    update_post_meta($postId, "_ai_media_os_roundup_runner", "X_NR_AUTO_1");

xnr_verify_existing_roundup:
    clean_post_cache($postId);
    $verified = get_post($postId);
    $verifiedCards = $verified ? substr_count((string)$verified->post_content, 'class="ai-nr-roundup__item"') : 0;

    $expectedVerifiedStatus = (
        $reusePublished
        ? "publish"
        : ($reuseFuture ? "future" : "draft")
    );

    /*
     * XNR_PUBLISHED_FROZEN_DIGEST_READBACK_V1
     *
     * For a semantic-equivalent drift on an already-published
     * roundup, the published source digest is intentionally
     * frozen. The current plan digest MUST NOT be written back.
     *
     * Normal draft/future/publish paths still verify against
     * the current plan digest.
     */
    $expectedVerifiedSourceDigest = (
        $reusePublished
        && ($publishedSourceDrift ?? false)
    )
        ? $existingSourceDigest
        : $sourceDigest;

    if (
        !$verified
        || (string)$verified->post_status !== $expectedVerifiedStatus
        || $verifiedCards !== $expectedCount
        || intval(get_post_meta($postId, "_ai_media_os_roundup_item_count", true)) !== $expectedCount
        || (string)get_post_meta($postId, "_ai_media_os_roundup_source_digest", true) !== $expectedVerifiedSourceDigest
    ) {
        echo "WORDPRESS_APPLY=BLOCKED CODE=POST_WRITE_VERIFY_FAILED\n";
        exit(40);
    }

    $verifiedPermalink = get_permalink($postId);

    if (
        !is_string($verifiedPermalink)
        || strpos($verifiedPermalink, "https://") !== 0
        || strpos($verifiedPermalink, "/wp-admin/") !== false
        || strpos($verifiedPermalink, "{ARTICLE_URL}") !== false
    ) {
        echo "WORDPRESS_APPLY=BLOCKED CODE=INVALID_PERMALINK_READBACK\n";
        exit(40);
    }

    echo "POST_STATUS=" . (string)$verified->post_status . "\n";
    echo "PERMALINK=" . $verifiedPermalink . "\n";

    echo "WORDPRESS_APPLY=PASS\n";
    echo "WORDPRESS_ACTION=" . $action . "\n";
    echo "POST_ID=" . $postId . "\n";
    echo "POST_STATUS=" . (string)$verified->post_status . "\n";
    echo "CARD_COUNT=" . $verifiedCards . "\n";
    echo "ITEM_COUNT=" . $expectedCount . "\n";
    echo "EDIT_URL=" . admin_url("post.php?post=" . $postId . "&action=edit") . "\n";
} finally {
    $wpdb->get_var($wpdb->prepare("SELECT RELEASE_LOCK(%s)", $lockName));
}
