from PIL import ImageChops, ImageFilter
from PIL.Image import Image, Resampling
import PIL.Image


def remove_border(image: Image) -> Image:
    bg = PIL.Image.new(mode="RGB", size=image.size, color=image.getpixel((0, 0)))
    diff = ImageChops.difference(image, bg)
    diff = ImageChops.add(image1=diff, image2=diff, scale=2, offset=-30)
    bbox = diff.getbbox()
    return image.crop(bbox)


def resize_blur(blur_img: Image, sizers: tuple[int, int]) -> Image:
    return (
        blur_img
        .resize(sizers, resample=Resampling.LANCZOS)
        .filter(ImageFilter.GaussianBlur(10))
    )


def resize_width_main(border_img: Image, size_width: int) -> Image:
    width, height = border_img.size[:2]
    w_percent = size_width / width
    h_size = round(height * w_percent)
    return border_img.resize((size_width, h_size), Resampling.LANCZOS)


def center_overlay(overlay_img: Image, blur_img: Image) -> None:
    box = [
        round((xb - xo)/2)
        for xb, xo in zip(blur_img.size, overlay_img.size)
    ][:2]
    blur_img.paste(im=overlay_img, box=box)


def main() -> None:
    image = PIL.Image.open('resized_download.png')
    border_img = remove_border(image)
    blur_img = resize_blur(border_img, (1080, 1080))
    overlay_img = resize_width_main(border_img, 1080)
    center_overlay(overlay_img, blur_img)
    blur_img.save('resized.png')


if __name__ == '__main__':
    main()