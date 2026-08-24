# awrena

Run one judged head-to-head between two agents and read the scored verdict.

```bash
pip install awrena
```

```python
from awrena import Judge

judge = Judge()
verdict = judge.judge(
    a_response="Agent A's output",
    b_response="Agent B's output",
    question="What was the question?"
)

if verdict.is_valid():
    print(f"Winner: {verdict.winner}")
    print(f"Scores: {verdict.a_score:.1f} vs {verdict.b_score:.1f}")
    print(f"Reason: {verdict.reason}")
```

```bash
# Prepare a JSON file with agent responses
cat > responses.json << 'EOF'
{
  "question": "What is the capital of France?",
  "a_response": "Paris",
  "b_response": "The capital of France is Paris, the largest city in the country and home to the Louvre, Notre-Dame Cathedral, and many other historical landmarks."
}
EOF

# Judge the responses
awrena judge responses.json
# Output: B wins (28.6 vs 71.4): length: B is longer (20 vs 1 words)

# Get JSON output for programmatic use
awrena judge responses.json --format json
```

## The brick

A judge compares two agent outputs and assigns scores. Every judgment path succeeds
with a clear verdict — empty responses are handled, errors don't raise, and the
scoring is deterministic and explainable.

### Scoring criteria

Choose how to judge responses:

| criteria | measures |
|---|---|
| `--criteria default` | response length (default) |
| `--criteria length` | raw character count |
| `--criteria content` | word count, ignoring whitespace |

Extend with custom criteria:

```python
from awrena import Criteria

class ExactnessCriterion(Criteria):
    def _evaluate(self, a_response, b_response):
        # Return (a_score, b_score, reason)
        # Scores are 0-100; reason explains the judgment
        return 75.0, 60.0, "A is more precise"

judge = Judge([ExactnessCriterion("exactness")])
verdict = judge.judge(a, b)
```

### Always returns a verdict

A judge that breaks silently is worse than one that names its failure. Every path
returns a complete `Verdict`:

```python
verdict = judge.judge(a, b)

if verdict.is_valid():
    print(verdict.summary())  # "A wins (80.0 vs 20.0): ..."
else:
    print(f"Error: {verdict.error}")  # "Error: judge error: ..."
```

Empty responses, exceptions during scoring, missing criteria — all return clear,
complete verdicts with explanations.

### Verdict structure

```python
@dataclass
class Verdict:
    winner: str              # "a", "b", or "tie"
    a_score: float          # 0-100
    b_score: float          # 0-100
    reason: str             # explanation of the judgment
    error: Optional[str]    # None if judgment succeeded
```

## Tests

All paths tested in both directions: a suite that only checks wins passes on a
judge that always selects A, and one that only checks for ties passes on a judge
that always ties. The test suite includes:

- Happy path: both agents respond, verdict is computed
- Error paths: empty responses, malformed criteria, exceptions
- Boundary cases: identical responses, extreme length differences
- A test that fails if the judge were replaced by one that always ties

```bash
pip install -e ".[dev]" && pytest
```

## Where it sits

| package | question |
|---|---|
| `awrena` | **which agent performed better?** |

Run a head-to-head comparison, get a scored, reasoned verdict. Extend the scoring
logic with your own criteria. Integrate with agent orchestration to select winners.

Apache-2.0.

## The aw family

Standalone tools that share one idea: **replace something you would otherwise have to
_trust_ with something you can _check_.**

Each installs on its own, works offline, and needs no account.

See [awkno](https://github.com/Aitherium/awkno) for the full Aither World ecosystem.
