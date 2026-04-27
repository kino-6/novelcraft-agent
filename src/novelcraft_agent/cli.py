from __future__ import annotations

import argparse
from pathlib import Path

from .io import resolve_output_dir, save_outputs, timestamp_utc
from .ollama_client import OllamaClient
from .pipeline import PipelineConfig, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Continue a novel text file with Ollama.")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--model", default="llama3.1")
    parser.add_argument("--analyzer-model")
    parser.add_argument("--director-model")
    parser.add_argument("--writer-model")
    parser.add_argument("--polish-model")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--tail-chars", type=int, default=4000)
    parser.add_argument("--out-dir")
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--no-polish", action="store_true")
    parser.add_argument("--show-thinking", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--preview-chars", type=int, default=600)
    return parser


def _phase_printer(verbose: bool):
    def inner(msg: str) -> None:
        print(f"\n== {msg} ==")
        if verbose:
            print("processing...")

    return inner


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path: Path = args.input_path
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    source = input_path.read_text(encoding="utf-8")
    output_dir = resolve_output_dir(input_path, args.out_dir)

    config = PipelineConfig(
        model=args.model,
        analyzer_model=args.analyzer_model,
        director_model=args.director_model,
        writer_model=args.writer_model,
        polish_model=args.polish_model,
        iterations=args.iterations,
        tail_chars=args.tail_chars,
        no_polish=args.no_polish,
        show_thinking=args.show_thinking,
    )

    client = OllamaClient()
    stream = lambda chunk: print(chunk, end="", flush=True)
    think = (lambda chunk: print(chunk, end="", flush=True)) if args.show_thinking else None
    result = run_pipeline(
        input_text=source,
        skills_dir=Path(args.skills_dir),
        config=config,
        client=client,
        on_stream=stream,
        on_phase=_phase_printer(args.verbose),
        on_thinking=think,
    )

    stamp = timestamp_utc()
    paths = save_outputs(
        input_path=input_path,
        output_dir=output_dir,
        stamp=stamp,
        final_continuation=result.continuation,
        original_text=source,
        state_history=result.state_history,
        artifacts=result.artifacts,
        verbose=args.verbose,
    )

    print("\n\n== Saved ==")
    for key, path in paths.items():
        print(f"{key}: {path}")

    preview = result.continuation[: args.preview_chars]
    print("\n== Preview ==")
    print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
