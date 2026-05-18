"""check_wp_draft_prepublish.py

DRY_RUN 専用。WordPress の下書き（draft）記事に対して公開前品質チェックを
実行し、チェック結果を標準出力に表示するだけで、draft の編集・公開・状態変更は
一切行わない。

使い方:
    python3 tools/check_wp_draft_prepublish.py list
    python3 tools/check_wp_draft_prepublish.py check --post-id 12345
    python3 tools/check_wp_draft_prepublish.py report --output report.json

参考資料:
    - docs/PREPUBLISH_CHECK_47C1_DESIGN.md
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# Project imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
import requests
import os

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

MIN_CONTENT_LENGTH = 100  # 本文品質チェック: 最小文字数


# ---------------------------------------------------------------------------
# WordPress API クライアント
# ---------------------------------------------------------------------------

class WordPressClient:
    """Simple WordPress REST API client for draft checking"""
    
    def __init__(self, base_url: str, username: str, app_password: str, timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.timeout = timeout
    
    def get_posts(self, status: str = 'draft', per_page: int = 20) -> list:
        """Get posts by status"""
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        params = {'status': status, 'per_page': per_page}
        resp = requests.get(
            url,
            auth=(self.username, self.app_password),
            params=params,
            timeout=self.timeout,
            headers={'Content-Type': 'application/json'}
        )
        resp.raise_for_status()
        return resp.json() if isinstance(resp.json(), list) else []
    
    def get_post(self, post_id: int) -> dict:
        """Get single post"""
        url = f"{self.base_url}/wp-json/wp/v2/posts/{post_id}"
        resp = requests.get(
            url,
            auth=(self.username, self.app_password),
            timeout=self.timeout,
            headers={'Content-Type': 'application/json'}
        )
        resp.raise_for_status()
        return resp.json() if isinstance(resp.json(), dict) else {}


# ---------------------------------------------------------------------------
# チェック関数群
# ---------------------------------------------------------------------------

def check_content_quality(content: str) -> Tuple[str, list]:
    """
    本文品質チェック
    
    Returns:
        (result, details) where result in ['PASS', 'WARN', 'FAIL']
    """
    issues = []
    
    # Empty content
    if not content or content.strip() == '':
        return 'FAIL', ['本文が空です']
    
    # Too short
    if len(content) < MIN_CONTENT_LENGTH:
        issues.append(f'本文が短い（{len(content)}文字、推奨100以上）')
    
    # Check headings
    if '<h2>' not in content and '<h3>' not in content:
        issues.append('見出し（h2/h3）が見つかりません')
    
    result = 'WARN' if issues else 'PASS'
    return result, issues


def check_urls(content: str) -> Tuple[str, list]:
    """
    URL チェック（楽天/DMM/外部リンク）
    
    Returns:
        (result, details)
    """
    details = []
    
    has_rakuten = 'rakuten.co.jp' in content
    has_dmm = 'dmm.co.jp' in content
    
    # Extract all hrefs
    urls = re.findall(r'href=["\']([^"\']+)["\']', content)
    external_urls = [u for u in urls if u.startswith('http')]
    
    if has_rakuten:
        details.append('楽天リンク確認')
    if has_dmm:
        details.append('DMM リンク確認')
    if external_urls and not (has_rakuten or has_dmm):
        details.append(f'外部リンク確認（{len(external_urls)}件）')
    
    # At least one URL source
    if has_rakuten or has_dmm or external_urls:
        result = 'PASS'
    else:
        result = 'WARN'
        details.append('URL が見つかりません')
    
    return result, details


def check_cta(content: str) -> Tuple[str, list]:
    """
    CTA（Call-to-Action）チェック（ボタン/リンク文言）
    
    Returns:
        (result, details)
    """
    details = []
    
    has_button = '<button>' in content
    has_link = '<a' in content and '</a>' in content
    
    if has_button:
        details.append('ボタン CTA 確認')
    if has_link:
        details.append('リンク CTA 確認')
    
    if has_button or has_link:
        result = 'PASS'
    else:
        result = 'WARN'
        details.append('CTA（ボタン/リンク）が見つかりません')
    
    return result, details


def check_pr_notice(content: str, excerpt: str = '') -> Tuple[str, list]:
    """
    PR表記チェック（広告/PR/アフィリエイト表記）
    
    Returns:
        (result, details)
    """
    details = []
    combined = (content + excerpt).lower()
    
    keywords = ['広告', 'pr', 'アフィリエイト', 'affiliate', '本サイトは']
    found = [k for k in keywords if k in combined]
    
    if found:
        result = 'PASS'
        details.append(f'PR表記確認: {", ".join(found)}')
    else:
        result = 'WARN'
        details.append('PR/広告表記が見つかりません')
    
    return result, details


def check_featured_image(post: dict) -> Tuple[str, list]:
    """
    アイキャッチチェック（featured_media）
    
    Returns:
        (result, details)
    """
    details = []
    featured_media_id = post.get('featured_media', 0)
    
    if featured_media_id > 0:
        result = 'PASS'
        details.append(f'アイキャッチ設定済み（ID: {featured_media_id}）')
    else:
        result = 'WARN'
        details.append('アイキャッチが未設定です')
    
    return result, details


def aggregate_check_results(checks: dict) -> str:
    """
    複数チェック結果を集約し最終判定を決定
    
    Args:
        checks: {check_name: result} dict
    
    Returns:
        'PASS_ALL' | 'PASS_WITH_WARNS' | 'FAIL'
    """
    has_fail = any(v == 'FAIL' for v in checks.values())
    has_warn = any(v == 'WARN' for v in checks.values())
    
    if has_fail:
        return 'FAIL'
    elif has_warn:
        return 'PASS_WITH_WARNS'
    else:
        return 'PASS_ALL'


# ---------------------------------------------------------------------------
# チェック実行エンジン
# ---------------------------------------------------------------------------

def run_prepublish_check(post: dict) -> dict:
    """
    1つの draft に対して全チェックを実行
    
    Args:
        post: WordPress post dict
    
    Returns:
        {
            'post_id': int,
            'post_title': str,
            'check_timestamp': str (ISO format),
            'checks': {
                'content_quality': {'result': str, 'details': list},
                ...
            },
            'final_result': str,
            'recommendation': str
        }
    """
    content = post.get('content', {}).get('raw', '')
    excerpt = post.get('excerpt', {}).get('raw', '')
    
    checks = {
        'content_quality': dict(zip(
            ['result', 'details'],
            check_content_quality(content)
        )),
        'urls': dict(zip(
            ['result', 'details'],
            check_urls(content)
        )),
        'cta': dict(zip(
            ['result', 'details'],
            check_cta(content)
        )),
        'pr_notice': dict(zip(
            ['result', 'details'],
            check_pr_notice(content, excerpt)
        )),
        'featured_image': dict(zip(
            ['result', 'details'],
            check_featured_image(post)
        )),
    }
    
    result_values = {name: check['result'] for name, check in checks.items()}
    final_result = aggregate_check_results(result_values)
    
    # Generate recommendation
    failures = [k for k, v in result_values.items() if v == 'FAIL']
    warns = [k for k, v in result_values.items() if v == 'WARN']
    
    if failures:
        recommendation = f'公開不可: {", ".join(failures)}'
    elif warns:
        recommendation = f'修正推奨: {", ".join(warns)}'
    else:
        recommendation = '公開可能'
    
    return {
        'post_id': post.get('id'),
        'post_title': post.get('title', {}).get('raw', '(untitled)'),
        'check_timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': checks,
        'final_result': final_result,
        'recommendation': recommendation,
    }


# ---------------------------------------------------------------------------
# CLI コマンド
# ---------------------------------------------------------------------------

def cmd_list(wp: WordPressClient, limit: int = 20):
    """
    下書き記事を一覧表示
    """
    try:
        drafts = wp.get_posts(status='draft', per_page=limit)
        print(f"\n=== 下書き記事一覧（最新{limit}件） ===\n")
        for post in drafts:
            post_id = post.get('id')
            title = post.get('title', {}).get('raw', '(untitled)')
            date = post.get('date', 'N/A')
            print(f"  ID: {post_id:6d} | {title:40s} | {date}")
        print(f"\nTotal: {len(drafts)} posts\n")
    except Exception as e:
        print(f"Error listing drafts: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_check(wp: WordPressClient, post_id: int):
    """
    指定 post_id のチェック実行
    """
    try:
        post = wp.get_post(post_id)
        if post.get('status') != 'draft':
            print(f"Warning: Post {post_id} is not draft (status: {post.get('status')})")
        
        result = run_prepublish_check(post)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error checking post {post_id}: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_report(wp: WordPressClient, output_path: Optional[str] = None, limit: int = 20):
    """
    全下書きのチェック結果を JSON レポート出力
    """
    try:
        drafts = wp.get_posts(status='draft', per_page=limit)
        
        results = {
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_drafted': len(drafts),
            'checks': []
        }
        
        for post in drafts:
            result = run_prepublish_check(post)
            results['checks'].append(result)
        
        # Aggregate summary
        summary = {
            'PASS_ALL': len([r for r in results['checks'] if r['final_result'] == 'PASS_ALL']),
            'PASS_WITH_WARNS': len([r for r in results['checks'] if r['final_result'] == 'PASS_WITH_WARNS']),
            'FAIL': len([r for r in results['checks'] if r['final_result'] == 'FAIL']),
        }
        results['summary'] = summary
        
        # Output
        report_json = json.dumps(results, ensure_ascii=False, indent=2)
        
        if output_path:
            Path(output_path).write_text(report_json, encoding='utf-8')
            print(f"Report saved: {output_path}")
        else:
            print(report_json)
        
        # Console summary
        print(f"\n=== チェック結果サマリー ===")
        print(f"  PASS_ALL:         {summary['PASS_ALL']}")
        print(f"  PASS_WITH_WARNS:  {summary['PASS_WITH_WARNS']}")
        print(f"  FAIL:             {summary['FAIL']}")
        print()
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='WordPress 下書き記事の公開前チェック（dry-run）'
    )
    subparsers = parser.add_subparsers(dest='command', help='Subcommand')
    
    # list command
    list_parser = subparsers.add_parser('list', help='下書き記事を一覧表示')
    list_parser.add_argument('--limit', type=int, default=20, help='表示件数（デフォルト: 20）')
    
    # check command
    check_parser = subparsers.add_parser('check', help='指定 post_id をチェック')
    check_parser.add_argument('--post-id', type=int, required=True, help='Post ID')
    
    # report command
    report_parser = subparsers.add_parser('report', help='全下書きのレポート出力')
    report_parser.add_argument('--output', help='出力ファイルパス（省略時は stdout）')
    report_parser.add_argument('--limit', type=int, default=20, help='チェック件数（デフォルト: 20）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize WordPress client
    base_url = os.environ.get('WP_BASE_URL', '').rstrip('/')
    username = os.environ.get('WP_USER', '') or os.environ.get('WP_USERNAME', '')
    app_password = os.environ.get('WP_APP_PASSWORD', '')
    
    missing = []
    if not base_url:
        missing.append('WP_BASE_URL')
    if not username:
        missing.append('WP_USER or WP_USERNAME')
    if not app_password:
        missing.append('WP_APP_PASSWORD')
    
    if missing:
        print(f'Error: Missing environment variables: {", ".join(missing)}', file=sys.stderr)
        sys.exit(1)
    
    wp = WordPressClient(
        base_url=base_url,
        username=username,
        app_password=app_password,
    )
    
    # Route command
    if args.command == 'list':
        cmd_list(wp, limit=args.limit)
    elif args.command == 'check':
        cmd_check(wp, post_id=args.post_id)
    elif args.command == 'report':
        cmd_report(wp, output_path=args.output, limit=args.limit)


if __name__ == '__main__':
    main()
