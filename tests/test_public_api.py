"""
Tests for the public API surface of research_core.

These tests verify that the top-level __init__.py exports are complete
and that no unexpected runtime dependencies are introduced.
"""

from __future__ import annotations


class TestPublicApiExports:
    def test_version_available(self) -> None:
        import research_core

        assert hasattr(research_core, "__version__")
        assert isinstance(research_core.__version__, str)
        assert research_core.__version__ != "0.0.0"  # RC1 bumps to 0.1.0

    def test_all_defined(self) -> None:
        import research_core

        assert hasattr(research_core, "__all__")
        assert len(research_core.__all__) > 0

    def test_all_exports_importable(self) -> None:
        import research_core

        for name in research_core.__all__:
            assert hasattr(research_core, name), f"__all__ member {name!r} is not accessible"

    def test_contracts_package_importable(self) -> None:
        from research_core import contracts

        assert hasattr(contracts, "__all__")

    def test_protocols_package_importable(self) -> None:
        from research_core import protocols

        assert hasattr(protocols, "__all__")

    def test_exceptions_importable(self) -> None:
        from research_core.exceptions import (
            ContractValidationError,
            ProviderUnavailableError,
            ResearchCoreError,
            UnknownProfileError,
        )
        assert issubclass(ContractValidationError, ResearchCoreError)
        assert issubclass(UnknownProfileError, ResearchCoreError)
        assert issubclass(ProviderUnavailableError, ResearchCoreError)

    def test_key_contracts_at_top_level(self) -> None:
        import research_core

        assert hasattr(research_core, "ResearchRequest")
        assert hasattr(research_core, "ResearchResult")
        assert hasattr(research_core, "ResearchStatus")
        assert hasattr(research_core, "serialize")

    def test_key_protocols_at_top_level(self) -> None:
        import research_core

        assert hasattr(research_core, "KnowledgeProvider")
        assert hasattr(research_core, "Synthesizer")
        assert hasattr(research_core, "ProfileProvider")
        assert hasattr(research_core, "Renderer")

    def test_no_failed_status(self) -> None:
        from research_core import ResearchStatus

        names = {m.name for m in ResearchStatus}
        assert "FAILED" not in names
        assert "COMPLETE" in names
        assert "PARTIAL" in names


class TestNoRuntimeDependencies:
    def test_no_prohibited_third_party_imports(self) -> None:
        """Verify that known third-party AI/LLM libraries are not imported at load time.

        Uses a subprocess to get a clean import environment, independent of the
        test runner's already-loaded modules (pytest, anyio, pygments, etc.).
        """
        import subprocess
        import sys

        script = (
            "import sys; "
            "import research_core; "
            "prohibited = ['anthropic', 'openai', 'langchain', 'transformers', "
            "              'torch', 'tensorflow', 'httpx', 'aiohttp', 'requests']; "
            "found = [p for p in prohibited if p in sys.modules or "
            "         any(k.startswith(p + '.') for k in sys.modules)]; "
            "print('FOUND:' + ','.join(found) if found else 'OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Import check failed:\n{result.stderr}"
        )
        output = result.stdout.strip()
        assert output == "OK", (
            f"Prohibited third-party modules imported by research_core: {output}"
        )
