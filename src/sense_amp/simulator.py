"""Circuit simulator interface (Cadence Spectre primary, HSPICE optional)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sense_amp.extract.measures import collect_simulation_measures, parse_measures
from sense_amp.paths import include_search_roots


class SimulatorBackend(str, Enum):
    """Supported SPICE simulators."""

    SPECTRE = "spectre"
    HSPICE = "hspice"


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


DEFAULT_CADENCE_ENV = Path("/eda/env/cadence.river.zsh")


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


def cadence_env_file() -> Path | None:
    """Return Cadence environment script path if configured or present."""
    env = os.environ.get("CADENCE_ENV")
    if env:
        path = Path(env)
        return path if path.is_file() else None
    return DEFAULT_CADENCE_ENV if DEFAULT_CADENCE_ENV.is_file() else None


def resolve_backend(requested: str | None = None) -> SimulatorBackend:
    """Resolve simulator backend from env, request, or auto-detection."""
    choice = (requested or os.environ.get("OPEN_DRAM_SIMULATOR", "")).lower().strip()
    if choice == "spectre":
        if not find_spectre() and not cadence_env_file():
            raise RuntimeError(
                "Spectre requested but not found. Source Cadence env or set SPECTRE."
            )
        return SimulatorBackend.SPECTRE
    if choice == "hspice":
        if not find_hspice():
            raise RuntimeError("HSPICE requested but not found.")
        return SimulatorBackend.HSPICE
    if find_spectre() or cadence_env_file():
        return SimulatorBackend.SPECTRE
    if find_hspice():
        return SimulatorBackend.HSPICE
    raise RuntimeError(
        "No supported simulator found. Source /eda/env/cadence.river.zsh for Spectre, "
        "or set OPEN_DRAM_SIMULATOR=hspice with HSPICE on PATH."
    )


def simulator_available(backend: SimulatorBackend | None = None) -> bool:
    """Return True when the requested (or any) backend is available."""
    try:
        resolve_backend(backend.value if backend else None)
        return True
    except RuntimeError:
        return False


def _collect_measure_files(cwd: Path, stem: str) -> dict[str, float]:
    measures = collect_simulation_measures(cwd, stem)
    if measures:
        return measures
    lis_path = cwd / f"{stem}.lis"
    if lis_path.is_file():
        return parse_measures(lis_path.read_text(encoding="utf-8", errors="replace"))
    return {}


def _run_subprocess(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _include_root_args() -> list[str]:
    """Return ``-I`` flags so repo-relative ``.include`` paths resolve."""
    return [f"-I{root.as_posix()}" for root in include_search_roots()]


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
            "Spectre not found. Source /eda/env/cadence.river.zsh or set CADENCE_ENV."
        )

    combined = proc.stdout + "\n" + proc.stderr
    measures = parse_measures(combined)
    measures.update(_collect_measure_files(cwd, deck_path.stem))

    log_file = cwd / f"{deck_path.stem}.log"
    print_file = cwd / f"{deck_path.stem}.print"
    measure_file = cwd / f"{deck_path.stem}.measure"
    return SimulationResult(
        deck_path=deck_path,
        backend=SimulatorBackend.SPECTRE,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        measures=measures,
        log_path=log_file if log_file.is_file() else None,
        print_path=print_file if print_file.is_file() else None,
        measure_path=measure_file if measure_file.is_file() else None,
    )


def run_hspice(deck_path: Path, work_dir: Path | None = None) -> SimulationResult:
    """Run HSPICE on a single deck in batch mode."""
    hspice = find_hspice()
    if hspice is None:
        raise RuntimeError("HSPICE not found. Set HSPICE=/path/to/hspice.")

    deck_resolved = deck_path.resolve()
    cwd = work_dir or deck_path.parent
    cwd.mkdir(parents=True, exist_ok=True)
    inc_args: list[str] = []
    for root in include_search_roots():
        inc_args.extend(["-inc", root.as_posix()])
    proc = _run_subprocess(
        [
            str(hspice),
            *inc_args,
            "-i",
            deck_resolved.as_posix(),
            "-o",
            deck_path.stem,
        ],
        cwd,
    )
    combined = proc.stdout + "\n" + proc.stderr
    measures = parse_measures(combined)
    measures.update(_collect_measure_files(cwd, deck_path.stem))

    lis = cwd / f"{deck_path.stem}.lis"
    mt0_file = cwd / f"{deck_path.stem}.mt0"
    return SimulationResult(
        deck_path=deck_path,
        backend=SimulatorBackend.HSPICE,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        measures=measures,
        log_path=lis if lis.is_file() else None,
        print_path=None,
        measure_path=mt0_file if mt0_file.is_file() else None,
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
    return run_hspice(deck_path, work_dir)


def load_simulation_result(
    deck_path: Path,
    backend: SimulatorBackend | str | None = None,
) -> SimulationResult:
    """Build a ``SimulationResult`` from existing simulation artifacts (no re-run)."""
    resolved = resolve_backend(backend.value if isinstance(backend, SimulatorBackend) else backend)
    cwd = deck_path.parent
    stem = deck_path.stem
    measures = _collect_measure_files(cwd, stem)
    log_path = cwd / f"{stem}.log"
    print_path = cwd / f"{stem}.print"
    if resolved is SimulatorBackend.HSPICE:
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
        log_path=log_path if log_path.is_file() else None,
        print_path=print_path if print_path.is_file() else None,
        measure_path=measure_path if measure_path.is_file() else None,
    )
