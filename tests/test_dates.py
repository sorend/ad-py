"""Tests for dates module - title date extraction and year_month derivation."""

import pytest


class TestExtractTitleDate:
    """Tests for extract_title_date()."""

    # ── yyyy.mm.dd pattern ────────────────────────────────────────────────────

    def test_yyyy_mm_dd_at_start(self):
        """yyyy.mm.dd at the start of a title is parsed to yyyy-MM."""
        from dates import extract_title_date
        assert extract_title_date("2023.05.15 Summer holiday") == "2023-05"

    def test_yyyy_mm_dd_embedded(self):
        """yyyy.mm.dd embedded in a title is found and parsed."""
        from dates import extract_title_date
        assert extract_title_date("Holiday 2023.07.04 fun") == "2023-07"

    def test_yyyy_mm_dd_only(self):
        """Title that is only a date string."""
        from dates import extract_title_date
        assert extract_title_date("2019.12.31") == "2019-12"

    # ── year + English month name ─────────────────────────────────────────────

    def test_english_month_january(self):
        from dates import extract_title_date
        assert extract_title_date("2023 January trip") == "2023-01"

    def test_english_month_february(self):
        from dates import extract_title_date
        assert extract_title_date("2022 February") == "2022-02"

    def test_english_month_march(self):
        from dates import extract_title_date
        assert extract_title_date("2023 March skiing") == "2023-03"

    def test_english_month_may(self):
        """'May' matches as month name, not just any word."""
        from dates import extract_title_date
        assert extract_title_date("2023 May birthday") == "2023-05"

    def test_english_month_december(self):
        from dates import extract_title_date
        assert extract_title_date("2020 December Christmas") == "2020-12"

    # ── year + Danish month name ──────────────────────────────────────────────

    def test_danish_januar(self):
        from dates import extract_title_date
        assert extract_title_date("2023 Januar") == "2023-01"

    def test_danish_februar(self):
        from dates import extract_title_date
        assert extract_title_date("2022 Februar") == "2022-02"

    def test_danish_marts(self):
        from dates import extract_title_date
        assert extract_title_date("2022 Marts") == "2022-03"

    def test_danish_maj(self):
        from dates import extract_title_date
        assert extract_title_date("2023 Maj tur") == "2023-05"

    def test_danish_juni(self):
        from dates import extract_title_date
        assert extract_title_date("2023 Juni Ferie") == "2023-06"

    def test_danish_juli(self):
        from dates import extract_title_date
        assert extract_title_date("2021 Juli sommer") == "2021-07"

    def test_danish_oktober(self):
        from dates import extract_title_date
        assert extract_title_date("2020 Oktober efterår") == "2020-10"

    # ── month before year (reversed order) ───────────────────────────────────

    def test_month_before_year_english(self):
        """Month name appearing before the year is also matched."""
        from dates import extract_title_date
        assert extract_title_date("June 2023 party") == "2023-06"

    def test_month_before_year_danish(self):
        from dates import extract_title_date
        assert extract_title_date("Juni 2023 ferie") == "2023-06"

    # ── case-insensitivity ────────────────────────────────────────────────────

    def test_lowercase_month(self):
        from dates import extract_title_date
        assert extract_title_date("2023 june holiday") == "2023-06"

    def test_uppercase_month(self):
        from dates import extract_title_date
        assert extract_title_date("2023 JUNE holiday") == "2023-06"

    def test_mixed_case_danish(self):
        from dates import extract_title_date
        assert extract_title_date("2023 jUnI ferie") == "2023-06"

    # ── no-match / negative cases ─────────────────────────────────────────────

    def test_no_date_returns_none(self):
        """Plain title with no date pattern returns None."""
        from dates import extract_title_date
        assert extract_title_date("My Photo Album") is None

    def test_year_only_returns_none(self):
        """A bare year without a month name returns None."""
        from dates import extract_title_date
        assert extract_title_date("2023 summer") is None

    def test_empty_string_returns_none(self):
        from dates import extract_title_date
        assert extract_title_date("") is None

    def test_none_returns_none(self):
        from dates import extract_title_date
        assert extract_title_date(None) is None

    def test_only_year_number_returns_none(self):
        from dates import extract_title_date
        assert extract_title_date("2023") is None

    # ── yyyy.mm.dd takes priority over year+month ─────────────────────────────

    def test_ymd_pattern_takes_priority(self):
        """When yyyy.mm.dd is present it is preferred over a month name."""
        from dates import extract_title_date
        # Title has both a dot-date and a separate month name — dot-date wins
        assert extract_title_date("2023.05.15 June trip") == "2023-05"


class TestComputeYearMonth:
    """Tests for compute_year_month()."""

    def test_uses_title_date_when_present(self):
        """title_date is the highest-priority source."""
        from dates import compute_year_month
        result = compute_year_month("2022-08", "2021-03-15 00:00:00", "2020-01-01 00:00:00")
        assert result == "2022-08"

    def test_uses_median_taken_when_no_title_date(self):
        """median_taken_date is used when title_date is None."""
        from dates import compute_year_month
        result = compute_year_month(None, "2021-03-15 00:00:00", "2020-01-01 00:00:00")
        assert result == "2021-03"

    def test_uses_updated_when_neither_title_nor_median(self):
        """Falls back to updated when both title_date and median_taken_date are None."""
        from dates import compute_year_month
        result = compute_year_month(None, None, "2020-01-01 00:00:00")
        assert result == "2020-01"

    def test_median_taken_date_truncated_to_year_month(self):
        """Only the first 7 characters (yyyy-MM) of median_taken_date are used."""
        from dates import compute_year_month
        result = compute_year_month(None, "2023-11-25 14:30:00", "2020-01-01 00:00:00")
        assert result == "2023-11"

    def test_updated_truncated_to_year_month(self):
        """Only the first 7 characters (yyyy-MM) of updated are used."""
        from dates import compute_year_month
        result = compute_year_month(None, None, "2019-07-04 08:30:00")
        assert result == "2019-07"

    def test_title_date_takes_priority_over_both(self):
        """title_date wins even when median_taken_date and updated are present."""
        from dates import compute_year_month
        result = compute_year_month("2024-06", "2020-01-01 00:00:00", "2019-01-01 00:00:00")
        assert result == "2024-06"

    def test_none_median_falls_back_correctly(self):
        """None median_taken_date (YouTube case) falls through to updated."""
        from dates import compute_year_month
        result = compute_year_month(None, None, "2023-09-10 12:00:00")
        assert result == "2023-09"
