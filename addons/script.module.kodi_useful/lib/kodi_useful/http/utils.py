from email.message import Message
import typing as t


__all__ = (
    'get_content_disposition',
    'split_pairs',
)


def get_content_disposition(header_value: str) -> t.Optional[str]:
    msg = Message()
    msg['Content-Disposition'] = header_value
    return msg.get_param('filename', header='Content-Disposition')


def split_pairs(s: str, step: int = 2, max_split: int = 3) -> t.Sequence[str]:
    """
    Splits the string into parts of the specified length.

    Arguments:
        s (str):
        step (int): Cutting step. Default to ``2``.
        max_split (int): Maximum number of splits to do. Default to ``3``.
    """
    length = len(s)
    end = step * (max_split - 1) if max_split else length
    pairs = []

    for start in range(0, end, step):
        if start < length:
            pairs.append(s[start:start + step])

    if end < length:
        pairs.append(s[end:])

    return pairs
