"""Obsolete noise dataset construction entry point.

Use the consolidated constructor instead:

    python -m pipeline.dataset_constructor.cli --input ... --output ...
"""


def main() -> None:
    raise RuntimeError(
        "pipeline/query_gen/qgen_test_noise.py is no longer a functional entry "
        "point. Use python -m pipeline.dataset_constructor.cli."
    )


if __name__ == "__main__":
    main()
