import fiona
import rasterio
from rasterio.tools.mask import mask



class Mask(object):
    'Masking processed images'

    def __init__(self, input_file, mask):
        self.input = input_file
        self.input_name = self.input.replace(".TIF","")
        self.mask = mask

    def run(self):

        with fiona.open(self.mask, "r") as shapefile:
            geoms = [feature["geometry"] for feature in shapefile]

        with rasterio.open(self.input) as src:
            out_image, out_transform = mask(src, geoms, crop=True)
            out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})

        with rasterio.open(self.input_name + "_masked" + ".TIF", "w", **out_meta) as dest:
            dest.write(out_image)



#
# test = Mask("/Users/iaryna/Desktop/rasterio-cookbook-master/recipies/data/LC81810252016195LGN00432.TIF", "/Users/iaryna/Desktop/rasterio-cookbook-master/recipies/data/kyiv_right.shp")
#
# test.run()
