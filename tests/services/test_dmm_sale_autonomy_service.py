from datetime import (
    datetime,
    timezone,
)

from app.services.dmm_sale_autonomy_service import (
    campaign_id_for,
)


def test_campaign_id_matches_live_dmm_contract():
    result = campaign_id_for(
        campaign_url=(
            "https://book.dmm.com/"
            "list/campaign/"
            "jPq20e2HhpaGgLiN1ZPLBlFV06eY3N2Nisqvg43Q/"
        ),
        sale_end_at=(
            "2026-10-04T23:59:59+09:00"
        ),
    )

    assert result == (
        "dmm-official-"
        "ba9486538471c005-"
        "20261004"
    )


def test_campaign_id_accepts_datetime():
    result = campaign_id_for(
        campaign_url=(
            "https://book.dmm.com/"
            "list/campaign/"
            "example/"
        ),
        sale_end_at=datetime(
            2026,
            10,
            4,
            14,
            59,
            59,
            tzinfo=timezone.utc,
        ),
    )

    assert result.startswith(
        "dmm-official-"
    )

    assert result.endswith(
        "-20261004"
    )
