import re
from collections import Counter, defaultdict
from typing import TextIO

from categories import CATEGORIES_THAT_GO_AT_THE_TOP, clean_category


def replace_author_and_pr_url(input: str) -> str:
    output = re.sub(r"https://github.com/ArchipelagoMW/Archipelago/pull/([0-9]+)", r"#\1", input)
    output = re.sub(r"by @([^\s]+) in #([0-9]+)", r"[@\1] #\2", output)
    return output


def clean_line(line: str) -> str:
    assert line.startswith("* ")

    line_after_star = line[2:]
    title_pattern = r"((?: *[{0-9a-z'.:()&/\-}])+)"
    # Try alternate formattings like "Game - " or "[Game]" first. Only do if it is deemed necessary.
    title_formats = [
        fr"^(?:fix|feat|chore|docs|test) *\({title_pattern}\)\s*:",  # e.g. "feat(Game): PR Title"
        fr"^\[{title_pattern}]",  # e.g. "[Game] PR Title"
        fr"^{title_pattern}\s-\s",  # e.g. "Game - PR Title"
        fr"^{title_pattern}\s*:",  # e.g. "Game: PR Title"
    ]

    for test in title_formats:
        replaced = re.sub(test, r"\1SPLITHERE", line_after_star, flags=re.IGNORECASE)
        if "SPLITHERE" in replaced and replaced.index("SPLITHERE") <= 30:
            line_after_star = replaced
            break

    line_after_star = replace_author_and_pr_url(line_after_star)

    return line_after_star


def split_category_and_line(line: str) -> tuple[str | None, str]:
    if "SPLITHERE" not in line or line.index("SPLITHERE") > 30:
        return "Unknown", line

    category, line = line.split("SPLITHERE", 1)

    return category, line.lstrip()


def write_category_lines(category: str, lines: list[str]) -> None:
    outfile.write(f"### {category}\n")
    for line in lines:
        outfile.write(f"* {line}\n")
    outfile.write("\n")


def reorder_file(infile: TextIO, outfile: TextIO):
    lines_per_category = defaultdict(list)
    capitalisations_per_category = defaultdict(Counter)

    for line in infile:
        if line.startswith("## What's Changed"):
            break

    # Group lines into games/categories

    next_line = ""
    for line in infile:
        if line.startswith("##"):
            next_line = line
            break

        line = line.strip()

        if not line:
            continue

        line = clean_line(line)

        category, line = split_category_and_line(line)

        line = line[0].upper() + line[1:]

        category = clean_category(category)

        category_lower = category.lower()

        capitalisations_per_category[category_lower][category] += 1

        lines_per_category[category_lower].append(line)

    most_common_capitalisation_per_category = {
        category: max(capitalisations_counter.items(), key=lambda pair: pair[1])[0]
        for category, capitalisations_counter in capitalisations_per_category.items()
    }

    # Write the grouped lines by category, starting with known core categories

    if CATEGORIES_THAT_GO_AT_THE_TOP:
        outfile.write("## Archipelago\n\n")

        for start_category in CATEGORIES_THAT_GO_AT_THE_TOP:
            if start_category not in lines_per_category:
                continue

            write_category_lines(
                most_common_capitalisation_per_category[start_category], lines_per_category[start_category]
            )

            del lines_per_category[start_category]

    if lines_per_category:
        outfile.write("## Game Updates\n\n")

        for category in sorted(lines_per_category):
            lines = lines_per_category[category]
            write_category_lines(most_common_capitalisation_per_category[category], lines)

    # Leave end unchanged

    next_line = next_line.replace("made their first contribution in ", "")

    outfile.write(next_line)

    for line in infile:
        outfile.write(replace_author_and_pr_url(line))


with open("output.txt", "w") as outfile:
    with open("input.txt") as infile:
        reorder_file(infile, outfile)
