# Writing style — external voice

How the README, the LinkedIn post, and anything else public should read. The goal is one thing:
sound like a sharp human who built this, not like a model that described it.

## The voice in one line

Write the way you would explain it to a smart colleague who is short on time: confident, specific,
and getting to the point without throat-clearing.

## The five rules that do the work

1. **Open on a moment, not a definition.** Put a real person in a real bind in the first two
   sentences (the pharmacist whose backup order also bounces). The reader should feel the problem
   before they meet the tool.

2. **Connect every sentence to the next (old-to-new flow).** End a sentence on the new idea, then
   open the next sentence with that same idea. This is the single fix for prose that feels choppy or
   AI-generated. Fragments that each restart cold are the tell; a thread that pulls forward is the cure.

3. **Vary the rhythm: short, short, long.** Short sentences land. The long one carries the reader.
   Uniform sentence length is what makes writing feel machine-made, so break the pattern on purpose.

4. **Show, don't tell, and let them verify.** Replace "supports shortage checking" with a real input
   and its real output, then invite the reader to run it on their own drug. The result is the proof.
   An adjective is not.

5. **Get a technical reader to something runnable fast.** Hook, then a prompt they can paste, then
   Quickstart. A GitHub visitor who came for the code should reach it within a screen.

## Speak the audience's language

This audience is informatics pharmacists and engineers. Use RxCUI, ATC-4, openFDA, MCP, stdio, and
read-only without defining them. Respecting what they already know is part of sounding human to them.

## Cut these (the AI tells)

- The "it's not just X, it's Y" construction.
- Hedging: "it's worth noting," "arguably," "very," "somewhat."
- Over-bolding. Bold a few load-bearing phrases, not every other line.
- Tidy three-item lists used for rhythm rather than meaning.
- "In today's fast-paced world" openers and generic adjectives.
- Walls of bullets where connected reasoning belongs in prose. Bullets are for steps, facts, and
  lookups; prose is for an argument that builds.

## Em-dashes

Keep them, ration them. They read as human when used a few times for a genuine break in thought, and
as a machine tic when they appear in every paragraph. If in doubt, a period or a comma is fine.

## A quick before/after

- Choppy: "The model was wrong. The data was stale. We missed it. It cost a week."
- Fluid: "The model was wrong because the data was stale, and nobody owned the freshness check, so we
  missed it and lost a week."

## Sources behind these rules

Old-to-new flow and stress position (Yale Poorvu Center, Duke Scientific Writing). Sentence-rhythm
variation (Gary Provost). Specificity and cutting qualifiers (Strunk & White; Paul Graham, "Write
Like You Talk"). Prose over bullets for reasoning (the Amazon narrative-memo doctrine). AI tells
(Wikipedia, "Signs of AI writing"). README craft drawn from widely praised examples (HTTPie,
re-frame, dbt-core via the awesome-readme list).
