"""Lazy audio HAL factories."""

from sbd.core.audio.base import AudioInput, AudioOutput


def make_audio_input(config) -> AudioInput:
    if config.driver == "null":
        from sbd.core.audio.null.input import NullAudioInput
        return NullAudioInput(config)
    if config.driver == "mock":
        from sbd.core.audio.mock.input import MockAudioInput
        return MockAudioInput(config)
    if config.driver == "alsa":
        from sbd.core.audio.alsa.input import AlsaAudioInput
        return AlsaAudioInput(config)
    raise ValueError(f"unknown audio driver: {config.driver}")


def make_audio_output(config) -> AudioOutput:
    if config.driver == "null":
        from sbd.core.audio.null.output import NullAudioOutput
        return NullAudioOutput()
    if config.driver == "mock":
        from sbd.core.audio.mock.output import MockAudioOutput
        return MockAudioOutput()
    if config.driver == "alsa":
        from sbd.core.audio.alsa.output import AlsaAudioOutput
        return AlsaAudioOutput(config)
    raise ValueError(f"unknown audio driver: {config.driver}")


__all__ = ["AudioInput", "AudioOutput", "make_audio_input", "make_audio_output"]
