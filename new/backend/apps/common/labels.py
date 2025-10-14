from typing import Tuple


def parse_question_label(label: str) -> Tuple[int, str]:
    label = (label or "").strip()
    if not label:
        raise ValueError("Empty label")
    # Split leading digits and trailing letters e.g., '12b' -> 12, 'b'
    i = 0
    while i < len(label) and label[i].isdigit():
        i += 1
    if i == 0:
        raise ValueError("Label must start with a number, e.g., '1a'")
    order_index = int(label[:i])
    part_label = label[i:].lower() if i < len(label) else ""
    return order_index, part_label


def format_question_label(order_index: int, part_label: str) -> str:
    return f"{order_index}{(part_label or '').lower()}"



