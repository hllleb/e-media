"""FFTAnalyzer – 2-D Fourier spectrum of a PNG image."""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from .png_file import PNGFile


class FFTAnalyzer:
    """
    Computes and visualises the 2-D discrete Fourier transform of a PNG image.

    The analysis pipeline:
        1. Extract raw pixel data by decompressing IDAT and reversing PNG filters
           (done entirely with our own parser – no Pillow).
        2. Convert to a 2-D numpy array.  RGB/RGBA images are converted to
           luminance (grayscale) using the standard Rec.601 coefficients so
           the spectrum is a single 2-D plot.  Grayscale images are used as-is.
        3. Apply ``np.fft.fft2`` and shift the zero-frequency component to the
           centre with ``np.fft.fftshift``.
        4. Display the log-magnitude spectrum with matplotlib.

    Testing / validation approach:
        A synthetic test image (e.g. a pure sine wave or a checkerboard) has a
        known Fourier spectrum: specific peaks at the signal frequencies.
        ``FFTAnalyzer.verify_with_synthetic()`` generates such an image and
        confirms that the computed FFT matches the theoretical expectation.
    """

    def __init__(self, png_file: PNGFile) -> None:
        self.png_file = png_file
        self._pixel_array: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Pixel extraction
    # ------------------------------------------------------------------

    def get_pixel_array(self) -> np.ndarray:
        """
        Return the image as a 2-D (grayscale) numpy float64 array of shape
        (height, width).  Result is cached after the first call.

        RGB/RGBA images are converted to luminance (Rec.601) because the 2-D
        FFT operates on a single channel.  Use :meth:`get_display_array` to
        obtain the original colours for visualization.
        """
        if self._pixel_array is not None:
            return self._pixel_array

        rgb = self._load_channel_array()
        channels = rgb.shape[2]

        if channels == 1:
            gray = rgb[:, :, 0]
        elif channels == 2:
            gray = rgb[:, :, 0]
        else:
            gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        self._pixel_array = gray
        return self._pixel_array

    def _load_channel_array(self) -> np.ndarray:
        """Return pixels as float64 array of shape (height, width, channels) in [0, 1]."""
        image_data = self.png_file.get_image_data()
        raw_pixels = image_data.to_flat_pixels()

        width, height, channels = self.png_file.get_pixel_layout()
        bit_depth = image_data.output_bit_depth

        dtype = np.uint16 if bit_depth == 16 else np.uint8
        arr = np.frombuffer(raw_pixels, dtype=dtype)

        if bit_depth == 16:
            arr = arr.byteswap().newbyteorder()

        arr = arr.reshape(height, width, channels).astype(np.float64)
        max_val = (2 ** bit_depth) - 1
        return arr / max_val

    def get_display_array(self) -> np.ndarray:
        """
        Return pixels ready for ``imshow``.

        RGB/RGBA images are returned as (H, W, 3) float arrays in [0, 1].
        Grayscale images are returned as (H, W) float arrays in [0, 1].
        """
        rgb = self._load_channel_array()
        channels = rgb.shape[2]

        if channels == 1:
            return rgb[:, :, 0]
        if channels == 2:
            return rgb[:, :, 0]
        if channels == 4:
            return rgb[:, :, :3]
        return rgb

    # ------------------------------------------------------------------
    # FFT computation
    # ------------------------------------------------------------------

    def compute_fft(self) -> np.ndarray:
        """
        Compute the 2-D FFT of the image and return the shifted
        log-magnitude spectrum (ready for plotting).
        """
        pixels = self.get_pixel_array()
        fft2 = np.fft.fft2(pixels)
        fft_shifted = np.fft.fftshift(fft2)
        # Add 1 before log to avoid log(0)
        magnitude = np.log1p(np.abs(fft_shifted))
        return magnitude

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_spectrum(
        self,
        save_path: str | None = None,
        show: bool = True,
    ) -> None:
        """
        Display a side-by-side figure:
            Left  – original image (colour when RGB/RGBA, else grayscale)
            Right – log-magnitude FFT spectrum (DC at centre)

        Parameters:
            save_path – if provided, save the figure to this path.
            show      – if True, call plt.show() (blocks until window closed).
        """
        display = self.get_display_array()
        spectrum = self.compute_fft()

        ihdr = self.png_file.get_ihdr()
        fig = plt.figure(figsize=(12, 5))
        gs = gridspec.GridSpec(1, 2, figure=fig)

        # Original image – show true colours for RGB/RGBA
        ax_img = fig.add_subplot(gs[0])
        if display.ndim == 3:
            ax_img.imshow(display, vmin=0, vmax=1)
        else:
            ax_img.imshow(display, cmap="gray", vmin=0, vmax=1)
        ax_img.set_title(
            f"Original image\n"
            f"{ihdr.width}x{ihdr.height} px - {ihdr.color_type_name}"
        )
        ax_img.axis("off")

        # FFT spectrum
        ax_fft = fig.add_subplot(gs[1])
        im = ax_fft.imshow(spectrum, cmap="inferno", origin="upper")
        ax_fft.set_title(
            "2-D FFT – log|F(u,v)|\n(zero frequency at centre)"
        )
        ax_fft.set_xlabel("Frequency u")
        ax_fft.set_ylabel("Frequency v")
        plt.colorbar(im, ax=ax_fft, fraction=0.046, pad=0.04)

        plt.suptitle(f"FFT Analysis - {self.png_file.path}", fontsize=9)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Spectrum saved to: {save_path}")

        if show:
            plt.show()
        else:
            plt.close(fig)

    # ------------------------------------------------------------------
    # Validation with synthetic test image
    # ------------------------------------------------------------------

    @staticmethod
    def verify_with_synthetic(frequency: int = 8, show: bool = True) -> bool:
        """
        Validate the FFT pipeline using a synthetic sine-wave image.

        Creates an N×N image containing a horizontal sine wave of *frequency*
        complete cycles.  The FFT of such an image should show exactly two
        symmetric peaks at ±*frequency* on the horizontal frequency axis.

        Returns True if the peaks are at the expected positions.
        """
        N = 256
        x = np.linspace(0, 2 * np.pi * frequency, N, endpoint=False)
        sine_row = np.sin(x)
        image = np.tile(sine_row, (N, 1))  # N identical rows

        fft2 = np.fft.fft2(image)
        fft_shifted = np.fft.fftshift(fft2)
        magnitude = np.abs(fft_shifted)

        # The DC row (centre row) should have peaks at col = N//2 ± frequency
        centre_row = magnitude[N // 2, :]
        expected_peak_cols = {N // 2 - frequency, N // 2 + frequency}
        top2_cols = set(np.argsort(centre_row)[-2:])
        peaks_correct = top2_cols == expected_peak_cols

        if show:
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            axes[0].imshow(image, cmap="gray", aspect="auto")
            axes[0].set_title(f"Synthetic sine wave (f={frequency} cycles)")
            axes[0].axis("off")

            im = axes[1].imshow(np.log1p(magnitude), cmap="inferno", origin="upper")
            axes[1].set_title("FFT spectrum (expected peaks visible)")
            plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

            status = "PASS" if peaks_correct else "FAIL"
            plt.suptitle(
                f"FFT validation: {status}\n"
                f"Expected peaks at columns {sorted(expected_peak_cols)}, "
                f"found at {sorted(top2_cols)}"
            )
            plt.tight_layout()
            plt.show()

        return peaks_correct
