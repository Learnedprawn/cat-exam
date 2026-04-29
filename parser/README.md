# CAT PDF Parser

Offline parser for converting CAT exam PDFs into JSON files that the exam app can read from `backend/data/papers/`.

## What It Does

The parser reads a text-based CAT PDF, extracts question text, optionally extracts answers from the same PDF or a separate answer-key file, and writes a normalized JSON paper file.

Output path by default:

```text
backend/data/papers/{paper_id}.json
```

## Current Pipeline

The parser is split into two passes:

1. Question pass
   - Extract text from the main PDF using PyMuPDF
   - Remove repeated headers and footers
   - Normalize whitespace
   - Split content into question-safe chunks
   - Parse questions with `gpt-4.1-mini` using structured output

2. Answer pass
   - Look for an answer-key section in the same PDF
   - Or read a separate answer-key PDF/text file if `--answers` is provided
   - Split answer text into answer chunks
   - Parse answers with `gpt-4.1-mini` using structured output
   - Merge answers back onto questions by `question_number`

3. Finalization
   - Deduplicate repeated questions using normalized `question_text`
   - Generate stable `question_id` values from hashed normalized text
   - Sort by `question_number`
   - Save final JSON

## Folder Layout

```text
parser/
  main.py
  extract.py
  cleaner.py
  chunker.py
  llm_parser.py
  schema.py
  requirements.txt
  output/
```

## Requirements

- Python 3.11+
- OpenAI API key available as `OPENAI_API_KEY`
- Text-based PDFs only for this MVP

Install parser dependencies:

```bash
cd parser
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## How To Run

From the repo root:

```bash
cd parser
.venv/bin/python main.py --input ../pdfs/2024_slot1.pdf
```

If the answer key is in a separate file:

```bash
.venv/bin/python main.py \
  --input ../pdfs/2024_slot1_questions.pdf \
  --answers ../pdfs/2024_slot1_answers.pdf
```

If the filename does not clearly contain year and slot, provide them explicitly:

```bash
.venv/bin/python main.py \
  --input ../pdfs/mock_paper.pdf \
  --paper-id 2024_slot_1 \
  --year 2024 \
  --slot 1
```

If you want to override the output location:

```bash
.venv/bin/python main.py \
  --input ../pdfs/2024_slot1.pdf \
  --output ../backend/data/papers/custom_name.json
```

## CLI Arguments

- `--input`: required, path to the main question PDF
- `--answers`: optional, separate answer-key PDF or `.txt` file
- `--paper-id`: optional override for the output `paper_id`
- `--year`: optional override for the paper year
- `--slot`: optional override for the CAT slot
- `--output`: optional explicit output path

## How Metadata Is Inferred

By default, the parser tries to extract year and slot from the input filename.

Supported examples:

- `2024_slot1.pdf`
- `2024_slot_1.pdf`
- `cat_2024_slot_1.pdf`

If inference fails, the parser stops and asks you to supply `--year` and `--slot`.

## Output Format

The parser writes JSON in the app paper format:

```json
{
  "paper_id": "2024_slot_1",
  "year": 2024,
  "slot": 1,
  "sets": [
    {
      "set_id": "set_1_abc123def456",
      "section": "VARC",
      "shared_context": "Shared passage or caselet text",
      "image_link": null,
      "questions": [
        {
          "question_id": "q_1_abc123def456",
          "question_number": 1,
          "section": "VARC",
          "question_type": "mcq",
          "question_text": "string",
          "options": [
            { "option_id": "A", "option_text": "..." }
          ],
          "correct_answer": "B"
        }
      ],
    },
    {
      "section": "QA",
      "shared_context": null,
      "image_link": null,
      "questions": [
        {
          "question_id": "q_2_abc123def456",
          "question_number": 2,
          "section": "QA",
          "question_type": "tita",
          "question_text": "string",
          "correct_answer": null
        }
      ]
    }
  ]
}
```

Notes:

- `set_id` is generated locally from the first question number plus the shared context hash
- `question_id` is generated locally from the normalized question text
- `shared_context` is populated when multiple questions share a passage or caselet
- `image_link` is always saved as `null`; add DILR images manually later if needed
- `options` are present only for `mcq`
- `correct_answer` may be `null` if no reliable answer was parsed

## Step-By-Step Behavior

### 1. Extract text

`extract.py` reads all PDF pages using PyMuPDF. If no text is extracted, the run aborts.

### 2. Clean text

`cleaner.py` removes repeated page headers and footers and normalizes whitespace while preserving section markers and question numbering.

### 3. Split question and answer regions

`chunker.py` looks for an embedded answer-key section such as `Answer Key` or `Answers`.

- Text before that marker is treated as the question region
- Text after that marker is treated as the answer region

If `--answers` is provided, that separate file is used as the answer source instead.

### 4. Chunk questions

Question text is grouped by detected question boundaries.

The chunker tries to:

- preserve question numbering
- keep section context
- avoid splitting mid-question
- keep shared passage/set context attached to the following questions

### 5. Parse questions with the LLM

`llm_parser.py` sends each question chunk to `gpt-4.1-mini` using structured output.

Rules enforced in the prompt:

- do not guess missing content
- skip incomplete questions
- infer `VARC`, `DILR`, or `QA` from local context
- classify `mcq` vs `tita`
- do not produce answers during the question pass

### 6. Parse answers with the LLM

Answer chunks are parsed separately into `{question_number, answer}` records.

The parser then merges answers onto questions by `question_number`.

### 7. Validate and save

Before saving, the parser:

- normalizes whitespace and casing
- deduplicates by normalized `question_text`
- sorts by `question_number`
- groups questions into `sets` using shared context
- writes the final JSON file

## Error Handling

### Empty extraction

If the PDF produces no text, the parser aborts.

### Chunk parse failure

If a chunk fails structured parsing:

1. it retries once
2. if the retry fails, the chunk is skipped
3. the failure is logged to:

```text
parser/output/parse_errors.jsonl
```

### Missing answer key

Questions are still kept if answers cannot be parsed.

In that case:

- `correct_answer` becomes `null`
- the exam app treats those questions as ungraded

## Supported Inputs

Currently supported:

- `.pdf`
- `.txt` for answer keys or extracted text

Not supported in MVP:

- scanned PDFs that require OCR
- image-only PDFs
- complex answer keys that do not map cleanly by question number

## Troubleshooting

### `Unable to infer year/slot from filename`

Use:

```bash
--paper-id 2024_slot_1 --year 2024 --slot 1
```

### `PDF extraction produced no text`

The PDF is likely scanned or image-based. This parser currently supports only text-based PDFs.

### `OpenAI SDK is required for LLM parsing`

Install dependencies from `parser/requirements.txt`.

### `Model returned no structured output`

Check:

- your `OPENAI_API_KEY`
- network access
- whether the chunk text is malformed or too noisy

Then inspect:

```text
parser/output/parse_errors.jsonl
```

## Recommended Workflow

1. Start with one known text-based CAT PDF
2. Run the parser without `--answers`
3. Inspect the generated JSON for question quality
4. If answers are missing, rerun with a separate answer-key file
5. Load the JSON through the app and verify paper behavior

## Related Files

- [main.py](/home/learnedprawn/Work/Ideas/cat-exam/parser/main.py)
- [schema.py](/home/learnedprawn/Work/Ideas/cat-exam/parser/schema.py)
- [llm_parser.py](/home/learnedprawn/Work/Ideas/cat-exam/parser/llm_parser.py)
- [backend/app/models.py](/home/learnedprawn/Work/Ideas/cat-exam/backend/app/models.py)
