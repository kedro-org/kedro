def parse_add_ons_input(add_ons_str):
    """Parse the add-ons input string.

    Args:
        add_ons_str: Input string from prompts.yml.

    Returns:
        list: List of selected add-ons as strings.
    """
    if add_ons_str == "all":
        return ["1", "2", "3", "4", "5"]
    if add_ons_str == "none":
        return []

    # Split by comma
    add_ons_choices = add_ons_str.split(",")
    selected = []

    for choice in add_ons_choices:
        if "-" in choice:
            start, end = choice.split("-")
            selected.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            selected.append(choice.strip())

    return selected
