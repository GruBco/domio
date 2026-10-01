from datetime import timedelta
from typing import List


def tabulate(column_widths: List[int],
             headers_list: List[str],
             tabular_data: List[List[str]],
             separator: str = "|",
             center_header: bool = True) -> str:
    rows_list = [
        centered_header_str(headers_list, column_widths, separator)
        if center_header
        else left_justified_header_str(headers_list, column_widths, separator)
    ]
    row_len = sum(column_widths) + len(column_widths)

    rows_list.append('-' * row_len)

    for row in tabular_data:
        row_str = rows_left_justified_str(row, column_widths, separator)
        rows_list.append(row_str)

    return '\n' + '\n'.join(rows_list) + '\n'


def left_justified_header_str(headers: List[str],
                              column_widths: List[int],
                              separator: str) -> str:
    titles_justified = [
        value.ljust(column_widths[i]) for i, value in enumerate(headers)
    ]

    return separator.join(titles_justified)


def centered_header_str(headers: List[str],
                        column_widths: List[int],
                        separator: str) -> str:
    titles_centered = []
    for i, value in enumerate(headers):
        column_width = column_widths[i]
        title_centered = value.center(column_width)
        titles_centered.append(title_centered)

    return separator.join(titles_centered)


def rows_left_justified_str(row_data: List[str],
                            column_widths: List[int],
                            separator: str = "|") -> str:
    row_data_left_justified = []
    for i, value in enumerate(row_data):
        column_width = column_widths[i]
        value_left_justified = value.ljust(column_width)
        row_data_left_justified.append(value_left_justified)
    return separator.join(row_data_left_justified)


def humanize_timedelta(td_object: timedelta) -> str:
    seconds = int(td_object)
    sec = seconds % 60
    days = int(seconds / 60 / 60 / 24)
    hours = int(seconds / 60 / 60 % 24)
    minutes = int(seconds / 60 % 60)

    return "{} days, {:02}:{:02}:{:02}".format(days, hours, minutes, sec)