import matchering as mg
import logging

logging.getLogger("matchering").setLevel(logging.WARNING)

def apply_automaster(
    target_path: str,
    reference_path: str,
    output_path: str,
) -> None:
    """
    Aplica auto-masterización al target igualando el espectro y loudness de la referencia.

    Usa matchering, que analiza la referencia en bandas de frecuencia y aplica filtros
    y compresión multibanda al target para aproximar su perfil espectral y dinámico.
    matchering solo trabaja con archivos en disco (no acepta arrays en memoria),
    por eso Step3Master escribe temporales antes de llamar esta función.

    El resultado se guarda como WAV 24-bit en output_path.

    Args:
        target_path: Ruta al WAV del track a masterizar (normalmente un temporal
                     generado desde processed_audio).
        reference_path: Ruta al track de referencia. Puede ser cualquier formato
                        soportado por matchering (WAV, MP3, FLAC, etc.).
        output_path: Ruta donde se escribe el WAV masterizado. Se sobreescribe si existe.
    """
    mg.process(
        target=target_path,
        reference=reference_path,
        results=[mg.pcm24(output_path)],
    )
