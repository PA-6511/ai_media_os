from app.services.dmm_sale_campaign_discovery_service import (
    parse_dmm_campaign_urls_html,
)


def test_parse_campaign_urls_deduplicates():
    html = """
    {
      "campaignUrls": [
        {
          "url":
          "https://book.dmm.com/list/campaign/ABC123_foo/"
        },
        {
          "url":
          "https://book.dmm.com/list/campaign/ABC123_foo/"
        },
        {
          "url":
          "https://book.dmm.com/list/campaign/XYZ789-bar/"
        }
      ]
    }
    """

    assert (
        parse_dmm_campaign_urls_html(
            html
        )
        == (
            "https://book.dmm.com/list/campaign/ABC123_foo/",
            "https://book.dmm.com/list/campaign/XYZ789-bar/",
        )
    )


def test_parse_campaign_urls_handles_escaped_slashes():
    html = (
        r'{"url":"https:\/\/book.dmm.com\/'
        r'list\/campaign\/jPq20e2HhpaGgLiN1ZPLBlFV06eY3N2Nisqvg43Q\/"}'
    )

    result = (
        parse_dmm_campaign_urls_html(
            html
        )
    )

    assert result == (
        "https://book.dmm.com/"
        "list/campaign/"
        "jPq20e2HhpaGgLiN1ZPLBlFV06eY3N2Nisqvg43Q/",
    )
