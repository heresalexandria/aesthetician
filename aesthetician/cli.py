"""Aesthetician command-line interface."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Optional

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.table import Table

console = Console()


def _parse_value(raw: str) -> Any:
    low = raw.lower()
    if low in ("true", "on", "yes"):
        return True
    if low in ("false", "off", "no"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _split_overrides(pairs: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Route key=value overrides to (video, audio) by the a_ effect prefix."""
    video: dict[str, Any] = {}
    audio: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise click.BadParameter(f"--set expects effect.param=value, got {pair!r}")
        path, raw = pair.split("=", 1)
        target = audio if path.split(".", 1)[0].startswith("a_") else video
        target[path.strip()] = _parse_value(raw.strip())
    return video, audio


@click.group(help="Aesthetician — era-authentic film/tape/broadcast looks and sounds for video.")
def main() -> None:
    pass


@main.command("list")
@click.option("--family", default=None, help="Filter by family (vhs, film, broadcast, cartoon, digital, audio…).")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def list_cmd(family: Optional[str], as_json: bool) -> None:
    """List all presets, grouped by family."""
    from .engine.presets import all_presets

    presets = sorted(all_presets().values(), key=lambda p: (p.family, p.id))
    if family:
        presets = [p for p in presets if p.family == family]
    if as_json:
        click.echo(json.dumps([{"id": p.id, "name": p.name, "family": p.family, "era": p.era} for p in presets]))
        return
    fam = None
    for p in presets:
        if p.family != fam:
            fam = p.family
            console.print(f"\n[bold cyan]{fam.upper()}[/bold cyan]")
        variants = f"  [dim]({len(p.variants)} variants)[/dim]" if p.variants else ""
        console.print(f"  [bold]{p.id:<28}[/bold] {p.era:<12} {p.name}{variants}")
    console.print(f"\n[dim]{len(presets)} presets. `aesthetician info <id>` for details.[/dim]")


@main.command()
@click.argument("preset_id")
def info(preset_id: str) -> None:
    """Show a preset's chains, parameters, and variants."""
    from .engine.graph import get_effect
    from .engine.presets import get_preset

    p = get_preset(preset_id)
    console.print(f"\n[bold]{p.name}[/bold]  [dim]{p.id} · {p.family} · {p.era}[/dim]")
    console.print(p.desc + "\n")
    if p.variants:
        t = Table(title="Variants", show_lines=False)
        t.add_column("id", style="bold")
        t.add_column("name")
        t.add_column("description")
        for v in p.variants:
            t.add_row(v.id, v.name, v.desc)
        console.print(t)

    for title, chain in (("Video chain", p.video), ("Audio chain", p.audio)):
        if not chain:
            continue
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
        counts: dict[str, int] = {}
        for eid, params in chain:
            counts[eid] = counts.get(eid, 0) + 1
            key = eid if counts[eid] == 1 else f"{eid}#{counts[eid]}"
            cls = get_effect(eid)
            console.print(f"  [bold]{key}[/bold] — {cls.label}")
            byname = {pp.name: pp for pp in cls.PARAMS}
            for pp in cls.PARAMS:
                cur = params.get(pp.name, pp.default)
                marker = "[yellow]•[/yellow]" if pp.name in params else " "
                rng = f"{pp.lo}–{pp.hi}" if pp.kind in ("float", "int") else "/".join(pp.choices) if pp.kind == "enum" else "bool"
                console.print(f"    {marker} {key}.{pp.name} = {cur}  [dim]({rng}{' ' + pp.unit if pp.unit else ''}) {pp.desc}[/dim]")
    console.print(
        "\n[dim]Override anything with --set effect.param=value (audio effects start with a_).[/dim]"
    )


@main.command()
@click.option("--json", "as_json", is_flag=True)
def effects(as_json: bool) -> None:
    """List every available effect and its parameters."""
    from .engine.graph import all_effects

    if as_json:
        from .schema import effect_schema

        click.echo(json.dumps(effect_schema()))
        return
    for eid, cls in sorted(all_effects().items()):
        console.print(f"[bold]{eid:<18}[/bold] [{cls.kind}] {cls.label} — [dim]{cls.desc}[/dim]")


@main.command()
def schema() -> None:
    """Dump the full machine-readable schema (effects + presets) as JSON."""
    from .schema import full_schema

    click.echo(json.dumps(full_schema()))


def _run_render(
    input_path: str,
    output: Optional[str],
    preset_id: str,
    variant: Optional[str],
    sets: tuple[str, ...],
    seed: Optional[int],
    intensity: float,
    texture: float,
    video_only: bool,
    audio_only: bool,
    start: float,
    duration: Optional[float],
    scale: float,
    crf: int,
    json_progress: bool,
    suffix: str,
) -> str:
    from .engine.presets import get_preset
    from .engine.render import RenderOptions, render

    preset = get_preset(preset_id)
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "little") % 999983 + 1
    video_over, audio_over = _split_overrides(sets)

    if not output:
        base, ext = os.path.splitext(input_path)
        vtag = f"-{variant}" if variant else ""
        output = f"{base}.{preset_id.replace('/', '-')}{vtag}{suffix}{ext or '.mp4'}"

    opts = RenderOptions(
        seed=seed,
        intensity=intensity,
        texture=texture,
        variant=variant,
        video_overrides=video_over,
        audio_overrides=audio_over,
        video_only=video_only,
        audio_only=audio_only,
        t0=start,
        duration=duration,
        scale=scale,
        crf=crf,
    )

    t_start = time.time()
    if json_progress:
        def cb(phase: str, frac: float) -> None:
            click.echo(json.dumps({"phase": phase, "progress": round(frac, 4)}), nl=True)
            sys.stdout.flush()

        render(input_path, output, preset, opts, progress=cb)
    else:
        console.print(f"[bold]{preset.name}[/bold] → {output}  [dim](seed {seed})[/dim]")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as prog:
            task = prog.add_task("render", total=1000)

            def cb(phase: str, frac: float) -> None:
                prog.update(task, completed=int(frac * 1000), description=phase)

            render(input_path, output, preset, opts, progress=cb)
    if not json_progress:
        console.print(f"[green]done[/green] in {time.time() - t_start:.1f}s")
    return output


_render_options = [
    click.option("--preset", "-p", "preset_id", required=True, help="Preset id (see `list`)."),
    click.option("--variant", default=None, help="Preset variant id."),
    click.option("--set", "sets", multiple=True, help="Override: effect.param=value (repeatable)."),
    click.option("--seed", type=int, default=None, help="Fix the random seed (default: random, printed)."),
    click.option("--intensity", type=float, default=1.0, help="Master strength multiplier (0–2)."),
    click.option("--texture", type=float, default=1.0,
                 help="Master grain/noise multiplier (0 = clean, 1 = as authored, 2 = heavy)."),
    click.option("--video-only", is_flag=True, help="Leave audio untouched."),
    click.option("--audio-only", is_flag=True, help="Leave video untouched."),
    click.option("--start", type=float, default=0.0, help="Start offset (s)."),
    click.option("--duration", type=float, default=None, help="Limit duration (s)."),
    click.option("--crf", type=int, default=17, help="Output H.264 CRF."),
    click.option("--json-progress", is_flag=True, help="Emit JSON progress lines (for the GUI)."),
]


def _with(opts):
    def deco(f):
        for o in reversed(opts):
            f = o(f)
        return f
    return deco


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", default=None, help="Output file (default: alongside input).")
@click.option("--scale", type=float, default=1.0, help="Output scale factor.")
@_with(_render_options)
def apply(input_path, output, scale, **kw) -> None:
    """Apply a preset to a video."""
    _run_render(input_path, output, scale=scale, suffix="", **kw)


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", default=None, help="Output file (default: alongside input).")
@click.option("--at", type=float, default=None, help="Preview position (s); default: clip middle.")
@click.option("--scale", type=float, default=0.5, help="Preview scale (default 0.5).")
@_with(_render_options)
def preview(input_path, output, at, scale, **kw) -> None:
    """Render a fast 3-second preview."""
    from .engine.media import probe

    if at is not None:
        kw["start"] = at
    elif not kw.get("start"):
        info = probe(input_path)
        kw["start"] = max((info.duration - 3.0) / 2, 0.0)
    if kw.get("duration") is None:
        kw["duration"] = 3.0
    _run_render(input_path, output, scale=scale, suffix=".preview", **kw)


@main.command("probe")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
def probe_cmd(input_path: str) -> None:
    """Probe a media file (JSON) — used by the GUI."""
    from .engine.media import probe

    info = probe(input_path)
    click.echo(
        json.dumps(
            {
                "path": info.path,
                "width": info.width,
                "height": info.height,
                "fps": info.fps,
                "duration": info.duration,
                "n_frames": info.n_frames,
                "has_audio": info.has_audio,
                "sr": info.sr,
                "channels": info.channels,
            }
        )
    )


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", required=True)
@click.option("--start", type=float, default=0.0)
@click.option("--duration", type=float, default=3.0)
@click.option("--scale", type=float, default=0.5)
def snippet(input_path: str, output: str, start: float, duration: float, scale: float) -> None:
    """Extract an untreated segment (the 'before' side of A/B) — used by the GUI."""
    from .engine.media import probe as _probe
    from .engine.render import _even, _plain_video

    info = _probe(input_path)
    w, h = _even(int(info.width * scale)), _even(int(info.height * scale))
    _plain_video(input_path, output, w, h, info.fps, start, duration, crf=17)
    if info.has_audio:
        import subprocess

        tmp = output + ".mux.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", output, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
             "-i", input_path, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", tmp],
            check=True,
        )
        os.replace(tmp, output)
    click.echo(json.dumps({"output": output}))


@main.group()
def assets() -> None:
    """Overlay asset packs (generation and status)."""


@assets.command("status")
def assets_status() -> None:
    from .assets.manifest import pack_status

    for name, info in pack_status().items():
        state = f"[green]{info['present']}/{info['count']}[/green]" if info["present"] else "[red]missing[/red]"
        console.print(f"{name:<22} {state}  [dim]{info['desc']}[/dim]")
    console.print("[dim]Generate with: aesthetician assets generate[/dim]")


@assets.command("generate")
@click.option("--pack", default=None, help="Only this pack.")
@click.option("--force", is_flag=True, help="Regenerate even if present.")
def assets_generate(pack: Optional[str], force: bool) -> None:
    from .assets.openai_gen import generate_packs

    generate_packs(only=pack, force=force, log=console.print)


if __name__ == "__main__":
    main()
