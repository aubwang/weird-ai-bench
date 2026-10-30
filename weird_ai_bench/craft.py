"""Optional qualitative craft guidance shared by writers and judges.

These notes describe source-song devices, never proposed jokes or new topics.
They do not participate in any automated gate.
"""

PARODY_CRAFT = (
    "Reward lyrics that a listener who knows the original would recognize as a parody of it "
    "from the words, not just the tune. Recognition comes from preserving enough of the "
    "source's distinctive structure while changing what it says: the hook's position and "
    "shape, rhetorical turns, line openings, and rhyme or sound patterns. The listed devices "
    "are opportunities, not a checklist: any individual device may be dropped or replaced "
    "as long as other features still carry the recognition. No exact phrase is required. "
    "Even a small substitution can earn craft credit when it preserves the source's logic "
    "or sound while making a specific new point. Funny lyrics with little recognizable "
    "connection to the source earn little parody-craft credit, even if they fit the same "
    "melody. Unchanged source lines and superficial word swaps that do not change the point "
    "earn no craft credit."
)
COHERENCE = (
    "Reward a clear, consistent comic argument or theme and parts that fit together. "
    "A continuous story is one option, not a requirement."
)


def describe_craft(spec) -> str:
    if not spec.uses_craft_guidance:
        return ""
    lines = ["Soft parody-craft guidance (qualitative, not additional hard rules):"]
    for key in spec.generation_order:
        sec = spec.sections[key]
        if sec.craft_notes:
            lines.append(f"{sec.label}:")
            lines.extend(f"- {note.strip()}" for note in sec.craft_notes)
    lines.append("These source-song devices are optional starting points for new material. "
                 "Individual devices may change, but the section should remain recognizable "
                 "as a transformation of the source. "
                 "No exact phrase, joke, or new internal-rhyme gate is required by these notes. "
                 "The separately listed hard constraints still apply.")
    return "\n".join(lines)
