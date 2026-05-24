"""Obsolete unstructured evidence dataset entry point.

Use the consolidated constructor instead:

    python -m pipeline.dataset_constructor.cli --kind unstructured --input ... --output ...
"""


def main() -> None:
    raise RuntimeError(
        "pipeline/query_module/unstructured_exe.py is no longer a functional "
        "entry point. Use python -m pipeline.dataset_constructor.cli --kind "
        "unstructured."
    )


if __name__ == "__main__":
    main()
