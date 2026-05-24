"""Obsolete noise execution entry point.

Noise graph execution is now part of pipeline.dataset_constructor.
"""


def main() -> None:
    raise RuntimeError(
        "pipeline/query_module/noise_exe.py is no longer a functional entry "
        "point. Use python -m pipeline.dataset_constructor.cli."
    )


if __name__ == "__main__":
    main()
