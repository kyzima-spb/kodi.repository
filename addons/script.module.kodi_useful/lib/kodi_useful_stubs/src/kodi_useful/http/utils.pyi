import typing as t

__all__ = ['get_content_disposition', 'split_pairs']

def get_content_disposition(header_value: str) -> str | None: ...
def split_pairs(s: str, step: int = 2, max_split: int = 3) -> t.Sequence[str]:
    """
    Splits the string into parts of the specified length.

    Arguments:
        s (str):
        step (int): Cutting step. Default to ``2``.
        max_split (int): Maximum number of splits to do. Default to ``3``.
    """
