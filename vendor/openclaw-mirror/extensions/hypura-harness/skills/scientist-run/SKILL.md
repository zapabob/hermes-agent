---
name: scientist-run
description: Launch SakanaAI's AI-Scientist for autonomous scientific research. Generates ideas, executes experiments, and writes papers based on a specified template and model.
---

# AI-Scientist Run Skill

Automate the entire scientific discovery process using SakanaAI's AI-Scientist framework.

## When to Use

- You want to conduct a new scientific study or experiment.
- You have a research template in `vendor/AI-Scientist/templates/`.
- You want to generate a full scientific paper from a core idea.

## Workflow

1. List available templates

```bash
ls ../vendor/AI-Scientist/templates
```

2. Run the scientist loop

```bash
python ../vendor/AI-Scientist/launch_scientist.py \
  --model "gpt-4o" \
  --experiment "nanoGPT" \
  --num-ideas 2 \
  --write-up
```

3. Review the generated papers in the results directory.

## Parameters

- `--model`: The LLM to use for idea generation and write-up.
- `--experiment`: The name of the experiment template to follow.
- `--num-ideas`: Number of ideas to generate and test.
- `--write-up`: Whether to generate the final LaTeX paper.
