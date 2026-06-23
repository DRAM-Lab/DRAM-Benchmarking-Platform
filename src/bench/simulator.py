"""Circuit simulator interface (Spectre primary, HSPICE/ngspice optional)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from bench.extract.measures import collect_simulation_measures, parse_measures
from bench.paths import PROJECT_ROOT


class SimulatorBackend(str, Enum):
    """Supported SPICE simulators."""

    SPECTRE = "spectre"
    HSPICE = "hspice"
    NGSPICE = "ngspice"


def uses_spectre_deck(backend: SimulatorBackend) -> bool:
    """Return True when netlists should use Spectre-specific analysis/measure syntax."""
    return backend == SimulatorBackend.SPECTRE


def uses_hspice_deck(backend: SimulatorBackend) -> bool:
    """Return True when netlists should use HSPICE/ngspice-compatible syntax."""
    return backend in (SimulatorBackend.HSPICE, SimulatorBackend.NGSPICE)


@dataclass(frozen=True)
class SimulationResult:
    """Outcome of one SPICE deck execution."""

    deck_path: Path
    backend: SimulatorBackend
    stdout: str
    stderr: str
    returncode: int
    measures: dict[str, float]
    log_path: Path | None
    print_path: Path | None
    measure_path: Path | None

    @property
    def lis_path(self) -> Path | None:
        """Backward-compatible alias for HSPICE `.lis` or Spectre `.log`."""
        return self.log_path


def find_spectre() -> Path | None:
    """Locate Spectre executable from PATH or SPECTRE env var."""
    env = os.environ.get("SPECTRE")
    if env and Path(env).is_file():
        return Path(env)
    found = shutil.which("spectre")
    return Path(found) if found else None


def find_hspice() -> Path | None:
    """Locate HSPICE executable from PATH or HSPICE env var."""
    env = os.environ.get("HSPICE")
    if env and Path(env).is_file():
        return Path(env)
    for name in ("hspice", "hspice64"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def find_ngspice() -> Path | None:
    """Locate ngspice executable from PATH or NGSPICE env var."""
    env = os.environ.get("NGSPICE")
    if env and Path(env).is_file():
        return Path(env)
    found = shutil.which("ngspice")
    return Path(found) if found else None


def cadence_env_file() -> Path | None:
    """Return Cadence environment script path when ``CADENCE_ENV`` is set and valid."""
    env = os.environ.get("CADENCE_ENV")
    if not env:
        return None
    path = Path(env)
    return path if path.is_file() else None


def resolve_backend(requested: str | None = None) -> SimulatorBackend:
    """Resolve simulator backend from env, request, or auto-detection.

    Priority: explicit ``requested`` > ``OPEN_DRAM_SIMULATOR`` env >
    Spectre (if available) > HSPICE.
    """
    choice = (requested or os.environ.get("OPEN_DRAM_SIMULATOR", "")).lower().strip()
    if choice == "spectre":
        if not find_spectre() and not cadence_env_file():
            raise RuntimeError("Spectre requested but not found. Source Cadence env or set SPECTRE.")
        return SimulatorBackend.SPECTRE
    if choice == "hspice":
        if not find_hspice():
            raise RuntimeError("HSPICE requested but not found.")
        return SimulatorBackend.HSPICE
    if choice == "ngspice":
        if not find_ngspice():
            raise RuntimeError("ngspice requested but not found. Set NGSPICE=/path/to/ngspice.")
        return SimulatorBackend.NGSPICE
    if find_spectre() or cadence_env_file():
        return SimulatorBackend.SPECTRE
    if find_hspice():
        return SimulatorBackend.HSPICE
    if find_ngspice():
        return SimulatorBackend.NGSPICE
    raise RuntimeError(
        "No supported simulator found. Put Spectre on PATH, set CADENCE_ENV, "
        "set OPEN_DRAM_SIMULATOR=hspice|ngspice, or install ngspice on PATH."
    )


def simulator_available(backend: SimulatorBackend | None = None) -> bool:
    """Return True when the requested (or any) backend is available."""
    try:
        resolve_backend(backend.value if backend else None)
        return True
    except RuntimeError:
        return False


def hspice_available() -> bool:
    """Return True when HSPICE is discoverable."""
    return find_hspice() is not None


def ngspice_available() -> bool:
    """Return True when ngspice is discoverable."""
    return find_ngspice() is not None


def spectre_available() -> bool:
    """Return True when Spectre is discoverable (directly or via Cadence env)."""
    return find_spectre() is not None or cadence_env_file() is not None


def available_backends() -> list[SimulatorBackend]:
    """Return all simulator backends currently discoverable on this host."""
    backends: list[SimulatorBackend] = []
    if spectre_available():
        backends.append(SimulatorBackend.SPECTRE)
    if hspice_available():
        backends.append(SimulatorBackend.HSPICE)
    if ngspice_available():
        backends.append(SimulatorBackend.NGSPICE)
    return backends


def use_multi_simulator_mode(explicit_backend: str | None = None) -> bool:
    """Return True when every available backend should run with comparison.

    Multi-simulator mode is disabled when the user pins one backend via CLI
    ``--simulator`` or the ``OPEN_DRAM_SIMULATOR`` environment variable.
    """
    if explicit_backend:
        return False
    if os.environ.get("OPEN_DRAM_SIMULATOR", "").strip():
        return False
    return len(available_backends()) >= 2


def _ngspice_log_path(artifact_dir: Path, stem: str) -> Path | None:
    """Return ngspice batch log path (``-o`` prefix has no extension)."""
    for name in (stem, f"{stem}.lis"):
        path = artifact_dir / name
        if path.is_file():
            return path
    return None


def _collect_measure_files(cwd: Path, stem: str) -> dict[str, float]:
    """Merge measures from backend-specific auxiliary files (no `.log`)."""
    measures = collect_simulation_measures(cwd, stem)
    if measures:
        return measures
    lis_path = _ngspice_log_path(cwd, stem)
    if lis_path is not None:
        return parse_measures(lis_path.read_text(encoding="utf-8", errors="replace"))
    return {}


def _run_subprocess(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _include_root_args() -> list[str]:
    """Return ``-I`` flags so repo-relative ``.include`` paths resolve."""
    return [f"-I{PROJECT_ROOT.as_posix()}"]


def run_spectre(deck_path: Path, work_dir: Path | None = None) -> SimulationResult:
    """Run Cadence Spectre on a single deck."""
    cwd = work_dir or deck_path.parent
    cwd.mkdir(parents=True, exist_ok=True)
    deck = deck_path.name
    env_file = cadence_env_file()
    spectre = find_spectre()
    include_args = _include_root_args()

    if env_file and spectre is None:
        inc = " ".join(include_args)
        cmd = ["bash", "-lc", f"source '{env_file}' && spectre {inc} '{deck}'"]
        proc = _run_subprocess(cmd, cwd)
    elif spectre is not None:
        proc = _run_subprocess([str(spectre), *include_args, deck], cwd)
    else:
        raise RuntimeError(
            "Spectre not found. Put spectre on PATH, set SPECTRE, or set CADENCE_ENV."
        )

    combined = proc.stdout + "\n" + proc.stderr
    measures = parse_measures(combined)
    measures.update(_collect_measure_files(cwd, deck_path.stem))

    return SimulationResult(
        deck_path=deck_path,
        backend=SimulatorBackend.SPECTRE,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        measures=measures,
        log_path=cwd / f"{deck_path.stem}.log" if (cwd / f"{deck_path.stem}.log").is_file() else None,
        print_path=cwd / f"{deck_path.stem}.print"
        if (cwd / f"{deck_path.stem}.print").is_file()
        else None,
        measure_path=cwd / f"{deck_path.stem}.measure"
        if (cwd / f"{deck_path.stem}.measure").is_file()
        else None,
    )


def run_hspice(deck_path: Path, work_dir: Path | None = None) -> SimulationResult:
    """Run HSPICE on a single deck in batch mode."""
    hspice = find_hspice()
    if hspice is None:
        raise RuntimeError("HSPICE not found. Set HSPICE=/path/to/hspice.")

    deck_resolved = deck_path.resolve()
    artifact_dir = (work_dir or deck_path.parent).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stem = deck_resolved.stem
    out_prefix = artifact_dir / stem

    proc = _run_subprocess(
        [
            str(hspice),
            "-inc",
            PROJECT_ROOT.as_posix(),
            "-i",
            deck_resolved.as_posix(),
            "-o",
            out_prefix.as_posix(),
        ],
        artifact_dir,
    )
    combined = proc.stdout + "\n" + proc.stderr
    measures = parse_measures(combined)
    measures.update(_collect_measure_files(artifact_dir, stem))

    lis = artifact_dir / f"{stem}.lis"
    return SimulationResult(
        deck_path=deck_path,
        backend=SimulatorBackend.HSPICE,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        measures=measures,
        log_path=lis if lis.is_file() else None,
        print_path=None,
        measure_path=artifact_dir / f"{stem}.mt0"
        if (artifact_dir / f"{stem}.mt0").is_file()
        else None,
    )


def run_ngspice(deck_path: Path, work_dir: Path | None = None) -> SimulationResult:
    """Run ngspice on a single deck in batch mode (HSPICE-compatible deck dialect)."""
    ngspice = find_ngspice()
    if ngspice is None:
        raise RuntimeError("ngspice not found. Set NGSPICE=/path/to/ngspice.")

    deck_resolved = deck_path.resolve()
    artifact_dir = (work_dir or deck_path.parent).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stem = deck_resolved.stem
    out_prefix = artifact_dir / stem

    proc = _run_subprocess(
        [str(ngspice), "-b", "-o", out_prefix.as_posix(), deck_resolved.as_posix()],
        artifact_dir,
    )
    combined = proc.stdout + "\n" + proc.stderr
    measures = parse_measures(combined)
    measures.update(_collect_measure_files(artifact_dir, stem))

    log_path = _ngspice_log_path(artifact_dir, stem)
    return SimulationResult(
        deck_path=deck_path,
        backend=SimulatorBackend.NGSPICE,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        measures=measures,
        log_path=log_path,
        print_path=artifact_dir / f"{stem}.print"
        if (artifact_dir / f"{stem}.print").is_file()
        else None,
        measure_path=artifact_dir / f"{stem}.measure"
        if (artifact_dir / f"{stem}.measure").is_file()
        else None,
    )


def run_simulation(
    deck_path: Path,
    work_dir: Path | None = None,
    backend: SimulatorBackend | str | None = None,
) -> SimulationResult:
    """Run a deck with the resolved or requested simulator backend."""
    resolved = resolve_backend(backend.value if isinstance(backend, SimulatorBackend) else backend)
    if resolved is SimulatorBackend.SPECTRE:
        return run_spectre(deck_path, work_dir)
    if resolved is SimulatorBackend.HSPICE:
        return run_hspice(deck_path, work_dir)
    return run_ngspice(deck_path, work_dir)


def load_simulation_result(
    deck_path: Path,
    backend: SimulatorBackend | str | None = None,
) -> SimulationResult:
    """Build a ``SimulationResult`` from existing simulation artifacts (no re-run).

    Args:
        deck_path: Path to the SPICE deck (``.sp``).
        backend: Simulator backend used for the original run.

    Returns:
        Result populated from ``.measure``, ``.print``, and log files in the deck directory.
    """
    resolved = resolve_backend(backend.value if isinstance(backend, SimulatorBackend) else backend)
    cwd = deck_path.parent
    stem = deck_path.stem
    measures = _collect_measure_files(cwd, stem)
    if resolved is SimulatorBackend.NGSPICE:
        log_path = _ngspice_log_path(cwd, stem)
    else:
        log_path = cwd / f"{stem}.log"
        if not log_path.is_file() and resolved is SimulatorBackend.HSPICE:
            log_path = cwd / f"{stem}.lis"
        if not log_path.is_file():
            log_path = None
    print_path = cwd / f"{stem}.print"
    if resolved is SimulatorBackend.HSPICE:
        measure_path = cwd / f"{stem}.mt0"
    elif resolved is SimulatorBackend.NGSPICE:
        measure_path = cwd / f"{stem}.measure"
        if not measure_path.is_file():
            measure_path = cwd / f"{stem}.mt0"
    else:
        measure_path = cwd / f"{stem}.measure"
    return SimulationResult(
        deck_path=deck_path,
        backend=resolved,
        stdout="",
        stderr="",
        returncode=0,
        measures=measures,
        log_path=log_path,
        print_path=print_path if print_path.is_file() else None,
        measure_path=measure_path if measure_path.is_file() else None,
    )
