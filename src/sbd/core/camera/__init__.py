"""Lazy camera HAL factory."""

from sbd.core.camera.base import Camera


def make_camera(config) -> Camera:
    if config.driver == "null":
        from sbd.core.camera.null.driver import NullCamera
        return NullCamera(config)
    if config.driver == "mock":
        from sbd.core.camera.mock.driver import MockCamera
        return MockCamera(config)
    if config.driver == "picamera2":
        from sbd.core.camera.picamera2.driver import PiCamera
        return PiCamera(config)
    raise ValueError(f"unknown camera driver: {config.driver}")


__all__ = ["Camera", "make_camera"]
