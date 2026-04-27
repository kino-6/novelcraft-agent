# novelcraft-agent

Local CLI tool that continues an existing novel text file with a structured multi-step agent pipeline powered by Ollama:

Analyzer → Director → Skill Selection → Writer → Light Polish.

## Requirements

- Python 3.11+
- Ollama running locally at `http://127.0.0.1:11434`

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e . pytest
```

## Pull an Ollama model (example)

```bash
ollama pull llama3.1
```

## CLI usage

```bash
python -m novelcraft_agent path/to/novel.txt --iterations 3
```

### Options

- `--model`
- `--analyzer-model`
- `--director-model`
- `--writer-model`
- `--polish-model`
- `--iterations`
- `--tail-chars`
- `--out-dir`
- `--skills-dir`
- `--no-polish`
- `--show-thinking`
- `--mock` (run without Ollama; deterministic test output)
- `--verbose`
- `--preview-chars`

### Example

```bash
python -m novelcraft_agent novel_25463845/novel_25463845.txt \
  --model llama3.1 \
  --iterations 3 \
  --tail-chars 5000 \
  --preview-chars 800
```

### Mock example (no Ollama needed)

```bash
python -m novelcraft_agent examples/sample_novel.txt --iterations 1 --mock --verbose
```

## Output files

Given input file `novel_25463845/novel_25463845.txt`, by default files are saved in:

`novel_25463845/output/`

Generated files:

- `<stem>_final_<timestamp>.txt` (continuation only)
- `<stem>_with_continuation_<timestamp>.txt` (original + continuation)
- `<stem>_state_history_<timestamp>.json` (analysis/direction by iteration)
- Per-iteration artifacts:
  - `<stem>_<timestamp>_part_001_analysis.json`
  - `<stem>_<timestamp>_part_001_direction.json`
  - `<stem>_<timestamp>_part_001_writer_part.txt`
  - `<stem>_<timestamp>_part_001_polished_part.txt`
  - `<stem>_<timestamp>_part_001_final_part.txt`

## Skills

Default skills are shipped in `skills/`:

- `tension_raise.md`
- `dialogue_drive.md`
- `character_conflict.md`
- `foreshadowing_insert.md`
- `quiet_scene_shift.md`
- `information_reveal.md`

### Skill authoring guide

Create a markdown file in your skills directory using this structure:

```markdown
# skill_name
## Purpose
...
## When to use
...
## Writing rules
...
## Avoid
...
```

The director can only choose from loaded skill names.

## Troubleshooting

### Models output “thinking” content

The runtime captures both `thinking` and `response` fields from Ollama stream chunks.
Only `response` is used as novel output. Thinking is shown only when `--show-thinking` is enabled.

### No skills found

Pass `--skills-dir` and ensure it contains `*.md` files with `# <name>` heading.

### Output contains artifacts (code fences/headings)

The cleaner removes `<think>...</think>`, `Thinking...done thinking.`, ANSI escapes, markdown fences, and labels such as `本文:`.

## Tests

```bash
uv run pytest
```

## Runtime dependencies

The runtime uses only Python standard library modules. Packaging/build tooling (`setuptools`, `wheel`) and test tooling (`pytest`) are development-time only.
