import type { PaperSummary } from "../types";

type PaperPickerProps = {
  papers: PaperSummary[];
  selectedPaperId: string;
  onChange: (paperId: string) => void;
  disabled?: boolean;
};

export function PaperPicker({
  papers,
  selectedPaperId,
  onChange,
  disabled = false,
}: PaperPickerProps) {
  return (
    <section className="panel">
      <label className="field">
        <span className="field-label">Select paper</span>
        <select
          value={selectedPaperId}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled || papers.length === 0}
        >
          <option value="">Choose a paper</option>
          {papers.map((paper) => (
            <option key={paper.paper_id} value={paper.paper_id}>
              CAT {paper.year} Slot {paper.slot}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}
