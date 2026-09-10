# Teaching alignment example

[Three-slide English review draft](teaching-example-v1.pptx).

The sequence shows a stored teaching profile, first-turn output, and follow-up
failure in the same synthetic two-turn case. These slides prototype the
setting-to-output explanation for the brief-aligned presentation; they are not
the complete deck and do not fix final page numbering.

Sora is the synthetic scoring system named in the source, not an OpenAI model.
The example includes all source material needed to understand the calculation.
Both response configurations are experimental. V4 is the comparison control,
not the retained deterministic release. The V19 candidate is not promoted.
One case illustrates a behavior; it does not establish general quality or
reproduction of an actual professor's teaching style.

[evidence.json](evidence.json) preserves exact source text, profile values,
student messages and delivered responses, with original JSONL paths and hashes.
No new model calls or app changes were made. No root cause beyond the recorded
validation failure is asserted for the withheld second response.

The exported PPTX passed package, geometry and import validation. All three slides
were rendered from that file and visually reviewed. Text and the profile table
are editable. Source notes are included; a final read-aloud script and native
PowerPoint playback check remain outside this draft.

Previews: [settings](slide-1.png), [first response](slide-2.png),
[follow-up](slide-3.png).

Superseded sample scope: the user now requires IT5004 lecture material for all
presentation examples. This draft remains historical and is not ready for
main-deck integration. Replace its unrelated course/sample before integration.
