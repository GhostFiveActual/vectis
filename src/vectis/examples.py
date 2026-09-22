# GHOST FIVE // VECTIS
# Provides canonical in-package VECTIS examples for the CLI, Studio, and demo tooling.

from __future__ import annotations


CANONICAL_EXAMPLES: dict[str, str] = {
    "release-gate": """mission "Release gate" {
    source ready true;
    source quality_score 0.96;
    let label upper("vectis");
    let approved ready && quality_score >= 0.90;

    assert quality_score >= 0.80;

    when approved {
        publish concat(label, " READY");
    } otherwise {
        request "manual-review";
    }
}
""",
    "functions": """mission "Built in functions" {
    source raw_name "  Ghost Five  ";
    let clean_name trim(raw_name);
    let banner concat(upper(clean_name), " // VECTIS");
    let score clamp(108, 0, 100);

    when score >= 90 {
        publish replace(banner, "GHOST FIVE", "VECTIS");
    }
}
""",
    "pure-functions": """function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}

function release_summary(score, risk) {
    return object(
        "approved", release_ready(score, risk),
        "score", score,
        "risk", risk
    );
}

mission "Pure function release gate" {
    source quality 96;
    source risk 15;
    let summary release_summary(quality, risk);

    assert get(summary, "approved"), "Release gate failed";
    publish summary;
}
""",
    "structured-syntax": """function summarize(build) {
    return {
        ready: build.passed && build.coverage >= 90 && all(build.checks),
        coverage: build.coverage,
        first_check: build.checks[0]
    };
}

mission "Structured syntax" {
    source build {
        passed: true,
        coverage: 96,
        checks: [true, true, true]
    };

    let summary summarize(build);
    assert summary.ready, "Structured readiness gate failed";
    publish summary;
}
""",
    "readiness": """mission "Operational readiness" {
    source ready true;
    source quality 94;
    source risk 22;
    let approved ready && quality >= 80 && risk <= 35;
    let status if_else(approved, "AUTHORIZED", "REVIEW");

    assert quality >= 0 && quality <= 100;
    assert risk >= 0 && risk <= 100;

    when approved {
        publish concat("STATUS: ", status);
    } otherwise {
        publish "STATUS: REVIEW";
    }
}
""",
}


def example_manifest() -> tuple[dict[str, str], ...]:
    """Return stable example identifiers and human readable titles."""
    return tuple(
        {
            "id": name,
            "title": name.replace("-", " ").title(),
        }
        for name in sorted(CANONICAL_EXAMPLES)
    )
