import matchering as mg
import logging

logging.getLogger("matchering").setLevel(logging.WARNING)

def apply_automaster(
    target_path: str,
    reference_path: str,
    output_path: str,
) -> None:
    """
    Applies auto-master to target matching the spectrum and loudness of reference.
    Writes result to output_path as 24-bit WAV.
    """
    mg.process(
        target=target_path,
        reference=reference_path,
        results=[mg.pcm24(output_path)],
    )
