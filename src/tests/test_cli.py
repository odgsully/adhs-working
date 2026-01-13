"""Tests for CLI module."""

from pathlib import Path

from typer.testing import CliRunner

from adhs_etl.cli import app

runner = CliRunner()


class TestCLI:
    """Test CLI commands."""

    def test_run_command_dry_run(
        self, sample_excel_file: Path, sample_field_map: Path, temp_dir: Path
    ):
        """Test run command with dry-run flag."""
        # Create a raw directory with the sample file
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        # Copy sample file to raw directory
        import shutil

        shutil.copy(sample_excel_file, raw_dir / "test_providers.xlsx")

        # Copy field map to working directory if different
        if sample_field_map != temp_dir / "field_map.yml":
            shutil.copy(sample_field_map, temp_dir / "field_map.yml")

        # Run CLI command
        result = runner.invoke(
            app,
            [
                "run",
                "--month",
                "2025-05",
                "--raw-dir",
                str(raw_dir),
                "--output-dir",
                str(temp_dir / "output"),
                "--dry-run",
            ],
            catch_exceptions=False,
        )

        # Check command succeeded
        assert result.exit_code == 0
        # Rich/Typer doesn't always capture output in tests the same way

        # Verify no output files were created (dry run)
        assert not (temp_dir / "output").exists()

    def test_run_command_missing_files(self, temp_dir: Path):
        """Test run command with missing raw files."""
        # Create empty raw directory
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "run",
                "--month",
                "2025-05",
                "--raw-dir",
                str(raw_dir),
                "--dry-run",
            ],
        )

        # Check command failed
        assert result.exit_code == 1
        # The error is logged, not printed to stdout with Typer/Rich

    def test_run_command_invalid_month(self, temp_dir: Path):
        """Test run command with invalid month format."""
        result = runner.invoke(
            app,
            [
                "run",
                "--month",
                "2025-13",  # Invalid month
                "--raw-dir",
                str(temp_dir),
                "--dry-run",
            ],
        )

        # Should fail validation
        assert result.exit_code != 0

    def test_validate_command_valid(self, sample_field_map: Path):
        """Test validate command with valid field map."""
        result = runner.invoke(
            app,
            ["validate", "--field-map", str(sample_field_map)],
        )

        assert result.exit_code == 0
        # Rich/Typer output not captured in test mode

    def test_validate_command_missing(self, temp_dir: Path):
        """Test validate command with missing field map."""
        result = runner.invoke(
            app,
            ["validate", "--field-map", str(temp_dir / "missing.yml")],
        )

        assert result.exit_code == 1
        # Error is logged, not in stdout

    def test_validate_command_invalid(self, temp_dir: Path):
        """Test validate command with invalid YAML."""
        invalid_yaml = temp_dir / "invalid.yml"
        invalid_yaml.write_text("invalid: yaml: content:")

        result = runner.invoke(
            app,
            ["validate", "--field-map", str(invalid_yaml)],
        )

        assert result.exit_code == 1

    def test_fuzzy_threshold_option(
        self, sample_excel_file: Path, sample_field_map: Path, temp_dir: Path
    ):
        """Test fuzzy threshold option."""
        # Create a raw directory with the sample file
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        import shutil

        shutil.copy(sample_excel_file, raw_dir / "test.xlsx")
        if sample_field_map != temp_dir / "field_map.yml":
            shutil.copy(sample_field_map, temp_dir / "field_map.yml")

        result = runner.invoke(
            app,
            [
                "run",
                "--month",
                "2025-05",
                "--raw-dir",
                str(raw_dir),
                "--fuzzy-threshold",
                "90.5",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

    def test_log_level_option(
        self, sample_excel_file: Path, sample_field_map: Path, temp_dir: Path
    ):
        """Test log level option."""
        # Create a raw directory with the sample file
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        import shutil

        shutil.copy(sample_excel_file, raw_dir / "test.xlsx")
        if sample_field_map != temp_dir / "field_map.yml":
            shutil.copy(sample_field_map, temp_dir / "field_map.yml")

        result = runner.invoke(
            app,
            [
                "run",
                "--month",
                "2025-05",
                "--raw-dir",
                str(raw_dir),
                "--log-level",
                "DEBUG",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
