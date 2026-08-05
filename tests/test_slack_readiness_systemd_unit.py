from __future__ import annotations

from pathlib import Path


def test_readiness_unit_is_dry_run_and_hardened() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    path = (
        repo_root
        / "systemd/"
        / (
            "ai-media-os-slack-approval-"
            "readiness.service"
        )
    )

    text = path.read_text(encoding="utf-8")

    required_entries = (
        "EnvironmentFile=/etc/ai-media-os/slack.env",
        "SLACK_APPROVAL_MODE=DRY_RUN",
        "SLACK_APPROVAL_LIVE_CONFIRM=",
        (
            "DATABASE_URL=sqlite:////var/lib/"
            "ai-media-os-slack-readiness/"
            "ebook_affiliate_readiness.db"
        ),
        "Restart=on-failure",
        "KillSignal=SIGTERM",
        "StateDirectory=ai-media-os-slack-readiness",
        "StateDirectoryMode=0700",
        "UMask=0077",
        "NoNewPrivileges=yes",
        "CapabilityBoundingSet=",
        "ProtectSystem=strict",
        "ProtectHome=read-only",
        "PrivateTmp=yes",
        "PrivateDevices=yes",
        (
            "RestrictAddressFamilies="
            "AF_UNIX AF_INET AF_INET6"
        ),
        "RestrictNamespaces=yes",
        "ProtectKernelModules=yes",
        "ProtectKernelTunables=yes",
    )

    for entry in required_entries:
        assert entry in text

    assert (
        "data/database/ebook_affiliate.db"
        not in text
    )

    assert "SLACK_APPROVAL_MODE=LIVE" not in text
    assert "I_UNDERSTAND_DB_WRITES" not in text
