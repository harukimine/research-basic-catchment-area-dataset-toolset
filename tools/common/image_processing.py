import os
from PIL import Image
from figure_setting import FigureSetting


class ImageProcessing:
    def __init__(self):
        super().__init__()
        print("init ImageProcessing")
        self.image_example: Image = None
        self.image_tag = None
        self.save_dir = "catchment-area"

    def set_tag(self, tag):
        self.image_tag = tag

    def set_save_dir(self, save_dir):
        self.save_dir = save_dir

    def save_image(self):
        self.save_tiff(self.image_example, file_name="example")
        self.close_image(self.image_example)

    def save_tiff(self, image: Image, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image is None:
            return
        if image.mode in ["1", "L"]:
            setting = FigureSetting.monochrome_tiff
        else:
            setting = FigureSetting.tiff
        path = os.path.join(self.save_dir, file_name + ".tif")
        image.save(path, **kwargs, **setting, tiffinfo=self.image_tag)

    def save_mono_tiff(self, image: Image, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_tiff(image, file_name, **kwargs)

    def save_png(self, image: Image, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image.mode in ["1", "L"]:
            setting = FigureSetting.monochrome_png
        else:
            setting = FigureSetting.png
        path = os.path.join(self.save_dir, file_name + ".png")
        image.save(path, **kwargs, **setting, tiffinfo=self.image_tag)

    def save_mono_png(self, image: Image, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_png(image, file_name, **kwargs)

    def close_image(self, image: Image):
        if image is not None:
            image.close()

    def convert_image_mono(self, image: Image) -> Image:
        new_image = Image.new(mode="1", size=image.size)
        for y in range(image.height):
            for x in range(image.width):
                if image.getpixel((x, y)) == 0:
                    new_image.putpixel((x, y), 0)
                else:
                    new_image.putpixel((x, y), 1)
        return new_image
