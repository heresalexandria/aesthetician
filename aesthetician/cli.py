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


def _split_mapping(sets: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Same routing as _split_overrides, for values that arrived already typed."""
    video: dict[str, Any] = {}
    audio: dict[str, Any] = {}
    for path, value in (sets or {}).items():
        target = audio if path.split(".", 1)[0].startswith("a_") else video
        target[path.strip()] = value
    return video, audio


def _parse_layers(raw: str) -> list[Any]:
    """Build engine Layers from the JSON the GUI sends.

    Accepts inline JSON or `@path`. The file form matters on Windows, where the
    whole command line is capped at 32k and a deep stack of overrides can get
    close to it.
    """
    from .engine.presets import get_preset
    from .engine.render import Layer

    text = raw
    if raw.startswith("@"):
        with open(raw[1:], encoding="utf-8") as fh:
            text = fh.read()
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as err:
        raise click.BadParameter(f"--layers is not valid JSON: {err}") from err
    if not isinstance(spec, list) or not spec:
        raise click.BadParameter("--layers expects a non-empty JSON array")

    layers = []
    for i, item in enumerate(spec):
        if not isinstance(item, dict) or not item.get("preset"):
            raise click.BadParameter(f"--layers[{i}] needs a 'preset' id")
        # A disabled layer is simply absent from the render, which is what makes
        # the checkbox in the GUI free rather than a re-render of everything.
        # Both section switches off means the same thing: the layer would only
        # cost an encode to change nothing.
        picture = item.get("picture") is not False
        sound = item.get("sound") is not False
        if item.get("enabled") is False or not (picture or sound):
            continue
        video_over, audio_over = _split_mapping(item.get("sets") or {})
        edits = item.get("events") or []
        if not isinstance(edits, list):
            raise click.BadParameter(f"--layers[{i}].events must be a list of ops")
        layers.append(Layer(
            preset=get_preset(item["preset"]),
            variant=item.get("variant") or None,
            video_overrides=video_over,
            audio_overrides=audio_over,
            seed=int(item.get("seed", 1)),
            intensity=float(item.get("intensity", 1.0)),
            texture=float(item.get("texture", 1.0)),
            event_edits=[e for e in edits if isinstance(e, dict)],
            picture=picture,
            sound=sound,
        ))
    if not layers:
        raise click.BadParameter("every layer in --layers is disabled")
    return layers


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


@click.group(help="Aesthetician - era-authentic film/tape/broadcast looks and sounds for video.")
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
    from .taxonomy import facets_for

    facets = ", ".join(f"{k}: {'/'.join(v)}" for k, v in facets_for(p).items() if v)
    if p.tags:
        console.print(f"[dim]tags:[/dim] {', '.join(p.tags)}")
    if p.keywords:
        console.print(f"[dim]keywords:[/dim] {', '.join(p.keywords)}")
    if facets:
        console.print(f"[dim]facets:[/dim] {facets}")
    from .presets._introduced import INTRODUCED

    day, ver = INTRODUCED.get(p.id, ("", "unreleased"))
    if day:
        console.print(f"[dim]added:[/dim] {day} (v{ver})\n" if ver != "unreleased" else f"[dim]added:[/dim] {day} (unreleased)\n")
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
            console.print(f"  [bold]{key}[/bold] - {cls.label}")
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
        console.print(f"[bold]{eid:<18}[/bold] [{cls.kind}] {cls.label} - [dim]{cls.desc}[/dim]")


@main.command()
def schema() -> None:
    """Dump the full machine-readable schema (effects + presets) as JSON."""
    from .schema import full_schema

    click.echo(json.dumps(full_schema()))


def _dispatch(input_path, output, preset, stack, opts, cb) -> None:
    """One preset or a stack of them, same progress callback either way."""
    from .engine.render import render, render_layers

    if stack:
        render_layers(input_path, output, stack, opts, progress=cb)
    else:
        render(input_path, output, preset, opts, progress=cb)


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
    layers_json: Optional[str] = None,
) -> str:
    from .engine.presets import get_preset
    from .engine.render import RenderOptions, render, render_layers

    stack = _parse_layers(layers_json) if layers_json else None
    if not stack and not preset_id:
        raise click.UsageError("give --preset, or --layers for a stack")
    # A stack takes its identity from its bottom layer; --preset is ignored, and
    # the single-preset path below is left exactly as it was.
    preset = stack[0].preset if stack else get_preset(preset_id)
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "little") % 999983 + 1
    video_over, audio_over = _split_overrides(sets)

    if not output:
        from .engine.media import probe as _probe

        base, ext = os.path.splitext(input_path)
        vtag = f"-{variant}" if variant else ""
        if not ext:
            ext = ".mp4" if _probe(input_path).has_video else ".wav"
        if stack:
            extra = f"+{len(stack) - 1}" if len(stack) > 1 else ""
            output = f"{base}.{preset.id.replace('/', '-')}{extra}{suffix}{ext}"
        else:
            output = f"{base}.{preset_id.replace('/', '-')}{vtag}{suffix}{ext}"

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

        _dispatch(input_path, output, preset, stack, opts, cb)
    else:
        what = (f"{preset.name} +{len(stack) - 1} more" if stack and len(stack) > 1
                else preset.name)
        console.print(f"[bold]{what}[/bold] → {output}  [dim](seed {seed})[/dim]")
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

            _dispatch(input_path, output, preset, stack, opts, cb)
    if not json_progress:
        console.print(f"[green]done[/green] in {time.time() - t_start:.1f}s")
    return output


_render_options = [
    click.option("--preset", "-p", "preset_id", default=None, help="Preset id (see `list`)."),
    click.option("--layers", "layers_json", default=None,
                 help="JSON array of stacked layers (or @file); each renders into the next. "
                      "Per layer: preset, variant, sets, events, seed, intensity, texture, "
                      "enabled, picture, sound (picture/sound false mutes that whole chain). "
                      "Takes precedence over --preset."),
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


@main.command("still")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", required=True, help="PNG to write.")
@click.option("--scale", type=float, default=0.5)
@_with(_render_options)
def still_cmd(input_path, output, scale, **kw) -> None:
    """Render frame 0 of what `preview` would produce, and nothing else.

    Roughly a tenth of the cost of the clip, because it does one frame's worth
    of pixel work rather than ninety - but the *whole* clip's worth of setup, so
    the frame it produces is the one the clip opens on. Prints JSON with an
    `exact` flag: false means the chain has a real codec pass (or is a stack),
    where one frame cannot stand in for the clip and the picture will shift
    slightly once the clip lands.
    """
    from .engine.presets import get_preset
    from .engine.render import RenderOptions, render_still, render_still_layers

    stack = _parse_layers(kw.get("layers_json")) if kw.get("layers_json") else None
    if not stack and not kw.get("preset_id"):
        raise click.UsageError("give --preset, or --layers for a stack")
    video_over, audio_over = _split_overrides(kw.get("sets") or ())
    opts = RenderOptions(
        seed=kw.get("seed") if kw.get("seed") is not None else 1,
        intensity=kw.get("intensity", 1.0),
        texture=kw.get("texture", 1.0),
        variant=kw.get("variant"),
        video_overrides=video_over,
        audio_overrides=audio_over,
        t0=kw.get("start") or 0.0,
        duration=kw.get("duration"),
        scale=scale,
        crf=kw.get("crf", 17),
    )
    if stack:
        got = render_still_layers(input_path, output, stack, opts)
    else:
        got = render_still(input_path, output, get_preset(kw["preset_id"]), opts)
    click.echo(json.dumps({"output": got.path, "exact": got.exact}))


@main.command("events")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--scale", type=float, default=0.5)
@_with(_render_options)
def events_cmd(input_path, scale, **kw) -> None:
    """List the discrete damage a render would produce, as JSON.

    Dropouts, transport glitches and the like, each with the moment on the clip
    it lands at and what it is made of - without rendering anything. This is what
    a timeline draws from.
    """
    from .engine.presets import get_preset
    from .engine.render import Layer, RenderOptions, plan_events

    stack = _parse_layers(kw.get("layers_json")) if kw.get("layers_json") else None
    if not stack:
        if not kw.get("preset_id"):
            raise click.UsageError("give --preset, or --layers for a stack")
        video_over, audio_over = _split_overrides(kw.get("sets") or ())
        stack = [Layer(preset=get_preset(kw["preset_id"]), variant=kw.get("variant"),
                       video_overrides=video_over, audio_overrides=audio_over,
                       seed=kw.get("seed") if kw.get("seed") is not None else 1,
                       intensity=kw.get("intensity", 1.0), texture=kw.get("texture", 1.0))]
    opts = RenderOptions(
        seed=stack[0].seed, t0=kw.get("start") or 0.0,
        duration=kw.get("duration"), scale=scale,
    )
    click.echo(json.dumps(plan_events(input_path, stack, opts)))


@main.command("probe")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
def probe_cmd(input_path: str) -> None:
    """Probe a media file (JSON) - used by the GUI."""
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
                "has_video": info.has_video,
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
    """Extract an untreated segment (the 'before' side of A/B) - used by the GUI."""
    from .engine.media import probe as _probe
    from .engine.render import _even, _plain_video

    info = _probe(input_path)
    if not info.has_video:
        from .engine.media import encode_audio_only, read_audio, write_wav

        audio = read_audio(input_path, info.sr, min(info.channels, 2), start, duration)
        tmp = output + ".snip.wav"
        write_wav(tmp, audio, info.sr)
        encode_audio_only(tmp, output)
        os.unlink(tmp)
        click.echo(json.dumps({"output": output, "audio_only": True}))
        return
    w, h = _even(int(info.width * scale)), _even(int(info.height * scale))
    from .engine.media import source_matrix

    _plain_video(input_path, output, w, h, info.fps, start, duration, crf=17,
                 src_matrix=source_matrix(info))
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
