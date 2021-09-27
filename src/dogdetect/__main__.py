"""Command-line interface."""
import subprocess
from datetime import datetime
from typing import List

import click
import ffmpeg
from pydub import AudioSegment

sampling_rate = 16000
seconds = 4

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def export(prev, current, kek=None):
    to_export = prev + current
    if kek:
        to_export += kek
    to_export.export(f"noise-{datetime.now()}.wav", format="wav")


@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.argument("path", type=str, required=True)
def main(path: str) -> None:
    """Detect noise in sound file or stream.

    PATH to file or URL.
    """
    averages = []
    prev = None
    current = None
    noise = False
    cmd: List = (
        ffmpeg.input(path)
        .output("pipe:", format="wav", acodec="pcm_s16le", ac=1, ar=sampling_rate)
        .compile()
    )
    cmd.insert(1, "-vn")
    if "rtsp" in path:
        cmd.insert(1, "-re")
        cmd.insert(1, "-rtsp_transport")  # Add this
        cmd.insert(2, "tcp")  # Add this

    out = subprocess.Popen(cmd, stdin=None, stdout=subprocess.PIPE, stderr=None)
    while True:
        in_bytes = out.stdout.read(sampling_rate * seconds * 2)
        if not in_bytes:
            if noise:
                export(prev, current)
            break
        metadata = {
            "frame_rate": sampling_rate,
            "channels": 1,
            "sample_width": 2,
            "frame_width": 2 * 1,
        }
        kek = AudioSegment(data=in_bytes, metadata=metadata)

        if noise:
            export(prev, current, kek)
            current = None
            noise = False

        prev = current
        ma = []
        avg = 0
        for ms, s in enumerate(kek):
            ma.append(s.dBFS)
            if len(ma) > 20:
                ma.pop(0)
            avg = sum(ma) / len(ma)
            averages.append(avg)
            if s.dBFS - 20 > avg and avg != float("-inf"):
                # print(f"{ms}: NOISE!")
                noise = True
                print(f"{ms}: {s.dBFS} {s.dBFS - 20} => avg: {avg}")
        current = kek


if __name__ == "__main__":
    main()  # pragma: no cover
